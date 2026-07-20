"""Tests for the DeepSeek provider.

These tests do not call the real DeepSeek API. They use a fake transport so the
provider contract can be tested safely without network access or API keys.
"""

from __future__ import annotations

import asyncio

import pytest

from app.providers import DeepSeekProvider, create_provider
from app.schemas import ExecutionPlan, TaskInput
from app.settings import AppSettings


def test_deepseek_provider_requires_api_key() -> None:
    """A real provider should fail fast when the API key is missing."""

    with pytest.raises(ValueError, match="DEEPSEEK_API_KEY"):
        DeepSeekProvider(api_key="")


def test_deepseek_provider_returns_execution_plan_from_fake_response() -> None:
    """DeepSeekProvider should parse OpenAI-compatible JSON responses."""

    def fake_transport(payload: dict[str, object]) -> dict[str, object]:
        assert payload["model"] == "deepseek-v4-flash"
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"task":"生成真实模型计划","steps":['
                            '{"step_id":1,"goal":"理解任务","expected_output":"任务摘要",'
                            '"tool_name":null,"depends_on":[],"status":"pending"},'
                            '{"step_id":2,"goal":"生成计划","expected_output":"结构化计划",'
                            '"tool_name":"planner","depends_on":[1],"status":"pending"}'
                            "]}"
                        )
                    }
                }
            ]
        }

    provider = DeepSeekProvider(
        api_key="test-key",
        model="deepseek-v4-flash",
        transport=fake_transport,
    )

    plan = asyncio.run(provider.create_plan(TaskInput(task="生成真实模型计划")))

    assert isinstance(plan, ExecutionPlan)
    assert plan.task == "生成真实模型计划"
    assert len(plan.steps) == 2
    assert plan.steps[1].tool_name == "planner"


def test_deepseek_provider_accepts_fenced_json_response() -> None:
    """Provider should tolerate fenced JSON even though prompt asks for plain JSON."""

    def fake_transport(_: dict[str, object]) -> dict[str, object]:
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            "```json\n"
                            '{"task":"围栏 JSON","steps":['
                            '{"step_id":1,"goal":"解析","expected_output":"成功",'
                            '"tool_name":null,"depends_on":[],"status":"pending"}'
                            "]}\n"
                            "```"
                        )
                    }
                }
            ]
        }

    provider = DeepSeekProvider(api_key="test-key", transport=fake_transport)

    plan = asyncio.run(provider.create_plan(TaskInput(task="围栏 JSON")))

    assert plan.task == "围栏 JSON"
    assert len(plan.steps) == 1


def test_deepseek_provider_can_return_markdown_text() -> None:
    """Provider should support non-JSON text generation for overview reports."""

    def fake_transport(payload: dict[str, object]) -> dict[str, object]:
        assert "response_format" not in payload
        return {"choices": [{"message": {"content": "# 仓库理解报告\n\n基于证据生成。"}}]}

    provider = DeepSeekProvider(api_key="test-key", transport=fake_transport)

    report = asyncio.run(provider.complete_text(system_prompt="写报告", user_prompt="证据"))

    assert "仓库理解报告" in report


def test_deepseek_factory_uses_settings() -> None:
    """Factory should create DeepSeekProvider from AppSettings."""

    settings = AppSettings(
        model_provider="deepseek",
        default_model="deepseek-v4-pro",
        deepseek_api_key="test-key",
        deepseek_base_url="https://api.deepseek.com",
    )

    provider = create_provider(settings)

    assert provider.info.name == "deepseek"
    assert provider.info.model == "deepseek-v4-pro"
    assert provider.info.is_mock is False


def test_deepseek_provider_rejects_invalid_json_response() -> None:
    """Invalid model JSON should fail before it reaches Planner."""

    def fake_transport(_: dict[str, object]) -> dict[str, object]:
        return {"choices": [{"message": {"content": "not json"}}]}

    provider = DeepSeekProvider(api_key="test-key", transport=fake_transport)

    with pytest.raises(ValueError, match="not valid JSON"):
        asyncio.run(provider.create_plan(TaskInput(task="坏 JSON")))
