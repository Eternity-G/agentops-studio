"""Tests for the stage 1 settings layer."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from app.settings import AppSettings, load_settings


class SettingsTests(unittest.TestCase):
    """Verify predictable settings defaults and environment overrides."""

    def test_default_settings_are_safe_for_local_development(self) -> None:
        """Defaults should not require external services or API keys."""

        with patch.dict(os.environ, {}, clear=True):
            settings = load_settings(load_dotenv=False)

        self.assertEqual(settings, AppSettings())
        self.assertEqual(settings.model_provider, "mock")

    def test_environment_variables_override_defaults(self) -> None:
        """Environment values should map into the typed settings object."""

        overrides = {
            "APP_NAME": "Local AgentOps",
            "APP_ENV": "test",
            "APP_DEBUG": "false",
            "MODEL_PROVIDER": "mock",
            "DEFAULT_MODEL": "mock-test-model",
        }

        with patch.dict(os.environ, overrides, clear=True):
            settings = load_settings()

        self.assertEqual(settings.app_name, "Local AgentOps")
        self.assertEqual(settings.app_env, "test")
        self.assertFalse(settings.debug)
        self.assertEqual(settings.default_model, "mock-test-model")


if __name__ == "__main__":
    unittest.main()
