"""Tests for the task-running API demo."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.routes import create_app


def test_run_task_api_returns_completed_state() -> None:
    """POST /tasks/run should run the minimal Agent flow."""

    client = TestClient(create_app())

    response = client.post("/tasks/run", json={"task": "通过 API 跑通 Agent 主链路"})
    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "completed"
    assert body["task_id"]
    assert body["trace_id"]
    assert body["plan"]["task"] == "通过 API 跑通 Agent 主链路"
    assert body["final_answer"]["completed"] is True


def test_run_task_api_returns_trace_events() -> None:
    """The API response should include basic trace events."""

    client = TestClient(create_app())

    response = client.post("/tasks/run", json={"task": "检查 trace 事件"})
    body = response.json()
    stages = {event["stage"] for event in body["trace_events"]}

    assert response.status_code == 200
    assert {"plan", "act", "reflect", "finalize"}.issubset(stages)
    assert all(event["trace_id"] == body["trace_id"] for event in body["trace_events"])


def test_run_task_api_rejects_invalid_task() -> None:
    """FastAPI should reject invalid request bodies via TaskInput schema."""

    client = TestClient(create_app())

    response = client.post("/tasks/run", json={"task": "   "})

    assert response.status_code == 422


def test_openapi_contains_task_run_path() -> None:
    """OpenAPI schema should expose the task-running demo endpoint."""

    client = TestClient(create_app())

    response = client.get("/openapi.json")
    schema = response.json()

    assert response.status_code == 200
    assert "/tasks/run" in schema["paths"]
