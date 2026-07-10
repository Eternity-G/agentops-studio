"""Minimal task planner.

第 5 步只跑通“任务输入 -> provider -> 结构化计划”这条链路。
Planner 不直接依赖 OpenAI、DeepSeek、通义千问或 Ollama SDK，而是依赖
第 4 步定义的 `ModelProvider` 接口。
"""

from __future__ import annotations

from dataclasses import dataclass

from app.providers import MockProvider, ModelProvider, ProviderInfo, create_provider
from app.schemas import ExecutionPlan, TaskInput


@dataclass(frozen=True, slots=True)
class ProviderAttempt:
    """One provider attempt recorded by Planner.

    这个结构用于第 12 步的可观测性：真实模型可能返回非法 JSON、非法 schema
    或网络错误，Planner 需要把每次尝试的结果暴露给 Agent trace。
    """

    provider_name: str
    model: str
    attempt: int
    success: bool
    error: str | None = None
    used_fallback: bool = False


class Planner:
    """Create structured execution plans from user tasks.

    Planner 的职责非常窄：
    1. 接收已经通过 schema 校验的 `TaskInput`。
    2. 调用 provider 生成计划。
    3. 再次用 `ExecutionPlan` 校验 provider 输出。

    这里不做工具调用、不做反思、不做执行。那些能力会在后续 Agent 主链路中加入。
    """

    def __init__(
        self,
        provider: ModelProvider | None = None,
        fallback_provider: ModelProvider | None = None,
        max_retries: int = 1,
    ) -> None:
        self._provider = provider or create_provider()
        self._fallback_provider = fallback_provider or MockProvider()
        self._max_retries = max_retries
        self._last_attempts: list[ProviderAttempt] = []

    @property
    def provider_info(self) -> ProviderInfo:
        """Expose provider metadata for future trace and debugging."""

        return self._provider.info

    @property
    def last_attempts(self) -> list[ProviderAttempt]:
        """Return provider attempts from the most recent planning call."""

        return list(self._last_attempts)

    async def create_plan(self, task_input: TaskInput) -> ExecutionPlan:
        """Create a validated execution plan from a task input."""

        self._last_attempts = []
        errors: list[str] = []

        for attempt in range(1, self._max_retries + 2):
            try:
                return await self._create_validated_plan(
                    provider=self._provider,
                    task_input=task_input,
                    attempt=attempt,
                    used_fallback=False,
                )
            except Exception as exc:
                error = str(exc)
                errors.append(error)
                self._record_attempt(
                    provider=self._provider,
                    attempt=attempt,
                    success=False,
                    error=error,
                    used_fallback=False,
                )

        if self._fallback_provider is not None:
            try:
                return await self._create_validated_plan(
                    provider=self._fallback_provider,
                    task_input=task_input,
                    attempt=1,
                    used_fallback=True,
                )
            except Exception as exc:
                error = str(exc)
                errors.append(error)
                self._record_attempt(
                    provider=self._fallback_provider,
                    attempt=1,
                    success=False,
                    error=error,
                    used_fallback=True,
                )

        joined_errors = " | ".join(errors)
        raise RuntimeError(f"all planning providers failed: {joined_errors}")

    async def create_plan_from_text(self, task: str) -> ExecutionPlan:
        """Convenience helper for demos and early tests."""

        return await self.create_plan(TaskInput(task=task))

    async def _create_validated_plan(
        self,
        *,
        provider: ModelProvider,
        task_input: TaskInput,
        attempt: int,
        used_fallback: bool,
    ) -> ExecutionPlan:
        """Call a provider and validate the returned execution plan."""

        plan = await provider.create_plan(task_input)

        # Provider 已声明返回 ExecutionPlan，但这里仍做一次显式 re-validation。
        # 未来真实模型 provider 可能先拿到 JSON，再转成 schema；这个边界校验
        # 能确保 Planner 对外永远返回合法计划。
        validated_plan = ExecutionPlan.model_validate(plan.model_dump())
        self._record_attempt(
            provider=provider,
            attempt=attempt,
            success=True,
            error=None,
            used_fallback=used_fallback,
        )
        return validated_plan

    def _record_attempt(
        self,
        *,
        provider: ModelProvider,
        attempt: int,
        success: bool,
        error: str | None,
        used_fallback: bool,
    ) -> None:
        """Record one provider attempt for Agent trace."""

        self._last_attempts.append(
            ProviderAttempt(
                provider_name=provider.info.name,
                model=provider.info.model,
                attempt=attempt,
                success=success,
                error=error,
                used_fallback=used_fallback,
            )
        )
