# AgentOps Studio

AgentOps Studio 是一个用于学习和构建 Agent 工程系统的项目。它的长期目标不是做一个简单聊天机器人，而是逐步搭建一个包含任务规划、工具调用、记忆、Trace、评测和部署能力的 Agent 工程平台。

当前已完成 **阶段 1 的第 3 步：Pydantic Schema**。这一阶段刻意保持简单，目的是先保证项目结构清晰、可以导入、可以测试、可以启动最小 API 服务，并拥有稳定的 Agent 数据契约。

## 当前目标

当前已验证几件事：

- Python 包可以被正常导入。
- 配置可以从环境变量中读取。
- 测试框架可以运行。
- FastAPI 应用可以创建。
- `/health` 可以返回服务状态。
- OpenAPI 文档可以识别 `/health` 路由。
- Pydantic schema 可以校验任务输入、执行计划、计划步骤和最终答案。
- Schema 可以导出 JSON Schema，后续可用于 OpenAPI 文档和 LLM 结构化输出校验。
- 仓库已经可以连接到 GitHub 远程地址。

本步骤暂不实现真实模型调用、Agent planning、RAG、记忆系统或工具调用。

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
.env.example
pyproject.toml
```

## 文件说明

| 文件 | 作用 |
|---|---|
| `app/__init__.py` | Python 包入口，当前只暴露项目版本号，用来验证项目可导入。 |
| `app/schemas.py` | 项目共享 Pydantic schema，定义任务输入、计划、步骤、证据和最终答案。 |
| `app/settings.py` | 配置加载模块，集中读取环境变量，避免后续代码到处直接访问 `os.environ`。 |
| `app/api/__init__.py` | API 包入口，后续会继续承载路由、依赖和中间件。 |
| `app/api/routes.py` | FastAPI 应用入口，当前实现 `GET /health` 健康检查接口。 |
| `tests/test_health.py` | 验证 `/health` 状态码、响应体和 OpenAPI 文档。 |
| `tests/test_project_import.py` | 验证 `app` 包可以被正常导入。 |
| `tests/test_schemas.py` | 验证 Pydantic schema 的合法输入、非法输入、依赖关系和 JSON Schema 导出。 |
| `tests/test_settings.py` | 验证默认配置和环境变量覆盖逻辑。 |
| `.env.example` | 环境变量模板，后续复制为 `.env` 使用。 |
| `pyproject.toml` | 项目配置文件，声明包信息、测试配置和代码规范工具配置。 |
| `.gitignore` | Git 忽略规则，避免提交缓存、虚拟环境和本地密钥文件。 |

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

如果暂时不想安装 `pytest`，也可以使用 Python 标准库自带的 `unittest`：

```bash
python -m unittest discover -s tests
```

## 可观测验证方式

完成当前步骤后，至少要能看到以下结果。

验证项目可以导入：

```bash
python -c "import app; print(app.__version__)"
```

期望输出：

```text
0.1.0
```

验证配置加载：

```bash
python -c "from app.settings import load_settings; print(load_settings())"
```

期望能看到类似输出：

```text
AppSettings(app_name='AgentOps Studio', app_env='development', debug=True, model_provider='mock', default_model='mock-planner-v1')
```

验证测试通过：

```bash
python -m pytest
```

期望输出：

```text
16 passed
```

验证 schema 可以导出 JSON Schema：

```bash
python -c "from app.schemas import ExecutionPlan; print(ExecutionPlan.model_json_schema()['title'])"
```

期望输出：

```text
ExecutionPlan
```

验证健康检查接口：

```bash
curl http://localhost:8000/health
```

期望输出：

```json
{
  "status": "ok",
  "app_name": "AgentOps Studio",
  "environment": "development",
  "version": "0.1.0"
}
```

## 当前阶段不做什么

为了保证学习节奏，当前步骤不做以下内容：

- 不接入真实大模型 API。
- 不实现 Agent planning。
- 不实现工具调用。
- 不实现 RAG 或数据库。
- 不实现前端页面。

这些内容会在后续步骤逐步添加，每一步都要有明确的测试方式。

## GitHub 远程仓库

当前本地仓库远程地址：

```bash
git remote -v
```

期望看到：

```text
origin  https://github.com/Eternity-G/agentops-studio.git (fetch)
origin  https://github.com/Eternity-G/agentops-studio.git (push)
```

## 下一步

下一步是 **4. Mock 模型适配层**：

- 定义统一模型提供商接口。
- 实现不依赖真实 API key 的 `MockProvider`。
- 让 MockProvider 固定返回符合 `ExecutionPlan` 的结构化计划。
- 编写测试验证 provider 返回结果稳定、字段符合 schema。

## 第 3 步复盘：Pydantic Schema

第 3 步的核心不是“会写几个 BaseModel”，而是为后续 Agent 主链路建立稳定的数据契约。Agent 后续会经历 Planner、Executor、Reflector、Finalizer 等节点，如果没有统一 schema，每个节点都可能传递形状不一致的数据，最终导致调试困难、评测困难、接口文档不稳定。

### 第 3 步已新增的文件

```text
app/
  schemas.py
