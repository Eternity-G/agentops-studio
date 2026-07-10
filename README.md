# AgentOps Studio

AgentOps Studio 是一个用于学习和构建 Agent 工程系统的项目。目标不是做一个简单聊天机器人，而是逐步搭建一个包含任务规划、模型适配、工具调用、Trace、记忆、评测和部署能力的 Agent 工程平台。

## 当前状态

当前固定路线共 **18 步**，已完成到 **第 13 步：本地 Markdown 文档读取工具**。

已经具备的核心能力：

- FastAPI 服务可以启动，并提供 `GET /health` 和 `POST /tasks/run`。
- Pydantic schema 可以约束任务输入、执行计划、步骤、工具结果和最终答案。
- `MockProvider` 和 `DeepSeekProvider` 已接入统一模型提供商接口。
- `Planner` 可以接收用户任务，调用模型 provider，并返回合法 `ExecutionPlan`。
- `AgentRuntime` 已跑通 `plan -> act -> reflect -> finalize` 的最小主链路。
- 工具层已支持 `MockToolRegistry`，并能把工具失败记录为结构化结果。
- DeepSeek 真实模型可以通过本地 `.env` 启用，不会把 API key 写入 Git。
- 第 12 步已经支持 provider 失败重试、模型输出再校验、失败后 fallback 到 `MockProvider`。
- Agent trace 会记录 provider 尝试、失败、重试和 fallback 事件，方便排查真实模型不稳定问题。
- `ReadMarkdownTool` 可以安全读取工作区内的 `.md` 文件，并限制输出长度。
- 默认工具注册表已经暴露 `read_markdown`，为后续文档问答和 RAG 做准备。

当前还没有实现：

- RAG 或向量数据库。
- 长期记忆系统。
- 自动评测集和评测报告。
- 前端页面。
- 生产部署配置。

## 固定 18 步路线

| 步骤 | 主题 | 状态 |
|---|---|---|
| 1 | 项目骨架与环境 | 已完成 |
| 2 | FastAPI 健康检查 | 已完成 |
| 3 | Pydantic Schema | 已完成 |
| 4 | Mock 模型适配层 | 已完成 |
| 5 | Planner 最小实现 | 已完成 |
| 6 | 状态机主链路 | 已完成 |
| 7 | 基础 Trace 与 API Demo | 已完成 |
| 8 | 工具层与 Mock Tool Registry | 已完成 |
| 9 | 工具调用失败处理与回归测试 | 已完成 |
| 10 | 接入 DeepSeek 大模型 Provider | 已完成 |
| 11 | 用真实 DeepSeek Planner 跑通 API Demo | 已完成 |
| 12 | 模型输出修复、重试与 fallback | 已完成 |
| 13 | 本地 Markdown 文档读取工具 | 已完成 |
| 14 | 文档问答最小 RAG 链路 | 下一步 |
| 15 | 记忆与会话状态 | 未开始 |
| 16 | 评测集与自动评测报告 | 未开始 |
| 17 | 前端 Demo 页面 | 未开始 |
| 18 | 部署、简历材料与项目复盘 | 未开始 |

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

查看接口文档：

```text
http://localhost:8000/docs
http://localhost:8000/openapi.json
```

运行 Agent API Demo：

```bash
curl -X POST http://localhost:8000/tasks/run ^
  -H "Content-Type: application/json" ^
  -d "{\"task\":\"分析一个 Agent 项目的下一步计划\"}"
```

## 当前验证结果

测试命令：

```bash
python -m pytest
```

当前期望结果：

```text
59 passed
```

Planner fallback 验证：

```bash
python -m pytest tests/test_planner_recovery.py
```

期望结果：

```text
4 passed
```

Markdown 工具验证：

```bash
python -m pytest tests/test_markdown_tool.py
```

期望结果：

```text
7 passed
```

## DeepSeek 本地配置

`.env` 只用于本地运行，已经被 `.gitignore` 忽略。不要把真实 API key 写入代码、README、测试或 Git 提交。

本地 `.env` 示例：

```bash
MODEL_PROVIDER=deepseek
DEFAULT_MODEL=deepseek-v4-flash
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_API_KEY=你的本地 API key
```

真实 DeepSeek Planner 验证：

```bash
python scripts/verify_deepseek_planner.py
```

## 学习文档

详细学习记录放在 `docs/` 目录中，每一步一个 Markdown 文件。README 只保留当前状态、路线和验证方式。

## 下一步

第 14 步：文档问答最小 RAG 链路。

目标是在不引入向量数据库的前提下，让 Agent 可以围绕本地 Markdown 文档完成一次最小问答链路。
