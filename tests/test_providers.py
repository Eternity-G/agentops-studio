"""Tests for the model provider abstraction and MockProvider."""

from __future__ import annotations

import asyncio

import pytest

from app.providers import MockProvider, ModelProvider, create_provider
from app.providers.base import ProviderInfo
from app.schemas import ExecutionPlan, TaskInput
from app.settings import AppSettings


def test_mock_provider_exposes_provider_info() -> None:
    """MockProvider should expose stable metadata for tracing and debugging."""

    provider = MockProvider(model="mock-test-model")

    assert provider.info == ProviderInfo(name="mock", model="mock-test-model", is_mock=True)


def test_mock_provider_matches_model_provider_protocol() -> None:
    """MockProvider should satisfy the shared provider interface."""

    provider = MockProvider()

    assert isinstance(provider, ModelProvider)


def test_mock_provider_returns_execution_plan() -> None:
    """MockProvider should return a valid ExecutionPlan without any API key."""

    provider = MockProvider()
    task_input = TaskInput(task="为 Agent 项目生成实施计划")

    plan = asyncio.run(provider.create_plan(task_input))

    assert isinstance(plan, ExecutionPlan)
    assert plan.task == "为 Agent 项目生成实施计划"
    assert len(plan.steps) == 3
    assert [step.step_id for step in plan.steps] == [1, 2, 3]
    assert plan.steps[1].depends_on == [1]
    assert plan.steps[2].depends_on == [2]


def test_mock_provider_output_can_round_trip_through_schema() -> None:
    """Provider output should be serializable and valid after re-validation."""

    provider = MockProvider()
    task_input = TaskInput(task="验证结构化计划是否稳定")

    plan = asyncio.run(provider.create_plan(task_input))
    revalidated_plan = ExecutionPlan.model_validate(plan.model_dump())

    assert revalidated_plan == plan


def test_create_provider_uses_settings_default_model() -> None:
    """The provider factory should read model selection from settings."""

    settings = AppSettings(model_provider="mock", default_model="mock-from-settings")

    provider = create_provider(settings)

    assert provider.info.name == "mock"
    assert provider.info.model == "mock-from-settings"


def test_create_provider_rejects_unknown_provider() -> None:
    """Unknown provider names should fail early with a clear error."""

    settings = AppSettings(model_provider="unknown")

    with pytest.raises(ValueError, match="unsupported model provider"):
        create_provider(settings)
