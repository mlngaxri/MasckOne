from __future__ import annotations

"""V7 pairwise symmetry gate for bilateral retention-root service clearance.

V6 proves the minimum exact B-rep clearance across bilateral service operations. V7
retains the individual exact distances and proves that the two crossed operation pairs
remain mirror-equivalent. This catches asymmetric service drift that a minimum-only gate
can hide while preserving the accepted service geometry and clearance authority.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math

from . import structural_frame_retention_root_service as v1
from . import structural_frame_retention_root_service_v6 as v6
from .structural_frame_retention_roots import build_structural_frame_retention_roots

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_ROOT_SERVICE_V7"
SUPERSEDES_SCHEMA = v6.SCHEMA
SYMMETRY_TOLERANCE_MM = 1e-6


class StructuralFrameRetentionRootServiceV7Error(ValueError):
    pass


def _pairwise_evidence() -> tuple[tuple[tuple[str, float], ...], str]:
    roots = build_structural_frame_retention_roots()
    service = v1.build_structural_frame_retention_root_service(roots=roots)
    if len(service.paths) != 2:
        raise StructuralFrameRetentionRootServiceV7Error("exactly two bilateral service paths are required")
    left, right = service.paths
    checks = (
        ("pin_withdraw_vs_pin_withdraw", left.pin_withdraw_sweep, right.pin_withdraw_sweep),
        ("clip_install_vs_clip_install", left.clip_install_sweep, right.clip_install_sweep),
        ("left_pin_withdraw_vs_right_clip_install", left.pin_withdraw_sweep, right.clip_install_sweep),
        ("left_clip_install_vs_right_pin_withdraw", left.clip_install_sweep, right.pin_withdraw_sweep),
    )
    records: list[tuple[str, float]] = []
    for label, first, second in checks:
        distance = v6._brep_distance(first, second)
        if distance < v6.MIN_BREP_SERVICE_CLEARANCE_MM:
            raise StructuralFrameRetentionRootServiceV7Error(f"insufficient pairwise service clearance for {label}")
        records.append((label, round(distance, 12)))

    distances = dict(records)
    crossed_error = abs(
        distances["left_pin_withdraw_vs_right_clip_install"]
        - distances["left_clip_install_vs_right_pin_withdraw"]
    )
    if not math.isfinite(crossed_error) or crossed_error > SYMMETRY_TOLERANCE_MM:
        raise StructuralFrameRetentionRootServiceV7Error(
            "crossed bilateral service clearances are not mirror-equivalent"
        )

    source = v6.build_structural_frame_retention_root_service_v6()
    minimum = min(distance for _, distance in records)
    if abs(minimum - source.minimum_brep_service_clearance_mm) > 1e-9:
        raise StructuralFrameRetentionRootServiceV7Error("pairwise clearances contradict V6 minimum authority")
    payload = {
        "source_v6_evidence_sha256": source.clearance_evidence_sha256,
        "records": [(label, format(distance, ".12f")) for label, distance in records],
        "symmetry_tolerance_mm": format(SYMMETRY_TOLERANCE_MM, ".12f"),
    }
    digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return tuple(records), digest


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionRootServiceV7:
    source_v6_evidence_sha256: str
    pairwise_clearances_mm: tuple[tuple[str, float], ...]
    pairwise_evidence_sha256: str
    physical_validation_eligible: bool = False

    def validate(self) -> "StructuralFrameRetentionRootServiceV7":
        source = v6.build_structural_frame_retention_root_service_v6()
        records, digest = _pairwise_evidence()
        if self.source_v6_evidence_sha256 != source.clearance_evidence_sha256:
            raise StructuralFrameRetentionRootServiceV7Error("source V6 service evidence is stale")
        if self.pairwise_clearances_mm != records:
            raise StructuralFrameRetentionRootServiceV7Error("pairwise service-clearance evidence is stale")
        if self.pairwise_evidence_sha256 != digest or len(digest) != 64:
            raise StructuralFrameRetentionRootServiceV7Error("pairwise service-clearance digest is stale")
        if self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionRootServiceV7Error("digital service geometry is not physical evidence")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        payload = {
            "schema": SCHEMA,
            "supersedes_schema": SUPERSEDES_SCHEMA,
            "source_v6_evidence_sha256": self.source_v6_evidence_sha256,
            "pairwise_clearances_mm": [list(record) for record in self.pairwise_clearances_mm],
            "symmetry_tolerance_mm": SYMMETRY_TOLERANCE_MM,
            "pairwise_evidence_sha256": self.pairwise_evidence_sha256,
            "criterion": "BILATERAL_SERVICE_CLEARANCES_REMAIN_PAIRWISE_BOUND_AND_MIRROR_EQUIVALENT",
            "whole_head_removal_status": "OPEN",
            "physical_validation_eligible": self.physical_validation_eligible,
        }
        payload["manifest_sha256"] = sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()
        return payload


def build_structural_frame_retention_root_service_v7() -> StructuralFrameRetentionRootServiceV7:
    source = v6.build_structural_frame_retention_root_service_v6()
    records, digest = _pairwise_evidence()
    return StructuralFrameRetentionRootServiceV7(
        source.clearance_evidence_sha256, records, digest, False
    ).validate()
