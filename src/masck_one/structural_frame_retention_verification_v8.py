from __future__ import annotations

"""Independently verify capture-pin clearance to the authoritative yoke bore.

V7 cross-checks source-frame capture metadata. V8 adds an independent B-rep distance
measurement between each capture pin and its nominal yoke material. It requires both
the generator metadata and B-rep result to agree with the analytical radial clearance
implied by the authoritative pin and bore radii. This prevents coherent geometry and
metadata drift from silently changing the mating contract.
"""

from dataclasses import dataclass
import math

import cadquery as cq

from .model import MasckOneModel, build_model
from .structural_frame_retention_roots import (
    CLEVIS_PIN_RADIUS_MM,
    YOKE_ROOT_BORE_RADIUS_MM,
    StructuralFrameRetentionRootArchitecture,
    build_structural_frame_retention_roots,
)
from .structural_frame_retention_verification_v7 import (
    StructuralFrameRetentionVerificationV7,
    StructuralFrameRetentionVerificationV7Error,
    verify_structural_frame_retention_roots_v7,
)

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_VERIFICATION_V8"
CLEARANCE_METADATA_ABSOLUTE_TOLERANCE_MM = 1e-6
AUTHORITY_RADIAL_CLEARANCE_MM = YOKE_ROOT_BORE_RADIUS_MM - CLEVIS_PIN_RADIUS_MM
EXPECTED_ROOT_IDS = frozenset({"RETENTION_ROOT_WEARER_LEFT", "RETENTION_ROOT_WEARER_RIGHT"})


class StructuralFrameRetentionVerificationV8Error(ValueError):
    pass


def _strict_distance_mm(a: cq.Workplane, b: cq.Workplane) -> float:
    try:
        distance = float(a.val().distance(b.val()))
    except Exception as exc:
        raise StructuralFrameRetentionVerificationV8Error("B-rep clearance query failed closed") from exc
    if not math.isfinite(distance) or distance < 0.0:
        raise StructuralFrameRetentionVerificationV8Error("B-rep clearance must be finite and nonnegative")
    return distance


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionVerificationV8:
    v7: StructuralFrameRetentionVerificationV7
    generated_clearances_mm: tuple[tuple[str, float], ...]
    independent_clearances_mm: tuple[tuple[str, float], ...]
    physical_validation_eligible: bool = False

    def validate(self) -> "StructuralFrameRetentionVerificationV8":
        try:
            self.v7.validate()
        except StructuralFrameRetentionVerificationV7Error as exc:
            raise StructuralFrameRetentionVerificationV8Error("V7 prerequisite verification failed") from exc
        if not math.isfinite(AUTHORITY_RADIAL_CLEARANCE_MM) or AUTHORITY_RADIAL_CLEARANCE_MM <= 0.0:
            raise StructuralFrameRetentionVerificationV8Error("authoritative pin/bore radial clearance must be finite and positive")
        generated = dict(self.generated_clearances_mm)
        independent = dict(self.independent_clearances_mm)
        if len(generated) != 2 or set(generated) != EXPECTED_ROOT_IDS:
            raise StructuralFrameRetentionVerificationV8Error("generated clearance metadata requires exactly one wearer-left and one wearer-right root")
        if len(independent) != 2 or set(independent) != EXPECTED_ROOT_IDS:
            raise StructuralFrameRetentionVerificationV8Error("independent clearance evidence requires exactly one wearer-left and one wearer-right root")
        for root_id in EXPECTED_ROOT_IDS:
            expected = generated[root_id]
            actual = independent[root_id]
            if not math.isfinite(expected) or expected <= 0.0:
                raise StructuralFrameRetentionVerificationV8Error(f"{root_id} generated radial clearance must be finite and positive")
            if not math.isfinite(actual) or actual <= 0.0:
                raise StructuralFrameRetentionVerificationV8Error(f"{root_id} independent radial clearance must be finite and positive")
            if abs(expected - actual) > CLEARANCE_METADATA_ABSOLUTE_TOLERANCE_MM:
                raise StructuralFrameRetentionVerificationV8Error(f"{root_id} generated radial clearance disagrees with independent B-rep distance")
            if abs(expected - AUTHORITY_RADIAL_CLEARANCE_MM) > CLEARANCE_METADATA_ABSOLUTE_TOLERANCE_MM:
                raise StructuralFrameRetentionVerificationV8Error(f"{root_id} generated radial clearance disagrees with authoritative pin/bore radii")
            if abs(actual - AUTHORITY_RADIAL_CLEARANCE_MM) > CLEARANCE_METADATA_ABSOLUTE_TOLERANCE_MM:
                raise StructuralFrameRetentionVerificationV8Error(f"{root_id} independent radial clearance disagrees with authoritative pin/bore radii")
        if self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionVerificationV8Error("digital clearance coherence is not physical validation evidence")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        generated = dict(self.generated_clearances_mm)
        independent = dict(self.independent_clearances_mm)
        return {
            "schema": SCHEMA,
            "verification_semantics": "FAIL_CLOSED_V7_PLUS_PIN_BORE_CLEARANCE_AUTHORITY_COHERENCE",
            "clearance_metadata_absolute_tolerance_mm": CLEARANCE_METADATA_ABSOLUTE_TOLERANCE_MM,
            "authority_pin_radius_mm": CLEVIS_PIN_RADIUS_MM,
            "authority_bore_radius_mm": YOKE_ROOT_BORE_RADIUS_MM,
            "authority_radial_clearance_mm": AUTHORITY_RADIAL_CLEARANCE_MM,
            "roots": [
                {
                    "root_id": root_id,
                    "generated_radial_clearance_mm": generated[root_id],
                    "independent_brep_clearance_mm": independent[root_id],
                    "absolute_error_mm": abs(generated[root_id] - independent[root_id]),
                    "authority_error_mm": abs(independent[root_id] - AUTHORITY_RADIAL_CLEARANCE_MM),
                }
                for root_id in sorted(EXPECTED_ROOT_IDS)
            ],
            "physical_validation_eligible": False,
        }


def verify_structural_frame_retention_roots_v8(
    *,
    model: MasckOneModel | None = None,
    architecture: StructuralFrameRetentionRootArchitecture | None = None,
) -> StructuralFrameRetentionVerificationV8:
    model = build_model() if model is None else model
    architecture = build_structural_frame_retention_roots(model=model) if architecture is None else architecture
    if type(model) is not MasckOneModel or type(architecture) is not StructuralFrameRetentionRootArchitecture:
        raise StructuralFrameRetentionVerificationV8Error("exact model and retention-root architecture types are required")
    root_ids = {root.root_id for root in architecture.roots}
    if len(architecture.roots) != 2 or root_ids != EXPECTED_ROOT_IDS:
        raise StructuralFrameRetentionVerificationV8Error("retention architecture must contain exactly one wearer-left and one wearer-right root")
    generated = tuple((root.root_id, float(root.pin_bore_radial_clearance_mm)) for root in architecture.roots)
    independent = tuple((root.root_id, _strict_distance_mm(root.capture_pin, root.yoke_root_reference)) for root in architecture.roots)
    v7 = verify_structural_frame_retention_roots_v7(model=model, architecture=architecture)
    return StructuralFrameRetentionVerificationV8(
        v7=v7,
        generated_clearances_mm=generated,
        independent_clearances_mm=independent,
    ).validate()
