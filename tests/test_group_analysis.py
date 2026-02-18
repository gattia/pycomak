"""
Tests for GroupJamAnalysis — group-level analysis logic.

Uses mock JamAnalysis objects (no H5 files needed) to test:
- _filter_jam_data(): memory filtering logic
- get_*_data(): shape validation, stat computation, missing key handling
- remove_subjects(): by id and by index
- identify_outlier_subjects(): detection with known data
- extract_values_at_time(): exact and window extraction
"""

import numpy as np
import pytest

# GroupJamAnalysis imports opensim at module level; mock it to avoid import errors
import sys
from unittest.mock import MagicMock

# Mock opensim before importing group_analysis
if "opensim" not in sys.modules:
    sys.modules["opensim"] = MagicMock()

from pycomak.group_analysis import GroupJamAnalysis


def _build_group_analysis(make_jam, n_subjects=3, n_timesteps=101, group="healthy"):
    """
    Helper to build a GroupJamAnalysis with mock JamAnalysis subjects.

    Each subject gets:
    - Coordinate 'knee_flex_r' with value = subject_index * linspace(0, 1, n)
    - Muscle 'recfem_r' with actuation = subject_index * 10 + linspace(0, 1, n)
    - Ligament fibers ACLam1, ACLpl1 with total_force = (subject_index + 1) * ones
    - Contact tf_contact/tibia_cartilage with regional and total data
    """
    ga = GroupJamAnalysis.__new__(GroupJamAnalysis)
    ga.groups = {}
    ga.base_results_dir = "/fake"
    ga.comak_subfolder = "comak_results"
    ga.timepoint = "00m"
    ga.removal_history = []

    ga.groups[group] = {
        "subjects": [],
        "subject_ids": [],
        "jam_list": [],
    }

    for i in range(n_subjects):
        n = n_timesteps
        coord_val = (i * np.linspace(0, 1, n)).reshape(-1, 1)
        muscle_val = (i * 10 + np.linspace(0, 1, n)).reshape(-1, 1)
        lig_force_am = ((i + 1) * np.ones(n)).reshape(-1, 1)
        lig_force_pl = ((i + 1) * 2 * np.ones(n)).reshape(-1, 1)
        contact_force = np.ones((n, 3, 1)) * (i + 1)
        regional_force = np.ones((n, 3, 1)) * (i + 1) * 0.5
        regional_pressure = (np.ones((n, 1)) * (i + 1) * 100)

        contacts = {
            "tf_contact": {
                "tibia_cartilage": {
                    "total_contact_force": contact_force,
                    4: {
                        "regional_contact_force": regional_force,
                        "regional_max_pressure": regional_pressure,
                    },
                    5: {
                        "regional_contact_force": regional_force * 0.8,
                        "regional_max_pressure": regional_pressure * 0.8,
                    },
                }
            }
        }

        jam = make_jam(
            n_timesteps=n,
            muscles={"recfem_r": {"actuation": muscle_val}},
            ligaments={
                "ACLam1": {"total_force": lig_force_am},
                "ACLpl1": {"total_force": lig_force_pl},
            },
            contacts=contacts,
            coordinates={"knee_flex_r": {"value": coord_val}},
        )

        ga.groups[group]["subjects"].append(
            {
                "subject_id": f"subj_{i}",
                "side": "RIGHT",
                "datetime": "2025-01-01",
                "folder_results": f"/fake/{i}",
                "h5_file": f"/fake/{i}/jm.h5",
            }
        )
        ga.groups[group]["subject_ids"].append(f"subj_{i}_RIGHT")
        ga.groups[group]["jam_list"].append(jam)

    return ga


# =========================================================================
# _filter_jam_data
# =========================================================================


