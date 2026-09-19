from __future__ import annotations

"""Cross-check generated retention-root capture metadata against independent B-rep evidence.

V6 bounds independently measured source-frame capture by counterpart material volume.
V7 additionally requires the capture volume recorded by the root generator to agree
with that independent measurement. This catches stale metadata, mixed CAD states, or
a generator-side intersection query that silently degraded while the B-rep changed.
"""

from dataclasses import dataclass
import math

from .model import MasckOneModel, build_model
from .structural_frame_retention_roots import (
    StructuralFrameRetentionRootArchitecture,
    build_structural_frame_retention_roots,
)
from .structural_frame_retention_verification_v6 import (
    StructuralFrameRetentionVerificationV6,
    StructuralFrameRetentionVerificationV6Error,
    verify_structural_frame_retention_roots_v6,
)

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_VERIFICATION_V7"
CAPTURE_METADATA_RELATIVE_TOLERANCE = 1e-6
EXPECTED_ROOT_IDS = frozenset({"RETENTION_ROOT_WEARER_LEFT", "RETENTION_ROOT_WEARER_RIGHT"})


class StructuralFrameRetentionVerificationV7Error(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionVerificationV7:
    v6: StructuralFrameRetentionVerificationV6
    generated_capture_volumes_mm3: tuple[tuple[str, float], ...]
    physical_validation_eligible: bool = False

    def validate(self) -> "StructuralFrameRetentionVerificationV7":
        try:
            self.v6.validate()
        except StructuralFrameRetentionVerificationV6Error as exc:
            raise StructuralFrameRetentionVerificationV7Error("V6 prerequisite verification failed") from exc

        generated = dict(self.generated_capture_volumes_mm3)
        if len(generated) != 2 or set(generated) != EXPECTED_ROOT_IDS:
            raise StructuralFrameRetentionVerificationV7Error(
                "generated capture metadata requires exactly one wearer-left and one wearer-right root"
            )
        measured = {
            root.root_id: root.source_frame_capture_mm3
            for root in self.v6.v5.v4.v3.v2.roots
        }
        for root_id in EXPECTED_ROOT_IDS:
            expected = generated[root_id]
            actual = measured[root_id]
            if not math.isfinite(expected) or expected <= 0.0:
                raise StructuralFrameRetentionVerificationV7Error(
                    f"{root_id} generated capture metadata must be finite and positive"
                )
            scale = max(abs(expected), abs(actual), 1.0)
            relative_error = abs(expected - actual) / scale
            if relative_error > CAPTURE_METADATA_RELATIVE_TOLERANCE:
                raise StructuralFrameRetentionVerificationV7Error(
                    f"{root_id} generated capture metadata disagrees with independent B-rep measurement"
                )
        if self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionVerificationV7Error(
                "digital metadata coherence is not physical validation evidence"
            )
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        generated = dict(self.generated_capture_volumes_mm3)
        measured = {root.root_id: root.source_frame_capture_mm3 for root in self.v6.v5.v4.v3.v2.roots}
        return {
            "schema": SCHEMA,
            "verification_semantics": "FAIL_CLOSED_V6_PLUS_GENERATOR_CAPTURE_METADATA_COHERENCE",
            "capture_metadata_relative_tolerance": CAPTURE_METADATA_RELATIVE_TOLERANCE,
            "roots": [
                {
                    "root_id": root_id,
                    "generated_capture_mm3": generated[root_id],
                    "independent_capture_mm3": measured[root_id],
                    "relative_error": abs(generated[root_id] - measured[root_id])
                    / max(abs(generated[root_id]), abs(measured[root_id]), 1.0),
                }
                for root_id in sorted(EXPECTED_ROOT_IDS)
            ],
            "physical_validation_eligible": False,
        }


def verify_structural_frame_retention_roots_v7(
    *,
    model: MasckOneModel | None = None,
    architecture: StructuralFrameRetentionRootArchitecture | None = None,
) -> StructuralFrameRetentionVerificationV7:
    model = build_model() if model is None else model
    architecture = build_structural_frame_retention_roots(model=model) if architecture is None else architecture
    if type(model) is not MasckOneModel or type(architecture) is not StructuralFrameRetentionRootArchitecture:
        raise StructuralFrameRetentionVerificationV7Error("exact model and retention-root architecture types are required")
    root_ids = {root.root_id for root in architecture.roots}
    if len(architecture.roots) != 2 or root_ids != EXPECTED_ROOT_IDS:
        raise StructuralFrameRetentionVerificationV7Error(
            "retention architecture must contain exactly one wearer-left and one wearer-right root"
        )
    generated = tuple((root.root_id, float(root.frame_capture_volume_mm3)) for root in architecture.roots)
    v6 = verify_structural_frame_retention_roots_v6(model=model, architecture=architecture)
    return StructuralFrameRetentionVerificationV7(
        v6=v6,
        generated_capture_volumes_mm3=generated,
    ).validate()
