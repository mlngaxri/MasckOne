from __future__ import annotations

from masck_one.structural_frame_actuator_reactions import REACTION_IDS
from masck_one.treatment_mounted_four_zone_v3 import (
    SCHEMA_V3,
    SOURCE_MAIN_SHA,
    SOURCE_TREATMENT_HEAD_SHA,
    build_mounted_four_zone_architecture_v3,
    manifest_v3,
)
from masck_one.treatment_terminal_kinematic_seat import SOURCE_CELL6_HEAD_SHA


def test_v3_fuses_terminal_seat_into_each_fixed_backbone_without_regressing_sweeps():
    architecture, seats = build_mounted_four_zone_architecture_v3()
    assert tuple(station.reaction_id for station in architecture.stations) == REACTION_IDS
    assert tuple(seat.reaction_id for seat in seats.seats) == REACTION_IDS

    for station in architecture.stations:
        material = dict(station.material_parts)
        assert material["fixed_backbone"].isValid()
        assert len(material["fixed_backbone"].Solids()) == 1
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
        seat_manifest = station.truss_screen["terminal_kinematic_seat"]
        assert seat_manifest["nominal_seated_geometric_dead_zone"].startswith(
            "ZERO_IN_IDEAL_RIGID_DATUM_MODEL"
        )
        assert seat_manifest["working_reaction_path"].startswith("RIGID_TAPER_FACES_TO_CELL6")


def test_v3_manifest_binds_current_cell6_and_keeps_physical_closure_open():
    architecture, seats = build_mounted_four_zone_architecture_v3()
    manifest = manifest_v3(architecture, seats)
    assert manifest["schema"] == SCHEMA_V3
    assert manifest["source_main_sha"] == SOURCE_MAIN_SHA
    assert manifest["source_cell6_head_sha"] == SOURCE_CELL6_HEAD_SHA
    assert manifest["source_treatment_head_sha"] == SOURCE_TREATMENT_HEAD_SHA
    assert manifest["terminal_kinematic_seat_architecture_sha256"] == seats.architecture_sha256
    assert manifest["physical_validation_eligible"] is False
    assert "TERMINAL_RIGID_XZ_KINEMATIC_TAPER_SEATING" in manifest["mechanical_status"]
    assert "PHYSICAL_OPEN" in manifest["seated_play_status"]
    assert manifest["supersedes"].endswith("V2_PARALLEL_CLEARANCE_YOKE")
