"""
Tests for plotting_utils.py — pure logic tests + smoke tests.

Pure logic tests: assign_colors_to_groups, _get_variable_label
Smoke tests: plot functions return Axes without crashing
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for testing
import matplotlib.pyplot as plt
import pytest

from pycomak.plotting_utils import (
    assign_colors_to_groups,
    _get_variable_label,
    GROUP_COLORS,
    plot_coordinate_comparison,
    plot_regional_contact,
    plot_variable_scatter,
)


# =========================================================================
# assign_colors_to_groups
# =========================================================================


class TestAssignColorsToGroups:
    def test_known_groups_get_predefined_colors(self):
        colors = assign_colors_to_groups(["healthy", "OA"])
        assert colors["healthy"] == GROUP_COLORS["healthy"]
        assert colors["OA"] == GROUP_COLORS["OA"]

    def test_unknown_groups_get_cycle_colors(self):
        colors = assign_colors_to_groups(["group_x", "group_y"])
        assert "group_x" in colors
        assert "group_y" in colors
        # Should be different from each other
        assert colors["group_x"] != colors["group_y"]


# =========================================================================
# _get_variable_label
# =========================================================================


class TestGetVariableLabel:
    def test_coordinate_rotation_label(self):
        label = _get_variable_label({"type": "coordinate", "name": "knee_flex_r"})
        assert "Flexion" in label
        assert "(rad)" in label

    def test_coordinate_translation_label(self):
        label = _get_variable_label({"type": "coordinate", "name": "knee_tx_r"})
        assert "Translation" in label
        assert "(m)" in label

    def test_unknown_type_returns_name(self):
        label = _get_variable_label({"type": "unknown", "name": "my_var"})
        assert label == "my_var"


# =========================================================================
# Smoke tests (plot functions return Axes without crashing)
# =========================================================================


class TestPlotSmoke:
    """Ensure plot functions don't crash and return Axes objects."""

    def _make_group_data_stats(self, n_groups=2, n_timesteps=101):
        """Create mock group data dicts (stats format)."""
        groups = {}
        for i in range(n_groups):
            name = f"group_{i}"
            t = np.linspace(0, 100, n_timesteps)
            groups[name] = {
                "mean": np.sin(t * 0.1) + i,
                "std": np.ones(n_timesteps) * 0.1,
                "ste": np.ones(n_timesteps) * 0.05,
                "time": t,
                "n": 10,
            }
        return groups

    def _make_scatter_data(self, n_groups=2, n_subjects=5):
        data = {}
        for i in range(n_groups):
            data[f"group_{i}"] = np.random.randn(n_subjects)
        return data

    def test_plot_coordinate_comparison(self):
        data = self._make_group_data_stats()
        ax = plot_coordinate_comparison(data, "knee_flex_r")
        assert isinstance(ax, plt.Axes)
        plt.close("all")

    def test_plot_regional_contact(self):
        data = self._make_group_data_stats()
        ax = plot_regional_contact(data, region=4, outcome_type="max_pressure")
        assert isinstance(ax, plt.Axes)
        plt.close("all")

    def test_plot_variable_scatter(self):
        x_data = self._make_scatter_data()
        y_data = self._make_scatter_data()
        ax = plot_variable_scatter(x_data, y_data)
        assert isinstance(ax, plt.Axes)
        plt.close("all")
