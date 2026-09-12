from __future__ import annotations

import math

from masck_one.structural_frame_actuator_reactions import REACTION_IDS
from masck_one.treatment_terminal_datum_preload import (
    AXIS_PRELOAD_TARGET_N,
    CAM_TRANSITION_TRAVEL_MM,
    FULL_SEAT_LAND_MM,
    PROFILE_SAMPLES,
    SOURCE_CELL6_HEAD_SHA,
    build_terminal_datum_preload_architecture,
    spring_leaf_screen,
)


def test_four_deterministic_terminal_mounts_exist_and_release_along_service_axis():
    architecture = build_terminal_datum_preload_architecture()
    assert tuple(item.reaction_id for item in architecture.stations) == REACTION_IDS
    assert architecture.source_cell6_head_sha == SOURCE_CELL6_HEAD_SHA
    assert architecture.physical_validation_eligible is False
    for item in architecture.stations:
        assert item.nominal_source_intersection_mm3 == 0.0
        assert min(item.master_probe_intersections_mm3) > 0.0
        assert min(item.free_preload_intersections_mm3) > 0.0
        assert item.service_source_intersection_mm3 == 0.0
        assert item.service_sweep.isValid()
        assert tuple(name for name, _shape in item.master_parts) == (
            "rigid_master_x",
            "rigid_master_z",
        )
        assert tuple(name for name, _shape in item.preload_installed_parts) == (
            "preload_x_installed",
            "preload_z_installed",
        )


def test_terminal_profile_uses_smooth_cam_then_flat_land():
    architecture = build_terminal_datum_preload_architecture()
    assert CAM_TRANSITION_TRAVEL_MM == 0.65
    assert FULL_SEAT_LAND_MM == 0.16
    assert PROFILE_SAMPLES >= 7
    for item in architecture.manifest()["stations"]:
        profile = item["terminal_profile"]
        assert profile["entry_slope"] == 0.0
        assert profile["full_seat_slope"] == 0.0
        assert profile["flat_full_seat_land_mm"] > 0.0


def test_preload_seed_has_more_margin_than_original_024N_screen():
    spring = spring_leaf_screen()
    assert AXIS_PRELOAD_TARGET_N == 0.30
    assert math.isclose(spring["preload_target_N"], 0.30, abs_tol=1e-12)
    assert 0.14 < spring["preload_deflection_seed_mm"] < 0.18
    assert spring["preload_root_stress_proxy_MPa"] < 350.0


def test_manifest_rejects_four_rigid_faces_and_keeps_spring_root_open():
    manifest = build_terminal_datum_preload_architecture().manifest()
    assert manifest["selected_v1_direction"].startswith("RIGID_MASTER_X_Z_DATUMS")
    assert manifest["supersedes_as_production_baseline"] == "FULLY_RIGID_FOUR_FACE_MATCHED_TAPER_V3"
    assert manifest["physical_validation_eligible"] is False
    for item in manifest["stations"]:
        assert item["load_path"].startswith("NORMAL_40HZ_REACTION_TO_RIGID_X_Z_MASTER_DATUMS")
        assert item["spring_root_attachment_status"].startswith("OPEN_EXPLICIT_CAPTURE_REQUIRED")
        assert item["physical_validation"].startswith("OPEN_")
