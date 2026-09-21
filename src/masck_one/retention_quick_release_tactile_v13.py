from __future__ import annotations

"""Retention quick-release V13: independently audit sampled release-path topology.

V12 cryptographically binds the canonical V11 station coordinates. V13 adds explicit
geometric invariants for that schedule so a self-consistent digest cannot hide endpoint,
ordering, spacing, or travel-span drift. This remains sampled digital evidence, not
continuous swept-volume or physical validation.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math

from . import retention_quick_release_tactile as v1
from . import retention_quick_release_tactile_v11 as v11
from . import retention_quick_release_tactile_v12 as v12

SCHEMA = "MASCK_ONE_RETENTION_QUICK_RELEASE_TACTILE_V13"
SUPERSEDES_SCHEMA = v12.SCHEMA
COORDINATE_TOL_MM = v12.COORDINATE_TOL_MM


class RetentionQuickReleaseTactileV13Error(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class RetentionQuickReleaseTactileV13:
    prior: v12.RetentionQuickReleaseTactileV12
    first_station_mm: float
    last_station_mm: float
    minimum_step_mm: float
    maximum_step_mm: float
    travel_span_mm: float

    def validate(self) -> "RetentionQuickReleaseTactileV13":
        self.prior.validate()
        positions = v12._canonical_positions()
        if len(positions) != v11.TRAVEL_STATIONS or len(positions) < 2:
            raise RetentionQuickReleaseTactileV13Error("canonical station schedule has invalid cardinality")
        if not all(math.isfinite(value) for value in positions):
            raise RetentionQuickReleaseTactileV13Error("canonical station schedule contains non-finite coordinates")
        steps = tuple(right - left for left, right in zip(positions, positions[1:]))
        if any(step <= 0.0 for step in steps):
            raise RetentionQuickReleaseTactileV13Error("canonical station schedule must be strictly increasing")
        expected_step = v1.RELEASE_TRAVEL_MM / (v11.TRAVEL_STATIONS - 1)
        expected = (positions[0], positions[-1], min(steps), max(steps), positions[-1] - positions[0])
        recorded = (self.first_station_mm, self.last_station_mm, self.minimum_step_mm, self.maximum_step_mm, self.travel_span_mm)
        if not all(math.isfinite(value) for value in recorded):
            raise RetentionQuickReleaseTactileV13Error("release-path topology evidence must be finite")
        if any(not math.isclose(value, target, rel_tol=0.0, abs_tol=COORDINATE_TOL_MM) for value, target in zip(recorded, expected)):
            raise RetentionQuickReleaseTactileV13Error("release-path topology evidence is stale")
        if not math.isclose(positions[0], 0.0, rel_tol=0.0, abs_tol=COORDINATE_TOL_MM):
            raise RetentionQuickReleaseTactileV13Error("release schedule does not start at retained state")
        if not math.isclose(positions[-1], v1.RELEASE_TRAVEL_MM, rel_tol=0.0, abs_tol=COORDINATE_TOL_MM):
            raise RetentionQuickReleaseTactileV13Error("release schedule does not reach full release travel")
        if any(not math.isclose(step, expected_step, rel_tol=0.0, abs_tol=COORDINATE_TOL_MM) for step in steps):
            raise RetentionQuickReleaseTactileV13Error("release schedule is not uniformly sampled")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        payload = self.prior.manifest()
        payload.pop("manifest_sha256", None)
        payload["schema"] = SCHEMA
        payload["supersedes_schema"] = SUPERSEDES_SCHEMA
        payload["release_path_topology_audit"] = {
            "first_station_mm": self.first_station_mm,
            "last_station_mm": self.last_station_mm,
            "minimum_step_mm": self.minimum_step_mm,
            "maximum_step_mm": self.maximum_step_mm,
            "travel_span_mm": self.travel_span_mm,
            "coordinate_tolerance_mm": COORDINATE_TOL_MM,
            "criterion": "STRICTLY_INCREASING_UNIFORM_FULL_TRAVEL_STATION_TOPOLOGY",
            "scope": "DIGITAL_SAMPLED_TOPOLOGY_NOT_CONTINUOUS_CLEARANCE_OR_PHYSICAL_VALIDATION",
        }
        payload["physical_validation_eligible"] = False
        payload["manifest_sha256"] = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        return payload


def build_retention_quick_release_tactile_v13() -> RetentionQuickReleaseTactileV13:
    prior = v12.build_retention_quick_release_tactile_v12()
    positions = v12._canonical_positions()
    steps = tuple(right - left for left, right in zip(positions, positions[1:]))
    return RetentionQuickReleaseTactileV13(prior, positions[0], positions[-1], min(steps), max(steps), positions[-1] - positions[0]).validate()
