"""Tests for enterprise codebase understanding features."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.api.routes import create_app
from app.codebase.qa import CodebaseQuestionAnswerer
from app.codebase.scanner import RepositoryScanner
from app.codebase.search import CodeSearcher
from app.codebase.security import RepositorySecurity
from app.codebase.symbols import PythonSymbolAnalyzer


def _create_sample_repo(root: Path) -> Path:
    """Create a small full-stack-like repository for tests."""

    repo = root / "sample-repo"
    backend = repo / "backend"
    frontend = repo / "frontend" / "src"
    tests = repo / "tests"
    backend.mkdir(parents=True)
    frontend.mkdir(parents=True)
    tests.mkdir(parents=True)

    (repo / "README.md").write_text("# Sample Repo\n\nFull-stack example.", encoding="utf-8")
    (repo / "package.json").write_text('{"scripts":{"dev":"vite"}}', encoding="utf-8")
    (repo / "pyproject.toml").write_text("[project]\nname='sample'", encoding="utf-8")
    (backend / "api.py").write_text(
        "\n".join(
            [
                "from backend.service import UserService",
                "",
                "class UserRoute:",
                "    def login(self):",
                "        return UserService().login_user()",
            ]
        ),
        encoding="utf-8",
    )
    (backend / "service.py").write_text(
        "\n".join(
            [
                "class UserService:",
                "    def login_user(self):",
                "        return 'token'",
            ]
        ),
        encoding="utf-8",
    )
    (frontend / "Login.tsx").write_text(
        "export function Login(){ return <button>login</button> }",
        encoding="utf-8",
    )
    (tests / "test_api.py").write_text("def test_login(): assert True", encoding="utf-8")
    (repo / ".env").write_text("SECRET=should-not-read", encoding="utf-8")
    return repo


def test_repository_scanner_detects_full_stack_signals(tmp_path: Path) -> None:
    """Scanner should identify key files, languages, and front/back signals."""

    repo = _create_sample_repo(tmp_path)
    scanner = RepositoryScanner(RepositorySecurity(tmp_path))

    summary = scanner.summarize("sample-repo")

    assert summary.analyzed_files >= 6
    assert "Python" in summary.languages
    assert "TypeScript" in summary.languages
    assert "package.json" in summary.key_files
    assert "pyproject.toml" in summary.key_files
    assert "package.json" in summary.frontend_signals
    assert "pyproject.toml" in summary.backend_signals


def test_code_searcher_returns_file_and_line(tmp_path: Path) -> None:
    """Search should return file path and line number for keyword matches."""

    _create_sample_repo(tmp_path)
    searcher = CodeSearcher(RepositorySecurity(tmp_path))

    matches = searcher.search("sample-repo", "login_user")

    assert matches
    assert matches[0].file_path in {"backend/api.py", "backend/service.py"}
    assert matches[0].line_number >= 1


def test_python_symbol_analyzer_extracts_classes_and_methods(tmp_path: Path) -> None:
    """Symbol analyzer should extract Python classes and methods."""

    _create_sample_repo(tmp_path)
    analyzer = PythonSymbolAnalyzer(RepositorySecurity(tmp_path))

    symbols = analyzer.analyze_repository("sample-repo")
    names = {(symbol.symbol_type, symbol.name) for symbol in symbols}

    assert ("class", "UserService") in names
    assert ("method", "login_user") in names


def test_codebase_answer_returns_evidence(tmp_path: Path) -> None:
    """Codebase QA should return grounded evidence for developer questions."""

    _create_sample_repo(tmp_path)
    answerer = CodebaseQuestionAnswerer(security=RepositorySecurity(tmp_path))

    answer = answerer.answer("sample-repo", "login_user 在哪里实现？")

    assert answer.completed is True
    assert answer.evidence
    assert any("backend/service.py" == evidence.file_path for evidence in answer.evidence)
    assert "backend/service.py" in answer.answer


def test_codebase_impact_finds_references(tmp_path: Path) -> None:
    """Impact analysis should find files referencing a target module."""

    _create_sample_repo(tmp_path)
    answerer = CodebaseQuestionAnswerer(security=RepositorySecurity(tmp_path))

    report = answerer.impact("sample-repo", "backend/service.py")

    assert report.target_path == "backend/service.py"
    assert any(evidence.file_path == "backend/api.py" for evidence in report.referenced_by)
    assert report.test_suggestions


def test_security_rejects_sensitive_files(tmp_path: Path) -> None:
    """Codebase reader should reject sensitive local files."""

    repo = _create_sample_repo(tmp_path)
    security = RepositorySecurity(tmp_path)

    repository_root = security.resolve_repository(repo.as_posix())

    try:
        security.resolve_file(repository_root, ".env")
    except ValueError as exc:
        assert "sensitive" in str(exc)
    else:  # pragma: no cover - defensive assertion.
        raise AssertionError("sensitive file should be rejected")


def test_codebase_api_exposes_summary_search_and_ask() -> None:
    """FastAPI should expose codebase analysis endpoints for the current project."""

    client = TestClient(create_app())

    summary_response = client.post("/codebase/summary", json={"repository_path": "."})
    overview_response = client.post("/codebase/overview", json={"repository_path": "."})
    search_response = client.post(
        "/codebase/search",
        json={"repository_path": ".", "query": "AgentRuntime", "limit": 5},
    )
    ask_response = client.post(
        "/codebase/ask",
        json={"repository_path": ".", "question": "AgentRuntime 的主流程是什么？"},
    )

    assert summary_response.status_code == 200
    assert summary_response.json()["analyzed_files"] > 0
    assert overview_response.status_code == 200
    assert "仓库理解报告" in overview_response.json()["report"]
    assert "这个项目是做什么的" in overview_response.json()["report"]
    assert search_response.status_code == 200
    assert search_response.json()
    assert ask_response.status_code == 200
    assert ask_response.json()["evidence"]


def test_openapi_contains_codebase_paths() -> None:
    """OpenAPI schema should expose enterprise codebase endpoints."""

    client = TestClient(create_app())

    response = client.get("/openapi.json")
    schema = response.json()

    assert response.status_code == 200
    assert "/codebase/summary" in schema["paths"]
    assert "/codebase/overview" in schema["paths"]
    assert "/codebase/ask" in schema["paths"]
    assert "/codebase/impact" in schema["paths"]
    assert "/codebase/review-diff" in schema["paths"]
