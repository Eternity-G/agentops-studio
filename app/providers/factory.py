"""Provider factory.

工厂函数把 provider 创建逻辑集中起来。后续接 OpenAI、DeepSeek、通义千问、
Ollama 时，只需要扩展这里，而不是让业务代码到处判断厂商名称。
"""

from __future__ import annotations

from app.providers.base import ModelProvider
from app.providers.deepseek import DeepSeekProvider
from app.providers.mock import MockProvider
from app.settings import AppSettings, load_settings


def create_provider(settings: AppSettings | None = None) -> ModelProvider:
    """Create a model provider from application settings.

    遇到未知 provider 时直接抛错，可以让配置错误在启动或测试阶段暴露，
    而不是等到 Agent 运行时才失败。
    """

    current_settings = settings or load_settings()
    provider_name = current_settings.model_provider.strip().lower()

    if provider_name == "mock":
        return MockProvider(model=current_settings.default_model)

    if provider_name == "deepseek":
        return DeepSeekProvider(
            api_key=current_settings.deepseek_api_key or "",
            base_url=current_settings.deepseek_base_url,
            model=current_settings.default_model,
        )

    raise ValueError(f"unsupported model provider: {current_settings.model_provider}")