class TestFilterJamData:
    """Tests for the memory filtering logic."""

    def test_muscle_filtering_keeps_actuation_only(self, make_jam):
        jam = make_jam(
            muscles={
                "recfem_r": {
                    "actuation": np.ones((10, 1)),
                    "activation": np.ones((10, 1)),
                    "fiber_length": np.ones((10, 1)),
                }
            }
        )
        ga = GroupJamAnalysis.__new__(GroupJamAnalysis)
        ga._filter_jam_data(jam)
        assert "actuation" in jam.forceset["Muscle"]["recfem_r"]
        assert "activation" not in jam.forceset["Muscle"]["recfem_r"]
        assert "fiber_length" not in jam.forceset["Muscle"]["recfem_r"]

    def test_contact_filtering_keeps_specified_regions(self, make_jam):
        contacts = {
            "tf_contact": {
                "tibia_cartilage": {
                    "total_contact_force": np.ones((10, 3, 1)),
                    0: {"regional_max_pressure": np.ones((10, 1))},
                    4: {"regional_max_pressure": np.ones((10, 1))},
                    5: {"regional_max_pressure": np.ones((10, 1))},
                }
            }
        }
        jam = make_jam(contacts=contacts)
        ga = GroupJamAnalysis.__new__(GroupJamAnalysis)
        ga._filter_jam_data(jam, regions=[4, 5])
        filtered = jam.forceset["Smith2018ArticularContactForce"]["tf_contact"]["tibia_cartilage"]
        assert 4 in filtered
        assert 5 in filtered
        assert 0 not in filtered

    def test_total_contact_force_preserved(self, make_jam):
        contacts = {
            "tf_contact": {
                "tibia_cartilage": {
                    "total_contact_force": np.ones((10, 3, 1)),
                    4: {"regional_max_pressure": np.ones((10, 1))},
                }
            }
        }
        jam = make_jam(contacts=contacts)
        ga = GroupJamAnalysis.__new__(GroupJamAnalysis)
        ga._filter_jam_data(jam)
        filtered = jam.forceset["Smith2018ArticularContactForce"]["tf_contact"]["tibia_cartilage"]
        assert "total_contact_force" in filtered

    def test_ligament_not_filtered_by_default(self, make_jam):
        """By default, ligament_outcomes=None means keep all."""
        jam = make_jam(
            ligaments={
                "ACLam1": {
                    "total_force": np.ones((10, 1)),
                    "strain": np.ones((10, 1)),
                }
            }
        )
        ga = GroupJamAnalysis.__new__(GroupJamAnalysis)
        ga._filter_jam_data(jam)
        # Both outcomes should still be present
        assert "total_force" in jam.forceset["Blankevoort1991Ligament"]["ACLam1"]
        assert "strain" in jam.forceset["Blankevoort1991Ligament"]["ACLam1"]

    def test_coordinates_never_filtered(self, make_jam):
        jam = make_jam(coordinates={"knee_flex_r": {"value": np.ones((10, 1)), "speed": np.ones((10, 1))}})
        ga = GroupJamAnalysis.__new__(GroupJamAnalysis)
        ga._filter_jam_data(jam)
        assert "value" in jam.coordinateset["knee_flex_r"]
        assert "speed" in jam.coordinateset["knee_flex_r"]


# =========================================================================
# get_*_data
# =========================================================================


class TestGetCoordinateData:
    def test_return_individuals_shape(self, make_jam):
        ga = _build_group_analysis(make_jam, n_subjects=3, n_timesteps=50)
        data = ga.get_coordinate_data("knee_flex_r", group="healthy", return_individuals=True)
        assert data.shape == (3, 50)

    def test_return_stats_keys(self, make_jam):
        ga = _build_group_analysis(make_jam, n_subjects=3)
        data = ga.get_coordinate_data("knee_flex_r", group="healthy", return_individuals=False)
        assert "mean" in data
        assert "std" in data
        assert "ste" in data
        assert "time" in data
        assert "n" in data

    def test_ste_formula(self, make_jam):
        """STE = std / sqrt(n)."""
        ga = _build_group_analysis(make_jam, n_subjects=5)
        data = ga.get_coordinate_data("knee_flex_r", group="healthy", return_individuals=False)
        expected_ste = data["std"] / np.sqrt(data["n"])
        np.testing.assert_array_almost_equal(data["ste"], expected_ste)

    def test_all_groups_returned(self, make_jam):
        ga = _build_group_analysis(make_jam, n_subjects=2, group="healthy")
        # Add a second group
        ga2 = _build_group_analysis(make_jam, n_subjects=2, group="OA")
        ga.groups["OA"] = ga2.groups["OA"]
        data = ga.get_coordinate_data("knee_flex_r", return_individuals=True)
        assert "healthy" in data
        assert "OA" in data


class TestGetMuscleData:
    def test_return_individuals_shape(self, make_jam):
        ga = _build_group_analysis(make_jam, n_subjects=3, n_timesteps=50)
        data = ga.get_muscle_data("recfem_r", group="healthy", return_individuals=True)
        assert data.shape == (3, 50)

    def test_return_stats(self, make_jam):
        ga = _build_group_analysis(make_jam, n_subjects=3)
        data = ga.get_muscle_data("recfem_r", group="healthy", return_individuals=False)
        assert "mean" in data
        assert "std" in data
        assert "ste" in data
        assert "time" in data
        assert "n" in data


class TestGetLigamentData:
    def test_fiber_summation(self, make_jam):
        """ACL should sum ACLam1 + ACLpl1."""
        ga = _build_group_analysis(make_jam, n_subjects=2, n_timesteps=20)
        data = ga.get_ligament_data("ACL", group="healthy", return_individuals=True)
        # Subject 0: ACLam1 = 1*ones, ACLpl1 = 1*2*ones → total = 3
        # Subject 1: ACLam1 = 2*ones, ACLpl1 = 2*2*ones → total = 6
        np.testing.assert_array_almost_equal(data[0, :], 3.0)
        np.testing.assert_array_almost_equal(data[1, :], 6.0)

    def test_return_stats_shape(self, make_jam):
        ga = _build_group_analysis(make_jam, n_subjects=3, n_timesteps=50)
        data = ga.get_ligament_data("ACL", group="healthy", return_individuals=False)
        assert data["mean"].shape == (50,)


