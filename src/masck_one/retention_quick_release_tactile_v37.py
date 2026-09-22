from __future__ import annotations

"""V37: bind complete longitudinal coverage to actual collision evidence.

V36 proves that the station, half, quarter, eighth and odd-sixteenth schedules
partition the complete 1/16 longitudinal lattice. This layer additionally binds
the pose counts and evidence digests of the five collision-screen layers that
own those schedules. It prevents schedule-completeness evidence from remaining
green if a collision layer silently loses poses. This is sampled digital B-rep
evidence, not continuous swept-volume proof.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import re

from . import retention_quick_release_tactile_v36 as v36

SCHEMA = "MASCK_ONE_RETENTION_QUICK_RELEASE_TACTILE_V37"
SUPERSEDES_SCHEMA = v36.SCHEMA
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


class RetentionQuickReleaseTactileV37Error(ValueError):
    pass


def _collision_layers(prior: v36.RetentionQuickReleaseTactileV36):
    v35 = prior.prior
    v34 = v35.prior
    v33 = v34.prior
    v32 = v33.prior
    v31 = v32.prior
    v30 = v31.prior
    return (v30, v32, v33, v34, v35)


def _collision_coverage_evidence(prior: v36.RetentionQuickReleaseTactileV36) -> tuple[int, int, str]:
    layers = _collision_layers(prior)
    transverse = layers[0].transverse_sample_count
    if any(layer.transverse_sample_count != transverse for layer in layers[1:]):
        raise RetentionQuickReleaseTactileV37Error("collision layers disagree on transverse sample authority")
    total_poses = sum(layer.pose_count for layer in layers)
    expected_poses = transverse * prior.complete_lattice_position_count
    if total_poses != expected_poses:
        raise RetentionQuickReleaseTactileV37Error("collision evidence does not cover every complete-lattice pose")
    digests = tuple(layer.evidence_sha256 for layer in layers)
    if any(not isinstance(digest, str) or _DIGEST_RE.fullmatch(digest) is None for digest in digests):
        raise RetentionQuickReleaseTactileV37Error("collision layer evidence digest is invalid")
    payload = {
        "complete_lattice_position_count": prior.complete_lattice_position_count,
        "transverse_sample_count": transverse,
        "collision_pose_count": total_poses,
        "layer_evidence_sha256": digests,
        "coverage_sha256": prior.coverage_sha256,
    }
    digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return transverse, total_poses, digest


@dataclass(frozen=True, slots=True)
class RetentionQuickReleaseTactileV37:
    prior: v36.RetentionQuickReleaseTactileV36
    transverse_sample_count: int
    complete_lattice_collision_pose_count: int
    collision_coverage_sha256: str

    def validate(self) -> "RetentionQuickReleaseTactileV37":
        self.prior.validate()
        transverse, poses, digest = _collision_coverage_evidence(self.prior)
        if self.transverse_sample_count != transverse:
            raise RetentionQuickReleaseTactileV37Error("complete-lattice transverse sample count is stale")
        if self.complete_lattice_collision_pose_count != poses:
            raise RetentionQuickReleaseTactileV37Error("complete-lattice collision pose count is stale")
        if not isinstance(self.collision_coverage_sha256, str) or _DIGEST_RE.fullmatch(self.collision_coverage_sha256) is None or self.collision_coverage_sha256 != digest:
            raise RetentionQuickReleaseTactileV37Error("complete-lattice collision coverage digest is stale")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        payload = self.prior.manifest()
        payload.pop("manifest_sha256", None)
        payload["schema"] = SCHEMA
        payload["supersedes_schema"] = SUPERSEDES_SCHEMA
        payload["complete_lattice_collision_binding"] = {
            "transverse_sample_count": self.transverse_sample_count,
            "complete_lattice_collision_pose_count": self.complete_lattice_collision_pose_count,
            "collision_coverage_sha256": self.collision_coverage_sha256,
            "criterion": "EVERY_COMPLETE_SIXTEENTH_LATTICE_POSITION_IS_BOUND_TO_VALIDATED_COLLISION_SCREEN_POSE_EVIDENCE",
            "scope": "SAMPLED_DIGITAL_BREP_SCREEN_NOT_CONTINUOUS_SWEPT_VOLUME_OR_MANUFACTURING_TOLERANCE_STACK",
        }
        payload["physical_validation_eligible"] = False
        payload["manifest_sha256"] = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        return payload


def build_retention_quick_release_tactile_v37() -> RetentionQuickReleaseTactileV37:
    prior = v36.build_retention_quick_release_tactile_v36()
    transverse, poses, digest = _collision_coverage_evidence(prior)
    return RetentionQuickReleaseTactileV37(prior, transverse, poses, digest).validate()
