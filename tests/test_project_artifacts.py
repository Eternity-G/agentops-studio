"""Tests for final project delivery artifacts."""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_deployment_artifacts_exist() -> None:
    """Final delivery should include Docker and deployment files."""

    required_paths = [
        "Dockerfile",
        ".dockerignore",
        "docs/部署说明.md",
        "docs/简历项目描述.md",
        "docs/项目复盘.md",
        "docs/第18步-部署简历材料与项目复盘.md",
    ]

    for relative_path in required_paths:
        assert (PROJECT_ROOT / relative_path).exists(), relative_path


def test_dockerfile_runs_fastapi_app() -> None:
    """Dockerfile should expose and start the FastAPI app."""

    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "EXPOSE 8000" in dockerfile
    assert "uvicorn" in dockerfile
    assert "app.api.routes:app" in dockerfile


def test_dockerignore_excludes_local_secrets() -> None:
    """Docker context should exclude local environment files."""

    dockerignore = (PROJECT_ROOT / ".dockerignore").read_text(encoding="utf-8")

    assert ".env" in dockerignore
    assert ".env.*" in dockerignore


def test_final_docs_include_acceptance_commands() -> None:
    """Final docs should include the commands needed for acceptance."""

    deploy_doc = (PROJECT_ROOT / "docs" / "部署说明.md").read_text(encoding="utf-8")
    review_doc = (PROJECT_ROOT / "docs" / "项目复盘.md").read_text(encoding="utf-8")

    for command in ["python -m pytest", "python scripts/run_evals.py", "python -m uvicorn"]:
        assert command in deploy_doc
        assert command in review_doc


def test_resume_doc_mentions_core_agent_capabilities() -> None:
    """Resume material should mention core project capabilities."""

    resume_doc = (PROJECT_ROOT / "docs" / "简历项目描述.md").read_text(encoding="utf-8")

    for keyword in ["Pydantic", "DeepSeek", "ToolRegistry", "EvaluationRunner"]:
        assert keyword in resume_doc