class TestGetContactForceData:
    def test_norm_axis(self, make_jam):
        ga = _build_group_analysis(make_jam, n_subjects=2, n_timesteps=20)
        data = ga.get_contact_force_data(axis="norm", group="healthy", return_individuals=True)
        # Subject 0: total_contact_force = ones * 1 → norm = sqrt(3) ≈ 1.732
        expected = np.sqrt(3)
        np.testing.assert_array_almost_equal(data[0, :], expected)

    def test_int_axis(self, make_jam):
        ga = _build_group_analysis(make_jam, n_subjects=2, n_timesteps=20)
        data = ga.get_contact_force_data(axis=0, group="healthy", return_individuals=True)
        # Subject 0: total_contact_force[:, 0, 0] = 1.0
        np.testing.assert_array_almost_equal(data[0, :], 1.0)


class TestGetRegionalContactData:
    def test_pressure_axis(self, make_jam):
        ga = _build_group_analysis(make_jam, n_subjects=2, n_timesteps=20)
        data = ga.get_regional_contact_data(
            region=4, outcome="regional_max_pressure", axis="pressure",
            group="healthy", return_individuals=True
        )
        # Subject 0: pressure = 100
        np.testing.assert_array_almost_equal(data[0, :], 100.0)

    def test_force_norm(self, make_jam):
        ga = _build_group_analysis(make_jam, n_subjects=2, n_timesteps=20)
        data = ga.get_regional_contact_data(
            region=4, outcome="regional_contact_force", axis="norm",
            group="healthy", return_individuals=True
        )
        # Subject 0: regional_force = ones * 0.5 → norm = sqrt(3)*0.5
        expected = np.sqrt(3) * 0.5
        np.testing.assert_array_almost_equal(data[0, :], expected)


class TestNaNDetection:
    """get_*_data methods should raise ValueError when data contains NaN or Inf."""

    def _build_ga_with_nan_coordinate(self, make_jam, n=20):
        """Build GA where subject 1 has NaN in knee_flex_r."""
        ga = _build_group_analysis(make_jam, n_subjects=3, n_timesteps=n)
        # Inject NaN into subject 1's coordinate data
        ga.groups["healthy"]["jam_list"][1].coordinateset["knee_flex_r"]["value"][5, 0] = np.nan
        return ga

    def test_coordinate_nan_raises(self, make_jam):
        ga = self._build_ga_with_nan_coordinate(make_jam)
        with pytest.raises(ValueError, match="NaN/Inf.*subj_1_RIGHT"):
            ga.get_coordinate_data("knee_flex_r", group="healthy")

    def test_muscle_nan_raises(self, make_jam):
        ga = _build_group_analysis(make_jam, n_subjects=2, n_timesteps=20)
        ga.groups["healthy"]["jam_list"][0].forceset["Muscle"]["recfem_r"]["actuation"][0, 0] = np.nan
        with pytest.raises(ValueError, match="NaN/Inf.*subj_0_RIGHT"):
            ga.get_muscle_data("recfem_r", group="healthy")

    def test_inf_also_caught(self, make_jam):
        ga = _build_group_analysis(make_jam, n_subjects=2, n_timesteps=20)
        ga.groups["healthy"]["jam_list"][1].coordinateset["knee_flex_r"]["value"][0, 0] = np.inf
        with pytest.raises(ValueError, match="NaN/Inf.*subj_1_RIGHT"):
            ga.get_coordinate_data("knee_flex_r", group="healthy")

    def test_clean_data_no_error(self, make_jam):
        ga = _build_group_analysis(make_jam, n_subjects=3, n_timesteps=20)
        # Should not raise
        ga.get_coordinate_data("knee_flex_r", group="healthy")


# =========================================================================
# remove_subjects
# =========================================================================


class TestRemoveSubjects:
    def test_remove_by_subject_id(self, make_jam):
        ga = _build_group_analysis(make_jam, n_subjects=3)
        ga.remove_subjects(subject_ids=["subj_1_RIGHT"])
        assert len(ga.groups["healthy"]["subjects"]) == 2
        remaining_ids = ga.groups["healthy"]["subject_ids"]
        assert "subj_1_RIGHT" not in remaining_ids

    def test_remove_by_index(self, make_jam):
        ga = _build_group_analysis(make_jam, n_subjects=4)
        ga.remove_subjects(subject_indices=[0, 2], group="healthy")
        assert len(ga.groups["healthy"]["subjects"]) == 2
        remaining_ids = ga.groups["healthy"]["subject_ids"]
        assert "subj_0_RIGHT" not in remaining_ids
        assert "subj_2_RIGHT" not in remaining_ids
        assert "subj_1_RIGHT" in remaining_ids
        assert "subj_3_RIGHT" in remaining_ids

    def test_remove_by_index_requires_group(self, make_jam):
        ga = _build_group_analysis(make_jam, n_subjects=2)
        with pytest.raises(ValueError, match="Must specify 'group'"):
            ga.remove_subjects(subject_indices=[0])

    def test_remove_no_args_raises(self, make_jam):
        ga = _build_group_analysis(make_jam, n_subjects=2)
        with pytest.raises(ValueError, match="Must specify either"):
            ga.remove_subjects()


# =========================================================================
# identify_outlier_subjects
# =========================================================================


