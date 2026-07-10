# 第 14 步：文档问答最小 RAG 链路

## 本步骤目标

第 14 步把第 13 步的 `ReadMarkdownTool` 连接成一个可以通过 HTTP 调用的最小文档问答链路。

本步骤暂不引入向量数据库、embedding、rerank 或复杂 prompt，只实现最小可观测流程：

```text
问题 + Markdown 路径 -> 读取文档 -> 抽取相关片段 -> 返回结构化答案和证据
```

这一步的重点不是追求答案质量，而是让 RAG 的工程边界先跑通。

## 本步骤新增或修改的文件

```text
app/
  document_qa.py
  schemas.py
  api/
    routes.py
tests/
  test_document_qa.py
docs/
  第14步-文档问答最小RAG链路.md
README.md
```

| 文件 | 作用 |
|---|---|
| `app/document_qa.py` | 实现 `MarkdownQuestionAnswerer`，负责读取文档、选择片段并生成结构化答案。 |
| `app/schemas.py` | 增加 `DocumentQuestionInput` 和 `DocumentQuestionAnswer`。 |
| `app/api/routes.py` | 增加 `POST /documents/ask` API。 |
| `tests/test_document_qa.py` | 覆盖文档问答 runtime、API 和 OpenAPI 文档。 |
| `README.md` | 更新当前状态、测试数量和下一步计划。 |

## 核心链路

### 1. 输入 schema

`DocumentQuestionInput` 包含两个字段：

- `question`：用户对文档提出的问题。
- `path`：工作区内的 Markdown 文件路径。

这让 API 请求保持明确，不让模型自由决定要读哪个系统文件。

### 2. 文档读取

`MarkdownQuestionAnswerer` 不直接读文件，而是复用第 13 步的 `ReadMarkdownTool`。

这样可以继续复用已有安全边界：

- 只能读取 `.md` 文件。
- 路径必须留在工作区内。
- 输出长度受控。

### 3. 最小检索

当前没有使用 embedding。

`MarkdownQuestionAnswerer` 会把 Markdown 按段落拆分，然后用简单关键词评分选出最相关片段。如果没有明显命中，则返回文档第一个非空段落。

这不是最终检索方案，但它有两个优点：

- 不依赖外部服务，测试稳定。
- 可以清楚观察“读取 -> 检索 -> 回答”的链路边界。

### 4. 结构化答案

返回的 `DocumentQuestionAnswer` 包含：

- `question`：原始问题。
- `answer`：基于片段生成的确定性答案。
- `source_path`：来源 Markdown 路径。
- `excerpt`：被选中的文档片段。
- `completed`：链路是否完成。
- `evidence`：证据列表，包含来源和引用片段。

## API

启动服务：

```bash
python -m uvicorn app.api.routes:app --reload
```

调用文档问答：

```bash
curl -X POST http://localhost:8000/documents/ask ^
  -H "Content-Type: application/json" ^
  -d "{\"question\":\"第 13 步实现了什么？\",\"path\":\"docs/第13步-本地Markdown文档读取工具.md\"}"
```

查看接口文档：

```text
http://localhost:8000/docs
```

## 可观测验证方式

只运行第 14 步测试：

```bash
python -m pytest tests/test_document_qa.py
```

期望结果：

```text
6 passed
```

运行全部测试：

```bash
python -m pytest
```

当前期望结果：

```text
65 passed
```

## 你需要理解的面试问题

### 1. 这一步算不算完整 RAG？

不算完整 RAG。

它是最小 RAG 工程链路：先把文档读取、片段选择、答案结构和 API 边界跑通。

完整 RAG 还需要：

- 文档切分。
- embedding。
- 向量数据库。
- 相似度检索。
- rerank。
- 大模型基于证据生成答案。
- 引用和评测。

### 2. 为什么不直接上向量数据库？

因为项目是学习型工程项目。

直接上向量数据库会同时引入存储、索引、召回质量、embedding 成本和部署复杂度。第 14 步先证明问答链路成立，第 16 步评测前再考虑升级检索质量。

### 3. 为什么答案要带 evidence？

Agent 项目的答案必须可追踪。

如果答案没有证据来源，后续就很难做评测、纠错和用户信任建设。即使现在只是简单片段，也应该从一开始保留证据结构。

## 下一步

第 15 步：记忆与会话状态。

目标是保存一次会话中的任务、文档问答结果和关键上下文，为多轮交互做准备。
