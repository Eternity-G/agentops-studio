"""Mock model provider used for local learning and tests.

MockProvider 不调用任何真实模型 API。它的作用是稳定地产生符合
`ExecutionPlan` 的结构化计划，让后续 Planner 和 Agent 主链路可以先开发、
先测试，再替换成真实模型 provider。
"""

from __future__ import annotations

from app.providers.base import ProviderInfo
from app.schemas import ExecutionPlan, PlanStep, TaskInput


class MockProvider:
    """Deterministic provider that returns a valid execution plan.

    这里故意保持确定性：同一个任务永远返回同样形状的计划。这样测试不会因为
    模型随机性而变得不稳定，也方便学习 provider 接口的边界。
    """

    def __init__(self, model: str = "mock-planner-v1") -> None:
        self._info = ProviderInfo(name="mock", model=model, is_mock=True)

    @property
    def info(self) -> ProviderInfo:
        """Return provider metadata."""

        return self._info

    async def create_plan(self, task_input: TaskInput) -> ExecutionPlan:
        """Return a valid plan that follows the shared Pydantic schemas."""

        normalized_task = task_input.task
        return ExecutionPlan(
            task=normalized_task,
            steps=[
                PlanStep(
                    step_id=1,
                    goal="理解用户任务",
                    expected_output="明确任务目标、约束和期望输出",
                ),
                PlanStep(
                    step_id=2,
                    goal="拆解执行步骤",
                    expected_output="生成可执行的结构化计划",
                    depends_on=[1],
                    tool_name="planner",
                ),
                PlanStep(
                    step_id=3,
                    goal="检查计划完整性",
                    expected_output="确认步骤依赖有效且输出可被验证",
                    depends_on=[2],
                ),
            ],
        )
