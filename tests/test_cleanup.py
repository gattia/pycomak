"""
Tests for cleanup.py — file operation tests.

All tests use tmp_path, no real files touched.
"""

import os
import pytest

from pycomak.cleanup import (
    format_size,
    find_joint_mechanics_dirs,
    delete_files_in_dir,
    cleanup_legacy_vtp_files,
)


# =========================================================================
# format_size
# =========================================================================


class TestFormatSize:
    def test_bytes(self):
        assert format_size(512) == "512.0 B"

    def test_kilobytes(self):
        assert format_size(1024) == "1.0 KB"

    def test_megabytes(self):
        assert format_size(1024 * 1024) == "1.0 MB"

    def test_gigabytes(self):
        assert format_size(1024**3) == "1.0 GB"

    def test_zero(self):
        assert format_size(0) == "0.0 B"

    def test_fractional_kb(self):
        result = format_size(1536)
        assert result == "1.5 KB"


# =========================================================================
# find_joint_mechanics_dirs
# =========================================================================


class TestFindJointMechanicsDirs:
    def test_finds_jm_dir(self, tmp_path):
        jm = tmp_path / "subject" / "results" / "joint-mechanics"
        jm.mkdir(parents=True)
        result = find_joint_mechanics_dirs(str(tmp_path))
        assert len(result) == 1
        assert result[0] == str(jm)

    def test_finds_multiple(self, tmp_path):
        for i in range(3):
            (tmp_path / f"subj_{i}" / "joint-mechanics").mkdir(parents=True)
        result = find_joint_mechanics_dirs(str(tmp_path))
        assert len(result) == 3

    def test_skips_excluded_dirs(self, tmp_path):
        (tmp_path / ".git" / "joint-mechanics").mkdir(parents=True)
        (tmp_path / "__pycache__" / "joint-mechanics").mkdir(parents=True)
        (tmp_path / "real" / "joint-mechanics").mkdir(parents=True)
        result = find_joint_mechanics_dirs(str(tmp_path))
        assert len(result) == 1

    def test_empty_dir_returns_empty(self, tmp_path):
        result = find_joint_mechanics_dirs(str(tmp_path))
        assert result == []


# =========================================================================
# delete_files_in_dir
# =========================================================================


class TestDeleteFilesInDir:
    def _create_test_files(self, jm_dir):
        """Create a set of test VTP/H5 files in a joint-mechanics directory."""
        os.makedirs(jm_dir, exist_ok=True)
        files = {
            "kept": [
                "_contact_mesh_0001.vtp",
                "_contact_mesh_0002.vtp",
                "joint_mechanics.h5",
            ],
            "deleted": [
                "_ligament_0001.vtp",
                "_ligament_0002.vtp",
                "_muscle_0001.vtp",
                "_mesh_0001.vtp",
            ],
        }
        for f in files["kept"] + files["deleted"]:
            path = os.path.join(jm_dir, f)
            with open(path, "w") as fh:
                fh.write("test content")
        return files

    def test_dry_run_counts_but_doesnt_delete(self, tmp_path):
        jm_dir = str(tmp_path / "joint-mechanics")
        files = self._create_test_files(jm_dir)
        result = delete_files_in_dir(jm_dir, dry_run=True)
        assert result["deleted"] == len(files["deleted"])
        # Files should still exist after dry run
        for f in files["deleted"]:
            assert os.path.exists(os.path.join(jm_dir, f))

    def test_execute_deletes_matching_patterns(self, tmp_path):
        jm_dir = str(tmp_path / "joint-mechanics")
        files = self._create_test_files(jm_dir)
        result = delete_files_in_dir(jm_dir, dry_run=False)
        assert result["deleted"] == len(files["deleted"])
        # Deleted files should be gone
        for f in files["deleted"]:
            assert not os.path.exists(os.path.join(jm_dir, f))

    def test_keeps_contact_vtp_and_h5(self, tmp_path):
        jm_dir = str(tmp_path / "joint-mechanics")
        files = self._create_test_files(jm_dir)
        delete_files_in_dir(jm_dir, dry_run=False)
        # Kept files should still exist
        for f in files["kept"]:
            assert os.path.exists(os.path.join(jm_dir, f))

    def test_size_freed_positive(self, tmp_path):
        jm_dir = str(tmp_path / "joint-mechanics")
        self._create_test_files(jm_dir)
        result = delete_files_in_dir(jm_dir, dry_run=True)
        assert result["size_freed"] > 0


# =========================================================================
# cleanup_legacy_vtp_files (integration)
# =========================================================================


class TestCleanupLegacyVtpFiles:
    def test_nonexistent_path_returns_error(self):
        result = cleanup_legacy_vtp_files("/nonexistent/path", verbose=False)
        assert result["errors"] == 1
        assert result["directories"] == 0

    def test_empty_dir_returns_zeros(self, tmp_path):
        result = cleanup_legacy_vtp_files(str(tmp_path), verbose=False)
        assert result["directories"] == 0
        assert result["files_deleted"] == 0
        assert result["errors"] == 0

    def test_dry_run_with_files(self, tmp_path):
        jm = tmp_path / "subj" / "joint-mechanics"
        jm.mkdir(parents=True)
        (jm / "_ligament_001.vtp").write_text("data")
        (jm / "_muscle_001.vtp").write_text("data")
        result = cleanup_legacy_vtp_files(str(tmp_path), execute=False, verbose=False)
        assert result["files_deleted"] == 2
        # Files still exist (dry run)
        assert (jm / "_ligament_001.vtp").exists()
