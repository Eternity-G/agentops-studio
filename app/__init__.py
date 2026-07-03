"""Top-level package for AgentOps Studio.

This file is deliberately small in stage 1. Its main job is to prove that the
project is importable as a Python package before we add API routes, Agent state,
or model providers.

Keeping a stable package entry point helps tests catch broken imports early.
"""

from __future__ import annotations

__all__ = ["__version__"]

# Keep this value aligned with `pyproject.toml` while the project is small.
__version__ = "0.1.0"
