from __future__ import annotations

"""Retention quick-release V16: densify the full transverse clearance screen.

V15 reaches the full declared transverse-clearance boundary but inherits V8's five
radial rings and 16 angular rays. V16 retains V15 unchanged and independently screens
the same full domain with nine radial rings and 32 angular rays through the canonical
V12 release schedule. This reduces unscreened transverse spacing without changing
mechanism geometry. Evidence remains sampled digital B-rep evidence, not continuous
swept-volume, manufacturing, tolerance-stack, wear, force, or physical validation.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import re

from . import retention_quick_release_tactile as v1
from . import retention_quick_release_tactile_v12 as v12
from . import retention_quick_release_tactile_v15 as v15

SCHEMA = "MASCK_ONE_RETENTION_QUICK_RELEASE_TACTILE_V16"
SUPERSEDES_SCHEMA = v15.SCHEMA
POLAR_RADII = tuple(index / 8.0 for index in range(9))
POLAR_ANGLES = 32
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


class RetentionQuickReleaseTactileV16Error(ValueError):
    pass


def _dedupe(points: list[tuple[float, float]]) -> tuple[tuple[float, float], ...]:
    unique: dict[tuple[int, int], tuple[float, float]] = {}
    for y, z in points:
        unique[(round(y * 1e9), round(z * 1e9))] = (y, z)
    return tuple(unique[key] for key in sorted(unique))


def _dense_samples(radial: float, side: float) -> tuple[tuple[float, float], ...]:
    if not all(math.isfinite(value) and value > 0.0 for value in (radial, side)):
        raise RetentionQuickReleaseTactileV16Error("declared transverse clearances must be finite and positive")
    points: list[tuple[float, float]] = [(0.0, 0.0)]
    for fraction in POLAR_RADII[1:]:
        radius = radial * fraction
        for index in range(POLAR_ANGLES):
            theta = 2.0 * math.pi * index / POLAR_ANGLES
            y, z = radius * math.cos(theta), radius * math.sin(theta)
            if abs(y) <= side + 1e-12:
                points.append((y, z))
    clipped_side = min(side, radial)
    points.extend(((clipped_side, 0.0), (-clipped_side, 0.0)))
    if side < radial:
        z_intersection = math.sqrt(max(0.0, radial * radial - side * side))
        points.extend(
            (
                (side, z_intersection),
                (side, -z_intersection),
                (-side, z_intersection),
                (-side, -z_intersection),
            )
        )
    samples = _dedupe(points)
    if not all(math.hypot(y, z) <= radial + 1e-12 and abs(y) <= side + 1e-12 for y, z in samples):
        raise RetentionQuickReleaseTactileV16Error("dense sample escaped declared transverse domain")
    return samples


def _is_boundary(y: float, z: float, radial: float, side: float) -> bool:
    return math.isclose(math.hypot(y, z), radial, rel_tol=0.0, abs_tol=1e-9) or math.isclose(
        abs(y), min(side, radial), rel_tol=0.0, abs_tol=1e-9
    )


def _dense_evidence(mechanism: v1.RetentionQuickReleaseTactile) -> tuple[int, int, int, float, str]:
    radial = mechanism.rail_radial_clearance_mm
    side = mechanism.anti_rotation_side_clearance_mm
    samples = _dense_samples(radial, side)
    positions = v12._canonical_positions()
    boundary_count = sum(_is_boundary(y, z, radial, side) for y, z in samples)
    records: list[tuple[str, str, str, str]] = []
    maximum = 0.0
    try:
        for y, z in samples:
            for x in positions:
                overlap = v1._intersection(mechanism.slider.translate((x, y, z)), mechanism.guide)
                if not math.isfinite(overlap) or overlap < 0.0:
                    raise RetentionQuickReleaseTactileV16Error("invalid dense clearance evidence")
                if overlap > v1.TOL_MM3:
                    raise RetentionQuickReleaseTactileV16Error("dense full-domain screen collides with rigid guide")
                maximum = max(maximum, overlap)
                records.append((format(x, ".12f"), format(y, ".12f"), format(z, ".12f"), format(overlap, ".12f")))
    except RetentionQuickReleaseTactileV16Error:
        raise
    except Exception as exc:
        raise RetentionQuickReleaseTactileV16Error("dense clearance evidence query failed") from exc
    payload = json.dumps(records, separators=(",", ":"), ensure_ascii=True)
    return len(samples), len(records), boundary_count, round(maximum, 12), sha256(payload.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class RetentionQuickReleaseTactileV16:
    prior: v15.RetentionQuickReleaseTactileV15
    transverse_sample_count: int
    pose_count: int
    boundary_sample_count: int
    max_rigid_guide_intersection_mm3: float
    evidence_sha256: str

    def validate(self) -> "RetentionQuickReleaseTactileV16":
        self.prior.validate()
        mechanism = self.prior.prior.prior.prior.prior.mechanism
        samples, poses, boundary, maximum, digest = _dense_evidence(mechanism)
        inherited_transverse = self.prior.full_domain_pose_count // len(v12._canonical_positions())
        if samples <= inherited_transverse:
            raise RetentionQuickReleaseTactileV16Error("dense screen must increase transverse sample density")
        if self.transverse_sample_count != samples:
            raise RetentionQuickReleaseTactileV16Error("dense transverse sample count is stale")
        if self.pose_count != poses or poses != samples * len(v12._canonical_positions()):
            raise RetentionQuickReleaseTactileV16Error("dense pose count is stale")
        if self.boundary_sample_count != boundary or boundary < self.prior.full_domain_boundary_sample_count:
            raise RetentionQuickReleaseTactileV16Error("dense boundary evidence is stale")
        if not math.isfinite(self.max_rigid_guide_intersection_mm3) or not math.isclose(
            self.max_rigid_guide_intersection_mm3, maximum, rel_tol=0.0, abs_tol=1e-12
        ):
            raise RetentionQuickReleaseTactileV16Error("dense maximum intersection is stale")
        if not _DIGEST_RE.fullmatch(self.evidence_sha256):
            raise RetentionQuickReleaseTactileV16Error("dense digest must be canonical lowercase SHA-256")
        if self.evidence_sha256 != digest:
            raise RetentionQuickReleaseTactileV16Error("dense evidence digest is stale")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        payload = self.prior.manifest()
        payload.pop("manifest_sha256", None)
        payload["schema"] = SCHEMA
        payload["supersedes_schema"] = SUPERSEDES_SCHEMA
        payload["dense_full_declared_transverse_clearance_screen"] = {
            "polar_radii": list(POLAR_RADII),
            "polar_angles": POLAR_ANGLES,
            "transverse_sample_count": self.transverse_sample_count,
            "pose_count": self.pose_count,
            "boundary_sample_count": self.boundary_sample_count,
            "max_rigid_guide_intersection_mm3": self.max_rigid_guide_intersection_mm3,
            "evidence_sha256": self.evidence_sha256,
            "criterion": "NO_POSITIVE_RIGID_GUIDE_INTERSECTION_ACROSS_DENSE_SAMPLED_FULL_DECLARED_TRANSVERSE_CLEARANCE_DOMAIN",
            "scope": "DIGITAL_BREP_DENSE_SAMPLED_SCREEN_NOT_CONTINUOUS_SWEPT_VOLUME_TOLERANCE_STACK_OR_PHYSICAL_VALIDATION",
        }
        payload["physical_validation_eligible"] = False
        payload["manifest_sha256"] = sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()
        return payload


def build_retention_quick_release_tactile_v16() -> RetentionQuickReleaseTactileV16:
    prior = v15.build_retention_quick_release_tactile_v15()
    mechanism = prior.prior.prior.prior.prior.mechanism
    samples, poses, boundary, maximum, digest = _dense_evidence(mechanism)
    return RetentionQuickReleaseTactileV16(prior, samples, poses, boundary, maximum, digest).validate()
