from __future__ import annotations

"""V19 fail-closed verification of root/yoke and protected-zone clearance.

The root generator historically treats an OCC intersection exception as zero volume.
That is conservative while searching for frame-capture candidates only when the later
positive-capture test also fails, but it can falsely certify pin/yoke or protected-zone
clearance. V19 independently recomputes those safety-relevant intersections and fails
closed if OCC cannot provide finite non-negative evidence.

Digital geometry only. This does not establish manufactured clearance, strength, fit,
comfort, service force, wear, contamination tolerance, or physical safety performance.
"""

from dataclasses import dataclass
import math

import cadquery as cq

from .model import MasckOneModel, build_model
from .structural_frame_realization import _protected_zone_solid
from .structural_frame_retention_roots import (
    ROOT_IDS,
    ROOT_Z_MM,
    StructuralFrameRetentionRootArchitecture,
    build_structural_frame_retention_roots,
)

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_VERIFICATION_V19"
INTERSECTION_TOLERANCE_MM3 = 1e-7


class StructuralFrameRetentionVerificationV19Error(ValueError):
    pass


def _intersection_mm3(a: cq.Workplane, b: cq.Workplane, label: str) -> float:
    try:
        value = float(a.intersect(b).val().Volume())
    except Exception as exc:
        raise StructuralFrameRetentionVerificationV19Error(
            f"{label} intersection query failed; clearance evidence is unavailable"
        ) from exc
    if not math.isfinite(value) or value < 0.0:
        raise StructuralFrameRetentionVerificationV19Error(
            f"{label} intersection evidence must be finite and nonnegative"
        )
    return 0.0 if value <= INTERSECTION_TOLERANCE_MM3 else value


@dataclass(frozen=True, slots=True)
class RootKeepoutClearance:
    root_id: str
    pin_yoke_intersection_mm3: float
    protected_intersection_mm3: float

    def validate(self) -> "RootKeepoutClearance":
        if self.root_id not in ROOT_IDS:
            raise StructuralFrameRetentionVerificationV19Error("unknown retention root")
        for label, value in (
            ("pin/yoke", self.pin_yoke_intersection_mm3),
            ("root/protected", self.protected_intersection_mm3),
        ):
            if not math.isfinite(value) or value < 0.0:
                raise StructuralFrameRetentionVerificationV19Error(
                    f"{label} evidence must be finite and nonnegative"
                )
            if value > INTERSECTION_TOLERANCE_MM3:
                raise StructuralFrameRetentionVerificationV19Error(
                    f"{label} material collision exceeds digital tolerance"
                )
        return self


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionVerificationV19:
    roots: tuple[RootKeepoutClearance, ...]
    physical_validation_eligible: bool = False

    def validate(self) -> "StructuralFrameRetentionVerificationV19":
        if tuple(root.root_id for root in self.roots) != ROOT_IDS:
            raise StructuralFrameRetentionVerificationV19Error(
                "both bilateral roots are required in controlled order"
            )
        for root in self.roots:
            root.validate()
        if self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionVerificationV19Error(
                "digital keepout clearance is not physical validation evidence"
            )
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": SCHEMA,
            "intersection_tolerance_mm3": INTERSECTION_TOLERANCE_MM3,
            "roots": [
                {
                    "root_id": root.root_id,
                    "pin_yoke_intersection_mm3": root.pin_yoke_intersection_mm3,
                    "protected_intersection_mm3": root.protected_intersection_mm3,
                }
                for root in self.roots
            ],
            "physical_validation_eligible": False,
        }


def build_structural_frame_retention_verification_v19(
    *,
    roots: StructuralFrameRetentionRootArchitecture | None = None,
    model: MasckOneModel | None = None,
) -> StructuralFrameRetentionVerificationV19:
    model = build_model() if model is None else model
    roots = build_structural_frame_retention_roots(model=model) if roots is None else roots
    if type(model) is not MasckOneModel or type(roots) is not StructuralFrameRetentionRootArchitecture:
        raise StructuralFrameRetentionVerificationV19Error(
            "exact model and retention-root architecture types are required"
        )

    frame_bb = roots.frame_with_retention_roots.val().BoundingBox()
    z_min = min(ROOT_Z_MM - 10.0, float(frame_bb.zmin) - 2.0)
    z_max = max(ROOT_Z_MM + 10.0, float(frame_bb.zmax) + 2.0)
    evidence: list[RootKeepoutClearance] = []

    for root in roots.roots:
        protected_total = 0.0
        for protected in model.protected_volumes.all:
            zone = protected.zone
            keepout = _protected_zone_solid(
                center_x_mm=zone.center.x,
                center_y_mm=zone.center.y,
                envelope_width_mm=zone.envelope_width_mm,
                envelope_height_mm=zone.envelope_height_mm,
                angle_deg=zone.angle_deg,
                z_min_mm=z_min,
                z_max_mm=z_max,
            )
            protected_total += _intersection_mm3(
                root.frame_counterpart,
                keepout,
                f"{root.root_id} root/protected-zone",
            )

        evidence.append(
            RootKeepoutClearance(
                root_id=root.root_id,
                pin_yoke_intersection_mm3=_intersection_mm3(
                    root.capture_pin,
                    root.yoke_root_reference,
                    f"{root.root_id} pin/yoke",
                ),
                protected_intersection_mm3=protected_total,
            ).validate()
        )

    return StructuralFrameRetentionVerificationV19(tuple(evidence), False).validate()
