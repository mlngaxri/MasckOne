from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Iterable

from .surface_workflow import SurfaceSample, surface_sample_manifest_sha256


class VisualInspectionError(ValueError):
    """Raised when deterministic visual-inspection geometry is invalid."""


_VIEW_BASES: dict[str, tuple[int, float, int, float]] = {
    "FRONT": (0, 1.0, 1, 1.0),
    "REAR": (0, -1.0, 1, 1.0),
    "LEFT": (2, 1.0, 1, 1.0),
    "RIGHT": (2, -1.0, 1, 1.0),
    "TOP": (0, -1.0, 2, 1.0),
    "BOTTOM": (0, 1.0, 2, 1.0),
}
_VIEW_ORDER = tuple(_VIEW_BASES)
_SCHEMA = "MASCK_ONE_VISUAL_INSPECTION_V2"
_AXIS_NAMES = ("X", "Y", "Z")
_EVIDENCE_STATUS = "DIGITAL_INSPECTION_METRICS_ONLY_NOT_APPEARANCE_FIT_OR_MANUFACTURING_EVIDENCE"


def _canonical_sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _finite_metric(value: object) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(float(value))


def _canonical_basis_sign(value: object) -> bool:
    return type(value) is int and value in (-1, 1)


@dataclass(frozen=True, slots=True)
class ViewMetrics:
    view_id: str
    horizontal_axis: str
    horizontal_sign: int
    vertical_axis: str
    vertical_sign: int
    horizontal_span_mm: float
    vertical_span_mm: float
    aspect_ratio: float
    centroid_horizontal_mm: float
    centroid_vertical_mm: float
    sample_count: int

    def manifest(self) -> dict[str, object]:
        return {
            "view_id": self.view_id,
            "horizontal_axis": self.horizontal_axis,
            "horizontal_sign": self.horizontal_sign,
            "vertical_axis": self.vertical_axis,
            "vertical_sign": self.vertical_sign,
            "horizontal_span_mm": self.horizontal_span_mm,
            "vertical_span_mm": self.vertical_span_mm,
            "aspect_ratio": self.aspect_ratio,
            "centroid_horizontal_mm": self.centroid_horizontal_mm,
            "centroid_vertical_mm": self.centroid_vertical_mm,
            "sample_count": self.sample_count,
        }


@dataclass(frozen=True, slots=True)
class VisualInspectionReport:
    source_sample_manifest_sha256: str
    views: tuple[ViewMetrics, ...]
    evidence_status: str = _EVIDENCE_STATUS
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        if not _canonical_sha256(self.source_sample_manifest_sha256):
            raise VisualInspectionError("Inspection source identity must be lowercase canonical SHA-256")
        if not isinstance(self.views, tuple) or not all(isinstance(view, ViewMetrics) for view in self.views):
            raise VisualInspectionError("Inspection views must be an immutable tuple of ViewMetrics records")
        try:
            view_ids = tuple(view.view_id for view in self.views)
        except AttributeError as exc:
            raise VisualInspectionError("Inspection views must be complete ViewMetrics records") from exc
        if view_ids != _VIEW_ORDER:
            raise VisualInspectionError("Inspection views must follow the controlled six-view order")
        for view in self.views:
            try:
                basis = _VIEW_BASES[view.view_id]
                horizontal_sign = view.horizontal_sign
                vertical_sign = view.vertical_sign
                horizontal_axis = view.horizontal_axis
                vertical_axis = view.vertical_axis
                metrics = (view.horizontal_span_mm, view.vertical_span_mm, view.aspect_ratio, view.centroid_horizontal_mm, view.centroid_vertical_mm)
                sample_count = view.sample_count
            except AttributeError as exc:
                raise VisualInspectionError("Inspection views must be complete ViewMetrics records") from exc
            if not _canonical_basis_sign(horizontal_sign) or not _canonical_basis_sign(vertical_sign):
                raise VisualInspectionError(f"{view.view_id} basis signs must be literal integer -1 or 1 values")
            expected = (_AXIS_NAMES[basis[0]], int(basis[1]), _AXIS_NAMES[basis[2]], int(basis[3]))
            actual = (horizontal_axis, horizontal_sign, vertical_axis, vertical_sign)
            if actual != expected:
                raise VisualInspectionError(f"{view.view_id} metrics do not match the controlled signed world-coordinate basis")
            if not all(_finite_metric(value) for value in metrics):
                raise VisualInspectionError(f"{view.view_id} contains non-finite derived inspection metrics")
            if view.horizontal_span_mm <= 0.0 or view.vertical_span_mm <= 0.0 or view.aspect_ratio <= 0.0:
                raise VisualInspectionError(f"{view.view_id} contains non-positive derived inspection metrics")
            if isinstance(sample_count, bool) or not isinstance(sample_count, int) or sample_count < 3:
                raise VisualInspectionError(f"{view.view_id} sample count is invalid")
        if self.evidence_status != _EVIDENCE_STATUS:
            raise VisualInspectionError("Digital visual inspection evidence status is controlled and cannot be promoted or relabelled")
        if not isinstance(self.physical_validation_eligible, bool):
            raise VisualInspectionError("Physical-validation eligibility must be an explicit boolean")
        if self.physical_validation_eligible:
            raise VisualInspectionError("Digital visual inspection cannot be physical-validation evidence")

    @property
    def report_sha256(self) -> str:
        payload = self.manifest(include_sha=False)
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": _SCHEMA,
            "coordinate_frame": "MASCK_ONE_CANONICAL_WORLD_X_WEARER_RIGHT_Y_SUPERIOR_Z_ANTERIOR",
            "source_sample_manifest_sha256": self.source_sample_manifest_sha256,
            "views": [view.manifest() for view in self.views],
            "evidence_status": self.evidence_status,
            "physical_validation_eligible": self.physical_validation_eligible,
        }
        if include_sha:
            payload["report_sha256"] = self.report_sha256
        return payload


