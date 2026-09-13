from __future__ import annotations

import math
import pytest

from masck_one.dry_side_resource_producer import build_dry_side_resource_producer

HEAD = "b" * 40


def test_dry_side_producer_exports_service_geometry_without_inventing_resources():
    manifest = build_dry_side_resource_producer(owner_head_sha=HEAD)
    assert manifest["schema"] == "MASCK_ONE_DRY_SIDE_RESOURCE_PRODUCER_V1"
    assert manifest["owner"]["pr"] == 142
    assert manifest["physical_validation_complete"] is False
    assert len(manifest["sources"]) == 3
    assert all(len(source["git_blob_sha"]) == 40 for source in manifest["sources"])
    assert all(source["evidence_class"] == "SOURCE_BOUND_DIGITAL_PACKAGE" for source in manifest["sources"])

    harness = manifest["harness"]
    assert harness["route_volume_mm3"] > 0
    assert math.isfinite(harness["route_volume_mm3"])
    assert harness["service_loop_extra_path_mm"] >= harness["service_loop_min_extra_path_mm"]
    assert len(harness["pcb_handoff_datum_world_mm"]) == 3
    assert len(harness["disconnect_mating_datum_world_mm"]) == 3
    assert len(harness["clip_bounds_world_mm"]) == 2

    contract = manifest["resource_contract"]
    assert contract["unknown_policy"] == "NEVER_ZERO_FILL"
    for key in (
        "component_masses_g",
        "mass_total_g",
        "mass_cg_world_mm",
        "energy_per_cycle_Wh",
        "release_reserve",
        "electrical_ratings",
    ):
        assert contract[key] is None


def test_dry_side_producer_keeps_route_inside_declared_dry_bay():
    manifest = build_dry_side_resource_producer(owner_head_sha=HEAD)
    xmin, xmax, ymin, ymax, zmin, zmax = manifest["containment"]["dry_bay_bounds_world_mm"]
    rb = manifest["harness"]["route_bounds_world_mm"]
    assert rb[0] >= xmin
    assert rb[1] <= xmax
    assert rb[2] >= ymin
    assert rb[3] <= ymax
    assert rb[4] >= zmin
    assert rb[5] <= zmax


@pytest.mark.parametrize("bad", ["", "abc", "0" * 39, "0" * 41, "G" * 40, "z" * 40])
def test_dry_side_producer_rejects_non_exact_owner_identity(bad):
    with pytest.raises(ValueError):
        build_dry_side_resource_producer(owner_head_sha=bad)