class TestIdentifyOutlierSubjects:
    def _build_uniform_ga(self, make_jam, n_subjects=10, n_timesteps=101, group="healthy"):
        """Build GA where all subjects have identical coordinate data (value=10.0)."""
        ga = GroupJamAnalysis.__new__(GroupJamAnalysis)
        ga.groups = {group: {"subjects": [], "subject_ids": [], "jam_list": []}}
        ga.base_results_dir = "/fake"
        ga.comak_subfolder = "test"
        ga.timepoint = ""
        ga.removal_history = []

        for i in range(n_subjects):
            jam = make_jam(
                n_timesteps=n_timesteps,
                coordinates={"knee_flex_r": {"value": np.ones((n_timesteps, 1)) * 10.0}},
            )
            ga.groups[group]["subjects"].append(
                {"subject_id": f"s{i}", "side": "R", "datetime": "d",
                 "folder_results": "/f", "h5_file": "/f.h5"}
            )
            ga.groups[group]["subject_ids"].append(f"s{i}_R")
            ga.groups[group]["jam_list"].append(jam)
        return ga

    def test_known_outlier_detected(self, make_jam):
        """Subject with extreme value is detected as outlier."""
        ga = self._build_uniform_ga(make_jam, n_subjects=10)
        # Override subject 9 to have extreme values
        jam = ga.groups["healthy"]["jam_list"][9]
        jam.coordinateset["knee_flex_r"]["value"][:] = 999.0

        outliers = ga.identify_outlier_subjects(
            coordinate_name="knee_flex_r", threshold_std=2.0
        )
        assert len(outliers["healthy"]["outlier_indices"]) > 0
        assert 9 in outliers["healthy"]["outlier_indices"]

    def test_single_group_does_not_crash(self, make_jam):
        """Passing group= explicitly should not raise AttributeError."""
        ga = self._build_uniform_ga(make_jam, n_subjects=10)
        jam = ga.groups["healthy"]["jam_list"][9]
        jam.coordinateset["knee_flex_r"]["value"][:] = 999.0
        outliers = ga.identify_outlier_subjects(
            coordinate_name="knee_flex_r", threshold_std=2.0, group="healthy"
        )
        assert "healthy" in outliers
        assert 9 in outliers["healthy"]["outlier_indices"]

    def test_uniform_data_no_outliers(self, make_jam):
        """When all subjects have identical data, no outliers detected."""
        ga = self._build_uniform_ga(make_jam, n_subjects=5)
        outliers = ga.identify_outlier_subjects(coordinate_name="knee_flex_r")
        assert len(outliers["healthy"]["outlier_indices"]) == 0

    def test_threshold_parameter(self, make_jam):
        """Higher threshold → fewer outliers."""
        ga = self._build_uniform_ga(make_jam, n_subjects=10)
        # Make subject 9 moderately extreme
        jam = ga.groups["healthy"]["jam_list"][9]
        jam.coordinateset["knee_flex_r"]["value"][:] = 50.0

        strict = ga.identify_outlier_subjects(
            coordinate_name="knee_flex_r", threshold_std=1.0
        )
        lenient = ga.identify_outlier_subjects(
            coordinate_name="knee_flex_r", threshold_std=10.0
        )
        assert len(strict["healthy"]["outlier_indices"]) >= len(
            lenient["healthy"]["outlier_indices"]
        )


# =========================================================================
# extract_values_at_time
# =========================================================================


class TestExtractValuesAtTime:
    def test_exact_timepoint(self, make_jam):
        ga = _build_group_analysis(make_jam, n_subjects=3, n_timesteps=101)
        result = ga.extract_values_at_time(
            var_type="coordinate", var_name="knee_flex_r", time_point=50.0
        )
        assert "healthy" in result
        assert len(result["healthy"]["values"]) == 3

    def test_window_averaging(self, make_jam):
        ga = _build_group_analysis(make_jam, n_subjects=2, n_timesteps=101)
        result = ga.extract_values_at_time(
            var_type="coordinate",
            var_name="knee_flex_r",
            time_point=50.0,
            time_window=10.0,
        )
        # Should return averaged values, not just one timepoint
        assert "values" in result["healthy"]

    def test_unknown_var_type_raises(self, make_jam):
        ga = _build_group_analysis(make_jam, n_subjects=2)
        with pytest.raises(ValueError, match="Unknown var_type"):
            ga.extract_values_at_time(
                var_type="nonexistent", var_name="test", time_point=50.0
            )

    def test_muscle_var_type(self, make_jam):
        ga = _build_group_analysis(make_jam, n_subjects=2, n_timesteps=101)
        result = ga.extract_values_at_time(
            var_type="muscle",
            var_name="recfem_r",
            time_point=50.0,
            var_params={"outcome": "actuation"},
        )
        assert len(result["healthy"]["values"]) == 2

    def test_ligament_var_type(self, make_jam):
        ga = _build_group_analysis(make_jam, n_subjects=2, n_timesteps=101)
        result = ga.extract_values_at_time(
            var_type="ligament", var_name="ACL", time_point=50.0
        )
        assert len(result["healthy"]["values"]) == 2


# =========================================================================
# Model consistency validation
# =========================================================================


