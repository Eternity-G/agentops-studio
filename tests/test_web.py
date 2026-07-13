"""Tests for the browser demo page."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.routes import create_app


def test_web_index_returns_demo_page() -> None:
    """GET / should return the static browser demo page."""

    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    assert "代码仓库理解 Agent" in response.text
    assert "/static/app.js" in response.text


def test_static_assets_are_served() -> None:
    """FastAPI should serve CSS, JS, and visual assets for the demo page."""

    client = TestClient(create_app())

    css_response = client.get("/static/styles.css")
    js_response = client.get("/static/app.js")
    svg_response = client.get("/static/assets/flow.svg")

    assert css_response.status_code == 200
    assert "panel-grid" in css_response.text
    assert js_response.status_code == 200
    assert "/codebase/ask" in js_response.text
    assert svg_response.status_code == 200
    assert "<svg" in svg_response.text


def test_latest_eval_report_endpoint_returns_markdown() -> None:
    """The frontend should be able to load the latest eval report."""

    client = TestClient(create_app())

    response = client.get("/evals/latest-report")

    assert response.status_code == 200
    assert "# AgentOps Studio 自动评测报告" in response.text
    assert "通过率：100%" in response.text


def test_openapi_contains_web_and_eval_report_paths() -> None:
    """OpenAPI schema should expose web and eval-report endpoints."""

    client = TestClient(create_app())

    response = client.get("/openapi.json")
    schema = response.json()

    assert response.status_code == 200
    assert "/" in schema["paths"]
    assert "/evals/latest-report" in schema["paths"]
