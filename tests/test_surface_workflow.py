from dataclasses import replace

import pytest

from masck_one.authority import load_authority
from masck_one.spatial import Point3
from masck_one.surface_workflow import (
    ClassAReferenceWorkflow,
    ReleasedSurfaceReference,
    SurfaceSample,
    SurfaceWorkflowError,
    build_class_a_workflow,
    sha256_bytes,
)


def _samples(offset_mm: float = 0.0):
    engineering = (
        SurfaceSample("A", Point3(0.0, 0.0, 0.0)),
        SurfaceSample("B", Point3(10.0, 0.0, 0.0)),
    )
    reference = (
        SurfaceSample("A", Point3(0.0, 0.0, offset_mm)),
        SurfaceSample("B", Point3(10.0, 0.0, offset_mm)),
    )
    return engineering, reference


def test_workflow_consumes_authority_limits_and_status():
    authority = load_authority()
    workflow = build_class_a_workflow(authority)
    assert workflow.rms_limit_mm == authority.number("manufacturing", "a_surface", "rms_deviation_max_mm")
    assert workflow.maximum_limit_mm == authority.number("manufacturing", "a_surface", "max_deviation_mm")
    assert workflow.authority_status == str(authority.get("manufacturing", "a_surface", "status"))
    assert workflow.physical_validation_eligible is False


def test_numeric_pass_without_released_reference_remains_blocked():
    workflow = build_class_a_workflow(load_authority())
    engineering, reference = _samples(0.10)
    report = workflow.evaluate(engineering, reference)
    assert report.numeric_gate_passed is True
    assert report.reference_release_eligible is False
    assert report.product_validation_status == "BLOCKED_RELEASE_REFERENCE_REQUIRED"


def test_released_reference_allows_only_digital_cad_closure_status():
    ref = ReleasedSurfaceReference(
        surface_id="MASCK_ONE-CLASS-A-REF-001",
        sha256=sha256_bytes(b"controlled-reference"),
        revision="R1",
        release_status="RELEASED_CLASS_A_REFERENCE",
    )
    workflow = build_class_a_workflow(load_authority(), reference=ref)
    engineering, reference = _samples(0.10)
    report = workflow.evaluate(engineering, reference)
    assert report.numeric_gate_passed is True
    assert report.reference_release_eligible is True
    assert report.product_validation_status == "CAD_CLOSURE_NUMERIC_PASS_AGAINST_RELEASED_REFERENCE"
    assert workflow.physical_validation_eligible is False


def test_deviation_over_limit_fails_numeric_gate():
    workflow = build_class_a_workflow(load_authority())
    engineering, reference = _samples(1.0)
    report = workflow.evaluate(engineering, reference)
    assert report.numeric_gate_passed is False
    assert report.product_validation_status == "CAD_CLOSURE_NUMERIC_FAIL"


def test_duplicate_sample_ids_are_rejected_not_silently_overwritten():
    workflow = build_class_a_workflow(load_authority())
    engineering = (
        SurfaceSample("A", Point3(0.0, 0.0, 0.0)),
        SurfaceSample("A", Point3(1.0, 0.0, 0.0)),
    )
    _, reference = _samples()
    with pytest.raises(SurfaceWorkflowError, match="unique"):
        workflow.evaluate(engineering, reference)


def test_mismatched_sample_ids_are_rejected():
    workflow = build_class_a_workflow(load_authority())
    engineering, _ = _samples()
    reference = (SurfaceSample("C", Point3(0.0, 0.0, 0.0)),)
    with pytest.raises(SurfaceWorkflowError, match="identical IDs"):
        workflow.evaluate(engineering, reference)


def test_invalid_reference_hash_or_release_status_is_rejected():
    with pytest.raises(SurfaceWorkflowError, match="SHA-256"):
        ReleasedSurfaceReference("ID", "abc", "R1", "RELEASED_CLASS_A_REFERENCE")
    with pytest.raises(SurfaceWorkflowError, match="explicit release status"):
        ReleasedSurfaceReference("ID", "0" * 64, "R1", "DRAFT")


def test_workflow_cannot_be_promoted_to_physical_validation():
    workflow = build_class_a_workflow(load_authority())
    with pytest.raises(SurfaceWorkflowError, match="not physical validation evidence"):
        replace(workflow, physical_validation_eligible=True)


def test_workflow_is_deterministic():
    first = build_class_a_workflow(load_authority())
    second = build_class_a_workflow(load_authority())
    engineering, reference = _samples(0.10)
    assert first.evaluate(engineering, reference) == second.evaluate(engineering, reference)
