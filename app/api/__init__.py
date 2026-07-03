"""API package for AgentOps Studio.

这个包会逐步承载 HTTP 路由、依赖注入和中间件。第 2 步只放一个
健康检查接口，避免过早引入 Agent 主链路。
"""

from __future__ import annotations