def _validated_samples(samples: Iterable[SurfaceSample]) -> tuple[SurfaceSample, ...]:
    materialized = tuple(samples)
    if len(materialized) < 3:
        raise VisualInspectionError("Visual inspection requires at least three surface samples")
    ids = [sample.sample_id for sample in materialized]
    if any(not sample_id.strip() for sample_id in ids) or len(ids) != len(set(ids)):
        raise VisualInspectionError("Visual inspection requires unique non-empty sample IDs")
    for sample in materialized:
        if not all(math.isfinite(value) for value in sample.point.as_tuple()):
            raise VisualInspectionError("Visual inspection requires finite world-coordinate samples")
    return tuple(sorted(materialized, key=lambda sample: sample.sample_id))


def _view_metrics(samples: tuple[SurfaceSample, ...], view_id: str) -> ViewMetrics:
    horizontal_axis, horizontal_sign, vertical_axis, vertical_sign = _VIEW_BASES[view_id]
    coordinates = [sample.point.as_tuple() for sample in samples]
    horizontal = [horizontal_sign * point[horizontal_axis] for point in coordinates]
    vertical = [vertical_sign * point[vertical_axis] for point in coordinates]
    h_span = max(horizontal) - min(horizontal)
    v_span = max(vertical) - min(vertical)
    if not math.isfinite(h_span) or not math.isfinite(v_span) or h_span <= 0.0 or v_span <= 0.0:
        raise VisualInspectionError(f"{view_id} projection is degenerate or non-finite; inspection metrics would be misleading")
    aspect_ratio = h_span / v_span
    centroid_horizontal = math.fsum(horizontal) / len(horizontal)
    centroid_vertical = math.fsum(vertical) / len(vertical)
    if not all(math.isfinite(value) for value in (aspect_ratio, centroid_horizontal, centroid_vertical)):
        raise VisualInspectionError(f"{view_id} derived inspection metrics are non-finite")
    return ViewMetrics(
        view_id=view_id,
        horizontal_axis=_AXIS_NAMES[horizontal_axis],
        horizontal_sign=int(horizontal_sign),
        vertical_axis=_AXIS_NAMES[vertical_axis],
        vertical_sign=int(vertical_sign),
        horizontal_span_mm=h_span,
        vertical_span_mm=v_span,
        aspect_ratio=aspect_ratio,
        centroid_horizontal_mm=centroid_horizontal,
        centroid_vertical_mm=centroid_vertical,
        sample_count=len(samples),
    )


def inspect_surface_samples(samples: Iterable[SurfaceSample]) -> VisualInspectionReport:
    """Create provenance-bound deterministic orthographic metrics from world-coordinate samples."""
    materialized = _validated_samples(samples)
    manifest_sha = surface_sample_manifest_sha256(materialized)
    views = tuple(_view_metrics(materialized, view_id) for view_id in _VIEW_ORDER)
    return VisualInspectionReport(source_sample_manifest_sha256=manifest_sha, views=views)
