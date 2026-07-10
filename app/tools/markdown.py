"""Markdown file reader tool.

第 13 步开始让 Agent 具备读取本地资料的能力。这个工具刻意保持边界很窄：
只读取工作区内的 Markdown 文件，不访问网络，不读取任意系统文件。
"""

from __future__ import annotations

from pathlib import Path

from app.schemas import PlanStep, StepStatus
from app.tools.base import ToolDefinition, ToolResult


class ReadMarkdownTool:
    """Read one local Markdown file inside a trusted workspace root."""

    def __init__(self, base_dir: Path | str | None = None, max_chars: int = 4000) -> None:
        if max_chars <= 0:
            raise ValueError("max_chars must be positive")

        self._base_dir = Path(base_dir or ".").resolve()
        self._max_chars = max_chars
        self._definition = ToolDefinition(
            name="read_markdown",
            description="Read a Markdown file inside the project workspace.",
            input_schema={
                "type": "object",
                "required": ["path"],
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Markdown file path relative to the workspace root.",
                    }
                },
            },
        )

    @property
    def definition(self) -> ToolDefinition:
        """Return markdown reader metadata."""

        return self._definition

    def read(self, path: str) -> ToolResult:
        """Read one Markdown file and return a structured tool result."""

        try:
            file_path = self._resolve_markdown_path(path)
            content = file_path.read_text(encoding="utf-8")
        except Exception as exc:
            message = str(exc)
            return ToolResult(
                tool_name=self.definition.name,
                status=StepStatus.FAILED,
                output=message,
                error=message,
            )

        truncated = len(content) > self._max_chars
        visible_content = content[: self._max_chars]
        relative_path = file_path.relative_to(self._base_dir).as_posix()

        header = f"file={relative_path}\nchars={len(content)}\ntruncated={str(truncated).lower()}"
        return ToolResult(
            tool_name=self.definition.name,
            status=StepStatus.COMPLETED,
            output=f"{header}\n\n{visible_content}",
        )

    def run(self, step: PlanStep) -> ToolResult:
        """Execute a plan step by treating expected_output as the target path.

        当前 `PlanStep` 还没有独立的 tool arguments 字段，所以第 13 步先把
        `expected_output` 作为 Markdown 路径。第 14 步做 RAG 时可以再引入
        更正式的工具参数 schema。
        """

        return self.read(step.expected_output)

    def _resolve_markdown_path(self, path: str) -> Path:
        """Resolve and validate a Markdown path inside the workspace root."""

        raw_path = Path(path.strip())
        if not str(raw_path):
            raise ValueError("markdown path cannot be empty")

        candidate = raw_path if raw_path.is_absolute() else self._base_dir / raw_path
        resolved = candidate.resolve()

        if self._base_dir not in [resolved, *resolved.parents]:
            raise ValueError("markdown path must stay inside the workspace root")
        if resolved.suffix.lower() != ".md":
            raise ValueError("only Markdown .md files can be read")
        if not resolved.is_file():
            raise FileNotFoundError(f"markdown file not found: {raw_path.as_posix()}")

        return resolved