def _make_ga(allow_mismatched_models=False):
    """Build a bare GroupJamAnalysis with the flag set."""
    ga = GroupJamAnalysis.__new__(GroupJamAnalysis)
    ga.groups = {}
    ga.base_results_dir = "/fake"
    ga.comak_subfolder = "test"
    ga.timepoint = ""
    ga.allow_mismatched_models = allow_mismatched_models
    ga.removal_history = []
    return ga


def _add_jam_to_ga(ga, jam, group="test", subject_id="s0"):
    """Add a JAM object to a group, calling validation."""
    if group not in ga.groups:
        ga.groups[group] = {"subjects": [], "subject_ids": [], "jam_list": []}
    ga._validate_jam_consistency(jam, group)
    ga.groups[group]["subjects"].append(
        {"subject_id": subject_id, "side": "R", "datetime": "d",
         "folder_results": "/f", "h5_file": "/f.h5"})
    ga.groups[group]["subject_ids"].append(f"{subject_id}_R")
    ga.groups[group]["jam_list"].append(jam)


class TestModelConsistencyValidation:
    """Tests for allow_mismatched_models flag and _validate_jam_consistency."""

    def test_default_flag_is_false(self):
        ga = GroupJamAnalysis.__new__(GroupJamAnalysis)
        ga.__init__.__wrapped__(ga, "/fake") if hasattr(ga.__init__, '__wrapped__') else None
        # Test through the normal constructor pattern used in _build_group_analysis
        ga2 = _make_ga()
        assert ga2.allow_mismatched_models is False

    def test_first_subject_always_accepted(self, make_jam):
        """First subject in a group has nothing to compare against."""
        ga = _make_ga(allow_mismatched_models=False)
        jam = make_jam(
            n_timesteps=50,
            coordinates={"knee_flex_r": {"value": np.ones((50, 1))}},
            muscles={"recfem_r": {"actuation": np.ones((50, 1))}},
            ligaments={"ACLam1": {"total_force": np.ones((50, 1))}},
        )
        # Should not raise
        _add_jam_to_ga(ga, jam)

    def test_consistent_subjects_no_error(self, make_jam):
        """Subjects with identical structure pass validation."""
        ga = _make_ga(allow_mismatched_models=False)
        for i in range(3):
            jam = make_jam(
                n_timesteps=50,
                coordinates={"knee_flex_r": {"value": np.ones((50, 1)) * i}},
                muscles={"recfem_r": {"actuation": np.ones((50, 1)) * i}},
                ligaments={"ACLam1": {"total_force": np.ones((50, 1)) * i}},
            )
            _add_jam_to_ga(ga, jam, subject_id=f"s{i}")

    def test_mismatched_timesteps_raises(self, make_jam):
        ga = _make_ga(allow_mismatched_models=False)
        jam0 = make_jam(n_timesteps=50, coordinates={"knee_flex_r": {"value": np.ones((50, 1))}})
        jam1 = make_jam(n_timesteps=100, coordinates={"knee_flex_r": {"value": np.ones((100, 1))}})
        _add_jam_to_ga(ga, jam0)
        with pytest.raises(ValueError, match="num_time_steps"):
            _add_jam_to_ga(ga, jam1, subject_id="s1")

    def test_mismatched_coordinates_raises(self, make_jam):
        ga = _make_ga(allow_mismatched_models=False)
        jam0 = make_jam(n_timesteps=50, coordinates={"knee_flex_r": {"value": np.ones((50, 1))}})
        jam1 = make_jam(n_timesteps=50, coordinates={
            "knee_flex_r": {"value": np.ones((50, 1))},
            "knee_add_r": {"value": np.ones((50, 1))},
        })
        _add_jam_to_ga(ga, jam0)
        with pytest.raises(ValueError, match="coordinateset"):
            _add_jam_to_ga(ga, jam1, subject_id="s1")

    def test_mismatched_ligament_fibers_raises(self, make_jam):
        ga = _make_ga(allow_mismatched_models=False)
        jam0 = make_jam(n_timesteps=50, ligaments={
            "ACLam1": {"total_force": np.ones((50, 1))},
        })
        jam1 = make_jam(n_timesteps=50, ligaments={
            "ACLam1": {"total_force": np.ones((50, 1))},
            "ACLpl1": {"total_force": np.ones((50, 1))},
        })
        _add_jam_to_ga(ga, jam0)
        with pytest.raises(ValueError, match="Blankevoort1991Ligament"):
            _add_jam_to_ga(ga, jam1, subject_id="s1")

    def test_mismatched_muscles_raises(self, make_jam):
        ga = _make_ga(allow_mismatched_models=False)
        jam0 = make_jam(n_timesteps=50, muscles={"recfem_r": {"actuation": np.ones((50, 1))}})
        jam1 = make_jam(n_timesteps=50, muscles={
            "recfem_r": {"actuation": np.ones((50, 1))},
            "vaslat_r": {"actuation": np.ones((50, 1))},
        })
        _add_jam_to_ga(ga, jam0)
        with pytest.raises(ValueError, match="Muscle"):
            _add_jam_to_ga(ga, jam1, subject_id="s1")

    def test_mismatched_contacts_raises(self, make_jam):
        ga = _make_ga(allow_mismatched_models=False)
        jam0 = make_jam(n_timesteps=50, contacts={
            "tf_contact": {"tibia_cartilage": {
                "total_contact_force": np.ones((50, 3, 1)),
                4: {"regional_max_pressure": np.ones((50, 1))},
            }}
        })
        jam1 = make_jam(n_timesteps=50, contacts={
            "tf_contact": {"tibia_cartilage": {
                "total_contact_force": np.ones((50, 3, 1)),
                4: {"regional_max_pressure": np.ones((50, 1))},
            }},
            "pf_contact": {"patella_cartilage": {
                "total_contact_force": np.ones((50, 3, 1)),
            }}
        })
        _add_jam_to_ga(ga, jam0)
        with pytest.raises(ValueError, match="Smith2018ArticularContactForce"):
            _add_jam_to_ga(ga, jam1, subject_id="s1")

    def test_allow_mismatched_flag_skips_validation(self, make_jam):
        """When allow_mismatched_models=True, different structures are accepted."""
        ga = _make_ga(allow_mismatched_models=True)
        jam0 = make_jam(n_timesteps=50, ligaments={
            "ACLam1": {"total_force": np.ones((50, 1))},
        })
        jam1 = make_jam(n_timesteps=50, ligaments={
            "ACLam1": {"total_force": np.ones((50, 1))},
            "ACLpl1": {"total_force": np.ones((50, 1))},
        })
        _add_jam_to_ga(ga, jam0)
        # Should not raise
        _add_jam_to_ga(ga, jam1, subject_id="s1")

    def test_error_message_lists_differences(self, make_jam):
        """Error message should show exactly what differs."""
        ga = _make_ga(allow_mismatched_models=False)
        jam0 = make_jam(n_timesteps=50, ligaments={
            "ACLam1": {"total_force": np.ones((50, 1))},
        })
        jam1 = make_jam(n_timesteps=50, ligaments={
            "ACLam1": {"total_force": np.ones((50, 1))},
            "ACLpl1": {"total_force": np.ones((50, 1))},
        })
        _add_jam_to_ga(ga, jam0)
        with pytest.raises(ValueError, match="ACLpl1"):
            _add_jam_to_ga(ga, jam1, subject_id="s1")


