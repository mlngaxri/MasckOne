from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from numbers import Real
from typing import Sequence


class SweepGeometryError(ValueError):
    """Raised when a continuous-sweep contract would become non-conservative."""


def _finite_real(value: object, *, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise SweepGeometryError(f"{label} must be a real finite number, not a boolean or coercible alias")
    out = float(value)
    if not math.isfinite(out):
        raise SweepGeometryError(f"{label} must be finite")
    return out


def _finite3(values: object, *, label: str) -> tuple[float, float, float]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise SweepGeometryError(f"{label} must contain exactly three coordinates")
    if len(values) != 3:
        raise SweepGeometryError(f"{label} must contain exactly three coordinates")
    return tuple(_finite_real(values[i], label=f"{label}[{i}]") for i in range(3))  # type: ignore[return-value]


def _canonical_sha256(value: str, *, label: str) -> str:
    if not isinstance(value, str):
        raise SweepGeometryError(f"{label} must be a lowercase canonical SHA-256 digest")
    if value != value.strip():
        raise SweepGeometryError(f"{label} must be a lowercase canonical SHA-256 digest without surrounding whitespace")
    if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise SweepGeometryError(f"{label} must be a lowercase canonical SHA-256 digest")
    return value


def _identity(value: str, *, label: str) -> str:
    if not isinstance(value, str):
        raise SweepGeometryError(f"{label} must be an explicit nonblank canonical string")
    if not value or value != value.strip():
        raise SweepGeometryError(f"{label} must be an explicit nonblank canonical string without surrounding whitespace")
    return value


def _frame_id(value: str) -> str:
    return _identity(value, label="AABB coordinate frame identity")


@dataclass(frozen=True, slots=True)
class AABB:
    minimum_xyz_mm: tuple[float, float, float]
    maximum_xyz_mm: tuple[float, float, float]
    frame_id: str

    def __post_init__(self) -> None:
        lo = _finite3(self.minimum_xyz_mm, label="AABB minimum")
        hi = _finite3(self.maximum_xyz_mm, label="AABB maximum")
        if any(a > b for a, b in zip(lo, hi)):
            raise SweepGeometryError("AABB minimum cannot exceed maximum")
        object.__setattr__(self, "minimum_xyz_mm", lo)
        object.__setattr__(self, "maximum_xyz_mm", hi)
        object.__setattr__(self, "frame_id", _frame_id(self.frame_id))

    def _require_same_frame(self, other: "AABB") -> None:
        if not isinstance(other, AABB):
            raise SweepGeometryError("Collision geometry must be an AABB with explicit coordinate identity")
        if self.frame_id != other.frame_id:
            raise SweepGeometryError(f"AABB coordinate-frame mismatch: {self.frame_id!r} != {other.frame_id!r}")

    def intersects(self, other: "AABB", *, clearance_mm: float = 0.0) -> bool:
        self._require_same_frame(other)
        clearance = _finite_real(clearance_mm, label="Collision clearance")
        if clearance < 0.0:
            raise SweepGeometryError("Collision clearance must be non-negative")
        return all(self.minimum_xyz_mm[i] - clearance <= other.maximum_xyz_mm[i] and other.minimum_xyz_mm[i] - clearance <= self.maximum_xyz_mm[i] for i in range(3))

    def translated(self, delta_xyz_mm: tuple[float, float, float]) -> "AABB":
        delta = _finite3(delta_xyz_mm, label="translation")
        return AABB(tuple(self.minimum_xyz_mm[i] + delta[i] for i in range(3)), tuple(self.maximum_xyz_mm[i] + delta[i] for i in range(3)), self.frame_id)

    def union(self, other: "AABB") -> "AABB":
        self._require_same_frame(other)
        return AABB(tuple(min(self.minimum_xyz_mm[i], other.minimum_xyz_mm[i]) for i in range(3)), tuple(max(self.maximum_xyz_mm[i], other.maximum_xyz_mm[i]) for i in range(3)), self.frame_id)

    def manifest(self) -> dict[str, object]:
        return {"minimum_xyz_mm": list(self.minimum_xyz_mm), "maximum_xyz_mm": list(self.maximum_xyz_mm), "frame_id": self.frame_id}


@dataclass(frozen=True, slots=True)
class LinearSweep:
    source_id: str
    start_box: AABB
    translation_xyz_mm: tuple[float, float, float]
    source_geometry_sha256: str
    rotation_invariant: bool

    def __post_init__(self) -> None:
        if not isinstance(self.start_box, AABB):
            raise SweepGeometryError("LinearSweep start_box must be an AABB with explicit coordinate identity")
        object.__setattr__(self, "source_id", _identity(self.source_id, label="Sweep source identity"))
        object.__setattr__(self, "translation_xyz_mm", _finite3(self.translation_xyz_mm, label="sweep translation"))
        object.__setattr__(self, "source_geometry_sha256", _canonical_sha256(self.source_geometry_sha256, label="Sweep source geometry identity"))
        if type(self.rotation_invariant) is not bool:
            raise SweepGeometryError("LinearSweep rotation_invariant must be an explicit boolean")
        if not self.rotation_invariant:
            raise SweepGeometryError("LinearSweep cannot certify changing orientation; provide a proven conservative rotational envelope")

    @property
    def end_box(self) -> AABB:
        return self.start_box.translated(self.translation_xyz_mm)

    @property
    def continuous_envelope(self) -> AABB:
        return self.start_box.union(self.end_box)

    @property
    def manifest_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def collides_with(self, keepout: AABB, *, expected_geometry_sha256: str, clearance_mm: float = 0.0) -> bool:
        require_fresh_sweep_source(self, expected_geometry_sha256=expected_geometry_sha256)
        return self.continuous_envelope.intersects(keepout, clearance_mm=clearance_mm)

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {"source_id": self.source_id, "source_geometry_sha256": self.source_geometry_sha256, "coordinate_frame_id": self.start_box.frame_id, "start_box": self.start_box.manifest(), "translation_xyz_mm": list(self.translation_xyz_mm), "end_box": self.end_box.manifest(), "continuous_envelope": self.continuous_envelope.manifest(), "rotation_invariant": self.rotation_invariant, "coverage_semantics": "ANALYTICAL_CONTINUOUS_PURE_TRANSLATION_T_IN_CLOSED_INTERVAL_0_1", "physical_validation_eligible": False}
        if include_sha:
            payload["manifest_sha256"] = self.manifest_sha256
        return payload


def require_fresh_sweep_source(sweep: LinearSweep, *, expected_geometry_sha256: str) -> None:
    if not isinstance(sweep, LinearSweep):
        raise SweepGeometryError("Sweep freshness requires a LinearSweep instance")
    expected = _canonical_sha256(expected_geometry_sha256, label="Expected geometry identity")
    if sweep.source_geometry_sha256 != expected:
        raise SweepGeometryError("Sweep geometry provenance is stale for the current source geometry")
