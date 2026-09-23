from dataclasses import replace
import math
import pytest

from masck_one import retention_quick_release_tactile_v43 as v43


def test_v43_builds_and_reconstructs_rectangle_metrics() -> None:
    audit = v43.build_retention_quick_release_tactile_v43()
    manifest = audit.manifest()["declared_clearance_tolerance_metrics"]
    assert audit.radial_span_mm == audit.prior.radial_maximum_mm - audit.prior.radial_nominal_mm
    assert audit.side_span_mm == audit.prior.side_maximum_mm - audit.prior.side_nominal_mm
    assert audit.rectangle_area_mm2 == audit.radial_span_mm * audit.side_span_mm
    assert audit.rectangle_diagonal_mm == math.hypot(audit.radial_span_mm, audit.side_span_mm)
    assert manifest["rectangle_area_mm2"] > 0.0
    assert len(audit.tolerance_metric_binding_sha256) == 64


def test_v43_rejects_stale_span_with_unchanged_v42_evidence() -> None:
    audit = v43.build_retention_quick_release_tactile_v43()
    with pytest.raises(v43.RetentionQuickReleaseTactileV43Error):
        replace(audit, radial_span_mm=audit.radial_span_mm + 0.001).validate()


def test_v43_rejects_axis_metric_swap() -> None:
    audit = v43.build_retention_quick_release_tactile_v43()
    assert audit.radial_span_mm != audit.side_span_mm
    with pytest.raises(v43.RetentionQuickReleaseTactileV43Error):
        replace(audit, radial_span_mm=audit.side_span_mm, side_span_mm=audit.radial_span_mm).validate()


def test_v43_rejects_stale_metric_digest() -> None:
    audit = v43.build_retention_quick_release_tactile_v43()
    with pytest.raises(v43.RetentionQuickReleaseTactileV43Error):
        replace(audit, tolerance_metric_binding_sha256="0" * 64).validate()
