"""FastAPI application routes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.agent import AgentRuntime, AgentState
from app.codebase.overview import CodebaseOverviewer
from app.codebase.qa import CodebaseQuestionAnswerer
from app.codebase.review import DiffReviewer
from app.codebase.scanner import RepositoryScanner
from app.codebase.search import CodeSearcher
from app.codebase.symbols import PythonSymbolAnalyzer
from app.document_qa import MarkdownQuestionAnswerer
from app.memory import InMemorySessionStore
from app.schemas import (
    CodeImpactInput,
    CodeImpactReport,
    CodeSearchInput,
    CodeSearchMatch,
    CodebaseAnswer,
    CodebaseInput,
    CodebaseOverview,
    CodebaseQuestionInput,
    CodebaseSummary,
    DocumentQuestionAnswer,
    DocumentQuestionInput,
    DiffReviewReport,
    MemoryEventType,
    MemoryNoteInput,
    PythonSymbol,
    SessionState,
    TaskInput,
)
from app.settings import load_settings


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    settings = load_settings()
    app_dir = Path(__file__).resolve().parents[1]
    project_root = app_dir.parent
    web_dir = app_dir / "web"
    eval_report_path = project_root / "evals" / "latest-report.md"
    application = FastAPI(
        title=settings.app_name,
        version=__version__,
        debug=settings.debug,
    )
    memory_store = InMemorySessionStore()
    application.mount("/static", StaticFiles(directory=web_dir), name="static")

    def page_response(file_name: str) -> FileResponse:
        """Return one browser page without HTTP cache."""

        return FileResponse(web_dir / file_name, headers={"Cache-Control": "no-store"})

    @application.get("/", tags=["web"])
    def web_index() -> FileResponse:
        """Return the browser home page."""

        return page_response("index.html")

    @application.get("/overview", tags=["web"])
    def web_overview() -> FileResponse:
        """Return the repository overview page."""

        return page_response("overview.html")

    @application.get("/ask", tags=["web"])
    def web_ask() -> FileResponse:
        """Return the codebase Q&A page."""

        return page_response("ask.html")

    @application.get("/impact", tags=["web"])
    def web_impact() -> FileResponse:
        """Return the impact analysis page."""

        return page_response("impact.html")

    @application.get("/review", tags=["web"])
    def web_review() -> FileResponse:
        """Return the diff review page."""

        return page_response("review.html")

    @application.get("/eval", tags=["web"])
    def web_eval() -> FileResponse:
        """Return the evaluation report page."""

        return page_response("eval.html")

    @application.get("/health", tags=["system"])
    def health_check() -> dict[str, Any]:
        """Return a lightweight health status for monitoring and tests."""

        current_settings = load_settings()
        return {
            "status": "ok",
            "app_name": current_settings.app_name,
            "environment": current_settings.app_env,
            "version": __version__,
        }

    @application.post("/tasks/run", response_model=AgentState, tags=["tasks"])
    async def run_task(task_input: TaskInput) -> AgentState:
        """Run the minimal Agent flow and return state with trace events."""

        runtime = AgentRuntime()
        state = await runtime.run(task_input)
        session_id = task_input.metadata.get("session_id")
        if session_id:
            memory_store.record_task_run(session_id=session_id, state=state)
        return state

    @application.post("/documents/ask", response_model=DocumentQuestionAnswer, tags=["documents"])
    def ask_document(question_input: DocumentQuestionInput) -> DocumentQuestionAnswer:
        """Answer a question from one local Markdown document."""

        answerer = MarkdownQuestionAnswerer()
        answer = answerer.answer(question_input)
        if question_input.session_id:
            memory_store.record_document_answer(session_id=question_input.session_id, answer=answer)
        return answer

    @application.get("/sessions/{session_id}", response_model=SessionState, tags=["sessions"])
    def get_session(session_id: str) -> SessionState:
        """Return the in-memory state for one session."""

        return memory_store.get_session(session_id)

    @application.post("/sessions/{session_id}/notes", response_model=SessionState, tags=["sessions"])
    def append_session_note(session_id: str, note: MemoryNoteInput) -> SessionState:
        """Append a manual note to one in-memory session."""

        return memory_store.record_note(session_id=session_id, note=note)

    @application.get("/evals/latest-report", tags=["evals"])
    def latest_eval_report() -> PlainTextResponse:
        """Return the latest offline evaluation report."""

        if not eval_report_path.exists():
            return PlainTextResponse("评测报告不存在，请先运行 python scripts/run_evals.py。", status_code=404)
        return PlainTextResponse(eval_report_path.read_text(encoding="utf-8"))

    @application.post("/codebase/summary", response_model=CodebaseSummary, tags=["codebase"])
    def codebase_summary(codebase_input: CodebaseInput) -> CodebaseSummary:
        """Summarize a local code repository."""

        return RepositoryScanner().summarize(codebase_input.repository_path)

    @application.post("/codebase/overview", response_model=CodebaseOverview, tags=["codebase"])
    def codebase_overview(codebase_input: CodebaseInput) -> CodebaseOverview:
        """Build a user-facing overview report for a local code repository."""

        return CodebaseOverviewer().build(codebase_input.repository_path)

    @application.post("/codebase/search", response_model=list[CodeSearchMatch], tags=["codebase"])
    def codebase_search(search_input: CodeSearchInput) -> list[CodeSearchMatch]:
        """Search source code by keyword."""

        return CodeSearcher().search(
            search_input.repository_path,
            search_input.query,
            limit=search_input.limit,
        )

    @application.post("/codebase/symbols", response_model=list[PythonSymbol], tags=["codebase"])
    def codebase_symbols(codebase_input: CodebaseInput) -> list[PythonSymbol]:
        """Extract Python symbols from a repository."""

        return PythonSymbolAnalyzer().analyze_repository(codebase_input.repository_path)

    @application.post("/codebase/ask", response_model=CodebaseAnswer, tags=["codebase"])
    def codebase_ask(question_input: CodebaseQuestionInput) -> CodebaseAnswer:
        """Answer developer questions from code repository evidence."""

        answerer = CodebaseQuestionAnswerer()
        answer = answerer.answer(question_input.repository_path, question_input.question)
        if question_input.session_id:
            memory_store.append_event(
                session_id=question_input.session_id,
                event_type=MemoryEventType.CODEBASE_QA,
                summary=f"代码仓库问答：{question_input.question[:80]}",
                payload={
                    "question": question_input.question,
                    "repository_path": answer.repository_path,
                    "evidence_count": len(answer.evidence),
                },
            )
        return answer

    @application.post("/codebase/impact", response_model=CodeImpactReport, tags=["codebase"])
    def codebase_impact(impact_input: CodeImpactInput) -> CodeImpactReport:
        """Analyze file-level impact for a target file."""

        return CodebaseQuestionAnswerer().impact(
            impact_input.repository_path,
            impact_input.target_path,
        )

    @application.post("/codebase/review-diff", response_model=DiffReviewReport, tags=["codebase"])
    def codebase_review_diff(codebase_input: CodebaseInput) -> DiffReviewReport:
        """Review current git diff in a repository."""

        return DiffReviewer().review(codebase_input.repository_path)

    return application


# Uvicorn looks for this module-level ASGI object:
#   python -m uvicorn app.api.routes:app --reload
app = create_app()
