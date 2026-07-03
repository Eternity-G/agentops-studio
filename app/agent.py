"""Minimal Agent state machine.

第 6 步把前面已经完成的 Planner、MockProvider 和 Pydantic schema 串起来，
形成第一条可测试的 Agent 主链路：

    task -> plan -> act -> reflect -> finalize

当前实现仍然是最小版本：`act` 阶段不调用真实工具，只生成可观测的 mock
步骤结果。真实工具调用、Trace、重试和人工审批会在后续步骤加入。
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from app.planner import Planner
from app.schemas import ExecutionPlan, FinalAnswer, StepStatus, StrictSchema, TaskInput


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
    status: StepStatus = Field(description="Execution status for this step.")
    output: str = Field(description="Human-readable mock output for this step.")


class AgentState(StrictSchema):
    """State object passed through the minimal Agent flow."""

    task_input: TaskInput
    status: AgentRunStatus = AgentRunStatus.CREATED
    plan: ExecutionPlan | None = None
    step_results: list[StepExecutionResult] = Field(default_factory=list)
    final_answer: FinalAnswer | None = None
    errors: list[str] = Field(default_factory=list)


class AgentRuntime:
    """Run the minimal Agent state machine.

    这个类是后续 LangGraph 或更完整 runtime 的前身。现在先用普通 Python
    方法把状态流跑通，让每个阶段都有清晰边界和测试。
    """

    def __init__(self, planner: Planner | None = None) -> None:
        self._planner = planner or Planner()

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

        return state

    async def run_from_text(self, task: str) -> AgentState:
        """Convenience helper for demos and early tests."""

        return await self.run(TaskInput(task=task))

    async def _plan(self, state: AgentState) -> AgentState:
        """Create a structured plan from the task input."""

        state.plan = await self._planner.create_plan(state.task_input)
        state.status = AgentRunStatus.PLANNED
        return state

    def _act(self, state: AgentState) -> AgentState:
        """Execute each plan step with a mock executor.

        后续真实工具调用会替换这里。当前 mock executor 的价值是让状态机
        可观测：每个 plan step 都会产生一个对应的 step result。
        """

        if state.plan is None:
            raise ValueError("cannot act before planning")

        state.step_results = [
            StepExecutionResult(
                step_id=step.step_id,
                status=StepStatus.COMPLETED,
                output=f"mock completed: {step.goal}",
            )
            for step in state.plan.steps
        ]
        state.status = AgentRunStatus.ACTED
        return state

    def _reflect(self, state: AgentState) -> AgentState:
        """Check whether mock execution covered every plan step."""

        if state.plan is None:
            raise ValueError("cannot reflect before planning")

        planned_step_ids = {step.step_id for step in state.plan.steps}
        completed_step_ids = {
            result.step_id for result in state.step_results if result.status == StepStatus.COMPLETED
        }

        missing_step_ids = planned_step_ids - completed_step_ids
        if missing_step_ids:
            missing = sorted(missing_step_ids)
            raise ValueError(f"missing completed step results: {missing}")

        state.status = AgentRunStatus.REFLECTED
        return state

    def _finalize(self, state: AgentState) -> AgentState:
        """Generate the final structured answer."""

        if state.plan is None:
            raise ValueError("cannot finalize before planning")

        state.final_answer = FinalAnswer(
            answer="已生成并完成最小 Agent 主链路的结构化计划。",
            summary="最小 Agent 流程已完成 plan -> act -> reflect -> finalize。",
            completed=True,
            confidence=1.0,
            next_actions=["进入第 7 步：基础 Trace 与 API Demo"],
        )
        state.status = AgentRunStatus.COMPLETED
        return state
