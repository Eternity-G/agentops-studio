"""Offline evaluation runner.

第 16 步建立最小评测体系。它不调用真实大模型 API，只评测当前项目已经稳定的
本地链路：Agent 主链路、Markdown 文档问答和内存会话记忆。
"""

from __future__ import annotations

import asyncio
from enum import StrEnum

from pydantic import Field

from app.agent import AgentRuntime
from app.codebase.qa import CodebaseQuestionAnswerer
from app.document_qa import MarkdownQuestionAnswerer
from app.memory import InMemorySessionStore
from app.planner import Planner
from app.providers import MockProvider
from app.schemas import DocumentQuestionInput, MemoryNoteInput, ShortText, StrictSchema


class EvalCaseType(StrEnum):
    """Supported offline evaluation case types."""

    TASK_RUN = "task_run"
    DOCUMENT_QA = "document_qa"
    SESSION_MEMORY = "session_memory"
    CODEBASE_QA = "codebase_qa"


class EvalCase(StrictSchema):
    """One deterministic evaluation case."""

    case_id: ShortText = Field(description="Stable case id.")
    case_type: EvalCaseType = Field(description="Evaluation case type.")
    description: ShortText = Field(description="Human-readable case description.")
    input: dict[str, object] = Field(description="Case input payload.")
    expected_contains: list[ShortText] = Field(
        default_factory=list,
        description="Substrings that must appear in the observable output.",
        max_length=10,
    )


class EvalResult(StrictSchema):
    """Result of running one evaluation case."""

    case_id: ShortText
    case_type: EvalCaseType
    passed: bool
    output: str
    missing: list[ShortText] = Field(default_factory=list, max_length=10)


class EvalReport(StrictSchema):
    """Aggregated evaluation report."""

    total: int
    passed: int
    failed: int
    results: list[EvalResult]

    @property
    def pass_rate(self) -> float:
        """Return pass rate from 0.0 to 1.0."""

        if self.total == 0:
            return 0.0
        return self.passed / self.total

    def to_markdown(self) -> str:
        """Render the report as Markdown for local review and GitHub."""

        lines = [
            "# AgentOps Studio 自动评测报告",
            "",
            f"- 总用例数：{self.total}",
            f"- 通过：{self.passed}",
            f"- 失败：{self.failed}",
            f"- 通过率：{self.pass_rate:.0%}",
            "",
            "| 用例 | 类型 | 结果 | 缺失内容 |",
            "|---|---|---|---|",
        ]
        for result in self.results:
            status = "通过" if result.passed else "失败"
            missing = "、".join(result.missing) if result.missing else "-"
            lines.append(f"| {result.case_id} | {result.case_type.value} | {status} | {missing} |")
        lines.append("")
        return "\n".join(lines)


class EvaluationRunner:
    """Run deterministic offline evaluation cases."""

    def __init__(
        self,
        *,
        agent_runtime: AgentRuntime | None = None,
        document_answerer: MarkdownQuestionAnswerer | None = None,
        codebase_answerer: CodebaseQuestionAnswerer | None = None,
        memory_store: InMemorySessionStore | None = None,
    ) -> None:
        self._agent_runtime = agent_runtime or AgentRuntime(
            planner=Planner(
                provider=MockProvider(),
                fallback_provider=MockProvider(model="eval-fallback-mock"),
            )
        )
        self._document_answerer = document_answerer or MarkdownQuestionAnswerer()
        self._codebase_answerer = codebase_answerer or CodebaseQuestionAnswerer()
        self._memory_store = memory_store or InMemorySessionStore()

    async def run(self, cases: list[EvalCase]) -> EvalReport:
        """Run all cases and return an aggregated report."""

        results = [await self._run_case(case) for case in cases]
        passed = sum(1 for result in results if result.passed)
        return EvalReport(
            total=len(results),
            passed=passed,
            failed=len(results) - passed,
            results=results,
        )

    def run_sync(self, cases: list[EvalCase]) -> EvalReport:
        """Synchronous wrapper for scripts and simple CLI usage."""

        return asyncio.run(self.run(cases))

    async def _run_case(self, case: EvalCase) -> EvalResult:
        """Run one evaluation case."""

        case_error = False
        try:
            if case.case_type == EvalCaseType.TASK_RUN:
                output = await self._run_task_case(case)
            elif case.case_type == EvalCaseType.DOCUMENT_QA:
                output = self._run_document_case(case)
            elif case.case_type == EvalCaseType.SESSION_MEMORY:
                output = self._run_memory_case(case)
            elif case.case_type == EvalCaseType.CODEBASE_QA:
                output = self._run_codebase_case(case)
            else:  # pragma: no cover - StrEnum validation prevents this branch.
                output = f"unsupported case type: {case.case_type}"
        except Exception as exc:
            case_error = True
            output = f"evaluation case failed: {exc}"

        missing = [text for text in case.expected_contains if text not in output]
        if case_error and not missing:
            missing = ["case completed without exception"]
        return EvalResult(
            case_id=case.case_id,
            case_type=case.case_type,
            passed=not missing,
            output=output,
            missing=missing,
        )

    async def _run_task_case(self, case: EvalCase) -> str:
        """Run an Agent task case and return observable text."""

        task = self._require_text(case, "task")
        state = await self._agent_runtime.run_from_text(task)
        final_summary = state.final_answer.summary if state.final_answer else ""
        return "\n".join(
            [
                state.status.value,
                state.task_input.task,
                final_summary,
                "\n".join(event.message for event in state.trace_events),
            ]
        )

    def _run_document_case(self, case: EvalCase) -> str:
        """Run a Markdown document QA case and return observable text."""

        question = self._require_text(case, "question")
        path = self._require_text(case, "path")
        answer = self._document_answerer.answer(DocumentQuestionInput(question=question, path=path))
        return "\n".join(
            [
                str(answer.completed).lower(),
                answer.source_path,
                answer.answer,
                answer.excerpt or "",
            ]
        )

    def _run_memory_case(self, case: EvalCase) -> str:
        """Run a session memory case and return observable text."""

        session_id = self._require_text(case, "session_id")
        content = self._require_text(case, "content")
        session = self._memory_store.record_note(
            session_id=session_id,
            note=MemoryNoteInput(content=content),
        )
        return "\n".join(
            [
                session.session_id,
                str(len(session.events)),
                "\n".join(event.event_type.value for event in session.events),
                "\n".join(event.summary for event in session.events),
            ]
        )

    def _run_codebase_case(self, case: EvalCase) -> str:
        """Run a codebase question-answer case and return observable text."""

        question = self._require_text(case, "question")
        repository_path = self._require_text(case, "repository_path")
        answer = self._codebase_answerer.answer(repository_path, question)
        evidence_text = "\n".join(
            f"{item.file_path}:{item.line_start}-{item.line_end}\n{item.quote}"
            for item in answer.evidence
        )
        return "\n".join(
            [
                str(answer.completed).lower(),
                answer.repository_path,
                answer.answer,
                evidence_text,
            ]
        )

    def _require_text(self, case: EvalCase, key: str) -> str:
        """Read a required string field from a case input."""

        value = case.input.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"eval case {case.case_id} requires text input: {key}")
        return value
