"""Python symbol extraction with the standard ast module."""

from __future__ import annotations

import ast
from pathlib import Path

from app.codebase.security import RepositorySecurity
from app.schemas import PythonSymbol


class PythonSymbolAnalyzer:
    """Extract Python classes, functions, methods, and imports."""

    def __init__(self, security: RepositorySecurity | None = None) -> None:
        self._security = security or RepositorySecurity()

    def analyze_repository(self, repository_path: str) -> list[PythonSymbol]:
        """Analyze all Python files in a repository."""

        repository_root = self._security.resolve_repository(repository_path)
        symbols: list[PythonSymbol] = []

        for path in sorted(repository_root.rglob("*.py")):
            if any(self._security.is_ignored_dir(parent) for parent in path.parents):
                continue
            symbols.extend(self.analyze_file(repository_root, path.relative_to(repository_root).as_posix()))

        return symbols

    def analyze_file(self, repository_root: Path, file_path: str) -> list[PythonSymbol]:
        """Analyze one Python file."""

        resolved = self._security.resolve_file(repository_root, file_path)
        if resolved.suffix.lower() != ".py":
            raise ValueError("Python symbol analysis only supports .py files")

        source = resolved.read_text(encoding="utf-8", errors="ignore")
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []

        relative_path = resolved.relative_to(repository_root).as_posix()
        symbols: list[PythonSymbol] = []

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                symbols.append(
                    PythonSymbol(
                        name=node.name,
                        symbol_type="class",
                        file_path=relative_path,
                        line_number=node.lineno,
                    )
                )
                symbols.extend(self._methods_from_class(node, relative_path))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                symbols.append(
                    PythonSymbol(
                        name=node.name,
                        symbol_type="function",
                        file_path=relative_path,
                        line_number=node.lineno,
                    )
                )
            elif isinstance(node, ast.Import):
                symbols.extend(self._imports_from_node(node, relative_path))
            elif isinstance(node, ast.ImportFrom):
                symbols.extend(self._imports_from_node(node, relative_path))

        return symbols

    def _methods_from_class(self, node: ast.ClassDef, file_path: str) -> list[PythonSymbol]:
        """Extract methods from a class node."""

        methods: list[PythonSymbol] = []
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(
                    PythonSymbol(
                        name=child.name,
                        symbol_type="method",
                        file_path=file_path,
                        line_number=child.lineno,
                        parent=node.name,
                    )
                )
        return methods

    def _imports_from_node(self, node: ast.AST, file_path: str) -> list[PythonSymbol]:
        """Extract import symbols."""

        imports: list[PythonSymbol] = []
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(
                    PythonSymbol(
                        name=alias.name,
                        symbol_type="import",
                        file_path=file_path,
                        line_number=node.lineno,
                    )
                )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                name = f"{module}.{alias.name}" if module else alias.name
                imports.append(
                    PythonSymbol(
                        name=name,
                        symbol_type="import",
                        file_path=file_path,
                        line_number=node.lineno,
                    )
                )
        return imports
