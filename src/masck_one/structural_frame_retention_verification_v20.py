from __future__ import annotations

"""V20 binds retention roots to the current source reaction architecture.

A retention-root object can be supplied alongside a different MasckOneModel because
runtime type checks alone do not prove common provenance. V20 independently rebuilds
the source reaction architecture from the supplied model and requires the retention
root provenance digest to match it exactly.

Digital provenance evidence only. This does not establish manufactured fit, strength,
comfort, service force, wear, contamination tolerance, or physical safety performance.
"""

from dataclasses import dataclass

from .model import MasckOneModel, build_model
from .structural_frame_actuator_reactions import build_structural_frame_actuator_reactions
from .structural_frame_retention_roots import (
    StructuralFrameRetentionRootArchitecture,
    build_structural_frame_retention_roots,
)

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_VERIFICATION_V20"


class StructuralFrameRetentionVerificationV20Error(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionVerificationV20:
    recorded_source_sha256: str
    expected_source_sha256: str
    physical_validation_eligible: bool = False

    def validate(self) -> "StructuralFrameRetentionVerificationV20":
        for label, value in (
            ("recorded", self.recorded_source_sha256),
            ("expected", self.expected_source_sha256),
        ):
            if not isinstance(value, str) or len(value) != 64:
                raise StructuralFrameRetentionVerificationV20Error(
                    f"{label} source reaction architecture SHA-256 is invalid"
                )
        if self.recorded_source_sha256 != self.expected_source_sha256:
            raise StructuralFrameRetentionVerificationV20Error(
                "retention roots are not bound to the supplied model's source reaction architecture"
            )
        if self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionVerificationV20Error(
                "digital provenance binding is not physical validation evidence"
            )
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": SCHEMA,
            "recorded_source_frame_reaction_architecture_sha256": self.recorded_source_sha256,
            "expected_source_frame_reaction_architecture_sha256": self.expected_source_sha256,
            "source_binding_match": True,
            "physical_validation_eligible": False,
        }


def build_structural_frame_retention_verification_v20(
    *,
    roots: StructuralFrameRetentionRootArchitecture | None = None,
    model: MasckOneModel | None = None,
) -> StructuralFrameRetentionVerificationV20:
    model = build_model() if model is None else model
    roots = build_structural_frame_retention_roots(model=model) if roots is None else roots
    if type(model) is not MasckOneModel or type(roots) is not StructuralFrameRetentionRootArchitecture:
        raise StructuralFrameRetentionVerificationV20Error(
            "exact model and retention-root architecture types are required"
        )

    expected = build_structural_frame_actuator_reactions(model=model).architecture_sha256
    return StructuralFrameRetentionVerificationV20(
        recorded_source_sha256=roots.source_frame_reaction_architecture_sha256,
        expected_source_sha256=expected,
        physical_validation_eligible=False,
    ).validate()
