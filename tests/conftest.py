"""Shared pytest configuration.

Unit tests must not load the developer's local `.env`, because `.env` may select
real paid providers such as DeepSeek. Real provider checks belong in manual
verification scripts, not in the default test suite.
"""

from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def isolate_provider_environment() -> None:
    """Keep unit tests independent from local paid-provider `.env` settings."""

    os.environ["AGENTOPS_DISABLE_DOTENV"] = "true"
    for key in (
        "MODEL_PROVIDER",
        "DEFAULT_MODEL",
        "DEEPSEEK_API_KEY",
        "DEEPSEEK_BASE_URL",
    ):
        os.environ.pop(key, None)
