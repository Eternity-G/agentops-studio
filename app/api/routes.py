"""FastAPI application routes.

当前 API 包含两个最小接口：
1. `GET /health` 用于健康检查。
2. `POST /tasks/run` 用于演示 Agent 主链路和基础 Trace。
3. `POST /documents/ask` 用于演示最小本地文档问答链路。
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from app import __version__
from app.agent import AgentRuntime, AgentState
from app.document_qa import MarkdownQuestionAnswerer
from app.schemas import DocumentQuestionAnswer, DocumentQuestionInput, TaskInput
from app.settings import load_settings


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    使用工厂函数而不是直接在全局堆叠配置，有两个好处：
    1. 测试可以创建一个干净的 app 实例。
    2. 后续加入中间件、异常处理、生命周期事件时有统一入口。
    """

    settings = load_settings()
    application = FastAPI(
        title=settings.app_name,
        version=__version__,
        debug=settings.debug,
    )

    @application.get("/health", tags=["system"])
    def health_check() -> dict[str, Any]:
        """Return a lightweight health status for monitoring and tests.

        健康检查必须保持轻量：这里不调用模型 API、不连接数据库、
        不执行外部工具。更重的依赖检查后续应放到 `/ready` 或诊断接口。
        """

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
        return await runtime.run(task_input)

    @application.post("/documents/ask", response_model=DocumentQuestionAnswer, tags=["documents"])
    def ask_document(question_input: DocumentQuestionInput) -> DocumentQuestionAnswer:
        """Answer a question from one local Markdown document."""

        answerer = MarkdownQuestionAnswerer()
        return answerer.answer(question_input)

    return application


# Uvicorn 默认寻找模块级 ASGI 应用对象：
#   python -m uvicorn app.api.routes:app --reload
app = create_app()
