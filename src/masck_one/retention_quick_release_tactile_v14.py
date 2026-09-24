from __future__ import annotations

"""Retention quick-release V14: bind the complete sampled clearance pose evidence.

V13 proves the release-station topology, while V11 screens the V8 transverse domain
through every eighth-interval travel station. V14 makes that sampled evidence auditable
as one canonical SHA-256 identity over every pose coordinate and measured rigid-guide
intersection. This remains sampled digital B-rep evidence, not continuous or physical
validation.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import re

from . import retention_quick_release_tactile as v1
from . import retention_quick_release_tactile_v8 as v8
from . import retention_quick_release_tactile_v11 as v11
from . import retention_quick_release_tactile_v12 as v12
from . import retention_quick_release_tactile_v13 as v13

SCHEMA = "MASCK_ONE_RETENTION_QUICK_RELEASE_TACTILE_V14"
SUPERSEDES_SCHEMA = v13.SCHEMA
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


class RetentionQuickReleaseTactileV14Error(ValueError):
    pass


def _pose_evidence(mechanism: v1.RetentionQuickReleaseTactile, radial_limit_mm: float, side_limit_mm: float) -> tuple[int, float, str]:
    samples = v8._constrained_transverse_samples(radial_limit_mm, side_limit_mm)
    positions = v12._canonical_positions()
    records: list[tuple[str, str, str, str]] = []
    maximum = 0.0
    try:
        for y, z in samples:
            for x in positions:
                overlap = v1._intersection(mechanism.slider.translate((x, y, z)), mechanism.guide)
                if not math.isfinite(overlap) or overlap < 0.0:
                    raise RetentionQuickReleaseTactileV14Error("invalid sampled clearance evidence")
                if overlap > v1.TOL_MM3:
                    raise RetentionQuickReleaseTactileV14Error("sampled rigid-guide collision exceeds tolerance")
                maximum = max(maximum, overlap)
                records.append((format(x, ".12f"), format(y, ".12f"), format(z, ".12f"), format(overlap, ".12f")))
    except RetentionQuickReleaseTactileV14Error:
        raise
    except Exception as exc:
        raise RetentionQuickReleaseTactileV14Error("sampled clearance evidence query failed") from exc
    payload = json.dumps(records, separators=(",", ":"), ensure_ascii=True)
    return len(records), round(maximum, 12), sha256(payload.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class RetentionQuickReleaseTactileV14:
    prior: v13.RetentionQuickReleaseTactileV13
    sampled_pose_count: int
    max_rigid_guide_intersection_mm3: float
    sampled_pose_evidence_sha256: str

    def validate(self) -> "RetentionQuickReleaseTactileV14":
        self.prior.validate()
        mechanism = self.prior.prior.prior.mechanism
        radial = self.prior.prior.prior.radial_limit_mm
        side = self.prior.prior.prior.side_limit_mm
        count, maximum, digest = _pose_evidence(mechanism, radial, side)
        if self.sampled_pose_count != count or count != self.prior.prior.prior.total_pose_count:
            raise RetentionQuickReleaseTactileV14Error("sampled pose count is stale")
        if not math.isfinite(self.max_rigid_guide_intersection_mm3):
            raise RetentionQuickReleaseTactileV14Error("sampled maximum intersection must be finite")
        if not math.isclose(self.max_rigid_guide_intersection_mm3, maximum, rel_tol=0.0, abs_tol=1e-12):
            raise RetentionQuickReleaseTactileV14Error("sampled maximum intersection is stale")
        if not _DIGEST_RE.fullmatch(self.sampled_pose_evidence_sha256):
            raise RetentionQuickReleaseTactileV14Error("sampled pose digest must be canonical lowercase SHA-256")
        if self.sampled_pose_evidence_sha256 != digest:
            raise RetentionQuickReleaseTactileV14Error("sampled pose evidence digest is stale")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        payload = self.prior.manifest()
        payload.pop("manifest_sha256", None)
        payload["schema"] = SCHEMA
        payload["supersedes_schema"] = SUPERSEDES_SCHEMA
        payload["sampled_clearance_pose_evidence"] = {
            "sampled_pose_count": self.sampled_pose_count,
            "max_rigid_guide_intersection_mm3": self.max_rigid_guide_intersection_mm3,
            "sampled_pose_evidence_sha256": self.sampled_pose_evidence_sha256,
            "criterion": "CANONICAL_SHA256_BINDS_EVERY_V8_TRANSVERSE_BY_V11_TRAVEL_POSE_AND_INTERSECTION",
            "scope": "DIGITAL_BREP_SAMPLED_CLEARANCE_EVIDENCE_NOT_CONTINUOUS_PROOF_OR_PHYSICAL_VALIDATION",
        }
        payload["physical_validation_eligible"] = False
        payload["manifest_sha256"] = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        return payload


def build_retention_quick_release_tactile_v14() -> RetentionQuickReleaseTactileV14:
    prior = v13.build_retention_quick_release_tactile_v13()
    mechanism = prior.prior.prior.mechanism
    radial = prior.prior.prior.radial_limit_mm
    side = prior.prior.prior.side_limit_mm
    count, maximum, digest = _pose_evidence(mechanism, radial, side)
    return RetentionQuickReleaseTactileV14(prior, count, maximum, digest).validate()
