"""Tests for the minimal Planner."""

from __future__ import annotations

import asyncio

from app.planner import Planner
from app.providers import MockProvider
from app.schemas import ExecutionPlan, TaskInput


def test_planner_uses_mock_provider_by_default() -> None:
    """Planner should work without real model API keys."""

    planner = Planner()

    assert planner.provider_info.name == "mock"
    assert planner.provider_info.is_mock is True


def test_planner_creates_execution_plan_from_task_input() -> None:
    """Planner should convert TaskInput into a validated ExecutionPlan."""

    planner = Planner(provider=MockProvider())
    task_input = TaskInput(task="为 Agent 项目生成最小任务计划")

    plan = asyncio.run(planner.create_plan(task_input))

    assert isinstance(plan, ExecutionPlan)
    assert plan.task == "为 Agent 项目生成最小任务计划"
    assert len(plan.steps) == 3
    assert [step.step_id for step in plan.steps] == [1, 2, 3]


def test_planner_create_plan_from_text_helper() -> None:
    """Planner should provide a small helper for demos and learning."""

    planner = Planner(provider=MockProvider())

    plan = asyncio.run(planner.create_plan_from_text("拆解 Planner 第 5 步"))

    assert isinstance(plan, ExecutionPlan)
    assert plan.task == "拆解 Planner 第 5 步"


def test_planner_output_round_trips_through_execution_plan_schema() -> None:
    """Planner output should remain valid after serialization and re-validation."""

    planner = Planner(provider=MockProvider())

    plan = asyncio.run(planner.create_plan_from_text("验证 Planner 输出稳定性"))
    revalidated_plan = ExecutionPlan.model_validate(plan.model_dump())

    assert revalidated_plan == plan
