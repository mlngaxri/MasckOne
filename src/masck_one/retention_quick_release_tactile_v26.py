from __future__ import annotations

"""Retention quick-release V26: bind transverse mesh uniqueness and inversion symmetry.

V25 proves boundary reach. V26 closes a complementary provenance gap: raw sample counts
must represent distinct transverse poses, and both aligned and interstitial families must
retain central inversion symmetry. This remains sampled digital B-rep evidence.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import re

from . import retention_quick_release_tactile as v1
from . import retention_quick_release_tactile_v16 as v16
from . import retention_quick_release_tactile_v17 as v17
from . import retention_quick_release_tactile_v25 as v25

SCHEMA = "MASCK_ONE_RETENTION_QUICK_RELEASE_TACTILE_V26"
SUPERSEDES_SCHEMA = v25.SCHEMA
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_QUANTUM = 10**12


class RetentionQuickReleaseTactileV26Error(ValueError):
    pass


def _key(point: tuple[float, float]) -> tuple[int, int]:
    y, z = point
    if not (math.isfinite(y) and math.isfinite(z)):
        raise RetentionQuickReleaseTactileV26Error("transverse mesh contains non-finite coordinate")
    return round(y * _QUANTUM), round(z * _QUANTUM)


def _audit_family(name: str, samples: tuple[tuple[float, float], ...]) -> tuple[int, str]:
    keys = tuple(_key(point) for point in samples)
    keyset = set(keys)
    if len(keyset) != len(keys):
        raise RetentionQuickReleaseTactileV26Error(f"{name} transverse mesh contains duplicate poses")
    missing_inverse = sorted(key for key in keyset if (-key[0], -key[1]) not in keyset)
    if missing_inverse:
        raise RetentionQuickReleaseTactileV26Error(f"{name} transverse mesh lost central inversion symmetry")
    canonical = sorted(keyset)
    digest = sha256(json.dumps(canonical, separators=(",", ":")).encode()).hexdigest()
    return len(keyset), digest


def _mesh_binding() -> tuple[int, int, int, str]:
    radial = float(v1.SPOOL_RAIL_RADIAL_CLEARANCE_MM)
    side = float(v1.ANTI_ROTATION_SIDE_CLEARANCE_MM)
    aligned = v16._dense_samples(radial, side)
    interstitial = v17._interstitial_samples(radial, side)
    aligned_count, aligned_digest = _audit_family("aligned", aligned)
    interstitial_count, interstitial_digest = _audit_family("interstitial", interstitial)
    aligned_keys = {_key(point) for point in aligned}
    interstitial_keys = {_key(point) for point in interstitial}
    overlap = aligned_keys & interstitial_keys
    if overlap:
        raise RetentionQuickReleaseTactileV26Error("aligned and interstitial transverse meshes overlap")
    records = {
        "aligned_unique_count": aligned_count,
        "interstitial_unique_count": interstitial_count,
        "combined_unique_count": len(aligned_keys | interstitial_keys),
        "aligned_sha256": aligned_digest,
        "interstitial_sha256": interstitial_digest,
    }
    digest = sha256(json.dumps(records, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return aligned_count, interstitial_count, records["combined_unique_count"], digest


@dataclass(frozen=True, slots=True)
class RetentionQuickReleaseTactileV26:
    prior: v25.RetentionQuickReleaseTactileV25
    aligned_unique_count: int
    interstitial_unique_count: int
    combined_unique_count: int
    mesh_identity_sha256: str

    def validate(self) -> "RetentionQuickReleaseTactileV26":
        self.prior.validate()
        aligned, interstitial, combined, digest = _mesh_binding()
        if self.aligned_unique_count != aligned:
            raise RetentionQuickReleaseTactileV26Error("bound aligned unique count is stale")
        if self.interstitial_unique_count != interstitial:
            raise RetentionQuickReleaseTactileV26Error("bound interstitial unique count is stale")
        if self.combined_unique_count != combined or combined != self.prior.bound_transverse_sample_count:
            raise RetentionQuickReleaseTactileV26Error("bound combined unique count is stale")
        if not isinstance(self.mesh_identity_sha256, str) or _DIGEST_RE.fullmatch(self.mesh_identity_sha256) is None:
            raise RetentionQuickReleaseTactileV26Error("mesh identity digest must be canonical lowercase SHA-256")
        if self.mesh_identity_sha256 != digest:
            raise RetentionQuickReleaseTactileV26Error("mesh identity digest is stale")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        payload = self.prior.manifest()
        payload.pop("manifest_sha256", None)
        payload["schema"] = SCHEMA
        payload["supersedes_schema"] = SUPERSEDES_SCHEMA
        payload["transverse_mesh_identity_binding"] = {
            "aligned_unique_count": self.aligned_unique_count,
            "interstitial_unique_count": self.interstitial_unique_count,
            "combined_unique_count": self.combined_unique_count,
            "mesh_identity_sha256": self.mesh_identity_sha256,
            "criterion": "TRANSVERSE_SAMPLE_FAMILIES_ARE_UNIQUE_DISJOINT_AND_CENTRALLY_INVERSION_SYMMETRIC",
            "scope": "SAMPLED_DIGITAL_BREP_MESH_IDENTITY_NOT_CONTINUOUS_CLEARANCE_TOLERANCE_STACK_OR_PHYSICAL_VALIDATION",
        }
        payload["physical_validation_eligible"] = False
        payload["manifest_sha256"] = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        return payload


def build_retention_quick_release_tactile_v26() -> RetentionQuickReleaseTactileV26:
    prior = v25.build_retention_quick_release_tactile_v25()
    aligned, interstitial, combined, digest = _mesh_binding()
    return RetentionQuickReleaseTactileV26(prior, aligned, interstitial, combined, digest).validate()
