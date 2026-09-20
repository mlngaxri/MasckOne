from dataclasses import replace

import pytest

from masck_one.structural_frame_retention_verification_v16 import (
    COM_SYMMETRY_NUMERICAL_TOLERANCE_MM,
    StructuralFrameRetentionVerificationV16Error,
    verify_structural_frame_retention_roots_v16,
)


def test_nominal_v16_capture_pin_centers_are_bilaterally_symmetric():
    result = verify_structural_frame_retention_roots_v16()
    manifest = result.manifest()
    assert manifest["physical_validation_eligible"] is False
    assert all(abs(value) <= COM_SYMMETRY_NUMERICAL_TOLERANCE_MM for value in manifest["symmetry_residual_xyz_mm"])


def test_v16_rejects_mirrored_root_placement_drift():
    nominal = verify_structural_frame_retention_roots_v16()
    values = list(nominal.pin_centers_of_mass_mm)
    root_id, center = values[0]
    values[0] = (root_id, (center[0] + 0.01, center[1], center[2]))
    with pytest.raises(StructuralFrameRetentionVerificationV16Error, match="bilateral mirror symmetry"):
        replace(nominal, pin_centers_of_mass_mm=tuple(values)).validate()


def test_v16_rejects_equal_volume_asymmetric_internal_material_relocation():
    nominal = verify_structural_frame_retention_roots_v16()
    values = list(nominal.pin_centers_of_mass_mm)
    root_id, center = values[0]
    values[0] = (root_id, (center[0], center[1] + 0.01, center[2]))
    with pytest.raises(StructuralFrameRetentionVerificationV16Error, match="bilateral mirror symmetry"):
        replace(nominal, pin_centers_of_mass_mm=tuple(values)).validate()


def test_v16_rejects_nonfinite_center_of_mass():
    nominal = verify_structural_frame_retention_roots_v16()
    values = list(nominal.pin_centers_of_mass_mm)
    root_id, center = values[0]
    values[0] = (root_id, (float("nan"), center[1], center[2]))
    with pytest.raises(StructuralFrameRetentionVerificationV16Error, match="finite XYZ"):
        replace(nominal, pin_centers_of_mass_mm=tuple(values)).validate()


def test_v16_rejects_duplicate_root_identity():
    nominal = verify_structural_frame_retention_roots_v16()
    root_id, center = nominal.pin_centers_of_mass_mm[0]
    with pytest.raises(StructuralFrameRetentionVerificationV16Error, match="exactly one wearer-left"):
        replace(nominal, pin_centers_of_mass_mm=((root_id, center), (root_id, center))).validate()


def test_v16_rejects_physical_validation_promotion():
    nominal = verify_structural_frame_retention_roots_v16()
    with pytest.raises(StructuralFrameRetentionVerificationV16Error, match="not physical validation"):
        replace(nominal, physical_validation_eligible=True).validate()
