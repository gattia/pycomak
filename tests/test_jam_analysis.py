"""
Tests for JamAnalysis H5 parsing — the most critical module in pycomak.

Every downstream module (GroupJamAnalysis, forsim criteria, plotting) depends on
correct parsing of H5 files. These tests verify:
- Entry point validation (bad inputs)
- Single-file shape correctness for every data type
- Multi-file stacking along the last axis
- Edge cases (missing groups, 1D regional data)
- Failure modes (mismatched files, truncated data, region counts)
"""

import warnings

import numpy as np
import h5py
import pytest

from pycomak.jam_analysis import JamAnalysis


# =========================================================================
# Entry point validation
# =========================================================================


class TestJamAnalysisEntryValidation:
    """Tests for jam_analysis() input validation."""

    def test_rejects_non_list_input(self):
        jam = JamAnalysis()
        with pytest.raises(Exception, match="should be type `list` or `tuple`"):
            jam.jam_analysis("not_a_list.h5")

    def test_rejects_non_h5_file(self, create_h5, tmp_path):
        # Create a non-h5 file
        bad_file = tmp_path / "data.csv"
        bad_file.write_text("a,b,c\n1,2,3")
        with pytest.raises(Exception, match="not `.h5` format"):
            jam = JamAnalysis()
            jam.jam_analysis([str(bad_file)])

    def test_missing_file_tracked_not_crashed(self, tmp_path):
        """Missing files are counted and recorded, not crashed on."""
        jam = JamAnalysis()
        jam.jam_analysis([str(tmp_path / "nonexistent.h5")])
        assert jam.num_missing_files == 1
        assert len(jam.missing_files) == 1
        assert jam.missing_files[0]["idx"] == 0

    def test_default_names_are_string_indices(self, create_h5):
        h5 = create_h5(muscles={"recfem_r": ["actuation"]})
        jam = JamAnalysis()
        jam.jam_analysis([str(h5)])
        assert jam.names == ["0"]

    def test_custom_names_used(self, create_h5):
        h5 = create_h5(muscles={"recfem_r": ["actuation"]})
        jam = JamAnalysis()
        jam.jam_analysis([str(h5)], names=["subject_A"])
        assert jam.names == ["subject_A"]

    def test_accepts_tuple_input(self, create_h5):
        h5 = create_h5(muscles={"recfem_r": ["actuation"]})
        jam = JamAnalysis()
        jam.jam_analysis((str(h5),))
        assert jam.num_files == 1


# =========================================================================
# Single-file shape validation
# =========================================================================


class TestSingleFileShapes:
    """Verify output shapes from a single H5 file."""

    @pytest.fixture(autouse=True)
    def _setup(self, create_h5):
        self.n = 101
        self.h5 = create_h5(
            n_timesteps=self.n,
            muscles={"recfem_r": ["actuation", "activation"]},
            ligaments={"ACLam1": ["total_force", "strain"]},
            contacts={"tf_contact": {"tibia_cartilage": 6}},
            coordinates=["knee_flex_r", "knee_add_r"],
            comak_items=["convergence"],
            data_fill="linear",
        )
        self.jam = JamAnalysis()
        self.jam.jam_analysis([str(self.h5)])

    def test_time_vector(self):
        assert self.jam.time.shape == (self.n,)

    def test_muscle_shape(self):
        data = self.jam.forceset["Muscle"]["recfem_r"]["actuation"]
        assert data.shape == (self.n, 1)

    def test_ligament_shape(self):
        data = self.jam.forceset["Blankevoort1991Ligament"]["ACLam1"]["total_force"]
        assert data.shape == (self.n, 1)

    def test_coordinate_value_shape(self):
        data = self.jam.coordinateset["knee_flex_r"]["value"]
        assert data.shape == (self.n, 1)

    def test_coordinate_speed_shape(self):
        data = self.jam.coordinateset["knee_flex_r"]["speed"]
        assert data.shape == (self.n, 1)

    def test_contact_total_force_shape(self):
        contact = self.jam.forceset["Smith2018ArticularContactForce"]
        data = contact["tf_contact"]["tibia_cartilage"]["total_contact_force"]
        assert data.shape == (self.n, 3, 1)

    def test_regional_contact_force_shape(self):
        """regional_contact_force from a Group → (n_timesteps, 3, 1) per region."""
        contact = self.jam.forceset["Smith2018ArticularContactForce"]
        data = contact["tf_contact"]["tibia_cartilage"][0]["regional_contact_force"]
        assert data.shape == (self.n, 3, 1)

    def test_regional_scalar_pressure_shape(self):
        """regional_max_pressure from a Dataset → (n_timesteps, 1) per region."""
        contact = self.jam.forceset["Smith2018ArticularContactForce"]
        data = contact["tf_contact"]["tibia_cartilage"][0]["regional_max_pressure"]
        assert data.shape == (self.n, 1)

    def test_six_regions_initialized(self):
        """Each cartilage surface should have integer keys 0-5."""
        contact = self.jam.forceset["Smith2018ArticularContactForce"]
        mesh = contact["tf_contact"]["tibia_cartilage"]
        for r in range(6):
            assert r in mesh, f"Region {r} not found"

    def test_comak_data_shape(self):
        data = self.jam.comak["convergence"]
        assert data.shape == (self.n, 1)


