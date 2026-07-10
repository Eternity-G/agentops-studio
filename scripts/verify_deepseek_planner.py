"""Manual DeepSeek planner verification script.

This script intentionally lives outside tests because it calls the real
DeepSeek API when `.env` is configured with a real key.

Run:
    python scripts/verify_deepseek_planner.py
"""

from __future__ import annotations

import asyncio

from app.planner import Planner
from app.settings import load_settings
from app.schemas import TaskInput


async def main() -> None:
    """Call the configured provider and print the generated plan."""

    settings = load_settings()
    print(f"provider={settings.model_provider}")
    print(f"model={settings.default_model}")

    planner = Planner()
    plan = await planner.create_plan(
        TaskInput(task="为 AgentOps Studio 生成一个三步以内的实施计划")
    )

    print(plan.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
