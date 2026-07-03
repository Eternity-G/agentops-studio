"""Base contracts for model providers.

第 4 步只定义 provider 数据契约，不接任何真实模型。核心目标是让后续
OpenAI、DeepSeek、通义千问、Ollama 等实现都遵守同一组方法签名。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from app.schemas import ExecutionPlan, TaskInput


@dataclass(frozen=True, slots=True)
class ProviderInfo:
    """Static information about a model provider.

    这些信息用于日志、Trace 和测试。真实 provider 后续可以把厂商名、
    模型名、是否 mock 等信息暴露给上层，但不泄漏 SDK 细节。
    """

    name: str
    model: str
    is_mock: bool = False


@runtime_checkable
class ModelProvider(Protocol):
    """Common interface that every model provider must implement.

    接口设计成 async，是为了贴近真实模型调用。即使 MockProvider 现在不访问网络，
    未来 OpenAI-compatible provider 也可以直接复用这个抽象。
    """

    @property
    def info(self) -> ProviderInfo:
        """Return provider metadata for observability and debugging."""

    async def create_plan(self, task_input: TaskInput) -> ExecutionPlan:
        """Create a structured execution plan for a user task."""