tests/
  test_schemas.py
```

| 文件 | 作用 |
|---|---|
| `app/schemas.py` | 定义共享 Pydantic schema，不绑定 FastAPI，后续 API、Agent、Eval 都可以复用。 |
| `tests/test_schemas.py` | 用测试锁定 schema 行为，避免后续重构时破坏数据契约。 |

### 当前已定义的 schema

| Schema | 作用 | 后续会被谁使用 |
|---|---|---|
| `TaskInput` | 表示用户输入任务，包含任务正文、可选用户 ID 和 metadata。 | API、Planner、Trace |
| `PlanStep` | 表示计划中的一个可执行步骤，包含步骤 ID、目标、预期输出、工具名、依赖和状态。 | Planner、Executor、Trace |
| `ExecutionPlan` | 表示完整执行计划，负责校验步骤 ID 唯一和依赖存在。 | Planner、Agent Runtime、Eval |
| `Evidence` | 表示最终答案引用的证据来源。 | RAG、Finalizer、Eval |
| `FinalAnswer` | 表示最终结构化答案，包含答案、摘要、完成状态、置信度、证据和下一步建议。 | Finalizer、API、Eval |
| `StepStatus` | 表示步骤状态枚举。 | Executor、Trace、前端展示 |

### 要融入项目的 Pydantic 面试问题

| 面试问题 | 项目中如何体现 | 你需要能讲清楚什么 |
|---|---|---|
| Pydantic 在 FastAPI 中解决什么问题？ | `app/schemas.py` 定义结构化数据，后续可以作为 request/response model。 | Pydantic 负责校验、类型转换、错误报告、JSON Schema 导出。 |
| 为什么 schema 不直接放在路由函数里？ | `TaskInput`、`ExecutionPlan`、`FinalAnswer` 放在共享模块。 | 这些是领域数据契约，不只是 HTTP 入参，Agent 和 Eval 也要复用。 |
| `extra="forbid"` 有什么价值？ | `StrictSchema` 禁止未定义字段。 | 可以及时发现模型输出多字段、拼错字段或调用方传错参数。 |
| 为什么要限制字符串长度？ | `ShortText`、`LongText` 用 `StringConstraints` 限制长度并去空格。 | Agent 系统要控制输入规模，避免无边界数据进入状态和 Trace。 |
| 为什么要校验 step id 唯一？ | `ExecutionPlan` 校验所有 `PlanStep.step_id` 不重复。 | Trace、重试、依赖关系都需要稳定唯一的步骤 ID。 |
| 为什么要校验依赖是否存在？ | `ExecutionPlan` 会拒绝依赖不存在步骤的计划。 | 防止 Executor 运行到一半才发现计划图无效。 |
| 为什么要导出 JSON Schema？ | `ExecutionPlan.model_json_schema()` 已有测试覆盖。 | JSON Schema 可用于 OpenAPI、结构化输出约束和自动化评测。 |
| Pydantic v1 和 v2 写法有什么差异？ | 当前使用 `model_validator`、`model_json_schema()` 和 `ConfigDict`。 | v2 的校验器和 schema API 有变化，面试时要能区分。 |

### 第 3 步测试方式

第 3 步已经覆盖以下测试：

| 测试重点 | 验证什么 |
|---|---|
| 合法 `TaskInput` | 正常任务输入可以创建，并自动去掉首尾空格。 |
| 空任务输入 | 空字符串会在进入 Agent 前被拒绝。 |
| 未知字段 | 未定义字段会被拒绝，防止 schema 漂移。 |
| 合法 `ExecutionPlan` | 多步骤计划可以表达依赖关系。 |
| 重复 step id | 重复步骤 ID 会被拒绝。 |
| 缺失依赖 | 依赖不存在的步骤会被拒绝。 |
| 自依赖步骤 | 步骤不能依赖自己。 |
| 合法 `FinalAnswer` | 最终答案可以携带证据和下一步建议。 |
| 非法置信度 | `confidence` 必须在 0.0 到 1.0 之间。 |
| JSON Schema 导出 | `ExecutionPlan` 可以导出 JSON Schema。 |

建议验证命令：

```bash
python -m pytest
```

### 第 3 步完成后你应该能回答

完成第 3 步后，你至少要能清晰回答：

1. 为什么 Agent 主链路需要稳定 schema？
2. 为什么 schema 不应该只写在 API 层？
3. Pydantic 的 `extra="forbid"` 对 LLM 结构化输出有什么价值？
4. 为什么计划步骤必须有唯一 ID？
5. 为什么要在 schema 层校验依赖关系，而不是等 Executor 执行时报错？
6. JSON Schema 对 OpenAPI、评测和模型结构化输出分别有什么帮助？
7. Pydantic v2 中 `model_validator` 和 `model_json_schema()` 的作用是什么？

## 第 2 步复盘：FastAPI 健康检查

第 2 步没有只把 `/health` 写出来，而是把它设计成一个 FastAPI 面试基础关卡。目标是：你既能运行接口，也能解释 FastAPI 的核心机制、测试方式和工程边界。

### 第 2 步已新增的文件

```text
app/
  api/
    __init__.py
    routes.py
