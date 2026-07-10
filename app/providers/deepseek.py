"""DeepSeek OpenAI-compatible provider.

这个 provider 使用 DeepSeek 的 OpenAI-compatible Chat Completions 接口。
它只负责把 `TaskInput` 转换成请求，把模型返回的 JSON 转换成 `ExecutionPlan`。

安全约束：
- API key 只从环境变量读取。
- 不在日志、异常、README 或测试中写入真实 key。
- 测试使用 fake transport，不真实访问 DeepSeek。
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable, Mapping
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.providers.base import ProviderInfo
from app.schemas import ExecutionPlan, TaskInput

ChatCompletionTransport = Callable[[dict[str, Any]], Mapping[str, Any]]


class DeepSeekProvider:
    """Provider that creates plans with DeepSeek's OpenAI-compatible API."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-v4-flash",
        timeout_seconds: int = 60,
        transport: ChatCompletionTransport | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY is required for DeepSeekProvider")

        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._transport = transport
        self._info = ProviderInfo(name="deepseek", model=model, is_mock=False)

    @property
    def info(self) -> ProviderInfo:
        """Return provider metadata."""

        return self._info

    async def create_plan(self, task_input: TaskInput) -> ExecutionPlan:
        """Create a structured execution plan from a user task."""

        payload = self._build_payload(task_input)
        if self._transport is not None:
            response = self._transport(payload)
        else:
            response = await asyncio.to_thread(self._post_chat_completion, payload)

        content = self._extract_message_content(response)
        plan_data = self._parse_json_content(content)
        return ExecutionPlan.model_validate(plan_data)

    def _build_payload(self, task_input: TaskInput) -> dict[str, Any]:
        """Build an OpenAI-compatible chat completion request."""

        return {
            "model": self._model,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是 AgentOps Studio 的任务规划器。"
                        "只输出 JSON，不要输出 Markdown。"
                        "JSON 必须符合 ExecutionPlan schema："
                        "{\"task\": string, \"steps\": [{\"step_id\": int, "
                        "\"goal\": string, \"expected_output\": string, "
                        "\"tool_name\": string|null, \"depends_on\": int[], "
                        "\"status\": \"pending\"}]}. "
                        "step_id 必须从 1 开始且唯一，depends_on 只能引用已存在步骤。"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"用户任务：{task_input.task}\n"
                        f"可选上下文 metadata：{task_input.metadata}\n"
                        "请生成 2 到 5 个可执行步骤。"
                    ),
                },
            ],
        }

    def _post_chat_completion(self, payload: dict[str, Any]) -> Mapping[str, Any]:
        """Send the HTTP request using Python standard library."""

        request = Request(
            url=f"{self._base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"DeepSeek API HTTP error {exc.code}: {body}") from exc
        except URLError as exc:
            raise RuntimeError(f"DeepSeek API request failed: {exc.reason}") from exc

    @staticmethod
    def _extract_message_content(response: Mapping[str, Any]) -> str:
        """Extract assistant message content from an OpenAI-compatible response."""

        try:
            content = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError("DeepSeek response does not contain choices[0].message.content") from exc

        if not isinstance(content, str) or not content.strip():
            raise ValueError("DeepSeek response content is empty")
        return content

    @staticmethod
    def _parse_json_content(content: str) -> dict[str, Any]:
        """Parse model JSON output, accepting plain JSON or fenced JSON."""

        cleaned = content.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ValueError("DeepSeek response content is not valid JSON") from exc

        if not isinstance(parsed, dict):
            raise ValueError("DeepSeek response JSON must be an object")
        return parsed
