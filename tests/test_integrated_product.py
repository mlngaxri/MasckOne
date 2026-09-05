import pytest

from masck_one.anatomy import build_facial_reference
from masck_one.authority import load_authority
from masck_one.exterior_eye_roll import build_eye_rolled_exterior_shell
from masck_one.integrated_product import (
    MVP_EXTERIOR_STATUS,
    build_integrated_product_candidate,
    integrated_exterior_manifest,
)
from masck_one.model import build_model
from masck_one.spatial import CanonicalDatums


VOLUME_TOLERANCE_MM3 = 1e-5
BOUND_TOLERANCE_MM = 1e-5


def _candidate_context():
    model = build_model()
    candidate = build_integrated_product_candidate(model)
    return model, candidate


def test_integrated_candidate_replaces_only_rigid_shell_material():
    model, candidate = _candidate_context()
    baseline = {component.name: component for component in model.components}
    current = {component.name: component for component in candidate.components}

    assert tuple(current) == tuple(baseline)
    assert candidate.rigid_shell.name == "rigid_shell"
    assert candidate.rigid_shell.status == "ENGINEERING_BASELINE"
    assert candidate.rigid_shell.kind == "physical"
    assert candidate.rigid_shell.solid.val().isValid()
    assert candidate.rigid_shell.solid.solids().size() == 1

    for name, original in baseline.items():
        if name == "rigid_shell":
            continue
        replacement = current[name]
        assert replacement is original
        assert replacement.solid is original.solid
        assert replacement.status == original.status
        assert replacement.kind == original.kind


def test_integrated_candidate_uses_exact_current_cell2_shell():
    model, candidate = _candidate_context()
    authority = load_authority()
    datums = CanonicalDatums.from_authority(authority)
    facial_reference = build_facial_reference(authority, datums)
    expected = build_eye_rolled_exterior_shell(authority, facial_reference).val()
    actual = candidate.rigid_shell.solid.val()

    assert float(actual.Volume()) == pytest.approx(
        float(expected.Volume()),
        abs=VOLUME_TOLERANCE_MM3,
    )
    expected_bb = expected.BoundingBox()
    actual_bb = actual.BoundingBox()
    for expected_value, actual_value in (
        (expected_bb.xmin, actual_bb.xmin),
        (expected_bb.xmax, actual_bb.xmax),
        (expected_bb.ymin, actual_bb.ymin),
        (expected_bb.ymax, actual_bb.ymax),
        (expected_bb.zmin, actual_bb.zmin),
        (expected_bb.zmax, actual_bb.zmax),
    ):
        assert float(actual_value) == pytest.approx(
            float(expected_value),
            abs=BOUND_TOLERANCE_MM,
        )


def test_integrated_candidate_does_not_mutate_released_model():
    model, candidate = _candidate_context()
    baseline_shell = model.shell.solid.val()
    candidate_shell = candidate.rigid_shell.solid.val()

    assert candidate.rigid_shell is not model.shell
    assert candidate.rigid_shell.solid is not model.shell.solid
    assert float(candidate_shell.Volume()) != pytest.approx(
        float(baseline_shell.Volume()),
        abs=VOLUME_TOLERANCE_MM3,
    )
    assert candidate.authority is model.authority
    assert candidate.facial_reference is model.facial_reference


def test_integration_manifest_is_fail_closed_on_claim_scope():
    manifest = integrated_exterior_manifest()
    assert manifest["integration_status"] == MVP_EXTERIOR_STATUS
    assert manifest["integration_policy"] == (
        "CURRENT_MAIN_COMPONENT_SET_PRESERVED_EXCEPT_RIGID_SHELL;"
        "CELL2_REAR_SERVICE_SKIN_REMAINS_SEPARATE_PENDING_DRY_SIDE_PACKAGE_REFLOW"
    )
    assert "PENDING_DRY_SIDE_PACKAGE_REFLOW" in manifest["integration_policy"]
    assert manifest["foreign_lane_geometry_modified"] is False
    assert "PHYSICAL" in manifest["evidence_status"]
