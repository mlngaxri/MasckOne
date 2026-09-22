from __future__ import annotations

"""Retention quick-release V24: cross-bind sampled travel stations to evidence.

V22 proves the accumulated 1/16 schedule and V23 binds the four clearance-evidence
families. V24 closes the remaining cross-contract gap by requiring each manifest
family to expose exactly its authoritative travel stations and by proving pose-count
arithmetic against those stations and the transverse mesh count. This remains
sampled digital B-rep evidence, not continuous swept-volume or physical proof.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import re

from . import retention_quick_release_tactile_v18 as v18
from . import retention_quick_release_tactile_v19 as v19
from . import retention_quick_release_tactile_v20 as v20
from . import retention_quick_release_tactile_v21 as v21
from . import retention_quick_release_tactile_v23 as v23

SCHEMA = "MASCK_ONE_RETENTION_QUICK_RELEASE_TACTILE_V24"
SUPERSEDES_SCHEMA = v23.SCHEMA
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_FAMILY_CONTRACTS = (
    ("interstitial_release_travel_screen", "travel_midpoints_mm", v18._midpoint_positions),
    ("quarter_release_travel_screen", "travel_quarter_points_mm", v19._quarter_positions),
    ("eighth_release_travel_screen", "travel_eighth_points_mm", v20._eighth_positions),
    ("sixteenth_release_travel_screen", "travel_sixteenth_points_mm", v21._sixteenth_positions),
)


class RetentionQuickReleaseTactileV24Error(ValueError):
    pass


def _station_binding(prior: v23.RetentionQuickReleaseTactileV23) -> tuple[int, int, str]:
    manifest = prior.prior.prior.manifest()
    records: list[dict[str, object]] = []
    station_total = 0
    pose_total = 0
    for family, position_key, supplier in _FAMILY_CONTRACTS:
        evidence = manifest.get(family)
        if not isinstance(evidence, dict):
            raise RetentionQuickReleaseTactileV24Error(f"missing travel evidence family {family}")
        positions = evidence.get(position_key)
        expected = tuple(supplier())
        if not isinstance(positions, list) or len(positions) != len(expected):
            raise RetentionQuickReleaseTactileV24Error(f"{family} travel station list is stale")
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)) for value in positions):
            raise RetentionQuickReleaseTactileV24Error(f"{family} travel station list is invalid")
        actual = tuple(float(value) for value in positions)
        if any(not math.isclose(a, b, rel_tol=0.0, abs_tol=1e-12) for a, b in zip(actual, expected)):
            raise RetentionQuickReleaseTactileV24Error(f"{family} travel stations do not match authoritative schedule")
        samples = evidence.get("transverse_sample_count")
        poses = evidence.get("pose_count")
        if isinstance(samples, bool) or not isinstance(samples, int) or samples <= 0:
            raise RetentionQuickReleaseTactileV24Error(f"{family} transverse sample count is invalid")
        if isinstance(poses, bool) or not isinstance(poses, int) or poses != len(expected) * samples:
            raise RetentionQuickReleaseTactileV24Error(f"{family} pose count does not match station/sample product")
        station_total += len(expected)
        pose_total += poses
        records.append({
            "family": family,
            "position_key": position_key,
            "positions_mm": [format(value, ".12f") for value in actual],
            "transverse_sample_count": samples,
            "pose_count": poses,
        })
    digest = sha256(json.dumps(records, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()
    return station_total, pose_total, digest


@dataclass(frozen=True, slots=True)
class RetentionQuickReleaseTactileV24:
    prior: v23.RetentionQuickReleaseTactileV23
    bound_station_count: int
    bound_pose_count: int
    station_evidence_sha256: str

    def validate(self) -> "RetentionQuickReleaseTactileV24":
        self.prior.validate()
        station_count, pose_count, digest = _station_binding(self.prior)
        if self.bound_station_count != station_count or station_count <= 0:
            raise RetentionQuickReleaseTactileV24Error("bound travel station count is stale")
        if self.bound_pose_count != pose_count or pose_count != self.prior.bound_pose_count:
            raise RetentionQuickReleaseTactileV24Error("bound travel pose count is stale")
        if not isinstance(self.station_evidence_sha256, str) or _DIGEST_RE.fullmatch(self.station_evidence_sha256) is None:
            raise RetentionQuickReleaseTactileV24Error("station evidence digest must be canonical lowercase SHA-256")
        if self.station_evidence_sha256 != digest:
            raise RetentionQuickReleaseTactileV24Error("station evidence digest is stale")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        payload = self.prior.manifest()
        payload.pop("manifest_sha256", None)
        payload["schema"] = SCHEMA
        payload["supersedes_schema"] = SUPERSEDES_SCHEMA
        payload["travel_station_clearance_cross_binding"] = {
            "bound_station_count": self.bound_station_count,
            "bound_pose_count": self.bound_pose_count,
            "station_evidence_sha256": self.station_evidence_sha256,
            "criterion": "EACH_BOUND_CLEARANCE_FAMILY_EXACTLY_MATCHES_AUTHORITATIVE_TRAVEL_STATIONS_AND_POSE_ARITHMETIC",
            "scope": "CROSS_CONTRACT_PROVENANCE_OF_SAMPLED_DIGITAL_BREP_CLEARANCE_NOT_CONTINUOUS_SWEPT_VOLUME_OR_PHYSICAL_VALIDATION",
        }
        payload["physical_validation_eligible"] = False
        payload["manifest_sha256"] = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        return payload


def build_retention_quick_release_tactile_v24() -> RetentionQuickReleaseTactileV24:
    prior = v23.build_retention_quick_release_tactile_v23()
    station_count, pose_count, digest = _station_binding(prior)
    return RetentionQuickReleaseTactileV24(prior, station_count, pose_count, digest).validate()
