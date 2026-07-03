"""Tests for shared Pydantic schemas.

这些测试的重点不是业务智能，而是数据契约是否稳定。后续 Agent 主链路
只要依赖这些 schema，就能更早发现结构化输出错误。
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas import Evidence, ExecutionPlan, FinalAnswer, PlanStep, StepStatus, TaskInput


def test_task_input_accepts_valid_payload() -> None:
    """Task input should keep only the structured fields we explicitly support."""

    task_input = TaskInput(
        task="  分析 Agent 项目的第三步应该如何设计  ",
        user_id="student-001",
        metadata={"stage": "schema"},
    )

    assert task_input.task == "分析 Agent 项目的第三步应该如何设计"
    assert task_input.user_id == "student-001"
    assert task_input.metadata["stage"] == "schema"


def test_task_input_rejects_empty_task() -> None:
    """An empty task should fail before it reaches any Agent logic."""

    with pytest.raises(ValidationError):
        TaskInput(task="   ")


def test_task_input_rejects_unknown_fields() -> None:
    """Unknown fields should be rejected to avoid silent schema drift."""

    with pytest.raises(ValidationError):
        TaskInput(task="生成计划", unexpected_field="should fail")


def test_execution_plan_accepts_valid_steps() -> None:
    """A valid plan should contain ordered steps with stable ids."""

    plan = ExecutionPlan(
        task="为 Agent 项目生成实施计划",
        steps=[
            PlanStep(
                step_id=1,
                goal="理解任务",
                expected_output="得到任务摘要",
            ),
            PlanStep(
                step_id=2,
                goal="生成计划",
                expected_output="得到结构化计划",
                depends_on=[1],
                tool_name="planner",
            ),
        ],
    )

    assert len(plan.steps) == 2
    assert plan.steps[0].status == StepStatus.PENDING
    assert plan.steps[1].depends_on == [1]


def test_execution_plan_rejects_duplicate_step_ids() -> None:
    """Step ids must be unique so traces and retries can reference them safely."""

    with pytest.raises(ValidationError):
        ExecutionPlan(
            task="生成重复步骤",
            steps=[
                PlanStep(step_id=1, goal="第一步", expected_output="输出 A"),
                PlanStep(step_id=1, goal="第二步", expected_output="输出 B"),
            ],
        )


def test_execution_plan_rejects_missing_dependencies() -> None:
    """A step cannot depend on a step id that is absent from the plan."""

    with pytest.raises(ValidationError):
        ExecutionPlan(
            task="生成缺失依赖",
            steps=[
                PlanStep(
                    step_id=1,
                    goal="执行任务",
                    expected_output="输出结果",
                    depends_on=[99],
                ),
            ],
        )


def test_plan_step_rejects_self_dependency() -> None:
    """A step depending on itself would make the execution graph invalid."""

    with pytest.raises(ValidationError):
        PlanStep(
            step_id=1,
            goal="自依赖步骤",
            expected_output="不应创建成功",
            depends_on=[1],
        )


def test_final_answer_accepts_evidence_and_next_actions() -> None:
    """Final answer should carry result, evidence, and optional next actions."""

    final_answer = FinalAnswer(
        answer="第 3 步应先定义稳定 schema，再接入 Planner。",
        summary="先定数据契约，再写执行逻辑。",
        completed=True,
        confidence=0.92,
        evidence=[
            Evidence(
                title="项目 README",
                source="README.md",
                quote="下一步是 3. Pydantic Schema。",
            )
        ],
        next_actions=["实现 Planner 最小版本"],
    )

    assert final_answer.completed is True
    assert final_answer.confidence == 0.92
    assert final_answer.evidence[0].source == "README.md"


def test_final_answer_rejects_invalid_confidence() -> None:
    """Confidence must stay inside the explicit 0.0 to 1.0 range."""

    with pytest.raises(ValidationError):
        FinalAnswer(
            answer="结果",
            summary="摘要",
            completed=True,
            confidence=1.5,
        )


def test_execution_plan_exports_json_schema() -> None:
    """Pydantic should expose JSON Schema for future OpenAPI and LLM output checks."""

    schema = ExecutionPlan.model_json_schema()

    assert schema["title"] == "ExecutionPlan"
    assert "steps" in schema["properties"]
