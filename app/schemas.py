"""Shared Pydantic schemas for the Agent main flow.

这些 schema 是后续 Agent 主链路的稳定数据契约。它们不依赖 FastAPI，
因此可以同时被 API 层、Planner、Executor、评测模块和测试代码复用。

本文件暂时只定义数据结构，不实现任何模型调用、工具调用或 Agent 执行逻辑。
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Annotated
from uuid import uuid4

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


class MemoryEventType(StrEnum):
    """Kinds of events stored in one in-memory session."""

    TASK_RUN = "task_run"
    DOCUMENT_QA = "document_qa"
    CODEBASE_QA = "codebase_qa"
    NOTE = "note"


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


class CodeEvidence(StrictSchema):
    """Source-grounded evidence from a code repository."""

    file_path: ShortText = Field(description="Repository-relative file path.")
    line_start: PositiveInt = Field(description="First evidence line number.")
    line_end: PositiveInt = Field(description="Last evidence line number.")
    quote: LongText = Field(description="Short code or documentation excerpt.")


class CodebaseInput(StrictSchema):
    """Input that identifies a local code repository."""

    repository_path: ShortText = Field(
        default=".",
        description="Local repository path. It must stay inside the configured workspace.",
    )


class CodebaseQuestionInput(CodebaseInput):
    """Question asked against a local code repository."""

    question: LongText = Field(description="Developer question about the codebase.")
    session_id: ShortText | None = Field(
        default=None,
        description="Optional session id used to store the codebase answer in memory.",
    )


class CodeSearchInput(CodebaseInput):
    """Keyword search request for a local code repository."""

    query: ShortText = Field(description="Keyword or symbol to search in the repository.")
    limit: PositiveInt = Field(default=20, le=50, description="Maximum number of matches.")


class CodeImpactInput(CodebaseInput):
    """Request for file-level impact analysis."""

    target_path: ShortText = Field(description="Repository-relative file path to analyze.")


class CodebaseSummary(StrictSchema):
    """High-level summary of a local code repository."""

    repository_path: ShortText
    total_files: int = Field(ge=0)
    analyzed_files: int = Field(ge=0)
    total_lines: int = Field(ge=0)
    top_level_directories: list[ShortText] = Field(default_factory=list, max_length=50)
    key_files: list[ShortText] = Field(default_factory=list, max_length=50)
    languages: dict[ShortText, int] = Field(default_factory=dict)
    frontend_signals: list[ShortText] = Field(default_factory=list, max_length=20)
    backend_signals: list[ShortText] = Field(default_factory=list, max_length=20)


class CodeSearchMatch(StrictSchema):
    """One keyword match in a code repository."""

    file_path: ShortText
    line_number: PositiveInt
    line: ShortText


class PythonSymbol(StrictSchema):
    """Python class/function/import symbol extracted with ast."""

    name: ShortText
    symbol_type: ShortText
    file_path: ShortText
    line_number: PositiveInt
    parent: ShortText | None = None


class CodebaseAnswer(StrictSchema):
    """Answer grounded in local repository evidence."""

    question: LongText
    answer: LongText
    completed: bool
    repository_path: ShortText
    evidence: list[CodeEvidence] = Field(default_factory=list, max_length=10)
    searched_terms: list[ShortText] = Field(default_factory=list, max_length=10)
    risk_notes: list[ShortText] = Field(default_factory=list, max_length=10)


class CodeImpactReport(StrictSchema):
    """File-level impact analysis report."""

    target_path: ShortText
    referenced_by: list[CodeEvidence] = Field(default_factory=list, max_length=20)
    likely_impacted_areas: list[ShortText] = Field(default_factory=list, max_length=20)
    test_suggestions: list[ShortText] = Field(default_factory=list, max_length=10)


class DiffReviewReport(StrictSchema):
    """Review report for current git diff."""

    changed_files: list[ShortText] = Field(default_factory=list, max_length=100)
    summary: LongText
    risk_notes: list[ShortText] = Field(default_factory=list, max_length=20)
    test_suggestions: list[ShortText] = Field(default_factory=list, max_length=20)
    evidence: list[CodeEvidence] = Field(default_factory=list, max_length=20)


class DocumentQuestionInput(StrictSchema):
    """Input for asking a question about one local Markdown document."""

    question: LongText = Field(description="Question to answer from the Markdown document.")
    path: ShortText = Field(description="Markdown file path relative to the workspace root.")
    session_id: ShortText | None = Field(
        default=None,
        description="Optional session id used to store the document answer in memory.",
    )


class DocumentQuestionAnswer(StrictSchema):
    """Structured answer produced from one local Markdown document."""

    question: LongText = Field(description="Original user question.")
    answer: LongText = Field(description="Answer grounded in the provided Markdown document.")
    source_path: ShortText = Field(description="Markdown file path used as the source.")
    excerpt: LongText | None = Field(
        default=None,
        description="Most relevant document excerpt found by the minimal retriever.",
    )
    completed: bool = Field(description="Whether the document question-answer flow completed.")
    evidence: list[Evidence] = Field(
        default_factory=list,
        description="Evidence snippets used to support the answer.",
        max_length=5,
    )


class MemoryNoteInput(StrictSchema):
    """Manual note that can be appended to a session."""

    content: LongText = Field(description="Human-readable note content.")
    metadata: dict[str, ShortText] = Field(
        default_factory=dict,
        description="Small structured note metadata.",
        max_length=20,
    )


class MemoryEvent(StrictSchema):
    """One event stored in a session memory timeline."""

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: MemoryEventType = Field(description="Type of memory event.")
    summary: ShortText = Field(description="Short event summary for quick inspection.")
    payload: dict[str, object] = Field(
        default_factory=dict,
        description="Small structured event payload for debugging and future retrieval.",
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SessionState(StrictSchema):
    """In-memory state for one user or demo session."""

    session_id: ShortText = Field(description="Stable id for one conversation session.")
    events: list[MemoryEvent] = Field(
        default_factory=list,
        description="Ordered memory events in this session.",
        max_length=100,
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
