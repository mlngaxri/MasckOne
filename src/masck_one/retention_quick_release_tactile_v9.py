from __future__ import annotations

"""Retention quick-release V9: inter-station release-path clearance verification.

V8 strengthens transverse boundary coverage but still evaluates only the 41 inherited
release stations. V9 preserves the V8 constrained transverse domain and inserts every
inter-station midpoint, screening 81 deterministic travel positions so collisions
between inherited stations fail closed. This remains sampled digital B-rep evidence.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math

from . import retention_quick_release_tactile as v1
from . import retention_quick_release_tactile_v4 as v4
from . import retention_quick_release_tactile_v8 as v8

SCHEMA = "MASCK_ONE_RETENTION_QUICK_RELEASE_TACTILE_V9"
SUPERSEDES_SCHEMA = v8.SCHEMA
CLEARANCE_FRACTION = v8.CLEARANCE_FRACTION
TRAVEL_SUBDIVISIONS_PER_V4_INTERVAL = 2
TRAVEL_STATIONS = (v4.SWEEP_STATIONS - 1) * TRAVEL_SUBDIVISIONS_PER_V4_INTERVAL + 1


class RetentionQuickReleaseTactileV9Error(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class RetentionQuickReleaseTactileV9:
    mechanism: v1.RetentionQuickReleaseTactile
    radial_limit_mm: float
    side_limit_mm: float
    transverse_sample_count: int
    boundary_sample_count: int
    release_station_count: int
    inherited_station_count: int
    midpoint_station_count: int
    total_pose_count: int
    max_rigid_guide_intersection_mm3: float

    def validate(self) -> "RetentionQuickReleaseTactileV9":
        self.mechanism.validate()
        metrics = (self.radial_limit_mm, self.side_limit_mm, self.max_rigid_guide_intersection_mm3)
        if not all(math.isfinite(value) for value in metrics):
            raise RetentionQuickReleaseTactileV9Error("clearance-screen metrics must be finite")
        if not 0.0 < self.radial_limit_mm < self.mechanism.rail_radial_clearance_mm:
            raise RetentionQuickReleaseTactileV9Error("radial limit must remain inside spool-rail radial clearance")
        if not 0.0 < self.side_limit_mm < self.mechanism.anti_rotation_side_clearance_mm:
            raise RetentionQuickReleaseTactileV9Error("side limit must remain inside anti-rotation side clearance")
        samples = v8._constrained_transverse_samples(self.radial_limit_mm, self.side_limit_mm)
        if self.transverse_sample_count != len(samples):
            raise RetentionQuickReleaseTactileV9Error("transverse sample count does not match V8 constrained domain")
        expected_boundary = sum(v8._is_boundary_sample(y, z, self.radial_limit_mm, self.side_limit_mm) for y, z in samples)
        if self.boundary_sample_count != expected_boundary:
            raise RetentionQuickReleaseTactileV9Error("boundary sample count does not match V8 constrained domain")
        if self.release_station_count != TRAVEL_STATIONS:
            raise RetentionQuickReleaseTactileV9Error("release station count does not cover inherited stations and midpoints")
        if self.inherited_station_count != v4.SWEEP_STATIONS:
            raise RetentionQuickReleaseTactileV9Error("all V4 release stations must remain represented")
        if self.midpoint_station_count != v4.SWEEP_STATIONS - 1:
            raise RetentionQuickReleaseTactileV9Error("every inherited travel interval must contribute one midpoint")
        if self.total_pose_count != self.transverse_sample_count * self.release_station_count:
            raise RetentionQuickReleaseTactileV9Error("pose count does not cover constrained samples through densified travel")
        if self.max_rigid_guide_intersection_mm3 > v1.TOL_MM3:
            raise RetentionQuickReleaseTactileV9Error("quick-release slider collides inside densified clearance envelope")
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
            "inherited_station_count": self.inherited_station_count,
            "midpoint_station_count": self.midpoint_station_count,
            "travel_subdivisions_per_v4_interval": TRAVEL_SUBDIVISIONS_PER_V4_INTERVAL,
            "total_pose_count": self.total_pose_count,
            "max_rigid_guide_intersection_mm3": self.max_rigid_guide_intersection_mm3,
            "criterion": "NO_POSITIVE_RIGID_GUIDE_INTERSECTION_AT_V8_TRANSVERSE_SAMPLES_AND_DENSIFIED_TRAVEL_STATIONS",
            "scope": "DIGITAL_BREP_SAMPLED_CLEARANCE_SCREEN_NOT_CONTINUOUS_PROOF_MANUFACTURING_OR_PHYSICAL_VALIDATION",
        }
        payload["physical_validation_eligible"] = False
        payload["manifest_sha256"] = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        return payload


def _travel_positions_mm() -> tuple[float, ...]:
    return tuple(
        v1.RELEASE_TRAVEL_MM * index / (TRAVEL_STATIONS - 1)
        for index in range(TRAVEL_STATIONS)
    )


def _densified_clearance_screen(
    mechanism: v1.RetentionQuickReleaseTactile,
    radial_limit_mm: float,
    side_limit_mm: float,
) -> tuple[int, int, int, int, int, int, float]:
    if not math.isfinite(radial_limit_mm) or not 0.0 < radial_limit_mm < mechanism.rail_radial_clearance_mm:
        raise RetentionQuickReleaseTactileV9Error("radial limit must stay inside spool-rail radial clearance")
    if not math.isfinite(side_limit_mm) or not 0.0 < side_limit_mm < mechanism.anti_rotation_side_clearance_mm:
        raise RetentionQuickReleaseTactileV9Error("side limit must stay inside anti-rotation side clearance")
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
                raise RetentionQuickReleaseTactileV9Error(
                    f"rigid-guide collision at x={x:.6f} mm, y={y:.6f} mm, z={z:.6f} mm: {overlap:.9f} mm3"
                )
    return len(samples), boundary, len(positions), v4.SWEEP_STATIONS, v4.SWEEP_STATIONS - 1, poses, maximum


def build_retention_quick_release_tactile_v9() -> RetentionQuickReleaseTactileV9:
    prior = v8.build_retention_quick_release_tactile_v8()
    mechanism = prior.mechanism
    values = _densified_clearance_screen(mechanism, prior.radial_limit_mm, prior.side_limit_mm)
    samples, boundary, stations, inherited, midpoints, poses, maximum = values
    return RetentionQuickReleaseTactileV9(
        mechanism=mechanism,
        radial_limit_mm=prior.radial_limit_mm,
        side_limit_mm=prior.side_limit_mm,
        transverse_sample_count=samples,
        boundary_sample_count=boundary,
        release_station_count=stations,
        inherited_station_count=inherited,
        midpoint_station_count=midpoints,
        total_pose_count=poses,
        max_rigid_guide_intersection_mm3=round(maximum, 12),
    ).validate()
