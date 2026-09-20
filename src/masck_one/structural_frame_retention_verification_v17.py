from __future__ import annotations

"""Independent V17 registration check for the frame-side capture-pin bores.

The clevis-bore repair proves breakthrough, material preservation, and zero pin/frame
intersection. Those conditions alone can still accept a laterally shifted pin inside a
larger bore. This verifier binds the actual capture-pin and bore B-reps to one X/Z axis
at each bilateral root and checks mirror registration between roots.

Digital geometry only. This does not establish manufactured coaxiality, tolerance
capability, bearing performance, strength, wear, or physical service performance.
"""

from dataclasses import dataclass
import math

import cadquery as cq

from .structural_frame_retention_clevis_bores import (
    StructuralFrameRetentionClevisBoreArchitecture,
    build_structural_frame_retention_clevis_bores,
)
from .structural_frame_retention_roots import (
    ROOT_IDS,
    StructuralFrameRetentionRootArchitecture,
    build_structural_frame_retention_roots,
)

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_VERIFICATION_V17"
AXIS_REGISTRATION_TOLERANCE_MM = 1e-6


class StructuralFrameRetentionVerificationV17Error(ValueError):
    pass


def _axis_xz(shape: cq.Workplane, label: str) -> tuple[float, float]:
    try:
        box = shape.val().BoundingBox()
        axis = (float((box.xmin + box.xmax) / 2.0), float((box.zmin + box.zmax) / 2.0))
    except Exception as exc:
        raise StructuralFrameRetentionVerificationV17Error(f"{label} axis query failed") from exc
    if not all(math.isfinite(value) for value in axis):
        raise StructuralFrameRetentionVerificationV17Error(f"{label} axis evidence must be finite")
    return axis


@dataclass(frozen=True, slots=True)
class RootAxisRegistration:
    root_id: str
    pin_axis_xz_mm: tuple[float, float]
    bore_axis_xz_mm: tuple[float, float]
    pin_bore_axis_offset_mm: float

    def validate(self) -> "RootAxisRegistration":
        if self.root_id not in ROOT_IDS:
            raise StructuralFrameRetentionVerificationV17Error("unknown retention root")
        values = (*self.pin_axis_xz_mm, *self.bore_axis_xz_mm, self.pin_bore_axis_offset_mm)
        if not all(math.isfinite(float(value)) for value in values):
            raise StructuralFrameRetentionVerificationV17Error("axis registration evidence must be finite")
        expected = math.hypot(
            self.pin_axis_xz_mm[0] - self.bore_axis_xz_mm[0],
            self.pin_axis_xz_mm[1] - self.bore_axis_xz_mm[1],
        )
        if not math.isclose(self.pin_bore_axis_offset_mm, expected, rel_tol=0.0, abs_tol=1e-12):
            raise StructuralFrameRetentionVerificationV17Error("recorded pin/bore axis offset disagrees with B-rep axes")
        if self.pin_bore_axis_offset_mm > AXIS_REGISTRATION_TOLERANCE_MM:
            raise StructuralFrameRetentionVerificationV17Error("capture pin and clevis bore are not coaxial")
        return self


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionVerificationV17:
    roots: tuple[RootAxisRegistration, ...]
    physical_validation_eligible: bool = False

    def validate(self) -> "StructuralFrameRetentionVerificationV17":
        if tuple(root.root_id for root in self.roots) != ROOT_IDS:
            raise StructuralFrameRetentionVerificationV17Error("both bilateral roots are required in controlled order")
        for root in self.roots:
            root.validate()
        left, right = self.roots
        if abs(left.bore_axis_xz_mm[0] + right.bore_axis_xz_mm[0]) > AXIS_REGISTRATION_TOLERANCE_MM:
            raise StructuralFrameRetentionVerificationV17Error("bilateral clevis bore X axes are not mirror registered")
        if abs(left.bore_axis_xz_mm[1] - right.bore_axis_xz_mm[1]) > AXIS_REGISTRATION_TOLERANCE_MM:
            raise StructuralFrameRetentionVerificationV17Error("bilateral clevis bore Z axes are not registered")
        if self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionVerificationV17Error("digital axis registration is not physical validation evidence")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": SCHEMA,
            "axis_registration_tolerance_mm": AXIS_REGISTRATION_TOLERANCE_MM,
            "roots": [
                {
                    "root_id": root.root_id,
                    "pin_axis_xz_mm": list(root.pin_axis_xz_mm),
                    "bore_axis_xz_mm": list(root.bore_axis_xz_mm),
                    "pin_bore_axis_offset_mm": root.pin_bore_axis_offset_mm,
                }
                for root in self.roots
            ],
            "physical_validation_eligible": False,
        }


def build_structural_frame_retention_verification_v17(
    *,
    roots: StructuralFrameRetentionRootArchitecture | None = None,
    bores: StructuralFrameRetentionClevisBoreArchitecture | None = None,
) -> StructuralFrameRetentionVerificationV17:
    roots = build_structural_frame_retention_roots() if roots is None else roots
    bores = build_structural_frame_retention_clevis_bores(architecture=roots) if bores is None else bores
    if type(roots) is not StructuralFrameRetentionRootArchitecture or type(bores) is not StructuralFrameRetentionClevisBoreArchitecture:
        raise StructuralFrameRetentionVerificationV17Error("exact retention-root and clevis-bore architecture types are required")

    registrations: list[RootAxisRegistration] = []
    for root, bore in zip(roots.roots, bores.roots, strict=True):
        if root.root_id != bore.root_id:
            raise StructuralFrameRetentionVerificationV17Error("retention-root and clevis-bore identities do not align")
        pin_axis = _axis_xz(root.capture_pin, f"{root.root_id} capture pin")
        bore_axis = _axis_xz(bore.bore_reference, f"{root.root_id} clevis bore")
        registrations.append(
            RootAxisRegistration(
                root_id=root.root_id,
                pin_axis_xz_mm=pin_axis,
                bore_axis_xz_mm=bore_axis,
                pin_bore_axis_offset_mm=math.hypot(pin_axis[0] - bore_axis[0], pin_axis[1] - bore_axis[1]),
            ).validate()
        )
    return StructuralFrameRetentionVerificationV17(roots=tuple(registrations)).validate()
