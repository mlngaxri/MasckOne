from __future__ import annotations

"""Bilateral load-path consistency verification for structural retention roots.

V4 proves bounded and mirrored capture-pin engagement. V5 additionally requires the
left and right frame-counterpart captures into the source structural reaction frame to
remain consistent. The accepted root contract is mirrored, so material asymmetry here
indicates one-sided load-path drift or stale mating geometry, not an intended product
feature. This remains digital geometry evidence only.
"""

from dataclasses import dataclass
import math

from .structural_frame_retention_verification_v4 import (
    StructuralFrameRetentionVerificationV4,
    StructuralFrameRetentionVerificationV4Error,
    verify_structural_frame_retention_roots_v4,
)

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_VERIFICATION_V5"
MAX_BILATERAL_SOURCE_FRAME_CAPTURE_RELATIVE_MISMATCH = 1e-6


class StructuralFrameRetentionVerificationV5Error(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionVerificationV5:
    v4: StructuralFrameRetentionVerificationV4
    maximum_bilateral_source_frame_capture_relative_mismatch: float = (
        MAX_BILATERAL_SOURCE_FRAME_CAPTURE_RELATIVE_MISMATCH
    )
    physical_validation_eligible: bool = False

    def validate(self) -> "StructuralFrameRetentionVerificationV5":
        try:
            self.v4.validate()
        except StructuralFrameRetentionVerificationV4Error as exc:
            raise StructuralFrameRetentionVerificationV5Error("V4 prerequisite verification failed") from exc
        limit = self.maximum_bilateral_source_frame_capture_relative_mismatch
        if not math.isfinite(limit) or limit < 0.0:
            raise StructuralFrameRetentionVerificationV5Error(
                "bilateral source-frame capture mismatch limit must be finite and nonnegative"
            )
        if limit > MAX_BILATERAL_SOURCE_FRAME_CAPTURE_RELATIVE_MISMATCH:
            raise StructuralFrameRetentionVerificationV5Error(
                "bilateral source-frame capture mismatch limit cannot weaken the authority ceiling"
            )
        captures = {
            root.root_id: root.source_frame_capture_mm3 for root in self.v4.v3.v2.roots
        }
        left = captures["RETENTION_ROOT_WEARER_LEFT"]
        right = captures["RETENTION_ROOT_WEARER_RIGHT"]
        scale = max(left, right)
        if not math.isfinite(scale) or scale <= 0.0:
            raise StructuralFrameRetentionVerificationV5Error(
                "bilateral source-frame capture scale must be finite and positive"
            )
        mismatch = abs(left - right) / scale
        if not math.isfinite(mismatch) or mismatch > limit:
            raise StructuralFrameRetentionVerificationV5Error(
                "bilateral retention-root source-frame capture is not symmetric within the authority ceiling"
            )
        if self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionVerificationV5Error(
                "digital load-path consistency is not physical validation evidence"
            )
        return self

    @property
    def bilateral_source_frame_capture_relative_mismatch(self) -> float:
        self.v4.validate()
        captures = {
            root.root_id: root.source_frame_capture_mm3 for root in self.v4.v3.v2.roots
        }
        left = captures["RETENTION_ROOT_WEARER_LEFT"]
        right = captures["RETENTION_ROOT_WEARER_RIGHT"]
        scale = max(left, right)
        if not math.isfinite(scale) or scale <= 0.0:
            raise StructuralFrameRetentionVerificationV5Error(
                "bilateral source-frame capture scale must be finite and positive"
            )
        return abs(left - right) / scale

    def manifest(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": SCHEMA,
            "verification_semantics": "FAIL_CLOSED_V4_PLUS_BILATERAL_SOURCE_FRAME_CAPTURE_CONSISTENCY",
            "authority_maximum_bilateral_source_frame_capture_relative_mismatch": (
                MAX_BILATERAL_SOURCE_FRAME_CAPTURE_RELATIVE_MISMATCH
            ),
            "enforced_maximum_bilateral_source_frame_capture_relative_mismatch": (
                self.maximum_bilateral_source_frame_capture_relative_mismatch
            ),
            "measured_bilateral_source_frame_capture_relative_mismatch": (
                self.bilateral_source_frame_capture_relative_mismatch
            ),
            "physical_validation_eligible": False,
        }


def verify_structural_frame_retention_roots_v5() -> StructuralFrameRetentionVerificationV5:
    return StructuralFrameRetentionVerificationV5(
        v4=verify_structural_frame_retention_roots_v4()
    ).validate()
