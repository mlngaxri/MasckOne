from dataclasses import replace

import pytest

from masck_one.spatial import Point3
from masck_one.surface_workflow import SurfaceSample
from masck_one.visual_inspection import inspect_surface_samples
from masck_one.visual_regression import VisualRegressionError, compare_visual_reports


def _samples():
    return (
        SurfaceSample("A", Point3(-20.0, -30.0, -4.0)),
        SurfaceSample("B", Point3(20.0, -30.0, 6.0)),
        SurfaceSample("C", Point3(20.0, 30.0, 8.0)),
        SurfaceSample("D", Point3(-20.0, 30.0, -8.0)),
    )


def test_comparison_is_deterministic_provenance_bound_and_threshold_free():
    baseline = inspect_surface_samples(_samples())
    changed = list(_samples())
    changed[2] = SurfaceSample("C", Point3(22.0, 31.0, 9.0))
    candidate = inspect_surface_samples(changed)
    comparison = compare_visual_reports(baseline, candidate)
    assert comparison.baseline_report_sha256 == baseline.report_sha256
    assert comparison.candidate_report_sha256 == candidate.report_sha256
    assert comparison.baseline_sample_manifest_sha256 == baseline.source_sample_manifest_sha256
    assert comparison.candidate_sample_manifest_sha256 == candidate.source_sample_manifest_sha256
    assert comparison.geometry_changed is True
    assert comparison.physical_validation_eligible is False
    assert "accept" not in comparison.manifest()
    assert comparison.comparison_sha256 == compare_visual_reports(baseline, candidate).comparison_sha256


def test_signed_span_and_centroid_deltas_preserve_direction():
    baseline = inspect_surface_samples(_samples())
    changed = tuple(SurfaceSample(sample.sample_id, Point3(sample.point.x + 3.0, sample.point.y, sample.point.z)) for sample in _samples())
    candidate = inspect_surface_samples(changed)
    comparison = compare_visual_reports(baseline, candidate)
    views = {delta.view_id: delta for delta in comparison.view_deltas}
    assert views["FRONT"].horizontal_span_delta_mm == pytest.approx(0.0)
    assert views["FRONT"].centroid_horizontal_shift_mm == pytest.approx(3.0)
    assert views["REAR"].centroid_horizontal_shift_mm == pytest.approx(-3.0)
    assert views["TOP"].centroid_horizontal_shift_mm == pytest.approx(-3.0)
    assert views["BOTTOM"].centroid_horizontal_shift_mm == pytest.approx(3.0)


def test_identical_geometry_is_explicitly_reported_without_false_change():
    baseline = inspect_surface_samples(_samples())
    candidate = inspect_surface_samples(reversed(_samples()))
    comparison = compare_visual_reports(baseline, candidate)
    assert comparison.geometry_changed is False
    assert all(delta.horizontal_span_delta_mm == 0.0 for delta in comparison.view_deltas)
    assert all(delta.vertical_span_delta_mm == 0.0 for delta in comparison.view_deltas)


def test_wrong_object_types_fail_closed():
    report = inspect_surface_samples(_samples())
    with pytest.raises(VisualRegressionError, match="VisualInspectionReport"):
        compare_visual_reports(report, object())


def test_tampered_coordinate_basis_cannot_be_compared():
    baseline = inspect_surface_samples(_samples())
    candidate = inspect_surface_samples(_samples())
    tampered_view = replace(candidate.views[0], horizontal_sign=-1)
    object.__setattr__(candidate, "views", (tampered_view, *candidate.views[1:]))
    with pytest.raises(VisualRegressionError, match="mismatched view identities or coordinate bases"):
        compare_visual_reports(baseline, candidate)


def test_comparison_identity_rejects_digest_alias_and_physical_promotion():
    baseline = inspect_surface_samples(_samples())
    changed = list(_samples())
    changed[0] = SurfaceSample("A", Point3(-21.0, -30.0, -4.0))
    comparison = compare_visual_reports(baseline, inspect_surface_samples(changed))
    with pytest.raises(VisualRegressionError, match="lowercase canonical SHA-256"):
        replace(comparison, baseline_report_sha256=comparison.baseline_report_sha256.upper())
    with pytest.raises(VisualRegressionError, match="physical-validation"):
        replace(comparison, physical_validation_eligible=True)


def test_nonfinite_or_boolean_delta_metrics_are_rejected():
    baseline = inspect_surface_samples(_samples())
    comparison = compare_visual_reports(baseline, baseline)
    bad_nan = replace(comparison.view_deltas[0], aspect_ratio_delta=float("nan"))
    with pytest.raises(VisualRegressionError, match="non-finite or non-real"):
        replace(comparison, view_deltas=(bad_nan, *comparison.view_deltas[1:]))
    bad_bool = replace(comparison.view_deltas[0], horizontal_span_delta_mm=True)
    with pytest.raises(VisualRegressionError, match="non-finite or non-real"):
        replace(comparison, view_deltas=(bad_bool, *comparison.view_deltas[1:]))
