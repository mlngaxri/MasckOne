from __future__ import annotations

"""Fail closed unless installed capture-pin material volume matches structural authority.

V14 binds the pin outer length and head radius. V15 closes a remaining internal-geometry
blind spot by independently measuring each installed capture-pin B-rep volume and comparing
it with the analytical shaft, head, and annular-groove volume implied by the structural-root
authority constants. This is digital geometry evidence only, not strength or tolerance proof.
"""

from dataclasses import dataclass
import math

from .model import MasckOneModel, build_model
from .structural_frame_retention_roots import (
    CLEVIS_EAR_Y_THICKNESS_MM,
    CLEVIS_PIN_DISTAL_EXTENSION_MM,
    CLEVIS_PIN_GROOVE_DEPTH_MM,
    CLEVIS_PIN_GROOVE_WIDTH_MM,
    CLEVIS_PIN_HEAD_RADIUS_MM,
    CLEVIS_PIN_HEAD_THICKNESS_MM,
    CLEVIS_PIN_RADIUS_MM,
    CLEVIS_SIDE_CLEARANCE_MM,
    YOKE_ROOT_BOSS_XYZ_MM,
    StructuralFrameRetentionRootArchitecture,
    build_structural_frame_retention_roots,
)
from .structural_frame_retention_verification_v14 import (
    StructuralFrameRetentionVerificationV14,
    StructuralFrameRetentionVerificationV14Error,
    verify_structural_frame_retention_roots_v14,
)

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_VERIFICATION_V15"
EXPECTED_ROOT_IDS = frozenset({"RETENTION_ROOT_WEARER_LEFT", "RETENTION_ROOT_WEARER_RIGHT"})
VOLUME_NUMERICAL_TOLERANCE_MM3 = 1e-6
EXPECTED_PIN_STACK_Y_MM = YOKE_ROOT_BOSS_XYZ_MM[1] + 2.0 * (
    CLEVIS_SIDE_CLEARANCE_MM + CLEVIS_EAR_Y_THICKNESS_MM
)
EXPECTED_SHAFT_LENGTH_MM = EXPECTED_PIN_STACK_Y_MM + CLEVIS_PIN_DISTAL_EXTENSION_MM
EXPECTED_GROOVE_BOTTOM_RADIUS_MM = CLEVIS_PIN_RADIUS_MM - CLEVIS_PIN_GROOVE_DEPTH_MM
EXPECTED_PIN_VOLUME_MM3 = (
    math.pi * CLEVIS_PIN_RADIUS_MM**2 * EXPECTED_SHAFT_LENGTH_MM
    + math.pi * CLEVIS_PIN_HEAD_RADIUS_MM**2 * CLEVIS_PIN_HEAD_THICKNESS_MM
    - math.pi
    * (CLEVIS_PIN_RADIUS_MM**2 - EXPECTED_GROOVE_BOTTOM_RADIUS_MM**2)
    * CLEVIS_PIN_GROOVE_WIDTH_MM
)


class StructuralFrameRetentionVerificationV15Error(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionVerificationV15:
    v14: StructuralFrameRetentionVerificationV14
    pin_volumes_mm3: tuple[tuple[str, float], ...]
    physical_validation_eligible: bool = False

    def validate(self) -> "StructuralFrameRetentionVerificationV15":
        try:
            self.v14.validate()
        except StructuralFrameRetentionVerificationV14Error as exc:
            raise StructuralFrameRetentionVerificationV15Error("V14 prerequisite verification failed") from exc
        volumes = dict(self.pin_volumes_mm3)
        if len(volumes) != 2 or set(volumes) != EXPECTED_ROOT_IDS:
            raise StructuralFrameRetentionVerificationV15Error(
                "pin volumes require exactly one wearer-left and one wearer-right root"
            )
        for root_id in EXPECTED_ROOT_IDS:
            volume = volumes[root_id]
            if not math.isfinite(volume) or abs(volume - EXPECTED_PIN_VOLUME_MM3) > VOLUME_NUMERICAL_TOLERANCE_MM3:
                raise StructuralFrameRetentionVerificationV15Error(
                    f"{root_id} capture-pin material volume drifted from structural authority"
                )
        if self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionVerificationV15Error(
                "digital capture-pin material authority is not physical validation evidence"
            )
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        volumes = dict(self.pin_volumes_mm3)
        return {
            "schema": SCHEMA,
            "verification_semantics": "FAIL_CLOSED_V14_PLUS_CAPTURE_PIN_MATERIAL_VOLUME_AUTHORITY",
            "volume_numerical_tolerance_mm3": VOLUME_NUMERICAL_TOLERANCE_MM3,
            "expected_pin_volume_mm3": EXPECTED_PIN_VOLUME_MM3,
            "authority": {
                "shaft_radius_mm": CLEVIS_PIN_RADIUS_MM,
                "shaft_length_mm": EXPECTED_SHAFT_LENGTH_MM,
                "head_radius_mm": CLEVIS_PIN_HEAD_RADIUS_MM,
                "head_thickness_mm": CLEVIS_PIN_HEAD_THICKNESS_MM,
                "groove_depth_mm": CLEVIS_PIN_GROOVE_DEPTH_MM,
                "groove_width_mm": CLEVIS_PIN_GROOVE_WIDTH_MM,
                "groove_bottom_radius_mm": EXPECTED_GROOVE_BOTTOM_RADIUS_MM,
            },
            "roots": [
                {"root_id": root_id, "pin_volume_mm3": volumes[root_id]}
                for root_id in sorted(EXPECTED_ROOT_IDS)
            ],
            "physical_validation_eligible": False,
        }


def verify_structural_frame_retention_roots_v15(
    *, model: MasckOneModel | None = None,
    architecture: StructuralFrameRetentionRootArchitecture | None = None,
) -> StructuralFrameRetentionVerificationV15:
    model = build_model() if model is None else model
    architecture = build_structural_frame_retention_roots(model=model) if architecture is None else architecture
    if type(model) is not MasckOneModel or type(architecture) is not StructuralFrameRetentionRootArchitecture:
        raise StructuralFrameRetentionVerificationV15Error("exact model and retention-root architecture types are required")
    if len(architecture.roots) != 2 or {root.root_id for root in architecture.roots} != EXPECTED_ROOT_IDS:
        raise StructuralFrameRetentionVerificationV15Error(
            "retention architecture must contain exactly one wearer-left and one wearer-right root"
        )

    volumes: list[tuple[str, float]] = []
    for root in architecture.roots:
        try:
            volume = float(root.capture_pin.val().Volume())
        except Exception as exc:
            raise StructuralFrameRetentionVerificationV15Error(
                "capture-pin material-volume B-rep query failed"
            ) from exc
        volumes.append((root.root_id, volume))

    v14 = verify_structural_frame_retention_roots_v14(model=model, architecture=architecture)
    return StructuralFrameRetentionVerificationV15(
        v14=v14,
        pin_volumes_mm3=tuple(volumes),
    ).validate()
