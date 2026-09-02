"""Controlled retention-package geometry contract for integrated CAD handoff.

This module intentionally does not invent anthropometric dimensions. It validates released
CAD datums supplied in world coordinates and fails closed when the crown/occipital/yoke
load path is incomplete, asymmetric beyond tolerance, or intrudes into protected/service
keepouts. Outputs are geometry-preflight evidence, not comfort or fit claims.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, sqrt
from typing import Iterable, Mapping, Sequence

Vec3 = tuple[float, float, float]


@dataclass(frozen=True)
class AABB:
    lo: Vec3
    hi: Vec3


@dataclass(frozen=True)
class RetentionDatums:
    left_yoke: Vec3
    right_yoke: Vec3
    left_junction: Vec3
    right_junction: Vec3
    crown_apex: Vec3
    occipital_center: Vec3


@dataclass(frozen=True)
class PackageResult:
    passed: bool
    bilateral_span_mm: float
    junction_span_mm: float
    crown_path_mm: float
    occipital_path_mm: float
    symmetry_error_mm: float
    minimum_keepout_clearance_mm: float
    failures: tuple[str, ...]


def _finite_point(p: Sequence[float]) -> bool:
    return len(p) == 3 and all(isinstance(v, (int, float)) and not isinstance(v, bool) and isfinite(v) for v in p)


def _dist(a: Vec3, b: Vec3) -> float:
    return sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def _point_aabb_signed_clearance(p: Vec3, box: AABB) -> float:
    # Positive outside clearance, negative penetration depth. Zero is contact.
    outside = [max(box.lo[i] - p[i], 0.0, p[i] - box.hi[i]) for i in range(3)]
    if any(v > 0.0 for v in outside):
        return sqrt(sum(v * v for v in outside))
    return -min(min(p[i] - box.lo[i], box.hi[i] - p[i]) for i in range(3))


def _segment_sample_clearance(a: Vec3, b: Vec3, box: AABB, samples: int) -> float:
    # Conservative status label remains sampled preflight, never continuous collision proof.
    return min(
        _point_aabb_signed_clearance(tuple(a[j] + (b[j] - a[j]) * i / samples for j in range(3)), box)
        for i in range(samples + 1)
    )


def evaluate_retention_package(
    datums: RetentionDatums,
    protected_keepouts: Mapping[str, AABB],
    *,
    minimum_member_length_mm: float,
    minimum_keepout_clearance_mm: float,
    bilateral_symmetry_tolerance_mm: float,
    sweep_samples_per_member: int = 64,
) -> PackageResult:
    points = tuple(datums.__dict__.values())
    if not all(_finite_point(p) for p in points):
        raise ValueError("all retention datums must be finite numeric xyz points")
    for name, box in protected_keepouts.items():
        if not _finite_point(box.lo) or not _finite_point(box.hi) or any(box.lo[i] > box.hi[i] for i in range(3)):
            raise ValueError(f"invalid keepout AABB: {name}")
    numeric = (minimum_member_length_mm, minimum_keepout_clearance_mm, bilateral_symmetry_tolerance_mm)
    if any(not isinstance(v, (int, float)) or isinstance(v, bool) or not isfinite(v) or v < 0 for v in numeric):
        raise ValueError("limits must be finite non-negative numbers")
    if not isinstance(sweep_samples_per_member, int) or isinstance(sweep_samples_per_member, bool) or sweep_samples_per_member < 2:
        raise ValueError("sweep_samples_per_member must be an integer >= 2")

    bilateral_span = _dist(datums.left_yoke, datums.right_yoke)
    junction_span = _dist(datums.left_junction, datums.right_junction)
    left_side = _dist(datums.left_yoke, datums.left_junction)
    right_side = _dist(datums.right_yoke, datums.right_junction)
    symmetry_error = abs(left_side - right_side)
    crown_path = _dist(datums.left_junction, datums.crown_apex) + _dist(datums.crown_apex, datums.right_junction)
    occipital_path = _dist(datums.left_junction, datums.occipital_center) + _dist(datums.occipital_center, datums.right_junction)

    members = {
        "left_yoke_link": (datums.left_yoke, datums.left_junction),
        "right_yoke_link": (datums.right_yoke, datums.right_junction),
        "crown_left": (datums.left_junction, datums.crown_apex),
        "crown_right": (datums.crown_apex, datums.right_junction),
        "occipital_left": (datums.left_junction, datums.occipital_center),
        "occipital_right": (datums.occipital_center, datums.right_junction),
    }
    failures: list[str] = []
    for name, (a, b) in members.items():
        if _dist(a, b) < minimum_member_length_mm:
            failures.append(f"{name}:degenerate_load_path")
    if symmetry_error > bilateral_symmetry_tolerance_mm:
        failures.append("bilateral_side_link_asymmetry")

    min_clearance = float("inf")
    for member_name, (a, b) in members.items():
        for keepout_name, box in protected_keepouts.items():
            clearance = _segment_sample_clearance(a, b, box, sweep_samples_per_member)
            min_clearance = min(min_clearance, clearance)
            if clearance < minimum_keepout_clearance_mm:
                failures.append(f"{member_name}:keepout:{keepout_name}")
    if not protected_keepouts:
        min_clearance = float("inf")

    return PackageResult(
        passed=not failures,
        bilateral_span_mm=bilateral_span,
        junction_span_mm=junction_span,
        crown_path_mm=crown_path,
        occipital_path_mm=occipital_path,
        symmetry_error_mm=symmetry_error,
        minimum_keepout_clearance_mm=min_clearance,
        failures=tuple(sorted(set(failures))),
    )
