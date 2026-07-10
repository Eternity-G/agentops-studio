# AgentOps Studio

AgentOps Studio 是一个用于学习和构建 Agent 工程系统的项目。目标是逐步搭建一个包含任务规划、工具调用、记忆、Trace、评测和部署能力的 Agent 工程平台。

## 当前状态

当前已完成 **阶段 1 的第 11 步：用真实 DeepSeek Planner 跑通 API Demo**。

已经具备的能力：

- Python 包可以被正常导入。
- 配置可以从环境变量中读取。
- FastAPI 应用可以启动。
- `GET /health` 可以返回服务状态。
- OpenAPI 文档可以识别 `/health` 路由。
- Pydantic schema 可以校验任务输入、执行计划、计划步骤、证据和最终答案。
- `ExecutionPlan` 可以导出 JSON Schema，后续可用于 OpenAPI、LLM 结构化输出和评测。
- 已定义统一模型提供商接口。
- `MockProvider` 可以在无 API key 情况下返回符合 `ExecutionPlan` 的结构化计划。
- Provider 工厂可以根据配置创建模型适配器。
- `Planner` 可以接收 `TaskInput`，调用 provider，并返回合法 `ExecutionPlan`。
- 已跑通 “任务输入 -> MockProvider -> 结构化计划” 的最小链路。
- `AgentRuntime` 可以串起 `plan -> act -> reflect -> finalize` 的最小状态流。
- 当前使用 mock executor，为每个计划步骤生成可观测的执行结果。
- `AgentState` 可以保存任务输入、计划、步骤结果、最终答案和错误信息。
- `AgentState` 已包含 `task_id`、`trace_id` 和基础 `trace_events`。
- `POST /tasks/run` 可以通过 HTTP 跑通最小 Agent 主链路。
- 已定义统一工具接口、工具定义和工具结果。
- `MockToolRegistry` 可以注册并路由 mock 工具。
- `AgentRuntime` 的 `act` 阶段已经通过工具层生成步骤结果。
- 工具调用失败会进入结构化 `FAILED` 结果，而不是静默成功。
- Agent 状态和 Trace 可以暴露未知工具、工具异常等失败边界。
- 已接入 DeepSeek OpenAI-compatible Provider。
- DeepSeekProvider 可以把模型 JSON 输出校验为 `ExecutionPlan`。
- Provider 工厂可以通过 `MODEL_PROVIDER=deepseek` 创建真实模型 provider。
- 本地 `.env` 可以启用真实 DeepSeek provider。
- `scripts/verify_deepseek_planner.py` 可以调用真实 DeepSeek 生成计划。
- `POST /tasks/run` 可以通过真实 DeepSeek Planner 跑通 Agent API Demo。

当前还没有实现：

- 真实外部工具调用。
- RAG 或数据库。
- 记忆系统。
- 前端页面。

## 当前目录结构

