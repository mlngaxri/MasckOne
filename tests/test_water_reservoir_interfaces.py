from dataclasses import replace

import pytest

from masck_one.authority import load_authority
from masck_one.water_reservoir import ORIENTATION_CASE_IDS, WaterReservoirError
from masck_one.realized_water_reservoir import build_realized_water_reservoir
from masck_one.water_reservoir_interfaces import (
    FILL_BORE_DIAMETER_MM,
    FILL_CLOSURE_RESERVATION_DIAMETER_MM,
    FILL_CLOSURE_RESERVATION_HEIGHT_MM,
    PHYSICAL_EVIDENCE_STATUS,
    PICKUP_CONNECTOR_RESERVATION_DIAMETER_MM,
    PICKUP_CONNECTOR_RESERVATION_LENGTH_MM,
    PICKUP_PASSAGE_DIAMETER_MM,
    VENT_EXTERNAL_BARRIER_RESERVATION_DIAMETER_MM,
    VENT_EXTERNAL_BARRIER_RESERVATION_HEIGHT_MM,
    VENT_LUMEN_DIAMETER_MM,
    build_water_reservoir_interface_geometry,
)


@pytest.fixture(scope="module")
def built():
    authority = load_authority()
    realized = build_realized_water_reservoir(authority)
    interfaces = build_water_reservoir_interface_geometry(authority, realized)
    return authority, realized, interfaces


def test_interfaces_bind_exact_realized_reservoir_and_fresh_water_identity(built):
    authority, realized, interfaces = built
    assert interfaces.source_realized_reservoir_sha256 == realized.manifest_sha256
    assert interfaces.source_authority_revision == authority.get("project", "authority_revision")
    assert interfaces.fluid_identity == "FRESH_WATER"
    interfaces.validate_current_sources(authority)


def test_fill_and_vent_are_actual_lid_openings_with_explicit_closure_reservations(built):
    _, realized, interfaces = built
    assert interfaces.lid_with_fill_vent_ports_solid.solids().size() == 1
    assert interfaces.lid_with_fill_vent_ports_solid.val().isValid()
    assert interfaces.lid_with_fill_vent_ports_solid.val().Volume() < realized.lid_solid.val().Volume()
    assert interfaces.fill_bore_solid.val().intersect(realized.lid_solid.val()).Volume() > 0.0
    assert interfaces.vent_path_solid.val().intersect(realized.lid_solid.val()).Volume() > 0.0

    fill_bb = interfaces.fill_closure_reservation_solid.val().BoundingBox()
    assert float(fill_bb.xlen) == pytest.approx(FILL_CLOSURE_RESERVATION_DIAMETER_MM, abs=2e-6)
    assert float(fill_bb.ylen) == pytest.approx(FILL_CLOSURE_RESERVATION_DIAMETER_MM, abs=2e-6)
    assert float(fill_bb.zlen) == pytest.approx(FILL_CLOSURE_RESERVATION_HEIGHT_MM, abs=2e-6)
    assert FILL_BORE_DIAMETER_MM == 6.0

    vent_bb = interfaces.vent_external_barrier_reservation_solid.val().BoundingBox()
    assert float(vent_bb.xlen) == pytest.approx(VENT_EXTERNAL_BARRIER_RESERVATION_DIAMETER_MM, abs=2e-6)
    assert float(vent_bb.zlen) == pytest.approx(VENT_EXTERNAL_BARRIER_RESERVATION_HEIGHT_MM, abs=2e-6)
    assert VENT_LUMEN_DIAMETER_MM == 1.2


def test_vent_path_is_continuous_to_high_side_internal_terminus_without_performance_claim(built):
    _, _, interfaces = built
    assert interfaces.vent_path_solid.solids().size() == 1
    assert interfaces.vent_path_solid.val().isValid()
    assert len(interfaces.vent_centerline) == 3
    assert interfaces.vent_centerline_length_mm == pytest.approx(13.0, abs=1e-12)
    assert interfaces.vent_internal_area_mm2 == pytest.approx(1.1309733552923256, abs=1e-12)
    assert interfaces.vent_centerline_geometric_volume_mL == pytest.approx(
        interfaces.vent_centerline_length_mm * interfaces.vent_internal_area_mm2 / 1000.0,
        abs=1e-15,
    )
    assert "INGRESS_UNVALIDATED" in interfaces.manifest()["vent"]["status"]


