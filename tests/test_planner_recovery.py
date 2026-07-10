"""Tests for planner retry and fallback behavior."""

from __future__ import annotations

import asyncio

import pytest

from app.agent import AgentRuntime
from app.planner import Planner
from app.providers import MockProvider
from app.providers.base import ProviderInfo
from app.schemas import ExecutionPlan, TaskInput


class FailingProvider:
    """Provider that always fails."""

    def __init__(self, message: str = "bad model output") -> None:
        self._message = message
        self._info = ProviderInfo(name="failing", model="broken-model", is_mock=False)

    @property
    def info(self) -> ProviderInfo:
        """Return provider metadata."""

        return self._info

    async def create_plan(self, task_input: TaskInput) -> ExecutionPlan:
        """Always fail to simulate invalid model output."""

        raise ValueError(self._message)


class FlakyProvider:
    """Provider that fails once and then succeeds."""

    def __init__(self) -> None:
        self._calls = 0
        self._mock = MockProvider(model="recovered-mock")
        self._info = ProviderInfo(name="flaky", model="flaky-model", is_mock=False)

    @property
    def info(self) -> ProviderInfo:
        """Return provider metadata."""

        return self._info

    async def create_plan(self, task_input: TaskInput) -> ExecutionPlan:
        """Fail on the first call, then return a valid plan."""

        self._calls += 1
        if self._calls == 1:
            raise ValueError("invalid json")
        return await self._mock.create_plan(task_input)


def test_planner_retries_after_provider_failure() -> None:
    """Planner should retry a failing provider before using fallback."""

    planner = Planner(provider=FlakyProvider(), fallback_provider=MockProvider(), max_retries=1)

    plan = asyncio.run(planner.create_plan_from_text("验证重试"))

    assert len(plan.steps) == 3
    assert [attempt.success for attempt in planner.last_attempts] == [False, True]
    assert planner.last_attempts[0].error == "invalid json"
    assert planner.last_attempts[1].provider_name == "flaky"


def test_planner_falls_back_to_mock_after_retries_fail() -> None:
    """Planner should fallback to MockProvider when the real provider keeps failing."""

    planner = Planner(
        provider=FailingProvider(),
        fallback_provider=MockProvider(model="fallback-mock"),
        max_retries=1,
    )

    plan = asyncio.run(planner.create_plan_from_text("验证 fallback"))

    assert len(plan.steps) == 3
    assert [attempt.success for attempt in planner.last_attempts] == [False, False, True]
    assert planner.last_attempts[-1].provider_name == "mock"
    assert planner.last_attempts[-1].used_fallback is True


def test_planner_raises_when_primary_and_fallback_fail() -> None:
    """Planner should raise a clear error if no provider can produce a plan."""

    planner = Planner(
        provider=FailingProvider("primary failed"),
        fallback_provider=FailingProvider("fallback failed"),
        max_retries=0,
    )

    with pytest.raises(RuntimeError, match="all planning providers failed"):
        asyncio.run(planner.create_plan_from_text("全部失败"))


def test_agent_trace_records_provider_retry_and_fallback() -> None:
    """Agent trace should expose provider retry and fallback events."""

    planner = Planner(
        provider=FailingProvider(),
        fallback_provider=MockProvider(model="fallback-mock"),
        max_retries=1,
    )
    runtime = AgentRuntime(planner=planner)

    state = asyncio.run(runtime.run_from_text("验证 trace 中的 fallback"))
    messages = [event.message for event in state.trace_events]

    assert state.status == "completed"
    assert any("provider failing/broken-model attempt 1 failed" in message for message in messages)
    assert any("provider failing/broken-model attempt 2 failed" in message for message in messages)
    assert any("provider mock/fallback-mock attempt 1 succeeded with fallback" in message for message in messages)