```text
app/
  __init__.py
  agent.py
  planner.py
  schemas.py
  settings.py
  api/
    __init__.py
    routes.py
  providers/
    __init__.py
    base.py
    deepseek.py
    factory.py
    mock.py
  tools/
    __init__.py
    base.py
    mock.py
    registry.py
scripts/
  verify_deepseek_planner.py
tests/
  test_agent.py
  test_deepseek_provider.py
  test_health.py
  test_planner.py
  test_providers.py
  test_project_import.py
  test_schemas.py
  test_settings.py
  test_task_api.py
  test_tools.py
  test_tool_failures.py
docs/
  第1步-项目骨架与环境.md
  第2步-FastAPI健康检查.md
  第3步-Pydantic-Schema.md
  第4步-Mock模型适配层.md
  第5步-Planner最小实现.md
  第6步-状态机主链路.md
  第7步-基础Trace与API-Demo.md
  第8步-工具层与Mock-Tool-Registry.md
  第9步-工具调用失败处理与回归测试.md
  第10步-接入DeepSeek大模型Provider.md
  第11步-用真实DeepSeek-Planner跑通API-Demo.md
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

运行 Agent API Demo：

```bash
curl -X POST http://localhost:8000/tasks/run ^
  -H "Content-Type: application/json" ^
  -d "{\"task\":\"通过 API 跑通 Agent 主链路\"}"
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
48 passed
```

Schema 导出：

```bash
python -c "from app.schemas import ExecutionPlan; print(ExecutionPlan.model_json_schema()['title'])"
```

期望结果：

```text
ExecutionPlan
```

MockProvider 输出验证：

```bash
python -c "import asyncio; from app.providers import create_provider; from app.schemas import TaskInput; provider = create_provider(); plan = asyncio.run(provider.create_plan(TaskInput(task='生成计划'))); print(provider.info); print(type(plan).__name__, len(plan.steps))"
```

期望结果包含：

```text
ProviderInfo(name='mock', model='mock-planner-v1', is_mock=True)
ExecutionPlan 3
```

Planner 输出验证：

```bash
python -c "import asyncio; from app.planner import Planner; plan = asyncio.run(Planner().create_plan_from_text('生成计划')); print(type(plan).__name__, len(plan.steps), plan.steps[0].goal)"
```

期望结果包含：

```text
ExecutionPlan 3 理解用户任务
```

Agent 主链路验证：

```bash
python -c "import asyncio; from app.agent import AgentRuntime; state = asyncio.run(AgentRuntime().run_from_text('生成计划')); print(state.status); print(type(state.plan).__name__, len(state.step_results), state.final_answer.completed)"
```

期望结果包含：

```text
completed
ExecutionPlan 3 True
```

API Demo 验证：

```bash
python -c "from fastapi.testclient import TestClient; from app.api.routes import create_app; body = TestClient(create_app()).post('/tasks/run', json={'task':'demo'}).json(); print(body['status'], bool(body['task_id']), bool(body['trace_id']), len(body['trace_events']))"
```

期望结果包含：

```text
completed True True 8
```

Mock Tool Registry 验证：

```bash
python -c "from app.tools import MockToolRegistry; registry = MockToolRegistry(); print([tool.name for tool in registry.list_definitions()])"
```

期望结果包含：

```text
['mock_step', 'planner']
```

工具失败回归验证：

```bash
python -c "import asyncio; from app.agent import AgentRuntime; from app.tools import MockStepTool, ToolRegistry; runtime = AgentRuntime(tool_registry=ToolRegistry(tools=[MockStepTool(name='mock_step')])); state = asyncio.run(runtime.run_from_text('failure demo')); print(state.status); print([(r.step_id, r.tool_name, r.status, r.error) for r in state.step_results]); print(state.errors)"
```

期望结果包含：

```text
failed
unknown tool: planner
missing completed step results: [2]
```

DeepSeek Provider 本地配置：

```bash
MODEL_PROVIDER=deepseek
DEFAULT_MODEL=deepseek-v4-flash
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_API_KEY=你的本地 API key
```

注意：不要把真实 API key 写进代码、README 或 Git 提交。

真实 DeepSeek Planner 验证：

```bash
python scripts/verify_deepseek_planner.py
```

本地已验证结果：

```text
provider=deepseek
model=deepseek-v4-flash
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
- [第 4 步：Mock 模型适配层](docs/第4步-Mock模型适配层.md)
- [第 5 步：Planner 最小实现](docs/第5步-Planner最小实现.md)
- [第 6 步：状态机主链路](docs/第6步-状态机主链路.md)
- [第 7 步：基础 Trace 与 API Demo](docs/第7步-基础Trace与API-Demo.md)
- [第 8 步：工具层与 Mock Tool Registry](docs/第8步-工具层与Mock-Tool-Registry.md)
- [第 9 步：工具调用失败处理与回归测试](docs/第9步-工具调用失败处理与回归测试.md)
- [第 10 步：接入 DeepSeek 大模型 Provider](docs/第10步-接入DeepSeek大模型Provider.md)
- [第 11 步：用真实 DeepSeek Planner 跑通 API Demo](docs/第11步-用真实DeepSeek-Planner跑通API-Demo.md)

## 下一步计划

下一步是 **第 12 步：真实模型输出修复、重试与 fallback**。

目标：

- 当真实模型输出非法 JSON 时，提供一次修复或重试机会。
- DeepSeek 调用失败时可 fallback 到 MockProvider，保证 demo 不直接崩溃。
- Trace 中记录 provider 名称、模型名和失败原因。
- 增加不访问真实网络的回归测试。

完成后应能验证：

```bash
python -m pytest
```

并能通过测试证明：

- 非法 JSON 可以被检测并解释。
- provider 失败可以进入 fallback 或结构化错误。
- API Demo 在真实模型不稳定时仍可调试。
