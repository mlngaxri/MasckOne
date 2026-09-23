from dataclasses import replace

import pytest

from masck_one.structural_frame_retention_root_capture_v5 import (
    StructuralFrameRetentionRootCaptureV5Error,
    build_structural_frame_retention_root_capture_v5,
)


def test_capture_v5_exposes_tolerance_critical_throat_transition() -> None:
    audit = build_structural_frame_retention_root_capture_v5()
    assert audit.throat_half_width_mm == pytest.approx(1.215)
    assert audit.bore_radius_mm == pytest.approx(1.08)
    assert audit.throat_to_bore_transition_margin_mm == pytest.approx(0.135)
    assert audit.transition_margin_fraction_of_bore == pytest.approx(0.135 / 1.08)
    assert audit.nominal_bore_connectivity_present is True
    assert audit.manufacturing_tolerance_closure_required is True
    assert audit.manufactured_connectivity_validated is False
    assert audit.manifest()["transition_status"] == "NOMINAL_CONNECTIVITY_PRESENT_TOLERANCE_CLOSURE_REQUIRED"


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_capture_v4_sha256", "0" * 64),
        ("throat_half_width_mm", 1.20),
        ("bore_radius_mm", 1.07),
        ("throat_to_bore_transition_margin_mm", 0.12),
        ("transition_margin_fraction_of_bore", 0.12 / 1.08),
        ("evidence_sha256", "1" * 64),
        ("nominal_bore_connectivity_present", False),
        ("manufacturing_tolerance_closure_required", False),
    ],
)
def test_capture_v5_fails_closed_on_stale_or_waived_transition_evidence(field: str, value: object) -> None:
    audit = build_structural_frame_retention_root_capture_v5()
    with pytest.raises(StructuralFrameRetentionRootCaptureV5Error):
        replace(audit, **{field: value}).validate()


@pytest.mark.parametrize("field", ["manufactured_connectivity_validated", "physical_validation_eligible"])
def test_capture_v5_cannot_promote_nominal_connectivity(field: str) -> None:
    audit = build_structural_frame_retention_root_capture_v5()
    with pytest.raises(StructuralFrameRetentionRootCaptureV5Error):
        replace(audit, **{field: True}).validate()
