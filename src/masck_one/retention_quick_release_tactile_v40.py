from __future__ import annotations

"""V40: bind collision evidence to the exact clearance-authority corners.

V39 binds each longitudinal collision layer to its schedule and evidence digest.
V40 closes the orthogonal provenance gap by binding those layers to the exact four
radial/anti-rotation clearance corners used by the collision screens. Evidence
remains sampled digital B-rep, not continuous swept-volume or manufactured-stack
proof.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import re

from . import retention_quick_release_tactile as v1
from . import retention_quick_release_tactile_v30 as v30
from . import retention_quick_release_tactile_v39 as v39

SCHEMA = "MASCK_ONE_RETENTION_QUICK_RELEASE_TACTILE_V40"
SUPERSEDES_SCHEMA = v39.SCHEMA
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


class RetentionQuickReleaseTactileV40Error(ValueError):
    pass


def _clearance_corner_identity(prior: v39.RetentionQuickReleaseTactileV39) -> tuple[tuple[tuple[str, float, float], ...], str]:
    mechanism = v1.build_retention_quick_release_tactile()
    corners = tuple(v30._clearance_corners(mechanism))
    if len(corners) != 4:
        raise RetentionQuickReleaseTactileV40Error("clearance authority must contain exactly four corners")
    names = tuple(item[0] for item in corners)
    pairs = tuple((float(item[1]), float(item[2])) for item in corners)
    if len(set(names)) != 4 or any(not name for name in names):
        raise RetentionQuickReleaseTactileV40Error("clearance-corner names must be unique and nonblank")
    if len(set(pairs)) != 4:
        raise RetentionQuickReleaseTactileV40Error("clearance-corner coordinate pairs must be unique")
    if any(not math.isfinite(value) or value <= 0.0 for pair in pairs for value in pair):
        raise RetentionQuickReleaseTactileV40Error("clearance-corner coordinates must be finite and positive")
    records = tuple((name, radial, side) for name, (radial, side) in zip(names, pairs))
    payload = {
        "corners": [[name, format(radial, ".12f"), format(side, ".12f")] for name, radial, side in records],
        "v39_layer_identity_sha256": prior.layer_identity_sha256,
        "v39_layers": [list(record) for record in prior.layer_identities],
    }
    digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    return records, digest


@dataclass(frozen=True, slots=True)
class RetentionQuickReleaseTactileV40:
    prior: v39.RetentionQuickReleaseTactileV39
    clearance_corner_identities: tuple[tuple[str, float, float], ...]
    clearance_corner_binding_sha256: str

    def validate(self) -> "RetentionQuickReleaseTactileV40":
        self.prior.validate()
        records, digest = _clearance_corner_identity(self.prior)
        if self.clearance_corner_identities != records:
            raise RetentionQuickReleaseTactileV40Error("clearance-corner identity evidence is stale")
        if (
            not isinstance(self.clearance_corner_binding_sha256, str)
            or _DIGEST_RE.fullmatch(self.clearance_corner_binding_sha256) is None
            or self.clearance_corner_binding_sha256 != digest
        ):
            raise RetentionQuickReleaseTactileV40Error("clearance-corner binding digest is stale")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        payload = self.prior.manifest()
        payload.pop("manifest_sha256", None)
        payload["schema"] = SCHEMA
        payload["supersedes_schema"] = SUPERSEDES_SCHEMA
        payload["clearance_corner_collision_authority_binding"] = {
            "corners": [list(record) for record in self.clearance_corner_identities],
            "clearance_corner_binding_sha256": self.clearance_corner_binding_sha256,
            "criterion": "ALL_COLLISION_LAYERS_ARE_BOUND_TO_THE_EXACT_FOUR_UNIQUE_CLEARANCE_AUTHORITY_CORNERS",
            "scope": "SAMPLED_DIGITAL_BREP_SCREEN_NOT_CONTINUOUS_SWEPT_VOLUME_OR_MANUFACTURING_TOLERANCE_STACK",
        }
        payload["physical_validation_eligible"] = False
        payload["manifest_sha256"] = sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()
        return payload


def build_retention_quick_release_tactile_v40() -> RetentionQuickReleaseTactileV40:
    prior = v39.build_retention_quick_release_tactile_v39()
    records, digest = _clearance_corner_identity(prior)
    return RetentionQuickReleaseTactileV40(prior, records, digest).validate()
