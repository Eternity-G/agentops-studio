"""Base contracts for Agent tools.

工具协议的目标和 provider 协议类似：上层 AgentRuntime 不关心具体工具如何实现，
只关心“给定一个 PlanStep，能否得到结构化 ToolResult”。
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import Field

from app.schemas import PlanStep, StepStatus, StrictSchema


class ToolDefinition(StrictSchema):
    """Static metadata for one tool."""

    name: str = Field(description="Unique tool name used by PlanStep.tool_name.")
    description: str = Field(description="Human-readable tool description.")
    input_schema: dict[str, object] = Field(
        default_factory=dict,
        description="JSON-schema-like input description for future LLM tool selection.",
    )


class ToolResult(StrictSchema):
    """Structured result returned by a tool call."""

    tool_name: str = Field(description="Name of the tool that produced this result.")
    status: StepStatus = Field(description="Tool execution status.")
    output: str = Field(description="Human-readable tool output.")
    error: str | None = Field(
        default=None,
        description="Optional machine-readable or human-readable failure reason.",
    )


@runtime_checkable
class Tool(Protocol):
    """Common interface for all tools."""

    @property
    def definition(self) -> ToolDefinition:
        """Return tool metadata for registry lookup and future LLM prompts."""

    def run(self, step: PlanStep) -> ToolResult:
        """Execute one plan step and return a structured result."""
