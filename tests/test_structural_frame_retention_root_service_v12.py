from dataclasses import replace
from types import SimpleNamespace

import pytest

from masck_one import structural_frame_retention_root_service_v12 as v12


def test_v12_binds_corridor_cross_sections_to_hardware_clearance_envelopes():
    audit = v12.build_structural_frame_retention_root_service_v12()
    assert len(audit.cross_section_boundary_error_mm) == 2
    for _, pin_errors, retainer_errors in audit.cross_section_boundary_error_mm:
        assert len(pin_errors) == 4
        assert len(retainer_errors) == 4
        assert max(abs(value) for value in pin_errors + retainer_errors) <= v12.REGISTRATION_TOLERANCE_MM
    assert audit.manifest()["access_clearance_mm"] == v12.v1.ACCESS_CLEARANCE_MM
    assert audit.manifest()["whole_head_removal_status"] == "OPEN"
    assert audit.physical_validation_eligible is False


def test_v12_rejects_stale_v11_provenance_records_and_digest():
    audit = v12.build_structural_frame_retention_root_service_v12()
    with pytest.raises(v12.StructuralFrameRetentionRootServiceV12Error, match="source V11"):
        replace(audit, source_v11_seat_registration_evidence_sha256="0" * 64).validate()
    records = list(audit.cross_section_boundary_error_mm)
    root_id, pin_errors, retainer_errors = records[0]
    records[0] = (root_id, (pin_errors[0] + 0.001,) + pin_errors[1:], retainer_errors)
    with pytest.raises(v12.StructuralFrameRetentionRootServiceV12Error, match="registration evidence is stale"):
        replace(audit, cross_section_boundary_error_mm=tuple(records)).validate()
    with pytest.raises(v12.StructuralFrameRetentionRootServiceV12Error, match="digest"):
        replace(audit, cross_section_registration_evidence_sha256="f" * 64).validate()


def _service_with_bilateral_shift(*, pin_shift_x=0.0, retainer_shift_y=0.0):
    service = v12.v1.build_structural_frame_retention_root_service()
    paths = tuple(
        replace(
            path,
            pin_withdraw_sweep=path.pin_withdraw_sweep.translate((pin_shift_x, 0.0, 0.0)),
            clip_install_sweep=path.clip_install_sweep.translate((0.0, retainer_shift_y, 0.0)),
        )
        for path in service.paths
    )
    return SimpleNamespace(paths=paths, architecture_sha256=service.architecture_sha256)


def test_v12_rejects_bilaterally_shifted_pin_cross_section(monkeypatch):
    bad_service = _service_with_bilateral_shift(pin_shift_x=0.01)
    monkeypatch.setattr(v12.v1, "build_structural_frame_retention_root_service", lambda: bad_service)
    with pytest.raises(v12.StructuralFrameRetentionRootServiceV12Error, match="pin corridor cross-section is misregistered"):
        v12._cross_section_evidence()


def test_v12_rejects_bilaterally_shifted_retainer_cross_section(monkeypatch):
    bad_service = _service_with_bilateral_shift(retainer_shift_y=0.01)
    monkeypatch.setattr(v12.v1, "build_structural_frame_retention_root_service", lambda: bad_service)
    with pytest.raises(v12.StructuralFrameRetentionRootServiceV12Error, match="retainer corridor cross-section is misregistered"):
        v12._cross_section_evidence()


def test_v12_rejects_physical_validation_promotion():
    audit = v12.build_structural_frame_retention_root_service_v12()
    with pytest.raises(v12.StructuralFrameRetentionRootServiceV12Error, match="not physical"):
        replace(audit, physical_validation_eligible=True).validate()
