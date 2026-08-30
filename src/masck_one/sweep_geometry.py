from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math


class SweepGeometryError(ValueError):
    """Raised when a continuous-sweep contract would become non-conservative."""


def _finite3(values: tuple[float, float, float], *, label: str) -> tuple[float, float, float]:
    if len(values) != 3:
        raise SweepGeometryError(f"{label} must contain exactly three coordinates")
    out = tuple(float(v) for v in values)
    if not all(math.isfinite(v) for v in out):
        raise SweepGeometryError(f"{label} must be finite")
    return out  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class AABB:
    """Closed axis-aligned world-coordinate bounding box in millimetres."""

    minimum_xyz_mm: tuple[float, float, float]
    maximum_xyz_mm: tuple[float, float, float]

    def __post_init__(self) -> None:
        lo = _finite3(self.minimum_xyz_mm, label="AABB minimum")
        hi = _finite3(self.maximum_xyz_mm, label="AABB maximum")
        if any(a > b for a, b in zip(lo, hi)):
            raise SweepGeometryError("AABB minimum cannot exceed maximum")
        object.__setattr__(self, "minimum_xyz_mm", lo)
        object.__setattr__(self, "maximum_xyz_mm", hi)

    def intersects(self, other: "AABB", *, clearance_mm: float = 0.0) -> bool:
        clearance = float(clearance_mm)
        if not math.isfinite(clearance) or clearance < 0.0:
            raise SweepGeometryError("Collision clearance must be finite and non-negative")
        return all(
            self.minimum_xyz_mm[i] - clearance <= other.maximum_xyz_mm[i]
            and other.minimum_xyz_mm[i] - clearance <= self.maximum_xyz_mm[i]
            for i in range(3)
        )

    def translated(self, delta_xyz_mm: tuple[float, float, float]) -> "AABB":
        delta = _finite3(delta_xyz_mm, label="translation")
        return AABB(
            tuple(self.minimum_xyz_mm[i] + delta[i] for i in range(3)),
            tuple(self.maximum_xyz_mm[i] + delta[i] for i in range(3)),
        )

    def union(self, other: "AABB") -> "AABB":
        return AABB(
            tuple(min(self.minimum_xyz_mm[i], other.minimum_xyz_mm[i]) for i in range(3)),
            tuple(max(self.maximum_xyz_mm[i], other.maximum_xyz_mm[i]) for i in range(3)),
        )

    def manifest(self) -> dict[str, object]:
        return {"minimum_xyz_mm": list(self.minimum_xyz_mm), "maximum_xyz_mm": list(self.maximum_xyz_mm)}


@dataclass(frozen=True, slots=True)
class LinearSweep:
    """Analytical conservative envelope for a rigid AABB translated along a segment.

    This primitive covers every position for t in [0, 1], not only sampled endpoints.
    It deliberately does not model rotation. Any consumer with changing orientation must
    provide a separately proven conservative rotational envelope rather than treating
    angle-DOE samples as continuous coverage.
    """

    source_id: str
    start_box: AABB
    translation_xyz_mm: tuple[float, float, float]
    source_geometry_sha256: str
    rotation_invariant: bool

    def __post_init__(self) -> None:
        if not self.source_id.strip():
            raise SweepGeometryError("Sweep source identity must be explicit")
        _finite3(self.translation_xyz_mm, label="sweep translation")
        digest = self.source_geometry_sha256.lower()
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise SweepGeometryError("Sweep source geometry identity must be SHA-256")
        if not self.rotation_invariant:
            raise SweepGeometryError(
                "LinearSweep cannot certify changing orientation; provide a proven conservative rotational envelope"
            )

    @property
    def end_box(self) -> AABB:
        return self.start_box.translated(self.translation_xyz_mm)

    @property
    def continuous_envelope(self) -> AABB:
        # For pure translation along a line segment, the coordinate extrema occur at
        # endpoints. Their union therefore contains the rigid body at every t in [0,1].
        return self.start_box.union(self.end_box)

    @property
    def manifest_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def collides_with(self, keepout: AABB, *, clearance_mm: float = 0.0) -> bool:
        return self.continuous_envelope.intersects(keepout, clearance_mm=clearance_mm)

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "source_id": self.source_id,
            "source_geometry_sha256": self.source_geometry_sha256,
            "start_box": self.start_box.manifest(),
            "translation_xyz_mm": list(self.translation_xyz_mm),
            "end_box": self.end_box.manifest(),
            "continuous_envelope": self.continuous_envelope.manifest(),
            "rotation_invariant": self.rotation_invariant,
            "coverage_semantics": "ANALYTICAL_CONTINUOUS_PURE_TRANSLATION_T_IN_CLOSED_INTERVAL_0_1",
            "physical_validation_eligible": False,
        }
        if include_sha:
            payload["manifest_sha256"] = self.manifest_sha256
        return payload


def require_fresh_sweep_source(sweep: LinearSweep, *, expected_geometry_sha256: str) -> None:
    """Reject a validly formatted but stale geometry identity before collision use."""
    expected = expected_geometry_sha256.lower()
    if len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
        raise SweepGeometryError("Expected geometry identity must be SHA-256")
    if sweep.source_geometry_sha256.lower() != expected:
        raise SweepGeometryError("Sweep geometry provenance is stale for the current source geometry")