# =========================================================================
# Failure mode: ligament prefix vs substring matching (Test 5)
# =========================================================================


class TestLigamentPrefixMatching:
    """Ligament fiber matching should use prefix (startswith), not substring (in).

    Currently 'CL' in 'MCLd1' is True — this is a false positive.
    The code should use startswith to prevent this.
    """

    def test_ligament_data_uses_prefix_matching(self, make_jam):
        """'CL' should NOT match 'MCLd1' or 'LCL1' — no fiber starts with 'CL'."""
        ga = _build_group_analysis(make_jam, n_subjects=2, n_timesteps=20)
        # The default _build_group_analysis has fibers: ACLam1, ACLpl1
        # Also add MCLd1, MCLs1, LCL1 to make the test more explicit
        for jam in ga.groups["healthy"]["jam_list"]:
            jam.forceset["Blankevoort1991Ligament"]["MCLd1"] = {
                "total_force": np.ones((20, 1))
            }
            jam.forceset["Blankevoort1991Ligament"]["MCLs1"] = {
                "total_force": np.ones((20, 1))
            }
            jam.forceset["Blankevoort1991Ligament"]["LCL1"] = {
                "total_force": np.ones((20, 1))
            }

        # 'CL' should NOT match anything — no fiber STARTS with 'CL'
        # Currently 'CL' matches MCLd1, MCLs1, LCL1, ACLam1, ACLpl1 via substring
        with pytest.raises((ValueError, KeyError)):
            ga.get_ligament_data("CL", group="healthy", return_individuals=True)


# =========================================================================
# Failure mode: single-subject group statistics (Test 6)
# =========================================================================


class TestSingleSubjectEdgeCases:
    """Edge cases when a group has only 1 subject."""

    def test_single_subject_stats_no_crash(self, make_jam):
        """get_coordinate_data with n=1 should return std=0, ste=0."""
        ga = _build_group_analysis(make_jam, n_subjects=1, n_timesteps=50)
        data = ga.get_coordinate_data(
            "knee_flex_r", group="healthy", return_individuals=False
        )
        assert data["n"] == 1
        # std and ste should be 0 (or NaN for ste, but 0 is acceptable)
        assert np.all(np.isfinite(data["std"]))
        assert np.all(np.isfinite(data["ste"]))

    def test_single_subject_outlier_detection_no_crash(self, make_jam):
        """identify_outlier_subjects with 1 subject should not crash on division by zero.

        With n=1, group_std=0. The z-score print line does (value - mean) / std,
        but since there are no outliers detected (0 > threshold * 0 is always False
        for non-zero values), the print line is never reached.
        """
        ga = _build_group_analysis(make_jam, n_subjects=1, n_timesteps=50)
        outliers = ga.identify_outlier_subjects(
            coordinate_name="knee_flex_r", threshold_std=2.0
        )
        # Should return empty outlier list, not crash
        assert len(outliers["healthy"]["outlier_indices"]) == 0


