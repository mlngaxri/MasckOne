from __future__ import annotations

"""V31: bind transverse-mesh integrity at every V30 clearance authority corner.

V26 proves uniqueness, disjointness and central inversion symmetry at nominal clearance.
V30 screens geometry at all nominal/maximum radial and side-clearance combinations. V31
closes the provenance gap between them by proving those mesh properties independently at
every V30 authority corner. This remains sampled digital packaging evidence only.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import re

from . import retention_quick_release_tactile as v1
from . import retention_quick_release_tactile_v16 as v16
from . import retention_quick_release_tactile_v17 as v17
from . import retention_quick_release_tactile_v26 as v26
from . import retention_quick_release_tactile_v30 as v30

SCHEMA = "MASCK_ONE_RETENTION_QUICK_RELEASE_TACTILE_V31"
SUPERSEDES_SCHEMA = v30.SCHEMA
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


class RetentionQuickReleaseTactileV31Error(ValueError):
    pass


def _corner_mesh_binding() -> tuple[int, int, int, str]:
    mechanism = v1.build_retention_quick_release_tactile()
    records: list[dict[str, object]] = []
    aligned_total = interstitial_total = combined_total = 0
    try:
        for corner, radial, side in v30._clearance_corners(mechanism):
            aligned = v16._dense_samples(radial, side)
            interstitial = v17._interstitial_samples(radial, side)
            aligned_count, aligned_digest = v26._audit_family(f"{corner} aligned", aligned)
            interstitial_count, interstitial_digest = v26._audit_family(f"{corner} interstitial", interstitial)
            aligned_keys = {v26._key(point) for point in aligned}
            interstitial_keys = {v26._key(point) for point in interstitial}
            if aligned_keys & interstitial_keys:
                raise RetentionQuickReleaseTactileV31Error(
                    f"{corner} aligned and interstitial transverse meshes overlap"
                )
            combined_count = len(aligned_keys | interstitial_keys)
            if combined_count != aligned_count + interstitial_count:
                raise RetentionQuickReleaseTactileV31Error(f"{corner} combined mesh count is inconsistent")
            aligned_total += aligned_count
            interstitial_total += interstitial_count
            combined_total += combined_count
            records.append(
                {
                    "corner": corner,
                    "radial_mm": format(radial, ".12f"),
                    "side_mm": format(side, ".12f"),
                    "aligned_unique_count": aligned_count,
                    "interstitial_unique_count": interstitial_count,
                    "combined_unique_count": combined_count,
                    "aligned_sha256": aligned_digest,
                    "interstitial_sha256": interstitial_digest,
                }
            )
    except RetentionQuickReleaseTactileV31Error:
        raise
    except Exception as exc:
        raise RetentionQuickReleaseTactileV31Error("clearance-corner mesh integrity audit failed") from exc
    digest = sha256(json.dumps(records, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return aligned_total, interstitial_total, combined_total, digest


@dataclass(frozen=True, slots=True)
class RetentionQuickReleaseTactileV31:
    prior: v30.RetentionQuickReleaseTactileV30
    aligned_unique_count: int
    interstitial_unique_count: int
    combined_unique_count: int
    corner_mesh_identity_sha256: str

    def validate(self) -> "RetentionQuickReleaseTactileV31":
        self.prior.validate()
        aligned, interstitial, combined, digest = _corner_mesh_binding()
        if self.aligned_unique_count != aligned:
            raise RetentionQuickReleaseTactileV31Error("clearance-corner aligned unique count is stale")
        if self.interstitial_unique_count != interstitial:
            raise RetentionQuickReleaseTactileV31Error("clearance-corner interstitial unique count is stale")
        if self.combined_unique_count != combined or combined != aligned + interstitial:
            raise RetentionQuickReleaseTactileV31Error("clearance-corner combined unique count is stale")
        if combined != self.prior.transverse_sample_count:
            raise RetentionQuickReleaseTactileV31Error("V31 corner mesh count no longer matches V30 screen")
        if not isinstance(self.corner_mesh_identity_sha256, str) or _DIGEST_RE.fullmatch(self.corner_mesh_identity_sha256) is None:
            raise RetentionQuickReleaseTactileV31Error("corner mesh identity must be canonical lowercase SHA-256")
        if self.corner_mesh_identity_sha256 != digest:
            raise RetentionQuickReleaseTactileV31Error("clearance-corner mesh identity is stale")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        payload = self.prior.manifest()
        payload.pop("manifest_sha256", None)
        payload["schema"] = SCHEMA
        payload["supersedes_schema"] = SUPERSEDES_SCHEMA
        payload["clearance_corner_mesh_integrity"] = {
            "corner_count": 4,
            "aligned_unique_count": self.aligned_unique_count,
            "interstitial_unique_count": self.interstitial_unique_count,
            "combined_unique_count": self.combined_unique_count,
            "corner_mesh_identity_sha256": self.corner_mesh_identity_sha256,
            "criterion": "EVERY_CLEARANCE_AUTHORITY_CORNER_MESH_IS_UNIQUE_DISJOINT_AND_CENTRALLY_INVERSION_SYMMETRIC",
            "scope": "SAMPLED_DIGITAL_BREP_MESH_PROVENANCE_NOT_CONTINUOUS_CLEARANCE_OR_MANUFACTURING_TOLERANCE_STACK",
        }
        payload["physical_validation_eligible"] = False
        payload["manifest_sha256"] = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        return payload


def build_retention_quick_release_tactile_v31() -> RetentionQuickReleaseTactileV31:
    prior = v30.build_retention_quick_release_tactile_v30()
    aligned, interstitial, combined, digest = _corner_mesh_binding()
    return RetentionQuickReleaseTactileV31(prior, aligned, interstitial, combined, digest).validate()
