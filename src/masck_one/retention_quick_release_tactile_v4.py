from __future__ import annotations

"""Retention quick-release V4: continuous guide-clearance verification.

V3 repaired the installed bumper/rib conflict but only proved rigid-guide clearance at
the two nominal end states. V4 keeps the V3 mechanism unchanged and adds a bounded
continuous-path digital verification so an interior collision cannot hide between
locked and released poses. This is kinematic B-rep evidence only; force, wet use,
wear, contamination tolerance and physical release performance remain unvalidated.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math

from . import retention_quick_release_tactile as v1
from . import retention_quick_release_tactile_v3 as v3

SCHEMA = "MASCK_ONE_RETENTION_QUICK_RELEASE_TACTILE_V4"
SUPERSEDES_SCHEMA = v3.SCHEMA
SWEEP_STATIONS = 41


class RetentionQuickReleaseTactileV4Error(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class RetentionQuickReleaseTactileV4:
    mechanism: v1.RetentionQuickReleaseTactile
    sweep_station_count: int
    max_rigid_guide_intersection_mm3: float
    minimum_checked_x_mm: float
    maximum_checked_x_mm: float

    def validate(self) -> "RetentionQuickReleaseTactileV4":
        self.mechanism.validate()
        if self.sweep_station_count < 3:
            raise RetentionQuickReleaseTactileV4Error("continuous sweep needs interior stations")
        if not all(math.isfinite(v) for v in (
            self.max_rigid_guide_intersection_mm3,
            self.minimum_checked_x_mm,
            self.maximum_checked_x_mm,
        )):
            raise RetentionQuickReleaseTactileV4Error("sweep metrics must be finite")
        if self.max_rigid_guide_intersection_mm3 > v1.TOL_MM3:
            raise RetentionQuickReleaseTactileV4Error("quick-release slider collides with rigid guide during travel")
        if abs(self.minimum_checked_x_mm) > 1e-12 or abs(self.maximum_checked_x_mm - v1.RELEASE_TRAVEL_MM) > 1e-12:
            raise RetentionQuickReleaseTactileV4Error("sweep must cover the complete release travel")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        payload = self.mechanism.manifest()
        payload.pop("manifest_sha256", None)
        payload["schema"] = SCHEMA
        payload["supersedes_schema"] = SUPERSEDES_SCHEMA
        payload["continuous_release_path"] = {
            "travel_mm": v1.RELEASE_TRAVEL_MM,
            "station_count": self.sweep_station_count,
            "includes_locked_endpoint": True,
            "includes_released_endpoint": True,
            "max_rigid_guide_intersection_mm3": self.max_rigid_guide_intersection_mm3,
            "criterion": "NO_POSITIVE_RIGID_GUIDE_INTERSECTION_AT_ANY_CHECKED_STATION",
            "scope": "DIGITAL_BREP_TRANSLATION_SCREEN_NOT_PHYSICAL_SERVICE_VALIDATION",
        }
        payload["physical_validation_eligible"] = False
        payload["manifest_sha256"] = sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()
        return payload


def _continuous_guide_screen(mechanism: v1.RetentionQuickReleaseTactile) -> tuple[int, float, float, float]:
    if SWEEP_STATIONS < 3:
        raise RetentionQuickReleaseTactileV4Error("SWEEP_STATIONS must include interior travel")
    maximum = 0.0
    xs: list[float] = []
    for index in range(SWEEP_STATIONS):
        x = v1.RELEASE_TRAVEL_MM * index / (SWEEP_STATIONS - 1)
        xs.append(x)
        moved = mechanism.slider.translate((x, 0.0, 0.0))
        overlap = v1._intersection(moved, mechanism.guide)
        maximum = max(maximum, overlap)
        if overlap > v1.TOL_MM3:
            raise RetentionQuickReleaseTactileV4Error(
                f"rigid-guide collision at release travel x={x:.6f} mm: {overlap:.9f} mm3"
            )
    return len(xs), maximum, min(xs), max(xs)


def build_retention_quick_release_tactile_v4() -> RetentionQuickReleaseTactileV4:
    prior = v3.build_retention_quick_release_tactile_v3()
    count, maximum, xmin, xmax = _continuous_guide_screen(prior.mechanism)
    return RetentionQuickReleaseTactileV4(
        mechanism=prior.mechanism,
        sweep_station_count=count,
        max_rigid_guide_intersection_mm3=round(maximum, 12),
        minimum_checked_x_mm=xmin,
        maximum_checked_x_mm=xmax,
    ).validate()
