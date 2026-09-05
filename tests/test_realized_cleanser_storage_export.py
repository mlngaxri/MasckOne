import json

import cadquery as cq
import pytest

from masck_one.authority import load_authority
from masck_one.cleanser_service_interfaces import build_cleanser_service_geometry
from masck_one.realized_cleanser_storage import build_realized_cleanser_storage


def test_cleanser_material_and_service_reference_solids_round_trip_through_step(tmp_path):
    authority = load_authority()
    realized = build_realized_cleanser_storage(authority)
    service = build_cleanser_service_geometry(authority)
    exports = {
        "body": service.ported_body_solid,
        "cradle": realized.cradle_solid,
        "retention_key": realized.retention_key_solid,
        "service_closure": service.service_closure_solid,
        "service_closure_key": service.service_retention_key_solid,
        "internal_cavity": realized.internal_cavity_solid,
        "fill_seal_reference": service.fill_seal_reference_solid,
        "purge_seal_reference": service.purge_seal_reference_solid,
        "vent_lumen": service.vent_lumen_solid,
        "vent_barrier_reservation": service.vent_barrier_reservation_solid,
        "pickup_tube": service.pickup_tube_solid,
        "pickup_lumen": service.pickup_lumen_solid,
        "purge_connector_reservation": realized.purge_connector_reservation_solid,
        "outlet_connector_reservation": realized.outlet_connector_reservation_solid,
        "drain_path_reference": realized.drain_path_reference_solid,
        "service_closure_sweep": service.service_closure_sweep_solid,
        "service_key_sweep": service.service_key_sweep_solid,
    }

    for name, source in exports.items():
        path = tmp_path / f"{name}.step"
        cq.exporters.export(source, str(path))
        assert path.exists() and path.stat().st_size > 0
        round_tripped = cq.importers.importStep(str(path))
        assert round_tripped.solids().size() == 1
        assert round_tripped.val().isValid()
        assert round_tripped.val().Volume() == pytest.approx(source.val().Volume(), rel=2e-6, abs=2e-5)


def test_cleanser_manifests_round_trip_retaining_source_identity_and_evidence_firewall(tmp_path):
    authority = load_authority()
    realized = build_realized_cleanser_storage(authority)
    service = build_cleanser_service_geometry(authority)
    payload = {
        "realized_cleanser_storage": realized.manifest(),
        "cleanser_service_interfaces": service.manifest(),
    }
    path = tmp_path / "realized_cleanser_geometry.json"
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    reloaded = json.loads(path.read_text(encoding="utf-8"))

    assert reloaded == payload
    assert reloaded["realized_cleanser_storage"]["source_architecture_sha256"] == realized.source_architecture_sha256
    assert reloaded["realized_cleanser_storage"]["fluid_identity"] == "CLEANSER"
    assert reloaded["realized_cleanser_storage"]["reservoir_cavity_classification"] == "WET_REMOVABLE"
    assert reloaded["realized_cleanser_storage"]["mount_cavity_classification"] == "WET_DRAINABLE"
    assert reloaded["realized_cleanser_storage"]["physical_validation_eligible"] is False
    assert reloaded["realized_cleanser_storage"]["geometry"]["geometric_cavity_volume_mL"] == pytest.approx(3.072)
    assert reloaded["cleanser_service_interfaces"]["source_storage_manifest_sha256"] == realized.manifest_sha256
    assert reloaded["cleanser_service_interfaces"]["fluid_identity"] == "CLEANSER"
    assert reloaded["cleanser_service_interfaces"]["viscosity_limit_mPa_s"] is None
    assert reloaded["cleanser_service_interfaces"]["physical_validation_eligible"] is False
