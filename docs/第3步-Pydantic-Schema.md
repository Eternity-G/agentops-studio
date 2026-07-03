# 第 3 步：Pydantic Schema

## 目标

第 3 步的目标是为后续 Agent 主链路准备稳定的数据结构，包括任务输入、计划、步骤、证据和最终答案 schema。

这个步骤只定义数据契约，不实现模型调用、Planner、Executor 或工具调用。

## 新增文件

```text
app/
  schemas.py
tests/
  test_schemas.py
```

## 当前 Schema

| Schema | 作用 | 后续会被谁使用 |
|---|---|---|
| `TaskInput` | 表示用户输入任务，包含任务正文、可选用户 ID 和 metadata。 | API、Planner、Trace |
| `PlanStep` | 表示计划中的一个可执行步骤，包含步骤 ID、目标、预期输出、工具名、依赖和状态。 | Planner、Executor、Trace |
| `ExecutionPlan` | 表示完整执行计划，校验步骤 ID 唯一和依赖存在。 | Planner、Agent Runtime、Eval |
| `Evidence` | 表示最终答案引用的证据来源。 | RAG、Finalizer、Eval |
| `FinalAnswer` | 表示最终结构化答案，包含答案、摘要、完成状态、置信度、证据和下一步建议。 | Finalizer、API、Eval |
| `StepStatus` | 表示步骤状态枚举。 | Executor、Trace、前端展示 |

## 核心设计

### 为什么 schema 不放在 API 层

这些结构不是单纯的 HTTP 请求体。后续 Planner、Executor、Finalizer、Trace、Eval 都要复用它们。因此它们放在 `app/schemas.py`，作为项目共享的数据契约。

### 为什么使用 `extra="forbid"`

Agent 项目里，很多结构化数据会来自 LLM 输出。如果允许未知字段悄悄进入系统，模型字段拼错、多字段、少字段都可能被忽略。`extra="forbid"` 可以让这些问题尽早暴露。

### 为什么要校验步骤依赖

`ExecutionPlan` 会校验：

- `step_id` 不能重复。
- `depends_on` 必须指向已存在步骤。
- `PlanStep` 不能依赖自己。

这样可以在计划生成阶段就发现无效计划，而不是等 Executor 执行到一半才失败。

## 可观测验证

运行测试：

```bash
python -m pytest
```

验证 JSON Schema 导出：

```bash
python -c "from app.schemas import ExecutionPlan; print(ExecutionPlan.model_json_schema()['title'])"
```

期望输出：

```text
ExecutionPlan
```

## 测试覆盖

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

## 面试问题

| 问题 | 回答要点 |
|---|---|
| Pydantic 在 FastAPI 中解决什么问题？ | 校验、类型转换、错误报告、JSON Schema 导出。 |
| 为什么 Agent 主链路需要稳定 schema？ | Planner、Executor、Finalizer、Eval 都需要一致的数据结构，否则调试和评测会失控。 |
| 为什么 schema 不应该只写在 API 层？ | 这些结构会被 API、Agent Runtime、Eval 复用，是领域数据契约。 |
| `extra="forbid"` 对 LLM 输出有什么价值？ | 防止模型输出未知字段或拼错字段时被静默接受。 |
| 为什么计划步骤必须有唯一 ID？ | Trace、重试、依赖关系和前端展示都需要稳定引用步骤。 |
| 为什么要在 schema 层校验依赖关系？ | 越早发现无效计划，越容易定位问题，避免 Executor 执行中途失败。 |
| JSON Schema 有什么价值？ | 可用于 OpenAPI、LLM 结构化输出约束和自动化评测。 |
| Pydantic v2 有哪些常用 API？ | 当前使用 `ConfigDict`、`model_validator`、`model_json_schema()`。 |

## 完成标准

- `TaskInput`、`PlanStep`、`ExecutionPlan`、`Evidence`、`FinalAnswer` 已定义。
- 无效任务、无效计划、无效置信度会被拒绝。
- `ExecutionPlan` 可以导出 JSON Schema。
- `python -m pytest` 通过。