# =========================================================================
# Multi-file stacking
# =========================================================================


class TestMultiFileStacking:
    """Verify that loading two files stacks along the last axis."""

    @pytest.fixture(autouse=True)
    def _setup(self, create_h5):
        self.n = 50

        self.h5_a = create_h5(
            filename="a.h5",
            n_timesteps=self.n,
            muscles={"recfem_r": ["actuation"]},
            ligaments={"ACLam1": ["total_force"]},
            contacts={"tf_contact": {"tibia_cartilage": 6}},
            coordinates=["knee_flex_r"],
            comak_items=["convergence"],
            data_fill="zeros",
        )
        self.h5_b = create_h5(
            filename="b.h5",
            n_timesteps=self.n,
            muscles={"recfem_r": ["actuation"]},
            ligaments={"ACLam1": ["total_force"]},
            contacts={"tf_contact": {"tibia_cartilage": 6}},
            coordinates=["knee_flex_r"],
            comak_items=["convergence"],
            data_fill="linear",
        )

        self.jam = JamAnalysis()
        self.jam.jam_analysis([str(self.h5_a), str(self.h5_b)])

    def test_muscle_stacked(self):
        data = self.jam.forceset["Muscle"]["recfem_r"]["actuation"]
        assert data.shape == (self.n, 2)

    def test_ligament_stacked(self):
        data = self.jam.forceset["Blankevoort1991Ligament"]["ACLam1"]["total_force"]
        assert data.shape == (self.n, 2)

    def test_coordinate_stacked(self):
        data = self.jam.coordinateset["knee_flex_r"]["value"]
        assert data.shape == (self.n, 2)

    def test_contact_force_stacked(self):
        contact = self.jam.forceset["Smith2018ArticularContactForce"]
        data = contact["tf_contact"]["tibia_cartilage"]["total_contact_force"]
        assert data.shape == (self.n, 3, 2)

    def test_regional_force_stacked(self):
        contact = self.jam.forceset["Smith2018ArticularContactForce"]
        data = contact["tf_contact"]["tibia_cartilage"][0]["regional_contact_force"]
        assert data.shape == (self.n, 3, 2)

    def test_regional_scalar_stacked(self):
        contact = self.jam.forceset["Smith2018ArticularContactForce"]
        data = contact["tf_contact"]["tibia_cartilage"][0]["regional_max_pressure"]
        assert data.shape == (self.n, 2)

    def test_comak_stacked(self):
        data = self.jam.comak["convergence"]
        assert data.shape == (self.n, 2)

    def test_data_values_in_correct_column(self):
        """File A is zeros, file B is linear ramp. Values should land in correct columns."""
        data = self.jam.forceset["Muscle"]["recfem_r"]["actuation"]
        # Column 0 = file A (zeros)
        assert np.allclose(data[:, 0], 0.0)
        # Column 1 = file B (linear ramp, non-zero)
        assert not np.allclose(data[:, 1], 0.0)


# =========================================================================
# Edge cases
# =========================================================================


