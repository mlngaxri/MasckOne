from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math

from .visual_inspection import VisualInspectionError, VisualInspectionReport


class VisualRegressionError(ValueError):
    """Raised when visual-regression comparison inputs or derived metrics are invalid."""


_SCHEMA = "MASCK_ONE_VISUAL_REGRESSION_V1"
_VIEW_ORDER = ("FRONT", "REAR", "LEFT", "RIGHT", "TOP", "BOTTOM")
_EVIDENCE_STATUS = "DIGITAL_GEOMETRY_REGRESSION_METRICS_ONLY_NO_AESTHETIC_OR_PHYSICAL_ACCEPTANCE_THRESHOLD"


def _canonical_sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _finite_real(value: object) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(float(value))


def _revalidate_report(report: VisualInspectionReport, label: str) -> None:
    try:
        report.__post_init__()
    except (VisualInspectionError, AttributeError, TypeError, ValueError) as exc:
        raise VisualRegressionError(f"Visual regression {label} report fails inspection invariants: {exc}") from exc


@dataclass(frozen=True, slots=True)
class ViewDelta:
    view_id: str
    horizontal_span_delta_mm: float
    vertical_span_delta_mm: float
    horizontal_span_delta_fraction: float
    vertical_span_delta_fraction: float
    aspect_ratio_delta: float
    centroid_horizontal_shift_mm: float
    centroid_vertical_shift_mm: float

    def __post_init__(self) -> None:
        if self.view_id not in _VIEW_ORDER:
            raise VisualRegressionError(f"Unknown controlled view {self.view_id!r}")
        values = (self.horizontal_span_delta_mm, self.vertical_span_delta_mm, self.horizontal_span_delta_fraction, self.vertical_span_delta_fraction, self.aspect_ratio_delta, self.centroid_horizontal_shift_mm, self.centroid_vertical_shift_mm)
        if not all(_finite_real(value) for value in values):
            raise VisualRegressionError(f"{self.view_id} contains non-finite or non-real regression metrics")

    def manifest(self) -> dict[str, object]:
        return {"view_id": self.view_id, "horizontal_span_delta_mm": self.horizontal_span_delta_mm, "vertical_span_delta_mm": self.vertical_span_delta_mm, "horizontal_span_delta_fraction": self.horizontal_span_delta_fraction, "vertical_span_delta_fraction": self.vertical_span_delta_fraction, "aspect_ratio_delta": self.aspect_ratio_delta, "centroid_horizontal_shift_mm": self.centroid_horizontal_shift_mm, "centroid_vertical_shift_mm": self.centroid_vertical_shift_mm}


@dataclass(frozen=True, slots=True)
class VisualRegressionComparison:
    baseline_report_sha256: str
    candidate_report_sha256: str
    baseline_sample_manifest_sha256: str
    candidate_sample_manifest_sha256: str
    view_deltas: tuple[ViewDelta, ...]
    evidence_status: str = _EVIDENCE_STATUS
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        identities = (self.baseline_report_sha256, self.candidate_report_sha256, self.baseline_sample_manifest_sha256, self.candidate_sample_manifest_sha256)
        if not all(_canonical_sha256(value) for value in identities):
            raise VisualRegressionError("Regression source identities must be lowercase canonical SHA-256 strings")
        if not isinstance(self.view_deltas, tuple):
            raise VisualRegressionError("Regression deltas must be an immutable tuple")
        if tuple(delta.view_id for delta in self.view_deltas) != _VIEW_ORDER:
            raise VisualRegressionError("Regression deltas must preserve the controlled six-view order")
        for delta in self.view_deltas:
            if not isinstance(delta, ViewDelta):
                raise VisualRegressionError("Regression deltas must contain only ViewDelta records")
            delta.__post_init__()
        if self.evidence_status != _EVIDENCE_STATUS:
            raise VisualRegressionError("Regression evidence status is controlled and cannot be promoted or relabelled")
        if not isinstance(self.physical_validation_eligible, bool):
            raise VisualRegressionError("Physical-validation eligibility must be an explicit boolean")
        if self.physical_validation_eligible:
            raise VisualRegressionError("Digital visual regression cannot be physical-validation evidence")

    @property
    def comparison_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    @property
    def geometry_changed(self) -> bool:
        return self.baseline_sample_manifest_sha256 != self.candidate_sample_manifest_sha256

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {"schema": _SCHEMA, "baseline_report_sha256": self.baseline_report_sha256, "candidate_report_sha256": self.candidate_report_sha256, "baseline_sample_manifest_sha256": self.baseline_sample_manifest_sha256, "candidate_sample_manifest_sha256": self.candidate_sample_manifest_sha256, "view_deltas": [delta.manifest() for delta in self.view_deltas], "geometry_changed": self.geometry_changed, "evidence_status": self.evidence_status, "physical_validation_eligible": self.physical_validation_eligible}
        if include_sha:
            payload["comparison_sha256"] = self.comparison_sha256
        return payload


def compare_visual_reports(baseline: VisualInspectionReport, candidate: VisualInspectionReport) -> VisualRegressionComparison:
    """Compare two provenance-bound six-view reports without inventing acceptance thresholds."""
    if not isinstance(baseline, VisualInspectionReport) or not isinstance(candidate, VisualInspectionReport):
        raise VisualRegressionError("Visual regression requires VisualInspectionReport inputs")
    _revalidate_report(baseline, "baseline")
    _revalidate_report(candidate, "candidate")
    deltas: list[ViewDelta] = []
    for base_view, candidate_view in zip(baseline.views, candidate.views, strict=True):
        base_basis = (base_view.horizontal_axis, base_view.horizontal_sign, base_view.vertical_axis, base_view.vertical_sign)
        candidate_basis = (candidate_view.horizontal_axis, candidate_view.horizontal_sign, candidate_view.vertical_axis, candidate_view.vertical_sign)
        if base_view.view_id != candidate_view.view_id or base_basis != candidate_basis:
            raise VisualRegressionError("Visual regression cannot compare mismatched view identities or coordinate bases")
        h_delta = candidate_view.horizontal_span_mm - base_view.horizontal_span_mm
        v_delta = candidate_view.vertical_span_mm - base_view.vertical_span_mm
        deltas.append(ViewDelta(view_id=base_view.view_id, horizontal_span_delta_mm=h_delta, vertical_span_delta_mm=v_delta, horizontal_span_delta_fraction=h_delta / base_view.horizontal_span_mm, vertical_span_delta_fraction=v_delta / base_view.vertical_span_mm, aspect_ratio_delta=candidate_view.aspect_ratio - base_view.aspect_ratio, centroid_horizontal_shift_mm=candidate_view.centroid_horizontal_mm - base_view.centroid_horizontal_mm, centroid_vertical_shift_mm=candidate_view.centroid_vertical_mm - base_view.centroid_vertical_mm))
    return VisualRegressionComparison(baseline_report_sha256=baseline.report_sha256, candidate_report_sha256=candidate.report_sha256, baseline_sample_manifest_sha256=baseline.source_sample_manifest_sha256, candidate_sample_manifest_sha256=candidate.source_sample_manifest_sha256, view_deltas=tuple(deltas))
