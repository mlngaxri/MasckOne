from __future__ import annotations

"""V39: bind each collision layer to the exact longitudinal schedule it owns.

V38 proves per-layer cardinality. V39 adds semantic provenance: each named layer is
bound to its ordered longitudinal positions and its validated collision-evidence
digest. This prevents a cardinality-correct layer/schedule reassignment from being
accepted. Evidence remains sampled digital B-rep, not continuous swept-volume proof.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import re

from . import retention_quick_release_tactile_v12 as v12
from . import retention_quick_release_tactile_v32 as v32
from . import retention_quick_release_tactile_v33 as v33
from . import retention_quick_release_tactile_v34 as v34
from . import retention_quick_release_tactile_v35 as v35
from . import retention_quick_release_tactile_v38 as v38

SCHEMA = "MASCK_ONE_RETENTION_QUICK_RELEASE_TACTILE_V39"
SUPERSEDES_SCHEMA = v38.SCHEMA
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


class RetentionQuickReleaseTactileV39Error(ValueError):
    pass


def _schedule_digest(positions: tuple[float, ...]) -> str:
    if not positions or any(not isinstance(p, (int, float)) for p in positions):
        raise RetentionQuickReleaseTactileV39Error("longitudinal schedule is invalid")
    return sha256(json.dumps(tuple(float(p) for p in positions), separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _layer_identity_evidence(prior: v38.RetentionQuickReleaseTactileV38) -> tuple[tuple[tuple[str, str, str, int], ...], str]:
    layers = v38.v37._collision_layers(prior.prior.prior)
    schedules = (
        ("stations", tuple(v12._canonical_positions())),
        ("midpoints", tuple(v32._midpoint_positions())),
        ("quarters", tuple(v33._quarter_positions())),
        ("eighths", tuple(v34._eighth_positions())),
        ("odd_sixteenths", tuple(v35._sixteenth_positions())),
    )
    records = []
    for (name, positions), layer, cardinality in zip(schedules, layers, prior.layer_cardinalities):
        if cardinality[0] != name or cardinality[1] != len(positions) or cardinality[2] != layer.pose_count:
            raise RetentionQuickReleaseTactileV39Error(f"{name} owner/cardinality binding drifted")
        evidence_digest = layer.evidence_sha256
        if not isinstance(evidence_digest, str) or _DIGEST_RE.fullmatch(evidence_digest) is None:
            raise RetentionQuickReleaseTactileV39Error(f"{name} collision evidence digest is invalid")
        records.append((name, _schedule_digest(positions), evidence_digest, layer.pose_count))
    payload = {
        "layers": records,
        "v38_layer_cardinality_sha256": prior.layer_cardinality_sha256,
        "v37_collision_coverage_sha256": prior.prior.collision_coverage_sha256,
    }
    digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return tuple(records), digest


@dataclass(frozen=True, slots=True)
class RetentionQuickReleaseTactileV39:
    prior: v38.RetentionQuickReleaseTactileV38
    layer_identities: tuple[tuple[str, str, str, int], ...]
    layer_identity_sha256: str

    def validate(self) -> "RetentionQuickReleaseTactileV39":
        self.prior.validate()
        records, digest = _layer_identity_evidence(self.prior)
        if self.layer_identities != records:
            raise RetentionQuickReleaseTactileV39Error("collision layer identity evidence is stale")
        if not isinstance(self.layer_identity_sha256, str) or _DIGEST_RE.fullmatch(self.layer_identity_sha256) is None or self.layer_identity_sha256 != digest:
            raise RetentionQuickReleaseTactileV39Error("collision layer identity digest is stale")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        payload = self.prior.manifest()
        payload.pop("manifest_sha256", None)
        payload["schema"] = SCHEMA
        payload["supersedes_schema"] = SUPERSEDES_SCHEMA
        payload["collision_layer_schedule_identity_binding"] = {
            "layers": [list(record) for record in self.layer_identities],
            "layer_identity_sha256": self.layer_identity_sha256,
            "criterion": "EACH_COLLISION_LAYER_IS_BOUND_TO_ITS_EXACT_ORDERED_LONGITUDINAL_SCHEDULE",
            "scope": "SAMPLED_DIGITAL_BREP_SCREEN_NOT_CONTINUOUS_SWEPT_VOLUME_OR_MANUFACTURING_TOLERANCE_STACK",
        }
        payload["physical_validation_eligible"] = False
        payload["manifest_sha256"] = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        return payload


def build_retention_quick_release_tactile_v39() -> RetentionQuickReleaseTactileV39:
    prior = v38.build_retention_quick_release_tactile_v38()
    records, digest = _layer_identity_evidence(prior)
    return RetentionQuickReleaseTactileV39(prior, records, digest).validate()
