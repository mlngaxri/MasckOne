from __future__ import annotations

"""Retention quick-release V8: boundary-aware transverse clearance verification.

V7 corrected the transverse domain to a radial disk but still sampled that domain with
only the inherited five-point Cartesian fractions. V8 adds deterministic polar rings
and explicit intersections between the radial and anti-rotation side bounds, so the
release sweep exercises the constrained clearance boundary instead of only a sparse
interior grid. This remains digital B-rep evidence only.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math

from . import retention_quick_release_tactile as v1
from . import retention_quick_release_tactile_v4 as v4
from . import retention_quick_release_tactile_v7 as v7

SCHEMA = "MASCK_ONE_RETENTION_QUICK_RELEASE_TACTILE_V8"
SUPERSEDES_SCHEMA = v7.SCHEMA
CLEARANCE_FRACTION = v7.CLEARANCE_FRACTION
POLAR_RADII = (0.0, 0.25, 0.5, 0.75, 1.0)
POLAR_ANGLES = 16


class RetentionQuickReleaseTactileV8Error(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class RetentionQuickReleaseTactileV8:
    mechanism: v1.RetentionQuickReleaseTactile
    radial_limit_mm: float
    side_limit_mm: float
    transverse_sample_count: int
    boundary_sample_count: int
    release_station_count: int
    total_pose_count: int
    max_rigid_guide_intersection_mm3: float

    def validate(self) -> "RetentionQuickReleaseTactileV8":
        self.mechanism.validate()
        metrics = (self.radial_limit_mm, self.side_limit_mm, self.max_rigid_guide_intersection_mm3)
        if not all(math.isfinite(value) for value in metrics):
            raise RetentionQuickReleaseTactileV8Error("clearance-screen metrics must be finite")
        if not 0.0 < self.radial_limit_mm < self.mechanism.rail_radial_clearance_mm:
            raise RetentionQuickReleaseTactileV8Error("radial limit must remain inside spool-rail radial clearance")
        if not 0.0 < self.side_limit_mm < self.mechanism.anti_rotation_side_clearance_mm:
            raise RetentionQuickReleaseTactileV8Error("side limit must remain inside anti-rotation side clearance")
        samples = _constrained_transverse_samples(self.radial_limit_mm, self.side_limit_mm)
        if self.transverse_sample_count != len(samples):
            raise RetentionQuickReleaseTactileV8Error("transverse sample count does not match constrained sample set")
        expected_boundary = sum(_is_boundary_sample(y, z, self.radial_limit_mm, self.side_limit_mm) for y, z in samples)
        if self.boundary_sample_count != expected_boundary or expected_boundary < 4:
            raise RetentionQuickReleaseTactileV8Error("constrained boundary is not explicitly covered")
        if self.release_station_count != v4.SWEEP_STATIONS:
            raise RetentionQuickReleaseTactileV8Error("release station count must match V4")
        if self.total_pose_count != self.transverse_sample_count * self.release_station_count:
            raise RetentionQuickReleaseTactileV8Error("pose count does not cover constrained samples through release travel")
        if self.max_rigid_guide_intersection_mm3 > v1.TOL_MM3:
            raise RetentionQuickReleaseTactileV8Error("quick-release slider collides inside constrained clearance envelope")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        payload = self.mechanism.manifest()
        payload.pop("manifest_sha256", None)
        payload["schema"] = SCHEMA
        payload["supersedes_schema"] = SUPERSEDES_SCHEMA
        payload["transverse_clearance_release_path"] = {
            "radial_limit_mm": self.radial_limit_mm,
            "anti_rotation_side_limit_mm": self.side_limit_mm,
            "clearance_fraction": CLEARANCE_FRACTION,
            "polar_radii": list(POLAR_RADII),
            "polar_angles": POLAR_ANGLES,
            "transverse_sample_count": self.transverse_sample_count,
            "boundary_sample_count": self.boundary_sample_count,
            "release_station_count": self.release_station_count,
            "total_pose_count": self.total_pose_count,
            "max_rigid_guide_intersection_mm3": self.max_rigid_guide_intersection_mm3,
            "criterion": "NO_POSITIVE_RIGID_GUIDE_INTERSECTION_AT_CONSTRAINED_BOUNDARY_AND_INTERIOR_SAMPLES",
            "scope": "DIGITAL_BREP_CLEARANCE_SCREEN_NOT_CONTINUOUS_PROOF_MANUFACTURING_OR_PHYSICAL_VALIDATION",
        }
        payload["physical_validation_eligible"] = False
        payload["manifest_sha256"] = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        return payload


def _dedupe(points: list[tuple[float, float]]) -> tuple[tuple[float, float], ...]:
    unique: dict[tuple[int, int], tuple[float, float]] = {}
    for y, z in points:
        unique[(round(y * 1e9), round(z * 1e9))] = (y, z)
    return tuple(unique[key] for key in sorted(unique))


def _constrained_transverse_samples(radial_limit_mm: float, side_limit_mm: float) -> tuple[tuple[float, float], ...]:
    if not all(math.isfinite(value) and value > 0.0 for value in (radial_limit_mm, side_limit_mm)):
        raise RetentionQuickReleaseTactileV8Error("sample limits must be finite and positive")
    points: list[tuple[float, float]] = []
    for radius_fraction in POLAR_RADII:
        radius = radial_limit_mm * radius_fraction
        if radius_fraction == 0.0:
            points.append((0.0, 0.0))
            continue
        for index in range(POLAR_ANGLES):
            theta = 2.0 * math.pi * index / POLAR_ANGLES
            y, z = radius * math.cos(theta), radius * math.sin(theta)
            if abs(y) <= side_limit_mm + 1e-12:
                points.append((y, z))
    # Explicitly sample the anti-rotation side boundary and its intersections with
    # the radial boundary. These are easy for a polar-only grid to miss.
    clipped_side = min(side_limit_mm, radial_limit_mm)
    points.extend(((clipped_side, 0.0), (-clipped_side, 0.0)))
    if side_limit_mm < radial_limit_mm:
        z_intersection = math.sqrt(max(0.0, radial_limit_mm**2 - side_limit_mm**2))
        points.extend(
            (
                (side_limit_mm, z_intersection),
                (side_limit_mm, -z_intersection),
                (-side_limit_mm, z_intersection),
                (-side_limit_mm, -z_intersection),
            )
        )
    samples = _dedupe(points)
    if not all(math.hypot(y, z) <= radial_limit_mm + 1e-12 and abs(y) <= side_limit_mm + 1e-12 for y, z in samples):
        raise RetentionQuickReleaseTactileV8Error("generated sample escaped constrained clearance domain")
    return samples


def _is_boundary_sample(y: float, z: float, radial_limit_mm: float, side_limit_mm: float) -> bool:
    radial_boundary = math.isclose(math.hypot(y, z), radial_limit_mm, rel_tol=0.0, abs_tol=1e-9)
    side_boundary = math.isclose(abs(y), min(side_limit_mm, radial_limit_mm), rel_tol=0.0, abs_tol=1e-9)
    return radial_boundary or side_boundary


def _boundary_aware_clearance_screen(
    mechanism: v1.RetentionQuickReleaseTactile,
    radial_limit_mm: float,
    side_limit_mm: float,
) -> tuple[int, int, int, int, float]:
    if not math.isfinite(radial_limit_mm) or not 0.0 < radial_limit_mm < mechanism.rail_radial_clearance_mm:
        raise RetentionQuickReleaseTactileV8Error("radial limit must stay inside spool-rail radial clearance")
    if not math.isfinite(side_limit_mm) or not 0.0 < side_limit_mm < mechanism.anti_rotation_side_clearance_mm:
        raise RetentionQuickReleaseTactileV8Error("side limit must stay inside anti-rotation side clearance")
    samples = _constrained_transverse_samples(radial_limit_mm, side_limit_mm)
    boundary_samples = sum(_is_boundary_sample(y, z, radial_limit_mm, side_limit_mm) for y, z in samples)
    maximum = 0.0
    poses = 0
    for y, z in samples:
        for index in range(v4.SWEEP_STATIONS):
            x = v1.RELEASE_TRAVEL_MM * index / (v4.SWEEP_STATIONS - 1)
            overlap = v1._intersection(mechanism.slider.translate((x, y, z)), mechanism.guide)
            maximum = max(maximum, overlap)
            poses += 1
            if overlap > v1.TOL_MM3:
                raise RetentionQuickReleaseTactileV8Error(
                    f"rigid-guide collision at x={x:.6f} mm, y={y:.6f} mm, z={z:.6f} mm: {overlap:.9f} mm3"
                )
    return len(samples), boundary_samples, v4.SWEEP_STATIONS, poses, maximum


def build_retention_quick_release_tactile_v8() -> RetentionQuickReleaseTactileV8:
    prior = v7.build_retention_quick_release_tactile_v7()
    mechanism = prior.mechanism
    radial_limit = CLEARANCE_FRACTION * mechanism.rail_radial_clearance_mm
    side_limit = CLEARANCE_FRACTION * mechanism.anti_rotation_side_clearance_mm
    samples, boundary, stations, poses, maximum = _boundary_aware_clearance_screen(mechanism, radial_limit, side_limit)
    return RetentionQuickReleaseTactileV8(
        mechanism=mechanism,
        radial_limit_mm=radial_limit,
        side_limit_mm=side_limit,
        transverse_sample_count=samples,
        boundary_sample_count=boundary,
        release_station_count=stations,
        total_pose_count=poses,
        max_rigid_guide_intersection_mm3=round(maximum, 12),
    ).validate()
