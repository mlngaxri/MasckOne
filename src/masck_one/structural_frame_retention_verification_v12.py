from __future__ import annotations

"""Fail closed on split-retainer collisions with its local mating structure.

V11 proves groove seating and pin non-interference. V12 closes the adjacent packaging
gap by independently checking each installed split retainer against the frame-integral
clevis counterpart and nominal yoke-root material. This remains digital geometry
evidence only and does not establish service access or physical removal performance.
"""

from dataclasses import dataclass
import math

from .model import MasckOneModel, build_model
from .structural_frame_retention_roots import (
    StructuralFrameRetentionRootArchitecture,
    build_structural_frame_retention_roots,
)
from .structural_frame_retention_verification_v11 import (
    StructuralFrameRetentionVerificationV11,
    StructuralFrameRetentionVerificationV11Error,
    verify_structural_frame_retention_roots_v11,
)

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_VERIFICATION_V12"
EXPECTED_ROOT_IDS = frozenset({"RETENTION_ROOT_WEARER_LEFT", "RETENTION_ROOT_WEARER_RIGHT"})
INTERFERENCE_TOLERANCE_MM3 = 1e-7


class StructuralFrameRetentionVerificationV12Error(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionVerificationV12:
    v11: StructuralFrameRetentionVerificationV11
    retainer_frame_intersections_mm3: tuple[tuple[str, float], ...]
    retainer_yoke_intersections_mm3: tuple[tuple[str, float], ...]
    physical_validation_eligible: bool = False

    def validate(self) -> "StructuralFrameRetentionVerificationV12":
        try:
            self.v11.validate()
        except StructuralFrameRetentionVerificationV11Error as exc:
            raise StructuralFrameRetentionVerificationV12Error("V11 prerequisite verification failed") from exc
        frame = dict(self.retainer_frame_intersections_mm3)
        yoke = dict(self.retainer_yoke_intersections_mm3)
        if len(frame) != 2 or set(frame) != EXPECTED_ROOT_IDS:
            raise StructuralFrameRetentionVerificationV12Error(
                "frame intersections require exactly one wearer-left and one wearer-right root"
            )
        if len(yoke) != 2 or set(yoke) != EXPECTED_ROOT_IDS:
            raise StructuralFrameRetentionVerificationV12Error(
                "yoke intersections require exactly one wearer-left and one wearer-right root"
            )
        for root_id in EXPECTED_ROOT_IDS:
            for label, value in (("frame counterpart", frame[root_id]), ("yoke material", yoke[root_id])):
                if not math.isfinite(value) or value < 0.0:
                    raise StructuralFrameRetentionVerificationV12Error(
                        f"{root_id} retainer/{label} intersection must be finite and nonnegative"
                    )
                if value > INTERFERENCE_TOLERANCE_MM3:
                    raise StructuralFrameRetentionVerificationV12Error(
                        f"{root_id} split retainer volumetrically interferes with {label}"
                    )
        if self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionVerificationV12Error(
                "digital local packaging is not physical validation evidence"
            )
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        frame = dict(self.retainer_frame_intersections_mm3)
        yoke = dict(self.retainer_yoke_intersections_mm3)
        return {
            "schema": SCHEMA,
            "verification_semantics": "FAIL_CLOSED_V11_PLUS_SPLIT_RETAINER_LOCAL_PACKAGING",
            "interference_tolerance_mm3": INTERFERENCE_TOLERANCE_MM3,
            "roots": [
                {
                    "root_id": root_id,
                    "retainer_frame_intersection_mm3": frame[root_id],
                    "retainer_yoke_intersection_mm3": yoke[root_id],
                }
                for root_id in sorted(EXPECTED_ROOT_IDS)
            ],
            "service_access_verified": False,
            "physical_validation_eligible": False,
        }


def verify_structural_frame_retention_roots_v12(
    *, model: MasckOneModel | None = None,
    architecture: StructuralFrameRetentionRootArchitecture | None = None,
) -> StructuralFrameRetentionVerificationV12:
    model = build_model() if model is None else model
    architecture = build_structural_frame_retention_roots(model=model) if architecture is None else architecture
    if type(model) is not MasckOneModel or type(architecture) is not StructuralFrameRetentionRootArchitecture:
        raise StructuralFrameRetentionVerificationV12Error("exact model and retention-root architecture types are required")
    if len(architecture.roots) != 2 or {root.root_id for root in architecture.roots} != EXPECTED_ROOT_IDS:
        raise StructuralFrameRetentionVerificationV12Error(
            "retention architecture must contain exactly one wearer-left and one wearer-right root"
        )

    frame_intersections: list[tuple[str, float]] = []
    yoke_intersections: list[tuple[str, float]] = []
    for root in architecture.roots:
        try:
            frame_intersection = float(root.split_retainer.intersect(root.frame_counterpart).val().Volume())
            yoke_intersection = float(root.split_retainer.intersect(root.yoke_root_reference).val().Volume())
        except Exception as exc:
            raise StructuralFrameRetentionVerificationV12Error(
                "split-retainer local packaging B-rep query failed"
            ) from exc
        frame_intersections.append((root.root_id, frame_intersection))
        yoke_intersections.append((root.root_id, yoke_intersection))

    v11 = verify_structural_frame_retention_roots_v11(model=model, architecture=architecture)
    return StructuralFrameRetentionVerificationV12(
        v11=v11,
        retainer_frame_intersections_mm3=tuple(frame_intersections),
        retainer_yoke_intersections_mm3=tuple(yoke_intersections),
    ).validate()
