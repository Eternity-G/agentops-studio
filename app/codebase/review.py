"""Git diff review helper for codebase Agent."""

from __future__ import annotations

import subprocess
from pathlib import Path

from app.codebase.reader import CodeFileReader
from app.codebase.security import RepositorySecurity
from app.schemas import CodeEvidence, DiffReviewReport


class DiffReviewer:
    """Review current git diff with static heuristics."""

    def __init__(
        self,
        *,
        security: RepositorySecurity | None = None,
        reader: CodeFileReader | None = None,
    ) -> None:
        self._security = security or RepositorySecurity()
        self._reader = reader or CodeFileReader(self._security)

    def review(self, repository_path: str = ".") -> DiffReviewReport:
        """Return a review report for uncommitted git diff."""

        repository_root = self._security.resolve_repository(repository_path)
        changed_files = self._changed_files(repository_root)
        evidence = self._evidence_for_files(repository_root, changed_files)
        risk_notes = self._risk_notes(changed_files)
        test_suggestions = self._test_suggestions(changed_files)

        summary = (
            f"当前工作区包含 {len(changed_files)} 个变更文件。"
            if changed_files
            else "当前工作区没有检测到未提交代码变更。"
        )
        return DiffReviewReport(
            changed_files=changed_files,
            summary=summary,
            risk_notes=risk_notes,
            test_suggestions=test_suggestions,
            evidence=evidence,
        )

    def _changed_files(self, repository_root: Path) -> list[str]:
        """Read changed files from git diff."""

        result = subprocess.run(
            ["git", "diff", "--name-only"],
            cwd=repository_root,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            return []
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]

    def _evidence_for_files(self, repository_root: Path, changed_files: list[str]) -> list[CodeEvidence]:
        """Read small evidence snippets for changed files."""

        evidence: list[CodeEvidence] = []
        for file_path in changed_files[:10]:
            try:
                evidence.append(self._reader.read(repository_root.as_posix(), file_path))
            except Exception:
                continue
        return evidence

    def _risk_notes(self, changed_files: list[str]) -> list[str]:
        """Generate static risk notes."""

        notes: list[str] = []
        if any(path.endswith(".py") for path in changed_files):
            notes.append("包含 Python 代码变更，需要运行 pytest 并关注类型/schema 兼容性。")
        if any(path.endswith((".ts", ".tsx", ".js", ".jsx")) for path in changed_files):
            notes.append("包含前端或 TypeScript/JavaScript 变更，需要检查浏览器交互和接口字段。")
        if any("schema" in path.lower() for path in changed_files):
            notes.append("包含 schema 变更，需要检查 API 响应、评测和前端解析。")
        if any(path in {"Dockerfile", "pyproject.toml", "package.json"} for path in changed_files):
            notes.append("包含构建或依赖配置变更，需要检查部署流程。")
        return notes or ["未发现明显高风险文件类型，但仍建议运行测试和评测。"]

    def _test_suggestions(self, changed_files: list[str]) -> list[str]:
        """Generate test suggestions for changed files."""

        suggestions = ["python -m pytest", "python scripts/run_evals.py"]
        if any(path.startswith("app/web/") for path in changed_files):
            suggestions.append("python -m pytest tests/test_web.py")
        if any(path.startswith("app/codebase/") for path in changed_files):
            suggestions.append("python -m pytest tests/test_codebase.py")
        return list(dict.fromkeys(suggestions))
