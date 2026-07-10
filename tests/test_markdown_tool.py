"""Tests for the local Markdown reader tool."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.schemas import PlanStep, StepStatus
from app.tools import MockToolRegistry, ReadMarkdownTool


def test_read_markdown_tool_reads_workspace_markdown(tmp_path: Path) -> None:
    """ReadMarkdownTool should read a Markdown file inside its workspace root."""

    document = tmp_path / "docs" / "note.md"
    document.parent.mkdir()
    document.write_text("# 标题\n\n这是测试文档。", encoding="utf-8")
    tool = ReadMarkdownTool(base_dir=tmp_path)

    result = tool.read("docs/note.md")

    assert result.tool_name == "read_markdown"
    assert result.status == StepStatus.COMPLETED
    assert "file=docs/note.md" in result.output
    assert "truncated=false" in result.output
    assert "这是测试文档" in result.output


def test_read_markdown_tool_can_run_from_plan_step(tmp_path: Path) -> None:
    """Tool.run should use PlanStep.expected_output as the Markdown path."""

    document = tmp_path / "guide.md"
    document.write_text("## 使用说明", encoding="utf-8")
    tool = ReadMarkdownTool(base_dir=tmp_path)
    step = PlanStep(
        step_id=1,
        goal="读取文档",
        expected_output="guide.md",
        tool_name="read_markdown",
    )

    result = tool.run(step)

    assert result.status == StepStatus.COMPLETED
    assert "使用说明" in result.output


def test_read_markdown_tool_rejects_non_markdown_file(tmp_path: Path) -> None:
    """Only .md files should be readable."""

    document = tmp_path / "secret.txt"
    document.write_text("不要读取", encoding="utf-8")
    tool = ReadMarkdownTool(base_dir=tmp_path)

    result = tool.read("secret.txt")

    assert result.status == StepStatus.FAILED
    assert result.error is not None
    assert "only Markdown .md files" in result.error


def test_read_markdown_tool_rejects_path_outside_workspace(tmp_path: Path) -> None:
    """Path traversal should not escape the configured workspace root."""

    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside.md"
    workspace.mkdir()
    outside.write_text("外部文件", encoding="utf-8")
    tool = ReadMarkdownTool(base_dir=workspace)

    result = tool.read("../outside.md")

    assert result.status == StepStatus.FAILED
    assert result.error is not None
    assert "workspace root" in result.error


def test_read_markdown_tool_truncates_long_content(tmp_path: Path) -> None:
    """Long Markdown files should be truncated to keep tool output bounded."""

    document = tmp_path / "long.md"
    document.write_text("abcdef", encoding="utf-8")
    tool = ReadMarkdownTool(base_dir=tmp_path, max_chars=3)

    result = tool.read("long.md")

    assert result.status == StepStatus.COMPLETED
    assert "truncated=true" in result.output
    assert result.output.endswith("abc")


def test_read_markdown_tool_rejects_invalid_max_chars() -> None:
    """max_chars should be positive to avoid ambiguous output limits."""

    with pytest.raises(ValueError, match="max_chars must be positive"):
        ReadMarkdownTool(max_chars=0)


def test_mock_registry_exposes_markdown_reader() -> None:
    """The default registry should expose the Markdown reader tool."""

    registry = MockToolRegistry()
    names = {definition.name for definition in registry.list_definitions()}

    assert "read_markdown" in names
