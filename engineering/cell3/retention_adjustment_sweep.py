"""Continuous straight-member preflight across a released retention adjustment interval.

This closes the gap between endpoint-only retention package checks and moving adjustment
geometry. Each retention datum moves linearly from a released minimum-fit state to a
released maximum-fit state. For straight structural members against AABB keepouts, the
member surface is conservatively bounded by its released envelope radius and the motion
interval is adaptively subdivided until a geometric Lipschitz bound proves clearance or
an evaluated state fails. This is not proof for curved members or non-linear adjusters.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, sqrt
from typing import Mapping

from engineering.cell3.retention_member_envelope import MemberEnvelope, _segment_aabb_distance
from engineering.cell3.retention_package_contract import AABB, RetentionDatums, Vec3


@dataclass(frozen=True)
class AdjustmentSweepResult:
    passed: bool
    minimum_clearance_mm: float
    evaluated_states: int
    failures: tuple[str, ...]


def _point_lerp(a: Vec3, b: Vec3, t: float) -> Vec3:
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))  # type: ignore[return-value]


def _point_dist(a: Vec3, b: Vec3) -> float:
    return sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def _datums_at(a: RetentionDatums, b: RetentionDatums, t: float) -> RetentionDatums:
    return RetentionDatums(**{name: _point_lerp(getattr(a, name), getattr(b, name), t) for name in a.__dict__})


def _members(d: RetentionDatums) -> dict[str, tuple[Vec3, Vec3]]:
    return {
        "left_yoke_link": (d.left_yoke, d.left_junction),
        "right_yoke_link": (d.right_yoke, d.right_junction),
        "crown_left": (d.left_junction, d.crown_apex),
        "crown_right": (d.crown_apex, d.right_junction),
        "occipital_left": (d.left_junction, d.occipital_center),
        "occipital_right": (d.occipital_center, d.right_junction),
    }


def evaluate_adjustment_sweep(
    minimum_fit: RetentionDatums,
    maximum_fit: RetentionDatums,
    member_envelopes: Mapping[str, MemberEnvelope],
    protected_keepouts: Mapping[str, AABB],
    *,
    minimum_residual_clearance_mm: float,
    proof_tolerance_mm: float = 0.01,
    max_depth: int = 24,
) -> AdjustmentSweepResult:
    if any(not isinstance(v, (int, float)) or isinstance(v, bool) or not isfinite(v) or v < 0 for v in (minimum_residual_clearance_mm, proof_tolerance_mm)):
        raise ValueError("clearance and proof tolerance must be finite non-negative numbers")
    if proof_tolerance_mm == 0:
        raise ValueError("proof_tolerance_mm must be positive")
    if not isinstance(max_depth, int) or isinstance(max_depth, bool) or max_depth < 1:
        raise ValueError("max_depth must be a positive integer")

    start_members = _members(minimum_fit)
    end_members = _members(maximum_fit)
    if set(member_envelopes) != set(start_members):
        raise ValueError("member envelope mapping must exactly cover all retention members")
    for name, env in member_envelopes.items():
        values = (env.half_envelope_mm, env.positional_tolerance_mm, env.manufacturing_tolerance_mm)
        if any(not isinstance(v, (int, float)) or isinstance(v, bool) or not isfinite(v) or v < 0 for v in values):
            raise ValueError(f"invalid envelope for {name}")
    for name, box in protected_keepouts.items():
        if any(not isinstance(v, (int, float)) or isinstance(v, bool) or not isfinite(v) for p in (box.lo, box.hi) for v in p) or any(box.lo[i] > box.hi[i] for i in range(3)):
            raise ValueError(f"invalid keepout AABB: {name}")

    failures: list[str] = []
    minimum = float("inf")
    evaluated: set[float] = set()

    def clearance(member_name: str, keepout_name: str, t: float) -> float:
        nonlocal minimum
        d = _datums_at(minimum_fit, maximum_fit, t)
        a, b = _members(d)[member_name]
        if a == b:
            failures.append(f"{member_name}:degenerate_at:{t:.9f}")
            return float("-inf")
        radius = member_envelopes[member_name].conservative_radius_mm
        value = _segment_aabb_distance(a, b, protected_keepouts[keepout_name]) - radius
        minimum = min(minimum, value)
        evaluated.add(t)
        return value

    for member_name in start_members:
        a0, b0 = start_members[member_name]
        a1, b1 = end_members[member_name]
        speed_bound = max(_point_dist(a0, a1), _point_dist(b0, b1))
        for keepout_name in protected_keepouts:
            def recurse(lo: float, hi: float, c_lo: float, c_hi: float, depth: int) -> None:
                if c_lo < minimum_residual_clearance_mm or c_hi < minimum_residual_clearance_mm:
                    failures.append(f"{member_name}:adjustment_keepout:{keepout_name}")
                    return
                interval_motion = speed_bound * (hi - lo)
                if min(c_lo, c_hi) - interval_motion >= minimum_residual_clearance_mm:
                    return
                if interval_motion <= proof_tolerance_mm:
                    mid = (lo + hi) * 0.5
                    c_mid = clearance(member_name, keepout_name, mid)
                    if c_mid < minimum_residual_clearance_mm:
                        failures.append(f"{member_name}:adjustment_keepout:{keepout_name}")
                    return
                if depth >= max_depth:
                    failures.append(f"{member_name}:unproven_continuous_clearance:{keepout_name}")
                    return
                mid = (lo + hi) * 0.5
                c_mid = clearance(member_name, keepout_name, mid)
                recurse(lo, mid, c_lo, c_mid, depth + 1)
                recurse(mid, hi, c_mid, c_hi, depth + 1)

            c0 = clearance(member_name, keepout_name, 0.0)
            c1 = clearance(member_name, keepout_name, 1.0)
            recurse(0.0, 1.0, c0, c1, 0)

    if not protected_keepouts:
        minimum = float("inf")
    return AdjustmentSweepResult(not failures, minimum, len(evaluated), tuple(sorted(set(failures))))
