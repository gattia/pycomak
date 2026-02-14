"""
Tests for utils.py — timeout and file copy utilities.
"""

import os
import time
import pytest

from pycomak.utils import run_with_timeout, copy_file_names_with_strings


# =========================================================================
# run_with_timeout
# =========================================================================


def _fast_func(result_list):
    """A fast function that completes quickly."""
    result_list.append("done")


def _slow_func():
    """A function that takes too long."""
    time.sleep(30)


def _func_with_args(a, b, key=None):
    """A function that accepts args and kwargs."""
    return a + b  # return value not used since it runs in a subprocess


class TestRunWithTimeout:
    def test_fast_function_completes(self):
        """Fast function completes without raising."""
        # run_with_timeout uses multiprocessing.Process, so we can't easily
        # check return values, but we can verify no exception is raised
        run_with_timeout(lambda: None, timeout=5)

    def test_slow_function_raises_timeout(self):
        with pytest.raises(TimeoutError):
            run_with_timeout(_slow_func, timeout=1)

    def test_args_forwarded(self):
        """Args and kwargs are forwarded to the function."""
        # This should not raise even though the function uses args
        run_with_timeout(_func_with_args, timeout=5, a=1, b=2, key="test")


# =========================================================================
# copy_file_names_with_strings
# =========================================================================


class TestCopyFileNamesWithStrings:
    def test_creates_paraview_dir(self, tmp_path):
        # Create some files
        (tmp_path / "data_001.vtp").write_text("content")
        copy_file_names_with_strings(["*_001.vtp"], str(tmp_path))
        assert (tmp_path / "paraview").is_dir()

    def test_copies_matching_files(self, tmp_path):
        (tmp_path / "mesh_001.vtp").write_text("mesh data")
        (tmp_path / "mesh_002.vtp").write_text("mesh data 2")
        (tmp_path / "other.txt").write_text("not copied")
        copy_file_names_with_strings(["mesh_*.vtp"], str(tmp_path))
        assert (tmp_path / "paraview" / "mesh_001.vtp").exists()
        assert (tmp_path / "paraview" / "mesh_002.vtp").exists()
        assert not (tmp_path / "paraview" / "other.txt").exists()

    def test_overwrite_false_skips_existing(self, tmp_path):
        (tmp_path / "file.vtp").write_text("original")
        paraview = tmp_path / "paraview"
        paraview.mkdir()
        (paraview / "file.vtp").write_text("existing")
        copy_file_names_with_strings(["file.vtp"], str(tmp_path), overwrite=False)
        # Existing file should not be overwritten
        assert (paraview / "file.vtp").read_text() == "existing"

    def test_overwrite_true_overwrites(self, tmp_path):
        (tmp_path / "file.vtp").write_text("new content")
        paraview = tmp_path / "paraview"
        paraview.mkdir()
        (paraview / "file.vtp").write_text("old content")
        copy_file_names_with_strings(["file.vtp"], str(tmp_path), overwrite=True)
        assert (paraview / "file.vtp").read_text() == "new content"

    def test_multiple_patterns(self, tmp_path):
        (tmp_path / "a.vtp").write_text("a")
        (tmp_path / "b.sto").write_text("b")
        copy_file_names_with_strings(["*.vtp", "*.sto"], str(tmp_path))
        assert (tmp_path / "paraview" / "a.vtp").exists()
        assert (tmp_path / "paraview" / "b.sto").exists()
