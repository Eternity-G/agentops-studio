"""Application settings for AgentOps Studio.

Stage 1 needs a tiny configuration layer so later modules do not read
environment variables directly. Centralising settings makes future changes
safer: API routes, model providers, and evaluation runners can all depend on
the same typed object.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_APP_NAME = "AgentOps Studio"
DEFAULT_APP_ENV = "development"
DEFAULT_DEBUG = True
DEFAULT_MODEL_PROVIDER = "mock"
DEFAULT_MODEL = "mock-planner-v1"
DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com"


def _load_dotenv_if_present(path: str = ".env") -> None:
    """Load local `.env` values into `os.environ` when they are not set.

    这里实现一个极小的 dotenv loader，避免把项目绑定到额外依赖。
    规则刻意简单：
    - 空行和 `#` 注释会被跳过。
    - 只支持 `KEY=value`。
    - 已经存在的系统环境变量优先级更高，不会被 `.env` 覆盖。
    """

    if _read_bool("AGENTOPS_DISABLE_DOTENV", default=False):
        return

    env_path = Path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _read_bool(name: str, default: bool) -> bool:
    """Read a boolean environment variable with predictable parsing.

    Environment variables are strings, so a strict parser avoids surprises such
    as treating the text `"false"` as truthy. Unknown values fall back to the
    provided default instead of crashing during local development.
    """

    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False

    return default


@dataclass(frozen=True, slots=True)
class AppSettings:
    """Typed settings used by the application.

    The defaults are intentionally safe for stage 1. The project should run
    without real API keys until the provider adapter step is implemented.
    """

    app_name: str = DEFAULT_APP_NAME
    app_env: str = DEFAULT_APP_ENV
    debug: bool = DEFAULT_DEBUG
    model_provider: str = DEFAULT_MODEL_PROVIDER
    default_model: str = DEFAULT_MODEL
    deepseek_api_key: str | None = None
    deepseek_base_url: str = DEFAULT_DEEPSEEK_BASE_URL


def load_settings(*, load_dotenv: bool = True) -> AppSettings:
    """Create settings from environment variables.

    This function is the only place in stage 1 that reads `os.environ`. It also
    loads local `.env` values first so `uvicorn app.api.routes:app` works without
    manually exporting variables in the shell.
    """

    if load_dotenv:
        _load_dotenv_if_present()

    return AppSettings(
        app_name=os.getenv("APP_NAME", DEFAULT_APP_NAME),
        app_env=os.getenv("APP_ENV", DEFAULT_APP_ENV),
        debug=_read_bool("APP_DEBUG", DEFAULT_DEBUG),
        model_provider=os.getenv("MODEL_PROVIDER", DEFAULT_MODEL_PROVIDER),
        default_model=os.getenv("DEFAULT_MODEL", DEFAULT_MODEL),
        deepseek_api_key=os.getenv("DEEPSEEK_API_KEY") or None,
        deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", DEFAULT_DEEPSEEK_BASE_URL),
    )
