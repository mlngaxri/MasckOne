from __future__ import annotations

from masck_one.structural_frame_actuator_reactions import REACTION_IDS
from masck_one.treatment_terminal_datum_preload_v2 import (
    CAM_TRAVEL_MM,
    FULL_SEAT_LAND_MM,
    PROFILE_SAMPLES,
    SCHEMA,
    SOURCE_CELL6_HEAD_SHA,
    X_CAM_PHASE_LEAD_MM,
    build_terminal_datum_preload_v2_architecture,
)


def test_v2_builds_all_four_phased_C2_terminal_datums_without_source_collision():
    architecture = build_terminal_datum_preload_v2_architecture()
    assert tuple(station.reaction_id for station in architecture.stations) == REACTION_IDS
    for station in architecture.stations:
        assert station.nominal_source_intersection_mm3 == 0.0
        assert min(station.master_probe_intersections_mm3) > 0.0
        assert station.service_source_intersection_mm3 == 0.0
        assert len(station.master_parts) == 2
        assert len(station.preload_outer_parts) == 2
        assert len(station.rigid_backup_parts) == 2


def test_v2_manifest_records_longer_phased_quintic_terminal_profile():
    architecture = build_terminal_datum_preload_v2_architecture()
    manifest = architecture.manifest()
    assert manifest["schema"] == SCHEMA
    assert manifest["source_cell6_head_sha"] == SOURCE_CELL6_HEAD_SHA
    assert manifest["physical_validation_eligible"] is False
    for station in manifest["stations"]:
        profile = station["terminal_profile"]
        assert profile["profile"] == "QUINTIC_C2_SMOOTHERSTEP_SPLINE_FIT"
        assert profile["cam_travel_mm"] == CAM_TRAVEL_MM == 0.95
        assert profile["X_phase_lead_mm"] == X_CAM_PHASE_LEAD_MM == 0.16
        assert profile["Z_phase_lead_mm"] == 0.0
        assert profile["flat_full_seat_land_mm"] == FULL_SEAT_LAND_MM
        assert profile["profile_samples"] == PROFILE_SAMPLES
        assert profile["entry_slope_intent"] == 0.0
        assert profile["entry_curvature_intent"] == 0.0
        assert profile["full_seat_slope_intent"] == 0.0
        assert profile["full_seat_curvature_intent"] == 0.0
        assert station["physical_validation"].startswith("OPEN_")


def test_v2_keeps_lossy_backup_reference_separate_from_rigid_overload_material():
    architecture = build_terminal_datum_preload_v2_architecture()
    for station in architecture.stations:
        assert {name for name, _shape in station.lossy_backup_references} == {
            "x_lossy_backup_reference_v2",
            "z_lossy_backup_reference_v2",
        }
        assert {name for name, _shape in station.rigid_backup_parts} == {
            "x_rigid_backup_stop_v2",
            "z_rigid_backup_stop_v2",
        }
