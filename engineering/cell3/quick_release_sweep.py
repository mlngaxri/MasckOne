"""Tolerance-aware continuous preflight for released quick-release trajectories.

A moving release component is represented by a straight physical member whose two end
datums move linearly between released mechanism states. Against static AABB keepouts,
clearance is bounded continuously with adaptive subdivision and a Lipschitz motion bound.
This is intentionally scoped to linear datum trajectories and straight member envelopes;
curved/nonlinear production geometry still requires CAD-native continuous collision proof.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, sqrt
from typing import Mapping

from engineering.cell3.retention_member_envelope import _segment_aabb_distance
from engineering.cell3.retention_package_contract import AABB, Vec3


@dataclass(frozen=True)
class MovingMember:
    start_a: Vec3
    start_b: Vec3
    end_a: Vec3
    end_b: Vec3
    half_envelope_mm: float
    positional_tolerance_mm: float = 0.0
    manufacturing_tolerance_mm: float = 0.0

    @property
    def conservative_radius_mm(self) -> float:
        return self.half_envelope_mm + self.positional_tolerance_mm + self.manufacturing_tolerance_mm


@dataclass(frozen=True)
class ReleaseSweepResult:
    passed: bool
    minimum_clearance_mm: float
    evaluated_states: int
    failures: tuple[str, ...]


def _point(label: str, p: Vec3) -> None:
    if not isinstance(p, tuple) or len(p) != 3 or any(
        not isinstance(v, (int, float)) or isinstance(v, bool) or not isfinite(v) for v in p
    ):
        raise ValueError(f"{label} must be a finite numeric 3-vector")


def _lerp(a: Vec3, b: Vec3, t: float) -> Vec3:
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))  # type: ignore[return-value]


def _dist(a: Vec3, b: Vec3) -> float:
    return sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def evaluate_release_sweep(
    moving_members: Mapping[str, MovingMember],
    protected_keepouts: Mapping[str, AABB],
    *,
    minimum_residual_clearance_mm: float,
    proof_tolerance_mm: float = 0.01,
    max_depth: int = 24,
) -> ReleaseSweepResult:
    for label, value in (("minimum_residual_clearance_mm", minimum_residual_clearance_mm), ("proof_tolerance_mm", proof_tolerance_mm)):
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not isfinite(value) or value < 0:
            raise ValueError(f"{label} must be finite and non-negative")
    if proof_tolerance_mm == 0:
        raise ValueError("proof_tolerance_mm must be positive")
    if not isinstance(max_depth, int) or isinstance(max_depth, bool) or max_depth < 1:
        raise ValueError("max_depth must be a positive integer")
    if not moving_members:
        raise ValueError("at least one moving member is required")

    for name, member in moving_members.items():
        for label, point in (("start_a", member.start_a), ("start_b", member.start_b), ("end_a", member.end_a), ("end_b", member.end_b)):
            _point(f"{name}.{label}", point)
        values = (member.half_envelope_mm, member.positional_tolerance_mm, member.manufacturing_tolerance_mm)
        if any(not isinstance(v, (int, float)) or isinstance(v, bool) or not isfinite(v) or v < 0 for v in values):
            raise ValueError(f"invalid envelope for {name}")
    for name, box in protected_keepouts.items():
        _point(f"{name}.lo", box.lo)
        _point(f"{name}.hi", box.hi)
        if any(box.lo[i] > box.hi[i] for i in range(3)):
            raise ValueError(f"invalid keepout AABB: {name}")

    failures: list[str] = []
    minimum = float("inf")
    evaluated: set[tuple[str, str, float]] = set()

    for member_name, member in moving_members.items():
        speed_bound = max(_dist(member.start_a, member.end_a), _dist(member.start_b, member.end_b))
        for keepout_name, box in protected_keepouts.items():
            def clearance(t: float) -> float:
                nonlocal minimum
                a = _lerp(member.start_a, member.end_a, t)
                b = _lerp(member.start_b, member.end_b, t)
                if a == b:
                    failures.append(f"{member_name}:degenerate_at:{t:.9f}")
                    return float("-inf")
                value = _segment_aabb_distance(a, b, box) - member.conservative_radius_mm
                minimum = min(minimum, value)
                evaluated.add((member_name, keepout_name, t))
                return value

            def recurse(lo: float, hi: float, c_lo: float, c_hi: float, depth: int) -> None:
                if c_lo < minimum_residual_clearance_mm or c_hi < minimum_residual_clearance_mm:
                    failures.append(f"{member_name}:release_keepout:{keepout_name}")
                    return
                motion = speed_bound * (hi - lo)
                if min(c_lo, c_hi) - motion >= minimum_residual_clearance_mm:
                    return
                if motion <= proof_tolerance_mm:
                    mid = (lo + hi) * 0.5
                    if clearance(mid) < minimum_residual_clearance_mm:
                        failures.append(f"{member_name}:release_keepout:{keepout_name}")
                    return
                if depth >= max_depth:
                    failures.append(f"{member_name}:unproven_continuous_clearance:{keepout_name}")
                    return
                mid = (lo + hi) * 0.5
                c_mid = clearance(mid)
                recurse(lo, mid, c_lo, c_mid, depth + 1)
                recurse(mid, hi, c_mid, c_hi, depth + 1)

            c0, c1 = clearance(0.0), clearance(1.0)
            recurse(0.0, 1.0, c0, c1, 0)

    return ReleaseSweepResult(not failures, minimum, len(evaluated), tuple(sorted(set(failures))))
