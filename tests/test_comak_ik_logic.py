"""
Tests for comak_ik.py ligament strain update logic.

Tests update_ligament_reference_strain() and update_multiple_ligament_reference_strains()
using a lightweight mock object with ref_force_info dict (no OpenSim needed).
"""

import pytest


class FakeComakIK:
    """Lightweight stand-in for COMAKInverseKinematics with just ref_force_info."""

    def __init__(self, ref_force_info):
        self.ref_force_info = ref_force_info

    # Bind the actual methods from the real class
    def update_ligament_reference_strain(self, ligament_name, new_reference_strain):
        from pycomak.comak_ik import COMAKInverseKinematics

        COMAKInverseKinematics.update_ligament_reference_strain(
            self, ligament_name, new_reference_strain
        )

    def update_multiple_ligament_reference_strains(self, strain_updates):
        from pycomak.comak_ik import COMAKInverseKinematics

        COMAKInverseKinematics.update_multiple_ligament_reference_strains(
            self, strain_updates
        )


@pytest.fixture
def fake_ik():
    """Create a FakeComakIK with representative ref_force_info."""
    ref_info = {
        "MCLd1": {
            "class": "Blankevoort1991Ligament",
            "reference_strain": 0.04,
            "length": 0.05,
            "slack_length": 0.048,
        },
        "ACLam1": {
            "class": "Blankevoort1991Ligament",
            "reference_strain": -0.14,
            "length": 0.03,
            "slack_length": 0.035,
        },
        "recfem_r": {
            "class": "Millard2012EquilibriumMuscle",
            "reference_strain": None,
            "length": 0.35,
            "slack_length": None,
        },
    }
    return FakeComakIK(ref_info)


class TestUpdateLigamentReferenceStrain:
    def test_updates_value_correctly(self, fake_ik):
        fake_ik.update_ligament_reference_strain("MCLd1", 0.10)
        assert fake_ik.ref_force_info["MCLd1"]["reference_strain"] == 0.10

    def test_keyerror_with_available_ligaments(self, fake_ik):
        with pytest.raises(KeyError, match="not found in ref_force_info"):
            fake_ik.update_ligament_reference_strain("NONEXISTENT", 0.05)

    def test_valueerror_when_not_ligament(self, fake_ik):
        """Updating a muscle (not a ligament) raises ValueError."""
        with pytest.raises(ValueError, match="not a ligament"):
            fake_ik.update_ligament_reference_strain("recfem_r", 0.05)

    def test_negative_strain_accepted(self, fake_ik):
        fake_ik.update_ligament_reference_strain("ACLam1", -0.20)
        assert fake_ik.ref_force_info["ACLam1"]["reference_strain"] == -0.20


class TestUpdateMultipleLigamentReferenceStrains:
    def test_multiple_updates(self, fake_ik):
        fake_ik.update_multiple_ligament_reference_strains(
            {"MCLd1": 0.05, "ACLam1": 0.02}
        )
        assert fake_ik.ref_force_info["MCLd1"]["reference_strain"] == 0.05
        assert fake_ik.ref_force_info["ACLam1"]["reference_strain"] == 0.02

    def test_single_bad_name_raises(self, fake_ik):
        with pytest.raises(KeyError):
            fake_ik.update_multiple_ligament_reference_strains(
                {"MCLd1": 0.05, "BAD_NAME": 0.02}
            )
        # MCLd1 should have been updated before the error
        assert fake_ik.ref_force_info["MCLd1"]["reference_strain"] == 0.05