def test_pickup_is_actual_low_side_wall_passage_with_connector_reservation(built):
    _, realized, interfaces = built
    assert interfaces.body_with_pickup_port_solid.solids().size() == 1
    assert interfaces.body_with_pickup_port_solid.val().isValid()
    assert interfaces.body_with_pickup_port_solid.val().Volume() < realized.body_solid.val().Volume()
    assert interfaces.pickup_passage_solid.val().intersect(realized.body_solid.val()).Volume() > 0.0
    assert interfaces.pickup_centerline_length_mm == pytest.approx(1.0, abs=1e-12)
    assert PICKUP_PASSAGE_DIAMETER_MM == 2.0

    pickup_bb = interfaces.pickup_connector_reservation_solid.val().BoundingBox()
    assert float(pickup_bb.xlen) == pytest.approx(PICKUP_CONNECTOR_RESERVATION_DIAMETER_MM, abs=2e-6)
    assert float(pickup_bb.zlen) == pytest.approx(PICKUP_CONNECTOR_RESERVATION_DIAMETER_MM, abs=2e-6)
    assert float(pickup_bb.ylen) == pytest.approx(PICKUP_CONNECTOR_RESERVATION_LENGTH_MM, abs=2e-6)


def test_orientation_reasoning_preserves_all_cases_and_fails_closed_where_angles_are_unknown(built):
    _, _, interfaces = built
    assert tuple(case.case_id for case in interfaces.orientation_cases) == ORIENTATION_CASE_IDS
    cases = {case.case_id: case for case in interfaces.orientation_cases}

    neutral = cases["ORIENTATION_NEUTRAL"]
    assert neutral.gravity_down_world.as_tuple() == (0.0, -1.0, 0.0)
    assert neutral.pickup_distance_to_gravity_low_boundary_mm == pytest.approx(0.0, abs=1e-12)
    assert neutral.vent_distance_to_gravity_high_boundary_mm == pytest.approx(1.0, abs=1e-12)

    face_up = cases["ORIENTATION_FACE_UP"]
    assert face_up.gravity_down_world.as_tuple() == (0.0, 0.0, -1.0)
    assert face_up.pickup_distance_to_gravity_low_boundary_mm == pytest.approx(1.0, abs=1e-12)
    assert face_up.vent_distance_to_gravity_high_boundary_mm == pytest.approx(0.5, abs=1e-12)

    face_down = cases["ORIENTATION_FACE_DOWN"]
    assert face_down.gravity_down_world.as_tuple() == (0.0, 0.0, 1.0)
    assert face_down.pickup_distance_to_gravity_low_boundary_mm == pytest.approx(9.0, abs=1e-12)
    assert face_down.vent_distance_to_gravity_high_boundary_mm == pytest.approx(9.5, abs=1e-12)

    for case_id in (
        "ORIENTATION_PITCH_FORWARD",
        "ORIENTATION_PITCH_BACK",
        "ORIENTATION_ROLL_LEFT",
        "ORIENTATION_ROLL_RIGHT",
    ):
        case = cases[case_id]
        assert case.gravity_down_world is None
        assert case.pickup_distance_to_gravity_low_boundary_mm is None
        assert case.vent_distance_to_gravity_high_boundary_mm is None
        assert case.numeric_screen_status == "ANGLE_UNRESOLVED_NO_NUMERIC_AXIS_SCREEN"

    assert all(case.physical_validation_eligible is False for case in interfaces.orientation_cases)


def test_manifest_is_deterministic_and_evidence_firewall_rejects_promotion(built):
    authority, _, interfaces = built
    rebuilt = build_water_reservoir_interface_geometry(authority)
    assert interfaces.manifest() == rebuilt.manifest()
    assert interfaces.manifest_sha256 == rebuilt.manifest_sha256
    assert len(interfaces.manifest_sha256) == 64
    assert interfaces.physical_validation_eligible is False
    assert interfaces.evidence_status == PHYSICAL_EVIDENCE_STATUS

    with pytest.raises(WaterReservoirError, match="cannot change FRESH_WATER"):
        replace(interfaces, fluid_identity="CLEANSER")
    with pytest.raises(WaterReservoirError, match="cannot become physical validation evidence"):
        replace(interfaces, physical_validation_eligible=True)
    stale = replace(interfaces, source_realized_reservoir_sha256="0" * 64)
    with pytest.raises(WaterReservoirError, match="stale for current realized reservoir"):
        stale.validate_current_sources(authority)
