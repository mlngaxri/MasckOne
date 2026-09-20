from __future__ import annotations

"""Fail closed unless bilateral installed capture-pin mass properties remain symmetric.

V15 binds each pin's scalar material volume to structural authority. V16 closes a remaining
bilateral blind spot by independently comparing installed B-rep centers of mass. Equal volume
alone cannot detect mirrored-root placement drift or asymmetric internal material relocation.
This remains digital geometry evidence only, not manufactured tolerance or strength proof.
"""

from dataclasses import dataclass
import math

from .model import MasckOneModel, build_model
from .structural_frame_retention_roots import (
    StructuralFrameRetentionRootArchitecture,
    build_structural_frame_retention_roots,
)
from .structural_frame_retention_verification_v15 import (
    StructuralFrameRetentionVerificationV15,
    StructuralFrameRetentionVerificationV15Error,
    verify_structural_frame_retention_roots_v15,
)

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_VERIFICATION_V16"
EXPECTED_ROOT_IDS = frozenset({"RETENTION_ROOT_WEARER_LEFT", "RETENTION_ROOT_WEARER_RIGHT"})
COM_SYMMETRY_NUMERICAL_TOLERANCE_MM = 1e-6


class StructuralFrameRetentionVerificationV16Error(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionVerificationV16:
    v15: StructuralFrameRetentionVerificationV15
    pin_centers_of_mass_mm: tuple[tuple[str, tuple[float, float, float]], ...]
    physical_validation_eligible: bool = False

    def validate(self) -> "StructuralFrameRetentionVerificationV16":
        try:
            self.v15.validate()
        except StructuralFrameRetentionVerificationV15Error as exc:
            raise StructuralFrameRetentionVerificationV16Error("V15 prerequisite verification failed") from exc
        centers = dict(self.pin_centers_of_mass_mm)
        if len(centers) != 2 or set(centers) != EXPECTED_ROOT_IDS:
            raise StructuralFrameRetentionVerificationV16Error(
                "pin centers of mass require exactly one wearer-left and one wearer-right root"
            )
        left = centers["RETENTION_ROOT_WEARER_LEFT"]
        right = centers["RETENTION_ROOT_WEARER_RIGHT"]
        if any(len(value) != 3 or not all(math.isfinite(component) for component in value) for value in (left, right)):
            raise StructuralFrameRetentionVerificationV16Error("capture-pin center-of-mass evidence must be finite XYZ")
        residuals = (left[0] + right[0], left[1] - right[1], left[2] - right[2])
        if any(abs(value) > COM_SYMMETRY_NUMERICAL_TOLERANCE_MM for value in residuals):
            raise StructuralFrameRetentionVerificationV16Error(
                "installed capture-pin centers of mass violate bilateral mirror symmetry"
            )
        if self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionVerificationV16Error(
                "digital capture-pin symmetry is not physical validation evidence"
            )
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        centers = dict(self.pin_centers_of_mass_mm)
        left = centers["RETENTION_ROOT_WEARER_LEFT"]
        right = centers["RETENTION_ROOT_WEARER_RIGHT"]
        return {
            "schema": SCHEMA,
            "verification_semantics": "FAIL_CLOSED_V15_PLUS_CAPTURE_PIN_BILATERAL_COM_SYMMETRY",
            "com_symmetry_numerical_tolerance_mm": COM_SYMMETRY_NUMERICAL_TOLERANCE_MM,
            "symmetry_residual_xyz_mm": (left[0] + right[0], left[1] - right[1], left[2] - right[2]),
            "roots": [
                {"root_id": root_id, "pin_center_of_mass_xyz_mm": centers[root_id]}
                for root_id in sorted(EXPECTED_ROOT_IDS)
            ],
            "physical_validation_eligible": False,
        }


def verify_structural_frame_retention_roots_v16(
    *, model: MasckOneModel | None = None,
    architecture: StructuralFrameRetentionRootArchitecture | None = None,
) -> StructuralFrameRetentionVerificationV16:
    model = build_model() if model is None else model
    architecture = build_structural_frame_retention_roots(model=model) if architecture is None else architecture
    if type(model) is not MasckOneModel or type(architecture) is not StructuralFrameRetentionRootArchitecture:
        raise StructuralFrameRetentionVerificationV16Error("exact model and retention-root architecture types are required")
    if len(architecture.roots) != 2 or {root.root_id for root in architecture.roots} != EXPECTED_ROOT_IDS:
        raise StructuralFrameRetentionVerificationV16Error(
            "retention architecture must contain exactly one wearer-left and one wearer-right root"
        )

    centers: list[tuple[str, tuple[float, float, float]]] = []
    for root in architecture.roots:
        try:
            center = root.capture_pin.val().CenterOfMass()
            xyz = (float(center.x), float(center.y), float(center.z))
        except Exception as exc:
            raise StructuralFrameRetentionVerificationV16Error(
                "capture-pin center-of-mass B-rep query failed"
            ) from exc
        centers.append((root.root_id, xyz))

    v15 = verify_structural_frame_retention_roots_v15(model=model, architecture=architecture)
    return StructuralFrameRetentionVerificationV16(v15=v15, pin_centers_of_mass_mm=tuple(centers)).validate()
