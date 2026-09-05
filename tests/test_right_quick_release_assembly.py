from __future__ import annotations

import json

import cadquery as cq

from masck_one.right_quick_release_assembly import (
    HOOK_DEFLECTION,
    SLIDER_START_Z,
    CLOSURE_START_Z,
    _upper,
    build_right_quick_release_assembly,
    export_right_quick_release_assembly,
)


def _intersection_mm3(first: cq.Workplane, second: cq.Workplane) -> float:
    return float(first.val().intersect(second.val()).Volume())


def _difference_mm3(first: cq.Workplane, second: cq.Workplane) -> float:
    return float(first.val().cut(second.val()).Volume())


def test_split_guide_has_nonteleporting_slider_insertion_and_positive_closure() -> None:
    assembly = build_right_quick_release_assembly()
    manifest = assembly.manifest()
    assert manifest["supersedes_source_guide_for_release_assembly"] is True
    assert [state["state_id"] for state in manifest["assembly_sequence"]] == [
        "GUIDE_OPEN_LOWER_HALF",
        "SLIDER_INSERTION",
        "UPPER_CLOSURE_DESCENT_HOOKS_DEFLECTED",
        "HOOK_RELAXATION_TO_POSITIVE_CAPTURE",
        "ASSEMBLED_OPERATIONAL",
    ]
    assert manifest["assembly_sequence"][1]["proof"] == "EXACT_RIGID_SLIDER_VERTICAL_SWEPT_SOLID"
    assert manifest["assembly_sequence"][-1]["no_factory_teleportation_required"] is True
    proof = manifest["continuous_assembly_proof"]
    assert proof["source_split_reconstruction_error_mm3"] == 0.0
    assert proof["exact_slider_insertion_sweep_vs_lower_mm3"] == 0.0
    assert proof["deflected_closure_vs_lower_mm3"] == 0.0
    assert proof["deflected_closure_vs_slider_mm3"] == 0.0
    for key in (
        "pin_bore_radial_clearance_mm",
        "spool_half_cavity_clearance_mm",
        "alignment_post_clearance_mm",
        "deflected_hook_side_clearance_mm",
        "nominal_beam_side_clearance_mm",
        "nominal_hook_vertical_gap_mm",
    ):
        assert proof[key] > 0.0
    retained = manifest["positive_closure_retention"]
    assert retained["friction_only"] is False
    assert retained["lift_probe_intersection_mm3"] > 0.0
    assert retained["down_probe_intersection_mm3"] > 0.0
    assert retained["x_shear_probe_intersection_mm3"] > 0.0
    assert retained["y_shear_probe_intersection_mm3"] > 0.0


def test_exact_slider_insertion_sweep_contains_complete_vertical_path() -> None:
    assembly = build_right_quick_release_assembly()
    slider = assembly.reset.latch.slider_and_grip.solid
    sweep = assembly.insertion_sweep.solid
    lower = assembly.lower.solid
    assert _intersection_mm3(sweep, lower) == 0.0
    for offset in (0.0, 0.37, 1.9, 4.2, 7.1, SLIDER_START_Z):
        state = slider.translate((0.0, 0.0, offset))
        assert _difference_mm3(state, sweep) <= 1e-7
        assert _intersection_mm3(state, lower) == 0.0


def test_closure_descent_and_hook_relaxation_regressions_remain_clear() -> None:
    assembly = build_right_quick_release_assembly()
    lower = assembly.lower.solid
    slider = assembly.reset.latch.slider_and_grip.solid
    for offset in (CLOSURE_START_Z, 4.0, 2.0, 1.0, 0.5, 0.1, 0.0):
        state = assembly.upper_deflected.solid.translate((0.0, 0.0, offset))
        assert _intersection_mm3(state, lower) == 0.0
        assert _intersection_mm3(state, slider) == 0.0
    source = assembly.reset.latch.guide_capsule.solid
    for deflection in (HOOK_DEFLECTION, 0.30, 0.20, 0.10, 0.0):
        state = _upper(source, deflection)
        assert _intersection_mm3(state, lower) == 0.0
        assert _intersection_mm3(state, slider) == 0.0


def test_split_guide_preserves_complete_operational_sweep_and_hard_stops() -> None:
    manifest = build_right_quick_release_assembly().manifest()
    operational = manifest["operational_preservation"]
    assert operational["exact_complete_withdrawal_sweep_vs_split_guide_mm3"] == 0.0
    assert operational["inboard_overtravel_probe_intersection_mm3"] > 0.0
    assert operational["outboard_overtravel_probe_intersection_mm3"] > 0.0
    assert operational["four_zone_actuation_preserved"] is True
    assert operational["full_head_removal_trajectory_included"] is False
    claims = manifest["manufacturing_claims"]
    assert claims["manufacturable_in_principle_digital_sequence"] is True
    assert claims["production_process_selected"] is False
    assert claims["hook_material_selected"] is False
    assert claims["hook_strain_or_fatigue_validated"] is False
    assert claims["assembly_force_validated"] is False
    assert manifest["physical_validation_eligible"] is False


def test_assembly_package_is_deterministic_and_step_roundtrips(tmp_path) -> None:
    first = build_right_quick_release_assembly()
    second = build_right_quick_release_assembly()
    assert first.package_sha256 == second.package_sha256
    assert first.manifest() == second.manifest()
    paths = export_right_quick_release_assembly(tmp_path, first)
    expected = {
        "right_latch_guide_lower_body.step",
        "right_latch_guide_upper_closure.step",
        "right_latch_guide_upper_closure_deflected.step",
        "right_latch_slider_factory_insertion_sweep.step",
        "right_latch_guide_assembled_reference.step",
        "right_quick_release_assembly_manifest.json",
    }
    assert {path.name for path in paths} == expected
    for path in paths:
        assert path.is_file() and path.stat().st_size > 0
        if path.suffix.lower() not in {".step", ".stp"}:
            continue
        shape = cq.importers.importStep(str(path)).val()
        assert shape.isValid()
        assert len(shape.Solids()) == 1
    payload = json.loads((tmp_path / "right_quick_release_assembly_manifest.json").read_text(encoding="utf-8"))
    assert payload["package_sha256"] == first.package_sha256
    assert payload["source_continuous_sweep_package_sha256"] == first.continuous.package_sha256
