from __future__ import annotations

"""Retention quick-release V6: two-axis guide-clearance release-path verification.

V5 perturbs the slider along one lateral axis. V6 closes the obvious orthogonal gap by
screening a bounded Y/Z offset grid through the complete release travel. The bound stays
inside the existing nominal guide clearance and is a digital robustness screen only,
not a manufactured tolerance or physical validation claim.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math

from . import retention_quick_release_tactile as v1
from . import retention_quick_release_tactile_v4 as v4
from . import retention_quick_release_tactile_v5 as v5

SCHEMA = "MASCK_ONE_RETENTION_QUICK_RELEASE_TACTILE_V6"
SUPERSEDES_SCHEMA = v5.SCHEMA
OFFSET_FRACTIONS = v5.LATERAL_OFFSET_FRACTIONS


class RetentionQuickReleaseTactileV6Error(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class RetentionQuickReleaseTactileV6:
    mechanism: v1.RetentionQuickReleaseTactile
    offset_limit_mm: float
    transverse_grid_count: int
    release_station_count: int
    total_pose_count: int
    max_rigid_guide_intersection_mm3: float

    def validate(self) -> "RetentionQuickReleaseTactileV6":
        self.mechanism.validate()
        if not all(math.isfinite(value) for value in (self.offset_limit_mm, self.max_rigid_guide_intersection_mm3)):
            raise RetentionQuickReleaseTactileV6Error("clearance-screen metrics must be finite")
        nominal_limit = min(self.mechanism.rail_radial_clearance_mm, self.mechanism.anti_rotation_side_clearance_mm)
        if self.offset_limit_mm <= 0.0 or self.offset_limit_mm >= nominal_limit:
            raise RetentionQuickReleaseTactileV6Error("offset limit must remain positive and inside nominal guide clearance")
        expected_grid = len(OFFSET_FRACTIONS) ** 2
        if self.transverse_grid_count != expected_grid:
            raise RetentionQuickReleaseTactileV6Error("transverse grid does not cover both offset axes")
        if self.release_station_count != v4.SWEEP_STATIONS:
            raise RetentionQuickReleaseTactileV6Error("release station count must match V4")
        if self.total_pose_count != expected_grid * self.release_station_count:
            raise RetentionQuickReleaseTactileV6Error("pose count does not cover the full transverse/travel grid")
        if self.max_rigid_guide_intersection_mm3 > v1.TOL_MM3:
            raise RetentionQuickReleaseTactileV6Error("quick-release slider collides inside transverse clearance envelope")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        payload = self.mechanism.manifest()
        payload.pop("manifest_sha256", None)
        payload["schema"] = SCHEMA
        payload["supersedes_schema"] = SUPERSEDES_SCHEMA
        payload["transverse_clearance_release_path"] = {
            "offset_limit_mm": self.offset_limit_mm,
            "offset_axes": ["Y", "Z"],
            "transverse_grid_count": self.transverse_grid_count,
            "release_station_count": self.release_station_count,
            "total_pose_count": self.total_pose_count,
            "max_rigid_guide_intersection_mm3": self.max_rigid_guide_intersection_mm3,
            "criterion": "NO_POSITIVE_RIGID_GUIDE_INTERSECTION_INSIDE_BOUNDED_YZ_CLEARANCE_GRID",
            "scope": "DIGITAL_BREP_CLEARANCE_SCREEN_NOT_MANUFACTURING_OR_PHYSICAL_VALIDATION",
        }
        payload["physical_validation_eligible"] = False
        payload["manifest_sha256"] = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        return payload


def _transverse_clearance_screen(mechanism: v1.RetentionQuickReleaseTactile, offset_limit_mm: float) -> tuple[int, int, int, float]:
    if not math.isfinite(offset_limit_mm) or offset_limit_mm <= 0.0:
        raise RetentionQuickReleaseTactileV6Error("offset limit must be finite and positive")
    nominal_limit = min(mechanism.rail_radial_clearance_mm, mechanism.anti_rotation_side_clearance_mm)
    if offset_limit_mm >= nominal_limit:
        raise RetentionQuickReleaseTactileV6Error("offset limit must stay inside nominal guide clearance")

    maximum = 0.0
    poses = 0
    for y_fraction in OFFSET_FRACTIONS:
        y = offset_limit_mm * y_fraction
        for z_fraction in OFFSET_FRACTIONS:
            z = offset_limit_mm * z_fraction
            for index in range(v4.SWEEP_STATIONS):
                x = v1.RELEASE_TRAVEL_MM * index / (v4.SWEEP_STATIONS - 1)
                moved = mechanism.slider.translate((x, y, z))
                overlap = v1._intersection(moved, mechanism.guide)
                maximum = max(maximum, overlap)
                poses += 1
                if overlap > v1.TOL_MM3:
                    raise RetentionQuickReleaseTactileV6Error(
                        f"rigid-guide collision at x={x:.6f} mm, y={y:.6f} mm, z={z:.6f} mm: {overlap:.9f} mm3"
                    )
    return len(OFFSET_FRACTIONS) ** 2, v4.SWEEP_STATIONS, poses, maximum


def build_retention_quick_release_tactile_v6() -> RetentionQuickReleaseTactileV6:
    prior = v5.build_retention_quick_release_tactile_v5()
    mechanism = prior.mechanism
    nominal_limit = min(mechanism.rail_radial_clearance_mm, mechanism.anti_rotation_side_clearance_mm)
    offset_limit = 0.8 * nominal_limit
    grid_count, station_count, poses, maximum = _transverse_clearance_screen(mechanism, offset_limit)
    return RetentionQuickReleaseTactileV6(
        mechanism=mechanism,
        offset_limit_mm=offset_limit,
        transverse_grid_count=grid_count,
        release_station_count=station_count,
        total_pose_count=poses,
        max_rigid_guide_intersection_mm3=round(maximum, 12),
    ).validate()
