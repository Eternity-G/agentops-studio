"""Minimal Agent state machine.

第 6 步把前面已经完成的 Planner、MockProvider 和 Pydantic schema 串起来，
形成第一条可测试的 Agent 主链路：

    task -> plan -> act -> reflect -> finalize

当前实现仍然是最小版本：`act` 阶段不调用真实工具，只生成可观测的 mock
步骤结果。真实工具调用、Trace、重试和人工审批会在后续步骤加入。
"""

from __future__ import annotations

from enum import StrEnum
from uuid import uuid4

from pydantic import Field

from app.planner import Planner
from app.schemas import ExecutionPlan, FinalAnswer, StepStatus, StrictSchema, TaskInput
from app.tools import MockToolRegistry, ToolRegistry


class AgentRunStatus(StrEnum):
    """Lifecycle status for one Agent run."""

    CREATED = "created"
    PLANNED = "planned"
    ACTED = "acted"
    REFLECTED = "reflected"
    COMPLETED = "completed"
    FAILED = "failed"


class StepExecutionResult(StrictSchema):
    """Observable result produced by executing one plan step."""

    step_id: int = Field(description="The plan step id that produced this result.")
    tool_name: str = Field(description="Tool used to produce this result.")
    status: StepStatus = Field(description="Execution status for this step.")
    output: str = Field(description="Human-readable mock output for this step.")
    error: str | None = Field(
        default=None,
        description="Optional failure reason when the tool call does not complete.",
    )


class TraceEvent(StrictSchema):
    """Minimal trace event recorded during one Agent run."""

    event_id: str = Field(description="Unique id for this trace event.")
    trace_id: str = Field(description="Trace id shared by all events in one Agent run.")
    stage: str = Field(description="Runtime stage, such as plan, act, reflect, or finalize.")
    message: str = Field(description="Human-readable event message.")


class AgentState(StrictSchema):
    """State object passed through the minimal Agent flow."""

    task_id: str = Field(default_factory=lambda: str(uuid4()))
    trace_id: str = Field(default_factory=lambda: str(uuid4()))
    task_input: TaskInput
    status: AgentRunStatus = AgentRunStatus.CREATED
    plan: ExecutionPlan | None = None
    step_results: list[StepExecutionResult] = Field(default_factory=list)
    final_answer: FinalAnswer | None = None
    trace_events: list[TraceEvent] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class AgentRuntime:
    """Run the minimal Agent state machine.

    这个类是后续 LangGraph 或更完整 runtime 的前身。现在先用普通 Python
    方法把状态流跑通，让每个阶段都有清晰边界和测试。
    """

    def __init__(
        self,
        planner: Planner | None = None,
        tool_registry: ToolRegistry | None = None,
    ) -> None:
        self._planner = planner or Planner()
        self._tool_registry = tool_registry or MockToolRegistry()

    async def run(self, task_input: TaskInput) -> AgentState:
        """Run the full minimal flow and return the final state."""

        state = AgentState(task_input=task_input)

        try:
            state = await self._plan(state)
            state = self._act(state)
            state = self._reflect(state)
            state = self._finalize(state)
        except Exception as exc:  # pragma: no cover - defensive boundary for future runtime errors.
            state.status = AgentRunStatus.FAILED
            state.errors.append(str(exc))
            self._record_trace(state, stage="failed", message=str(exc))

        return state

    async def run_from_text(self, task: str) -> AgentState:
        """Convenience helper for demos and early tests."""

        return await self.run(TaskInput(task=task))

    async def _plan(self, state: AgentState) -> AgentState:
        """Create a structured plan from the task input."""

        self._record_trace(state, stage="plan", message="start planning")
        state.plan = await self._planner.create_plan(state.task_input)
        for attempt in self._planner.last_attempts:
            if attempt.success:
                fallback = " with fallback" if attempt.used_fallback else ""
                self._record_trace(
                    state,
                    stage="plan",
                    message=(
                        f"provider {attempt.provider_name}/{attempt.model} "
                        f"attempt {attempt.attempt} succeeded{fallback}"
                    ),
                )
            else:
                self._record_trace(
                    state,
                    stage="plan",
                    message=(
                        f"provider {attempt.provider_name}/{attempt.model} "
                        f"attempt {attempt.attempt} failed: {attempt.error}"
                    ),
                )
        state.status = AgentRunStatus.PLANNED
        self._record_trace(
            state,
            stage="plan",
            message=f"created execution plan with {len(state.plan.steps)} steps",
        )
        return state

    def _act(self, state: AgentState) -> AgentState:
        """Execute each plan step with a mock executor.

        后续真实工具调用会替换这里。当前 mock executor 的价值是让状态机
        可观测：每个 plan step 都会产生一个对应的 step result。
        """

        if state.plan is None:
            raise ValueError("cannot act before planning")

        self._record_trace(state, stage="act", message="start tool execution")
        state.step_results = []
        for step in state.plan.steps:
            tool_result = self._tool_registry.execute_step(step)
            state.step_results.append(
                StepExecutionResult(
                    step_id=step.step_id,
                    tool_name=tool_result.tool_name,
                    status=tool_result.status,
                    output=tool_result.output,
                    error=tool_result.error,
                )
            )
            if tool_result.status == StepStatus.FAILED:
                self._record_trace(
                    state,
                    stage="act",
                    message=f"tool failed for step {step.step_id}: {tool_result.output}",
                )

        state.status = AgentRunStatus.ACTED
        self._record_trace(
            state,
            stage="act",
            message=f"created {len(state.step_results)} tool step results",
        )
        return state

    def _reflect(self, state: AgentState) -> AgentState:
        """Check whether mock execution covered every plan step."""

        if state.plan is None:
            raise ValueError("cannot reflect before planning")

        self._record_trace(state, stage="reflect", message="start reflection")
        planned_step_ids = {step.step_id for step in state.plan.steps}
        completed_step_ids = {
            result.step_id for result in state.step_results if result.status == StepStatus.COMPLETED
        }

        missing_step_ids = planned_step_ids - completed_step_ids
        if missing_step_ids:
            missing = sorted(missing_step_ids)
            raise ValueError(f"missing completed step results: {missing}")

        state.status = AgentRunStatus.REFLECTED
        self._record_trace(state, stage="reflect", message="all planned steps completed")
        return state

    def _finalize(self, state: AgentState) -> AgentState:
        """Generate the final structured answer."""

        if state.plan is None:
            raise ValueError("cannot finalize before planning")

        self._record_trace(state, stage="finalize", message="start finalization")
        state.final_answer = FinalAnswer(
            answer="已生成并完成最小 Agent 主链路的结构化计划。",
            summary="最小 Agent 流程已完成 plan -> act -> reflect -> finalize。",
            completed=True,
            confidence=1.0,
            next_actions=["进入第 13 步：本地 Markdown 文档读取工具"],
        )
        state.status = AgentRunStatus.COMPLETED
        self._record_trace(state, stage="finalize", message="final answer created")
        return state

    def _record_trace(self, state: AgentState, *, stage: str, message: str) -> None:
        """Append a minimal trace event to the state."""

        state.trace_events.append(
            TraceEvent(
                event_id=str(uuid4()),
                trace_id=state.trace_id,
                stage=stage,
                message=message,
            )
        )
