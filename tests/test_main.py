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

    def test_standard_filenames_defined(self, tmp_path):
        base = COMAKBASE(str(tmp_path / "results"))
        assert base.settle_sim_intermed_filename == "model_update_slack_intermediate.osim"
        assert base.settle_and_sweep_sim_filename == "model_updated_slack_final.osim"
        assert base.comak_ik_filename == "comak_ik.mot"
        assert base.comak_id_results_filename == "inverse-dynamics.sto"

    def test_idempotent(self, tmp_path):
        """Calling COMAKBASE twice on the same path doesn't crash."""
        COMAKBASE(str(tmp_path / "results"))
        COMAKBASE(str(tmp_path / "results"))
        assert os.path.isdir(str(tmp_path / "results" / "logs"))

    def test_results_dir_attribute(self, tmp_path):
        base = COMAKBASE(str(tmp_path / "results"))
        assert base.results_dir == str(tmp_path / "results")
