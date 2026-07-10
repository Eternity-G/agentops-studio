"""Tool registry implementations."""

from __future__ import annotations

from app.schemas import PlanStep, StepStatus
from app.tools.base import Tool, ToolDefinition, ToolResult
from app.tools.mock import MockStepTool


class ToolRegistry:
    """Registry that stores tools by name and executes plan steps."""

    def __init__(self, tools: list[Tool] | None = None, default_tool_name: str = "mock_step") -> None:
        self._tools: dict[str, Tool] = {}
        self._default_tool_name = default_tool_name

        for tool in tools or []:
            self.register(tool)

    def register(self, tool: Tool) -> None:
        """Register one tool by its unique name."""

        name = tool.definition.name
        if name in self._tools:
            raise ValueError(f"tool already registered: {name}")
        self._tools[name] = tool

    def list_definitions(self) -> list[ToolDefinition]:
        """Return tool metadata for documentation, prompts, and tests."""

        return [tool.definition for tool in self._tools.values()]

    def get(self, name: str) -> Tool:
        """Return a registered tool or raise a clear error."""

        try:
            return self._tools[name]
        except KeyError as exc:
            raise ValueError(f"unknown tool: {name}") from exc

    def execute_step(self, step: PlanStep) -> ToolResult:
        """Execute a plan step with its requested tool or the default tool."""

        tool_name = step.tool_name or self._default_tool_name
        try:
            tool = self.get(tool_name)
        except ValueError as exc:
            return ToolResult(
                tool_name=tool_name,
                status=StepStatus.FAILED,
                output=str(exc),
            )

        return tool.run(step)


class MockToolRegistry(ToolRegistry):
    """Default registry used before real tools are implemented."""

    def __init__(self) -> None:
        super().__init__(
            tools=[
                MockStepTool(name="mock_step", description="Default mock executor for simple steps."),
                MockStepTool(name="planner", description="Mock planner tool used by generated plans."),
            ],
            default_tool_name="mock_step",
        )
