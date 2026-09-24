from dataclasses import replace

import pytest

from masck_one.structural_frame_retention_verification_v15 import (
    VOLUME_NUMERICAL_TOLERANCE_MM3,
    StructuralFrameRetentionVerificationV15Error,
    verify_structural_frame_retention_roots_v15,
)


def test_nominal_v15_capture_pin_material_matches_structural_authority():
    result = verify_structural_frame_retention_roots_v15()
    manifest = result.manifest()
    assert manifest["physical_validation_eligible"] is False
    assert all(
        abs(root["pin_volume_mm3"] - manifest["expected_pin_volume_mm3"])
        <= VOLUME_NUMERICAL_TOLERANCE_MM3
        for root in manifest["roots"]
    )


def test_v15_rejects_material_volume_drift_hidden_from_outer_dimensions():
    nominal = verify_structural_frame_retention_roots_v15()
    values = list(nominal.pin_volumes_mm3)
    values[0] = (values[0][0], values[0][1] - 0.01)
    with pytest.raises(StructuralFrameRetentionVerificationV15Error, match="material volume drifted"):
        replace(nominal, pin_volumes_mm3=tuple(values)).validate()


def test_v15_rejects_nonfinite_material_volume():
    nominal = verify_structural_frame_retention_roots_v15()
    values = list(nominal.pin_volumes_mm3)
    values[0] = (values[0][0], float("nan"))
    with pytest.raises(StructuralFrameRetentionVerificationV15Error, match="material volume drifted"):
        replace(nominal, pin_volumes_mm3=tuple(values)).validate()


def test_v15_rejects_duplicate_root_identity():
    nominal = verify_structural_frame_retention_roots_v15()
    root_id, value = nominal.pin_volumes_mm3[0]
    with pytest.raises(StructuralFrameRetentionVerificationV15Error, match="exactly one wearer-left"):
        replace(nominal, pin_volumes_mm3=((root_id, value), (root_id, value))).validate()


def test_v15_rejects_physical_validation_promotion():
    nominal = verify_structural_frame_retention_roots_v15()
    with pytest.raises(StructuralFrameRetentionVerificationV15Error, match="not physical validation"):
        replace(nominal, physical_validation_eligible=True).validate()
