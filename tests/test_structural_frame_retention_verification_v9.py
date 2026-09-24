from dataclasses import replace

import cadquery as cq
import pytest

from masck_one.model import build_model
from masck_one.structural_frame_retention_roots import (
    CLEVIS_PIN_GROOVE_WIDTH_MM,
    build_structural_frame_retention_roots,
)
from masck_one.structural_frame_retention_verification_v9 import (
    MIN_RADIAL_WITHDRAWAL_BLOCK_MM,
    StructuralFrameRetentionVerificationV9,
    StructuralFrameRetentionVerificationV9Error,
    verify_structural_frame_retention_roots_v9,
)


def _nominal_candidate():
    result = verify_structural_frame_retention_roots_v9()
    return result.v8, result.retainer_axial_spans_mm, result.radial_withdrawal_blocks_mm


def test_nominal_v9_retainer_is_groove_contained_and_blocks_axial_withdrawal():
    result = verify_structural_frame_retention_roots_v9()
    manifest = result.manifest()
    assert manifest["physical_validation_eligible"] is False
    assert all(root["retainer_axial_span_mm"] <= CLEVIS_PIN_GROOVE_WIDTH_MM + 1e-6 for root in manifest["roots"])
    assert all(root["radial_withdrawal_block_mm"] >= MIN_RADIAL_WITHDRAWAL_BLOCK_MM for root in manifest["roots"])


def test_v9_rejects_retainer_wider_than_capture_groove():
    v8, spans, blocks = _nominal_candidate()
    bad = list(spans)
    bad[0] = (bad[0][0], CLEVIS_PIN_GROOVE_WIDTH_MM + 0.01)
    with pytest.raises(StructuralFrameRetentionVerificationV9Error, match="not axially contained"):
        StructuralFrameRetentionVerificationV9(v8=v8, retainer_axial_spans_mm=tuple(bad), radial_withdrawal_blocks_mm=blocks).validate()


def test_v9_rejects_insufficient_radial_withdrawal_block():
    v8, spans, blocks = _nominal_candidate()
    bad = list(blocks)
    bad[0] = (bad[0][0], MIN_RADIAL_WITHDRAWAL_BLOCK_MM - 0.01)
    with pytest.raises(StructuralFrameRetentionVerificationV9Error, match="minimum digital radial withdrawal block"):
        StructuralFrameRetentionVerificationV9(v8=v8, retainer_axial_spans_mm=spans, radial_withdrawal_blocks_mm=tuple(bad)).validate()


def test_v9_rejects_undersized_installed_retainer_brep():
    model = build_model()
    architecture = build_structural_frame_retention_roots(model=model)
    root = architecture.roots[0]
    x, y, z = root.center_xyz_mm
    undersized = cq.Workplane("XY").box(2.0, 0.5, 2.0, centered=(True, True, True)).translate((x, y, z))
    bad_root = replace(root, split_retainer=undersized)
    bad_architecture = replace(architecture, roots=(bad_root, architecture.roots[1]))
    with pytest.raises(StructuralFrameRetentionVerificationV9Error, match="minimum digital radial withdrawal block"):
        verify_structural_frame_retention_roots_v9(model=model, architecture=bad_architecture)


def test_v9_rejects_duplicate_root_identity():
    v8, spans, blocks = _nominal_candidate()
    root_id, value = spans[0]
    with pytest.raises(StructuralFrameRetentionVerificationV9Error, match="exactly one wearer-left"):
        StructuralFrameRetentionVerificationV9(v8=v8, retainer_axial_spans_mm=((root_id, value), (root_id, value)), radial_withdrawal_blocks_mm=blocks).validate()


def test_v9_rejects_physical_validation_promotion():
    v8, spans, blocks = _nominal_candidate()
    candidate = StructuralFrameRetentionVerificationV9(v8=v8, retainer_axial_spans_mm=spans, radial_withdrawal_blocks_mm=blocks)
    with pytest.raises(StructuralFrameRetentionVerificationV9Error, match="not physical validation"):
        replace(candidate, physical_validation_eligible=True).validate()
