"""Application settings for AgentOps Studio.

Stage 1 needs a tiny configuration layer so later modules do not read
environment variables directly. Centralising settings makes future changes
safer: API routes, model providers, and evaluation runners can all depend on
the same typed object.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


DEFAULT_APP_NAME = "AgentOps Studio"
DEFAULT_APP_ENV = "development"
DEFAULT_DEBUG = True
DEFAULT_MODEL_PROVIDER = "mock"
DEFAULT_MODEL = "mock-planner-v1"


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


def load_settings() -> AppSettings:
    """Create settings from environment variables.

    This function is the only place in stage 1 that reads `os.environ`. Tests can
    patch environment variables around this function and verify the rest of the
    application receives a clean `AppSettings` object.
    """

    return AppSettings(
        app_name=os.getenv("APP_NAME", DEFAULT_APP_NAME),
        app_env=os.getenv("APP_ENV", DEFAULT_APP_ENV),
        debug=_read_bool("APP_DEBUG", DEFAULT_DEBUG),
        model_provider=os.getenv("MODEL_PROVIDER", DEFAULT_MODEL_PROVIDER),
        default_model=os.getenv("DEFAULT_MODEL", DEFAULT_MODEL),
    )
