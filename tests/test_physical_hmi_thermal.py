from dataclasses import replace
import json
import math

import cadquery as cq
import pytest

from masck_one.model import build_model
from masck_one.physical_hmi_thermal import (
    AUTHORITY_BLOB_SHA,
    COOL_ID,
    COOL_STATUS,
    EVIDENCE_STATUS,
    HMI_MAPPING_STATUS,
    LEGACY_MANUAL_B_ELECTRONICS_BLOB_SHA,
    LEGACY_MANUAL_B_HEAD_SHA,
    OBSERVED_CELL2_GEOMETRY_CONSUMED,
    PRIMARY_ID,
    SCHEMA,
    SECONDARY_BAND_ID,
    SOURCE_MAIN_SHA,
    STATUS_WINDOW_ID,
    WARM_LEFT_ID,
    WARM_RIGHT_ID,
    WET_FINGER_ID,
    WORLD_FRAME_ID,
    PhysicalHmiThermalError,
    build_physical_hmi_thermal_decision_state,
    export_physical_hmi_thermal_review_artifacts,
)


@pytest.fixture(scope="module")
def state():
    return build_physical_hmi_thermal_decision_state()


def test_live_decision_state_separates_frozen_reserved_optional_and_blocked(state):
    assert state.schema == SCHEMA
    assert state.source_main_sha == SOURCE_MAIN_SHA
    assert state.authority_blob_sha == AUTHORITY_BLOB_SHA
    assert state.coordinate_frame_id == WORLD_FRAME_ID
    assert state.legacy_donor_head_sha == LEGACY_MANUAL_B_HEAD_SHA
    assert state.legacy_donor_blob_sha == LEGACY_MANUAL_B_ELECTRONICS_BLOB_SHA
    assert state.observed_cell2_geometry_consumed is OBSERVED_CELL2_GEOMETRY_CONSUMED is False
    assert state.reserved_ids == (
        PRIMARY_ID,
        SECONDARY_BAND_ID,
        STATUS_WINDOW_ID,
        WET_FINGER_ID,
        WARM_LEFT_ID,
        WARM_RIGHT_ID,
    )
    assert state.optional_ids == (COOL_ID,)
    assert len(state.decision_blocked_ids) == 9
    assert state.digital_mvp_hmi_thermal_ready is False
    assert state.physical_validation_eligible is False
    assert state.evidence_status == EVIDENCE_STATUS


def test_hmi_capacity_is_clean_first_but_does_not_freeze_control_count_or_mapping(state):
    hmi = state.hmi
    assert hmi.primary.reservation_id == PRIMARY_ID
    assert hmi.secondary_option_band.reservation_id == SECONDARY_BAND_ID
    assert hmi.final_control_count is None
    assert hmi.function_mapping is None
    assert hmi.donor_capacity_ceiling == 4
    assert hmi.clean_first_product_intent is True
    assert hmi.mapping_status == HMI_MAPPING_STATUS
    assert "GEOMETRIC_CAPACITY_ONLY" in hmi.manifest()["donor_capacity_semantics"]

    with pytest.raises(PhysicalHmiThermalError, match="control count or mapping"):
        replace(hmi, final_control_count=4)
    with pytest.raises(PhysicalHmiThermalError, match="control count or mapping"):
        replace(hmi, function_mapping=("CLEAN", "POWER", "WARM", "COOL"))


def test_hmi_and_warm_geometry_are_reference_only_and_valid(state):
    ids = tuple(item.reservation_id for item in state.world_review_reservations)
    assert ids == (
        PRIMARY_ID,
        SECONDARY_BAND_ID,
        STATUS_WINDOW_ID,
        WET_FINGER_ID,
        WARM_LEFT_ID,
        WARM_RIGHT_ID,
    )
    for item in state.world_review_reservations:
        assert item.development_assembly_material_eligible is False
        shape = item.solid.val()
        assert shape.isValid()
        assert len(shape.Solids()) == 1
        assert float(shape.Volume()) > 0.0
        with pytest.raises(PhysicalHmiThermalError, match="cannot silently become physical material"):
            replace(item, development_assembly_material_eligible=True)


def _protected_zone_conservative_aabb(zone):
    semi_x = zone.envelope_width_mm / 2.0
    semi_y = zone.envelope_height_mm / 2.0
    angle = math.radians(zone.angle_deg)
    half_x = math.sqrt((semi_x * math.cos(angle)) ** 2 + (semi_y * math.sin(angle)) ** 2)
    half_y = math.sqrt((semi_x * math.sin(angle)) ** 2 + (semi_y * math.cos(angle)) ** 2)
    return (
        zone.center.x - half_x,
        zone.center.x + half_x,
        zone.center.y - half_y,
        zone.center.y + half_y,
    )


