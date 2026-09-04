from masck_one.integrated_product import (
    MVP_EXTERIOR_STATUS,
    build_mvp_product_candidate,
    integrated_exterior_manifest,
)
from masck_one.model import build_model


def test_mvp_candidate_replaces_only_rigid_shell_component():
    baseline = build_model()
    candidate = build_mvp_product_candidate(baseline.authority)

    assert candidate.shell.status == MVP_EXTERIOR_STATUS
    assert candidate.shell.solid.val().isValid()
    assert candidate.shell.solid.val().Volume() > 0.0

    baseline_components = {component.name: component for component in baseline.components}
    candidate_components = {component.name: component for component in candidate.components}
    assert baseline_components.keys() == candidate_components.keys()
    assert set(candidate_components) - {"rigid_shell"} == set(baseline_components) - {"rigid_shell"}

    for name in set(candidate_components) - {"rigid_shell"}:
        before = baseline_components[name].solid.val().BoundingBox()
        after = candidate_components[name].solid.val().BoundingBox()
        assert (before.xmin, before.xmax, before.ymin, before.ymax, before.zmin, before.zmax) == (
            after.xmin,
            after.xmax,
            after.ymin,
            after.ymax,
            after.zmin,
            after.zmax,
        )


def test_mvp_candidate_shell_remains_inside_authority_xy_envelope():
    candidate = build_mvp_product_candidate()
    bb = candidate.shell.solid.val().BoundingBox()
    outer_w, outer_h = candidate.authority.pair("geometry", "outer_xy_envelope_mm")
    assert bb.xlen <= outer_w + 1e-6
    assert bb.ylen <= outer_h + 1e-6


def test_integration_manifest_explicitly_excludes_manual_a_edits():
    manifest = integrated_exterior_manifest()
    assert manifest["integration_status"] == MVP_EXTERIOR_STATUS
    assert manifest["integration_policy"] == "CURRENT_MAIN_COMPONENT_SET_PRESERVED_EXCEPT_RIGID_SHELL"
    assert manifest["manual_a_geometry_modified"] is False