class TestEdgeCases:
    """Edge cases and special handling."""

    def test_missing_forceset_group(self, tmp_path):
        """H5 file with no /model/forceset → forceset stays empty dict."""
        filepath = tmp_path / "no_forceset.h5"
        with h5py.File(filepath, "w") as f:
            f.create_dataset("time", data=np.linspace(0, 1, 50))
            f.create_dataset("model/coordinateset/knee_flex_r/value", data=np.zeros(50))
            f.create_dataset("model/coordinateset/knee_flex_r/speed", data=np.zeros(50))

        jam = JamAnalysis()
        jam.jam_analysis([str(filepath)])
        # Forceset should be empty since there's no forceset group
        assert "Muscle" not in jam.forceset
        assert "Blankevoort1991Ligament" not in jam.forceset
        # But coordinates should work
        assert "knee_flex_r" in jam.coordinateset

    def test_missing_comak_group(self, create_h5):
        """H5 file with no /comak → comak stays empty dict."""
        h5 = create_h5(muscles={"recfem_r": ["actuation"]}, comak_items=None)
        jam = JamAnalysis()
        jam.jam_analysis([str(h5)])
        assert jam.comak == {}

    def test_1d_regional_scalar_data(self, tmp_path):
        """Regional scalar data with shape (n_timesteps,) instead of (n_timesteps, n_regions)."""
        filepath = tmp_path / "1d_regional.h5"
        n = 50
        with h5py.File(filepath, "w") as f:
            f.create_dataset("time", data=np.linspace(0, 1, n))
            base = "model/forceset/Smith2018ArticularContactForce/tf_contact/tibia_cartilage"
            f.create_dataset(f"{base}/total_contact_force", data=np.zeros((n, 3)))
            # 1D regional data (only 1 region effectively)
            f.create_dataset(f"{base}/regional_max_pressure", data=np.ones(n))

        jam = JamAnalysis()
        jam.jam_analysis([str(filepath)])
        # Should not crash; data should be stored
        contact = jam.forceset["Smith2018ArticularContactForce"]
        data = contact["tf_contact"]["tibia_cartilage"][0]["regional_max_pressure"]
        assert data.shape == (n, 1)

    def test_custom_base_name(self, tmp_path):
        """Custom base_name parameter is used."""
        filepath = tmp_path / "custom_base.h5"
        n = 30
        with h5py.File(filepath, "w") as f:
            f.create_dataset("time", data=np.linspace(0, 1, n))
            f.create_dataset("custom/coordinateset/test_coord/value", data=np.zeros(n))
            f.create_dataset("custom/coordinateset/test_coord/speed", data=np.zeros(n))

        jam = JamAnalysis()
        jam.jam_analysis([str(filepath)], base_name="custom")
        assert "test_coord" in jam.coordinateset

    def test_mismatched_timesteps_raises(self, create_h5):
        """Loading H5 files with different timestep counts should fail.

        Arrays are pre-allocated from the first file's timestep count, so a second
        file with a different count will crash on numpy broadcasting.
        """
        h5_a = create_h5(filename="short.h5", n_timesteps=50,
                         muscles={"recfem_r": ["actuation"]})
        h5_b = create_h5(filename="long.h5", n_timesteps=100,
                         muscles={"recfem_r": ["actuation"]})
        jam = JamAnalysis()
        with pytest.raises(Exception):
            jam.jam_analysis([str(h5_a), str(h5_b)])

    def test_all_files_missing_attributes(self, tmp_path):
        """When all files are missing, time/num_time_steps are never set."""
        jam = JamAnalysis()
        jam.jam_analysis([
            str(tmp_path / "missing_a.h5"),
            str(tmp_path / "missing_b.h5"),
        ])
        assert jam.num_missing_files == 2
        assert jam.num_files == 2
        # time and num_time_steps are never set when all files are missing
        assert not hasattr(jam, "time")
        assert not hasattr(jam, "num_time_steps")



# =========================================================================
# Data integrity (values, not just shapes)
# =========================================================================