def test_world_reservations_clear_all_released_protected_xy_envelopes(state):
    model = build_model()
    minimum_conservative_margin_mm = math.inf
    for reservation in state.world_review_reservations:
        bb = reservation.solid.val().BoundingBox()
        for protected in model.protected_volumes.all:
            xmin, xmax, ymin, ymax = _protected_zone_conservative_aabb(protected.zone)
            x_separation = max(xmin - float(bb.xmax), float(bb.xmin) - xmax)
            y_separation = max(ymin - float(bb.ymax), float(bb.ymin) - ymax)
            conservative_margin = max(x_separation, y_separation)
            assert conservative_margin > 0.0, (
                f"{reservation.reservation_id} intersects conservative XY AABB for "
                f"{protected.zone.zone_id}"
            )
            minimum_conservative_margin_mm = min(minimum_conservative_margin_mm, conservative_margin)
    assert math.isfinite(minimum_conservative_margin_mm)
    assert minimum_conservative_margin_mm > 0.0


def test_warm_package_preserves_unknown_hardware_and_physical_gates(state):
    assert tuple(item.package.reservation_id for item in state.warm) == (WARM_LEFT_ID, WARM_RIGHT_ID)
    for warm in state.warm:
        assert warm.selected_hardware is None
        assert warm.temperature_limit_C is None
        assert warm.nominal_power_W is None
        assert warm.thermal_performance_validated is False
        assert warm.physical_skin_safety_validated is False
        with pytest.raises(PhysicalHmiThermalError, match="cannot invent WARM"):
            replace(warm, nominal_power_W=2.0)
        with pytest.raises(PhysicalHmiThermalError, match="validated thermal performance"):
            replace(warm, thermal_performance_validated=True)


def test_cool_is_bounded_optional_and_not_exported_without_world_transform(state):
    cool = state.cool
    assert cool.reservation_id == COOL_ID
    assert cool.local_envelope_mm == (24.0, 12.0, 4.0)
    assert cool.world_center_xyz_mm is None
    assert cool.world_transform is None
    assert cool.optional is True
    assert cool.mvp_blocking is False
    assert cool.status == COOL_STATUS
    assert cool.manifest()["exportable_world_brep"] is False
    with pytest.raises(PhysicalHmiThermalError, match="world placement"):
        replace(cool, world_center_xyz_mm=(0.0, 31.0, -38.0))
    with pytest.raises(PhysicalHmiThermalError, match="may not block"):
        replace(cool, mvp_blocking=True)


def test_hostile_source_frame_evidence_and_bool_mutations_fail_closed(state):
    with pytest.raises(PhysicalHmiThermalError, match="stale for released main"):
        replace(state, source_main_sha="0" * 40)
    with pytest.raises(PhysicalHmiThermalError, match="world frame changed"):
        replace(state, coordinate_frame_id="MASCK_ONE_GLOBAL")
    with pytest.raises(PhysicalHmiThermalError, match="cannot become release authority"):
        replace(state, legacy_donor_status="AUTHORITY")
    with pytest.raises(PhysicalHmiThermalError, match="exact bool"):
        replace(state, physical_validation_eligible=0)
    with pytest.raises(PhysicalHmiThermalError, match="evidence boundary changed"):
        replace(state, evidence_status="PHYSICAL_VALIDATION")


def test_manifest_is_deterministic_and_nonfinite_geometry_fails_closed(state):
    second = build_physical_hmi_thermal_decision_state()
    assert second.manifest() == state.manifest()
    assert second.manifest_sha256 == state.manifest_sha256
    assert len(state.manifest_sha256) == 64
    for value in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(PhysicalHmiThermalError):
            replace(state.hmi.primary, center_xyz_mm=(value, 25.0, 9.0))


def test_review_artifacts_export_and_step_roundtrip(tmp_path, state):
    filenames = export_physical_hmi_thermal_review_artifacts(tmp_path, state)
    assert filenames == (
        "hmi_primary_control_capacity_reference.step",
        "hmi_secondary_option_band_reference.step",
        "hmi_status_window_capacity_reference.step",
        "hmi_wet_finger_access_clearance_reference.step",
        "warm_left_package_reservation_reference.step",
        "warm_right_package_reservation_reference.step",
        "physical_hmi_thermal_decision_state.json",
    )
    for filename in filenames[:-1]:
        imported = cq.importers.importStep(str(tmp_path / filename))
        assert imported.val().isValid()
        assert len(imported.val().Solids()) == 1
        assert float(imported.val().Volume()) > 0.0
    payload = json.loads((tmp_path / filenames[-1]).read_text(encoding="utf-8"))
    assert payload["manifest_sha256"] == state.manifest_sha256
    assert payload["cool"]["exportable_world_brep"] is False
