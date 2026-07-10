# 第 13 步：本地 Markdown 文档读取工具

## 本步骤目标

第 13 步让 Agent 第一次具备读取本地资料的能力。

本步骤不做向量数据库、不做 embedding、不做复杂检索，只实现一个边界清晰、可测试、可替换的本地 Markdown 读取工具：`ReadMarkdownTool`。

完成后系统具备以下能力：

- 通过统一 `Tool` 协议读取本地 Markdown 文件。
- 只允许读取工作区内的 `.md` 文件。
- 拒绝目录穿越和非 Markdown 文件。
- 对长文档做输出长度限制，避免工具结果过大。
- 默认工具注册表可以暴露 `read_markdown` 工具。

## 为什么先做 Markdown 工具

后续第 14 步会做“文档问答最小 RAG 链路”。RAG 的第一步不是向量数据库，而是让系统可靠地拿到文档内容。

如果文档读取层不稳定，后面的检索、总结、问答都会变得不可控。

所以第 13 步只解决一个问题：

> Agent 如何安全、可测试地读取一份本地 Markdown 文档？

## 本步骤新增或修改的文件

```text
app/
  tools/
    markdown.py
    __init__.py
    registry.py
tests/
  test_markdown_tool.py
docs/
  第13步-本地Markdown文档读取工具.md
README.md
```

| 文件 | 作用 |
|---|---|
| `app/tools/markdown.py` | 实现 `ReadMarkdownTool`，负责读取受限 Markdown 文件。 |
| `app/tools/__init__.py` | 导出 `ReadMarkdownTool`，方便其他模块统一导入。 |
| `app/tools/registry.py` | 把 `read_markdown` 注册到默认 `MockToolRegistry`。 |
| `tests/test_markdown_tool.py` | 覆盖读取成功、安全边界、截断和注册表暴露。 |
| `README.md` | 更新当前状态、测试数量和下一步计划。 |

## 核心设计

### 1. 只读取 Markdown

工具只允许读取 `.md` 文件。

这样可以避免第 13 步变成任意文件读取工具，也避免误读 `.env`、数据库文件、缓存文件等敏感内容。

### 2. 限制在工作区内

`ReadMarkdownTool` 会把传入路径解析为绝对路径，并检查解析后的路径是否仍在 `base_dir` 内。

这可以拦截类似下面的目录穿越：

```text
../outside.md
```

### 3. 限制输出长度

工具默认最多返回 4000 个字符。

这是为后续模型调用做准备：工具结果如果无限长，会导致 prompt 过大、成本不可控，也会让测试输出难以阅读。

### 4. 先复用 PlanStep.expected_output

当前 `PlanStep` 还没有专门的工具参数字段，所以第 13 步先约定：

```text
PlanStep.expected_output = Markdown 文件路径
```

这只是过渡设计。第 14 步或后续工具调用升级时，可以引入更正式的 `tool_args` schema。

## 可观测验证方式

只运行第 13 步测试：

```bash
python -m pytest tests/test_markdown_tool.py
```

期望结果：

```text
7 passed
```

运行全部测试：

```bash
python -m pytest
```

当前期望结果：

```text
59 passed
```

## 你需要理解的面试问题

### 1. 为什么不能直接让工具读取任意路径？

因为 Agent 工具会被模型间接驱动。如果不限制路径，模型或用户输入可能让系统读取 `.env`、密钥、本地缓存或系统文件。

所以工具必须有清晰边界：

- 限定工作区。
- 限定文件类型。
- 明确失败原因。
- 输出长度受控。

### 2. 为什么读取失败要返回 ToolResult，而不是直接让程序崩溃？

工具失败是 Agent 主链路的一部分，应该被结构化记录。

这样上层 `AgentRuntime` 才能把失败写入 trace，并在 `reflect` 阶段判断任务是否可以继续。

### 3. 为什么现在不做向量数据库？

因为当前目标是学习主链路。

向量数据库、embedding、chunk、rerank 都属于检索增强的后续能力。如果一开始全部引入，会让问题边界变复杂，不利于观察每一步是否正确。

## 下一步

第 14 步：文档问答最小 RAG 链路。

目标是在不引入向量数据库的前提下，用 `ReadMarkdownTool` 读取 Markdown 文档，并让 Agent 基于文档内容回答问题。
