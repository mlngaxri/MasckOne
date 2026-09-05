from pathlib import Path

from masck_one.export import export_release
from masck_one.integrated_product import (
    MVP_EXTERIOR_STATUS,
    build_mvp_product_candidate,
    integrated_exterior_manifest,
)
from masck_one.model import build_model


def _component_signature(model):
    return tuple(component.name for component in model.components)


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
        assert candidate_component.solid.val().BoundingBox().xlen == baseline_component.solid.val().BoundingBox().xlen
        assert candidate_component.solid.val().BoundingBox().ylen == baseline_component.solid.val().BoundingBox().ylen
        assert candidate_component.solid.val().BoundingBox().zlen == baseline_component.solid.val().BoundingBox().zlen


def test_candidate_shell_materially_differs_from_released_ruled_shell():
    baseline = build_model().shell.solid.val()
    candidate = build_mvp_product_candidate().shell.solid.val()
    baseline_bb = baseline.BoundingBox()
    candidate_bb = candidate.BoundingBox()
    assert abs(candidate.Volume() - baseline.Volume()) > 1000.0
    assert candidate_bb.xlen < baseline_bb.xlen
    assert candidate_bb.ylen < baseline_bb.ylen
    assert candidate_bb.zlen <= baseline_bb.zlen + 1e-6


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
