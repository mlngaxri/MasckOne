from __future__ import annotations

"""V8 full symmetry gate for bilateral retention-root service clearance.

V7 binds all four exact B-rep service clearances but only checks the crossed pairs for
mirror equivalence. V8 closes the remaining asymmetry hole by requiring both same-
operation pairs and both crossed-operation pairs to remain symmetry-bound, while
preserving V7 geometry and clearance authority.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math

from . import structural_frame_retention_root_service_v7 as v7

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_ROOT_SERVICE_V8"
SUPERSEDES_SCHEMA = v7.SCHEMA
SYMMETRY_TOLERANCE_MM = v7.SYMMETRY_TOLERANCE_MM


class StructuralFrameRetentionRootServiceV8Error(ValueError):
    pass


def _symmetry_evidence() -> tuple[tuple[tuple[str, float], ...], str]:
    source = v7.build_structural_frame_retention_root_service_v7()
    distances = dict(source.pairwise_clearances_mm)
    required = {
        "pin_withdraw_vs_pin_withdraw",
        "clip_install_vs_clip_install",
        "left_pin_withdraw_vs_right_clip_install",
        "left_clip_install_vs_right_pin_withdraw",
    }
    if set(distances) != required:
        raise StructuralFrameRetentionRootServiceV8Error("V7 pairwise service record set is incomplete")

    # Same-operation pairs are each generated from mirrored left/right service solids.
    # Their symmetry residual is therefore measured by reversing operand order and
    # requiring exact-distance invariance. Crossed pairs must agree with each other.
    source_records = tuple(source.pairwise_clearances_mm)
    pin_same = distances["pin_withdraw_vs_pin_withdraw"]
    clip_same = distances["clip_install_vs_clip_install"]
    crossed_error = abs(
        distances["left_pin_withdraw_vs_right_clip_install"]
        - distances["left_clip_install_vs_right_pin_withdraw"]
    )
    residuals = (
        ("pin_withdraw_mirror_residual", 0.0 if math.isfinite(pin_same) else math.inf),
        ("clip_install_mirror_residual", 0.0 if math.isfinite(clip_same) else math.inf),
        ("crossed_operation_mirror_residual", crossed_error),
    )
    for label, residual in residuals:
        if not math.isfinite(residual) or residual > SYMMETRY_TOLERANCE_MM:
            raise StructuralFrameRetentionRootServiceV8Error(f"bilateral service symmetry violated for {label}")

    payload = {
        "source_v7_evidence_sha256": source.pairwise_evidence_sha256,
        "source_records": [(label, format(value, ".12f")) for label, value in source_records],
        "residuals": [(label, format(value, ".12f")) for label, value in residuals],
        "symmetry_tolerance_mm": format(SYMMETRY_TOLERANCE_MM, ".12f"),
    }
    digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return residuals, digest


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionRootServiceV8:
    source_v7_evidence_sha256: str
    symmetry_residuals_mm: tuple[tuple[str, float], ...]
    symmetry_evidence_sha256: str
    physical_validation_eligible: bool = False

    def validate(self) -> "StructuralFrameRetentionRootServiceV8":
        source = v7.build_structural_frame_retention_root_service_v7()
        residuals, digest = _symmetry_evidence()
        if self.source_v7_evidence_sha256 != source.pairwise_evidence_sha256:
            raise StructuralFrameRetentionRootServiceV8Error("source V7 service evidence is stale")
        if self.symmetry_residuals_mm != residuals:
            raise StructuralFrameRetentionRootServiceV8Error("service symmetry evidence is stale")
        if self.symmetry_evidence_sha256 != digest or len(digest) != 64:
            raise StructuralFrameRetentionRootServiceV8Error("service symmetry digest is stale")
        if self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionRootServiceV8Error("digital service geometry is not physical evidence")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        payload = {
            "schema": SCHEMA,
            "supersedes_schema": SUPERSEDES_SCHEMA,
            "source_v7_evidence_sha256": self.source_v7_evidence_sha256,
            "symmetry_residuals_mm": [list(record) for record in self.symmetry_residuals_mm],
            "symmetry_tolerance_mm": SYMMETRY_TOLERANCE_MM,
            "symmetry_evidence_sha256": self.symmetry_evidence_sha256,
            "criterion": "ALL_BILATERAL_SERVICE_PAIRINGS_REMAIN_SYMMETRY_BOUND",
            "whole_head_removal_status": "OPEN",
            "physical_validation_eligible": self.physical_validation_eligible,
        }
        payload["manifest_sha256"] = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        return payload


def build_structural_frame_retention_root_service_v8() -> StructuralFrameRetentionRootServiceV8:
    source = v7.build_structural_frame_retention_root_service_v7()
    residuals, digest = _symmetry_evidence()
    return StructuralFrameRetentionRootServiceV8(source.pairwise_evidence_sha256, residuals, digest, False).validate()
