from dataclasses import replace

import pytest

from masck_one.authority import load_authority
from masck_one.cleanser_storage import PORT_IDS
from masck_one.cleanser_service_interfaces import (
    PICKUP_LUMEN_DIAMETER_MM,
    SERVICE_SEQUENCE_IDS,
    VENT_FEATURE_ID,
    CleanserServiceGeometryError,
    build_cleanser_service_geometry,
)
from masck_one.realized_cleanser_storage import OUTLET_BORE_DIAMETER_MM, build_realized_cleanser_storage


def test_cleanser_service_geometry_binds_exact_realized_storage_and_preserves_fluid_identity():
    authority = load_authority()
    storage = build_realized_cleanser_storage(authority)
    geometry = build_cleanser_service_geometry(authority)

    assert geometry.source_storage_manifest_sha256 == storage.manifest_sha256
    assert geometry.validate_current_sources(authority).manifest_sha256 == storage.manifest_sha256
    assert geometry.fluid_identity == "CLEANSER"
    assert geometry.physical_validation_eligible is False
    assert geometry.manifest()["controlled_port_ids"] == list(PORT_IDS)
    assert geometry.manifest()["fresh_water_identity_unchanged"] is True
    assert "PASSIVE_BACKFLOW_PROTECTION" in geometry.manifest()["mixed_waste_architecture_unchanged"]


def test_fill_purge_closure_vent_and_pickup_are_actual_deterministic_breps():
    geometry = build_cleanser_service_geometry(load_authority())

    for shape in (
        geometry.ported_body_solid,
        geometry.service_closure_solid,
        geometry.service_retention_key_solid,
        geometry.fill_seal_reference_solid,
        geometry.purge_seal_reference_solid,
        geometry.vent_lumen_solid,
        geometry.vent_barrier_reservation_solid,
        geometry.pickup_tube_solid,
        geometry.pickup_lumen_solid,
        geometry.service_closure_sweep_solid,
        geometry.service_key_sweep_solid,
    ):
        assert shape.solids().size() == 1
        assert shape.val().isValid()
        assert shape.val().Volume() > 0.0

    assert geometry.ported_body_solid.val().intersect(geometry.vent_lumen_solid.val()).Volume() <= 1e-7
    assert geometry.pickup_tube_solid.val().intersect(geometry.pickup_lumen_solid.val()).Volume() <= 1e-7
    assert geometry.ported_body_solid.val().intersect(geometry.service_closure_solid.val()).Volume() <= 1e-7
    assert geometry.ported_body_solid.val().intersect(geometry.service_retention_key_solid.val()).Volume() <= 1e-7
    assert geometry.service_closure_solid.val().intersect(geometry.service_retention_key_solid.val()).Volume() <= 1e-7


def test_vent_is_not_promoted_to_a_fourth_controlled_liquid_port_and_pickup_preserves_outlet_bore():
    geometry = build_cleanser_service_geometry(load_authority())
    manifest = geometry.manifest()

    assert manifest["vent"]["feature_id"] == VENT_FEATURE_ID
    assert manifest["vent"]["feature_role"] == "HEADSPACE_GAS_EXCHANGE_FEATURE_NOT_FOURTH_CONTROLLED_LIQUID_PORT"
    assert manifest["controlled_port_ids"] == list(PORT_IDS)
    assert PICKUP_LUMEN_DIAMETER_MM == OUTLET_BORE_DIAMETER_MM
    assert manifest["pickup"]["lumen_diameter_mm"] == OUTLET_BORE_DIAMETER_MM
    assert manifest["pickup"]["outlet_port_id"] == "CLEANSER-PORT-OUTLET"


def test_refill_and_purge_service_requires_key_then_closure_withdrawal_and_defines_no_viscosity_limit():
    geometry = build_cleanser_service_geometry(load_authority())
    manifest = geometry.manifest()

    assert tuple(step.step_id for step in geometry.service_sequence) == SERVICE_SEQUENCE_IDS
    assert geometry.service_sequence[0].translation_world_mm[0] > 0.0
    assert geometry.service_sequence[1].translation_world_mm[2] < 0.0
    assert "CLOSURE_REMOVAL_EXPOSES_EXISTING_REALIZED_REFILL_BORE" == manifest["service_closure"]["refill_access_status"]
    assert "CLOSURE_REMOVAL_EXPOSES_EXISTING_REALIZED_PURGE_BORE" == manifest["service_closure"]["purge_access_status"]
    assert manifest["viscosity_limit_mPa_s"] is None
    assert "NOT_DEFINED" in manifest["viscosity_status"]


def test_stale_storage_wrong_fluid_and_evidence_promotion_fail_closed():
    authority = load_authority()
    geometry = build_cleanser_service_geometry(authority)

    with pytest.raises(CleanserServiceGeometryError, match="stale for realized storage"):
        replace(geometry, source_storage_manifest_sha256="0" * 64).validate_current_sources(authority)
    with pytest.raises(CleanserServiceGeometryError, match="exact CLEANSER"):
        replace(geometry, fluid_identity="FRESH_WATER")
    with pytest.raises(CleanserServiceGeometryError, match="cannot become physical validation"):
        replace(geometry, physical_validation_eligible=True)