class TestDataIntegrity:
    """Verify actual data values are read correctly, not just shapes."""

    def test_muscle_data_matches_h5(self, tmp_path):
        """Data read from H5 matches what was written."""
        filepath = tmp_path / "integrity.h5"
        n = 20
        expected = np.arange(n, dtype=float)

        with h5py.File(filepath, "w") as f:
            f.create_dataset("time", data=np.linspace(0, 1, n))
            f.create_dataset("model/forceset/Muscle/test_muscle/actuation", data=expected)

        jam = JamAnalysis()
        jam.jam_analysis([str(filepath)])
        actual = jam.forceset["Muscle"]["test_muscle"]["actuation"][:, 0]
        np.testing.assert_array_equal(actual, expected)

    def test_contact_force_data_matches_h5(self, tmp_path):
        filepath = tmp_path / "contact_integrity.h5"
        n = 20
        expected = np.arange(n * 3, dtype=float).reshape(n, 3)

        with h5py.File(filepath, "w") as f:
            f.create_dataset("time", data=np.linspace(0, 1, n))
            base = "model/forceset/Smith2018ArticularContactForce/tf/cart"
            f.create_dataset(f"{base}/total_contact_force", data=expected)

        jam = JamAnalysis()
        jam.jam_analysis([str(filepath)])
        contact = jam.forceset["Smith2018ArticularContactForce"]
        actual = contact["tf"]["cart"]["total_contact_force"][:, :, 0]
        np.testing.assert_array_equal(actual, expected)

    def test_regional_scalar_data_per_region(self, tmp_path):
        """Each region gets the correct column from the (n_timesteps, n_regions) dataset."""
        filepath = tmp_path / "regional_integrity.h5"
        n = 20
        n_regions = 6
        pressure_data = np.arange(n * n_regions, dtype=float).reshape(n, n_regions)

        with h5py.File(filepath, "w") as f:
            f.create_dataset("time", data=np.linspace(0, 1, n))
            base = "model/forceset/Smith2018ArticularContactForce/tf/cart"
            f.create_dataset(f"{base}/total_contact_force", data=np.zeros((n, 3)))
            f.create_dataset(f"{base}/regional_max_pressure", data=pressure_data)

        jam = JamAnalysis()
        jam.jam_analysis([str(filepath)])
        contact = jam.forceset["Smith2018ArticularContactForce"]

        for r in range(n_regions):
            actual = contact["tf"]["cart"][r]["regional_max_pressure"][:, 0]
            np.testing.assert_array_equal(actual, pressure_data[:, r])


# =========================================================================
# Failure mode: mismatched H5 file structures (Test 1)
# =========================================================================


class TestMismatchedFiles:
    """JamAnalysis should detect when multiple H5 files have different structures.

    Currently, mismatched structures silently produce arrays with zeros in columns
    where the data doesn't exist — this is silent data corruption for scientific data.
    """

    def test_mismatched_muscles_raises_by_default(self, create_h5):
        """File A has 2 muscles, file B has 1. Should raise, not silently zero-fill."""
        h5_a = create_h5(
            filename="two_muscles.h5", n_timesteps=50,
            muscles={"recfem_r": ["actuation"], "vaslat_r": ["actuation"]},
        )
        h5_b = create_h5(
            filename="one_muscle.h5", n_timesteps=50,
            muscles={"recfem_r": ["actuation"]},
        )
        jam = JamAnalysis()
        with pytest.raises(ValueError, match="structure"):
            jam.jam_analysis([str(h5_a), str(h5_b)])

    def test_mismatched_ligaments_raises_by_default(self, create_h5):
        """File A has 2 ligament fibers, file B has 1. Should raise ValueError."""
        h5_a = create_h5(
            filename="two_ligs.h5", n_timesteps=50,
            ligaments={"ACLam1": ["total_force"], "ACLpl1": ["total_force"]},
        )
        h5_b = create_h5(
            filename="one_lig.h5", n_timesteps=50,
            ligaments={"ACLam1": ["total_force"]},
        )
        jam = JamAnalysis()
        with pytest.raises(ValueError, match="structure"):
            jam.jam_analysis([str(h5_a), str(h5_b)])

    def test_mismatched_files_allowed_with_flag(self, create_h5):
        """With explicit opt-in flag, mismatched structures should be allowed."""
        h5_a = create_h5(
            filename="two_muscles_ok.h5", n_timesteps=50,
            muscles={"recfem_r": ["actuation"], "vaslat_r": ["actuation"]},
        )
        h5_b = create_h5(
            filename="one_muscle_ok.h5", n_timesteps=50,
            muscles={"recfem_r": ["actuation"]},
        )
        jam = JamAnalysis()
        # Should NOT raise when explicitly allowed
        jam.jam_analysis([str(h5_a), str(h5_b)], allow_mismatched_files=True)
        # vaslat_r column 1 should be zeros (no data from file B)
        data = jam.forceset["Muscle"]["vaslat_r"]["actuation"]
        assert np.allclose(data[:, 1], 0.0)


# =========================================================================
# Failure mode: truncated H5 data (Test 2)
# =========================================================================


