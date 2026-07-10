"""In-memory session store.

第 15 步先实现进程内记忆，用来学习会话状态的工程边界。它不负责持久化，
服务重启后数据会丢失；后续如果接数据库，可以保持相同的上层接口。
"""

from __future__ import annotations

from app.agent import AgentState
from app.schemas import (
    DocumentQuestionAnswer,
    MemoryEvent,
    MemoryEventType,
    MemoryNoteInput,
    SessionState,
)


class InMemorySessionStore:
    """Store session memory events in process memory."""

    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}

    def get_session(self, session_id: str) -> SessionState:
        """Return an existing session or create an empty one."""

        if session_id not in self._sessions:
            self._sessions[session_id] = SessionState(session_id=session_id)
        return self._sessions[session_id]

    def append_event(
        self,
        *,
        session_id: str,
        event_type: MemoryEventType,
        summary: str,
        payload: dict[str, object] | None = None,
    ) -> SessionState:
        """Append one event and return the updated session."""

        session = self.get_session(session_id)
        session.events.append(
            MemoryEvent(
                event_type=event_type,
                summary=summary,
                payload=payload or {},
            )
        )
        return session

    def record_task_run(self, *, session_id: str, state: AgentState) -> SessionState:
        """Store a compact summary of one Agent task run."""

        final_summary = state.final_answer.summary if state.final_answer else None
        return self.append_event(
            session_id=session_id,
            event_type=MemoryEventType.TASK_RUN,
            summary=f"任务运行：{state.task_input.task[:80]}",
            payload={
                "task_id": state.task_id,
                "trace_id": state.trace_id,
                "status": state.status.value,
                "task": state.task_input.task,
                "final_summary": final_summary,
                "error_count": len(state.errors),
            },
        )

    def record_document_answer(
        self,
        *,
        session_id: str,
        answer: DocumentQuestionAnswer,
    ) -> SessionState:
        """Store a compact summary of one document question-answer result."""

        return self.append_event(
            session_id=session_id,
            event_type=MemoryEventType.DOCUMENT_QA,
            summary=f"文档问答：{answer.question[:80]}",
            payload={
                "question": answer.question,
                "source_path": answer.source_path,
                "completed": answer.completed,
                "excerpt": answer.excerpt,
            },
        )

    def record_note(self, *, session_id: str, note: MemoryNoteInput) -> SessionState:
        """Store a manual note in a session."""

        return self.append_event(
            session_id=session_id,
            event_type=MemoryEventType.NOTE,
            summary=f"备注：{note.content[:80]}",
            payload={
                "content": note.content,
                "metadata": note.metadata,
            },
        )
