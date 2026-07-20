"""Tests for the browser pages."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.routes import create_app


def test_web_index_returns_demo_page() -> None:
    """GET / should return the static browser home page."""

    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert "代码仓库理解 Agent" in response.text
    assert "/overview" in response.text
    assert "/static/app.js?v=markdown-table-20260720" in response.text


def test_web_feature_pages_are_split() -> None:
    """Each major feature should have its own browser page."""

    client = TestClient(create_app())
    expected_titles = {
        "/overview": "仓库概览",
        "/ask": "代码问答",
        "/impact": "影响分析",
        "/review": "Diff Review",
        "/eval": "评测报告",
    }

    for path, title in expected_titles.items():
        response = client.get(path)

        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert title in response.text


def test_static_assets_are_served() -> None:
    """FastAPI should serve CSS, JS, and visual assets for the browser pages."""

    client = TestClient(create_app())

    css_response = client.get("/static/styles.css")
    js_response = client.get("/static/app.js")
    svg_response = client.get("/static/assets/flow.svg")

    assert css_response.status_code == 200
    assert "tool-layout" in css_response.text
    assert "markdown-output" in css_response.text
    assert js_response.status_code == 200
    assert "/codebase/ask" in js_response.text
    assert "/codebase/overview" in js_response.text
    assert "markdownToHtml" in js_response.text
    assert "tableAlignments" in js_response.text
    assert 'class="table-scroll"' in js_response.text
    assert ".markdown-output table" in css_response.text
    assert svg_response.status_code == 200
    assert "<svg" in svg_response.text


def test_latest_eval_report_endpoint_returns_markdown() -> None:
    """The frontend should be able to load the latest eval report."""

    client = TestClient(create_app())

    response = client.get("/evals/latest-report")

    assert response.status_code == 200
    assert "# AgentOps Studio" in response.text
    assert "100%" in response.text


def test_openapi_contains_web_and_eval_report_paths() -> None:
    """OpenAPI schema should expose web and eval-report endpoints."""

    client = TestClient(create_app())

    response = client.get("/openapi.json")
    schema = response.json()

    assert response.status_code == 200
    assert "/" in schema["paths"]
    assert "/overview" in schema["paths"]
    assert "/ask" in schema["paths"]
    assert "/impact" in schema["paths"]
    assert "/review" in schema["paths"]
    assert "/eval" in schema["paths"]
    assert "/evals/latest-report" in schema["paths"]