tests/
  test_health.py
```

| 文件 | 作用 |
|---|---|
| `app/api/__init__.py` | 声明 `api` 是 Python 包，后续可以继续放路由、依赖和中间件。 |
| `app/api/routes.py` | 创建 FastAPI 应用实例，并实现 `GET /health`。 |
| `tests/test_health.py` | 使用 FastAPI `TestClient` 测试接口，不需要真的启动网络服务。 |

### 要融入项目的 FastAPI 面试问题

| 面试问题 | 项目中如何体现 | 你需要能讲清楚什么 |
|---|---|---|
| FastAPI 和 Flask 的主要区别是什么？ | 使用类型注解和 Pydantic schema，让接口输入输出可校验、可生成 OpenAPI 文档。 | FastAPI 基于 ASGI，天然支持 async；类型注解能驱动校验、文档和编辑器提示。 |
| ASGI 和 WSGI 有什么区别？ | 用 Uvicorn 启动 FastAPI 应用。 | WSGI 主要面向同步请求；ASGI 支持异步、WebSocket、长连接，更适合 Agent 流式输出。 |
| 为什么需要 `/health`？ | 实现 `GET /health`，返回服务状态、环境、版本号。 | 健康检查用于部署、监控、负载均衡和故障定位，不是业务接口。 |
| FastAPI 如何自动生成接口文档？ | 启动服务后访问 `/docs` 和 `/openapi.json`。 | FastAPI 根据路径函数、类型注解和 response model 生成 OpenAPI。 |
| `TestClient` 有什么价值？ | `tests/test_health.py` 不启动真实端口也能测试接口。 | 单元/集成测试可以直接调用 ASGI app，速度快、稳定、适合 CI。 |
| 路由函数应该返回 dict 还是 Pydantic model？ | 第 2 步可以先返回 dict；后续第 3 步再引入 response schema。 | dict 简单；Pydantic model 更适合结构化输出、文档和长期维护。 |
| 同步函数和异步函数怎么选？ | `/health` 可以用普通 `def`，后续模型调用或工具调用用 `async def`。 | 简单 CPU 逻辑用同步即可；I/O 密集任务适合 async，但不能把阻塞代码直接塞进 async。 |
| 如何管理配置？ | `/health` 从 `load_settings()` 读取 `app_env` 和 `app_name`。 | 路由不直接读环境变量，配置集中在 `settings.py`，方便测试和替换。 |
| API 错误如何处理？ | 第 2 步先保持成功路径；后续任务接口再设计统一错误响应。 | 面试时要说明错误模型、状态码和日志记录会在复杂接口中统一处理。 |
| 为什么健康检查不能做太重？ | `/health` 只检查进程可用和基础配置，不调用模型 API。 | 健康检查应快速、稳定、低成本；深度依赖检查可以放到 `/ready` 或内部诊断接口。 |

### 第 2 步实现标准

`GET /health` 当前返回：

```json
{
  "status": "ok",
  "app_name": "AgentOps Studio",
  "environment": "development",
  "version": "0.1.0"
}
```

字段设计理由：

| 字段 | 理由 |
|---|---|
| `status` | 给监控和测试一个稳定判断条件。 |
| `app_name` | 验证 API 层正确读取了配置。 |
| `environment` | 方便区分 development、test、production。 |
| `version` | 方便排查当前部署的是哪个版本。 |

### 第 2 步测试方式

第 2 步已经包含 3 个健康检查相关测试：

| 测试 | 验证什么 | 通过标准 |
|---|---|---|
| `test_health_status_code` | 路由是否存在 | `GET /health` 返回 200 |
| `test_health_response_body` | 响应结构是否稳定 | JSON 中包含 `status`、`app_name`、`environment`、`version` |
| `test_openapi_contains_health_path` | FastAPI 文档是否识别该路由 | `/openapi.json` 中包含 `/health` |

建议验证命令：

```bash
python -m pytest
```

启动本地服务：

```bash
python -m uvicorn app.api.routes:app --reload
```

手动检查接口：

```bash
curl http://localhost:8000/health
```

手动检查文档：

```text
http://localhost:8000/docs
http://localhost:8000/openapi.json
```

### 第 2 步完成后你应该能回答

完成第 2 步后，你至少要能清晰回答：

1. 为什么 Agent 项目需要一个健康检查接口？

2. 为什么 `/health` 不应该调用真实模型 API？
3. FastAPI 的 OpenAPI 文档是怎么生成的？
4. `TestClient` 为什么可以不启动服务就测试接口？
5. Uvicorn 在 FastAPI 项目中扮演什么角色？
6. ASGI 对后续 Agent 流式输出有什么意义？
7. 路由为什么应该通过 `load_settings()` 读取配置，而不是直接读环境变量？

第 2 步通过后，项目已经进入并完成第 3 步：Pydantic Schema。
