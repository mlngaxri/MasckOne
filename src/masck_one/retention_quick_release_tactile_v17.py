from __future__ import annotations

"""Retention quick-release V17: screen interstitial gaps in the V16 polar mesh.

V16 densifies the declared transverse domain, but all angular samples remain on one
32-ray phase. V17 preserves V16 and independently samples radial and angular mid-cells
through the canonical V12 release schedule. This targets gaps between V16 rays/rings
without changing mechanism geometry. Evidence remains sampled digital B-rep evidence.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import re

from . import retention_quick_release_tactile as v1
from . import retention_quick_release_tactile_v12 as v12
from . import retention_quick_release_tactile_v16 as v16

SCHEMA = "MASCK_ONE_RETENTION_QUICK_RELEASE_TACTILE_V17"
SUPERSEDES_SCHEMA = v16.SCHEMA
INTERSTITIAL_RADII = tuple((index + 0.5) / 8.0 for index in range(8))
INTERSTITIAL_ANGLES = 32
ANGLE_PHASE_RAD = math.pi / INTERSTITIAL_ANGLES
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


class RetentionQuickReleaseTactileV17Error(ValueError):
    pass


def _interstitial_samples(radial: float, side: float) -> tuple[tuple[float, float], ...]:
    if not all(math.isfinite(value) and value > 0.0 for value in (radial, side)):
        raise RetentionQuickReleaseTactileV17Error("declared transverse clearances must be finite and positive")
    points: list[tuple[float, float]] = []
    for fraction in INTERSTITIAL_RADII:
        radius = radial * fraction
        for index in range(INTERSTITIAL_ANGLES):
            theta = ANGLE_PHASE_RAD + 2.0 * math.pi * index / INTERSTITIAL_ANGLES
            y, z = radius * math.cos(theta), radius * math.sin(theta)
            if abs(y) <= side + 1e-12:
                points.append((y, z))
    samples = tuple(points)
    if not samples:
        raise RetentionQuickReleaseTactileV17Error("interstitial screen produced no samples")
    if not all(math.hypot(y, z) < radial and abs(y) <= side + 1e-12 for y, z in samples):
        raise RetentionQuickReleaseTactileV17Error("interstitial sample escaped declared transverse domain")
    return samples


def _interstitial_evidence(mechanism: v1.RetentionQuickReleaseTactile) -> tuple[int, int, float, str]:
    samples = _interstitial_samples(mechanism.rail_radial_clearance_mm, mechanism.anti_rotation_side_clearance_mm)
    positions = v12._canonical_positions()
    records: list[tuple[str, str, str, str]] = []
    maximum = 0.0
    try:
        for y, z in samples:
            for x in positions:
                overlap = v1._intersection(mechanism.slider.translate((x, y, z)), mechanism.guide)
                if not math.isfinite(overlap) or overlap < 0.0:
                    raise RetentionQuickReleaseTactileV17Error("invalid interstitial clearance evidence")
                if overlap > v1.TOL_MM3:
                    raise RetentionQuickReleaseTactileV17Error("interstitial screen collides with rigid guide")
                maximum = max(maximum, overlap)
                records.append((format(x, ".12f"), format(y, ".12f"), format(z, ".12f"), format(overlap, ".12f")))
    except RetentionQuickReleaseTactileV17Error:
        raise
    except Exception as exc:
        raise RetentionQuickReleaseTactileV17Error("interstitial clearance evidence query failed") from exc
    payload = json.dumps(records, separators=(",", ":"), ensure_ascii=True)
    return len(samples), len(records), round(maximum, 12), sha256(payload.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class RetentionQuickReleaseTactileV17:
    prior: v16.RetentionQuickReleaseTactileV16
    interstitial_sample_count: int
    pose_count: int
    max_rigid_guide_intersection_mm3: float
    evidence_sha256: str

    def validate(self) -> "RetentionQuickReleaseTactileV17":
        self.prior.validate()
        mechanism = self.prior.prior.prior.prior.prior.prior.mechanism
        samples, poses, maximum, digest = _interstitial_evidence(mechanism)
        if self.interstitial_sample_count != samples:
            raise RetentionQuickReleaseTactileV17Error("interstitial sample count is stale")
        if self.pose_count != poses or poses != samples * len(v12._canonical_positions()):
            raise RetentionQuickReleaseTactileV17Error("interstitial pose count is stale")
        if not math.isfinite(self.max_rigid_guide_intersection_mm3) or not math.isclose(
            self.max_rigid_guide_intersection_mm3, maximum, rel_tol=0.0, abs_tol=1e-12
        ):
            raise RetentionQuickReleaseTactileV17Error("interstitial maximum intersection is stale")
        if not _DIGEST_RE.fullmatch(self.evidence_sha256):
            raise RetentionQuickReleaseTactileV17Error("interstitial digest must be canonical lowercase SHA-256")
        if self.evidence_sha256 != digest:
            raise RetentionQuickReleaseTactileV17Error("interstitial evidence digest is stale")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        payload = self.prior.manifest()
        payload.pop("manifest_sha256", None)
        payload["schema"] = SCHEMA
        payload["supersedes_schema"] = SUPERSEDES_SCHEMA
        payload["interstitial_full_declared_transverse_clearance_screen"] = {
            "radial_midpoints": list(INTERSTITIAL_RADII),
            "angular_rays": INTERSTITIAL_ANGLES,
            "angular_phase_rad": ANGLE_PHASE_RAD,
            "transverse_sample_count": self.interstitial_sample_count,
            "pose_count": self.pose_count,
            "max_rigid_guide_intersection_mm3": self.max_rigid_guide_intersection_mm3,
            "evidence_sha256": self.evidence_sha256,
            "criterion": "NO_POSITIVE_RIGID_GUIDE_INTERSECTION_AT_INTERSTITIAL_RADIAL_ANGULAR_SAMPLES",
            "scope": "DIGITAL_BREP_INTERSTITIAL_SAMPLED_SCREEN_NOT_CONTINUOUS_SWEPT_VOLUME_TOLERANCE_STACK_OR_PHYSICAL_VALIDATION",
        }
        payload["physical_validation_eligible"] = False
        payload["manifest_sha256"] = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        return payload


def build_retention_quick_release_tactile_v17() -> RetentionQuickReleaseTactileV17:
    prior = v16.build_retention_quick_release_tactile_v16()
    mechanism = prior.prior.prior.prior.prior.prior.mechanism
    samples, poses, maximum, digest = _interstitial_evidence(mechanism)
    return RetentionQuickReleaseTactileV17(prior, samples, poses, maximum, digest).validate()
