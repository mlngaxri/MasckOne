from __future__ import annotations

from masck_one.structural_frame_actuator_reactions import REACTION_IDS
from masck_one.treatment_mounted_four_zone_v7 import (
    ROOT_PULL_OUT_PROBE_MM,
    SCHEMA_V7,
    TIP_PULL_OUT_PROBE_MM,
    build_mounted_four_zone_architecture_v7,
    manifest_v7,
)


def test_v7_builds_four_encapsulated_two_material_preload_mounts():
    architecture, datums = build_mounted_four_zone_architecture_v7()
    assert tuple(station.reaction_id for station in architecture.stations) == REACTION_IDS
    assert tuple(station.reaction_id for station in datums.stations) == REACTION_IDS
    for station in architecture.stations:
        material = dict(station.material_parts)
        assert "terminal_x_spring_insert" in material
        assert "terminal_z_spring_insert" in material
        assert "terminal_x_preload_shoe_polymer" in material
        assert "terminal_z_preload_shoe_polymer" in material
        assert material["fixed_backbone"].isValid()
        assert len(material["fixed_backbone"].Solids()) == 1

        screen = station.truss_screen["encapsulated_parallel_spring_v7"]
        assert screen["root_pullout_probe_mm"] == ROOT_PULL_OUT_PROBE_MM
        assert screen["tip_pullout_probe_mm"] == TIP_PULL_OUT_PROBE_MM
        assert min(screen["root_pullout_intersections_mm3"].values()) > 0.0
        assert min(screen["tip_pullout_intersections_mm3"].values()) > 0.0
        assert max(screen["material_overlap_mm3"].values()) == 0.0
        assert screen["X"]["robustness_corner_contact_margin_N"] > 0.03
        assert screen["Z"]["robustness_corner_contact_margin_N"] > 0.01
        assert screen["working_reaction_rule"].startswith("SPRING_ONLY_MAINTAINS_CONTACT")


def test_v7_preserves_nominal_operational_and_full_service_clearance():
    architecture, _datums = build_mounted_four_zone_architecture_v7()
    for station in architecture.stations:
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


def test_v7_manifest_removes_tiny_capture_fit_from_current_buttery_candidate():
    architecture, datums = build_mounted_four_zone_architecture_v7()
    manifest = manifest_v7(architecture, datums)
    assert manifest["schema"] == SCHEMA_V7
    assert "PHASED_X_THEN_Z_C2_TERMINAL_TAKEUP" in manifest["selected_buttery_candidate"]
    assert "ENCAPSULATED_AXIS_TUNED_PARALLEL_SPRING_INSERTS" in manifest["selected_buttery_candidate"]
    assert "NO_0P01MM_MOLDED_RUNNING_CLEARANCE_REQUIRED" in manifest["manufacturing_intent"]
    assert manifest["physical_validation_eligible"] is False
    assert manifest["physical_validation"].startswith("OPEN_")
    assert manifest["supersedes_as_current_v1_mount_candidate"].endswith("V6")
