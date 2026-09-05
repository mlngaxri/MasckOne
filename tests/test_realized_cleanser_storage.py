from dataclasses import replace

import pytest

from masck_one.cleanser_storage import PORT_IDS, build_cleanser_storage_architecture
from masck_one.realized_cleanser_storage import (
    CAVITY_X_MM,
    CAVITY_Y_MM,
    CAVITY_Z_MM,
    OUTLET_Y_MM,
    RealizedCleanserStorageError,
    SERVICE_SEQUENCE_IDS,
)


def test_realized_cleanser_storage_binds_current_architecture_without_mutating_topology_contract(
    cell4_authority,
    cell4_cleanser_storage,
):
    architecture = build_cleanser_storage_architecture(cell4_authority)
    realized = cell4_cleanser_storage

    assert realized.source_architecture_sha256 == architecture.architecture_sha256
    assert realized.validate_current_sources(cell4_authority) == architecture
    assert realized.fluid_identity == "CLEANSER"
    assert realized.reservoir_cavity_classification == "WET_REMOVABLE"
    assert realized.mount_cavity_classification == "WET_DRAINABLE"
    assert realized.physical_validation_eligible is False

    # The released Iteration 21 contract remains topology-only. Geometric accounting
    # lives only in the realized layer and must not silently promote its blocked fields.
    assert architecture.storage_capacity_mL is None
    assert architecture.dead_volume_mL is None
    assert architecture.purge_volume_mL is None


def test_realized_cleanser_geometry_has_deterministic_cavity_and_exact_controlled_ports(
    cell4_cleanser_storage,
):
    realized = cell4_cleanser_storage
    manifest = realized.manifest()

    assert realized.geometric_cavity_volume_mL == pytest.approx(
        CAVITY_X_MM * CAVITY_Y_MM * CAVITY_Z_MM / 1000.0,
        abs=1e-9,
    )
    assert realized.geometric_cavity_volume_mL == pytest.approx(3.072, abs=1e-9)
    assert realized.neutral_geometry_below_outlet_center_plane_mL == pytest.approx(0.192, abs=1e-9)
    assert tuple(port["port_id"] for port in manifest["ports"]) == PORT_IDS
    assert {port["fluid_identity"] for port in manifest["ports"]} == {"CLEANSER"}
    assert manifest["geometry"]["volume_evidence_role"] == (
        "GEOMETRIC_ACCOUNTING_ONLY_NOT_DRAWABLE_VOLUME_OR_SERVICE_CADENCE"
    )
    assert OUTLET_Y_MM > manifest["geometry"]["center_world_mm"][1] - CAVITY_Y_MM / 2.0
    assert manifest["physical_validation_eligible"] is False
    assert manifest["manifest_sha256"] == realized.manifest_sha256


def test_material_body_cradle_key_and_reference_solids_are_single_valid_breps(cell4_cleanser_storage):
    realized = cell4_cleanser_storage
    for shape in (
        realized.body_solid,
        realized.cradle_solid,
        realized.retention_key_solid,
        realized.internal_cavity_solid,
        realized.refill_bore_solid,
        realized.purge_bore_solid,
        realized.outlet_bore_solid,
        realized.refill_closure_reservation_solid,
        realized.purge_connector_reservation_solid,
        realized.outlet_connector_reservation_solid,
        realized.drain_path_reference_solid,
        realized.cassette_service_sweep_solid,
        realized.key_service_sweep_solid,
    ):
        assert shape.solids().size() == 1
        assert shape.val().isValid()
        assert shape.val().Volume() > 0.0

    # The fluid cavity and the three actual bores are voids, not overlapping material.
    assert realized.body_solid.val().intersect(realized.internal_cavity_solid.val()).Volume() <= 1e-7
    assert realized.body_solid.val().intersect(realized.refill_bore_solid.val()).Volume() <= 1e-7
    assert realized.body_solid.val().intersect(realized.purge_bore_solid.val()).Volume() <= 1e-7
    assert realized.body_solid.val().intersect(realized.outlet_bore_solid.val()).Volume() <= 1e-7


def test_cradle_key_and_body_are_nonintersecting_in_assembled_state_with_positive_capture_path(
    cell4_cleanser_storage,
):
    realized = cell4_cleanser_storage

    assert realized.body_solid.val().intersect(realized.cradle_solid.val()).Volume() <= 1e-7
    assert realized.body_solid.val().intersect(realized.retention_key_solid.val()).Volume() <= 1e-7
    assert realized.cradle_solid.val().intersect(realized.retention_key_solid.val()).Volume() <= 1e-7
    assert tuple(step.step_id for step in realized.service_sequence) == SERVICE_SEQUENCE_IDS
    assert realized.service_sequence[0].translation_world_mm[0] > 0.0
    assert realized.service_sequence[1].translation_world_mm[2] < 0.0
    assert all("MASK_REMOVED" in step.precondition for step in realized.service_sequence)


def test_stale_architecture_wrong_fluid_and_evidence_promotion_fail_closed(
    cell4_authority,
    cell4_cleanser_storage,
):
    realized = cell4_cleanser_storage

    with pytest.raises(RealizedCleanserStorageError, match="stale for current cleanser architecture"):
        replace(realized, source_architecture_sha256="0" * 64).validate_current_sources(cell4_authority)
    with pytest.raises(RealizedCleanserStorageError, match="exact CLEANSER"):
        replace(realized, fluid_identity="FRESH_WATER")
    with pytest.raises(RealizedCleanserStorageError, match="cannot become physical validation"):
        replace(realized, physical_validation_eligible=True)
