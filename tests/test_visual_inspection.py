from dataclasses import replace

import pytest

from masck_one.spatial import Point3
from masck_one.surface_workflow import SurfaceSample, surface_sample_manifest_sha256
from masck_one.visual_inspection import VisualInspectionError, inspect_surface_samples


def _samples():
    return (
        SurfaceSample("A", Point3(-20.0, -30.0, -4.0)),
        SurfaceSample("B", Point3(20.0, -30.0, 6.0)),
        SurfaceSample("C", Point3(20.0, 30.0, 8.0)),
        SurfaceSample("D", Point3(-20.0, 30.0, -8.0)),
    )


def _asymmetric_samples():
    return (
        SurfaceSample("A", Point3(-10.0, -20.0, -5.0)),
        SurfaceSample("B", Point3(30.0, -10.0, 4.0)),
        SurfaceSample("C", Point3(20.0, 25.0, 12.0)),
        SurfaceSample("D", Point3(-5.0, 15.0, -2.0)),
    )


def test_six_view_metrics_are_deterministic_and_provenance_bound():
    samples = _samples()
    report = inspect_surface_samples(reversed(samples))
    assert report.source_sample_manifest_sha256 == surface_sample_manifest_sha256(samples)
    assert tuple(view.view_id for view in report.views) == ("FRONT", "REAR", "LEFT", "RIGHT", "TOP", "BOTTOM")
    front = report.views[0]
    assert front.horizontal_axis == "X"
    assert front.horizontal_sign == 1
    assert front.vertical_axis == "Y"
    assert front.vertical_sign == 1
    assert front.horizontal_span_mm == pytest.approx(40.0)
    assert front.vertical_span_mm == pytest.approx(60.0)
    assert front.aspect_ratio == pytest.approx(2.0 / 3.0)
    assert report.report_sha256 == inspect_surface_samples(samples).report_sha256
    assert report.physical_validation_eligible is False


def test_metrics_are_order_invariant_for_adversarial_floating_point_inputs():
    samples = (
        SurfaceSample("A", Point3(1.0e16, -30.0, -4.0)),
        SurfaceSample("B", Point3(-1.0e16, -20.0, 6.0)),
        SurfaceSample("C", Point3(1.0, 30.0, 8.0)),
        SurfaceSample("D", Point3(3.0, 10.0, -8.0)),
    )
    forward = inspect_surface_samples(samples)
    reverse = inspect_surface_samples(reversed(samples))
    assert forward.report_sha256 == reverse.report_sha256
    assert forward.views == reverse.views


def test_finite_inputs_that_overflow_derived_span_are_rejected():
    huge = 1.0e308
    samples = (
        SurfaceSample("A", Point3(-huge, -30.0, -4.0)),
        SurfaceSample("B", Point3(huge, -20.0, 6.0)),
        SurfaceSample("C", Point3(0.0, 30.0, 8.0)),
    )
    with pytest.raises(VisualInspectionError, match="non-finite"):
        inspect_surface_samples(samples)


def test_opposing_views_preserve_handedness_instead_of_collapsing():
    report = inspect_surface_samples(_asymmetric_samples())
    views = {view.view_id: view for view in report.views}
    assert views["FRONT"].horizontal_span_mm == pytest.approx(views["REAR"].horizontal_span_mm)
    assert views["FRONT"].centroid_horizontal_mm == pytest.approx(-views["REAR"].centroid_horizontal_mm)
    assert views["LEFT"].horizontal_span_mm == pytest.approx(views["RIGHT"].horizontal_span_mm)
    assert views["LEFT"].centroid_horizontal_mm == pytest.approx(-views["RIGHT"].centroid_horizontal_mm)
    assert views["TOP"].horizontal_span_mm == pytest.approx(views["BOTTOM"].horizontal_span_mm)
    assert views["TOP"].centroid_horizontal_mm == pytest.approx(-views["BOTTOM"].centroid_horizontal_mm)


def test_geometry_change_changes_report_identity():
    original = inspect_surface_samples(_samples())
    changed = list(_samples())
    changed[2] = SurfaceSample("C", Point3(21.0, 30.0, 8.0))
    revised = inspect_surface_samples(changed)
    assert revised.source_sample_manifest_sha256 != original.source_sample_manifest_sha256
    assert revised.report_sha256 != original.report_sha256


def test_duplicate_ids_are_rejected():
    samples = list(_samples())
    samples[-1] = SurfaceSample("A", samples[-1].point)
    with pytest.raises(VisualInspectionError, match="unique non-empty"):
        inspect_surface_samples(samples)


def test_degenerate_projection_is_rejected_instead_of_faking_metrics():
    samples = (
        SurfaceSample("A", Point3(-1.0, -1.0, 0.0)),
        SurfaceSample("B", Point3(1.0, -1.0, 0.0)),
        SurfaceSample("C", Point3(0.0, 1.0, 0.0)),
    )
    with pytest.raises(VisualInspectionError, match="degenerate"):
        inspect_surface_samples(samples)


def test_digital_report_cannot_be_promoted_to_physical_evidence():
    report = inspect_surface_samples(_samples())
    with pytest.raises(VisualInspectionError, match="physical-validation"):
        replace(report, physical_validation_eligible=True)
    with pytest.raises(VisualInspectionError, match="explicit boolean"):
        replace(report, physical_validation_eligible=0)
    with pytest.raises(VisualInspectionError, match="cannot be promoted or relabelled"):
        replace(report, evidence_status="PHYSICALLY_VALIDATED_APPEARANCE")
    with pytest.raises(VisualInspectionError, match="cannot be promoted or relabelled"):
        replace(report, evidence_status="")


def test_view_basis_tampering_is_rejected():
    report = inspect_surface_samples(_asymmetric_samples())
    tampered_front = replace(report.views[0], horizontal_sign=-1)
    with pytest.raises(VisualInspectionError, match="controlled signed world-coordinate basis"):
        replace(report, views=(tampered_front, *report.views[1:]))


def test_view_basis_rejects_boolean_sign_aliases_and_nonrecord_containers():
    report = inspect_surface_samples(_asymmetric_samples())
    bool_front = replace(report.views[0], horizontal_sign=True)
    with pytest.raises(VisualInspectionError, match="literal integer -1 or 1"):
        replace(report, views=(bool_front, *report.views[1:]))
    with pytest.raises(VisualInspectionError, match="immutable tuple of ViewMetrics"):
        replace(report, views=list(report.views))
    malformed = object.__new__(type(report.views[0]))
    with pytest.raises(VisualInspectionError, match="immutable tuple of ViewMetrics"):
        replace(report, views=(malformed, *report.views[1:]))


def test_report_rejects_noncanonical_source_identity_and_nonfinite_derived_metric():
    report = inspect_surface_samples(_samples())
    with pytest.raises(VisualInspectionError, match="lowercase canonical SHA-256"):
        replace(report, source_sample_manifest_sha256=report.source_sample_manifest_sha256.upper())
    bad_front = replace(report.views[0], aspect_ratio=float("nan"))
    with pytest.raises(VisualInspectionError, match="non-finite"):
        replace(report, views=(bad_front, *report.views[1:]))
