"""Tests for the minimal Agent state machine."""

from __future__ import annotations

import asyncio

from app.agent import AgentRunStatus, AgentRuntime, AgentState, StepExecutionResult
from app.schemas import ExecutionPlan, FinalAnswer, StepStatus, TaskInput


def test_agent_runtime_completes_minimal_flow() -> None:
    """AgentRuntime should run task -> plan -> act -> reflect -> finalize."""

    runtime = AgentRuntime()

    state = asyncio.run(runtime.run(TaskInput(task="跑通最小 Agent 主链路")))

    assert state.status == AgentRunStatus.COMPLETED
    assert isinstance(state.plan, ExecutionPlan)
    assert isinstance(state.final_answer, FinalAnswer)
    assert state.final_answer.completed is True
    assert state.errors == []


def test_agent_runtime_creates_step_result_for_each_plan_step() -> None:
    """Every planned step should produce one mock execution result."""

    runtime = AgentRuntime()

    state = asyncio.run(runtime.run_from_text("验证步骤执行结果数量"))

    assert state.plan is not None
    assert len(state.step_results) == len(state.plan.steps)
    assert all(isinstance(result, StepExecutionResult) for result in state.step_results)
    assert all(result.status == StepStatus.COMPLETED for result in state.step_results)


def test_agent_state_round_trips_through_schema() -> None:
    """The final state should be serializable and valid after re-validation."""

    runtime = AgentRuntime()

    state = asyncio.run(runtime.run_from_text("验证 AgentState 可序列化"))
    revalidated_state = AgentState.model_validate(state.model_dump())

    assert revalidated_state == state


def test_agent_runtime_exposes_final_answer_summary() -> None:
    """The minimal flow should end with a user-facing final answer placeholder."""

    runtime = AgentRuntime()

    state = asyncio.run(runtime.run_from_text("生成最终答案占位结果"))

    assert state.final_answer is not None
    assert "plan -> act -> reflect -> finalize" in state.final_answer.summary
