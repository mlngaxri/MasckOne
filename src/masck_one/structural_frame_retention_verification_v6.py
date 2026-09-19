from __future__ import annotations

"""Physical upper-bound verification for retention-root source-frame capture.

V5 proves bilateral consistency, but two equally impossible capture volumes could still
pass. V6 binds each measured source-frame intersection to the independently measured
volume of its frame counterpart. An intersection cannot contain more material than the
counterpart body itself. This remains digital geometry evidence only.
"""

from dataclasses import dataclass
import math

from .model import MasckOneModel, build_model
from .structural_frame_retention_roots import (
    StructuralFrameRetentionRootArchitecture,
    build_structural_frame_retention_roots,
)
from .structural_frame_retention_verification_v5 import (
    StructuralFrameRetentionVerificationV5,
    StructuralFrameRetentionVerificationV5Error,
    verify_structural_frame_retention_roots_v5,
)

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_VERIFICATION_V6"
CAPTURE_VOLUME_RELATIVE_NUMERICAL_TOLERANCE = 1e-6
EXPECTED_ROOT_IDS = frozenset({"RETENTION_ROOT_WEARER_LEFT", "RETENTION_ROOT_WEARER_RIGHT"})


class StructuralFrameRetentionVerificationV6Error(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionVerificationV6:
    v5: StructuralFrameRetentionVerificationV5
    frame_counterpart_volumes_mm3: tuple[tuple[str, float], ...]
    physical_validation_eligible: bool = False

    def validate(self) -> "StructuralFrameRetentionVerificationV6":
        try:
            self.v5.validate()
        except StructuralFrameRetentionVerificationV5Error as exc:
            raise StructuralFrameRetentionVerificationV6Error("V5 prerequisite verification failed") from exc

        capacities = dict(self.frame_counterpart_volumes_mm3)
        if len(capacities) != 2 or set(capacities) != EXPECTED_ROOT_IDS:
            raise StructuralFrameRetentionVerificationV6Error(
                "counterpart capacities require exactly one wearer-left and one wearer-right root"
            )
        captures = {root.root_id: root.source_frame_capture_mm3 for root in self.v5.v4.v3.v2.roots}
        for root_id in EXPECTED_ROOT_IDS:
            capacity = capacities[root_id]
            capture = captures[root_id]
            if not math.isfinite(capacity) or capacity <= 0.0:
                raise StructuralFrameRetentionVerificationV6Error(
                    f"{root_id} counterpart volume must be finite and positive"
                )
            maximum = capacity * (1.0 + CAPTURE_VOLUME_RELATIVE_NUMERICAL_TOLERANCE)
            if capture > maximum:
                raise StructuralFrameRetentionVerificationV6Error(
                    f"{root_id} source-frame capture exceeds physical counterpart volume"
                )
        if self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionVerificationV6Error(
                "digital capture-volume bounds are not physical validation evidence"
            )
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        captures = {root.root_id: root.source_frame_capture_mm3 for root in self.v5.v4.v3.v2.roots}
        capacities = dict(self.frame_counterpart_volumes_mm3)
        return {
            "schema": SCHEMA,
            "verification_semantics": "FAIL_CLOSED_V5_PLUS_SOURCE_CAPTURE_PHYSICAL_VOLUME_BOUND",
            "capture_volume_relative_numerical_tolerance": CAPTURE_VOLUME_RELATIVE_NUMERICAL_TOLERANCE,
            "roots": [
                {
                    "root_id": root_id,
                    "source_frame_capture_mm3": captures[root_id],
                    "frame_counterpart_volume_mm3": capacities[root_id],
                    "source_frame_capture_fraction": captures[root_id] / capacities[root_id],
                }
                for root_id in sorted(EXPECTED_ROOT_IDS)
            ],
            "physical_validation_eligible": False,
        }


def verify_structural_frame_retention_roots_v6(
    *,
    model: MasckOneModel | None = None,
    architecture: StructuralFrameRetentionRootArchitecture | None = None,
) -> StructuralFrameRetentionVerificationV6:
    model = build_model() if model is None else model
    architecture = build_structural_frame_retention_roots(model=model) if architecture is None else architecture
    if type(model) is not MasckOneModel or type(architecture) is not StructuralFrameRetentionRootArchitecture:
        raise StructuralFrameRetentionVerificationV6Error("exact model and retention-root architecture types are required")
    root_ids = {root.root_id for root in architecture.roots}
    if len(architecture.roots) != 2 or root_ids != EXPECTED_ROOT_IDS:
        raise StructuralFrameRetentionVerificationV6Error(
            "retention architecture must contain exactly one wearer-left and one wearer-right root"
        )
    capacities: list[tuple[str, float]] = []
    for root in architecture.roots:
        try:
            body = root.frame_counterpart.val()
            volume = float(body.Volume())
        except Exception as exc:
            raise StructuralFrameRetentionVerificationV6Error(
                "frame-counterpart volume query failed closed"
            ) from exc
        if not body.isValid() or not math.isfinite(volume) or volume <= 0.0:
            raise StructuralFrameRetentionVerificationV6Error(
                "frame-counterpart body must be valid with finite positive volume"
            )
        capacities.append((root.root_id, volume))

    return StructuralFrameRetentionVerificationV6(
        v5=verify_structural_frame_retention_roots_v5(),
        frame_counterpart_volumes_mm3=tuple(capacities),
    ).validate()
