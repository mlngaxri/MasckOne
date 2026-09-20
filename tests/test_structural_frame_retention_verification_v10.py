from dataclasses import replace

import pytest

from masck_one.model import build_model
from masck_one.structural_frame_retention_roots import build_structural_frame_retention_roots
from masck_one.structural_frame_retention_verification_v10 import (
    AXIAL_REGISTRATION_TOLERANCE_MM,
    StructuralFrameRetentionVerificationV10,
    StructuralFrameRetentionVerificationV10Error,
    verify_structural_frame_retention_roots_v10,
)


def test_nominal_v10_retainer_is_registered_to_capture_pin_groove():
    result = verify_structural_frame_retention_roots_v10()
    manifest = result.manifest()
    assert manifest["physical_validation_eligible"] is False
    assert all(
        root["axial_registration_error_mm"] <= AXIAL_REGISTRATION_TOLERANCE_MM
        for root in manifest["roots"]
    )


def test_v10_rejects_axially_shifted_installed_retainer_brep():
    model = build_model()
    architecture = build_structural_frame_retention_roots(model=model)
    root = architecture.roots[0]
    shifted = root.split_retainer.translate((0.0, 0.10, 0.0))
    bad_root = replace(root, split_retainer=shifted)
    bad_architecture = replace(architecture, roots=(bad_root, architecture.roots[1]))
    with pytest.raises(StructuralFrameRetentionVerificationV10Error, match="not registered"):
        verify_structural_frame_retention_roots_v10(model=model, architecture=bad_architecture)


def test_v10_rejects_synthetic_center_drift_even_when_v9_is_nominal():
    nominal = verify_structural_frame_retention_roots_v10()
    centers = list(nominal.retainer_center_y_mm)
    centers[0] = (centers[0][0], centers[0][1] + 0.01)
    with pytest.raises(StructuralFrameRetentionVerificationV10Error, match="not registered"):
        StructuralFrameRetentionVerificationV10(
            v9=nominal.v9,
            retainer_center_y_mm=tuple(centers),
        ).validate()


def test_v10_rejects_duplicate_root_identity():
    nominal = verify_structural_frame_retention_roots_v10()
    root_id, center = nominal.retainer_center_y_mm[0]
    with pytest.raises(StructuralFrameRetentionVerificationV10Error, match="exactly one wearer-left"):
        StructuralFrameRetentionVerificationV10(
            v9=nominal.v9,
            retainer_center_y_mm=((root_id, center), (root_id, center)),
        ).validate()


def test_v10_rejects_physical_validation_promotion():
    nominal = verify_structural_frame_retention_roots_v10()
    with pytest.raises(StructuralFrameRetentionVerificationV10Error, match="not physical validation"):
        replace(nominal, physical_validation_eligible=True).validate()
