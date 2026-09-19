from __future__ import annotations

"""Retention quick-release V10: quarter-interval release-path clearance verification.

V9 inserts one midpoint between each inherited V4 release station. V10 preserves the
accepted V8 transverse clearance domain and resolves each inherited V4 travel interval
into four equal segments. This retains every V9 station and adds both quarter points,
reducing the maximum unscreened travel interval by half without changing mechanism
geometry. This remains sampled digital B-rep evidence, not continuous clearance proof.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math

from . import retention_quick_release_tactile as v1
from . import retention_quick_release_tactile_v4 as v4
from . import retention_quick_release_tactile_v8 as v8
from . import retention_quick_release_tactile_v9 as v9

SCHEMA = "MASCK_ONE_RETENTION_QUICK_RELEASE_TACTILE_V10"
SUPERSEDES_SCHEMA = v9.SCHEMA
CLEARANCE_FRACTION = v8.CLEARANCE_FRACTION
TRAVEL_SUBDIVISIONS_PER_V4_INTERVAL = 4
TRAVEL_STATIONS = (v4.SWEEP_STATIONS - 1) * TRAVEL_SUBDIVISIONS_PER_V4_INTERVAL + 1


class RetentionQuickReleaseTactileV10Error(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class RetentionQuickReleaseTactileV10:
    mechanism: v1.RetentionQuickReleaseTactile
    radial_limit_mm: float
    side_limit_mm: float
    transverse_sample_count: int
    boundary_sample_count: int
    release_station_count: int
    inherited_v9_station_count: int
    added_quarter_station_count: int
    max_unscreened_travel_interval_mm: float
    total_pose_count: int
    max_rigid_guide_intersection_mm3: float

    def validate(self) -> "RetentionQuickReleaseTactileV10":
        self.mechanism.validate()
        metrics = (self.radial_limit_mm, self.side_limit_mm, self.max_unscreened_travel_interval_mm, self.max_rigid_guide_intersection_mm3)
        if not all(math.isfinite(value) for value in metrics):
            raise RetentionQuickReleaseTactileV10Error("clearance-screen metrics must be finite")
        if not 0.0 < self.radial_limit_mm < self.mechanism.rail_radial_clearance_mm:
            raise RetentionQuickReleaseTactileV10Error("radial limit must remain inside spool-rail radial clearance")
        if not 0.0 < self.side_limit_mm < self.mechanism.anti_rotation_side_clearance_mm:
            raise RetentionQuickReleaseTactileV10Error("side limit must remain inside anti-rotation side clearance")
        samples = v8._constrained_transverse_samples(self.radial_limit_mm, self.side_limit_mm)
        if self.transverse_sample_count != len(samples):
            raise RetentionQuickReleaseTactileV10Error("transverse sample count does not match V8 constrained domain")
        expected_boundary = sum(v8._is_boundary_sample(y, z, self.radial_limit_mm, self.side_limit_mm) for y, z in samples)
        if self.boundary_sample_count != expected_boundary:
            raise RetentionQuickReleaseTactileV10Error("boundary sample count does not match V8 constrained domain")
        if self.release_station_count != TRAVEL_STATIONS:
            raise RetentionQuickReleaseTactileV10Error("release station count does not cover quarter intervals")
        if self.inherited_v9_station_count != v9.TRAVEL_STATIONS:
            raise RetentionQuickReleaseTactileV10Error("all V9 travel stations must remain represented")
        if self.added_quarter_station_count != TRAVEL_STATIONS - v9.TRAVEL_STATIONS:
            raise RetentionQuickReleaseTactileV10Error("quarter-point station count is inconsistent")
        expected_interval = v1.RELEASE_TRAVEL_MM / (TRAVEL_STATIONS - 1)
        if not math.isclose(self.max_unscreened_travel_interval_mm, expected_interval, rel_tol=0.0, abs_tol=1e-12):
            raise RetentionQuickReleaseTactileV10Error("maximum unscreened travel interval is inconsistent")
        if self.total_pose_count != self.transverse_sample_count * self.release_station_count:
            raise RetentionQuickReleaseTactileV10Error("pose count does not cover constrained samples through quartered travel")
        if self.max_rigid_guide_intersection_mm3 > v1.TOL_MM3:
            raise RetentionQuickReleaseTactileV10Error("quick-release slider collides inside quartered clearance envelope")
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
            "boundary_sample_count": self.boundary_sample_count,
            "release_station_count": self.release_station_count,
            "inherited_v9_station_count": self.inherited_v9_station_count,
            "added_quarter_station_count": self.added_quarter_station_count,
            "travel_subdivisions_per_v4_interval": TRAVEL_SUBDIVISIONS_PER_V4_INTERVAL,
            "max_unscreened_travel_interval_mm": self.max_unscreened_travel_interval_mm,
            "total_pose_count": self.total_pose_count,
            "max_rigid_guide_intersection_mm3": self.max_rigid_guide_intersection_mm3,
            "criterion": "NO_POSITIVE_RIGID_GUIDE_INTERSECTION_AT_V8_TRANSVERSE_SAMPLES_AND_QUARTERED_TRAVEL_STATIONS",
            "scope": "DIGITAL_BREP_SAMPLED_CLEARANCE_SCREEN_NOT_CONTINUOUS_PROOF_MANUFACTURING_OR_PHYSICAL_VALIDATION",
        }
        payload["physical_validation_eligible"] = False
        payload["manifest_sha256"] = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        return payload


def _travel_positions_mm() -> tuple[float, ...]:
    return tuple(v1.RELEASE_TRAVEL_MM * index / (TRAVEL_STATIONS - 1) for index in range(TRAVEL_STATIONS))


def _quartered_clearance_screen(mechanism: v1.RetentionQuickReleaseTactile, radial_limit_mm: float, side_limit_mm: float) -> tuple[int, int, int, int, int, float, int, float]:
    if not math.isfinite(radial_limit_mm) or not 0.0 < radial_limit_mm < mechanism.rail_radial_clearance_mm:
        raise RetentionQuickReleaseTactileV10Error("radial limit must stay inside spool-rail radial clearance")
    if not math.isfinite(side_limit_mm) or not 0.0 < side_limit_mm < mechanism.anti_rotation_side_clearance_mm:
        raise RetentionQuickReleaseTactileV10Error("side limit must stay inside anti-rotation side clearance")
    samples = v8._constrained_transverse_samples(radial_limit_mm, side_limit_mm)
    boundary = sum(v8._is_boundary_sample(y, z, radial_limit_mm, side_limit_mm) for y, z in samples)
    positions = _travel_positions_mm()
    maximum = 0.0
    poses = 0
    for y, z in samples:
        for x in positions:
            overlap = v1._intersection(mechanism.slider.translate((x, y, z)), mechanism.guide)
            maximum = max(maximum, overlap)
            poses += 1
            if overlap > v1.TOL_MM3:
                raise RetentionQuickReleaseTactileV10Error(f"rigid-guide collision at x={x:.6f} mm, y={y:.6f} mm, z={z:.6f} mm: {overlap:.9f} mm3")
    interval = max(right - left for left, right in zip(positions, positions[1:]))
    return len(samples), boundary, len(positions), v9.TRAVEL_STATIONS, len(positions) - v9.TRAVEL_STATIONS, interval, poses, maximum


def build_retention_quick_release_tactile_v10() -> RetentionQuickReleaseTactileV10:
    prior = v9.build_retention_quick_release_tactile_v9()
    mechanism = prior.mechanism
    samples, boundary, stations, inherited, added, interval, poses, maximum = _quartered_clearance_screen(mechanism, prior.radial_limit_mm, prior.side_limit_mm)
    return RetentionQuickReleaseTactileV10(mechanism, prior.radial_limit_mm, prior.side_limit_mm, samples, boundary, stations, inherited, added, interval, poses, round(maximum, 12)).validate()
