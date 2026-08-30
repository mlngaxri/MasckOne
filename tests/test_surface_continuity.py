from dataclasses import replace
import math

import pytest

from masck_one.surface_continuity import (
    SeamContinuityMetrics,
    SurfaceContinuityError,
    SurfaceContinuityReport,
)


SOURCE = "1" * 64


def seam(seam_id: str = "outer_perimeter_left") -> SeamContinuityMetrics:
    return SeamContinuityMetrics(seam_id, "G2", 21, 0.02, 0.3, 0.01)


def report(*seams: SeamContinuityMetrics) -> SurfaceContinuityReport:
    records = seams or (seam(),)
    return SurfaceContinuityReport(SOURCE, "MASCK_ONE_ROOT_WORLD_MM", tuple(records))


def test_report_identity_is_deterministic_and_geometry_bound() -> None:
    assert report().report_sha256 == report().report_sha256
    assert report().report_sha256 != replace(report(), source_geometry_sha256="2" * 64).report_sha256


def test_seams_require_canonical_unique_order() -> None:
    a = seam("a")
    b = seam("b")
    with pytest.raises(SurfaceContinuityError):
        report(b, a)
    with pytest.raises(SurfaceContinuityError):
        report(a, a)


@pytest.mark.parametrize("bad", [math.nan, math.inf, -0.01, True])
def test_metrics_fail_closed_on_invalid_numeric_values(bad: object) -> None:
    with pytest.raises(SurfaceContinuityError):
        SeamContinuityMetrics("seam", "G1", 5, bad, 0.0, 0.0)


def test_boolean_sample_count_alias_is_rejected() -> None:
    with pytest.raises(SurfaceContinuityError):
        SeamContinuityMetrics("seam", "G1", True, 0.0, 0.0, 0.0)


def test_evidence_status_cannot_be_promoted_or_relabelled() -> None:
    with pytest.raises(SurfaceContinuityError):
        replace(report(), evidence_status="CLASS_A_ACCEPTED")
    with pytest.raises(SurfaceContinuityError):
        replace(report(), physical_validation_eligible=True)
    with pytest.raises(SurfaceContinuityError):
        replace(report(), physical_validation_eligible=1)


def test_post_construction_record_tampering_is_revalidated() -> None:
    record = seam()
    object.__setattr__(record, "max_tangent_angle_deg", math.nan)
    with pytest.raises(SurfaceContinuityError):
        report(record)


def test_contract_records_metrics_without_inventing_acceptance_thresholds() -> None:
    record = SeamContinuityMetrics("nose_transition", "G2", 31, 0.4, 17.0, 2.5)
    accepted = report(record)
    assert accepted.seams[0].max_tangent_angle_deg == 17.0
    assert accepted.physical_validation_eligible is False
