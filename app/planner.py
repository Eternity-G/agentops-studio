"""Minimal task planner.

第 5 步只跑通“任务输入 -> provider -> 结构化计划”这条链路。
Planner 不直接依赖 OpenAI、DeepSeek、通义千问或 Ollama SDK，而是依赖
第 4 步定义的 `ModelProvider` 接口。
"""

from __future__ import annotations

from app.providers import ModelProvider, ProviderInfo, create_provider
from app.schemas import ExecutionPlan, TaskInput


class Planner:
    """Create structured execution plans from user tasks.

    Planner 的职责非常窄：
    1. 接收已经通过 schema 校验的 `TaskInput`。
    2. 调用 provider 生成计划。
    3. 再次用 `ExecutionPlan` 校验 provider 输出。

    这里不做工具调用、不做反思、不做执行。那些能力会在后续 Agent 主链路中加入。
    """

    def __init__(self, provider: ModelProvider | None = None) -> None:
        self._provider = provider or create_provider()

    @property
    def provider_info(self) -> ProviderInfo:
        """Expose provider metadata for future trace and debugging."""

        return self._provider.info

    async def create_plan(self, task_input: TaskInput) -> ExecutionPlan:
        """Create a validated execution plan from a task input."""

        plan = await self._provider.create_plan(task_input)

        # Provider 已声明返回 ExecutionPlan，但这里仍做一次显式 re-validation。
        # 未来真实模型 provider 可能先拿到 JSON，再转成 schema；这个边界校验
        # 能确保 Planner 对外永远返回合法计划。
        return ExecutionPlan.model_validate(plan.model_dump())

    async def create_plan_from_text(self, task: str) -> ExecutionPlan:
        """Convenience helper for demos and early tests."""

        return await self.create_plan(TaskInput(task=task))
