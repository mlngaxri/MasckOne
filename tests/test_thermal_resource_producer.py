from __future__ import annotations

import math
import pytest

from masck_one.thermal_resource_producer import build_thermal_resource_producer


HEAD = "a" * 40


def test_producer_exports_geometry_without_inventing_mass_or_energy():
    manifest = build_thermal_resource_producer(owner_head_sha=HEAD)
    assert manifest["schema"] == "MASCK_ONE_THERMAL_RESOURCE_PRODUCER_V2"
    assert manifest["owner"]["pr"] == 143
    assert manifest["physical_validation_complete"] is False
    assert manifest["fluid"]["classification"] == "GEOMETRIC_VOID_NOT_RETAINED_CAPACITY"
    assert manifest["fluid"]["retained_capacity_mm3"] is None
    assert manifest["energy"]["heater_electrical_input"] is None
    assert manifest["energy"]["cooling_energy"] is None
    assert manifest["energy"]["dock_reset_energy"] is None
    assert manifest["components"]
    for component in manifest["components"]:
        assert component["volume_mm3"] > 0
        assert math.isfinite(component["volume_mm3"])
        assert component["geometry_evidence"] == "EXACT_SOURCE_BREP"
        assert component["mass_g"] is None
        assert component["mass_cg_world_mm"] is None
        assert component["mass_evidence"].startswith("UNKNOWN_")
        assert len(component["geometric_centroid_world_mm"]) == 3


def test_producer_preserves_exact_face_footprint_and_geometric_void():
    manifest = build_thermal_resource_producer(owner_head_sha=HEAD)
    assert manifest["face_facing"]["left_contact_plate_footprint_mm"] == [22.0, 28.0]
    assert manifest["face_facing"]["right_contact_plate_footprint_mm"] == [22.0, 28.0]
    assert manifest["face_facing"]["evidence"] == "EXACT_CAD_DIMENSION"
    assert manifest["fluid"]["pcm_internal_void_each_mm3"] > 0


def test_producer_exports_explicit_world_transforms_and_never_zero_fills_unknowns():
    manifest = build_thermal_resource_producer(owner_head_sha=HEAD)
    identity = [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]
    assert manifest["source"]["evidence_class"] == "SOURCE_BOUND_DIGITAL_GEOMETRY"
    for component in manifest["components"]:
        assert component["transform_to_world_4x4"] == identity
        assert component["transform_evidence"] == "SOURCE_BREP_ALREADY_AUTHORED_IN_WORLD_FRAME"
    contract = manifest["resource_contract"]
    assert contract["unknown_policy"] == "NEVER_ZERO_FILL"
    for key in (
        "mass_total_g",
        "mass_cg_world_mm",
        "energy_per_cycle_Wh",
        "thermal_safety",
        "condensation_behavior",
    ):
        assert contract[key] is None


@pytest.mark.parametrize("bad", ["", "abc", "0" * 39, "0" * 41])
def test_producer_rejects_non_exact_owner_identity(bad):
    with pytest.raises(ValueError):
        build_thermal_resource_producer(owner_head_sha=bad)