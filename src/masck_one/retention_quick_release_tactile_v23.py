from __future__ import annotations

"""Retention quick-release V23: bind travel-grid coverage to clearance evidence.

V22 proves schedule completeness. V23 closes the complementary provenance gap by
requiring every interior schedule family to carry non-empty sampled B-rep clearance
evidence and binding those family digests, pose counts and maxima into one audit.
This remains sampled digital evidence, not continuous swept-volume or physical proof.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import re

from . import retention_quick_release_tactile_v22 as v22

SCHEMA = "MASCK_ONE_RETENTION_QUICK_RELEASE_TACTILE_V23"
SUPERSEDES_SCHEMA = v22.SCHEMA
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_FAMILIES = (
    "interstitial_release_travel_screen",
    "quarter_release_travel_screen",
    "eighth_release_travel_screen",
    "sixteenth_release_travel_screen",
)


class RetentionQuickReleaseTactileV23Error(ValueError):
    pass


def _evidence_binding(prior: v22.RetentionQuickReleaseTactileV22) -> tuple[int, int, float, str]:
    manifest = prior.prior.manifest()
    records: list[dict[str, object]] = []
    total_poses = 0
    maximum = 0.0
    for family in _FAMILIES:
        evidence = manifest.get(family)
        if not isinstance(evidence, dict):
            raise RetentionQuickReleaseTactileV23Error(f"missing clearance evidence family {family}")
        pose_count = evidence.get("pose_count")
        sample_count = evidence.get("transverse_sample_count")
        digest = evidence.get("evidence_sha256")
        overlap = evidence.get("max_rigid_guide_intersection_mm3")
        if isinstance(pose_count, bool) or not isinstance(pose_count, int) or pose_count <= 0:
            raise RetentionQuickReleaseTactileV23Error(f"{family} pose count must be positive")
        if isinstance(sample_count, bool) or not isinstance(sample_count, int) or sample_count <= 0:
            raise RetentionQuickReleaseTactileV23Error(f"{family} transverse sample count must be positive")
        if not isinstance(digest, str) or _DIGEST_RE.fullmatch(digest) is None:
            raise RetentionQuickReleaseTactileV23Error(f"{family} evidence digest is invalid")
        if isinstance(overlap, bool) or not isinstance(overlap, (int, float)) or not math.isfinite(float(overlap)) or float(overlap) < 0.0:
            raise RetentionQuickReleaseTactileV23Error(f"{family} maximum intersection is invalid")
        total_poses += pose_count
        maximum = max(maximum, float(overlap))
        records.append({"family": family, "pose_count": pose_count, "transverse_sample_count": sample_count, "max_rigid_guide_intersection_mm3": format(float(overlap), ".12f"), "evidence_sha256": digest})
    digest = sha256(json.dumps(records, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()
    return len(records), total_poses, round(maximum, 12), digest


@dataclass(frozen=True, slots=True)
class RetentionQuickReleaseTactileV23:
    prior: v22.RetentionQuickReleaseTactileV22
    bound_family_count: int
    bound_pose_count: int
    maximum_bound_intersection_mm3: float
    clearance_evidence_sha256: str

    def validate(self) -> "RetentionQuickReleaseTactileV23":
        self.prior.validate()
        family_count, pose_count, maximum, digest = _evidence_binding(self.prior)
        if self.bound_family_count != family_count or family_count != len(_FAMILIES):
            raise RetentionQuickReleaseTactileV23Error("clearance evidence family count is stale")
        if self.bound_pose_count != pose_count or pose_count <= 0:
            raise RetentionQuickReleaseTactileV23Error("bound clearance pose count is stale")
        if not math.isfinite(self.maximum_bound_intersection_mm3) or not math.isclose(self.maximum_bound_intersection_mm3, maximum, rel_tol=0.0, abs_tol=1e-12):
            raise RetentionQuickReleaseTactileV23Error("bound maximum intersection is stale")
        if not _DIGEST_RE.fullmatch(self.clearance_evidence_sha256):
            raise RetentionQuickReleaseTactileV23Error("clearance evidence digest must be canonical lowercase SHA-256")
        if self.clearance_evidence_sha256 != digest:
            raise RetentionQuickReleaseTactileV23Error("clearance evidence digest is stale")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        payload = self.prior.manifest()
        payload.pop("manifest_sha256", None)
        payload["schema"] = SCHEMA
        payload["supersedes_schema"] = SUPERSEDES_SCHEMA
        payload["sixteenth_grid_clearance_evidence_binding"] = {
            "families": list(_FAMILIES),
            "bound_family_count": self.bound_family_count,
            "bound_pose_count": self.bound_pose_count,
            "maximum_bound_intersection_mm3": self.maximum_bound_intersection_mm3,
            "clearance_evidence_sha256": self.clearance_evidence_sha256,
            "criterion": "COMPLETE_INTERIOR_SIXTEENTH_GRID_SCHEDULE_FAMILIES_CARRY_BOUND_NONEMPTY_CLEARANCE_EVIDENCE",
            "scope": "PROVENANCE_BINDING_OF_SAMPLED_DIGITAL_BREP_CLEARANCE_NOT_CONTINUOUS_SWEPT_VOLUME_TOLERANCE_STACK_OR_PHYSICAL_VALIDATION",
        }
        payload["physical_validation_eligible"] = False
        payload["manifest_sha256"] = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        return payload


def build_retention_quick_release_tactile_v23() -> RetentionQuickReleaseTactileV23:
    prior = v22.build_retention_quick_release_tactile_v22()
    family_count, pose_count, maximum, digest = _evidence_binding(prior)
    return RetentionQuickReleaseTactileV23(prior, family_count, pose_count, maximum, digest).validate()
