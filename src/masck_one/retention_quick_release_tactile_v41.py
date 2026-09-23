from __future__ import annotations

"""V41: bind clearance-corner identities to their transverse mesh authority.

V40 binds collision provenance to the exact four clearance-coordinate corners. V31
independently proves the aligned/interstitial mesh integrity at those corners. V41
binds those authorities together so corner coordinates cannot remain valid while the
transverse sampling authority silently drifts. Evidence remains sampled digital B-rep.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import re

from . import retention_quick_release_tactile_v31 as v31
from . import retention_quick_release_tactile_v40 as v40

SCHEMA = "MASCK_ONE_RETENTION_QUICK_RELEASE_TACTILE_V41"
SUPERSEDES_SCHEMA = v40.SCHEMA
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


class RetentionQuickReleaseTactileV41Error(ValueError):
    pass


def _corner_mesh_authority_binding(prior: v40.RetentionQuickReleaseTactileV40) -> tuple[int, int, int, str, str]:
    mesh = v31.build_retention_quick_release_tactile_v31()
    if mesh.combined_unique_count != mesh.prior.transverse_sample_count:
        raise RetentionQuickReleaseTactileV41Error("corner mesh authority count drifted from collision screen")
    if not isinstance(mesh.corner_mesh_identity_sha256, str) or _DIGEST_RE.fullmatch(mesh.corner_mesh_identity_sha256) is None:
        raise RetentionQuickReleaseTactileV41Error("corner mesh authority digest is invalid")
    payload = {
        "v40_clearance_corner_binding_sha256": prior.clearance_corner_binding_sha256,
        "v40_clearance_corner_identities": [list(record) for record in prior.clearance_corner_identities],
        "v31_aligned_unique_count": mesh.aligned_unique_count,
        "v31_interstitial_unique_count": mesh.interstitial_unique_count,
        "v31_combined_unique_count": mesh.combined_unique_count,
        "v31_corner_mesh_identity_sha256": mesh.corner_mesh_identity_sha256,
    }
    digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    return (
        mesh.aligned_unique_count,
        mesh.interstitial_unique_count,
        mesh.combined_unique_count,
        mesh.corner_mesh_identity_sha256,
        digest,
    )


@dataclass(frozen=True, slots=True)
class RetentionQuickReleaseTactileV41:
    prior: v40.RetentionQuickReleaseTactileV40
    aligned_unique_count: int
    interstitial_unique_count: int
    combined_unique_count: int
    corner_mesh_identity_sha256: str
    corner_mesh_authority_binding_sha256: str

    def validate(self) -> "RetentionQuickReleaseTactileV41":
        self.prior.validate()
        aligned, interstitial, combined, mesh_digest, binding_digest = _corner_mesh_authority_binding(self.prior)
        if (self.aligned_unique_count, self.interstitial_unique_count, self.combined_unique_count) != (aligned, interstitial, combined):
            raise RetentionQuickReleaseTactileV41Error("corner mesh authority counts are stale")
        if self.corner_mesh_identity_sha256 != mesh_digest:
            raise RetentionQuickReleaseTactileV41Error("corner mesh authority identity is stale")
        if (
            not isinstance(self.corner_mesh_authority_binding_sha256, str)
            or _DIGEST_RE.fullmatch(self.corner_mesh_authority_binding_sha256) is None
            or self.corner_mesh_authority_binding_sha256 != binding_digest
        ):
            raise RetentionQuickReleaseTactileV41Error("corner mesh authority binding digest is stale")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        payload = self.prior.manifest()
        payload.pop("manifest_sha256", None)
        payload["schema"] = SCHEMA
        payload["supersedes_schema"] = SUPERSEDES_SCHEMA
        payload["clearance_corner_mesh_authority_binding"] = {
            "aligned_unique_count": self.aligned_unique_count,
            "interstitial_unique_count": self.interstitial_unique_count,
            "combined_unique_count": self.combined_unique_count,
            "corner_mesh_identity_sha256": self.corner_mesh_identity_sha256,
            "corner_mesh_authority_binding_sha256": self.corner_mesh_authority_binding_sha256,
            "criterion": "EXACT_CLEARANCE_CORNERS_ARE_BOUND_TO_THE_VALIDATED_TRANSVERSE_MESH_AUTHORITY",
            "scope": "SAMPLED_DIGITAL_BREP_SCREEN_NOT_CONTINUOUS_SWEPT_VOLUME_OR_MANUFACTURING_TOLERANCE_STACK",
        }
        payload["physical_validation_eligible"] = False
        payload["manifest_sha256"] = sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()
        return payload


def build_retention_quick_release_tactile_v41() -> RetentionQuickReleaseTactileV41:
    prior = v40.build_retention_quick_release_tactile_v40()
    aligned, interstitial, combined, mesh_digest, binding_digest = _corner_mesh_authority_binding(prior)
    return RetentionQuickReleaseTactileV41(
        prior, aligned, interstitial, combined, mesh_digest, binding_digest
    ).validate()
