from dataclasses import replace

import pytest

from masck_one.structural_frame_retention_root_capture_v3 import (
    StructuralFrameRetentionRootCaptureV3Error,
    build_structural_frame_retention_root_capture_v3,
)


def test_capture_v3_exposes_required_elastic_installation_opening() -> None:
    audit = build_structural_frame_retention_root_capture_v3()
    assert audit.pin_shaft_diameter_mm == 2.70
    assert audit.free_throat_width_mm == 2.43
    assert audit.required_total_throat_opening_mm == 0.27
    assert audit.required_per_arm_displacement_mm == 0.135
    assert audit.required_opening_ratio == pytest.approx(0.27 / 2.43)
    assert audit.elastic_installation_required is True
    assert audit.manifest()["installation_status"] == "ELASTIC_OPENING_REQUIRED_MATERIAL_AND_FORCE_UNVALIDATED"


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_capture_v2_sha256", "0" * 64),
        ("pin_shaft_diameter_mm", 2.60),
        ("free_throat_width_mm", 2.30),
        ("required_total_throat_opening_mm", 0.40),
        ("required_per_arm_displacement_mm", 0.20),
        ("required_opening_ratio", 0.1),
        ("evidence_sha256", "1" * 64),
        ("elastic_installation_required", False),
    ],
)
def test_capture_v3_fails_closed_on_stale_installation_demand(field: str, value: object) -> None:
    audit = build_structural_frame_retention_root_capture_v3()
    with pytest.raises(StructuralFrameRetentionRootCaptureV3Error):
        replace(audit, **{field: value}).validate()


@pytest.mark.parametrize("field", ["material_deflection_validated", "insertion_force_validated", "physical_validation_eligible"])
def test_capture_v3_cannot_promote_geometry_to_physical_validation(field: str) -> None:
    audit = build_structural_frame_retention_root_capture_v3()
    with pytest.raises(StructuralFrameRetentionRootCaptureV3Error):
        replace(audit, **{field: True}).validate()
