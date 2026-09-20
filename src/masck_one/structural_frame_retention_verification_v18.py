from __future__ import annotations

"""V18 integrated-frame collision gate for the bilateral retention capture pins.

The clevis-bore layer proves each pin clears its corrected local clevis counterpart.
That local proof does not establish that the same installed pin clears every other
piece of the assembled structural frame. V18 therefore intersects each actual pin
B-rep with the fully corrected frame after both clevis bores have been cut.

Digital geometry only. This does not establish manufactured clearance, strength,
wear, release force, service access, or physical safety performance.
"""

from dataclasses import dataclass
import math

import cadquery as cq

from .structural_frame_retention_clevis_bores import (
    INTERSECTION_TOLERANCE_MM3,
    StructuralFrameRetentionClevisBoreArchitecture,
    build_structural_frame_retention_clevis_bores,
)
from .structural_frame_retention_roots import (
    ROOT_IDS,
    StructuralFrameRetentionRootArchitecture,
    build_structural_frame_retention_roots,
)

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_VERIFICATION_V18"


class StructuralFrameRetentionVerificationV18Error(ValueError):
    pass


def _intersection_mm3(a: cq.Workplane, b: cq.Workplane, label: str) -> float:
    try:
        value = float(a.intersect(b).val().Volume())
    except Exception as exc:
        raise StructuralFrameRetentionVerificationV18Error(f"{label} intersection query failed") from exc
    if not math.isfinite(value) or value < 0.0:
        raise StructuralFrameRetentionVerificationV18Error(f"{label} intersection evidence must be finite and nonnegative")
    return 0.0 if value <= INTERSECTION_TOLERANCE_MM3 else value


@dataclass(frozen=True, slots=True)
class RootIntegratedFrameClearance:
    root_id: str
    pin_integrated_frame_intersection_mm3: float

    def validate(self) -> "RootIntegratedFrameClearance":
        if self.root_id not in ROOT_IDS:
            raise StructuralFrameRetentionVerificationV18Error("unknown retention root")
        value = float(self.pin_integrated_frame_intersection_mm3)
        if not math.isfinite(value) or value < 0.0:
            raise StructuralFrameRetentionVerificationV18Error("integrated-frame intersection evidence must be finite and nonnegative")
        if value > INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameRetentionVerificationV18Error("capture pin intersects integrated structural frame")
        return self


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionVerificationV18:
    roots: tuple[RootIntegratedFrameClearance, ...]
    physical_validation_eligible: bool = False

    def validate(self) -> "StructuralFrameRetentionVerificationV18":
        if tuple(root.root_id for root in self.roots) != ROOT_IDS:
            raise StructuralFrameRetentionVerificationV18Error("both bilateral roots are required in controlled order")
        for root in self.roots:
            root.validate()
        if self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionVerificationV18Error("digital integrated-frame clearance is not physical validation evidence")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": SCHEMA,
            "intersection_tolerance_mm3": INTERSECTION_TOLERANCE_MM3,
            "roots": [
                {
                    "root_id": root.root_id,
                    "pin_integrated_frame_intersection_mm3": root.pin_integrated_frame_intersection_mm3,
                }
                for root in self.roots
            ],
            "physical_validation_eligible": False,
        }


def build_structural_frame_retention_verification_v18(
    *,
    roots: StructuralFrameRetentionRootArchitecture | None = None,
    bores: StructuralFrameRetentionClevisBoreArchitecture | None = None,
) -> StructuralFrameRetentionVerificationV18:
    roots = build_structural_frame_retention_roots() if roots is None else roots
    bores = build_structural_frame_retention_clevis_bores(architecture=roots) if bores is None else bores
    if type(roots) is not StructuralFrameRetentionRootArchitecture or type(bores) is not StructuralFrameRetentionClevisBoreArchitecture:
        raise StructuralFrameRetentionVerificationV18Error("exact retention-root and clevis-bore architecture types are required")
    if tuple(root.root_id for root in roots.roots) != tuple(root.root_id for root in bores.roots):
        raise StructuralFrameRetentionVerificationV18Error("retention-root and clevis-bore identities do not align")

    evidence = tuple(
        RootIntegratedFrameClearance(
            root_id=root.root_id,
            pin_integrated_frame_intersection_mm3=_intersection_mm3(
                root.capture_pin,
                bores.frame_with_clevis_bores,
                f"{root.root_id} pin/integrated frame",
            ),
        ).validate()
        for root in roots.roots
    )
    return StructuralFrameRetentionVerificationV18(roots=evidence).validate()
