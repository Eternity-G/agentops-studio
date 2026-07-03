"""Import checks for the stage 1 project skeleton.

These tests are intentionally basic. Their purpose is to catch broken package
layout before more complex Agent code is added.
"""

from __future__ import annotations

import unittest

import app


class ProjectImportTests(unittest.TestCase):
    """Verify that the Python package has a stable import surface."""

    def test_package_exposes_version(self) -> None:
        """The package should expose the current project version."""

        self.assertEqual(app.__version__, "0.1.0")


if __name__ == "__main__":
    unittest.main()
