"""Safe code file reader."""

from __future__ import annotations

from pathlib import Path

from app.codebase.security import RepositorySecurity
from app.schemas import CodeEvidence


class CodeFileReader:
    """Read repository files with path and size constraints."""

    def __init__(self, security: RepositorySecurity | None = None, max_chars: int = 3500) -> None:
        if max_chars <= 0:
            raise ValueError("max_chars must be positive")
        self._security = security or RepositorySecurity()
        self._max_chars = max_chars

    def read(self, repository_path: str, file_path: str) -> CodeEvidence:
        """Read one file and return it as code evidence."""

        repository_root = self._security.resolve_repository(repository_path)
        resolved = self._security.resolve_file(repository_root, file_path)
        content = resolved.read_text(encoding="utf-8", errors="ignore")
        visible_content = content[: self._max_chars]
        line_count = max(1, len(visible_content.splitlines()))

        return CodeEvidence(
            file_path=resolved.relative_to(repository_root).as_posix(),
            line_start=1,
            line_end=line_count,
            quote=visible_content,
        )

    def read_lines(
        self,
        repository_root: Path,
        file_path: str,
        *,
        line_number: int,
        context: int = 3,
    ) -> CodeEvidence:
        """Read a small line window around a match."""

        resolved = self._security.resolve_file(repository_root, file_path)
        lines = resolved.read_text(encoding="utf-8", errors="ignore").splitlines()
        start = max(1, line_number - context)
        end = min(len(lines), line_number + context)
        quote = "\n".join(lines[start - 1 : end])

        return CodeEvidence(
            file_path=resolved.relative_to(repository_root).as_posix(),
            line_start=start,
            line_end=max(start, end),
            quote=quote[: self._max_chars],
        )
