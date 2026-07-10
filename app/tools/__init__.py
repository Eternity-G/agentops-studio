"""Tool layer for AgentOps Studio.

工具层负责把 Agent 的“动作”变成可注册、可测试、可替换的工具调用。
第 8 步只实现 mock 工具注册表，不接真实搜索、SQL、Python 或 MCP。
"""

from __future__ import annotations

from app.tools.base import Tool, ToolDefinition, ToolResult
from app.tools.mock import MockStepTool
from app.tools.registry import MockToolRegistry, ToolRegistry

__all__ = [
    "MockStepTool",
    "MockToolRegistry",
    "Tool",
    "ToolDefinition",
    "ToolRegistry",
    "ToolResult",
]
