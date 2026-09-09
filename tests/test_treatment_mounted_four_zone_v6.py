from __future__ import annotations

from masck_one.structural_frame_actuator_reactions import REACTION_IDS
from masck_one.treatment_mounted_four_zone_v6 import (
    ROOT_PULL_OUT_PROBE_MM,
    SCHEMA_V6,
    build_mounted_four_zone_architecture_v6,
    manifest_v6,
)


def test_v6_realizes_two_captured_parallel_preload_cassettes_per_station():
    architecture, datums = build_mounted_four_zone_architecture_v6()
    assert tuple(station.reaction_id for station in architecture.stations) == REACTION_IDS
    for station in architecture.stations:
        material = dict(station.material_parts)
        reference = dict(station.reference_parts)
        assert "terminal_x_parallel_preload_cassette" in material
        assert "terminal_z_parallel_preload_cassette" in material
        assert "terminal_x_parallel_preload_free_reference" in reference
        assert "terminal_z_parallel_preload_free_reference" in reference
        assert material["fixed_backbone"].isValid()
        assert len(material["fixed_backbone"].Solids()) == 1

        capture = station.truss_screen["parallel_preload_cassette"]
        assert capture["root_pullout_probe_mm"] == ROOT_PULL_OUT_PROBE_MM
        assert capture["root_pullout_intersections_mm3"]["X"] > 0.0
        assert capture["root_pullout_intersections_mm3"]["Z"] > 0.0
        assert capture["X"]["entry_force_N"] < 0.015
        assert capture["Z"]["entry_force_N"] < 0.015
        assert capture["X"]["continuous_contact_margin_N"] > 0.09
        assert capture["Z"]["continuous_contact_margin_N"] > 0.09
        assert capture["physical_validation"].startswith("OPEN_")


def test_v6_preserves_nominal_operational_and_service_clearance_gates():
    architecture, _datums = build_mounted_four_zone_architecture_v6()
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


def test_v6_manifest_keeps_rigid_datums_as_working_path_and_physical_feel_open():
    architecture, datums = build_mounted_four_zone_architecture_v6()
    manifest = manifest_v6(architecture, datums)
    assert manifest["schema"] == SCHEMA_V6
    assert manifest["physical_validation_eligible"] is False
    assert "AXIS_TUNED_PARALLEL_PRELOAD_CASSETTES" in manifest["selected_buttery_candidate"]
    assert "LIMIT_PRELOAD_SHOE_PITCH" in manifest["why_parallel_leaves"]
    assert "PRELOAD_RELAXATION_RISK" in manifest["why_captured_spring_candidate"]
    assert manifest["physical_validation"].startswith("OPEN_")
