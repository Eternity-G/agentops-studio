# 第 4 步：Mock 模型适配层

## 目标

第 4 步的目标是承接第 3 步的 `ExecutionPlan`、`PlanStep`、`TaskInput` 等 schema，建立统一模型适配层。

这个步骤不接真实模型 API。它只实现 `MockProvider`，用于在没有 OpenAI、DeepSeek、通义千问、Ollama API key 的情况下稳定地产生结构化计划。

## 新增文件

```text
app/
  providers/
    __init__.py
    base.py
    factory.py
    mock.py
tests/
  test_providers.py
```

## 文件职责

| 文件 | 作用 |
|---|---|
| `app/providers/__init__.py` | 暴露 provider 层公共入口。 |
| `app/providers/base.py` | 定义 `ModelProvider` 协议和 `ProviderInfo` 元信息。 |
| `app/providers/factory.py` | 根据配置创建 provider，目前只支持 `mock`。 |
| `app/providers/mock.py` | 实现不依赖真实模型 API 的 `MockProvider`。 |
| `tests/test_providers.py` | 验证 provider 接口、MockProvider 输出和工厂函数行为。 |

## 核心设计

### 为什么需要模型适配层

后续项目可能接入 OpenAI、DeepSeek、通义千问、Ollama 或本地 vLLM/SGLang。如果业务代码直接调用某个厂商 SDK，后面切换模型会非常痛苦。

模型适配层的作用是把两件事隔离开：

- 上层业务只关心“给我一个结构化计划”。
- 下层 provider 负责“具体如何调用某个模型服务”。

这样 Planner 后续只依赖 `ModelProvider` 接口，而不是依赖某个具体厂商。

### 为什么接口设计成 async

真实模型调用本质上是网络 I/O。即使当前 `MockProvider` 不访问网络，接口也设计成：

```python
async def create_plan(self, task_input: TaskInput) -> ExecutionPlan:
    ...
```

这样后续接真实模型时，不需要大规模修改 Planner 和 Agent 主链路的函数签名。

### 为什么 MockProvider 必须确定性输出

MockProvider 的目标不是“模拟模型聪明”，而是“稳定地产生合法结构”。同一个任务返回同样形状的计划，可以让测试稳定、学习路径清晰。

当前 MockProvider 固定返回 3 个步骤：

1. 理解用户任务。
2. 拆解执行步骤。
3. 检查计划完整性。

这 3 个步骤都符合 `ExecutionPlan` 和 `PlanStep` 的 schema。

## 可观测验证

运行全部测试：

```bash
python -m pytest
```

当前期望结果：

```text
22 passed
```

手动验证 MockProvider：

```bash
python -c "import asyncio; from app.providers import create_provider; from app.schemas import TaskInput; provider = create_provider(); plan = asyncio.run(provider.create_plan(TaskInput(task='生成计划'))); print(provider.info); print(type(plan).__name__, len(plan.steps))"
```

期望输出包含：

```text
ProviderInfo(name='mock', model='mock-planner-v1', is_mock=True)
ExecutionPlan 3
```

## 测试覆盖

| 测试 | 验证什么 |
|---|---|
| `test_mock_provider_exposes_provider_info` | MockProvider 暴露稳定元信息。 |
| `test_mock_provider_matches_model_provider_protocol` | MockProvider 满足 `ModelProvider` 协议。 |
| `test_mock_provider_returns_execution_plan` | MockProvider 返回合法 `ExecutionPlan`。 |
| `test_mock_provider_output_can_round_trip_through_schema` | provider 输出可以序列化并重新通过 schema 校验。 |
| `test_create_provider_uses_settings_default_model` | 工厂函数能读取配置中的默认模型。 |
| `test_create_provider_rejects_unknown_provider` | 未知 provider 会尽早失败。 |

## 面试问题

| 问题 | 回答要点 |
|---|---|
| 为什么需要 provider adapter？ | 隔离业务逻辑和厂商 SDK，方便切换 OpenAI、DeepSeek、通义千问、Ollama。 |
| 为什么不直接在 Planner 里调 OpenAI SDK？ | 会让 Planner 绑定具体厂商，难测试、难替换、难做 fallback。 |
| 为什么 MockProvider 也要实现同一个接口？ | 这样后续真实 provider 和 mock provider 可以无缝替换。 |
| 为什么 provider 接口是 async？ | 真实模型调用是网络 I/O，async 更适合后续并发和流式场景。 |
| provider 返回字符串还是 schema？ | 当前返回 `ExecutionPlan`，让结构化约束尽早生效，避免上层解析散文。 |
| 工厂函数有什么价值？ | 把 provider 选择逻辑集中在一个地方，后续扩展真实模型时不污染业务代码。 |
| 未知 provider 为什么要抛错？ | 配置错误应尽早暴露，而不是等 Agent 运行中途失败。 |

## 完成标准

- `ModelProvider` 协议已定义。
- `MockProvider` 已实现。
- `create_provider()` 可以根据配置创建 provider。
- MockProvider 不需要真实 API key。
- MockProvider 返回值通过 `ExecutionPlan` 校验。
- `python -m pytest` 通过。
