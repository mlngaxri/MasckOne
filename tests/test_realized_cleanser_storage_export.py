import json

import cadquery as cq
import pytest

from masck_one.authority import load_authority
from masck_one.realized_cleanser_storage import build_realized_cleanser_storage


def test_cleanser_material_and_service_reference_solids_round_trip_through_step(tmp_path):
    realized = build_realized_cleanser_storage(load_authority())
    exports = {
        "body": realized.body_solid,
        "cradle": realized.cradle_solid,
        "retention_key": realized.retention_key_solid,
        "internal_cavity": realized.internal_cavity_solid,
        "refill_closure_reservation": realized.refill_closure_reservation_solid,
        "purge_connector_reservation": realized.purge_connector_reservation_solid,
        "outlet_connector_reservation": realized.outlet_connector_reservation_solid,
        "drain_path_reference": realized.drain_path_reference_solid,
    }

    for name, source in exports.items():
        path = tmp_path / f"{name}.step"
        cq.exporters.export(source, str(path))
        assert path.exists() and path.stat().st_size > 0
        round_tripped = cq.importers.importStep(str(path))
        assert round_tripped.solids().size() == 1
        assert round_tripped.val().isValid()
        assert round_tripped.val().Volume() == pytest.approx(source.val().Volume(), rel=2e-6, abs=2e-5)


def test_cleanser_manifest_json_round_trip_retains_source_identity_and_evidence_firewall(tmp_path):
    realized = build_realized_cleanser_storage(load_authority())
    path = tmp_path / "realized_cleanser_storage.json"
    path.write_text(json.dumps(realized.manifest(), sort_keys=True), encoding="utf-8")
    reloaded = json.loads(path.read_text(encoding="utf-8"))

    assert reloaded == realized.manifest()
    assert reloaded["source_architecture_sha256"] == realized.source_architecture_sha256
    assert reloaded["fluid_identity"] == "CLEANSER"
    assert reloaded["reservoir_cavity_classification"] == "WET_REMOVABLE"
    assert reloaded["mount_cavity_classification"] == "WET_DRAINABLE"
    assert reloaded["physical_validation_eligible"] is False
    assert reloaded["geometry"]["geometric_cavity_volume_mL"] == pytest.approx(3.072)
