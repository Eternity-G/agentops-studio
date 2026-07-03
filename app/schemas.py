"""Shared Pydantic schemas for the Agent main flow.

这些 schema 是后续 Agent 主链路的稳定数据契约。它们不依赖 FastAPI，
因此可以同时被 API 层、Planner、Executor、评测模块和测试代码复用。

本文件暂时只定义数据结构，不实现任何模型调用、工具调用或 Agent 执行逻辑。
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, StringConstraints, model_validator


ShortText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=200),
]
LongText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=4000),
]


class StrictSchema(BaseModel):
    """Base class for project schemas.

    `extra="forbid"` 可以防止调用方悄悄传入未定义字段。对 Agent 项目来说，
    这很重要：模型输出一旦多字段、少字段或字段拼错，测试应该立刻暴露问题。
    """

    model_config = ConfigDict(extra="forbid")


class StepStatus(StrEnum):
    """Execution status for a plan step."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class TaskInput(StrictSchema):
    """User task accepted by the future Agent runtime."""

    task: LongText = Field(
        description="The concrete task that the Agent should solve.",
        examples=["分析一个 Agent 项目应该如何拆解，并输出执行计划。"],
    )
    user_id: ShortText | None = Field(
        default=None,
        description="Optional user identifier for future memory and tracing.",
    )
    metadata: dict[str, ShortText] = Field(
        default_factory=dict,
        description="Small structured context, such as project name or scenario tags.",
        max_length=20,
    )


class PlanStep(StrictSchema):
    """One executable step in an Agent plan."""

    step_id: PositiveInt = Field(description="Unique positive step id inside one plan.")
    goal: ShortText = Field(description="The goal of this step.")
    expected_output: ShortText = Field(description="The observable output this step should produce.")
    tool_name: ShortText | None = Field(
        default=None,
        description="Optional tool name. Empty means the model can answer or reason directly.",
    )
    depends_on: list[PositiveInt] = Field(
        default_factory=list,
        description="Step ids that must complete before this step can run.",
        max_length=10,
    )
    status: StepStatus = Field(
        default=StepStatus.PENDING,
        description="Current execution status. Stage 3 only defines the enum; it does not run steps.",
    )

    @model_validator(mode="after")
    def reject_self_dependency(self) -> PlanStep:
        """A step cannot depend on itself."""

        if self.step_id in self.depends_on:
            raise ValueError("a plan step cannot depend on itself")
        return self


class ExecutionPlan(StrictSchema):
    """Structured plan generated from a task."""

    task: LongText = Field(description="Original task or normalized task description.")
    steps: list[PlanStep] = Field(
        description="Ordered steps that the Agent should execute.",
        min_length=1,
        max_length=20,
    )

    @model_validator(mode="after")
    def validate_step_graph(self) -> ExecutionPlan:
        """Ensure step ids are unique and dependencies point to existing steps."""

        step_ids = [step.step_id for step in self.steps]
        unique_ids = set(step_ids)
        if len(step_ids) != len(unique_ids):
            raise ValueError("plan step ids must be unique")

        for step in self.steps:
            missing_dependencies = set(step.depends_on) - unique_ids
            if missing_dependencies:
                missing = sorted(missing_dependencies)
                raise ValueError(f"step {step.step_id} depends on missing steps: {missing}")

        return self


class Evidence(StrictSchema):
    """Evidence item used to support a final answer."""

    title: ShortText = Field(description="Human-readable source title.")
    source: ShortText = Field(description="Source identifier, URL, file path, or tool result id.")
    quote: LongText | None = Field(
        default=None,
        description="Optional short evidence excerpt. Keep it small and traceable.",
    )


class FinalAnswer(StrictSchema):
    """Structured final answer returned by the future Agent runtime."""

    answer: LongText = Field(description="Final answer for the user.")
    summary: ShortText = Field(description="One-sentence summary of the result.")
    completed: bool = Field(description="Whether the task is considered completed.")
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score from 0.0 to 1.0. This is a system signal, not truth.",
    )
    evidence: list[Evidence] = Field(
        default_factory=list,
        description="Evidence used to support the answer.",
        max_length=10,
    )
    next_actions: list[ShortText] = Field(
        default_factory=list,
        description="Optional recommended next actions for the user or system.",
        max_length=5,
    )
