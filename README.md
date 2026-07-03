# AgentOps Studio

AgentOps Studio 是一个用于学习和构建 Agent 工程系统的项目。它的长期目标不是做一个简单聊天机器人，而是逐步搭建一个包含任务规划、工具调用、记忆、Trace、评测和部署能力的 Agent 工程平台。

当前只完成 **阶段 1 的第 1 步：项目骨架与环境**。这一阶段刻意保持简单，目的是先保证项目结构清晰、可以导入、可以测试、可以被 Git 管理。

## 当前目标

第 1 步只验证几件事：

- Python 包可以被正常导入。
- 配置可以从环境变量中读取。
- 测试框架可以运行。
- 项目已经准备好继续扩展后续功能。
- 仓库已经可以连接到 GitHub 远程地址。

本步骤暂不实现真实模型调用、FastAPI 接口、RAG、记忆系统或工具调用。

## 当前目录结构

```text
app/
  __init__.py
  settings.py
tests/
  test_project_import.py
  test_settings.py
.env.example
pyproject.toml
```

## 文件说明

| 文件 | 作用 |
|---|---|
| `app/__init__.py` | Python 包入口，当前只暴露项目版本号，用来验证项目可导入。 |
| `app/settings.py` | 配置加载模块，集中读取环境变量，避免后续代码到处直接访问 `os.environ`。 |
| `tests/test_project_import.py` | 验证 `app` 包可以被正常导入。 |
| `tests/test_settings.py` | 验证默认配置和环境变量覆盖逻辑。 |
| `.env.example` | 环境变量模板，后续复制为 `.env` 使用。 |
| `pyproject.toml` | 项目配置文件，声明包信息、测试配置和代码规范工具配置。 |
| `.gitignore` | Git 忽略规则，避免提交缓存、虚拟环境和本地密钥文件。 |

## 快速开始

安装开发依赖：

```bash
python -m pip install -e ".[dev]"
```

运行测试：

```bash
python -m pytest
```

如果暂时不想安装 `pytest`，也可以使用 Python 标准库自带的 `unittest`：

```bash
python -m unittest discover -s tests
```

## 可观测验证方式

完成第 1 步后，至少要能看到以下结果。

验证项目可以导入：

```bash
python -c "import app; print(app.__version__)"
```

期望输出：

```text
0.1.0
```

验证配置加载：

```bash
python -c "from app.settings import load_settings; print(load_settings())"
```

期望能看到类似输出：

```text
AppSettings(app_name='AgentOps Studio', app_env='development', debug=True, model_provider='mock', default_model='mock-planner-v1')
```

验证测试通过：

```bash
python -m pytest
```

期望输出：

```text
3 passed
```

## 当前阶段不做什么

为了保证学习节奏，第 1 步不做以下内容：

- 不接入真实大模型 API。
- 不实现 FastAPI 路由。
- 不实现 Agent planning。
- 不实现工具调用。
- 不实现 RAG 或数据库。
- 不实现前端页面。

这些内容会在后续步骤逐步添加，每一步都要有明确的测试方式。

## GitHub 远程仓库

当前本地仓库远程地址：

```bash
git remote -v
```

期望看到：

```text
origin  https://github.com/Eternity-G/agentops-studio.git (fetch)
origin  https://github.com/Eternity-G/agentops-studio.git (push)
```

## 下一步

下一步是 **2. FastAPI 健康检查**：

- 安装 FastAPI 和 Uvicorn。
- 创建最小 API 服务。
- 实现 `GET /health`。
- 编写测试验证 `/health` 返回 200 和 `{"status": "ok"}`。
