from dataclasses import replace

import pytest

from masck_one.authority import load_authority
from masck_one.realized_water_reservoir import (
    DATUM_IDS,
    DATUM_SERVICE_WITHDRAWAL,
    FLUID_IDENTITY,
    INTERNAL_DEPTH_Z_MM,
    INTERNAL_HEIGHT_Y_MM,
    INTERNAL_WIDTH_X_MM,
    OUTER_DEPTH_Z_MM,
    OUTER_HEIGHT_Y_MM,
    OUTER_WIDTH_X_MM,
    PHYSICAL_EVIDENCE_STATUS,
    PORT_FILL,
    PORT_PICKUP,
    PORT_VENT,
    SERVICE_WITHDRAWAL_TRAVEL_MM,
    WALL_THICKNESS_MM,
    build_realized_water_reservoir,
)
from masck_one.water_reservoir import WaterReservoirError, build_water_reservoir_architecture


def test_realized_reservoir_closes_authority_volume_with_actual_internal_geometry():
    authority = load_authority()
    realized = build_realized_water_reservoir(authority)

    assert realized.gross_geometric_volume_mL == pytest.approx(6.5, abs=1e-12)
    assert realized.neutral_geometric_dead_volume_mL == pytest.approx(0.65, abs=1e-12)
    assert realized.neutral_geometric_usable_volume_mL == pytest.approx(5.85, abs=1e-12)
    assert realized.gross_target_met is True
    assert realized.minimum_usable_met is True
    assert realized.gross_target_mL == authority.number("fluid", "water_reservoir", "gross_mL")
    assert realized.minimum_usable_mL == authority.number("fluid", "water_reservoir", "minimum_usable_mL")


def test_realized_reservoir_has_controlled_cavity_walls_lid_and_package_bounds():
    realized = build_realized_water_reservoir(load_authority())

    assert realized.wall_thickness_mm == WALL_THICKNESS_MM == 1.0
    assert realized.body_solid.solids().size() == 1
    assert realized.lid_solid.solids().size() == 1
    assert realized.cavity_solid.solids().size() == 1
    assert realized.body_solid.val().isValid()
    assert realized.lid_solid.val().isValid()

    cavity = realized.cavity_solid.val().BoundingBox()
    assert float(cavity.xlen) == pytest.approx(INTERNAL_WIDTH_X_MM, abs=2e-6)
    assert float(cavity.ylen) == pytest.approx(INTERNAL_HEIGHT_Y_MM, abs=2e-6)
    assert float(cavity.zlen) == pytest.approx(INTERNAL_DEPTH_Z_MM, abs=2e-6)

    outer = realized.outer_envelope_solid.val().BoundingBox()
    assert float(outer.xlen) == pytest.approx(OUTER_WIDTH_X_MM, abs=2e-6)
    assert float(outer.ylen) == pytest.approx(OUTER_HEIGHT_Y_MM, abs=2e-6)
    assert float(outer.zlen) == pytest.approx(OUTER_DEPTH_Z_MM, abs=2e-6)


def test_reservoir_datums_preserve_fresh_water_identity_and_unpowered_service_axis():
    realized = build_realized_water_reservoir(load_authority())

    assert tuple(datum.datum_id for datum in realized.datums) == DATUM_IDS
    by_id = {datum.datum_id: datum for datum in realized.datums}
    assert by_id[PORT_FILL].fluid_identity == FLUID_IDENTITY == "FRESH_WATER"
    assert by_id[PORT_VENT].fluid_identity == FLUID_IDENTITY
    assert by_id[PORT_PICKUP].fluid_identity == FLUID_IDENTITY
    assert by_id[DATUM_SERVICE_WITHDRAWAL].fluid_identity is None
    assert by_id[DATUM_SERVICE_WITHDRAWAL].axis.as_tuple() == (0.0, 0.0, -1.0)
    assert realized.service_withdrawal_travel_mm == SERVICE_WITHDRAWAL_TRAVEL_MM == 14.0
    assert realized.cavity_classification == "WET_REMOVABLE"


def test_realized_reservoir_is_bound_to_current_architecture_and_rejects_stale_digest():
    authority = load_authority()
    architecture = build_water_reservoir_architecture(authority)
    realized = build_realized_water_reservoir(authority)

    assert realized.source_architecture_sha256 == architecture.architecture_sha256
    realized.validate_current_sources(authority)

    stale = replace(realized, source_architecture_sha256="0" * 64)
    with pytest.raises(WaterReservoirError, match="stale for current water-reservoir architecture"):
        stale.validate_current_sources(authority)


def test_reservoir_evidence_firewall_and_manifest_are_deterministic():
    authority = load_authority()
    first = build_realized_water_reservoir(authority)
    second = build_realized_water_reservoir(authority)

    assert first.manifest() == second.manifest()
    assert first.manifest_sha256 == second.manifest_sha256
    assert len(first.manifest_sha256) == 64
    assert first.physical_validation_eligible is False
    assert first.evidence_status == PHYSICAL_EVIDENCE_STATUS
    assert first.manifest()["fluid_identity"] == "FRESH_WATER"
    assert first.manifest()["volume_evidence_kind"] == "DIGITAL_GEOMETRIC_VOLUME_ONLY"

    with pytest.raises(WaterReservoirError, match="cannot change FRESH_WATER"):
        replace(first, fluid_identity="CLEANSER")
    with pytest.raises(WaterReservoirError, match="cannot be physical validation evidence"):
        replace(first, physical_validation_eligible=True)
