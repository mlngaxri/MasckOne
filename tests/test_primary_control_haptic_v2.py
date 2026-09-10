from __future__ import annotations

import math

from masck_one.primary_control_haptic import (
    CAP_THICKNESS_MM,
    HARD_STOP_MM,
    STEM_LENGTH_MM,
)
from masck_one.primary_control_haptic_v2 import (
    SCHEMA_V2,
    build_primary_control_haptic_architecture_v2,
    manifest_v2,
)


def test_primary_control_v2_builds_valid_material_and_continuous_reference():
    architecture = build_primary_control_haptic_architecture_v2()
    assert architecture.physical_validation_eligible is False
    assert max(architecture.keepout_intersections_mm3.values(), default=0.0) == 0.0
    assert all(shape.isValid() and shape.Solids() for _name, shape in architecture.material_parts)
    assert architecture.motion_sweep.isValid()
    assert len(architecture.motion_sweep.Solids()) >= 5

    bb = architecture.motion_sweep.BoundingBox()
    rest = architecture.rest_cap_underside_z_mm
    assert bb.zmax >= rest + CAP_THICKNESS_MM - 1e-9
    assert bb.zmin <= rest - STEM_LENGTH_MM - HARD_STOP_MM + 1e-9


def test_primary_control_v2_preserves_single_break_then_progressive_landing():
    architecture = build_primary_control_haptic_architecture_v2()
    manifest = manifest_v2(architecture)
    assert manifest["schema"] == SCHEMA_V2
    assert manifest["supersedes"].endswith("SAMPLED_MOTION_REFERENCE")
    assert manifest["motion_reference"].startswith("CONTINUOUS_CONSERVATIVE_ANALYTIC")
    assert "SINGLE_DECISIVE_FORCE_BREAK" in manifest["satisfying_interaction_intent"]

    screen = manifest["haptic_profile_screen"]
    checks = screen["digital_checks"]
    assert all(checks.values())
    derived = screen["derived"]
    assert derived["force_break_drop_N"] > 0.30
    assert 0.25 < derived["force_break_fraction_of_peak"] < 0.40
    assert derived["normal_bottom_to_hard_stop_reserve_mm"] >= 0.10


def test_primary_control_v2_keeps_evidence_firewall_and_fusion_handoff():
    architecture = build_primary_control_haptic_architecture_v2()
    manifest = manifest_v2(architecture)
    assert manifest["physical_validation_eligible"] is False
    assert manifest["physical_validation"].startswith("OPEN_")
    handoff = manifest["fusion_handoff"]
    assert handoff["cad_platform"] == "AUTODESK_FUSION_360"
    assert handoff["button_slider_dof"].startswith("TRANSLATION_-Z")
    assert handoff["grounded_component"] == "shell_with_primary_control_interface"
    assert math.isclose(manifest["travel_events_mm"]["hard_stop"], HARD_STOP_MM)