class TestTruncatedH5Data:
    """Simulation crashes can produce H5 files with inconsistent dataset lengths."""

    def test_truncated_dataset_raises_error(self, tmp_path):
        """When a dataset has fewer timesteps than /time, an error should be raised.

        Currently numpy raises a broadcasting error (opaque). Ideally the code
        would catch this and raise a clear ValueError mentioning the dataset
        path and the length mismatch, but at minimum it should not silently succeed.
        """
        filepath = tmp_path / "truncated.h5"
        with h5py.File(filepath, "w") as f:
            f.create_dataset("time", data=np.linspace(0, 1, 101))
            # Muscle dataset is truncated (only 50 timesteps instead of 101)
            f.create_dataset(
                "model/forceset/Muscle/recfem_r/actuation",
                data=np.ones(50),
            )

        jam = JamAnalysis()
        with pytest.raises(Exception):
            jam.jam_analysis([str(filepath)])


# =========================================================================
# Failure mode: calling jam_analysis() twice (Test 3)
# =========================================================================


class TestDoubleCall:
    """Calling jam_analysis() twice on the same object corrupts internal state."""

    def test_calling_jam_analysis_twice_raises(self, create_h5):
        """Second call to jam_analysis() should raise RuntimeError."""
        h5_a = create_h5(
            filename="first.h5", n_timesteps=50,
            muscles={"recfem_r": ["actuation"]},
        )
        h5_b = create_h5(
            filename="second.h5", n_timesteps=50,
            muscles={"recfem_r": ["actuation"]},
        )
        jam = JamAnalysis()
        jam.jam_analysis([str(h5_a)])
        with pytest.raises(RuntimeError, match="already been called"):
            jam.jam_analysis([str(h5_b)])


# =========================================================================
# Failure mode: contact regions != 6 (Test 4)
# =========================================================================


class TestRegionCounts:
    """The code hardcodes 6 regions. Test behavior when actual count differs."""

    def test_fewer_than_6_regions_accessible(self, tmp_path):
        """With 3 regions, regions 0-2 have data and regions 3-5 are empty dicts."""
        filepath = tmp_path / "three_regions.h5"
        n = 50
        n_regions = 3
        with h5py.File(filepath, "w") as f:
            f.create_dataset("time", data=np.linspace(0, 1, n))
            base = "model/forceset/Smith2018ArticularContactForce/tf/cart"
            f.create_dataset(f"{base}/total_contact_force", data=np.zeros((n, 3)))
            # Only 3 regions of regional data
            for r in range(n_regions):
                f.create_dataset(
                    f"{base}/regional_contact_force/{r}",
                    data=np.ones((n, 3)) * (r + 1),
                )
            f.create_dataset(
                f"{base}/regional_max_pressure",
                data=np.ones((n, n_regions)),
            )

        jam = JamAnalysis()
        jam.jam_analysis([str(filepath)])
        contact = jam.forceset["Smith2018ArticularContactForce"]["tf"]["cart"]

        # Regions 0-2 should have pressure data
        for r in range(n_regions):
            assert "regional_max_pressure" in contact[r]

        # Regions 3-5 should be empty dicts (initialized but no data)
        for r in range(n_regions, 6):
            assert r in contact  # key exists
            assert contact[r] == {}  # but no data

    def test_more_than_6_regions_warns(self, tmp_path):
        """With 8 regions, data for regions 6-7 is silently dropped. Should warn."""
        filepath = tmp_path / "eight_regions.h5"
        n = 50
        n_regions = 8
        pressure_data = np.arange(n * n_regions, dtype=float).reshape(n, n_regions)

        with h5py.File(filepath, "w") as f:
            f.create_dataset("time", data=np.linspace(0, 1, n))
            base = "model/forceset/Smith2018ArticularContactForce/tf/cart"
            f.create_dataset(f"{base}/total_contact_force", data=np.zeros((n, 3)))
            for r in range(n_regions):
                f.create_dataset(
                    f"{base}/regional_contact_force/{r}",
                    data=np.ones((n, 3)),
                )
            f.create_dataset(f"{base}/regional_max_pressure", data=pressure_data)

        jam = JamAnalysis()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            jam.jam_analysis([str(filepath)])
            # Should issue a warning about truncated regions
            region_warnings = [x for x in w if "region" in str(x.message).lower()]
            assert len(region_warnings) > 0, "Expected warning about regions being dropped"

        # First 6 regions should still have correct data
        contact = jam.forceset["Smith2018ArticularContactForce"]["tf"]["cart"]
        for r in range(6):
            actual = contact[r]["regional_max_pressure"][:, 0]
            np.testing.assert_array_equal(actual, pressure_data[:, r])
