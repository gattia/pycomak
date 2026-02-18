"""
Tests for main.py — COMAKBASE directory structure creation.
"""

import os
import pytest

from pycomak.main import COMAKBASE


class TestCOMAKBASE:
    def test_creates_all_expected_subdirectories(self, tmp_path):
        base = COMAKBASE(str(tmp_path / "results"))
        expected_dirs = [
            "logs",
            "comak-inverse-kinematics",
            "inputs",
            "comak-inverse-dynamics",
            "comak",
            "joint-mechanics",
            os.path.join("joint-mechanics", "paraview"),
            "graphics",
        ]
        for d in expected_dirs:
            full = os.path.join(str(tmp_path / "results"), d)
            assert os.path.isdir(full), f"Missing directory: {d}"

    def test_idempotent(self, tmp_path):
        """Calling COMAKBASE twice on the same path doesn't crash."""
        COMAKBASE(str(tmp_path / "results"))
        COMAKBASE(str(tmp_path / "results"))
        assert os.path.isdir(str(tmp_path / "results" / "logs"))

