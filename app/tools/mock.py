"""Mock tools for local learning and tests."""

from __future__ import annotations

from app.schemas import PlanStep, StepStatus
from app.tools.base import ToolDefinition, ToolResult


class MockStepTool:
    """Deterministic tool that marks a plan step as completed.

    这个工具不访问网络、不读写文件、不调用模型。它只把 PlanStep 转成
    ToolResult，让第 8 步可以先验证工具层边界。
    """

    def __init__(self, name: str = "mock_step", description: str | None = None) -> None:
        self._definition = ToolDefinition(
            name=name,
            description=description or "A deterministic mock tool for executing plan steps.",
            input_schema={
                "type": "object",
                "required": ["step_id", "goal", "expected_output"],
                "properties": {
                    "step_id": {"type": "integer"},
                    "goal": {"type": "string"},
                    "expected_output": {"type": "string"},
                },
            },
        )

    @property
    def definition(self) -> ToolDefinition:
        """Return mock tool metadata."""

        return self._definition

    def run(self, step: PlanStep) -> ToolResult:
        """Return a deterministic successful result for a plan step."""

        return ToolResult(
            tool_name=self.definition.name,
            status=StepStatus.COMPLETED,
            output=f"mock tool completed step {step.step_id}: {step.goal}",
        )
