"""
Tests for forsim.py criteria evaluation functions.

Tests get_total_ligament_force() and analyze_criteria() — the pure-Python
logic used during patella optimization to decide pass/fail.
"""

import numpy as np
import pytest

from pycomak.forsim import get_total_ligament_force, analyze_criteria


# =========================================================================
# get_total_ligament_force
# =========================================================================


class TestGetTotalLigamentForce:
    """Tests for fiber summation logic."""

    def _make_jam_with_ligaments(self, make_jam, fibers):
        """Helper to build a JamAnalysis with specified ligament fibers."""
        ligaments = {}
        for name, force_values in fibers.items():
            ligaments[name] = {"total_force": force_values.reshape(-1, 1)}
        return make_jam(ligaments=ligaments)

    def test_sums_fibers_correctly(self, make_jam):
        """Total force = sum of all matching fiber forces."""
        jam = self._make_jam_with_ligaments(
            make_jam,
            {
                "ACLam1": np.array([10.0, 20.0, 30.0]),
                "ACLpl1": np.array([5.0, 10.0, 15.0]),
            },
        )
        result = get_total_ligament_force(jam, "ACL")
        np.testing.assert_array_almost_equal(result, [15.0, 30.0, 45.0])

    def test_pattern_match_acl_not_pcl(self, make_jam):
        """'ACL' should match 'ACLam1' and 'ACLpl1' but NOT 'PCLal1'."""
        jam = self._make_jam_with_ligaments(
            make_jam,
            {
                "ACLam1": np.array([10.0, 10.0]),
                "ACLpl1": np.array([5.0, 5.0]),
                "PCLal1": np.array([100.0, 100.0]),
            },
        )
        result = get_total_ligament_force(jam, "ACL")
        np.testing.assert_array_almost_equal(result, [15.0, 15.0])

    def test_single_fiber(self, make_jam):
        """Ligament with only one fiber works."""
        jam = self._make_jam_with_ligaments(
            make_jam,
            {"LCL1": np.array([7.0, 14.0])},
        )
        result = get_total_ligament_force(jam, "LCL")
        np.testing.assert_array_almost_equal(result, [7.0, 14.0])

    def test_not_found_raises_value_error(self, make_jam):
        jam = self._make_jam_with_ligaments(
            make_jam,
            {"ACLam1": np.array([1.0])},
        )
        with pytest.raises(ValueError, match="not found"):
            get_total_ligament_force(jam, "NONEXISTENT")

    def test_mcl_pattern(self, make_jam):
        """MCL matches MCLd1, MCLd2, MCLs1, MCLs2, etc."""
        jam = self._make_jam_with_ligaments(
            make_jam,
            {
                "MCLd1": np.array([10.0]),
                "MCLd2": np.array([20.0]),
                "MCLs1": np.array([30.0]),
            },
        )
        result = get_total_ligament_force(jam, "MCL")
        np.testing.assert_array_almost_equal(result, [60.0])

    def test_prefix_matching_not_substring(self, make_jam):
        """'PT' should match PT1, PT2 but NOT mPTl1 (hypothetical fiber)."""
        jam = self._make_jam_with_ligaments(
            make_jam,
            {
                "PT1": np.array([10.0, 20.0]),
                "PT2": np.array([5.0, 10.0]),
                "mPTl1": np.array([100.0, 200.0]),
            },
        )
        result = get_total_ligament_force(jam, "PT")
        # Should be PT1 + PT2 = [15, 30], NOT PT1 + PT2 + mPTl1 = [115, 230]
        np.testing.assert_array_almost_equal(result, [15.0, 30.0])

    def test_bare_pfl_does_not_match_prefixed_variants(self, make_jam):
        """'PFL' should match PFL1 only, not lPFL1 or mPFL1 (startswith matching)."""
        jam = self._make_jam_with_ligaments(
            make_jam,
            {
                "lPFL1": np.array([10.0]),
                "mPFL1": np.array([20.0]),
                "PFL1": np.array([30.0]),
            },
        )
        result = get_total_ligament_force(jam, "PFL")
        # startswith: "lPFL1".startswith("PFL") is False, "mPFL1".startswith("PFL") is False
        np.testing.assert_array_almost_equal(result, [30.0])

    def test_pfl_prefix_specificity(self, make_jam):
        """'lPFL' should match only lPFL1, not mPFL1."""
        jam = self._make_jam_with_ligaments(
            make_jam,
            {
                "lPFL1": np.array([10.0]),
                "mPFL1": np.array([50.0]),
            },
        )
        result_l = get_total_ligament_force(jam, "lPFL")
        np.testing.assert_array_almost_equal(result_l, [10.0])

        result_m = get_total_ligament_force(jam, "mPFL")
        np.testing.assert_array_almost_equal(result_m, [50.0])


# =========================================================================
# analyze_criteria
# =========================================================================


