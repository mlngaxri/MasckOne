from __future__ import annotations

import math

from masck_one.structural_frame_actuator_reactions import REACTION_IDS
from masck_one.treatment_mounted_four_zone import (
    OPERATIONAL_HALF_STROKE_MM,
    SERVICE_WITHDRAWAL_MM,
    SOURCE_CELL6_HEAD_SHA,
    SOURCE_MAIN_SHA,
    SOURCE_TREATMENT_HEAD_SHA,
    STATION_AXIS_DEG,
    STATION_CENTERS_MM,
    TRUSS_POLYMER_SCREEN_E_MPA,
    build_mounted_four_zone_architecture,
)


def test_four_mounted_station_candidates_close_current_digital_collision_gates():
    architecture = build_mounted_four_zone_architecture()
    assert tuple(station.reaction_id for station in architecture.stations) == REACTION_IDS
    assert architecture.physical_validation_eligible is False
    assert SERVICE_WITHDRAWAL_MM == 32.0
    assert OPERATIONAL_HALF_STROKE_MM == 0.26

    for station in architecture.stations:
        assert station.treatment_center_mm == STATION_CENTERS_MM[station.reaction_id]
        assert station.axis_angle_deg == STATION_AXIS_DEG[station.reaction_id]
        assert max(station.nominal_source_intersections_mm3.values()) == 0.0
        assert max(station.nominal_protected_intersections_mm3.values()) == 0.0
        assert station.nominal_shell_intersection_mm3 == 0.0
        assert station.operational_fixed_intersection_mm3 == 0.0
        assert station.operational_source_intersection_mm3 == 0.0
        assert station.operational_protected_intersection_mm3 == 0.0
        assert station.operational_shell_intersection_mm3 == 0.0
        assert station.service_source_intersection_mm3 == 0.0
        assert station.service_protected_intersection_mm3 == 0.0
        assert station.service_shell_intersection_mm3 == 0.0
        assert station.operational_sweep.isValid()
        assert station.service_sweep.isValid()
        assert station.truss_screen["rear_anchor_separation_mm"] > 4.0
        assert station.truss_screen["2p5GPa_screen"]["transient_buckling_ratio"] > 1.0


def test_station_layout_is_mirrored_and_tilts_outward():
    left_ids = [reaction_id for reaction_id in REACTION_IDS if "LEFT" in reaction_id]
    right_ids = [reaction_id for reaction_id in REACTION_IDS if "RIGHT" in reaction_id]
    assert all(STATION_AXIS_DEG[reaction_id] < 0.0 for reaction_id in left_ids)
    assert all(STATION_AXIS_DEG[reaction_id] > 0.0 for reaction_id in right_ids)

    assert STATION_CENTERS_MM["ACTUATOR_REACTION_SUPERIOR_LEFT"][0] == -STATION_CENTERS_MM["ACTUATOR_REACTION_SUPERIOR_RIGHT"][0]
    assert STATION_CENTERS_MM["ACTUATOR_REACTION_INFERIOR_LEFT"][0] == -STATION_CENTERS_MM["ACTUATOR_REACTION_INFERIOR_RIGHT"][0]
    assert STATION_CENTERS_MM["ACTUATOR_REACTION_SUPERIOR_LEFT"][1:] == STATION_CENTERS_MM["ACTUATOR_REACTION_SUPERIOR_RIGHT"][1:]
    assert STATION_CENTERS_MM["ACTUATOR_REACTION_INFERIOR_LEFT"][1:] == STATION_CENTERS_MM["ACTUATOR_REACTION_INFERIOR_RIGHT"][1:]


def test_manifest_preserves_source_binding_and_evidence_firewall():
    architecture = build_mounted_four_zone_architecture()
    manifest = architecture.manifest()
    assert manifest["source_main_sha"] == SOURCE_MAIN_SHA
    assert manifest["source_cell6_head_sha"] == SOURCE_CELL6_HEAD_SHA
    assert manifest["source_treatment_head_sha"] == SOURCE_TREATMENT_HEAD_SHA
    assert manifest["physical_validation_eligible"] is False
    assert "FOUR_MOUNTED_STATION_CANDIDATES" in manifest["mechanical_status"]

    for station in manifest["stations"]:
        assert station["reaction_architecture"].startswith("OPEN_SHOULDER_YOKE_PLUS_TWO_CHORD")
        assert station["physical_validation"].startswith("OPEN_")
        screen = station["truss_screen"]
        assert screen["2p5GPa_screen"]["transient_buckling_ratio"] > 1.0
        assert math.isclose(TRUSS_POLYMER_SCREEN_E_MPA, 2500.0, rel_tol=0.0, abs_tol=0.0)
