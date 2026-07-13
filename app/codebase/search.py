"""Keyword search for local code repositories."""

from __future__ import annotations

from pathlib import Path

from app.codebase.security import RepositorySecurity
from app.schemas import CodeSearchMatch


class CodeSearcher:
    """Search supported text files with deterministic limits."""

    def __init__(self, security: RepositorySecurity | None = None, max_file_chars: int = 200_000) -> None:
        self._security = security or RepositorySecurity()
        self._max_file_chars = max_file_chars

    def search(self, repository_path: str, query: str, limit: int = 20) -> list[CodeSearchMatch]:
        """Search a keyword in repository files."""

        normalized_query = query.strip().lower()
        if not normalized_query:
            raise ValueError("search query cannot be empty")

        repository_root = self._security.resolve_repository(repository_path)
        matches: list[CodeSearchMatch] = []

        for path in self._iter_supported_files(repository_root):
            if len(matches) >= limit:
                break

            text = path.read_text(encoding="utf-8", errors="ignore")[: self._max_file_chars]
            for index, line in enumerate(text.splitlines(), start=1):
                if normalized_query in line.lower():
                    relative_path = path.relative_to(repository_root).as_posix()
                    matches.append(
                        CodeSearchMatch(
                            file_path=relative_path,
                            line_number=index,
                            line=line.strip()[:200],
                        )
                    )
                    if len(matches) >= limit:
                        break

        return matches

    def _iter_supported_files(self, repository_root: Path) -> list[Path]:
        """Return searchable files while skipping ignored directories."""

        files: list[Path] = []
        for path in repository_root.rglob("*"):
            if self._has_ignored_relative_part(repository_root, path):
                continue
            if self._security.is_supported_file(path):
                files.append(path)
        return sorted(
            files,
            key=lambda item: self._file_priority(item.relative_to(repository_root).as_posix()),
        )

    def _file_priority(self, relative_path: str) -> tuple[int, str]:
        """Prioritize product source files before docs and configuration."""

        if relative_path.startswith(("apps/", "libs/", "packages/", "enterprise/")):
            source_rank = 0
        elif relative_path.startswith(("src/", "backend/", "frontend/", "server/")):
            source_rank = 1
        elif relative_path.endswith(".md") or relative_path.startswith("docs/"):
            source_rank = 3
        else:
            source_rank = 2

        suffix_rank = 1 if relative_path.endswith((".md", ".json", ".yaml", ".yml", ".toml")) else 0
        return (source_rank, suffix_rank, relative_path)

    def _has_ignored_relative_part(self, repository_root: Path, path: Path) -> bool:
        """Return whether a path contains ignored directories inside the repository."""

        relative_parts = path.relative_to(repository_root).parts[:-1]
        return any(part in self._security.ignored_dir_names for part in relative_parts)
