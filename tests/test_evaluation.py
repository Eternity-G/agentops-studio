"""Tests for the offline evaluation runner."""

from __future__ import annotations

from app.evaluation import EvalCase, EvalCaseType, EvaluationRunner
from scripts.run_evals import load_cases


def test_evaluation_runner_passes_mixed_cases() -> None:
    """EvaluationRunner should pass deterministic task, document, and memory cases."""

    cases = [
        EvalCase(
            case_id="task",
            case_type=EvalCaseType.TASK_RUN,
            description="任务主链路",
            input={"task": "生成计划"},
            expected_contains=["completed"],
        ),
        EvalCase(
            case_id="document",
            case_type=EvalCaseType.DOCUMENT_QA,
            description="文档问答",
            input={
                "question": "ReadMarkdownTool 是什么？",
                "path": "docs/第13步-本地Markdown文档读取工具.md",
            },
            expected_contains=["ReadMarkdownTool"],
        ),
        EvalCase(
            case_id="memory",
            case_type=EvalCaseType.SESSION_MEMORY,
            description="会话记忆",
            input={"session_id": "test-session", "content": "保存备注"},
            expected_contains=["test-session", "note", "保存备注"],
        ),
    ]

    report = EvaluationRunner().run_sync(cases)

    assert report.total == 3
    assert report.passed == 3
    assert report.failed == 0


def test_evaluation_report_renders_markdown() -> None:
    """EvalReport should render a readable Markdown summary."""

    cases = [
        EvalCase(
            case_id="task",
            case_type=EvalCaseType.TASK_RUN,
            description="任务主链路",
            input={"task": "生成计划"},
            expected_contains=["completed"],
        )
    ]

    report = EvaluationRunner().run_sync(cases)
    markdown = report.to_markdown()

    assert "# AgentOps Studio 自动评测报告" in markdown
    assert "通过率：100%" in markdown
    assert "| task | task_run | 通过 | - |" in markdown


def test_load_cases_reads_default_eval_file() -> None:
    """The eval script should load tracked JSON cases."""

    cases = load_cases()

    assert len(cases) == 3
    assert {case.case_type for case in cases} == {
        EvalCaseType.TASK_RUN,
        EvalCaseType.DOCUMENT_QA,
        EvalCaseType.SESSION_MEMORY,
    }
