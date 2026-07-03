# 第 2 步：FastAPI 健康检查

## 目标

第 2 步的目标是实现最小 FastAPI 服务和 `GET /health` 健康检查接口。这个步骤不实现业务接口，也不调用模型 API。

## 新增文件

```text
app/
  api/
    __init__.py
    routes.py
tests/
  test_health.py
```

## 文件职责

| 文件 | 作用 |
|---|---|
| `app/api/__init__.py` | 声明 `api` 是 Python 包，后续可放路由、依赖和中间件。 |
| `app/api/routes.py` | 创建 FastAPI 应用，并实现 `GET /health`。 |
| `tests/test_health.py` | 使用 `TestClient` 测试接口，不需要真的启动网络端口。 |

## 当前接口

`GET /health` 返回：

```json
{
  "status": "ok",
  "app_name": "AgentOps Studio",
  "environment": "development",
  "version": "0.1.0"
}
```

字段说明：

| 字段 | 理由 |
|---|---|
| `status` | 给监控和测试一个稳定判断条件。 |
| `app_name` | 验证 API 层正确读取配置。 |
| `environment` | 区分 development、test、production。 |
| `version` | 排查当前运行的项目版本。 |

## 可观测验证

运行测试：

```bash
python -m pytest
```

启动服务：

```bash
python -m uvicorn app.api.routes:app --reload
```

检查健康接口：

```bash
curl http://localhost:8000/health
```

检查自动文档：

```text
http://localhost:8000/docs
http://localhost:8000/openapi.json
```

## 测试覆盖

| 测试 | 验证什么 |
|---|---|
| `test_health_status_code` | `GET /health` 返回 200。 |
| `test_health_response_body` | 响应包含稳定字段。 |
| `test_openapi_contains_health_path` | `/openapi.json` 中包含 `/health`。 |

## 面试问题

| 问题 | 回答要点 |
|---|---|
| FastAPI 和 Flask 的主要区别是什么？ | FastAPI 基于 ASGI，支持 async；类型注解可以驱动校验、文档和编辑器提示。 |
| ASGI 和 WSGI 有什么区别？ | WSGI 面向同步请求；ASGI 支持异步、WebSocket、长连接，更适合后续 Agent 流式输出。 |
| 为什么需要 `/health`？ | 健康检查用于部署、监控、负载均衡和故障定位，不是业务接口。 |
| 为什么 `/health` 不能太重？ | 健康检查应快速、稳定、低成本；不应调用真实模型 API 或复杂外部依赖。 |
| FastAPI 如何生成 `/docs`？ | FastAPI 根据路径函数、类型注解和 response model 生成 OpenAPI，再由 Swagger UI 渲染。 |
| `TestClient` 有什么价值？ | 可以直接调用 ASGI app 测试接口，不需要启动真实端口，适合 CI。 |
| Uvicorn 的作用是什么？ | Uvicorn 是 ASGI server，负责运行 FastAPI 应用并处理 HTTP 请求。 |

## 完成标准

- `GET /health` 返回 200。
- 响应体包含 `status`、`app_name`、`environment`、`version`。
- `/openapi.json` 包含 `/health`。
- `python -m pytest` 通过。
