"""Tests for the minimal Markdown question-answer chain."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.api.routes import create_app
from app.document_qa import MarkdownQuestionAnswerer
from app.schemas import DocumentQuestionInput
from app.tools import ReadMarkdownTool


def test_markdown_question_answerer_returns_grounded_answer(tmp_path: Path) -> None:
    """The answerer should cite an excerpt from the requested Markdown document."""

    document = tmp_path / "agent.md"
    document.write_text(
        "# AgentOps\n\nAgentOps Studio 用于构建 Agent 工程系统。\n\n其他内容。",
        encoding="utf-8",
    )
    answerer = MarkdownQuestionAnswerer(reader=ReadMarkdownTool(base_dir=tmp_path))

    result = answerer.answer(DocumentQuestionInput(question="AgentOps Studio 用于什么？", path="agent.md"))

    assert result.completed is True
    assert result.source_path == "agent.md"
    assert "Agent 工程系统" in result.answer
    assert result.evidence
    assert result.evidence[0].source == "agent.md"


def test_markdown_question_answerer_returns_structured_failure(tmp_path: Path) -> None:
    """Missing documents should become structured incomplete answers."""

    answerer = MarkdownQuestionAnswerer(reader=ReadMarkdownTool(base_dir=tmp_path))

    result = answerer.answer(DocumentQuestionInput(question="缺失文档是什么？", path="missing.md"))

    assert result.completed is False
    assert result.excerpt is None
    assert result.evidence == []
    assert "无法读取文档" in result.answer


def test_markdown_question_answerer_limits_excerpt_length(tmp_path: Path) -> None:
    """Selected excerpts should stay bounded for future prompt usage."""

    document = tmp_path / "long.md"
    document.write_text("abcdef", encoding="utf-8")
    answerer = MarkdownQuestionAnswerer(
        reader=ReadMarkdownTool(base_dir=tmp_path),
        excerpt_chars=3,
    )

    result = answerer.answer(DocumentQuestionInput(question="abcdef", path="long.md"))

    assert result.completed is True
    assert result.excerpt == "abc"


def test_document_ask_api_returns_answer() -> None:
    """POST /documents/ask should expose the minimal document QA chain."""

    client = TestClient(create_app())

    response = client.post(
        "/documents/ask",
        json={
            "question": "第 13 步实现了什么？",
            "path": "docs/第13步-本地Markdown文档读取工具.md",
        },
    )
    body = response.json()

    assert response.status_code == 200
    assert body["completed"] is True
    assert body["source_path"] == "docs/第13步-本地Markdown文档读取工具.md"
    assert body["evidence"]


def test_document_ask_api_rejects_invalid_body() -> None:
    """FastAPI should validate document question request bodies."""

    client = TestClient(create_app())

    response = client.post("/documents/ask", json={"question": "   ", "path": "docs/readme.md"})

    assert response.status_code == 422


def test_openapi_contains_document_ask_path() -> None:
    """OpenAPI schema should expose the document question-answer endpoint."""

    client = TestClient(create_app())

    response = client.get("/openapi.json")
    schema = response.json()

    assert response.status_code == 200
    assert "/documents/ask" in schema["paths"]
