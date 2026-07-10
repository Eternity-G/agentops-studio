"""Regression tests for tool-call failure handling."""

from __future__ import annotations

import asyncio

from app.agent import AgentRunStatus, AgentRuntime
from app.schemas import PlanStep, StepStatus
from app.tools import MockStepTool, ToolDefinition, ToolRegistry, ToolResult


class ExplodingTool:
    """Test tool that raises an exception during execution."""

    def __init__(self, name: str = "exploding") -> None:
        self._name = name

    @property
    def definition(self) -> ToolDefinition:
        """Return test tool metadata."""

        return ToolDefinition(
            name=self._name,
            description="A test tool that raises an exception.",
            input_schema={"type": "object"},
        )

    def run(self, step: PlanStep) -> ToolResult:
        """Raise a deterministic exception for regression testing."""

        raise RuntimeError(f"boom at step {step.step_id}")


def test_registry_converts_tool_exception_to_failed_result() -> None:
    """Tool exceptions should become structured failed ToolResult objects."""

    registry = ToolRegistry(tools=[ExplodingTool()])
    step = PlanStep(
        step_id=1,
        goal="触发工具异常",
        expected_output="失败结果",
        tool_name="exploding",
    )

    result = registry.execute_step(step)

    assert result.tool_name == "exploding"
    assert result.status == StepStatus.FAILED
    assert result.error is not None
    assert "boom at step 1" in result.error


def test_agent_runtime_fails_when_plan_uses_unknown_tool() -> None:
    """Unknown tool names should make the Agent run fail in a visible way."""

    registry = ToolRegistry(tools=[MockStepTool(name="mock_step")])
    runtime = AgentRuntime(tool_registry=registry)

    state = asyncio.run(runtime.run_from_text("生成包含未知工具的计划"))

    failed_results = [result for result in state.step_results if result.status == StepStatus.FAILED]
    trace_messages = [event.message for event in state.trace_events]

    assert state.status == AgentRunStatus.FAILED
    assert failed_results
    assert failed_results[0].tool_name == "planner"
    assert failed_results[0].error is not None
    assert "unknown tool: planner" in failed_results[0].error
    assert any("tool failed for step 2" in message for message in trace_messages)
    assert state.errors
    assert state.final_answer is None


def test_agent_runtime_fails_when_tool_raises_exception() -> None:
    """Tool exceptions should propagate as failed Agent state, not silent success."""

    registry = ToolRegistry(
        tools=[
            MockStepTool(name="mock_step"),
            ExplodingTool(name="planner"),
        ]
    )
    runtime = AgentRuntime(tool_registry=registry)

    state = asyncio.run(runtime.run_from_text("生成工具异常回归测试"))

    failed_results = [result for result in state.step_results if result.status == StepStatus.FAILED]

    assert state.status == AgentRunStatus.FAILED
    assert failed_results
    assert failed_results[0].tool_name == "planner"
    assert failed_results[0].error is not None
    assert "boom at step 2" in failed_results[0].error