class TestAnalyzeCriteria:
    """Tests for criteria evaluation logic."""

    def _make_jam_for_criteria(self, make_jam, lig_forces=None, coord_values=None):
        """Build JamAnalysis with data suitable for analyze_criteria."""
        ligaments = {}
        if lig_forces:
            for name, values in lig_forces.items():
                ligaments[name] = {"total_force": values.reshape(-1, 1)}

        coordinates = {}
        if coord_values:
            for name, values in coord_values.items():
                coordinates[name] = {"value": values.reshape(-1, 1)}

        return make_jam(ligaments=ligaments, coordinates=coordinates)

    def test_all_pass(self, make_jam):
        """All criteria met → passed=True."""
        jam = self._make_jam_for_criteria(
            make_jam,
            lig_forces={"PT1": np.array([10.0, 10.0, 10.0])},
            coord_values={"pf_tx_r": np.array([0.001, 0.001, 0.001])},
        )
        criteria = {
            "ligaments": {"PT": {"max_range": 1100, "max": 1100}},
            "coords": {"pf_tx_r": {"max_range": 0.005, "max": 0.005}},
        }
        criteria, passed = analyze_criteria(jam, criteria, "ligaments")
        criteria, passed = analyze_criteria(jam, criteria, "coords", passed=passed)
        assert passed is True

    def test_max_range_fails(self, make_jam):
        """ptp > threshold → passed=False."""
        jam = self._make_jam_for_criteria(
            make_jam,
            lig_forces={"PT1": np.array([0.0, 2000.0])},
        )
        criteria = {"ligaments": {"PT": {"max_range": 1100}}}
        criteria, passed = analyze_criteria(jam, criteria, "ligaments")
        assert passed is False

    def test_max_exceeds(self, make_jam):
        """max > threshold → passed=False."""
        jam = self._make_jam_for_criteria(
            make_jam,
            lig_forces={"PT1": np.array([0.0, 1200.0])},
        )
        criteria = {"ligaments": {"PT": {"max": 1100}}}
        criteria, passed = analyze_criteria(jam, criteria, "ligaments")
        assert passed is False

    def test_min_below(self, make_jam):
        """min < threshold → passed=False."""
        jam = self._make_jam_for_criteria(
            make_jam,
            coord_values={"pf_tx_r": np.array([-0.01, 0.001])},
        )
        criteria = {"coords": {"pf_tx_r": {"min": 0.0}}}
        criteria, passed = analyze_criteria(jam, criteria, "coords")
        assert passed is False

    def test_mutates_dict_with_results(self, make_jam):
        """analyze_criteria adds 'ptp_', 'min_', 'max_' keys to the criteria dict."""
        jam = self._make_jam_for_criteria(
            make_jam,
            lig_forces={"PT1": np.array([5.0, 15.0])},
        )
        criteria = {"ligaments": {"PT": {}}}
        criteria, _ = analyze_criteria(jam, criteria, "ligaments")
        assert "ptp_" in criteria["ligaments"]["PT"]
        assert "min_" in criteria["ligaments"]["PT"]
        assert "max_" in criteria["ligaments"]["PT"]
        assert criteria["ligaments"]["PT"]["ptp_"] == pytest.approx(10.0)
        assert criteria["ligaments"]["PT"]["min_"] == pytest.approx(5.0)
        assert criteria["ligaments"]["PT"]["max_"] == pytest.approx(15.0)

    def test_empty_criteria_passes(self, make_jam):
        """Empty criteria dict → always passes."""
        jam = self._make_jam_for_criteria(
            make_jam,
            lig_forces={"PT1": np.array([99999.0])},
        )
        criteria = {"ligaments": {"PT": {}}}
        criteria, passed = analyze_criteria(jam, criteria, "ligaments")
        assert passed is True

    def test_preserves_passed_false(self, make_jam):
        """If passed=False is passed in, it stays False even if current criteria pass."""
        jam = self._make_jam_for_criteria(
            make_jam,
            lig_forces={"PT1": np.array([1.0])},
        )
        criteria = {"ligaments": {"PT": {"max": 9999}}}
        criteria, passed = analyze_criteria(jam, criteria, "ligaments", passed=False)
        assert passed is False

    def test_coords_criteria_type(self, make_jam):
        """analyze_criteria works with coords criteria_type."""
        jam = self._make_jam_for_criteria(
            make_jam,
            coord_values={"pf_tx_r": np.array([0.001, 0.002, 0.003])},
        )
        criteria = {"coords": {"pf_tx_r": {"max_range": 0.005}}}
        criteria, passed = analyze_criteria(jam, criteria, "coords")
        assert passed is True
        assert "ptp_" in criteria["coords"]["pf_tx_r"]

    def test_criteria_dict_reuse_across_calls(self, make_jam):
        """Reusing the same criteria dict across calls should overwrite, not accumulate.

        This documents existing correct behavior — analyze_criteria uses .update()
        which overwrites previous ptp_/min_/max_ values.
        """
        # First call: PT range = 500 (passes max_range=1100)
        jam1 = self._make_jam_for_criteria(
            make_jam,
            lig_forces={"PT1": np.array([0.0, 500.0])},
        )
        criteria = {"ligaments": {"PT": {"max_range": 1100}}}
        criteria, passed1 = analyze_criteria(jam1, criteria, "ligaments")
        assert passed1 is True
        assert criteria["ligaments"]["PT"]["ptp_"] == pytest.approx(500.0)

        # Second call with DIFFERENT data: PT range = 2000 (fails max_range=1100)
        jam2 = self._make_jam_for_criteria(
            make_jam,
            lig_forces={"PT1": np.array([0.0, 2000.0])},
        )
        criteria, passed2 = analyze_criteria(jam2, criteria, "ligaments")
        assert passed2 is False
        # ptp_ should be overwritten to 2000, not accumulated
        assert criteria["ligaments"]["PT"]["ptp_"] == pytest.approx(2000.0)

    def test_multi_file_jam_raises(self, make_jam):
        """analyze_criteria rejects multi-file JamAnalysis objects."""
        jam = self._make_jam_for_criteria(
            make_jam,
            lig_forces={"PT1": np.array([10.0])},
        )
        jam.num_files = 3
        criteria = {"ligaments": {"PT": {"max_range": 1100}}}
        with pytest.raises(ValueError, match="single-file"):
            analyze_criteria(jam, criteria, "ligaments")
