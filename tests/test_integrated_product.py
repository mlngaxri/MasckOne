from pathlib import Path
import math

from masck_one.exterior_surface import (
    ANTERIOR_CROWN_RELIEF_MAX_MM,
    ANTERIOR_CROWN_RELIEF_MIN_MM,
    EXTERIOR_Z_STATIONS_MM,
)
from masck_one.export import export_release
from masck_one.integrated_product import (
    MVP_EXTERIOR_STATUS,
    build_mvp_product_candidate,
    integrated_exterior_manifest,
)
from masck_one.model import build_model


GEOMETRY_COMPARE_TOLERANCE_MM = 1e-9
COLLISION_VOLUME_TOLERANCE_MM3 = 1e-6


def _component_signature(model):
    return tuple(component.name for component in model.components)


def _intersection_volume_mm3(a, b) -> float:
    intersection = a.intersect(b)
    return float(intersection.Volume()) if not intersection.isNull() else 0.0


def test_candidate_preserves_current_component_set_and_replaces_only_shell_status():
    baseline = build_model()
    candidate = build_mvp_product_candidate()
    assert _component_signature(candidate) == _component_signature(baseline)
    assert baseline.shell.status != MVP_EXTERIOR_STATUS
    assert candidate.shell.status == MVP_EXTERIOR_STATUS
    assert candidate.shell.name == baseline.shell.name == "rigid_shell"

    for candidate_component, baseline_component in zip(candidate.components[1:], baseline.components[1:]):
        assert candidate_component.name == baseline_component.name
        assert candidate_component.status == baseline_component.status
        candidate_bb = candidate_component.solid.val().BoundingBox()
        baseline_bb = baseline_component.solid.val().BoundingBox()
        assert math.isclose(candidate_bb.xlen, baseline_bb.xlen, abs_tol=GEOMETRY_COMPARE_TOLERANCE_MM)
        assert math.isclose(candidate_bb.ylen, baseline_bb.ylen, abs_tol=GEOMETRY_COMPARE_TOLERANCE_MM)
        assert math.isclose(candidate_bb.zlen, baseline_bb.zlen, abs_tol=GEOMETRY_COMPARE_TOLERANCE_MM)


def test_candidate_shell_materially_differs_from_released_ruled_shell():
    baseline = build_model().shell.solid.val()
    candidate = build_mvp_product_candidate().shell.solid.val()
    baseline_bb = baseline.BoundingBox()
    candidate_bb = candidate.BoundingBox()
    visible_relief = candidate_bb.zmax - EXTERIOR_Z_STATIONS_MM[-1]
    assert abs(candidate.Volume() - baseline.Volume()) > 1000.0
    assert candidate_bb.xlen < baseline_bb.xlen
    assert candidate_bb.ylen < baseline_bb.ylen
    assert candidate_bb.zlen > baseline_bb.zlen
    assert ANTERIOR_CROWN_RELIEF_MIN_MM <= visible_relief <= ANTERIOR_CROWN_RELIEF_MAX_MM


def test_candidate_does_not_introduce_new_shell_intersection_with_released_components():
    baseline = build_model()
    candidate = build_mvp_product_candidate()
    baseline_shell = baseline.shell.solid.val()
    candidate_shell = candidate.shell.solid.val()

    for baseline_component, candidate_component in zip(baseline.components[1:], candidate.components[1:]):
        if baseline_component.status == "REFERENCE_ONLY":
            continue
        baseline_collision = _intersection_volume_mm3(baseline_shell, baseline_component.solid.val())
        candidate_collision = _intersection_volume_mm3(candidate_shell, candidate_component.solid.val())
        assert candidate_collision <= baseline_collision + COLLISION_VOLUME_TOLERANCE_MM3, (
            f"Cell 2 shell introduces additional intersection with {candidate_component.name}: "
            f"baseline={baseline_collision:.9f} mm3 candidate={candidate_collision:.9f} mm3"
        )


def test_integration_manifest_is_fail_closed_on_claim_scope():
    manifest = integrated_exterior_manifest()
    assert manifest["integration_status"] == MVP_EXTERIOR_STATUS
    assert manifest["integration_policy"] == "CURRENT_MAIN_COMPONENT_SET_PRESERVED_EXCEPT_RIGID_SHELL"
    assert manifest["foreign_lane_geometry_modified"] is False
    assert "PHYSICAL" in manifest["evidence_status"]


def test_candidate_runs_release_export_smoke(tmp_path: Path):
    candidate = build_mvp_product_candidate()
    report = export_release(tmp_path, model=candidate)
    assert report["result"] == "PASS"
    assert (tmp_path / "rigid_shell.step").exists()
    assert (tmp_path / "masck_one_development_assembly.step").exists()
    assert (tmp_path / "build_report.json").exists()
