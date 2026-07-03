# AgentOps Studio

AgentOps Studio 是一个用于学习和构建 Agent 工程系统的项目。目标是逐步搭建一个包含任务规划、工具调用、记忆、Trace、评测和部署能力的 Agent 工程平台。

## 当前状态

当前已完成 **阶段 1 的第 3 步：Pydantic Schema**。

已经具备的能力：

- Python 包可以被正常导入。
- 配置可以从环境变量中读取。
- FastAPI 应用可以启动。
- `GET /health` 可以返回服务状态。
- OpenAPI 文档可以识别 `/health` 路由。
- Pydantic schema 可以校验任务输入、执行计划、计划步骤、证据和最终答案。
- `ExecutionPlan` 可以导出 JSON Schema，后续可用于 OpenAPI、LLM 结构化输出和评测。

当前还没有实现：

- 真实大模型调用。
- Agent planning。
- 工具调用。
- RAG 或数据库。
- 记忆系统。
- 前端页面。

## 当前目录结构

```text
app/
  __init__.py
  schemas.py
  settings.py
  api/
    __init__.py
    routes.py
tests/
  test_health.py
  test_project_import.py
  test_schemas.py
  test_settings.py
docs/
  第1步-项目骨架与环境.md
  第2步-FastAPI健康检查.md
  第3步-Pydantic-Schema.md
.env.example
pyproject.toml
```

## 快速开始

安装开发依赖：

```bash
python -m pip install -e ".[dev]"
```

运行测试：

```bash
python -m pytest
```

启动本地 API 服务：

```bash
python -m uvicorn app.api.routes:app --reload
```

查看健康检查：

```bash
curl http://localhost:8000/health
```

查看接口文档：

```text
http://localhost:8000/docs
http://localhost:8000/openapi.json
```

## 当前验证结果

测试：

```bash
python -m pytest
```

期望结果：

```text
16 passed
```

Schema 导出：

```bash
python -c "from app.schemas import ExecutionPlan; print(ExecutionPlan.model_json_schema()['title'])"
```

期望结果：

```text
ExecutionPlan
```

健康检查响应：

```json
{
  "status": "ok",
  "app_name": "AgentOps Studio",
  "environment": "development",
  "version": "0.1.0"
}
```

## 学习文档

每一步的详细设计、测试方式和面试问题整理在独立文档中：

- [第 1 步：项目骨架与环境](docs/第1步-项目骨架与环境.md)
- [第 2 步：FastAPI 健康检查](docs/第2步-FastAPI健康检查.md)
- [第 3 步：Pydantic Schema](docs/第3步-Pydantic-Schema.md)

## 下一步计划

下一步是 **第 4 步：Mock 模型适配层**。

目标：

- 定义统一模型提供商接口。
- 实现不依赖真实 API key 的 `MockProvider`。
- 让 `MockProvider` 固定返回符合 `ExecutionPlan` 的结构化计划。
- 编写测试验证 provider 返回结果稳定、字段符合 schema。

完成后应能验证：

```bash
python -m pytest
```

并能通过测试证明：

- 不配置真实模型 API key 也能生成结构化计划。
- provider 返回值可以被 `ExecutionPlan` 校验。
- 后续 Planner 可以依赖统一 provider 接口，而不是直接依赖某个模型厂商 SDK。
