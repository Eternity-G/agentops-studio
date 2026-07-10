# 第 17 步：前端 Demo 页面

## 本步骤目标

第 17 步提供一个浏览器可用的 Demo 页面，让用户可以不用 curl 也能体验项目当前能力。

页面覆盖四个功能：

- 任务运行：调用 `POST /tasks/run`。
- 文档问答：调用 `POST /documents/ask`。
- 会话记忆：调用 `GET /sessions/{session_id}` 和 `POST /sessions/{session_id}/notes`。
- 评测报告：调用 `GET /evals/latest-report`。

## 为什么不用 React 或 Vue

当前项目重点是 Agent 后端工程链路。

如果第 17 步引入 React、Vite、Node、前端路由和构建流程，会增加学习负担，也会让部署复杂度上升。

所以本步骤使用 FastAPI 直接托管静态文件：

```text
app/web/index.html
app/web/styles.css
app/web/app.js
app/web/assets/flow.svg
```

这样做的好处是：

- 不需要额外前端依赖。
- 启动 FastAPI 就能访问页面。
- 测试可以直接用 `TestClient` 验证页面和静态资源。
- 第 18 步部署时更简单。

## 本步骤新增或修改的文件

```text
app/
  api/
    routes.py
  web/
    index.html
    styles.css
    app.js
    assets/
      flow.svg
tests/
  test_web.py
docs/
  第17步-前端Demo页面.md
README.md
```

| 文件 | 作用 |
|---|---|
| `app/web/index.html` | 前端 Demo 页面结构。 |
| `app/web/styles.css` | 页面样式，包含响应式布局。 |
| `app/web/app.js` | 调用后端 API 并展示结果。 |
| `app/web/assets/flow.svg` | 页面中的 Agent 流程视觉资产。 |
| `app/api/routes.py` | 托管首页、静态资源和最新评测报告。 |
| `tests/test_web.py` | 验证首页、静态资源、评测报告和 OpenAPI 路由。 |

## 页面入口

启动服务：

```bash
python -m uvicorn app.api.routes:app --reload
```

打开浏览器：

```text
http://localhost:8000/
```

## 可观测验证方式

只运行第 17 步测试：

```bash
python -m pytest tests/test_web.py
```

期望结果：

```text
4 passed
```

运行全部测试：

```bash
python -m pytest
```

当前期望结果：

```text
79 passed
```

## 你需要理解的面试问题

### 1. 为什么这个前端页面也要写测试？

因为页面是项目的演示入口。

如果首页、静态资源或评测报告接口挂了，用户即使不能直接看到后端 bug，也会认为项目不可用。

### 2. 为什么前端 Demo 不等于生产前端？

Demo 页面的目标是展示功能闭环，不是构建完整产品前端。

生产前端还需要：

- 用户认证。
- 表单错误提示。
- 加载状态细化。
- 权限控制。
- 前端构建和发布流程。
- 更完整的可访问性测试。

### 3. 为什么把评测报告暴露给前端？

这能让项目从“功能展示”升级为“质量展示”。

用户可以看到系统不只是能跑，还能被固定用例持续验证。

## 下一步

第 18 步：部署、简历材料与项目复盘。

目标是补齐最终部署说明、项目亮点、简历表述和验收清单。
