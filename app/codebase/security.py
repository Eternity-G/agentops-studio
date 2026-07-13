"""Security helpers for local repository analysis."""

from __future__ import annotations

from pathlib import Path


DEFAULT_ALLOWED_SUFFIXES = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".html",
    ".css",
    ".scss",
    ".json",
    ".toml",
    ".yaml",
    ".yml",
    ".md",
    ".sql",
    ".go",
    ".java",
    ".kt",
    ".rs",
    ".cs",
    ".php",
}

DEFAULT_IGNORED_DIRS = {
    ".git",
    ".agents",
    ".claude",
    ".cursor",
    ".deepsec",
    ".devcontainer",
    ".github",
    ".husky",
    ".idea",
    ".source",
    ".vscode",
    ".windsurf",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    "node_modules",
    ".next",
    "dist",
    "build",
    "coverage",
    "external-repos",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "target",
}

SENSITIVE_FILE_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    "id_rsa",
    "id_ed25519",
}


class RepositorySecurity:
    """Resolve and validate repository paths."""

    def __init__(self, workspace_root: Path | str | None = None) -> None:
        self.workspace_root = Path(workspace_root or ".").resolve()

    def resolve_repository(self, repository_path: str) -> Path:
        """Resolve a repository path and ensure it stays inside workspace root."""

        raw_path = Path(repository_path.strip() or ".")
        candidate = raw_path if raw_path.is_absolute() else self.workspace_root / raw_path
        resolved = candidate.resolve()
        self.ensure_inside_workspace(resolved)
        if not resolved.is_dir():
            raise ValueError(f"repository path is not a directory: {repository_path}")
        return resolved

    def resolve_file(self, repository_root: Path, file_path: str) -> Path:
        """Resolve a repository-relative file path safely."""

        raw_path = Path(file_path.strip())
        if raw_path.is_absolute():
            raise ValueError("file path must be repository-relative")

        resolved = (repository_root / raw_path).resolve()
        self.ensure_inside_workspace(resolved)
        if repository_root not in [resolved, *resolved.parents]:
            raise ValueError("file path must stay inside the repository root")
        if self.is_sensitive_file(resolved):
            raise ValueError("sensitive files are not readable")
        if resolved.suffix.lower() not in DEFAULT_ALLOWED_SUFFIXES:
            raise ValueError(f"unsupported file type: {resolved.suffix}")
        if not resolved.is_file():
            raise FileNotFoundError(f"file not found: {file_path}")
        return resolved

    def ensure_inside_workspace(self, path: Path) -> None:
        """Reject paths outside the configured workspace root."""

        if self.workspace_root not in [path, *path.parents]:
            raise ValueError("path must stay inside the configured workspace root")

    def is_ignored_dir(self, path: Path) -> bool:
        """Return whether a directory should be ignored while scanning."""

        return path.name in DEFAULT_IGNORED_DIRS

    @property
    def ignored_dir_names(self) -> set[str]:
        """Return ignored directory names for repository-relative checks."""

        return set(DEFAULT_IGNORED_DIRS)

    def is_supported_file(self, path: Path) -> bool:
        """Return whether a file can be read for code analysis."""

        return (
            path.is_file()
            and path.suffix.lower() in DEFAULT_ALLOWED_SUFFIXES
            and not self.is_sensitive_file(path)
        )

    def is_sensitive_file(self, path: Path) -> bool:
        """Return whether a file name is sensitive."""

        return path.name in SENSITIVE_FILE_NAMES or path.name.startswith(".env.")
