"""Tests for in-memory session state."""

from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

from app.agent import AgentRuntime
from app.api.routes import create_app
from app.document_qa import MarkdownQuestionAnswerer
from app.memory import InMemorySessionStore
from app.schemas import DocumentQuestionInput, MemoryEventType, MemoryNoteInput, TaskInput


def test_memory_store_records_task_run() -> None:
    """The store should keep a compact task-run event."""

    store = InMemorySessionStore()
    state = asyncio.run(AgentRuntime().run(TaskInput(task="记录任务记忆")))

    session = store.record_task_run(session_id="session-a", state=state)

    assert session.session_id == "session-a"
    assert len(session.events) == 1
    assert session.events[0].event_type == MemoryEventType.TASK_RUN
    assert session.events[0].payload["task_id"] == state.task_id


def test_memory_store_records_document_answer() -> None:
    """The store should keep a compact document-QA event."""

    store = InMemorySessionStore()
    answer = MarkdownQuestionAnswerer().answer(
        DocumentQuestionInput(
            question="第 14 步是什么？",
            path="docs/第14步-文档问答最小RAG链路.md",
        )
    )

    session = store.record_document_answer(session_id="session-a", answer=answer)

    assert len(session.events) == 1
    assert session.events[0].event_type == MemoryEventType.DOCUMENT_QA
    assert session.events[0].payload["source_path"] == "docs/第14步-文档问答最小RAG链路.md"


def test_memory_store_records_note() -> None:
    """Manual notes should be appended as memory events."""

    store = InMemorySessionStore()
    note = MemoryNoteInput(content="这是一次人工备注", metadata={"kind": "learning"})

    session = store.record_note(session_id="session-a", note=note)

    assert len(session.events) == 1
    assert session.events[0].event_type == MemoryEventType.NOTE
    assert session.events[0].payload["content"] == "这是一次人工备注"


def test_task_api_writes_session_memory() -> None:
    """POST /tasks/run should write memory when metadata.session_id is provided."""

    client = TestClient(create_app())

    response = client.post(
        "/tasks/run",
        json={"task": "把任务写入会话", "metadata": {"session_id": "api-session"}},
    )
    session_response = client.get("/sessions/api-session")
    session = session_response.json()

    assert response.status_code == 200
    assert session_response.status_code == 200
    assert session["session_id"] == "api-session"
    assert session["events"][0]["event_type"] == "task_run"


def test_document_api_writes_session_memory() -> None:
    """POST /documents/ask should write memory when session_id is provided."""

    client = TestClient(create_app())

    response = client.post(
        "/documents/ask",
        json={
            "question": "第 14 步是什么？",
            "path": "docs/第14步-文档问答最小RAG链路.md",
            "session_id": "doc-session",
        },
    )
    session_response = client.get("/sessions/doc-session")
    session = session_response.json()

    assert response.status_code == 200
    assert session_response.status_code == 200
    assert session["events"][0]["event_type"] == "document_qa"
    assert session["events"][0]["payload"]["source_path"] == "docs/第14步-文档问答最小RAG链路.md"


def test_session_note_api_appends_note() -> None:
    """POST /sessions/{session_id}/notes should append a manual note."""

    client = TestClient(create_app())

    response = client.post(
        "/sessions/note-session/notes",
        json={"content": "保留这个学习重点", "metadata": {"source": "manual"}},
    )
    body = response.json()

    assert response.status_code == 200
    assert body["session_id"] == "note-session"
    assert body["events"][0]["event_type"] == "note"
    assert body["events"][0]["payload"]["metadata"]["source"] == "manual"


def test_openapi_contains_session_paths() -> None:
    """OpenAPI schema should expose session memory endpoints."""

    client = TestClient(create_app())

    response = client.get("/openapi.json")
    schema = response.json()

    assert response.status_code == 200
    assert "/sessions/{session_id}" in schema["paths"]
    assert "/sessions/{session_id}/notes" in schema["paths"]
