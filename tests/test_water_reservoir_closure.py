from dataclasses import replace

import cadquery as cq
import pytest

from masck_one.authority import load_authority
from masck_one.realized_water_reservoir import build_realized_water_reservoir
from masck_one.water_reservoir import WaterReservoirError
from masck_one.water_reservoir_closure import (
    KEY_BORE_DIAMETER_MM,
    KEY_DETENT_DIAMETER_MM,
    KEY_HEAD_DIAMETER_MM,
    KEY_STEM_DIAMETER_MM,
    LID_LIFT_SERVICE_TRAVEL_MM,
    LID_SLIDE_RELEASE_TRAVEL_MM,
    PHYSICAL_EVIDENCE_STATUS,
    RAIL_RUNNING_CLEARANCE_Z_MM,
    SEAL_GROOVE_DEPTH_MM,
    SEAL_GROOVE_WIDTH_MM,
    SERVICE_SEQUENCE_IDS,
    build_water_reservoir_closure_geometry,
)
from masck_one.water_reservoir_interfaces import build_water_reservoir_interface_geometry


@pytest.fixture(scope="module")
def built():
    authority = load_authority()
    realized = build_realized_water_reservoir(authority)
    interfaces = build_water_reservoir_interface_geometry(authority, realized)
    closure = build_water_reservoir_closure_geometry(authority, realized, interfaces)
    return authority, realized, interfaces, closure


def _translated(shape: cq.Workplane, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> cq.Workplane:
    return cq.Workplane(obj=shape.val().moved(cq.Location(cq.Vector(x, y, z))))


def _intersection_volume(a: cq.Workplane, b: cq.Workplane) -> float:
    return float(a.val().intersect(b.val()).Volume())


def test_closure_binds_exact_interface_manifest_and_preserves_fresh_water(built):
    authority, _, interfaces, closure = built
    assert closure.source_interface_manifest_sha256 == interfaces.manifest_sha256
    assert closure.fluid_identity == "FRESH_WATER"
    closure.validate_current_sources(authority)


def test_body_lid_and_retention_key_are_valid_nonoverlapping_closed_state_solids(built):
    _, _, interfaces, closure = built
    assert closure.closure_body_solid.solids().size() == 1
    assert closure.closure_lid_solid.solids().size() == 1
    assert closure.retention_key_solid.solids().size() == 1
    assert closure.closure_body_solid.val().isValid()
    assert closure.closure_lid_solid.val().isValid()
    assert closure.retention_key_solid.val().isValid()

    assert closure.closure_body_solid.val().Volume() > interfaces.body_with_pickup_port_solid.val().Volume()
    assert closure.closure_lid_solid.val().Volume() < interfaces.lid_with_fill_vent_ports_solid.val().Volume()
    assert _intersection_volume(closure.closure_body_solid, closure.closure_lid_solid) == pytest.approx(0.0, abs=1e-8)
    assert _intersection_volume(closure.closure_body_solid, closure.retention_key_solid) == pytest.approx(0.0, abs=1e-8)
    assert _intersection_volume(closure.closure_lid_solid, closure.retention_key_solid) == pytest.approx(0.0, abs=1e-8)


def test_capture_rails_and_key_provide_positive_digital_motion_blocking(built):
    _, _, _, closure = built
    assert closure.bilateral_capture_rails_solid.solids().size() == 2
    assert RAIL_RUNNING_CLEARANCE_Z_MM > 0.0

    # With the key retained, a small inferior slide drives lid material into the key.
    shifted_inferior = _translated(closure.closure_lid_solid, y=-0.25)
    assert _intersection_volume(shifted_inferior, closure.retention_key_solid) > 0.0

    # With key ignored, the fixed overhanging rails block direct +Z lid lift.
    shifted_anterior = _translated(closure.closure_lid_solid, z=0.20)
    assert _intersection_volume(shifted_anterior, closure.closure_body_solid) > 0.0

    # The blind/front end of the guide relief also blocks insertion overtravel.
    shifted_superior = _translated(closure.closure_lid_solid, y=0.50)
    assert _intersection_volume(shifted_superior, closure.closure_body_solid) > 0.0


def test_retention_key_has_running_clearance_and_positive_anti_ejection_features(built):
    _, _, _, closure = built
    assert KEY_STEM_DIAMETER_MM < KEY_BORE_DIAMETER_MM
    assert KEY_DETENT_DIAMETER_MM > KEY_BORE_DIAMETER_MM
    assert KEY_HEAD_DIAMETER_MM > KEY_BORE_DIAMETER_MM
    manifest = closure.manifest()["retention_key"]
    assert manifest["status"].endswith("FORCE_AND_STRAIN_UNVALIDATED")


def test_continuous_seal_land_and_lid_groove_are_actual_geometry_without_seal_claim(built):
    _, _, interfaces, closure = built
    assert closure.seal_groove_reservation_solid.solids().size() == 1
    assert closure.seal_land_reference_solid.solids().size() == 1
    assert SEAL_GROOVE_WIDTH_MM == 0.5
    assert SEAL_GROOVE_DEPTH_MM == 0.2
    assert closure.seal_groove_reservation_solid.val().Volume() > 0.0
    assert closure.seal_land_reference_solid.val().Volume() > 0.0
    assert closure.closure_lid_solid.val().Volume() < interfaces.lid_with_fill_vent_ports_solid.val().Volume()
    assert "NO_SEAL_MATERIAL_OR_COMPRESSION_SELECTION" in closure.seal_status


def test_key_removed_lid_slide_then_lift_sequence_clears_fixed_body_geometry(built):
    _, _, _, closure = built
    assert tuple(step.step_id for step in closure.service_sequence) == SERVICE_SEQUENCE_IDS
    slid = _translated(closure.closure_lid_solid, y=-LID_SLIDE_RELEASE_TRAVEL_MM)
    assert _intersection_volume(slid, closure.closure_body_solid) == pytest.approx(0.0, abs=1e-8)
    lifted = _translated(slid, z=LID_LIFT_SERVICE_TRAVEL_MM)
    assert _intersection_volume(lifted, closure.closure_body_solid) == pytest.approx(0.0, abs=1e-8)
    assert closure.service_sequence[0].translation_world_mm.as_tuple() == (0.0, 0.0, -14.0)
    assert closure.service_sequence[2].translation_world_mm.as_tuple() == (0.0, -26.0, 0.0)
    assert closure.service_sequence[3].translation_world_mm.as_tuple() == (0.0, 0.0, 3.0)


def test_closure_manifest_is_deterministic_and_physical_evidence_promotion_fails_closed(built):
    authority, _, _, closure = built
    rebuilt = build_water_reservoir_closure_geometry(authority)
    assert closure.manifest() == rebuilt.manifest()
    assert closure.manifest_sha256 == rebuilt.manifest_sha256
    assert len(closure.manifest_sha256) == 64
    assert closure.physical_validation_eligible is False
    assert closure.evidence_status == PHYSICAL_EVIDENCE_STATUS

    stale = replace(closure, source_interface_manifest_sha256="0" * 64)
    with pytest.raises(WaterReservoirError, match="stale for current water-service interfaces"):
        stale.validate_current_sources(authority)
    with pytest.raises(WaterReservoirError, match="cannot change FRESH_WATER"):
        replace(closure, fluid_identity="CLEANSER")
    with pytest.raises(WaterReservoirError, match="cannot become physical validation evidence"):
        replace(closure, physical_validation_eligible=True)
