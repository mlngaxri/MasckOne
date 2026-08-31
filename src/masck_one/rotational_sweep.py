from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from numbers import Real
import re

from .sweep_geometry import AABB, SweepGeometryError


class RotationalSweepError(ValueError):
    """Raised when a rotational sweep cannot be proven conservative."""


_SOURCE_ID_RE = re.compile(r"^[A-Z0-9][A-Z0-9._-]*$", re.ASCII)


def _finite_real(value: object, *, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise RotationalSweepError(f"{label} must be a finite real number")
    out = float(value)
    if not math.isfinite(out):
        raise RotationalSweepError(f"{label} must be finite")
    return 0.0 if out == 0.0 else out


def _finite3(value: object, *, label: str) -> tuple[float, float, float]:
    if not isinstance(value, (tuple, list)) or len(value) != 3:
        raise RotationalSweepError(f"{label} must contain exactly three coordinates")
    return tuple(_finite_real(v, label=f"{label}[{i}]") for i, v in enumerate(value))  # type: ignore[return-value]


def _canonical_sha256(value: object, *, label: str) -> str:
    if not isinstance(value, str) or value != value.strip() or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise RotationalSweepError(f"{label} must be an exact lowercase canonical SHA-256 digest")
    return value


def _canonical_frame_id(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise RotationalSweepError(f"{label} must be an exact nonblank coordinate-frame identity")
    return value


def _canonical_source_id(value: object) -> str:
    if not isinstance(value, str) or _SOURCE_ID_RE.fullmatch(value) is None:
        raise RotationalSweepError("source_id must use canonical ASCII uppercase identifier syntax")
    return value


def _canonical_aabb(box: AABB) -> AABB:
    return AABB(
        tuple(0.0 if v == 0.0 else v for v in box.minimum_xyz_mm),
        tuple(0.0 if v == 0.0 else v for v in box.maximum_xyz_mm),
        box.frame_id,
    )


def _outward_lower(center: float, radius: float) -> float:
    value = center - radius
    if not math.isfinite(value):
        raise RotationalSweepError("conservative rotational envelope is not finitely representable")
    return math.nextafter(value, -math.inf)


def _outward_upper(center: float, radius: float) -> float:
    value = center + radius
    if not math.isfinite(value):
        raise RotationalSweepError("conservative rotational envelope is not finitely representable")
    return math.nextafter(value, math.inf)


@dataclass(frozen=True, slots=True)
class ConservativeRotationalSweep:
    """Orientation-independent sphere bound for a rigid AABB rotating about a fixed pivot."""

    source_id: str
    source_box: AABB
    pivot_xyz_mm: tuple[float, float, float]
    pivot_frame_id: str
    angle_min_deg: float
    angle_max_deg: float
    source_geometry_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_id", _canonical_source_id(self.source_id))
        if not isinstance(self.source_box, AABB):
            raise RotationalSweepError("source_box must be an AABB with explicit frame identity")
        object.__setattr__(self, "source_box", _canonical_aabb(self.source_box))
        object.__setattr__(self, "pivot_xyz_mm", _finite3(self.pivot_xyz_mm, label="pivot"))
        pivot_frame = _canonical_frame_id(self.pivot_frame_id, label="pivot frame")
        if pivot_frame != self.source_box.frame_id:
            raise RotationalSweepError("pivot/source coordinate-frame mismatch")
        object.__setattr__(self, "pivot_frame_id", pivot_frame)
        amin = _finite_real(self.angle_min_deg, label="minimum angle")
        amax = _finite_real(self.angle_max_deg, label="maximum angle")
        if amin > amax:
            raise RotationalSweepError("minimum angle cannot exceed maximum angle")
        object.__setattr__(self, "angle_min_deg", amin)
        object.__setattr__(self, "angle_max_deg", amax)
        object.__setattr__(self, "source_geometry_sha256", _canonical_sha256(self.source_geometry_sha256, label="source geometry identity"))

    @property
    def maximum_radius_mm(self) -> float:
        p = self.pivot_xyz_mm
        corners = (
            (x, y, z)
            for x in (self.source_box.minimum_xyz_mm[0], self.source_box.maximum_xyz_mm[0])
            for y in (self.source_box.minimum_xyz_mm[1], self.source_box.maximum_xyz_mm[1])
            for z in (self.source_box.minimum_xyz_mm[2], self.source_box.maximum_xyz_mm[2])
        )
        radius = max(math.dist(p, corner) for corner in corners)
        if not math.isfinite(radius):
            raise RotationalSweepError("maximum rotational radius is not finitely representable")
        return math.nextafter(radius, math.inf)

    @property
    def conservative_envelope(self) -> AABB:
        r = self.maximum_radius_mm
        p = self.pivot_xyz_mm
        return AABB(
            tuple(_outward_lower(c, r) for c in p),
            tuple(_outward_upper(c, r) for c in p),
            self.pivot_frame_id,
        )

    def collides(self, keepout: AABB, *, clearance_mm: float = 0.0, current_source_geometry_sha256: str) -> bool:
        current = _canonical_sha256(current_source_geometry_sha256, label="current source geometry identity")
        if current != self.source_geometry_sha256:
            raise RotationalSweepError("rotational sweep is stale for the current source geometry")
        try:
            return self.conservative_envelope.intersects(keepout, clearance_mm=clearance_mm)
        except SweepGeometryError as exc:
            raise RotationalSweepError(f"rotational collision evaluation rejected: {exc}") from exc

    @property
    def sweep_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "source_id": self.source_id,
            "source_box": self.source_box.manifest(),
            "pivot_xyz_mm": list(self.pivot_xyz_mm),
            "pivot_frame_id": self.pivot_frame_id,
            "angle_interval_deg": [self.angle_min_deg, self.angle_max_deg],
            "coverage_semantic": "CONSERVATIVE_ARBITRARY_ORIENTATION_SPHERE_BOUND_OUTWARD_ROUNDED",
            "source_geometry_sha256": self.source_geometry_sha256,
            "maximum_radius_mm": self.maximum_radius_mm,
            "conservative_envelope": self.conservative_envelope.manifest(),
            "physical_validation_eligible": False,
        }
        if include_sha:
            payload["sweep_sha256"] = self.sweep_sha256
        return payload
