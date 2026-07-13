# 企业级代码仓库问答与代码理解 Agent 设计

## 项目背景

企业研发团队的代码仓库通常存在这些问题：

- 新人上手慢，需要花大量时间理解目录结构、核心模块和启动方式。
- 老项目文档过期，真实业务逻辑只能从代码中还原。
- PR Review 成本高，Reviewer 需要快速判断影响范围和测试是否充分。
- 线上问题排查慢，需要快速定位日志、接口、配置和代码路径。

因此，本项目从通用 Agent 学习平台升级为代码仓库问答与代码理解 Agent。

目标是：

```text
让研发人员可以对真实代码仓库提问，并得到带文件路径、行号和证据片段的答案。
```

## 真实应用场景

| 场景 | 用户问题 | 系统能力 |
|---|---|---|
| 新人 onboarding | 这个项目有哪些模块？如何启动？ | 仓库扫描、关键文件识别、前后端信号识别 |
| 功能定位 | 登录逻辑在哪里实现？ | 关键词搜索、代码证据返回 |
| 代码解释 | AgentRuntime 的主流程是什么？ | 搜索类/函数、读取片段、生成证据答案 |
| 影响分析 | 修改 app/schemas.py 会影响哪里？ | 引用搜索、影响区域、测试建议 |
| PR Review | 当前 diff 有哪些风险？ | 变更文件、风险点、测试建议 |

## 为什么暂不主打代码生成

企业内部代码工具首先要可信。

相比自动生成代码，代码理解、影响分析和 PR Review 更容易真实落地，因为它们：

- 风险更低。
- 更容易用证据验证。
- 更符合研发团队日常工作。
- 不会绕过人工审批。

后续可以增加“生成修改建议”，但不建议直接自动改文件和提交 PR。

## 核心架构

```text
用户问题
-> CodebaseQuestionAnswerer
-> RepositoryScanner
-> CodeSearcher
-> CodeFileReader
-> PythonSymbolAnalyzer
-> Evidence
-> CodebaseAnswer
```

## 核心模块

### RepositoryScanner

扫描仓库结构，输出：

- 文件数量。
- 可分析文件数量。
- 代码行数。
- 顶层目录。
- 关键文件。
- 语言分布。
- 前端信号。
- 后端信号。

### CodeSearcher

对仓库中的白名单文件做关键词搜索，返回：

- 文件路径。
- 行号。
- 命中的代码行。

### CodeFileReader

安全读取代码文件。

安全规则：

- 只能读取工作区内仓库。
- 只能读取白名单扩展名。
- 拒绝 `.env` 和 `.env.*`。
- 跳过 `.git`、`node_modules`、构建目录和缓存目录。
- 限制输出长度。

### PythonSymbolAnalyzer

使用 Python 标准库 `ast` 提取：

- class。
- function。
- method。
- import。

这让系统不仅能关键词搜索，也能结构化理解 Python 代码。

### CodebaseQuestionAnswerer

负责把搜索、读取、摘要和证据拼成回答。

回答必须包含：

- 问题。
- 结论。
- 仓库路径。
- 搜索词。
- 文件路径。
- 行号。
- 代码片段。
- 风险提示。

### Impact Analysis

对目标文件做静态影响分析：

- 搜索文件路径。
- 搜索模块路径。
- 搜索文件名。
- 找到引用方。
- 给出可能影响区域。
- 给出测试建议。

### Diff Review

读取当前 git diff，输出：

- 变更文件。
- 改动摘要。
- 风险点。
- 测试建议。
- 代码证据。

## API

```text
POST /codebase/summary
POST /codebase/search
POST /codebase/symbols
POST /codebase/ask
POST /codebase/impact
POST /codebase/review-diff
```

## 可观测验证

运行测试：

```bash
python -m pytest tests/test_codebase.py
```

运行完整测试：

```bash
python -m pytest
```

运行评测：

```bash
python scripts/run_evals.py
```

## 企业级判断标准

这个项目不像 Demo 的关键点：

- 可以分析真实本地仓库，而不是固定文档。
- 返回代码证据，而不是只返回自然语言。
- 有安全边界，避免读取敏感文件。
- 有影响分析和 Diff Review，贴近研发工作流。
- 有自动评测和回归测试。
- 有 FastAPI、前端页面和 Docker 部署材料。
