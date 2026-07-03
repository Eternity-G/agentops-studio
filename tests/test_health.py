"""Tests for the FastAPI health-check endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app import __version__
from app.api.routes import create_app


def test_health_status_code() -> None:
    """`GET /health` should exist and return HTTP 200."""

    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200


def test_health_response_body() -> None:
    """The health response should expose stable, observable fields."""

    client = TestClient(create_app())

    response = client.get("/health")

    assert response.json() == {
        "status": "ok",
        "app_name": "AgentOps Studio",
        "environment": "development",
        "version": __version__,
    }


def test_openapi_contains_health_path() -> None:
    """FastAPI should include `/health` in the generated OpenAPI schema."""

    client = TestClient(create_app())

    response = client.get("/openapi.json")
    schema = response.json()

    assert response.status_code == 200
    assert "/health" in schema["paths"]
