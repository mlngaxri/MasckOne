from __future__ import annotations

"""Retention quick-release V7: radial-aware transverse release-path verification.

V6 sampled a square Y/Z grid using one scalar limit. That overstates the valid radial
clearance at diagonal grid corners because the spool-rail constraint is radial. V7
screens only poses inside the actual radial-clearance disk while independently enforcing
the anti-rotation Y side-clearance bound. This remains digital B-rep evidence only.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math

from . import retention_quick_release_tactile as v1
from . import retention_quick_release_tactile_v4 as v4
from . import retention_quick_release_tactile_v6 as v6

SCHEMA = "MASCK_ONE_RETENTION_QUICK_RELEASE_TACTILE_V7"
SUPERSEDES_SCHEMA = v6.SCHEMA
OFFSET_FRACTIONS = v6.OFFSET_FRACTIONS
CLEARANCE_FRACTION = 0.8


class RetentionQuickReleaseTactileV7Error(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class RetentionQuickReleaseTactileV7:
    mechanism: v1.RetentionQuickReleaseTactile
    radial_limit_mm: float
    side_limit_mm: float
    transverse_sample_count: int
    release_station_count: int
    total_pose_count: int
    max_rigid_guide_intersection_mm3: float

    def validate(self) -> "RetentionQuickReleaseTactileV7":
        self.mechanism.validate()
        metrics = (self.radial_limit_mm, self.side_limit_mm, self.max_rigid_guide_intersection_mm3)
        if not all(math.isfinite(value) for value in metrics):
            raise RetentionQuickReleaseTactileV7Error("clearance-screen metrics must be finite")
        if not 0.0 < self.radial_limit_mm < self.mechanism.rail_radial_clearance_mm:
            raise RetentionQuickReleaseTactileV7Error("radial limit must remain inside spool-rail radial clearance")
        if not 0.0 < self.side_limit_mm < self.mechanism.anti_rotation_side_clearance_mm:
            raise RetentionQuickReleaseTactileV7Error("side limit must remain inside anti-rotation side clearance")
        expected_samples = len(_normalised_disk_samples())
        if self.transverse_sample_count != expected_samples:
            raise RetentionQuickReleaseTactileV7Error("transverse sample count does not match radial-aware grid")
        if self.release_station_count != v4.SWEEP_STATIONS:
            raise RetentionQuickReleaseTactileV7Error("release station count must match V4")
        if self.total_pose_count != expected_samples * self.release_station_count:
            raise RetentionQuickReleaseTactileV7Error("pose count does not cover radial-aware grid through release travel")
        if self.max_rigid_guide_intersection_mm3 > v1.TOL_MM3:
            raise RetentionQuickReleaseTactileV7Error("quick-release slider collides inside radial-aware clearance envelope")
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
            "transverse_sample_count": self.transverse_sample_count,
            "release_station_count": self.release_station_count,
            "total_pose_count": self.total_pose_count,
            "max_rigid_guide_intersection_mm3": self.max_rigid_guide_intersection_mm3,
            "criterion": "NO_POSITIVE_RIGID_GUIDE_INTERSECTION_INSIDE_RADIAL_AND_SIDE_CLEARANCE_BOUNDS",
            "scope": "DIGITAL_BREP_CLEARANCE_SCREEN_NOT_MANUFACTURING_OR_PHYSICAL_VALIDATION",
        }
        payload["physical_validation_eligible"] = False
        payload["manifest_sha256"] = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        return payload


def _normalised_disk_samples() -> tuple[tuple[float, float], ...]:
    return tuple(
        (y_fraction, z_fraction)
        for y_fraction in OFFSET_FRACTIONS
        for z_fraction in OFFSET_FRACTIONS
        if math.hypot(y_fraction, z_fraction) <= 1.0 + 1e-12
    )


def _radial_clearance_screen(
    mechanism: v1.RetentionQuickReleaseTactile,
    radial_limit_mm: float,
    side_limit_mm: float,
) -> tuple[int, int, int, float]:
    if not math.isfinite(radial_limit_mm) or not 0.0 < radial_limit_mm < mechanism.rail_radial_clearance_mm:
        raise RetentionQuickReleaseTactileV7Error("radial limit must stay inside spool-rail radial clearance")
    if not math.isfinite(side_limit_mm) or not 0.0 < side_limit_mm < mechanism.anti_rotation_side_clearance_mm:
        raise RetentionQuickReleaseTactileV7Error("side limit must stay inside anti-rotation side clearance")

    maximum = 0.0
    poses = 0
    samples = _normalised_disk_samples()
    for y_fraction, z_fraction in samples:
        y = radial_limit_mm * y_fraction
        z = radial_limit_mm * z_fraction
        if abs(y) > side_limit_mm + 1e-12:
            continue
        if math.hypot(y, z) > radial_limit_mm + 1e-12:
            raise RetentionQuickReleaseTactileV7Error("internal radial sample escaped configured clearance disk")
        for index in range(v4.SWEEP_STATIONS):
            x = v1.RELEASE_TRAVEL_MM * index / (v4.SWEEP_STATIONS - 1)
            overlap = v1._intersection(mechanism.slider.translate((x, y, z)), mechanism.guide)
            maximum = max(maximum, overlap)
            poses += 1
            if overlap > v1.TOL_MM3:
                raise RetentionQuickReleaseTactileV7Error(
                    f"rigid-guide collision at x={x:.6f} mm, y={y:.6f} mm, z={z:.6f} mm: {overlap:.9f} mm3"
                )
    accepted_samples = poses // v4.SWEEP_STATIONS
    return accepted_samples, v4.SWEEP_STATIONS, poses, maximum


def build_retention_quick_release_tactile_v7() -> RetentionQuickReleaseTactileV7:
    prior = v6.build_retention_quick_release_tactile_v6()
    mechanism = prior.mechanism
    radial_limit = CLEARANCE_FRACTION * mechanism.rail_radial_clearance_mm
    side_limit = CLEARANCE_FRACTION * mechanism.anti_rotation_side_clearance_mm
    samples, stations, poses, maximum = _radial_clearance_screen(mechanism, radial_limit, side_limit)
    return RetentionQuickReleaseTactileV7(
        mechanism=mechanism,
        radial_limit_mm=radial_limit,
        side_limit_mm=side_limit,
        transverse_sample_count=samples,
        release_station_count=stations,
        total_pose_count=poses,
        max_rigid_guide_intersection_mm3=round(maximum, 12),
    ).validate()
