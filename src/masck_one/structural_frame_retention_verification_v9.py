from __future__ import annotations

"""Fail closed on split-retainer placement and axial capture geometry.

V8 proves the capture pin fits the authoritative yoke bore. V9 verifies the removable
split retainer is actually located inside the pin groove and has radial material beyond
the full shaft radius, so the digital assembly contains an axial withdrawal stop rather
than merely a nearby clip-shaped solid. This remains digital geometry evidence only.
"""

from dataclasses import dataclass
import math

from .model import MasckOneModel, build_model
from .structural_frame_retention_roots import (
    CLEVIS_PIN_GROOVE_WIDTH_MM,
    CLEVIS_PIN_RADIUS_MM,
    StructuralFrameRetentionRootArchitecture,
    build_structural_frame_retention_roots,
)
from .structural_frame_retention_verification_v8 import (
    StructuralFrameRetentionVerificationV8,
    StructuralFrameRetentionVerificationV8Error,
    verify_structural_frame_retention_roots_v8,
)

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_VERIFICATION_V9"
EXPECTED_ROOT_IDS = frozenset({"RETENTION_ROOT_WEARER_LEFT", "RETENTION_ROOT_WEARER_RIGHT"})
AXIAL_CONTAINMENT_TOLERANCE_MM = 1e-6
MIN_RADIAL_WITHDRAWAL_BLOCK_MM = 0.20


class StructuralFrameRetentionVerificationV9Error(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionVerificationV9:
    v8: StructuralFrameRetentionVerificationV8
    retainer_axial_spans_mm: tuple[tuple[str, float], ...]
    radial_withdrawal_blocks_mm: tuple[tuple[str, float], ...]
    physical_validation_eligible: bool = False

    def validate(self) -> "StructuralFrameRetentionVerificationV9":
        try:
            self.v8.validate()
        except StructuralFrameRetentionVerificationV8Error as exc:
            raise StructuralFrameRetentionVerificationV9Error("V8 prerequisite verification failed") from exc
        spans = dict(self.retainer_axial_spans_mm)
        blocks = dict(self.radial_withdrawal_blocks_mm)
        if len(spans) != 2 or set(spans) != EXPECTED_ROOT_IDS:
            raise StructuralFrameRetentionVerificationV9Error("retainer spans require exactly one wearer-left and one wearer-right root")
        if len(blocks) != 2 or set(blocks) != EXPECTED_ROOT_IDS:
            raise StructuralFrameRetentionVerificationV9Error("withdrawal blocks require exactly one wearer-left and one wearer-right root")
        for root_id in EXPECTED_ROOT_IDS:
            span = spans[root_id]
            block = blocks[root_id]
            if not math.isfinite(span) or span <= 0.0:
                raise StructuralFrameRetentionVerificationV9Error(f"{root_id} retainer axial span must be finite and positive")
            if span > CLEVIS_PIN_GROOVE_WIDTH_MM + AXIAL_CONTAINMENT_TOLERANCE_MM:
                raise StructuralFrameRetentionVerificationV9Error(f"{root_id} split retainer is not axially contained by the pin groove")
            if not math.isfinite(block) or block < MIN_RADIAL_WITHDRAWAL_BLOCK_MM:
                raise StructuralFrameRetentionVerificationV9Error(f"{root_id} split retainer does not provide the minimum digital radial withdrawal block")
        if self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionVerificationV9Error("digital retainer capture is not physical validation evidence")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        spans = dict(self.retainer_axial_spans_mm)
        blocks = dict(self.radial_withdrawal_blocks_mm)
        return {
            "schema": SCHEMA,
            "verification_semantics": "FAIL_CLOSED_V8_PLUS_SPLIT_RETAINER_GROOVE_CAPTURE",
            "authority_groove_width_mm": CLEVIS_PIN_GROOVE_WIDTH_MM,
            "authority_pin_radius_mm": CLEVIS_PIN_RADIUS_MM,
            "minimum_digital_radial_withdrawal_block_mm": MIN_RADIAL_WITHDRAWAL_BLOCK_MM,
            "roots": [
                {"root_id": root_id, "retainer_axial_span_mm": spans[root_id], "radial_withdrawal_block_mm": blocks[root_id]}
                for root_id in sorted(EXPECTED_ROOT_IDS)
            ],
            "physical_validation_eligible": False,
        }


def verify_structural_frame_retention_roots_v9(*, model: MasckOneModel | None = None, architecture: StructuralFrameRetentionRootArchitecture | None = None) -> StructuralFrameRetentionVerificationV9:
    model = build_model() if model is None else model
    architecture = build_structural_frame_retention_roots(model=model) if architecture is None else architecture
    if type(model) is not MasckOneModel or type(architecture) is not StructuralFrameRetentionRootArchitecture:
        raise StructuralFrameRetentionVerificationV9Error("exact model and retention-root architecture types are required")
    if len(architecture.roots) != 2 or {root.root_id for root in architecture.roots} != EXPECTED_ROOT_IDS:
        raise StructuralFrameRetentionVerificationV9Error("retention architecture must contain exactly one wearer-left and one wearer-right root")
    spans = []
    blocks = []
    for root in architecture.roots:
        bb = root.split_retainer.val().BoundingBox()
        span = float(bb.ylen)
        center_x, _, center_z = root.center_xyz_mm
        measured_outer_radius = max(
            abs(float(bb.xmin) - center_x),
            abs(float(bb.xmax) - center_x),
            abs(float(bb.zmin) - center_z),
            abs(float(bb.zmax) - center_z),
        )
        # Measure the installed B-rep rather than deriving withdrawal block from the
        # same constants that generated it. This makes a missing, undersized or stale
        # split retainer fail closed even when the authority constants remain nominal.
        block = measured_outer_radius - CLEVIS_PIN_RADIUS_MM
        spans.append((root.root_id, span))
        blocks.append((root.root_id, block))
    v8 = verify_structural_frame_retention_roots_v8(model=model, architecture=architecture)
    return StructuralFrameRetentionVerificationV9(v8=v8, retainer_axial_spans_mm=tuple(spans), radial_withdrawal_blocks_mm=tuple(blocks)).validate()
