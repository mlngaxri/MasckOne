from __future__ import annotations

"""V29: screen the accepted maximum transverse-clearance envelope.

V16/V17 densely sample the nominal realized guidance clearances. V29 adds a conservative
digital packaging screen at the existing maximum accepted radial and anti-rotation side
clearances, across the canonical V12 release schedule. This does not change mechanism
geometry or claim a manufacturing tolerance stack; it fails closed if the current rigid
guide cannot accommodate the already-declared clearance limits at sampled poses.
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
from . import retention_quick_release_tactile_v28 as v28

SCHEMA = "MASCK_ONE_RETENTION_QUICK_RELEASE_TACTILE_V29"
SUPERSEDES_SCHEMA = v28.SCHEMA
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


class RetentionQuickReleaseTactileV29Error(ValueError):
    pass


def _worst_case_clearance_evidence() -> tuple[int, int, float, str]:
    mechanism = v1.build_retention_quick_release_tactile()
    radial = float(v1.MAX_SPOOL_RAIL_RADIAL_CLEARANCE_MM)
    side = float(v1.MAX_ANTI_ROTATION_SIDE_CLEARANCE_MM)
    if radial < mechanism.rail_radial_clearance_mm or side < mechanism.anti_rotation_side_clearance_mm:
        raise RetentionQuickReleaseTactileV29Error("maximum clearance authority fell below nominal mechanism clearance")

    aligned = v16._dense_samples(radial, side)
    interstitial = v17._interstitial_samples(radial, side)
    positions = v12._canonical_positions()
    records: list[tuple[str, str, str, str, str]] = []
    maximum = 0.0
    try:
        for family, samples in (("aligned", aligned), ("interstitial", interstitial)):
            for y, z in samples:
                for x in positions:
                    overlap = v1._intersection(mechanism.slider.translate((x, y, z)), mechanism.guide)
                    if not math.isfinite(overlap) or overlap < 0.0:
                        raise RetentionQuickReleaseTactileV29Error("invalid worst-case clearance evidence")
                    if overlap > v1.TOL_MM3:
                        raise RetentionQuickReleaseTactileV29Error("accepted maximum transverse clearance collides with rigid guide")
                    maximum = max(maximum, overlap)
                    records.append((family, format(x, ".12f"), format(y, ".12f"), format(z, ".12f"), format(overlap, ".12f")))
    except RetentionQuickReleaseTactileV29Error:
        raise
    except Exception as exc:
        raise RetentionQuickReleaseTactileV29Error("worst-case clearance evidence query failed") from exc

    digest_payload = {
        "radial_clearance_mm": format(radial, ".12f"),
        "side_clearance_mm": format(side, ".12f"),
        "records": records,
    }
    digest = sha256(json.dumps(digest_payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return len(aligned) + len(interstitial), len(records), round(maximum, 12), digest


@dataclass(frozen=True, slots=True)
class RetentionQuickReleaseTactileV29:
    prior: v28.RetentionQuickReleaseTactileV28
    transverse_sample_count: int
    pose_count: int
    max_rigid_guide_intersection_mm3: float
    evidence_sha256: str

    def validate(self) -> "RetentionQuickReleaseTactileV29":
        self.prior.validate()
        samples, poses, maximum, digest = _worst_case_clearance_evidence()
        if self.transverse_sample_count != samples:
            raise RetentionQuickReleaseTactileV29Error("worst-case transverse sample count is stale")
        if self.pose_count != poses or poses != samples * len(v12._canonical_positions()):
            raise RetentionQuickReleaseTactileV29Error("worst-case pose count is stale")
        if not math.isfinite(self.max_rigid_guide_intersection_mm3) or self.max_rigid_guide_intersection_mm3 != maximum:
            raise RetentionQuickReleaseTactileV29Error("worst-case maximum intersection is stale")
        if maximum > v1.TOL_MM3:
            raise RetentionQuickReleaseTactileV29Error("worst-case rigid-guide intersection must remain zero")
        if not isinstance(self.evidence_sha256, str) or _DIGEST_RE.fullmatch(self.evidence_sha256) is None:
            raise RetentionQuickReleaseTactileV29Error("worst-case evidence digest must be canonical lowercase SHA-256")
        if self.evidence_sha256 != digest:
            raise RetentionQuickReleaseTactileV29Error("worst-case evidence digest is stale")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        payload = self.prior.manifest()
        payload.pop("manifest_sha256", None)
        payload["schema"] = SCHEMA
        payload["supersedes_schema"] = SUPERSEDES_SCHEMA
        payload["maximum_accepted_transverse_clearance_screen"] = {
            "radial_clearance_mm": v1.MAX_SPOOL_RAIL_RADIAL_CLEARANCE_MM,
            "anti_rotation_side_clearance_mm": v1.MAX_ANTI_ROTATION_SIDE_CLEARANCE_MM,
            "transverse_sample_count": self.transverse_sample_count,
            "pose_count": self.pose_count,
            "max_rigid_guide_intersection_mm3": self.max_rigid_guide_intersection_mm3,
            "evidence_sha256": self.evidence_sha256,
            "criterion": "NO_POSITIVE_RIGID_GUIDE_INTERSECTION_AT_ACCEPTED_MAXIMUM_TRANSVERSE_CLEARANCE_SAMPLES",
            "scope": "CONSERVATIVE_SAMPLED_DIGITAL_BREP_CLEARANCE_SCREEN_NOT_MANUFACTURING_TOLERANCE_STACK_OR_PHYSICAL_VALIDATION",
        }
        payload["physical_validation_eligible"] = False
        payload["manifest_sha256"] = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        return payload


def build_retention_quick_release_tactile_v29() -> RetentionQuickReleaseTactileV29:
    prior = v28.build_retention_quick_release_tactile_v28()
    samples, poses, maximum, digest = _worst_case_clearance_evidence()
    return RetentionQuickReleaseTactileV29(prior, samples, poses, maximum, digest).validate()
