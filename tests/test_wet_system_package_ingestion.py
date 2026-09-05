from __future__ import annotations

import json
from pathlib import Path
import subprocess

import cadquery as cq
import pytest

from masck_one.fresh_pump_packaging import ROUTE_IDS as FRESH_ROUTE_IDS
from masck_one.realized_waste_backbone import PHASE_MIXED_WASTE
from masck_one.structural_frame import RESERVATION_HMI_ELECTRONICS
from masck_one.waste_pump_architecture import (
    BARRIER_WASTE,
    INTERFACE_BARRIER_OUTLET,
    INTERFACE_CARTRIDGE_INLET_I27,
    ROUTE_IDS as WASTE_ROUTE_IDS,
)
from masck_one.wet_system_package_ingestion import (
    CONTROLLED_ENVELOPE,
    FROZEN_HYGIENE_CLASSES,
    REALIZED_ROUTE,
    SOURCE_BLOBS,
    SOURCE_MAIN_SHA,
    TOPOLOGY_ONLY,
    UNRESOLVED,
    WetSystemPackageIntegration,
    build_wet_system_package_integration,
    export_wet_system_package_review,
)


@pytest.fixture(scope="module")
def wet_integration() -> WetSystemPackageIntegration:
    return build_wet_system_package_integration()


def _git(*args: str) -> str:
    return subprocess.check_output(("git", *args), text=True).strip()


def test_wet_integration_is_bound_to_exact_released_main_and_source_blobs():
    _git("cat-file", "-e", f"{SOURCE_MAIN_SHA}^{{commit}}")
    assert subprocess.run(
        ("git", "merge-base", "--is-ancestor", SOURCE_MAIN_SHA, "HEAD"),
        check=False,
    ).returncode == 0
    for path, expected_blob in SOURCE_BLOBS:
        assert _git("hash-object", path) == expected_blob


def test_released_package_references_are_geometry_not_realization_claims(
    wet_integration: WetSystemPackageIntegration,
):
    components = {item.component_id: item for item in wet_integration.components}

    water = components["WET-WATER-RESERVOIR-PACKAGE-REFERENCE"]
    cartridge = components["WET-WASTE-CARTRIDGE-PACKAGE-REFERENCE"]
    battery = components["DRY-BATTERY-PACKAGING-BENCHMARK"]
    for record in (water, cartridge, battery):
        assert record.maturity == CONTROLLED_ENVELOPE
        assert record.geometry is not None
        shape = record.geometry.val()
        assert shape.isValid()
        assert len(shape.Solids()) == 1
        assert shape.Volume() > 0.0
        assert len(record.manifest()["brep_sha256"]) == 64

    assert "NOT_REALIZED_RESERVOIR_BODY" in water.evidence_status
    assert "KEY_SEAL_SERVICE_TRAJECTORY" in cartridge.evidence_status
    assert "NOT_PRODUCTION_BATTERY" in battery.evidence_status


def test_unreleased_dry_bay_harness_and_hmi_remain_geometry_free(
    wet_integration: WetSystemPackageIntegration,
):
    components = {item.component_id: item for item in wet_integration.components}
    for component_id in ("DRY-BAY", "HARNESS", "HMI"):
        record = components[component_id]
        assert record.maturity == UNRESOLVED
        assert record.geometry is None
        assert record.geometry_source is None
        assert record.interface_ids == (RESERVATION_HMI_ELECTRONICS,)
        assert "CURRENT_RELEASED" in record.evidence_status


def test_released_fresh_routes_remain_topology_only_without_invented_geometry(
    wet_integration: WetSystemPackageIntegration,
):
    routes = wet_integration.routes[: len(FRESH_ROUTE_IDS)]
    assert tuple(item.route_id for item in routes) == FRESH_ROUTE_IDS
    assert all(item.maturity == TOPOLOGY_ONLY for item in routes)
    assert all(item.service_aabb is None for item in routes)
    assert all(item.centerline_length_mm is None for item in routes)
    assert all(item.geometric_dead_volume_mL is None for item in routes)
    assert tuple(item.fluid_identity for item in routes) == (
        "FRESH_WATER",
        "FRESH_WATER",
        "CLEANSER",
        "CLEANSER",
    )


def test_released_mixed_waste_routes_keep_passive_backflow_order_and_service_aabbs(
    wet_integration: WetSystemPackageIntegration,
):
    routes = wet_integration.routes[len(FRESH_ROUTE_IDS) :]
    assert tuple(item.route_id for item in routes) == WASTE_ROUTE_IDS
    assert all(item.maturity == REALIZED_ROUTE for item in routes)
    assert all(item.fluid_identity == PHASE_MIXED_WASTE for item in routes)
    assert all(item.centerline_length_mm is not None and item.centerline_length_mm > 0.0 for item in routes)
    assert all(item.geometric_dead_volume_mL is not None and item.geometric_dead_volume_mL > 0.0 for item in routes)
    assert all(item.service_envelope_radius_mm == pytest.approx(3.2, abs=1e-12) for item in routes)

    for item in routes:
        assert item.service_aabb is not None
        shape = item.service_aabb.val()
        assert shape.isValid()
        assert len(shape.Solids()) == 1
        assert shape.Volume() > 0.0
        manifest = item.manifest()
        assert len(manifest["service_aabb_brep_sha256"]) == 64
        assert "NOT_TUBING_CHANNEL_OR_PHYSICAL_CLEARANCE_EVIDENCE" in manifest["service_aabb_semantics"]

    assert routes[1].target_interface_id == BARRIER_WASTE
    assert routes[2].source_interface_id == INTERFACE_BARRIER_OUTLET
    assert routes[2].target_interface_id == INTERFACE_CARTRIDGE_INLET_I27


