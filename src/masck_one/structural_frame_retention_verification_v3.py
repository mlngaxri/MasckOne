from __future__ import annotations

"""Coverage-strengthened verification for bilateral retention capture pins.

V2 proves that each pin intersects its intended yoke bore. V3 additionally requires
that the intersection covers essentially the full nominal bore span, preventing a
barely engaged or axially shifted pin from passing on a microscopic positive overlap.
The authority floor is fail-closed: callers may strengthen it, but cannot lower it.
V3 also rejects geometrically impossible over-capture, so a stale bore/pin contract or
corrupt intersection metric cannot masquerade as stronger engagement. This remains
digital geometry evidence only.
"""

from dataclasses import dataclass
import math

from .structural_frame_retention_roots import (
    CLEVIS_PIN_RADIUS_MM,
    YOKE_ROOT_BORE_LENGTH_MM,
)
from .structural_frame_retention_verification_v2 import (
    StructuralFrameRetentionVerificationV2,
    StructuralFrameRetentionVerificationV2Error,
    verify_structural_frame_retention_roots_v2,
)

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_VERIFICATION_V3"
MIN_PIN_BORE_CAPTURE_FRACTION = 0.98
NOMINAL_PIN_BORE_CAPTURE_MM3 = math.pi * CLEVIS_PIN_RADIUS_MM**2 * YOKE_ROOT_BORE_LENGTH_MM
MIN_PIN_BORE_CAPTURE_MM3 = MIN_PIN_BORE_CAPTURE_FRACTION * NOMINAL_PIN_BORE_CAPTURE_MM3
CAPTURE_VOLUME_NUMERICAL_REL_TOL = 1e-6
MAX_PIN_BORE_CAPTURE_MM3 = NOMINAL_PIN_BORE_CAPTURE_MM3 * (1.0 + CAPTURE_VOLUME_NUMERICAL_REL_TOL)


class StructuralFrameRetentionVerificationV3Error(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionVerificationV3:
    v2: StructuralFrameRetentionVerificationV2
    minimum_pin_bore_capture_mm3: float = MIN_PIN_BORE_CAPTURE_MM3
    physical_validation_eligible: bool = False

    def validate(self) -> "StructuralFrameRetentionVerificationV3":
        try:
            self.v2.validate()
        except StructuralFrameRetentionVerificationV2Error as exc:
            raise StructuralFrameRetentionVerificationV3Error("V2 prerequisite verification failed") from exc
        if not math.isfinite(self.minimum_pin_bore_capture_mm3) or self.minimum_pin_bore_capture_mm3 <= 0.0:
            raise StructuralFrameRetentionVerificationV3Error("minimum bore capture must be finite and positive")
        if self.minimum_pin_bore_capture_mm3 < MIN_PIN_BORE_CAPTURE_MM3:
            raise StructuralFrameRetentionVerificationV3Error(
                "minimum bore capture cannot weaken the authority floor"
            )
        if self.minimum_pin_bore_capture_mm3 > MAX_PIN_BORE_CAPTURE_MM3:
            raise StructuralFrameRetentionVerificationV3Error(
                "minimum bore capture cannot exceed the nominal pin/bore capture bound"
            )
        for root in self.v2.roots:
            if root.pin_bore_capture_mm3 < self.minimum_pin_bore_capture_mm3:
                raise StructuralFrameRetentionVerificationV3Error(
                    f"{root.root_id} capture pin does not span enough of the nominal yoke bore"
                )
            if root.pin_bore_capture_mm3 > MAX_PIN_BORE_CAPTURE_MM3:
                raise StructuralFrameRetentionVerificationV3Error(
                    f"{root.root_id} capture pin exceeds the nominal pin/bore capture bound"
                )
        if self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionVerificationV3Error(
                "digital capture coverage is not physical validation evidence"
            )
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": SCHEMA,
            "verification_semantics": "FAIL_CLOSED_V2_PLUS_BOUNDED_AXIAL_PIN_BORE_CAPTURE_COVERAGE",
            "nominal_pin_bore_capture_mm3": NOMINAL_PIN_BORE_CAPTURE_MM3,
            "minimum_pin_bore_capture_fraction": MIN_PIN_BORE_CAPTURE_FRACTION,
            "authority_minimum_pin_bore_capture_mm3": MIN_PIN_BORE_CAPTURE_MM3,
            "enforced_minimum_pin_bore_capture_mm3": self.minimum_pin_bore_capture_mm3,
            "maximum_pin_bore_capture_mm3": MAX_PIN_BORE_CAPTURE_MM3,
            "capture_volume_numerical_relative_tolerance": CAPTURE_VOLUME_NUMERICAL_REL_TOL,
            "measured_pin_bore_capture_mm3": {
                root.root_id: root.pin_bore_capture_mm3 for root in self.v2.roots
            },
            "physical_validation_eligible": False,
        }


def verify_structural_frame_retention_roots_v3() -> StructuralFrameRetentionVerificationV3:
    return StructuralFrameRetentionVerificationV3(
        v2=verify_structural_frame_retention_roots_v2()
    ).validate()
