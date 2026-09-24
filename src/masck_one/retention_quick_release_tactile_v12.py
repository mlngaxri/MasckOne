from __future__ import annotations

"""Retention quick-release V12: bind the exact sampled release-station schedule.

V11 proves sampled B-rep clearance on an eighth-interval schedule, but its retained
evidence records counts and maximum interval rather than the exact station identity.
V12 preserves V11 geometry and clearance evidence while cryptographically binding the
canonical station coordinates and explicitly proving every V10 station is inherited.
This remains sampled digital evidence, not continuous swept-volume or physical proof.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import re

from . import retention_quick_release_tactile as v1
from . import retention_quick_release_tactile_v10 as v10
from . import retention_quick_release_tactile_v11 as v11

SCHEMA = "MASCK_ONE_RETENTION_QUICK_RELEASE_TACTILE_V12"
SUPERSEDES_SCHEMA = v11.SCHEMA
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
COORDINATE_TOL_MM = 1e-12


class RetentionQuickReleaseTactileV12Error(ValueError):
    pass


def _canonical_positions() -> tuple[float, ...]:
    return tuple(v1.RELEASE_TRAVEL_MM * index / (v11.TRAVEL_STATIONS - 1) for index in range(v11.TRAVEL_STATIONS))


def _schedule_digest(positions: tuple[float, ...]) -> str:
    payload = json.dumps(positions, separators=(",", ":"), allow_nan=False).encode()
    return sha256(payload).hexdigest()


@dataclass(frozen=True, slots=True)
class RetentionQuickReleaseTactileV12:
    prior: v11.RetentionQuickReleaseTactileV11
    station_schedule_sha256: str
    inherited_v10_station_count: int
    max_v10_registration_error_mm: float

    def validate(self) -> "RetentionQuickReleaseTactileV12":
        self.prior.validate()
        positions = _canonical_positions()
        expected_digest = _schedule_digest(positions)
        if not isinstance(self.station_schedule_sha256, str) or _SHA256.fullmatch(self.station_schedule_sha256) is None:
            raise RetentionQuickReleaseTactileV12Error("station schedule digest must be canonical lowercase SHA-256")
        if self.station_schedule_sha256 != expected_digest:
            raise RetentionQuickReleaseTactileV12Error("station schedule digest does not match canonical V11 coordinates")
        inherited = v10._travel_positions_mm()
        errors = tuple(min(abs(x - old) for x in positions) for old in inherited)
        if self.inherited_v10_station_count != len(inherited):
            raise RetentionQuickReleaseTactileV12Error("V10 station inheritance count is inconsistent")
        expected_error = max(errors, default=0.0)
        if not math.isfinite(self.max_v10_registration_error_mm) or self.max_v10_registration_error_mm < 0.0:
            raise RetentionQuickReleaseTactileV12Error("V10 station registration evidence must be finite and nonnegative")
        if not math.isclose(self.max_v10_registration_error_mm, expected_error, rel_tol=0.0, abs_tol=COORDINATE_TOL_MM):
            raise RetentionQuickReleaseTactileV12Error("V10 station registration evidence is stale")
        if expected_error > COORDINATE_TOL_MM:
            raise RetentionQuickReleaseTactileV12Error("canonical V11 schedule does not retain every V10 station")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        payload = self.prior.manifest()
        payload.pop("manifest_sha256", None)
        payload["schema"] = SCHEMA
        payload["supersedes_schema"] = SUPERSEDES_SCHEMA
        payload["release_station_schedule_identity"] = {
            "station_schedule_sha256": self.station_schedule_sha256,
            "station_count": v11.TRAVEL_STATIONS,
            "inherited_v10_station_count": self.inherited_v10_station_count,
            "max_v10_registration_error_mm": self.max_v10_registration_error_mm,
            "coordinate_tolerance_mm": COORDINATE_TOL_MM,
            "criterion": "CANONICAL_EIGHTH_INTERVAL_SCHEDULE_DIGEST_AND_EXACT_V10_STATION_INHERITANCE",
            "scope": "DIGITAL_SAMPLED_STATION_IDENTITY_NOT_CONTINUOUS_CLEARANCE_OR_PHYSICAL_VALIDATION",
        }
        payload["physical_validation_eligible"] = False
        payload["manifest_sha256"] = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        return payload


def build_retention_quick_release_tactile_v12() -> RetentionQuickReleaseTactileV12:
    prior = v11.build_retention_quick_release_tactile_v11()
    positions = _canonical_positions()
    inherited = v10._travel_positions_mm()
    error = max((min(abs(x - old) for x in positions) for old in inherited), default=0.0)
    return RetentionQuickReleaseTactileV12(prior, _schedule_digest(positions), len(inherited), error).validate()
