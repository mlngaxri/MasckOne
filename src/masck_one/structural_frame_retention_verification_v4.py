from __future__ import annotations

"""Bilateral-consistency verification for retention-root capture pins.

V3 bounds each pin's yoke-bore engagement independently. V4 additionally requires the
left and right engagement measurements to remain bilaterally consistent. The accepted
root/yoke contract is mirrored, so a material left/right capture mismatch is evidence
of one-sided geometry drift, stale mating geometry, or a corrupt Boolean result rather
than an intended product asymmetry. This remains digital geometry evidence only.
"""

from dataclasses import dataclass
import math

from .structural_frame_retention_verification_v3 import (
    StructuralFrameRetentionVerificationV3,
    StructuralFrameRetentionVerificationV3Error,
    verify_structural_frame_retention_roots_v3,
)

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_VERIFICATION_V4"
MAX_BILATERAL_PIN_CAPTURE_RELATIVE_MISMATCH = 1e-6


class StructuralFrameRetentionVerificationV4Error(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionVerificationV4:
    v3: StructuralFrameRetentionVerificationV3
    maximum_bilateral_pin_capture_relative_mismatch: float = MAX_BILATERAL_PIN_CAPTURE_RELATIVE_MISMATCH
    physical_validation_eligible: bool = False

    def validate(self) -> "StructuralFrameRetentionVerificationV4":
        try:
            self.v3.validate()
        except StructuralFrameRetentionVerificationV3Error as exc:
            raise StructuralFrameRetentionVerificationV4Error("V3 prerequisite verification failed") from exc
        limit = self.maximum_bilateral_pin_capture_relative_mismatch
        if not math.isfinite(limit) or limit < 0.0:
            raise StructuralFrameRetentionVerificationV4Error(
                "bilateral pin capture mismatch limit must be finite and nonnegative"
            )
        if limit > MAX_BILATERAL_PIN_CAPTURE_RELATIVE_MISMATCH:
            raise StructuralFrameRetentionVerificationV4Error(
                "bilateral pin capture mismatch limit cannot weaken the authority ceiling"
            )
        captures = {root.root_id: root.pin_bore_capture_mm3 for root in self.v3.v2.roots}
        left = captures["RETENTION_ROOT_WEARER_LEFT"]
        right = captures["RETENTION_ROOT_WEARER_RIGHT"]
        scale = max(left, right)
        mismatch = abs(left - right) / scale
        if not math.isfinite(mismatch) or mismatch > limit:
            raise StructuralFrameRetentionVerificationV4Error(
                "bilateral capture-pin yoke engagement is not symmetric within the authority ceiling"
            )
        if self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionVerificationV4Error(
                "digital bilateral consistency is not physical validation evidence"
            )
        return self

    @property
    def bilateral_pin_capture_relative_mismatch(self) -> float:
        self.v3.validate()
        captures = {root.root_id: root.pin_bore_capture_mm3 for root in self.v3.v2.roots}
        left = captures["RETENTION_ROOT_WEARER_LEFT"]
        right = captures["RETENTION_ROOT_WEARER_RIGHT"]
        return abs(left - right) / max(left, right)

    def manifest(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": SCHEMA,
            "verification_semantics": "FAIL_CLOSED_V3_PLUS_BILATERAL_PIN_BORE_CAPTURE_CONSISTENCY",
            "authority_maximum_bilateral_pin_capture_relative_mismatch": MAX_BILATERAL_PIN_CAPTURE_RELATIVE_MISMATCH,
            "enforced_maximum_bilateral_pin_capture_relative_mismatch": self.maximum_bilateral_pin_capture_relative_mismatch,
            "measured_bilateral_pin_capture_relative_mismatch": self.bilateral_pin_capture_relative_mismatch,
            "physical_validation_eligible": False,
        }


def verify_structural_frame_retention_roots_v4() -> StructuralFrameRetentionVerificationV4:
    return StructuralFrameRetentionVerificationV4(
        v3=verify_structural_frame_retention_roots_v3()
    ).validate()
