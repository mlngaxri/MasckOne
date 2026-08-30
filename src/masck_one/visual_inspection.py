from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Iterable

from .surface_workflow import SurfaceSample, surface_sample_manifest_sha256


class VisualInspectionError(ValueError):
    """Raised when deterministic visual-inspection geometry is invalid."""


# Each view uses an explicit signed screen basis in canonical world coordinates.
# This prevents opposing views from silently collapsing to the same unsigned
# projection and preserves handedness/asymmetry information for later visual
# regression work.
#
# Canonical axes: X wearer-right, Y superior, Z anterior.
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
    evidence_status: str = "DIGITAL_INSPECTION_METRICS_ONLY_NOT_APPEARANCE_FIT_OR_MANUFACTURING_EVIDENCE"
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        if tuple(view.view_id for view in self.views) != _VIEW_ORDER:
            raise VisualInspectionError("Inspection views must follow the controlled six-view order")
        for view in self.views:
            basis = _VIEW_BASES[view.view_id]
            expected = (
                _AXIS_NAMES[basis[0]],
                int(basis[1]),
                _AXIS_NAMES[basis[2]],
                int(basis[3]),
            )
            actual = (view.horizontal_axis, view.horizontal_sign, view.vertical_axis, view.vertical_sign)
            if actual != expected:
                raise VisualInspectionError(f"{view.view_id} metrics do not match the controlled signed world-coordinate basis")
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
    return materialized


def _view_metrics(samples: tuple[SurfaceSample, ...], view_id: str) -> ViewMetrics:
    horizontal_axis, horizontal_sign, vertical_axis, vertical_sign = _VIEW_BASES[view_id]
    coordinates = [sample.point.as_tuple() for sample in samples]
    horizontal = [horizontal_sign * point[horizontal_axis] for point in coordinates]
    vertical = [vertical_sign * point[vertical_axis] for point in coordinates]
    h_span = max(horizontal) - min(horizontal)
    v_span = max(vertical) - min(vertical)
    if h_span <= 0.0 or v_span <= 0.0:
        raise VisualInspectionError(f"{view_id} projection is degenerate; inspection metrics would be misleading")
    return ViewMetrics(
        view_id=view_id,
        horizontal_axis=_AXIS_NAMES[horizontal_axis],
        horizontal_sign=int(horizontal_sign),
        vertical_axis=_AXIS_NAMES[vertical_axis],
        vertical_sign=int(vertical_sign),
        horizontal_span_mm=h_span,
        vertical_span_mm=v_span,
        aspect_ratio=h_span / v_span,
        centroid_horizontal_mm=sum(horizontal) / len(horizontal),
        centroid_vertical_mm=sum(vertical) / len(vertical),
        sample_count=len(samples),
    )


def inspect_surface_samples(samples: Iterable[SurfaceSample]) -> VisualInspectionReport:
    """Create provenance-bound orthographic inspection metrics from world-coordinate samples.

    This deliberately supplies no aesthetic pass/fail threshold. It creates deterministic
    front/rear/left/right/top/bottom bookkeeping using controlled signed screen bases so
    opposing views retain handedness information. Later CAD and visual-regression work can
    compare these metrics without promoting sampled geometry into appearance or physical evidence.
    """
    materialized = _validated_samples(samples)
    manifest_sha = surface_sample_manifest_sha256(materialized)
    views = tuple(_view_metrics(materialized, view_id) for view_id in _VIEW_ORDER)
    return VisualInspectionReport(source_sample_manifest_sha256=manifest_sha, views=views)
