# 第 5 步：Planner 最小实现

## 目标

第 5 步的目标是跑通 Agent 系统的第一条核心链路：

```text
任务输入 -> Planner -> ModelProvider -> ExecutionPlan
```

这个步骤只做任务规划，不做工具调用、不做反思、不做最终答案生成。

## 新增文件

```text
app/
  planner.py
tests/
  test_planner.py
```

## 文件职责

| 文件 | 作用 |
|---|---|
| `app/planner.py` | 定义最小 `Planner`，接收 `TaskInput`，调用 provider，返回 `ExecutionPlan`。 |
| `tests/test_planner.py` | 验证 Planner 默认使用 mock provider，并能返回合法结构化计划。 |

## 核心设计

### Planner 的职责边界

当前 Planner 只负责三件事：

1. 接收已经通过 schema 校验的 `TaskInput`。
2. 调用符合 `ModelProvider` 协议的 provider。
3. 返回经过 `ExecutionPlan` 再校验的结构化计划。

它不负责：

- 调用工具。
- 执行步骤。
- 反思或重规划。
- 生成最终答案。
- 直接调用 OpenAI、DeepSeek、通义千问或 Ollama SDK。

这些边界很重要。Planner 如果过早承担太多职责，后续 Agent 主链路会变得难拆、难测、难替换。

### 为什么 Planner 依赖 provider 接口

Planner 不知道具体模型来自哪里。它只知道 provider 能执行：

```python
async def create_plan(task_input: TaskInput) -> ExecutionPlan:
    ...
```

这样后续从 `MockProvider` 切换到 OpenAI、DeepSeek、通义千问或 Ollama 时，Planner 不需要改业务逻辑。

### 为什么还要重新校验 provider 输出

虽然 `ModelProvider` 声明返回 `ExecutionPlan`，但真实模型 provider 后续很可能先拿到 JSON，再转成 Pydantic 对象。

Planner 再做一次：

```python
ExecutionPlan.model_validate(plan.model_dump())
```

可以确保 Planner 对外输出永远是合法计划。这个校验边界对后续真实模型接入很重要。

## 可观测验证

运行全部测试：

```bash
python -m pytest
```

当前期望结果：

```text
26 passed
```

手动验证 Planner：

```bash
python -c "import asyncio; from app.planner import Planner; plan = asyncio.run(Planner().create_plan_from_text('生成计划')); print(type(plan).__name__, len(plan.steps), plan.steps[0].goal)"
```

期望输出包含：

```text
ExecutionPlan 3 理解用户任务
```

## 测试覆盖

| 测试 | 验证什么 |
|---|---|
| `test_planner_uses_mock_provider_by_default` | Planner 默认不需要真实 API key，使用 mock provider。 |
| `test_planner_creates_execution_plan_from_task_input` | Planner 能把 `TaskInput` 转成 `ExecutionPlan`。 |
| `test_planner_create_plan_from_text_helper` | Planner 提供便于演示和学习的文本入口。 |
| `test_planner_output_round_trips_through_execution_plan_schema` | Planner 输出可以序列化并重新通过 schema 校验。 |

## 面试问题

| 问题 | 回答要点 |
|---|---|
| Planner 在 Agent 系统中负责什么？ | 把用户任务拆成结构化计划，不负责执行和工具调用。 |
| 为什么 Planner 不直接调用 OpenAI SDK？ | 直接绑定厂商会让后续切换模型、测试和 fallback 变困难。 |
| 为什么 Planner 要依赖 `ModelProvider` 协议？ | 这样 MockProvider 和真实 provider 可以无缝替换。 |
| 为什么 Planner 输入是 `TaskInput` 而不是普通字符串？ | `TaskInput` 已经完成校验，后续还能承载 user_id、metadata、trace 信息。 |
| 为什么 Planner 输出是 `ExecutionPlan`？ | 后续 Executor、Trace、Eval 都需要稳定结构，而不是自然语言计划。 |
| 为什么 Planner 暂时不做工具调用？ | 工具调用属于 Executor 阶段，当前步骤只跑通规划链路，降低学习复杂度。 |

## 完成标准

- `Planner` 已实现。
- 默认不配置 API key 也能工作。
- Planner 可以调用 `MockProvider`。
- Planner 返回合法 `ExecutionPlan`。
- `python -m pytest` 通过。
