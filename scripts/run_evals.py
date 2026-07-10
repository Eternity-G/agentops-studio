"""Run offline evaluation cases and write a Markdown report."""

from __future__ import annotations

import json
from pathlib import Path

from app.evaluation import EvalCase, EvaluationRunner


DEFAULT_CASES_PATH = Path("evals/cases.json")
DEFAULT_REPORT_PATH = Path("evals/latest-report.md")


def load_cases(path: Path = DEFAULT_CASES_PATH) -> list[EvalCase]:
    """Load evaluation cases from a JSON file."""

    raw_cases = json.loads(path.read_text(encoding="utf-8"))
    return [EvalCase.model_validate(raw_case) for raw_case in raw_cases]


def main() -> int:
    """Run evaluations and return a process exit code."""

    cases = load_cases()
    report = EvaluationRunner().run_sync(cases)
    DEFAULT_REPORT_PATH.write_text(report.to_markdown(), encoding="utf-8")
    print(report.to_markdown())
    return 0 if report.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
