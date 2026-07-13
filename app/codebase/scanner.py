"""Repository scanner for codebase understanding."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from app.codebase.security import RepositorySecurity
from app.schemas import CodebaseSummary


LANGUAGE_BY_SUFFIX = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "CSS",
    ".json": "JSON",
    ".toml": "TOML",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".md": "Markdown",
    ".sql": "SQL",
    ".go": "Go",
    ".java": "Java",
    ".kt": "Kotlin",
    ".rs": "Rust",
    ".cs": "C#",
    ".php": "PHP",
}

KEY_FILE_NAMES = {
    "README.md",
    "pyproject.toml",
    "package.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "requirements.txt",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "next.config.js",
    "vite.config.ts",
    "app.py",
    "main.py",
}

FRONTEND_SIGNALS = {
    "package.json",
    "next.config.js",
    "next.config.mjs",
    "vite.config.ts",
    "vite.config.js",
    "src",
    "pages",
    "components",
    "app",
    "web",
    "frontend",
    "dashboard",
}

BACKEND_SIGNALS = {
    "pyproject.toml",
    "requirements.txt",
    "app.py",
    "main.py",
    "manage.py",
    "Dockerfile",
    "api",
    "server",
    "backend",
    "routes",
    "apps",
    "worker",
    "workers",
    "services",
}


class RepositoryScanner:
    """Scan local repositories with bounded cost."""

    def __init__(self, security: RepositorySecurity | None = None, max_files: int = 5000) -> None:
        self._security = security or RepositorySecurity()
        self._max_files = max_files

    def summarize(self, repository_path: str = ".") -> CodebaseSummary:
        """Return a high-level repository summary."""

        repository_root = self._security.resolve_repository(repository_path)
        analyzed_files = 0
        total_files = 0
        total_lines = 0
        language_counts: Counter[str] = Counter()
        key_files: list[str] = []

        for path in self._iter_files(repository_root):
            total_files += 1
            if not self._security.is_supported_file(path):
                continue
            analyzed_files += 1
            if analyzed_files > self._max_files:
                break

            relative_path = path.relative_to(repository_root).as_posix()
            language = LANGUAGE_BY_SUFFIX.get(path.suffix.lower(), "Other")
            language_counts[language] += 1
            if path.name in KEY_FILE_NAMES:
                key_files.append(relative_path)
            total_lines += self._count_lines(path)

        top_level_directories = [
            path.name
            for path in sorted(repository_root.iterdir(), key=lambda item: item.name.lower())
            if path.is_dir() and not self._security.is_ignored_dir(path)
        ][:50]

        names = {path.name for path in repository_root.iterdir()}
        names.update(top_level_directories)
        for directory in top_level_directories[:20]:
            child = repository_root / directory
            if child.is_dir():
                names.update(path.name for path in child.iterdir() if path.is_dir() or path.is_file())

        return CodebaseSummary(
            repository_path=repository_root.as_posix(),
            total_files=total_files,
            analyzed_files=analyzed_files,
            total_lines=total_lines,
            top_level_directories=top_level_directories,
            key_files=key_files[:50],
            languages=dict(language_counts.most_common()),
            frontend_signals=sorted(names & FRONTEND_SIGNALS),
            backend_signals=sorted(names & BACKEND_SIGNALS),
        )

    def _iter_files(self, repository_root: Path) -> list[Path]:
        """Return repository files while skipping ignored directories."""

        files: list[Path] = []
        for path in repository_root.rglob("*"):
            if self._has_ignored_relative_part(repository_root, path):
                continue
            if path.is_file():
                files.append(path)
        return files

    def _has_ignored_relative_part(self, repository_root: Path, path: Path) -> bool:
        """Return whether a path contains ignored directories inside the repository."""

        relative_parts = path.relative_to(repository_root).parts[:-1]
        return any(part in self._security.ignored_dir_names for part in relative_parts)

    def _count_lines(self, path: Path) -> int:
        """Count lines with defensive encoding handling."""

        try:
            return len(path.read_text(encoding="utf-8", errors="ignore").splitlines())
        except OSError:
            return 0
