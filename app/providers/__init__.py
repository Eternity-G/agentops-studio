"""Model provider adapters.

模型适配层把“业务需要什么”与“具体厂商 SDK 怎么调用”隔离开。
后续接 OpenAI、DeepSeek、通义千问、Ollama 时，都应该实现同一个 provider 接口。
"""

from __future__ import annotations

from app.providers.base import ModelProvider, ProviderInfo
from app.providers.factory import create_provider
from app.providers.mock import MockProvider

__all__ = [
    "MockProvider",
    "ModelProvider",
    "ProviderInfo",
    "create_provider",
]
