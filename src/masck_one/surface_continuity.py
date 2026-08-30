from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math


class SurfaceContinuityError(ValueError):
    """Raised when digital surface-continuity inspection data is invalid."""


_SCHEMA = "MASCK_ONE_SURFACE_CONTINUITY_V1"
_EVIDENCE_STATUS = "DIGITAL_SURFACE_CONTINUITY_METRICS_ONLY_NOT_CLASS_A_OR_PHYSICAL_EVIDENCE"
_ALLOWED_TARGETS = ("G0", "G1", "G2")


def _finite_real(value: object) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(float(value))


def _canonical_sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


@dataclass(frozen=True, slots=True)
class SeamContinuityMetrics:
    seam_id: str
    target: str
    sample_count: int
    max_position_gap_mm: float
    max_tangent_angle_deg: float
    max_curvature_delta_per_mm: float

    def __post_init__(self) -> None:
        if not isinstance(self.seam_id, str) or not self.seam_id.strip():
            raise SurfaceContinuityError("Seam identity must be nonblank text")
        if self.target not in _ALLOWED_TARGETS:
            raise SurfaceContinuityError("Continuity target must be G0, G1, or G2")
        if type(self.sample_count) is not int or self.sample_count < 3:
            raise SurfaceContinuityError("Continuity sampling requires at least three samples")
        metrics = (
            self.max_position_gap_mm,
            self.max_tangent_angle_deg,
            self.max_curvature_delta_per_mm,
        )
        if not all(_finite_real(value) and float(value) >= 0.0 for value in metrics):
            raise SurfaceContinuityError("Continuity metrics must be finite nonnegative real values")

    def manifest(self) -> dict[str, object]:
        return {
            "seam_id": self.seam_id,
            "target": self.target,
            "sample_count": self.sample_count,
            "max_position_gap_mm": float(self.max_position_gap_mm),
            "max_tangent_angle_deg": float(self.max_tangent_angle_deg),
            "max_curvature_delta_per_mm": float(self.max_curvature_delta_per_mm),
        }


@dataclass(frozen=True, slots=True)
class SurfaceContinuityReport:
    source_geometry_sha256: str
    coordinate_frame: str
    seams: tuple[SeamContinuityMetrics, ...]
    evidence_status: str = _EVIDENCE_STATUS
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        if not _canonical_sha256(self.source_geometry_sha256):
            raise SurfaceContinuityError("Source geometry identity must be canonical lowercase SHA-256")
        if not isinstance(self.coordinate_frame, str) or not self.coordinate_frame.strip():
            raise SurfaceContinuityError("Coordinate frame must be explicit nonblank text")
        if not isinstance(self.seams, tuple) or not self.seams or not all(isinstance(seam, SeamContinuityMetrics) for seam in self.seams):
            raise SurfaceContinuityError("Seams must be a nonempty immutable tuple of continuity records")
        seam_ids = tuple(seam.seam_id for seam in self.seams)
        if len(set(seam_ids)) != len(seam_ids) or seam_ids != tuple(sorted(seam_ids)):
            raise SurfaceContinuityError("Seam identities must be unique and canonically sorted")
        for seam in self.seams:
            seam.__post_init__()
        if self.evidence_status != _EVIDENCE_STATUS:
            raise SurfaceContinuityError("Surface continuity evidence status is controlled")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise SurfaceContinuityError("Digital continuity inspection cannot be physical-validation evidence")

    @property
    def report_sha256(self) -> str:
        payload = {
            "schema": _SCHEMA,
            "source_geometry_sha256": self.source_geometry_sha256,
            "coordinate_frame": self.coordinate_frame,
            "seams": [seam.manifest() for seam in self.seams],
            "evidence_status": self.evidence_status,
            "physical_validation_eligible": self.physical_validation_eligible,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()
