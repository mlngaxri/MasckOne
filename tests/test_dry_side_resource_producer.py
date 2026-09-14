from __future__ import annotations

import math
import pytest

from masck_one.dry_side_resource_producer import build_dry_side_resource_producer

HEAD = "b" * 40


def test_dry_side_producer_exports_service_geometry_without_inventing_resources():
    manifest = build_dry_side_resource_producer(owner_head_sha=HEAD)
    assert manifest["schema"] == "MASCK_ONE_DRY_SIDE_RESOURCE_PRODUCER_V6"
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

    harness_component = next(c for c in manifest["components"] if c["component_id"] == "DRY_SIDE_HARNESS_ROUTE_ENVELOPE")
    assert harness_component["source_git_blob_sha"] == next(
        source["git_blob_sha"] for source in manifest["sources"]
        if source["path"] == "src/masck_one/dry_side_harness_service.py"
    )
    assert harness_component["transform_to_world_mm"] == [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]
    assert harness_component["bounds_world_mm"] == harness["route_bounds_world_mm"]
    assert harness_component["mass_g"] is None
    assert harness_component["mass_source"].startswith("UNKNOWN_")

    service = manifest["service_envelope"]
    assert service["route_bounds_world_mm"] == harness["route_bounds_world_mm"]
    assert service["clip_bounds_world_mm"] == harness["clip_bounds_world_mm"]
    assert service["transform_to_world_mm"] == harness_component["transform_to_world_mm"]

    contract = manifest["resource_contract"]
    assert contract["unknown_policy"] == "NEVER_ZERO_FILL"
    for key in (
        "component_masses_g", "mass_total_g", "mass_cg_world_mm",
        "energy_per_cycle_Wh", "release_reserve", "electrical_ratings",
    ):
        assert contract[key] is None


def test_disconnect_is_source_bound_and_service_sweep_is_exported_without_electrical_claims():
    manifest = build_dry_side_resource_producer(owner_head_sha=HEAD)
    disconnect = manifest["disconnect"]
    component = next(c for c in manifest["components"] if c["component_id"] == "DRY_SIDE_CONNECTOR_RESERVATION")
    source = next(s for s in manifest["sources"] if s["path"] == "src/masck_one/dry_side_disconnect_interface.py")
    assert component["source_git_blob_sha"] == source["git_blob_sha"]
    assert component["bounds_world_mm"] == disconnect["connector_reservation_bounds_world_mm"]
    assert component["volume_mm3"] > 0
    assert component["mass_g"] is None
    assert component["mass_source"] == "UNKNOWN_CONNECTOR_UNSELECTED"
    assert disconnect["travel_mm"] > 0
    assert len(disconnect["mating_datum_world_mm"]) == 3
    assert len(disconnect["mating_axis_world"]) == 3
    assert disconnect["connector_selected"] is False
    assert disconnect["electrical_ratings_selected"] is False
    assert manifest["service_envelope"]["disconnect_sweep_bounds_world_mm"] == disconnect["service_sweep_bounds_world_mm"]
    assert manifest["service_envelope"]["disconnect_travel_mm"] == disconnect["travel_mm"]


def test_battery_benchmark_is_exported_but_cannot_be_promoted_to_production_mass_cg_or_transform():
    manifest = build_dry_side_resource_producer(owner_head_sha=HEAD)
    battery = manifest["battery_packaging_benchmark"]
    source = next(item for item in manifest["sources"] if item["path"] == "src/masck_one/battery_benchmark.py")
    assert battery["source_git_blob_sha"] == source["git_blob_sha"]
    assert battery["mass_g"] > 0
    assert battery["mass_evidence_class"] == "AUTHORITY_PACKAGING_BENCHMARK_NOT_PRODUCTION_MASS"
    assert battery["production_selected"] is False
    assert battery["supplier_document_bound"] is False
    assert battery["runtime_validated"] is False
    contract = manifest["resource_contract"]
    assert contract["battery_benchmark_mass_g"] == battery["mass_g"]
    assert contract["battery_benchmark_mass_class"] == "REFERENCE_ONLY_NOT_AGGREGATABLE_AS_PRODUCTION_MASS"
    assert contract["battery_benchmark_cg_world_mm"] == battery["cg_world_mm"]
    if battery["transform_to_world_mm"] is None:
        assert battery["transform_evidence_class"] == "UNKNOWN_NO_SOURCE_BOUND_WORLD_TRANSFORM"
        assert contract["battery_benchmark_transform_to_world_mm"] is None
        assert contract["battery_benchmark_transform_class"] == "UNKNOWN"
    else:
        assert battery["transform_evidence_class"] == "SOURCE_BOUND_MODEL_TRANSFORM"
        assert contract["battery_benchmark_transform_to_world_mm"] == battery["transform_to_world_mm"]
        assert contract["battery_benchmark_transform_class"] == "REFERENCE_ONLY_SOURCE_BOUND"
    if battery["cg_world_mm"] is None:
        assert battery["cg_evidence_class"] == "UNKNOWN_NO_SOURCE_BOUND_BENCHMARK_CG"
        assert contract["battery_benchmark_cg_class"] == "UNKNOWN"
    else:
        assert len(battery["cg_world_mm"]) == 3
        assert all(math.isfinite(float(v)) for v in battery["cg_world_mm"])
        assert battery["cg_evidence_class"] == "AUTHORITY_PACKAGING_BENCHMARK_NOT_PRODUCTION_CG"
        assert contract["battery_benchmark_cg_class"] == "REFERENCE_ONLY_NOT_AGGREGATABLE_AS_PRODUCTION_CG"
    assert contract["mass_total_g"] is None
    assert contract["mass_cg_world_mm"] is None


def test_dry_side_producer_keeps_route_and_disconnect_service_sweep_inside_declared_dry_bay():
    manifest = build_dry_side_resource_producer(owner_head_sha=HEAD)
    xmin, xmax, ymin, ymax, zmin, zmax = manifest["containment"]["dry_bay_bounds_world_mm"]
    for rb in (manifest["harness"]["route_bounds_world_mm"], manifest["disconnect"]["service_sweep_bounds_world_mm"]):
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
