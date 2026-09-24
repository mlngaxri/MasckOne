from __future__ import annotations

"""Retention quick-release V19: screen quarter points inside every V12 travel interval.

V18 checks each interval midpoint. V19 preserves that evidence and independently checks
the 25% and 75% positions of every canonical interval against both dense aligned and
interstitial transverse meshes. This reduces the largest unscreened travel interval by
half again without changing mechanism geometry or interface authority.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import re

from . import retention_quick_release_tactile as v1
from . import retention_quick_release_tactile_v12 as v12
from . import retention_quick_release_tactile_v16 as v16
from . import retention_quick_release_tactile_v17 as v17
from . import retention_quick_release_tactile_v18 as v18

SCHEMA = "MASCK_ONE_RETENTION_QUICK_RELEASE_TACTILE_V19"
SUPERSEDES_SCHEMA = v18.SCHEMA
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


class RetentionQuickReleaseTactileV19Error(ValueError):
    pass


def _quarter_positions() -> tuple[float, ...]:
    positions = v12._canonical_positions()
    if len(positions) < 2 or any(b <= a for a, b in zip(positions, positions[1:])):
        raise RetentionQuickReleaseTactileV19Error("canonical release schedule cannot define quarter points")
    points: list[float] = []
    for a, b in zip(positions, positions[1:]):
        span = b - a
        q1, q3 = a + span * 0.25, a + span * 0.75
        if not (a < q1 < q3 < b):
            raise RetentionQuickReleaseTactileV19Error("release quarter point escaped its canonical interval")
        points.extend((q1, q3))
    return tuple(points)


def _quarter_gap_evidence(mechanism: v1.RetentionQuickReleaseTactile) -> tuple[int, int, int, float, str]:
    samples = v16._dense_samples(mechanism.rail_radial_clearance_mm, mechanism.anti_rotation_side_clearance_mm) + v17._interstitial_samples(mechanism.rail_radial_clearance_mm, mechanism.anti_rotation_side_clearance_mm)
    points = _quarter_positions()
    records: list[tuple[str, str, str, str]] = []
    maximum = 0.0
    try:
        for y, z in samples:
            for x in points:
                overlap = v1._intersection(mechanism.slider.translate((x, y, z)), mechanism.guide)
                if not math.isfinite(overlap) or overlap < 0.0:
                    raise RetentionQuickReleaseTactileV19Error("invalid quarter-gap clearance evidence")
                if overlap > v1.TOL_MM3:
                    raise RetentionQuickReleaseTactileV19Error("quarter-gap screen collides with rigid guide")
                maximum = max(maximum, overlap)
                records.append((format(x, ".12f"), format(y, ".12f"), format(z, ".12f"), format(overlap, ".12f")))
    except RetentionQuickReleaseTactileV19Error:
        raise
    except Exception as exc:
        raise RetentionQuickReleaseTactileV19Error("quarter-gap clearance evidence query failed") from exc
    payload = json.dumps(records, separators=(",", ":"), ensure_ascii=True)
    return len(points), len(samples), len(records), round(maximum, 12), sha256(payload.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class RetentionQuickReleaseTactileV19:
    prior: v18.RetentionQuickReleaseTactileV18
    travel_quarter_point_count: int
    transverse_sample_count: int
    pose_count: int
    max_rigid_guide_intersection_mm3: float
    evidence_sha256: str

    def validate(self) -> "RetentionQuickReleaseTactileV19":
        self.prior.validate()
        mechanism = self.prior.prior.prior.prior.prior.prior.prior.prior.mechanism
        point_count, sample_count, pose_count, maximum, digest = _quarter_gap_evidence(mechanism)
        if self.travel_quarter_point_count != point_count:
            raise RetentionQuickReleaseTactileV19Error("travel quarter-point count is stale")
        if self.transverse_sample_count != sample_count:
            raise RetentionQuickReleaseTactileV19Error("quarter-gap transverse sample count is stale")
        if self.pose_count != pose_count or pose_count != point_count * sample_count:
            raise RetentionQuickReleaseTactileV19Error("quarter-gap pose count is stale")
        if not math.isfinite(self.max_rigid_guide_intersection_mm3) or not math.isclose(self.max_rigid_guide_intersection_mm3, maximum, rel_tol=0.0, abs_tol=1e-12):
            raise RetentionQuickReleaseTactileV19Error("quarter-gap maximum intersection is stale")
        if not _DIGEST_RE.fullmatch(self.evidence_sha256):
            raise RetentionQuickReleaseTactileV19Error("quarter-gap digest must be canonical lowercase SHA-256")
        if self.evidence_sha256 != digest:
            raise RetentionQuickReleaseTactileV19Error("quarter-gap evidence digest is stale")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        payload = self.prior.manifest()
        payload.pop("manifest_sha256", None)
        payload["schema"] = SCHEMA
        payload["supersedes_schema"] = SUPERSEDES_SCHEMA
        payload["quarter_release_travel_screen"] = {
            "travel_quarter_points_mm": list(_quarter_positions()),
            "travel_quarter_point_count": self.travel_quarter_point_count,
            "transverse_sample_count": self.transverse_sample_count,
            "pose_count": self.pose_count,
            "max_rigid_guide_intersection_mm3": self.max_rigid_guide_intersection_mm3,
            "evidence_sha256": self.evidence_sha256,
            "criterion": "NO_POSITIVE_RIGID_GUIDE_INTERSECTION_AT_TRAVEL_QUARTER_POINT_TRANSVERSE_SAMPLES",
            "scope": "DIGITAL_BREP_SAMPLED_TRAVEL_GAP_SCREEN_NOT_CONTINUOUS_SWEPT_VOLUME_TOLERANCE_STACK_OR_PHYSICAL_VALIDATION",
        }
        payload["physical_validation_eligible"] = False
        payload["manifest_sha256"] = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        return payload


def build_retention_quick_release_tactile_v19() -> RetentionQuickReleaseTactileV19:
    prior = v18.build_retention_quick_release_tactile_v18()
    mechanism = prior.prior.prior.prior.prior.prior.prior.prior.mechanism
    point_count, sample_count, pose_count, maximum, digest = _quarter_gap_evidence(mechanism)
    return RetentionQuickReleaseTactileV19(prior, point_count, sample_count, pose_count, maximum, digest).validate()