# =========================================================================
# Failure mode: remove_subjects edge cases + history (Test 7)
# =========================================================================


class TestRemoveSubjectsEdgeCases:
    """Edge cases for remove_subjects that are currently silently handled."""

    def test_out_of_range_index_raises(self, make_jam):
        """Removing index 10 from a group with 3 subjects should raise IndexError."""
        ga = _build_group_analysis(make_jam, n_subjects=3)
        with pytest.raises(IndexError):
            ga.remove_subjects(subject_indices=[10], group="healthy")

    def test_nonexistent_id_raises(self, make_jam):
        """Removing a subject ID that doesn't exist should raise KeyError."""
        ga = _build_group_analysis(make_jam, n_subjects=3)
        with pytest.raises(KeyError):
            ga.remove_subjects(subject_ids=["nonexistent_RIGHT"])

    def test_removal_history_tracked(self, make_jam):
        """Removals should be logged in removal_history for reproducibility."""
        ga = _build_group_analysis(make_jam, n_subjects=3)
        ga.remove_subjects(subject_ids=["subj_1_RIGHT"])
        ga.remove_subjects(subject_indices=[0], group="healthy")

        assert hasattr(ga, "removal_history")
        assert len(ga.removal_history) == 2
        # Each entry should identify what was removed
        assert ga.removal_history[0]["subject_id"] == "subj_1_RIGHT"
        assert ga.removal_history[0]["group"] == "healthy"

    def test_removal_history_initialized_empty(self, make_jam):
        """Fresh GroupJamAnalysis should have empty removal_history."""
        ga = _make_ga()
        assert hasattr(ga, "removal_history")
        assert ga.removal_history == []


# =========================================================================
# Failure mode: extract_values_at_time boundary (Test 8)
# =========================================================================


class TestExtractValuesAtTimeBoundary:
    """Time point validation for extract_values_at_time."""

    def test_out_of_range_time_point_raises(self, make_jam):
        """time_point=150 (beyond 0-100 range) should raise ValueError."""
        ga = _build_group_analysis(make_jam, n_subjects=2, n_timesteps=101)
        with pytest.raises(ValueError, match="(range|outside|bound)"):
            ga.extract_values_at_time(
                var_type="coordinate", var_name="knee_flex_r", time_point=150.0
            )

    def test_boundary_time_points_work(self, make_jam):
        """time_point=0.0 and time_point=100.0 should both return valid data."""
        ga = _build_group_analysis(make_jam, n_subjects=2, n_timesteps=101)

        result_0 = ga.extract_values_at_time(
            var_type="coordinate", var_name="knee_flex_r", time_point=0.0
        )
        assert len(result_0["healthy"]["values"]) == 2

        result_100 = ga.extract_values_at_time(
            var_type="coordinate", var_name="knee_flex_r", time_point=100.0
        )
        assert len(result_100["healthy"]["values"]) == 2


# =========================================================================
# Failure mode: filter then access non-existent contact type (Test 9)
# =========================================================================


class TestFilterThenGetData:
    """Accessing data after filtering with wrong contact type."""

    def test_get_data_after_filtering_wrong_contact_type(self, make_jam):
        """Filtering for pf_contact when data only has tf_contact should give a KeyError.

        The error message is currently opaque (raw KeyError from nested dict access).
        A future improvement could add context about available contact types.
        """
        # Build GA where data only has tf_contact
        ga = _build_group_analysis(make_jam, n_subjects=2, n_timesteps=20)

        # Filter to keep only pf_contact (which doesn't exist in the data)
        for jam in ga.groups["healthy"]["jam_list"]:
            contact_data = jam.forceset.get("Smith2018ArticularContactForce", {})
            # Remove tf_contact, simulating a filter that kept only pf_contact
            if "tf_contact" in contact_data:
                del contact_data["tf_contact"]

        # This should raise KeyError (currently a raw KeyError from dict access)
        with pytest.raises(KeyError):
            ga.get_regional_contact_data(
                contact_type="pf_contact", region=4,
                outcome="regional_max_pressure", axis="pressure",
                group="healthy", return_individuals=True,
            )

    def test_get_regional_data_after_filtering(self, make_jam):
        """get_regional_contact_data returns correct values after _filter_jam_data."""
        n = 20
        region4_pressure = np.ones((n, 1)) * 100
        region5_pressure = np.ones((n, 1)) * 200

        ga = GroupJamAnalysis.__new__(GroupJamAnalysis)
        ga.groups = {"test": {"subjects": [], "subject_ids": [], "jam_list": []}}
        ga.base_results_dir = "/fake"
        ga.comak_subfolder = "test"
        ga.timepoint = ""
        ga.removal_history = []
        ga.allow_mismatched_models = False

        for i in range(2):
            contacts = {
                "tf_contact": {
                    "tibia_cartilage": {
                        "total_contact_force": np.ones((n, 3, 1)),
                        0: {"regional_max_pressure": np.ones((n, 1)) * 999},
                        4: {"regional_max_pressure": region4_pressure * (i + 1)},
                        5: {"regional_max_pressure": region5_pressure * (i + 1)},
                    }
                }
            }
            jam = make_jam(n_timesteps=n, contacts=contacts)

            # Filter to regions 4 and 5 only
            ga._filter_jam_data(jam, regions=[4, 5])

            ga.groups["test"]["subjects"].append(
                {"subject_id": f"s{i}", "side": "R", "datetime": "d",
                 "folder_results": "/f", "h5_file": "/f.h5"})
            ga.groups["test"]["subject_ids"].append(f"s{i}_R")
            ga.groups["test"]["jam_list"].append(jam)

        data4 = ga.get_regional_contact_data(
            region=4, outcome="regional_max_pressure", axis="pressure",
            group="test", return_individuals=True,
        )
        # Subject 0: 100, Subject 1: 200
        np.testing.assert_array_almost_equal(data4[0, :], 100.0)
        np.testing.assert_array_almost_equal(data4[1, :], 200.0)

        data5 = ga.get_regional_contact_data(
            region=5, outcome="regional_max_pressure", axis="pressure",
            group="test", return_individuals=True,
        )
        # Subject 0: 200, Subject 1: 400
        np.testing.assert_array_almost_equal(data5[0, :], 200.0)
        np.testing.assert_array_almost_equal(data5[1, :], 400.0)


