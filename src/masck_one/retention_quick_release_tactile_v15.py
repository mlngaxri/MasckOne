from __future__ import annotations

"""Retention quick-release V15: screen the full declared transverse clearance domain.

V14 binds sampled evidence only inside the inherited 80% transverse-clearance domain.
V15 closes that digital-screening gap by reusing the V8 boundary-aware transverse
sampler and V12/V11 travel schedule at the mechanism's full declared rail-radial and
anti-rotation side clearances. This is sampled digital B-rep evidence only. It is not
manufacturing, tolerance-stack, wear, contamination, force, or physical validation.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import re

from . import retention_quick_release_tactile as v1
from . import retention_quick_release_tactile_v8 as v8
from . import retention_quick_release_tactile_v12 as v12
from . import retention_quick_release_tactile_v14 as v14

SCHEMA = "MASCK_ONE_RETENTION_QUICK_RELEASE_TACTILE_V15"
SUPERSEDES_SCHEMA = v14.SCHEMA
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


class RetentionQuickReleaseTactileV15Error(ValueError):
    pass


def _full_domain_evidence(mechanism: v1.RetentionQuickReleaseTactile) -> tuple[int, int, float, str]:
    radial = mechanism.rail_radial_clearance_mm
    side = mechanism.anti_rotation_side_clearance_mm
    if not all(math.isfinite(value) and value > 0.0 for value in (radial, side)):
        raise RetentionQuickReleaseTactileV15Error("declared transverse clearances must be finite and positive")
    samples = v8._constrained_transverse_samples(radial, side)
    positions = v12._canonical_positions()
    boundary_count = sum(v8._is_boundary_sample(y, z, radial, side) for y, z in samples)
    records: list[tuple[str, str, str, str]] = []
    maximum = 0.0
    try:
        for y, z in samples:
            for x in positions:
                overlap = v1._intersection(mechanism.slider.translate((x, y, z)), mechanism.guide)
                if not math.isfinite(overlap) or overlap < 0.0:
                    raise RetentionQuickReleaseTactileV15Error("invalid full-domain clearance evidence")
                if overlap > v1.TOL_MM3:
                    raise RetentionQuickReleaseTactileV15Error("full declared clearance domain collides with rigid guide")
                maximum = max(maximum, overlap)
                records.append((format(x, ".12f"), format(y, ".12f"), format(z, ".12f"), format(overlap, ".12f")))
    except RetentionQuickReleaseTactileV15Error:
        raise
    except Exception as exc:
        raise RetentionQuickReleaseTactileV15Error("full-domain clearance evidence query failed") from exc
    payload = json.dumps(records, separators=(",", ":"), ensure_ascii=True)
    return len(records), boundary_count, round(maximum, 12), sha256(payload.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class RetentionQuickReleaseTactileV15:
    prior: v14.RetentionQuickReleaseTactileV14
    full_domain_pose_count: int
    full_domain_boundary_sample_count: int
    full_domain_max_rigid_guide_intersection_mm3: float
    full_domain_evidence_sha256: str

    def validate(self) -> "RetentionQuickReleaseTactileV15":
        self.prior.validate()
        mechanism = self.prior.prior.prior.prior.mechanism
        count, boundary_count, maximum, digest = _full_domain_evidence(mechanism)
        if self.full_domain_pose_count != count or count <= self.prior.sampled_pose_count:
            raise RetentionQuickReleaseTactileV15Error("full-domain pose count is stale or does not expand V14 evidence")
        if self.full_domain_boundary_sample_count != boundary_count or boundary_count < 4:
            raise RetentionQuickReleaseTactileV15Error("full-domain boundary evidence is stale")
        if not math.isfinite(self.full_domain_max_rigid_guide_intersection_mm3):
            raise RetentionQuickReleaseTactileV15Error("full-domain maximum intersection must be finite")
        if not math.isclose(self.full_domain_max_rigid_guide_intersection_mm3, maximum, rel_tol=0.0, abs_tol=1e-12):
            raise RetentionQuickReleaseTactileV15Error("full-domain maximum intersection is stale")
        if not _DIGEST_RE.fullmatch(self.full_domain_evidence_sha256):
            raise RetentionQuickReleaseTactileV15Error("full-domain digest must be canonical lowercase SHA-256")
        if self.full_domain_evidence_sha256 != digest:
            raise RetentionQuickReleaseTactileV15Error("full-domain evidence digest is stale")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        mechanism = self.prior.prior.prior.prior.mechanism
        payload = self.prior.manifest()
        payload.pop("manifest_sha256", None)
        payload["schema"] = SCHEMA
        payload["supersedes_schema"] = SUPERSEDES_SCHEMA
        payload["full_declared_transverse_clearance_screen"] = {
            "rail_radial_clearance_mm": mechanism.rail_radial_clearance_mm,
            "anti_rotation_side_clearance_mm": mechanism.anti_rotation_side_clearance_mm,
            "full_domain_pose_count": self.full_domain_pose_count,
            "full_domain_boundary_sample_count": self.full_domain_boundary_sample_count,
            "max_rigid_guide_intersection_mm3": self.full_domain_max_rigid_guide_intersection_mm3,
            "full_domain_evidence_sha256": self.full_domain_evidence_sha256,
            "criterion": "NO_POSITIVE_RIGID_GUIDE_INTERSECTION_ACROSS_SAMPLED_FULL_DECLARED_TRANSVERSE_CLEARANCE_DOMAIN",
            "scope": "DIGITAL_BREP_SAMPLED_FULL_CLEARANCE_SCREEN_NOT_TOLERANCE_STACK_CONTINUOUS_PROOF_OR_PHYSICAL_VALIDATION",
        }
        payload["physical_validation_eligible"] = False
        payload["manifest_sha256"] = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        return payload


def build_retention_quick_release_tactile_v15() -> RetentionQuickReleaseTactileV15:
    prior = v14.build_retention_quick_release_tactile_v14()
    mechanism = prior.prior.prior.prior.mechanism
    count, boundary_count, maximum, digest = _full_domain_evidence(mechanism)
    return RetentionQuickReleaseTactileV15(prior, count, boundary_count, maximum, digest).validate()
