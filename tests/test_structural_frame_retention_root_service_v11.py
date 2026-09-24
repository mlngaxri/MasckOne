from dataclasses import replace
from types import SimpleNamespace

import pytest

from masck_one import structural_frame_retention_root_service_v11 as v11


def test_v11_binds_service_corridors_to_seated_hardware_boundaries():
    audit = v11.build_structural_frame_retention_root_service_v11()
    assert len(audit.seat_boundary_error_mm) == 2
    for _, pin_error, retainer_error in audit.seat_boundary_error_mm:
        assert abs(pin_error) <= v11.REGISTRATION_TOLERANCE_MM
        assert abs(retainer_error) <= v11.REGISTRATION_TOLERANCE_MM
    assert audit.manifest()["whole_head_removal_status"] == "OPEN"
    assert audit.physical_validation_eligible is False


def test_v11_rejects_stale_v10_provenance_records_and_digest():
    audit = v11.build_structural_frame_retention_root_service_v11()
    with pytest.raises(v11.StructuralFrameRetentionRootServiceV11Error, match="source V10"):
        replace(audit, source_v10_travel_closure_evidence_sha256="0" * 64).validate()
    records = list(audit.seat_boundary_error_mm)
    root_id, pin_error, retainer_error = records[0]
    records[0] = (root_id, pin_error + 0.001, retainer_error)
    with pytest.raises(v11.StructuralFrameRetentionRootServiceV11Error, match="registration evidence is stale"):
        replace(audit, seat_boundary_error_mm=tuple(records)).validate()
    with pytest.raises(v11.StructuralFrameRetentionRootServiceV11Error, match="digest"):
        replace(audit, seat_registration_evidence_sha256="f" * 64).validate()


def _service_with_shifted_path(*, pin_shift_y=0.0, retainer_shift_z=0.0):
    service = v11.v1.build_structural_frame_retention_root_service()
    path = service.paths[0]
    bad_path = replace(
        path,
        pin_withdraw_sweep=path.pin_withdraw_sweep.translate((0.0, pin_shift_y, 0.0)),
        clip_install_sweep=path.clip_install_sweep.translate((0.0, 0.0, retainer_shift_z)),
    )
    return SimpleNamespace(paths=(bad_path, service.paths[1]), architecture_sha256=service.architecture_sha256)


def test_v11_rejects_pin_corridor_detached_from_seated_boundary(monkeypatch):
    bad_service = _service_with_shifted_path(pin_shift_y=-0.01)
    monkeypatch.setattr(v11.v1, "build_structural_frame_retention_root_service", lambda: bad_service)
    with pytest.raises(v11.StructuralFrameRetentionRootServiceV11Error, match="pin withdrawal corridor is detached"):
        v11._seat_registration_evidence()


def test_v11_rejects_retainer_corridor_detached_from_seated_boundary(monkeypatch):
    bad_service = _service_with_shifted_path(retainer_shift_z=0.01)
    monkeypatch.setattr(v11.v1, "build_structural_frame_retention_root_service", lambda: bad_service)
    with pytest.raises(v11.StructuralFrameRetentionRootServiceV11Error, match="retainer corridor is detached"):
        v11._seat_registration_evidence()


def test_v11_rejects_physical_validation_promotion():
    audit = v11.build_structural_frame_retention_root_service_v11()
    with pytest.raises(v11.StructuralFrameRetentionRootServiceV11Error, match="not physical"):
        replace(audit, physical_validation_eligible=True).validate()