def test_cavity_ledger_uses_only_producer_owned_authority_classes_or_explicit_unresolved(
    wet_integration: WetSystemPackageIntegration,
):
    by_id = {item.cavity_id: item for item in wet_integration.cavities}
    assert by_id["CAVITY-WATER-RESERVOIR"].classification == "WET_REMOVABLE"
    assert by_id["CAVITY-CLEANSER-RESERVOIR"].classification == "WET_REMOVABLE"
    for region in ("FOREHEAD", "LEFT_CHEEK", "RIGHT_CHEEK", "NOSE_T_ZONE", "CHIN_PERIORAL"):
        assert by_id[f"CAVITY-WASTE-ACQUISITION-{region}"].classification == "WET_DRAINABLE"

    assert by_id["CAVITY-WASTE-CARTRIDGE"].classification is None
    assert by_id["CAVITY-FRESH-WATER-PUMP"].classification is None
    assert by_id["CAVITY-CLEANSER-PUMP"].classification is None
    assert by_id["CAVITY-DRY-BAY"].classification is None
    assert all(
        item.classification is None or item.classification in FROZEN_HYGIENE_CLASSES
        for item in wet_integration.cavities
    )


def test_unmerged_cell4_realizations_are_not_smuggled_into_released_component_truth(
    wet_integration: WetSystemPackageIntegration,
):
    components = {item.component_id: item for item in wet_integration.components}
    cleanser = components["WET-CLEANSER-RESERVOIR"]
    water_pump = components["WET-FRESH-WATER-PUMP"]
    assert cleanser.geometry is None
    assert cleanser.maturity == TOPOLOGY_ONLY
    assert "CURRENT_REALIZED_CLEANSER_MODULE_PR_NOT_CONSUMED" in cleanser.evidence_status
    assert water_pump.geometry is None
    assert water_pump.maturity == TOPOLOGY_ONLY
    assert "PACKAGE_SELECTION_AND_GEOMETRY_UNRESOLVED" in water_pump.evidence_status


def test_manifest_is_deterministic_and_physical_evidence_stays_fail_closed(
    wet_integration: WetSystemPackageIntegration,
):
    first = wet_integration.manifest()
    second = wet_integration.manifest()
    assert first == second
    assert len(wet_integration.integration_sha256) == 64
    assert first["integration_sha256"] == wet_integration.integration_sha256
    assert first["physical_validation_eligible"] is False
    assert "NOT_FLOW_LEAKAGE_RECOVERY" in first["evidence_status"]
    assert "DRY_BAY_PCB_HARNESS_CHARGING_AND_PHYSICAL_HMI_HAVE_NO_CURRENT_RELEASED_PRODUCER" in first["unresolved_integration"]
    assert "WET_DRY_BULKHEAD_DRAIN_DRY_AND_WHOLE_PRODUCT_HYGIENE_CLOSURE_UNRESOLVED" in first["unresolved_integration"]


def test_review_export_roundtrips_package_and_route_reservation_geometry(
    tmp_path: Path,
    wet_integration: WetSystemPackageIntegration,
):
    outputs = export_wet_system_package_review(tmp_path, wet_integration)
    by_name = {path.name: path for path in outputs}
    assert "cell1_wet_package_reference_compound.step" in by_name
    assert "cell1_wet_system_package_ingestion_manifest.json" in by_name

    compound = cq.importers.importStep(str(by_name["cell1_wet_package_reference_compound.step"]))
    assert compound.val().isValid()
    assert len(compound.val().Solids()) >= 3

    route_steps = sorted(name for name in by_name if name.endswith("service_aabb_reference.step"))
    assert len(route_steps) == len(WASTE_ROUTE_IDS)
    for name in route_steps:
        shape = cq.importers.importStep(str(by_name[name])).val()
        assert shape.isValid()
        assert len(shape.Solids()) == 1

    manifest = json.loads(
        by_name["cell1_wet_system_package_ingestion_manifest.json"].read_text(encoding="utf-8")
    )
    assert manifest["schema"] == "MASCK_ONE_CELL1_WET_SYSTEM_PACKAGE_INGESTION_V1"
    assert manifest["integration_sha256"] == wet_integration.integration_sha256
    assert manifest["physical_validation_eligible"] is False
