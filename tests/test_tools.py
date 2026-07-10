"""Tests for the mock tool layer."""

from __future__ import annotations

import pytest

from app.schemas import PlanStep, StepStatus
from app.tools import MockStepTool, MockToolRegistry, ToolRegistry


def test_mock_step_tool_returns_completed_result() -> None:
    """MockStepTool should convert a PlanStep into a successful ToolResult."""

    tool = MockStepTool()
    step = PlanStep(step_id=1, goal="执行 mock 步骤", expected_output="得到 mock 输出")

    result = tool.run(step)

    assert result.tool_name == "mock_step"
    assert result.status == StepStatus.COMPLETED
    assert "执行 mock 步骤" in result.output


def test_tool_registry_lists_tool_definitions() -> None:
    """Tool registry should expose metadata for prompts, docs, and tests."""

    registry = MockToolRegistry()

    definitions = registry.list_definitions()
    names = {definition.name for definition in definitions}

    assert {"mock_step", "planner"}.issubset(names)
    assert all(definition.description for definition in definitions)
    assert all(definition.input_schema for definition in definitions)


def test_tool_registry_executes_default_tool_when_step_has_no_tool_name() -> None:
    """Steps without a tool name should use the registry default tool."""

    registry = MockToolRegistry()
    step = PlanStep(step_id=1, goal="默认工具", expected_output="完成")

    result = registry.execute_step(step)

    assert result.tool_name == "mock_step"
    assert result.status == StepStatus.COMPLETED


def test_tool_registry_executes_named_tool() -> None:
    """Steps with a tool name should route to the named tool."""

    registry = MockToolRegistry()
    step = PlanStep(step_id=1, goal="规划工具", expected_output="完成", tool_name="planner")

    result = registry.execute_step(step)

    assert result.tool_name == "planner"
    assert result.status == StepStatus.COMPLETED


def test_tool_registry_rejects_duplicate_tool_names() -> None:
    """Duplicate tool names should fail early."""

    registry = ToolRegistry(tools=[MockStepTool(name="duplicate")])

    with pytest.raises(ValueError, match="tool already registered"):
        registry.register(MockStepTool(name="duplicate"))


def test_tool_registry_returns_failed_result_for_unknown_tool() -> None:
    """Unknown tools should produce an explainable failed ToolResult."""

    registry = MockToolRegistry()
    step = PlanStep(step_id=1, goal="未知工具", expected_output="失败", tool_name="missing_tool")

    result = registry.execute_step(step)

    assert result.tool_name == "missing_tool"
    assert result.status == StepStatus.FAILED
    assert "unknown tool" in result.output
