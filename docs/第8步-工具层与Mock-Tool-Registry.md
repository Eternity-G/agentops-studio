# 第 8 步：工具层与 Mock Tool Registry

## 目标

第 8 步的目标是定义统一工具接口，实现 mock 工具注册表，并让 `AgentRuntime` 的 `act` 阶段通过工具层生成步骤结果。

当前仍然不接真实搜索、SQL、Python 或 MCP。先把工具层边界跑通，后续再替换成真实工具。

## 新增文件

```text
app/
  tools/
    __init__.py
    base.py
    mock.py
    registry.py
tests/
  test_tools.py
```

## 文件职责

| 文件 | 作用 |
|---|---|
| `app/tools/base.py` | 定义 `Tool` 协议、`ToolDefinition` 和 `ToolResult`。 |
| `app/tools/mock.py` | 实现 `MockStepTool`，把 `PlanStep` 转成成功的 `ToolResult`。 |
| `app/tools/registry.py` | 实现 `ToolRegistry` 和 `MockToolRegistry`。 |
| `app/tools/__init__.py` | 暴露工具层公共入口。 |
| `tests/test_tools.py` | 验证工具注册、工具定义、默认工具、命名工具和未知工具失败结果。 |

## 当前工具结构

| 结构 | 作用 |
|---|---|
| `ToolDefinition` | 工具元信息，包含名称、描述和输入 schema。 |
| `ToolResult` | 工具执行结果，包含工具名、状态和输出。 |
| `Tool` | 所有工具都要实现的协议。 |
| `MockStepTool` | 确定性 mock 工具，不访问外部系统。 |
| `ToolRegistry` | 注册工具并按名称执行 `PlanStep`。 |
| `MockToolRegistry` | 默认注册 `mock_step` 和 `planner` 两个 mock 工具。 |

## AgentRuntime 变化

第 8 步之前，`AgentRuntime._act()` 直接拼接字符串生成步骤结果。

现在流程变成：

```text
PlanStep -> ToolRegistry.execute_step() -> ToolResult -> StepExecutionResult
```

这样后续接入真实工具时，只需要新增工具实现并注册到 registry，而不是重写 Agent 主链路。

## 当前工具路由规则

| PlanStep 情况 | 使用哪个工具 |
|---|---|
| `tool_name is None` | 使用默认工具 `mock_step`。 |
| `tool_name == "planner"` | 使用注册表里的 `planner` mock 工具。 |
| `tool_name` 未注册 | 返回 `FAILED` 的 `ToolResult`，输出中包含 `unknown tool`。 |

## 可观测验证

运行全部测试：

```bash
python -m pytest
```

当前期望结果：

```text
40 passed
```

手动验证工具注册表：

```bash
python -c "from app.tools import MockToolRegistry; registry = MockToolRegistry(); print([tool.name for tool in registry.list_definitions()])"
```

期望输出包含：

```text
['mock_step', 'planner']
```

手动验证 AgentRuntime 使用工具层：

```bash
python -c "import asyncio; from app.agent import AgentRuntime; state = asyncio.run(AgentRuntime().run_from_text('demo')); print([(r.step_id, r.tool_name, r.status) for r in state.step_results])"
```

期望输出包含：

```text
(1, 'mock_step', <StepStatus.COMPLETED: 'completed'>)
(2, 'planner', <StepStatus.COMPLETED: 'completed'>)
(3, 'mock_step', <StepStatus.COMPLETED: 'completed'>)
```

## 测试覆盖

| 测试 | 验证什么 |
|---|---|
| `test_mock_step_tool_returns_completed_result` | MockStepTool 能把步骤转为成功结果。 |
| `test_tool_registry_lists_tool_definitions` | Registry 能暴露工具名称、描述和输入 schema。 |
| `test_tool_registry_executes_default_tool_when_step_has_no_tool_name` | 无工具名步骤走默认工具。 |
| `test_tool_registry_executes_named_tool` | 指定工具名步骤能路由到命名工具。 |
| `test_tool_registry_rejects_duplicate_tool_names` | 重复工具名会尽早失败。 |
| `test_tool_registry_returns_failed_result_for_unknown_tool` | 未知工具返回可解释失败结果。 |

## 面试问题

| 问题 | 回答要点 |
|---|---|
| 为什么需要工具注册表？ | Agent 不能把工具调用写死在主链路里，注册表让工具可发现、可替换、可测试。 |
| ToolDefinition 有什么价值？ | 后续可以用于 LLM tool prompt、OpenAPI 文档、权限控制和调试面板。 |
| 为什么 ToolResult 要结构化？ | 结构化结果便于 Trace、Eval、失败分类和前端展示。 |
| 为什么未知工具不直接崩溃？ | 当前 Registry 返回失败结果，Agent 后续可以决定重试、降级或进入反思。 |
| 第 8 步和第 6 步的 act 有什么区别？ | 第 6 步 act 是硬编码 mock；第 8 步 act 通过工具层执行。 |
| 后续真实工具如何接入？ | 实现 `Tool` 协议，提供 `ToolDefinition` 和 `run()`，再注册到 `ToolRegistry`。 |

## 完成标准

- `Tool` 协议已定义。
- `ToolDefinition` 和 `ToolResult` 已定义。
- `MockToolRegistry` 已实现。
- `AgentRuntime._act()` 通过工具层生成 step result。
- 未知工具能返回可解释失败结果。
- `python -m pytest` 通过。
