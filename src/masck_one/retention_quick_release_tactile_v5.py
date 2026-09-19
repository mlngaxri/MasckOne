from __future__ import annotations

"""Retention quick-release V5: lateral-clearance release-path verification.

V4 screens the nominal slider through the complete release travel. V5 keeps that
mechanism unchanged and repeats the same B-rep collision screen at bounded lateral
assembly offsets inside the smaller nominal guide clearance. This detects a release
path that is collision-free only when perfectly centred. It is digital geometry
evidence only, not a manufactured tolerance, force, wear or contamination claim.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math

from . import retention_quick_release_tactile as v1
from . import retention_quick_release_tactile_v4 as v4

SCHEMA = "MASCK_ONE_RETENTION_QUICK_RELEASE_TACTILE_V5"
SUPERSEDES_SCHEMA = v4.SCHEMA
LATERAL_OFFSET_FRACTIONS = (-0.8, -0.4, 0.0, 0.4, 0.8)


class RetentionQuickReleaseTactileV5Error(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class RetentionQuickReleaseTactileV5:
    mechanism: v1.RetentionQuickReleaseTactile
    lateral_offset_limit_mm: float
    lateral_offset_count: int
    release_station_count: int
    total_pose_count: int
    max_rigid_guide_intersection_mm3: float

    def validate(self) -> "RetentionQuickReleaseTactileV5":
        self.mechanism.validate()
        values = (
            self.lateral_offset_limit_mm,
            self.max_rigid_guide_intersection_mm3,
        )
        if not all(math.isfinite(value) for value in values):
            raise RetentionQuickReleaseTactileV5Error("clearance-screen metrics must be finite")
        if self.lateral_offset_limit_mm <= 0.0:
            raise RetentionQuickReleaseTactileV5Error("lateral offset limit must be positive")
        if self.lateral_offset_limit_mm >= min(
            self.mechanism.rail_radial_clearance_mm,
            self.mechanism.anti_rotation_side_clearance_mm,
        ):
            raise RetentionQuickReleaseTactileV5Error("lateral screen must remain inside nominal guide clearance")
        if self.lateral_offset_count != len(LATERAL_OFFSET_FRACTIONS):
            raise RetentionQuickReleaseTactileV5Error("unexpected lateral offset count")
        if self.release_station_count != v4.SWEEP_STATIONS:
            raise RetentionQuickReleaseTactileV5Error("release station count must match V4")
        if self.total_pose_count != self.lateral_offset_count * self.release_station_count:
            raise RetentionQuickReleaseTactileV5Error("pose count does not cover the full offset/travel grid")
        if self.max_rigid_guide_intersection_mm3 > v1.TOL_MM3:
            raise RetentionQuickReleaseTactileV5Error("quick-release slider collides inside lateral clearance envelope")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        payload = self.mechanism.manifest()
        payload.pop("manifest_sha256", None)
        payload["schema"] = SCHEMA
        payload["supersedes_schema"] = SUPERSEDES_SCHEMA
        payload["lateral_clearance_release_path"] = {
            "offset_limit_mm": self.lateral_offset_limit_mm,
            "offset_count": self.lateral_offset_count,
            "release_station_count": self.release_station_count,
            "total_pose_count": self.total_pose_count,
            "max_rigid_guide_intersection_mm3": self.max_rigid_guide_intersection_mm3,
            "criterion": "NO_POSITIVE_RIGID_GUIDE_INTERSECTION_INSIDE_BOUNDED_LATERAL_CLEARANCE_GRID",
            "scope": "DIGITAL_BREP_CLEARANCE_SCREEN_NOT_MANUFACTURING_OR_PHYSICAL_VALIDATION",
        }
        payload["physical_validation_eligible"] = False
        payload["manifest_sha256"] = sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()
        return payload


def _lateral_clearance_screen(
    mechanism: v1.RetentionQuickReleaseTactile,
    offset_limit_mm: float,
) -> tuple[int, int, int, float]:
    if not math.isfinite(offset_limit_mm) or offset_limit_mm <= 0.0:
        raise RetentionQuickReleaseTactileV5Error("offset limit must be finite and positive")
    nominal_limit = min(
        mechanism.rail_radial_clearance_mm,
        mechanism.anti_rotation_side_clearance_mm,
    )
    if offset_limit_mm >= nominal_limit:
        raise RetentionQuickReleaseTactileV5Error("offset limit must stay inside nominal guide clearance")

    maximum = 0.0
    poses = 0
    for fraction in LATERAL_OFFSET_FRACTIONS:
        y = offset_limit_mm * fraction
        for index in range(v4.SWEEP_STATIONS):
            x = v1.RELEASE_TRAVEL_MM * index / (v4.SWEEP_STATIONS - 1)
            moved = mechanism.slider.translate((x, y, 0.0))
            overlap = v1._intersection(moved, mechanism.guide)
            maximum = max(maximum, overlap)
            poses += 1
            if overlap > v1.TOL_MM3:
                raise RetentionQuickReleaseTactileV5Error(
                    f"rigid-guide collision at x={x:.6f} mm, y={y:.6f} mm: {overlap:.9f} mm3"
                )
    return len(LATERAL_OFFSET_FRACTIONS), v4.SWEEP_STATIONS, poses, maximum


def build_retention_quick_release_tactile_v5() -> RetentionQuickReleaseTactileV5:
    prior = v4.build_retention_quick_release_tactile_v4()
    mechanism = prior.mechanism
    nominal_limit = min(
        mechanism.rail_radial_clearance_mm,
        mechanism.anti_rotation_side_clearance_mm,
    )
    offset_limit = 0.8 * nominal_limit
    offset_count, station_count, poses, maximum = _lateral_clearance_screen(mechanism, offset_limit)
    return RetentionQuickReleaseTactileV5(
        mechanism=mechanism,
        lateral_offset_limit_mm=offset_limit,
        lateral_offset_count=offset_count,
        release_station_count=station_count,
        total_pose_count=poses,
        max_rigid_guide_intersection_mm3=round(maximum, 12),
    ).validate()
