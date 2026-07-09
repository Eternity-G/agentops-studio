# 第 7 步：基础 Trace 与 API Demo

## 目标

第 7 步的目标是把第 6 步已经跑通的 Agent 主链路包装成一个真正可以被 HTTP 调用的 API，并且开始记录最基础的 Trace。

当前仍然不引入数据库、消息队列或专业 tracing 系统。Trace 先保存在 `AgentState.trace_events` 中，方便学习和测试。

## 改动文件

```text
app/
  agent.py
  api/
    routes.py
tests/
  test_task_api.py
```

## 新增能力

| 能力 | 说明 |
|---|---|
| `task_id` | 每次 Agent 运行的任务 ID。 |
| `trace_id` | 每次 Agent 运行的追踪 ID。 |
| `TraceEvent` | 最小 trace 事件，包含 event_id、trace_id、stage、message。 |
| `trace_events` | 保存在 `AgentState` 中的事件列表。 |
| `POST /tasks/run` | 通过 HTTP 调用最小 Agent 主链路。 |

## 当前 API

### `POST /tasks/run`

请求体：

```json
{
  "task": "通过 API 跑通 Agent 主链路"
}
```

响应体是完整 `AgentState`，核心字段包括：

```json
{
  "task_id": "...",
  "trace_id": "...",
  "status": "completed",
  "plan": {},
  "step_results": [],
  "final_answer": {},
  "trace_events": []
}
```

## Trace 设计

当前每次运行会记录以下阶段：

| 阶段 | 当前事件 |
|---|---|
| `plan` | 开始规划、生成计划完成。 |
| `act` | 开始 mock 执行、生成步骤结果完成。 |
| `reflect` | 开始反思、确认步骤结果覆盖计划。 |
| `finalize` | 开始生成最终答案、最终答案创建完成。 |

这不是最终生产级 Trace，只是第一版可观测数据结构。后续可以扩展：

- 时间戳。
- 耗时。
- token 用量。
- 模型名称。
- 工具输入输出。
- 错误堆栈。
- trace 持久化存储。

## 可观测验证

运行全部测试：

```bash
python -m pytest
```

当前期望结果：

```text
34 passed
```

启动服务：

```bash
python -m uvicorn app.api.routes:app --reload
```

调用 API：

```bash
curl -X POST http://localhost:8000/tasks/run ^
  -H "Content-Type: application/json" ^
  -d "{\"task\":\"通过 API 跑通 Agent 主链路\"}"
```

也可以用 TestClient 快速验证：

```bash
python -c "from fastapi.testclient import TestClient; from app.api.routes import create_app; body = TestClient(create_app()).post('/tasks/run', json={'task':'demo'}).json(); print(body['status'], bool(body['task_id']), bool(body['trace_id']), len(body['trace_events']))"
```

期望输出：

```text
completed True True 8
```

## 测试覆盖

| 测试 | 验证什么 |
|---|---|
| `test_run_task_api_returns_completed_state` | API 可以跑通 Agent 主链路并返回 completed 状态。 |
| `test_run_task_api_returns_trace_events` | 响应包含 plan、act、reflect、finalize trace event。 |
| `test_run_task_api_rejects_invalid_task` | 无效任务会被 FastAPI/Pydantic 拒绝。 |
| `test_openapi_contains_task_run_path` | OpenAPI 文档包含 `/tasks/run`。 |

## 面试问题

| 问题 | 回答要点 |
|---|---|
| 为什么 Agent 系统需要 Trace？ | Agent 是多阶段系统，Trace 能帮助定位规划、执行、反思、最终输出中的问题。 |
| 为什么现在先把 Trace 放在 state 中？ | 当前阶段先验证数据结构和可观测性，不急着引入数据库或复杂 tracing 平台。 |
| `task_id` 和 `trace_id` 有什么区别？ | `task_id` 标识任务，`trace_id` 标识一次执行链路；未来一次任务可能有多次运行。 |
| 为什么 API 返回完整 `AgentState`？ | 学习阶段优先可观察，方便看到 plan、step_results、final_answer 和 trace。 |
| 为什么 `/tasks/run` 是 async？ | Agent 后续会调用模型和工具，都是 I/O 密集操作，async 接口更容易扩展。 |
| 为什么无效任务返回 422？ | FastAPI 使用 Pydantic 自动校验请求体，无效输入不会进入业务逻辑。 |

## 完成标准

- `AgentState` 包含 `task_id`、`trace_id`、`trace_events`。
- `POST /tasks/run` 可以返回完整 Agent 状态。
- Trace 至少覆盖 `plan`、`act`、`reflect`、`finalize`。
- `/openapi.json` 包含 `/tasks/run`。
- `python -m pytest` 通过。
