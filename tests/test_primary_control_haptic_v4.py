from __future__ import annotations

import math

from masck_one import primary_control_haptic as v1
from masck_one.primary_control_haptic_v4 import (
    BUSHING_CAPTURE_GROOVE_OD_MM,
    BUSHING_FREE_FLANGE_OD_MM,
    BUSHING_FREE_ID_MM,
    BUSHING_FREE_JOURNAL_OD_MM,
    BUSHING_FREE_SPLIT_GAP_MM,
    BUSHING_INSTALLED_FLANGE_OD_MM,
    BUSHING_INSTALLED_ID_MM,
    BUSHING_INSTALLED_JOURNAL_OD_MM,
    BUSHING_INSTALLED_SPLIT_GAP_MM,
    SCHEMA,
    SOURCE_MAIN_SHA,
    build_primary_control_haptic_architecture_v4,
)


def test_v4_guide_sleeves_are_valid_shell_registered_and_axially_captured():
    architecture = build_primary_control_haptic_architecture_v4()
    material = dict(architecture.material_parts)
    refs = dict(architecture.reference_parts)

    assert architecture.source_main_sha == SOURCE_MAIN_SHA
    assert min(architecture.bushing_capture_removed_mm3.values()) > 0.0
    assert max(architecture.keepout_intersections_mm3.values(), default=0.0) == 0.0

    for name in ("upper_split_bushing_free", "lower_split_bushing_free"):
        shape = material[name]
        assert shape.isValid()
        assert len(shape.Solids()) == 1
        assert shape.Volume() > 0.0

    for name in (
        "upper_split_bushing_installed_reference",
        "lower_split_bushing_installed_reference",
    ):
        shape = refs[name]
        assert shape.isValid()
        assert len(shape.Solids()) == 1
        assert shape.Volume() > 0.0

    assert math.isclose(BUSHING_INSTALLED_JOURNAL_OD_MM, v1.BARREL_BORE_DIAMETER_MM)
    assert BUSHING_INSTALLED_FLANGE_OD_MM < BUSHING_CAPTURE_GROOVE_OD_MM


def test_v4_free_to_installed_split_sleeve_preserves_material_wall():
    free_journal_wall = (BUSHING_FREE_JOURNAL_OD_MM - BUSHING_FREE_ID_MM) / 2.0
    installed_journal_wall = (BUSHING_INSTALLED_JOURNAL_OD_MM - BUSHING_INSTALLED_ID_MM) / 2.0
    free_flange_wall = (BUSHING_FREE_FLANGE_OD_MM - BUSHING_FREE_ID_MM) / 2.0
    installed_flange_wall = (BUSHING_INSTALLED_FLANGE_OD_MM - BUSHING_INSTALLED_ID_MM) / 2.0

    assert math.isclose(free_journal_wall, installed_journal_wall, abs_tol=1e-12)
    assert math.isclose(free_flange_wall, installed_flange_wall, abs_tol=1e-12)
    assert BUSHING_INSTALLED_ID_MM > BUSHING_FREE_ID_MM
    assert BUSHING_INSTALLED_SPLIT_GAP_MM > BUSHING_FREE_SPLIT_GAP_MM


def test_v4_manifest_closes_floating_guide_failure_without_claiming_feel():
    architecture = build_primary_control_haptic_architecture_v4()
    manifest = architecture.manifest()

    assert manifest["schema"] == SCHEMA
    assert manifest["supersedes"].endswith("FLOATING_DIMENSIONALLY_INCONSISTENT_GUIDE_BUSHING_REFERENCES")
    guidance = manifest["guidance"]
    assert guidance["architecture"] == "TWO_SHELL_FIXED_SPLIT_LOW_FRICTION_FLANGED_SLEEVES"
    assert guidance["shell_fixed_axial_capture"] is True
    assert guidance["nominal_journal_wall_preserved"] is True
    assert guidance["nominal_flange_wall_preserved"] is True
    assert manifest["physical_validation_eligible"] is False
    assert "WOBBLE_FRICTION_STICTION_WEAR_CREEP_AND_CONTAMINATION_REQUIRE_BENCH_TEST" in manifest["tactile_quality_interpretation"]
