from __future__ import annotations

"""Retention quick-release V25: prove sampled transverse-domain boundary reach.

V24 binds travel stations to sampled clearance evidence. V25 independently audits the
transverse mesh itself so a future sampler refactor cannot silently shrink the screened
domain while retaining plausible counts and digests. This remains sampled digital
B-rep evidence, not continuous swept-volume, tolerance-stack, or physical proof.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import re

from . import retention_quick_release_tactile as v1
from . import retention_quick_release_tactile_v16 as v16
from . import retention_quick_release_tactile_v17 as v17
from . import retention_quick_release_tactile_v24 as v24

SCHEMA = "MASCK_ONE_RETENTION_QUICK_RELEASE_TACTILE_V25"
SUPERSEDES_SCHEMA = v24.SCHEMA
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_ABS_TOL = 1e-12


class RetentionQuickReleaseTactileV25Error(ValueError):
    pass


def _boundary_binding(prior: v24.RetentionQuickReleaseTactileV24) -> tuple[int, float, float, int, str]:
    # V1 constants are the owner-local clearance authority used to construct the mechanism.
    radial = float(v1.SPOOL_RAIL_RADIAL_CLEARANCE_MM)
    side = float(v1.ANTI_ROTATION_SIDE_CLEARANCE_MM)
    if not all(math.isfinite(value) and value > 0.0 for value in (radial, side)):
        raise RetentionQuickReleaseTactileV25Error("declared transverse clearance domain is invalid")

    aligned = v16._dense_samples(radial, side)
    interstitial = v17._interstitial_samples(radial, side)
    samples = aligned + interstitial
    if not samples:
        raise RetentionQuickReleaseTactileV25Error("transverse clearance mesh is empty")
    if any(math.hypot(y, z) > radial + _ABS_TOL or abs(y) > side + _ABS_TOL for y, z in samples):
        raise RetentionQuickReleaseTactileV25Error("transverse sample escaped declared clearance domain")

    max_abs_y = max(abs(y) for y, _ in samples)
    max_abs_z = max(abs(z) for _, z in samples)
    if not math.isclose(max_abs_y, min(side, radial), rel_tol=0.0, abs_tol=_ABS_TOL):
        raise RetentionQuickReleaseTactileV25Error("transverse mesh does not reach lateral clearance boundary")
    if not math.isclose(max_abs_z, radial, rel_tol=0.0, abs_tol=_ABS_TOL):
        raise RetentionQuickReleaseTactileV25Error("transverse mesh does not reach radial clearance boundary")

    quadrants = {
        (1 if y > _ABS_TOL else -1, 1 if z > _ABS_TOL else -1)
        for y, z in samples
        if abs(y) > _ABS_TOL and abs(z) > _ABS_TOL and v16._is_boundary(y, z, radial, side)
    }
    if quadrants != {(-1, -1), (-1, 1), (1, -1), (1, 1)}:
        raise RetentionQuickReleaseTactileV25Error("transverse boundary coverage is not four-quadrant symmetric")

    records = {
        "radial_clearance_mm": format(radial, ".12f"),
        "side_clearance_mm": format(side, ".12f"),
        "aligned_sample_count": len(aligned),
        "interstitial_sample_count": len(interstitial),
        "max_abs_y_mm": format(max_abs_y, ".12f"),
        "max_abs_z_mm": format(max_abs_z, ".12f"),
        "boundary_quadrants": sorted([list(item) for item in quadrants]),
    }
    digest = sha256(json.dumps(records, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()
    return len(samples), max_abs_y, max_abs_z, len(quadrants), digest


@dataclass(frozen=True, slots=True)
class RetentionQuickReleaseTactileV25:
    prior: v24.RetentionQuickReleaseTactileV24
    bound_transverse_sample_count: int
    bound_max_abs_y_mm: float
    bound_max_abs_z_mm: float
    bound_boundary_quadrant_count: int
    boundary_evidence_sha256: str

    def validate(self) -> "RetentionQuickReleaseTactileV25":
        self.prior.validate()
        count, max_y, max_z, quadrants, digest = _boundary_binding(self.prior)
        if self.bound_transverse_sample_count != count or count <= 0:
            raise RetentionQuickReleaseTactileV25Error("bound transverse sample count is stale")
        if not math.isclose(self.bound_max_abs_y_mm, max_y, rel_tol=0.0, abs_tol=_ABS_TOL):
            raise RetentionQuickReleaseTactileV25Error("bound lateral boundary reach is stale")
        if not math.isclose(self.bound_max_abs_z_mm, max_z, rel_tol=0.0, abs_tol=_ABS_TOL):
            raise RetentionQuickReleaseTactileV25Error("bound radial boundary reach is stale")
        if self.bound_boundary_quadrant_count != quadrants or quadrants != 4:
            raise RetentionQuickReleaseTactileV25Error("bound boundary quadrant coverage is stale")
        if not isinstance(self.boundary_evidence_sha256, str) or _DIGEST_RE.fullmatch(self.boundary_evidence_sha256) is None:
            raise RetentionQuickReleaseTactileV25Error("boundary evidence digest must be canonical lowercase SHA-256")
        if self.boundary_evidence_sha256 != digest:
            raise RetentionQuickReleaseTactileV25Error("boundary evidence digest is stale")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        payload = self.prior.manifest()
        payload.pop("manifest_sha256", None)
        payload["schema"] = SCHEMA
        payload["supersedes_schema"] = SUPERSEDES_SCHEMA
        payload["transverse_clearance_boundary_binding"] = {
            "bound_transverse_sample_count": self.bound_transverse_sample_count,
            "bound_max_abs_y_mm": self.bound_max_abs_y_mm,
            "bound_max_abs_z_mm": self.bound_max_abs_z_mm,
            "bound_boundary_quadrant_count": self.bound_boundary_quadrant_count,
            "boundary_evidence_sha256": self.boundary_evidence_sha256,
            "criterion": "SAMPLED_TRANSVERSE_MESH_REACHES_DECLARED_LATERAL_AND_RADIAL_BOUNDARIES_WITH_FOUR_QUADRANT_COVERAGE",
            "scope": "SAMPLED_DIGITAL_BREP_DOMAIN_COVERAGE_NOT_CONTINUOUS_SWEPT_VOLUME_TOLERANCE_STACK_OR_PHYSICAL_VALIDATION",
        }
        payload["physical_validation_eligible"] = False
        payload["manifest_sha256"] = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        return payload


def build_retention_quick_release_tactile_v25() -> RetentionQuickReleaseTactileV25:
    prior = v24.build_retention_quick_release_tactile_v24()
    count, max_y, max_z, quadrants, digest = _boundary_binding(prior)
    return RetentionQuickReleaseTactileV25(prior, count, max_y, max_z, quadrants, digest).validate()
