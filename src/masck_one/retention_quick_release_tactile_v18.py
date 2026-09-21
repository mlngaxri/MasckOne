from __future__ import annotations

"""Retention quick-release V18: screen release-travel gaps between V12 stations.

V16 and V17 densify transverse coverage but both evaluate the same discrete V12 travel
stations. V18 preserves that evidence and independently evaluates the midpoint of every
adjacent travel interval against both aligned and interstitial transverse meshes. This
reduces a remaining sampled-motion blind spot without changing mechanism geometry.
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

SCHEMA = "MASCK_ONE_RETENTION_QUICK_RELEASE_TACTILE_V18"
SUPERSEDES_SCHEMA = v17.SCHEMA
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


class RetentionQuickReleaseTactileV18Error(ValueError):
    pass


def _midpoint_positions() -> tuple[float, ...]:
    positions = v12._canonical_positions()
    if len(positions) < 2 or any(b <= a for a, b in zip(positions, positions[1:])):
        raise RetentionQuickReleaseTactileV18Error("canonical release schedule cannot define travel midpoints")
    midpoints = tuple((a + b) / 2.0 for a, b in zip(positions, positions[1:]))
    if any(not (a < midpoint < b) for a, midpoint, b in zip(positions, midpoints, positions[1:])):
        raise RetentionQuickReleaseTactileV18Error("release midpoint escaped its canonical interval")
    return midpoints


def _travel_gap_evidence(mechanism: v1.RetentionQuickReleaseTactile) -> tuple[int, int, int, float, str]:
    aligned = v16._dense_samples(mechanism.rail_radial_clearance_mm, mechanism.anti_rotation_side_clearance_mm)
    interstitial = v17._interstitial_samples(mechanism.rail_radial_clearance_mm, mechanism.anti_rotation_side_clearance_mm)
    samples = aligned + interstitial
    midpoints = _midpoint_positions()
    records: list[tuple[str, str, str, str]] = []
    maximum = 0.0
    try:
        for y, z in samples:
            for x in midpoints:
                overlap = v1._intersection(mechanism.slider.translate((x, y, z)), mechanism.guide)
                if not math.isfinite(overlap) or overlap < 0.0:
                    raise RetentionQuickReleaseTactileV18Error("invalid travel-gap clearance evidence")
                if overlap > v1.TOL_MM3:
                    raise RetentionQuickReleaseTactileV18Error("travel-gap screen collides with rigid guide")
                maximum = max(maximum, overlap)
                records.append((format(x, ".12f"), format(y, ".12f"), format(z, ".12f"), format(overlap, ".12f")))
    except RetentionQuickReleaseTactileV18Error:
        raise
    except Exception as exc:
        raise RetentionQuickReleaseTactileV18Error("travel-gap clearance evidence query failed") from exc
    payload = json.dumps(records, separators=(",", ":"), ensure_ascii=True)
    return len(midpoints), len(samples), len(records), round(maximum, 12), sha256(payload.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class RetentionQuickReleaseTactileV18:
    prior: v17.RetentionQuickReleaseTactileV17
    travel_midpoint_count: int
    transverse_sample_count: int
    pose_count: int
    max_rigid_guide_intersection_mm3: float
    evidence_sha256: str

    def validate(self) -> "RetentionQuickReleaseTactileV18":
        self.prior.validate()
        mechanism = self.prior.prior.prior.prior.prior.prior.prior.mechanism
        midpoint_count, sample_count, pose_count, maximum, digest = _travel_gap_evidence(mechanism)
        if self.travel_midpoint_count != midpoint_count:
            raise RetentionQuickReleaseTactileV18Error("travel midpoint count is stale")
        if self.transverse_sample_count != sample_count:
            raise RetentionQuickReleaseTactileV18Error("travel-gap transverse sample count is stale")
        if self.pose_count != pose_count or pose_count != midpoint_count * sample_count:
            raise RetentionQuickReleaseTactileV18Error("travel-gap pose count is stale")
        if not math.isfinite(self.max_rigid_guide_intersection_mm3) or not math.isclose(self.max_rigid_guide_intersection_mm3, maximum, rel_tol=0.0, abs_tol=1e-12):
            raise RetentionQuickReleaseTactileV18Error("travel-gap maximum intersection is stale")
        if not _DIGEST_RE.fullmatch(self.evidence_sha256):
            raise RetentionQuickReleaseTactileV18Error("travel-gap digest must be canonical lowercase SHA-256")
        if self.evidence_sha256 != digest:
            raise RetentionQuickReleaseTactileV18Error("travel-gap evidence digest is stale")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        payload = self.prior.manifest()
        payload.pop("manifest_sha256", None)
        payload["schema"] = SCHEMA
        payload["supersedes_schema"] = SUPERSEDES_SCHEMA
        payload["interstitial_release_travel_screen"] = {
            "travel_midpoints_mm": list(_midpoint_positions()),
            "travel_midpoint_count": self.travel_midpoint_count,
            "transverse_sample_count": self.transverse_sample_count,
            "pose_count": self.pose_count,
            "max_rigid_guide_intersection_mm3": self.max_rigid_guide_intersection_mm3,
            "evidence_sha256": self.evidence_sha256,
            "criterion": "NO_POSITIVE_RIGID_GUIDE_INTERSECTION_AT_TRAVEL_MIDPOINT_TRANSVERSE_SAMPLES",
            "scope": "DIGITAL_BREP_SAMPLED_TRAVEL_GAP_SCREEN_NOT_CONTINUOUS_SWEPT_VOLUME_TOLERANCE_STACK_OR_PHYSICAL_VALIDATION",
        }
        payload["physical_validation_eligible"] = False
        payload["manifest_sha256"] = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        return payload


def build_retention_quick_release_tactile_v18() -> RetentionQuickReleaseTactileV18:
    prior = v17.build_retention_quick_release_tactile_v17()
    mechanism = prior.prior.prior.prior.prior.prior.prior.mechanism
    midpoint_count, sample_count, pose_count, maximum, digest = _travel_gap_evidence(mechanism)
    return RetentionQuickReleaseTactileV18(prior, midpoint_count, sample_count, pose_count, maximum, digest).validate()
