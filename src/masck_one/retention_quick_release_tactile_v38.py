from __future__ import annotations

"""V38: bind each longitudinal authority to its own collision-pose cardinality.

V37 binds the aggregate complete 1/16 lattice to collision evidence. An aggregate
count alone is weaker than proving that each owning collision layer contributes
exactly the poses implied by its own longitudinal authority. V38 closes that gap
without changing geometry. This remains sampled digital B-rep evidence, not a
continuous swept-volume or manufactured-tolerance proof.
"""

from dataclasses import dataclass
from hashlib import sha256
import json

from . import retention_quick_release_tactile_v12 as v12
from . import retention_quick_release_tactile_v32 as v32
from . import retention_quick_release_tactile_v33 as v33
from . import retention_quick_release_tactile_v34 as v34
from . import retention_quick_release_tactile_v35 as v35
from . import retention_quick_release_tactile_v37 as v37

SCHEMA = "MASCK_ONE_RETENTION_QUICK_RELEASE_TACTILE_V38"
SUPERSEDES_SCHEMA = v37.SCHEMA


class RetentionQuickReleaseTactileV38Error(ValueError):
    pass


def _layer_cardinality_evidence(prior: v37.RetentionQuickReleaseTactileV37) -> tuple[tuple[tuple[str, int, int], ...], str]:
    layers = v37._collision_layers(prior.prior)
    names = ("stations", "midpoints", "quarters", "eighths", "odd_sixteenths")
    longitudinal_counts = (
        len(v12._canonical_positions()),
        len(v32._midpoint_positions()),
        len(v33._quarter_positions()),
        len(v34._eighth_positions()),
        len(v35._sixteenth_positions()),
    )
    records: list[tuple[str, int, int]] = []
    for name, longitudinal_count, layer in zip(names, longitudinal_counts, layers):
        expected = prior.transverse_sample_count * longitudinal_count
        if layer.transverse_sample_count != prior.transverse_sample_count:
            raise RetentionQuickReleaseTactileV38Error(f"{name} transverse authority drifted")
        if layer.pose_count != expected:
            raise RetentionQuickReleaseTactileV38Error(f"{name} collision pose cardinality is incomplete")
        records.append((name, longitudinal_count, layer.pose_count))
    if sum(record[2] for record in records) != prior.complete_lattice_collision_pose_count:
        raise RetentionQuickReleaseTactileV38Error("per-layer collision pose cardinalities disagree with V37 aggregate")
    payload = {"transverse_sample_count": prior.transverse_sample_count, "layers": records, "v37_collision_coverage_sha256": prior.collision_coverage_sha256}
    digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return tuple(records), digest


@dataclass(frozen=True, slots=True)
class RetentionQuickReleaseTactileV38:
    prior: v37.RetentionQuickReleaseTactileV37
    layer_cardinalities: tuple[tuple[str, int, int], ...]
    layer_cardinality_sha256: str

    def validate(self) -> "RetentionQuickReleaseTactileV38":
        self.prior.validate()
        records, digest = _layer_cardinality_evidence(self.prior)
        if self.layer_cardinalities != records:
            raise RetentionQuickReleaseTactileV38Error("per-layer collision cardinality evidence is stale")
        if self.layer_cardinality_sha256 != digest:
            raise RetentionQuickReleaseTactileV38Error("per-layer collision cardinality digest is stale")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        payload = self.prior.manifest()
        payload.pop("manifest_sha256", None)
        payload["schema"] = SCHEMA
        payload["supersedes_schema"] = SUPERSEDES_SCHEMA
        payload["per_layer_collision_cardinality_binding"] = {
            "layers": [list(record) for record in self.layer_cardinalities],
            "layer_cardinality_sha256": self.layer_cardinality_sha256,
            "criterion": "EACH_LONGITUDINAL_AUTHORITY_CONTRIBUTES_EXACTLY_ITS_EXPECTED_COLLISION_POSES",
            "scope": "SAMPLED_DIGITAL_BREP_SCREEN_NOT_CONTINUOUS_SWEPT_VOLUME_OR_MANUFACTURING_TOLERANCE_STACK",
        }
        payload["physical_validation_eligible"] = False
        payload["manifest_sha256"] = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        return payload


def build_retention_quick_release_tactile_v38() -> RetentionQuickReleaseTactileV38:
    prior = v37.build_retention_quick_release_tactile_v37()
    records, digest = _layer_cardinality_evidence(prior)
    return RetentionQuickReleaseTactileV38(prior, records, digest).validate()
