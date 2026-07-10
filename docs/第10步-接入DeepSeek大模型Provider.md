# 第 10 步：接入 DeepSeek 大模型 Provider

## 目标

第 10 步的目标是接入真实 DeepSeek 大模型 API，但不破坏现有 mock 测试体系。

当前实现使用 DeepSeek 的 OpenAI-compatible 接口：

```text
BASE URL: https://api.deepseek.com
Endpoint: /chat/completions
```

支持模型：

```text
deepseek-v4-flash
deepseek-v4-pro
```

## 安全说明

真实 API key 只能放在本地 `.env` 或终端环境变量中。

不要把真实 key 写入：

- 代码文件。
- README。
- docs 文档。
- 测试文件。
- Git commit message。

如果 key 已经在聊天、截图或日志中暴露，建议到 DeepSeek 控制台轮换。

## 改动文件

```text
app/
  providers/
    deepseek.py
    factory.py
    __init__.py
  settings.py
tests/
  test_deepseek_provider.py
.env.example
```

## 本地配置

复制环境变量模板：

```bash
cp .env.example .env
```

在 `.env` 中配置：

```bash
MODEL_PROVIDER=deepseek
DEFAULT_MODEL=deepseek-v4-flash
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_API_KEY=你的本地 API key
```

如果想使用更强模型：

```bash
DEFAULT_MODEL=deepseek-v4-pro
```

## 当前实现

`DeepSeekProvider` 做了几件事：

1. 从配置读取 `DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL`、`DEFAULT_MODEL`。
2. 构造 OpenAI-compatible chat completions 请求。
3. 要求模型输出 JSON。
4. 解析 `choices[0].message.content`。
5. 将 JSON 校验为 `ExecutionPlan`。

## 为什么仍保留 MockProvider

真实模型 API 有几个不稳定因素：

- 网络可能失败。
- API key 可能缺失。
- 模型输出可能偶发不符合 schema。
- 调用会产生费用。

因此测试默认仍使用 MockProvider。DeepSeekProvider 的单元测试使用 fake transport，不真实访问网络。

## 可观测验证

运行全部测试：

```bash
python -m pytest
```

当前期望结果：

```text
48 passed
```

验证工厂可以创建 DeepSeekProvider：

```bash
python -c "from app.providers import create_provider; from app.settings import AppSettings; p = create_provider(AppSettings(model_provider='deepseek', default_model='deepseek-v4-flash', deepseek_api_key='test-key')); print(p.info)"
```

期望输出包含：

```text
ProviderInfo(name='deepseek', model='deepseek-v4-flash', is_mock=False)
```

## 测试覆盖

| 测试 | 验证什么 |
|---|---|
| `test_deepseek_provider_requires_api_key` | 没有 API key 时快速失败。 |
| `test_deepseek_provider_returns_execution_plan_from_fake_response` | 能解析 OpenAI-compatible JSON 响应并生成 `ExecutionPlan`。 |
| `test_deepseek_provider_accepts_fenced_json_response` | 即使模型返回 fenced JSON，也能容错解析。 |
| `test_deepseek_factory_uses_settings` | Provider 工厂能根据配置创建 DeepSeekProvider。 |
| `test_deepseek_provider_rejects_invalid_json_response` | 非 JSON 输出会在进入 Planner 前失败。 |

## 面试问题

| 问题 | 回答要点 |
|---|---|
| 为什么选择 OpenAI-compatible 接口？ | 它能统一 DeepSeek、OpenAI、Ollama、vLLM 等调用形状，降低 provider 扩展成本。 |
| 为什么真实 provider 不直接返回字符串？ | 上层 Planner 需要 `ExecutionPlan`，结构化校验能提前发现模型输出错误。 |
| 为什么测试不用真实 DeepSeek API？ | 单元测试应稳定、无费用、无网络依赖；真实 API 验证应放在本地手动或集成测试。 |
| 为什么 key 不能写进仓库？ | API key 是敏感凭据，一旦提交会泄露权限和费用风险。 |
| 模型输出不是合法 JSON 怎么办？ | Provider 会抛出错误，后续步骤可以增加修复、重试和 fallback。 |

## 完成标准

- `DeepSeekProvider` 已实现。
- `create_provider()` 支持 `MODEL_PROVIDER=deepseek`。
- `.env.example` 提供 DeepSeek 配置模板，但不包含真实 key。
- DeepSeekProvider 输出会校验成 `ExecutionPlan`。
- 测试不访问真实 DeepSeek API。
- `python -m pytest` 通过。
