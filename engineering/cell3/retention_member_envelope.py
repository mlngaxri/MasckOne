"""Tolerance-aware physical envelope preflight for retention members.

Unlike retention_package_contract.py, which checks centerline topology, this module
inflates each structural member by its released physical half-envelope plus positional
and manufacturing tolerance. It then computes continuous segment-to-AABB clearance.
This is an analytic capsule-vs-AABB preflight for straight members, not proof for curved
production surfaces or moving release geometry.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, sqrt
from typing import Mapping

from engineering.cell3.retention_package_contract import AABB, RetentionDatums, Vec3


@dataclass(frozen=True)
class MemberEnvelope:
    half_envelope_mm: float
    positional_tolerance_mm: float
    manufacturing_tolerance_mm: float

    @property
    def conservative_radius_mm(self) -> float:
        return self.half_envelope_mm + self.positional_tolerance_mm + self.manufacturing_tolerance_mm


@dataclass(frozen=True)
class EnvelopeResult:
    passed: bool
    minimum_clearance_mm: float
    failures: tuple[str, ...]


def _finite_nonnegative(value: float) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value) and value >= 0.0


def _point_aabb_distance_sq(p: Vec3, box: AABB) -> float:
    return sum(max(box.lo[i] - p[i], 0.0, p[i] - box.hi[i]) ** 2 for i in range(3))


def _segment_aabb_distance(a: Vec3, b: Vec3, box: AABB) -> float:
    """Continuous Euclidean distance between a segment and an axis-aligned box.

    Squared point-to-box distance along a segment is convex and piecewise quadratic.
    Breakpoints occur when a coordinate crosses a box face. On every interval, the
    active outside coordinates are fixed, so the quadratic minimum is analytic.
    """
    ts = {0.0, 1.0}
    d = tuple(b[i] - a[i] for i in range(3))
    for axis in range(3):
        if d[axis] == 0.0:
            continue
        for face in (box.lo[axis], box.hi[axis]):
            t = (face - a[axis]) / d[axis]
            if 0.0 < t < 1.0:
                ts.add(t)
    ordered = sorted(ts)
    best_sq = min(_point_aabb_distance_sq(tuple(a[i] + d[i] * t for i in range(3)), box) for t in ordered)
    for lo, hi in zip(ordered, ordered[1:]):
        mid = (lo + hi) * 0.5
        active: list[tuple[float, float]] = []
        for axis in range(3):
            x = a[axis] + d[axis] * mid
            if x < box.lo[axis]:
                active.append((a[axis] - box.lo[axis], d[axis]))
            elif x > box.hi[axis]:
                active.append((a[axis] - box.hi[axis], d[axis]))
        if not active:
            return 0.0
        aa = sum(slope * slope for _, slope in active)
        ab = sum(offset * slope for offset, slope in active)
        candidate = lo if aa == 0.0 else max(lo, min(hi, -ab / aa))
        p = tuple(a[i] + d[i] * candidate for i in range(3))
        best_sq = min(best_sq, _point_aabb_distance_sq(p, box))
    return sqrt(best_sq)


def evaluate_member_envelopes(
    datums: RetentionDatums,
    member_envelopes: Mapping[str, MemberEnvelope],
    protected_keepouts: Mapping[str, AABB],
    *,
    minimum_residual_clearance_mm: float,
) -> EnvelopeResult:
    if not _finite_nonnegative(minimum_residual_clearance_mm):
        raise ValueError("minimum_residual_clearance_mm must be finite and non-negative")
    members = {
        "left_yoke_link": (datums.left_yoke, datums.left_junction),
        "right_yoke_link": (datums.right_yoke, datums.right_junction),
        "crown_left": (datums.left_junction, datums.crown_apex),
        "crown_right": (datums.crown_apex, datums.right_junction),
        "occipital_left": (datums.left_junction, datums.occipital_center),
        "occipital_right": (datums.occipital_center, datums.right_junction),
    }
    missing = sorted(set(members) - set(member_envelopes))
    extra = sorted(set(member_envelopes) - set(members))
    if missing or extra:
        raise ValueError(f"member envelope mapping mismatch; missing={missing}, extra={extra}")
    for name, env in member_envelopes.items():
        if not all(_finite_nonnegative(v) for v in (env.half_envelope_mm, env.positional_tolerance_mm, env.manufacturing_tolerance_mm)):
            raise ValueError(f"invalid envelope for {name}")
    for name, box in protected_keepouts.items():
        if any(not _finite_nonnegative(box.hi[i] - box.lo[i]) for i in range(3)):
            raise ValueError(f"invalid keepout AABB: {name}")

    failures: list[str] = []
    minimum = float("inf")
    for member_name, (a, b) in members.items():
        radius = member_envelopes[member_name].conservative_radius_mm
        for keepout_name, box in protected_keepouts.items():
            residual = _segment_aabb_distance(a, b, box) - radius
            minimum = min(minimum, residual)
            if residual < minimum_residual_clearance_mm:
                failures.append(f"{member_name}:envelope_keepout:{keepout_name}")
    return EnvelopeResult(not failures, minimum, tuple(sorted(set(failures))))