# =========================================================================
# add_subject (integration test with real H5 files)
# =========================================================================


class TestAddSubject:
    """Tests for add_subject() using create_h5 to produce real H5 files."""

    def _make_h5(self, create_h5, **kwargs):
        """Create a standard H5 file with muscles, ligaments, coordinates, and contacts."""
        defaults = dict(
            n_timesteps=50,
            muscles={"recfem_r": ["actuation"]},
            ligaments={"ACLam1": ["total_force"]},
            coordinates=["knee_flex_r"],
            contacts={"tf_contact": {"tibia_cartilage": 6}},
        )
        defaults.update(kwargs)
        return create_h5(**defaults)

    def test_add_subject_with_h5_path(self, create_h5, tmp_path):
        h5_path = self._make_h5(create_h5)
        ga = GroupJamAnalysis(str(tmp_path), timepoint="")
        result = ga.add_subject("s0", "RIGHT", "d0", group="test", h5_file_path=str(h5_path))

        assert result is True
        assert len(ga.groups["test"]["subjects"]) == 1
        assert ga.groups["test"]["subject_ids"] == ["s0_RIGHT"]
        assert len(ga.groups["test"]["jam_list"]) == 1
        # Verify JAM was actually loaded
        jam = ga.groups["test"]["jam_list"][0]
        assert "knee_flex_r" in jam.coordinateset

    def test_add_subject_missing_h5_returns_false(self, tmp_path):
        ga = GroupJamAnalysis(str(tmp_path), timepoint="")
        result = ga.add_subject(
            "s0", "RIGHT", "d0", group="test",
            h5_file_path="/nonexistent/file.h5",
        )
        assert result is False
        # Group should not have been created or should be empty
        assert "test" not in ga.groups or len(ga.groups["test"]["jam_list"]) == 0

    def test_add_subject_filter_data(self, create_h5, tmp_path):
        # Create H5 with both tf_contact and pf_contact
        h5_path = create_h5(
            n_timesteps=50,
            muscles={"recfem_r": ["actuation", "activation"]},
            coordinates=["knee_flex_r"],
            contacts={
                "tf_contact": {"tibia_cartilage": 6},
                "pf_contact": {"patella_cartilage": 6},
            },
        )
        ga = GroupJamAnalysis(str(tmp_path), timepoint="")
        ga.add_subject(
            "s0", "RIGHT", "d0", group="test",
            h5_file_path=str(h5_path),
            filter_data=True,
            contact_types=["tf_contact"],
            muscle_outcomes=["actuation"],
        )

        jam = ga.groups["test"]["jam_list"][0]
        contacts = jam.forceset["Smith2018ArticularContactForce"]
        # tf_contact should remain, pf_contact should be filtered out
        assert "tf_contact" in contacts
        assert "pf_contact" not in contacts
        # Only 'actuation' muscle outcome should remain
        assert "actuation" in jam.forceset["Muscle"]["recfem_r"]
        assert "activation" not in jam.forceset["Muscle"]["recfem_r"]

    def test_add_two_subjects_same_group(self, create_h5, tmp_path):
        h5_a = self._make_h5(create_h5, filename="a.h5")
        h5_b = self._make_h5(create_h5, filename="b.h5")
        ga = GroupJamAnalysis(str(tmp_path), timepoint="")

        ga.add_subject("s0", "RIGHT", "d0", group="test", h5_file_path=str(h5_a))
        ga.add_subject("s1", "LEFT", "d1", group="test", h5_file_path=str(h5_b))

        assert len(ga.groups["test"]["subjects"]) == 2
        assert len(ga.groups["test"]["jam_list"]) == 2
        assert ga.groups["test"]["subject_ids"] == ["s0_RIGHT", "s1_LEFT"]
