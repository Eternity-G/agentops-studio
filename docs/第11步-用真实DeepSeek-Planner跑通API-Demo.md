# 第 11 步：用真实 DeepSeek Planner 跑通 API Demo

## 目标

第 11 步的目标是让本地项目真正使用 DeepSeek 大模型生成 `ExecutionPlan`，并通过现有 Planner 和 API Demo 跑通真实模型规划链路。

## 本地 `.env`

本步骤需要本地 `.env` 文件。`.env` 已经被 `.gitignore` 忽略，不会提交到仓库。

推荐配置：

```bash
APP_NAME=AgentOps Studio
APP_ENV=development
APP_DEBUG=true

MODEL_PROVIDER=deepseek
DEFAULT_MODEL=deepseek-v4-flash
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_API_KEY=你的本地 API key
```

不要把真实 API key 写入 Git。

## 新增能力

| 能力 | 说明 |
|---|---|
| `.env` 自动加载 | `load_settings()` 会读取本地 `.env`，无需手动 export 环境变量。 |
| DeepSeek Planner 手动验证 | `scripts/verify_deepseek_planner.py` 可以调用真实 DeepSeek API。 |
| API Demo 复用真实 provider | `POST /tasks/run` 会通过 `Planner -> DeepSeekProvider` 生成真实计划。 |

## 本地验证结果

已验证 `scripts/verify_deepseek_planner.py` 可以返回真实 DeepSeek 生成的 `ExecutionPlan`。

示例输出：

```text
provider=deepseek
model=deepseek-v4-flash
```

已验证 `POST /tasks/run` 可以通过真实 DeepSeek Planner 跑通 API Demo，返回：

```text
completed
plan.steps = 5
trace_events = 8
```

## 验证方式

先确认配置读取正确：

```bash
python -c "from app.settings import load_settings; s=load_settings(); print(s.model_provider, s.default_model, bool(s.deepseek_api_key))"
```

期望输出：

```text
deepseek deepseek-v4-flash True
```

手动调用真实 DeepSeek Planner：

```bash
python scripts/verify_deepseek_planner.py
```

启动 API：

```bash
python -m uvicorn app.api.routes:app --reload
```

调用 API Demo：

```bash
curl -X POST http://localhost:8000/tasks/run ^
  -H "Content-Type: application/json" ^
  -d "{\"task\":\"请为 AgentOps Studio 生成一个三步以内的实施计划\"}"
```

## 注意事项

- 真实 API 调用会产生费用。
- 网络失败、余额不足、key 错误都会导致 provider 抛错。
- 单元测试仍然不访问真实 DeepSeek API，保证 CI 稳定。
- 如果真实模型输出不是合法 JSON，DeepSeekProvider 会报错；后续可以增加修复和重试策略。
