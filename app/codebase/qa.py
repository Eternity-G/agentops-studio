"""Codebase question answering and impact analysis."""

from __future__ import annotations

import re
from pathlib import Path

from app.codebase.reader import CodeFileReader
from app.codebase.scanner import RepositoryScanner
from app.codebase.search import CodeSearcher
from app.codebase.security import RepositorySecurity
from app.codebase.symbols import PythonSymbolAnalyzer
from app.schemas import (
    CodeEvidence,
    CodeImpactReport,
    CodebaseAnswer,
    CodebaseSummary,
    CodeSearchMatch,
    PythonSymbol,
)


class CodebaseQuestionAnswerer:
    """Answer developer questions from repository evidence."""

    def __init__(
        self,
        *,
        security: RepositorySecurity | None = None,
        scanner: RepositoryScanner | None = None,
        searcher: CodeSearcher | None = None,
        reader: CodeFileReader | None = None,
        symbol_analyzer: PythonSymbolAnalyzer | None = None,
    ) -> None:
        self._security = security or RepositorySecurity()
        self._scanner = scanner or RepositoryScanner(self._security)
        self._searcher = searcher or CodeSearcher(self._security)
        self._reader = reader or CodeFileReader(self._security)
        self._symbol_analyzer = symbol_analyzer or PythonSymbolAnalyzer(self._security)

    def answer(self, repository_path: str, question: str) -> CodebaseAnswer:
        """Answer a question with repository-grounded evidence."""

        repository_root = self._security.resolve_repository(repository_path)
        terms = self._extract_search_terms(question)
        summary = self._scanner.summarize(repository_root.as_posix())
        matches = self._search_terms(repository_root, terms)
        evidence = self._evidence_from_matches(repository_root, matches)

        if not evidence:
            evidence = self._fallback_evidence(repository_root, summary)

        answer = self._compose_answer(question=question, summary=summary, evidence=evidence)
        risk_notes = self._risk_notes(question, evidence)

        return CodebaseAnswer(
            question=question,
            answer=answer,
            completed=bool(evidence),
            repository_path=repository_root.as_posix(),
            evidence=evidence[:10],
            searched_terms=terms[:10],
            risk_notes=risk_notes,
        )

    def impact(self, repository_path: str, target_path: str) -> CodeImpactReport:
        """Analyze file-level impact by searching references to the target."""

        repository_root = self._security.resolve_repository(repository_path)
        target = self._security.resolve_file(repository_root, target_path)
        relative_target = target.relative_to(repository_root).as_posix()
        module_like = self._module_like_terms(relative_target)

        matches: list[CodeSearchMatch] = []
        for term in module_like:
            matches.extend(self._searcher.search(repository_root.as_posix(), term, limit=20))

        referenced_by = [
            self._reader.read_lines(repository_root, match.file_path, line_number=match.line_number, context=2)
            for match in matches
            if match.file_path != relative_target
        ][:20]

        impacted_areas = sorted({evidence.file_path.split("/", 1)[0] for evidence in referenced_by})
        test_suggestions = self._test_suggestions(relative_target, impacted_areas)

        return CodeImpactReport(
            target_path=relative_target,
            referenced_by=referenced_by,
            likely_impacted_areas=impacted_areas,
            test_suggestions=test_suggestions,
        )

    def symbols(self, repository_path: str) -> list[PythonSymbol]:
        """Return Python symbols extracted from the repository."""

        return self._symbol_analyzer.analyze_repository(repository_path)

    def _extract_search_terms(self, question: str) -> list[str]:
        """Extract search terms for code questions."""

        code_terms = re.findall(r"[A-Za-z_][A-Za-z0-9_./-]{2,}", question)
        chinese_terms = re.findall(r"[\u4e00-\u9fff]{2,}", question)
        terms = [term.strip("`'\"") for term in code_terms + chinese_terms]

        normalized: list[str] = []
        for term in terms:
            if term.lower() in {"where", "what", "how", "why", "the", "and", "with"}:
                continue
            if term not in normalized:
                normalized.append(term)
        return normalized[:8] or [question[:80]]

    def _search_terms(self, repository_root: Path, terms: list[str]) -> list[CodeSearchMatch]:
        """Search several terms and merge matches."""

        matches: list[CodeSearchMatch] = []
        seen: set[tuple[str, int]] = set()
        for term in terms:
            for match in self._searcher.search(repository_root.as_posix(), term, limit=12):
                key = (match.file_path, match.line_number)
                if key not in seen:
                    seen.add(key)
                    matches.append(match)
        return matches[:20]

    def _evidence_from_matches(
        self,
        repository_root: Path,
        matches: list[CodeSearchMatch],
    ) -> list[CodeEvidence]:
        """Convert search matches to evidence windows."""

        evidence: list[CodeEvidence] = []
        for match in matches:
            try:
                evidence.append(
                    self._reader.read_lines(
                        repository_root,
                        match.file_path,
                        line_number=match.line_number,
                        context=4,
                    )
                )
            except Exception:
                continue
        return evidence

    def _fallback_evidence(self, repository_root: Path, summary: CodebaseSummary) -> list[CodeEvidence]:
        """Fallback to key files when keyword search has no match."""

        evidence: list[CodeEvidence] = []
        for file_path in summary.key_files[:5]:
            try:
                evidence.append(self._reader.read(repository_root.as_posix(), file_path))
            except Exception:
                continue
        return evidence

    def _compose_answer(
        self,
        *,
        question: str,
        summary: CodebaseSummary,
        evidence: list[CodeEvidence],
    ) -> str:
        """Compose a deterministic enterprise-style answer."""

        if not evidence:
            return f"没有在仓库中找到足够证据回答：{question}"

        evidence_lines = [
            f"- {item.file_path}:{item.line_start}-{item.line_end}"
            for item in evidence[:5]
        ]
        language_text = "、".join(f"{name}({count})" for name, count in summary.languages.items())
        return (
            f"这个问题应基于仓库证据回答，而不是凭空推断。\n"
            f"仓库概况：分析文件 {summary.analyzed_files} 个，代码行约 {summary.total_lines} 行，"
            f"主要语言为 {language_text or '未知'}。\n"
            f"针对问题“{question}”，最相关的证据位置是：\n"
            + "\n".join(evidence_lines)
            + "\n建议先阅读这些文件片段，再决定是否修改代码或补测试。"
        )

    def _risk_notes(self, question: str, evidence: list[CodeEvidence]) -> list[str]:
        """Return lightweight risk notes for developer questions."""

        notes = ["回答基于静态扫描和关键词证据，复杂调用链仍需结合运行时测试确认。"]
        if any("schema" in item.file_path.lower() for item in evidence):
            notes.append("命中 schema 文件，修改时需要同步检查 API 响应、测试和前端字段。")
        if any("route" in item.file_path.lower() or "api" in item.file_path.lower() for item in evidence):
            notes.append("命中 API/路由相关文件，修改时需要检查 OpenAPI 和接口回归测试。")
        if "生成代码" in question or "修改代码" in question:
            notes.append("当前系统只生成修改建议，不自动写入代码，避免未经审批的变更。")
        return notes[:10]

    def _module_like_terms(self, relative_target: str) -> list[str]:
        """Build search terms from a repository-relative file path."""

        stem_path = relative_target.rsplit(".", 1)[0]
        module_dot = stem_path.replace("/", ".")
        basename = Path(relative_target).stem
        return list(dict.fromkeys([relative_target, stem_path, module_dot, basename]))

    def _test_suggestions(self, target_path: str, impacted_areas: list[str]) -> list[str]:
        """Return practical test suggestions for impacted files."""

        suggestions = ["运行完整测试：python -m pytest"]
        if target_path.endswith(".py"):
            suggestions.append("补充或运行目标模块附近的 pytest 回归测试。")
        if any(area in {"app", "api", "server", "backend"} for area in impacted_areas):
            suggestions.append("检查 API 行为和 OpenAPI 文档是否变化。")
        if any(area in {"web", "frontend", "src", "components", "pages"} for area in impacted_areas):
            suggestions.append("检查前端页面和接口字段兼容性。")
        return suggestions[:10]
