from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import re


class SurfaceContinuityError(ValueError):
    """Raised when digital surface-continuity inspection data is invalid."""


_SCHEMA = "MASCK_ONE_SURFACE_CONTINUITY_V1"
_EVIDENCE_STATUS = "DIGITAL_SURFACE_CONTINUITY_METRICS_ONLY_NOT_CLASS_A_OR_PHYSICAL_EVIDENCE"
_ALLOWED_TARGETS = ("G0", "G1", "G2")
_WORLD_FRAME = "MASCK_ONE_ROOT_WORLD_MM"
_SEAM_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


def _finite_real(value: object) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(float(value))
    except (OverflowError, ValueError):
        return False


def _canonical_float(value: object) -> float:
    numeric = float(value)
    return 0.0 if numeric == 0.0 else numeric


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
        if not isinstance(self.seam_id, str) or not _SEAM_ID_RE.fullmatch(self.seam_id):
            raise SurfaceContinuityError("Seam identity must be canonical lowercase identifier text")
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
            "max_position_gap_mm": _canonical_float(self.max_position_gap_mm),
            "max_tangent_angle_deg": _canonical_float(self.max_tangent_angle_deg),
            "max_curvature_delta_per_mm": _canonical_float(self.max_curvature_delta_per_mm),
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
        if self.coordinate_frame != _WORLD_FRAME:
            raise SurfaceContinuityError("Surface continuity metrics must use the controlled root/world millimetre frame")
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

    def assert_current_geometry(self, current_geometry_sha256: object) -> None:
        if not _canonical_sha256(current_geometry_sha256):
            raise SurfaceContinuityError("Current geometry identity must be canonical lowercase SHA-256")
        if current_geometry_sha256 != self.source_geometry_sha256:
            raise SurfaceContinuityError("Surface continuity report is stale for the current geometry")

    @property
    def report_sha256(self) -> str:
        self.__post_init__()
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
