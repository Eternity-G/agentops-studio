# 第 12 步：模型输出修复、重试与 fallback

## 本步骤目标

第 12 步解决真实大模型接入后最常见的问题：模型调用不一定稳定，输出也不一定永远符合我们定义好的 schema。

本步骤完成后，`Planner` 不再只是假设 provider 一定成功，而是具备三层保护：

1. 对 provider 返回结果做 `ExecutionPlan` 再校验。
2. 当 provider 抛出异常时，按配置进行重试。
3. 如果真实 provider 多次失败，则 fallback 到 `MockProvider`，保证主链路仍然可观测、可测试。

## 为什么需要这一步

真实模型在工程中常见的失败包括：

- 返回非 JSON 文本。
- 返回 JSON，但字段缺失或类型错误。
- 网络超时、限流、服务端错误。
- API key、base URL 或模型名配置错误。
- 模型输出符合自然语言表达，但不符合业务 schema。

Agent 系统不能把这些问题隐藏起来。正确做法是：

- 失败要被捕获。
- 重试次数要受控。
- fallback 要可观测。
- trace 要记录每次 provider 尝试。
- 单元测试不能依赖真实外部 API。

## 本步骤新增或修改的文件

```text
app/
  planner.py
  agent.py
tests/
  test_planner_recovery.py
docs/
  第12步-模型输出修复重试与fallback.md
README.md
```

| 文件 | 作用 |
|---|---|
| `app/planner.py` | 增加 provider 尝试记录、重试、fallback 和输出再校验。 |
| `app/agent.py` | 把 Planner 的 provider 尝试结果写入 Agent trace。 |
| `tests/test_planner_recovery.py` | 覆盖重试、fallback、全部失败和 trace 记录。 |
| `README.md` | 更新当前状态、固定 18 步路线和验证方式。 |

## 核心设计

### 1. ProviderAttempt

`ProviderAttempt` 用来记录一次 provider 调用结果：

- `provider_name`：provider 名称，例如 `deepseek` 或 `mock`。
- `model`：模型名。
- `attempt`：第几次尝试。
- `success`：本次是否成功。
- `error`：失败原因。
- `used_fallback`：是否来自 fallback provider。

这不是业务 schema，而是运行时可观测性数据，主要用于 trace 和调试。

### 2. Planner 重试

`Planner` 默认 `max_retries=1`。

这意味着主 provider 最多会被调用两次：

1. 第一次正常调用。
2. 第一次失败后再重试一次。

如果两次都失败，才会进入 fallback provider。

### 3. Planner fallback

默认 fallback provider 是 `MockProvider`。

这样设计的原因是：当真实模型输出坏 JSON、schema 不合法或接口失败时，项目主链路仍然能继续运行，便于学习、调试和演示。

注意：fallback 不代表真实模型成功了。trace 中会明确记录：

```text
provider failing/broken-model attempt 1 failed
provider failing/broken-model attempt 2 failed
provider mock/fallback-mock attempt 1 succeeded with fallback
```

### 4. 输出再校验

虽然 provider 协议声明返回 `ExecutionPlan`，但 `Planner` 仍然会再次执行：

```python
ExecutionPlan.model_validate(plan.model_dump())
```

这样做是为了在 Planner 边界上保证：对外返回的一定是合法 `ExecutionPlan`。

## 测试设计

本步骤新增 4 个回归测试。

| 测试 | 验证内容 |
|---|---|
| `test_planner_retries_after_provider_failure` | provider 第一次失败、第二次成功时，Planner 能重试并返回计划。 |
| `test_planner_falls_back_to_mock_after_retries_fail` | 主 provider 多次失败后，Planner 能 fallback 到 `MockProvider`。 |
| `test_planner_raises_when_primary_and_fallback_fail` | 主 provider 和 fallback provider 都失败时，返回清晰错误。 |
| `test_agent_trace_records_provider_retry_and_fallback` | Agent trace 能记录 provider 失败、重试和 fallback。 |

## 可观测验证方式

只运行第 12 步测试：

```bash
python -m pytest tests/test_planner_recovery.py
```

期望结果：

```text
4 passed
```

运行全部测试：

```bash
python -m pytest
```

当前期望结果：

```text
52 passed
```

## 面试时可以这样解释

如果面试官问：真实大模型输出不稳定怎么办？

可以回答：

> 我会把模型接入层和业务链路解耦。Provider 负责调用模型并尽量转成结构化 schema，Planner 在边界处再次校验输出。如果 provider 失败，会按有限次数重试；如果仍失败，会 fallback 到 MockProvider 或其他备用 provider。同时把每次 provider 尝试写入 trace，避免系统静默降级。

如果面试官继续问：fallback 会不会掩盖真实错误？

可以回答：

> 不会。fallback 只保证主链路可运行，但 trace 会明确记录 primary provider 的失败原因、重试次数和 fallback 事件。监控或评测系统可以根据 trace 判断本次结果是否来自真实模型。

## 下一步

第 13 步：本地 Markdown 文档读取工具。

目标是让 Agent 第一次具备读取本地资料的能力，为后续文档问答和 RAG 做准备。
