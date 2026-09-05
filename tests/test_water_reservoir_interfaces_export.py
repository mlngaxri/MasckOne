import json

import cadquery as cq
import pytest

from masck_one.authority import load_authority
from masck_one.realized_water_reservoir import build_realized_water_reservoir
from masck_one.water_reservoir_closure import build_water_reservoir_closure_geometry
from masck_one.water_reservoir_interfaces import (
    FILL_CLOSURE_RESERVATION_DIAMETER_MM,
    FILL_CLOSURE_RESERVATION_HEIGHT_MM,
    build_water_reservoir_interface_geometry,
)


def test_water_service_release_references_round_trip_through_step_and_manifest(tmp_path):
    authority = load_authority()
    realized = build_realized_water_reservoir(authority)
    interfaces = build_water_reservoir_interface_geometry(authority, realized)
    closure = build_water_reservoir_closure_geometry(authority, realized, interfaces)

    exports = {
        "closure_body": closure.closure_body_solid,
        "closure_lid": closure.closure_lid_solid,
        "retention_key": closure.retention_key_solid,
        "fill_closure_reservation": interfaces.fill_closure_reservation_solid,
        "vent_path": interfaces.vent_path_solid,
        "pickup_passage": interfaces.pickup_passage_solid,
        "seal_groove_reference": closure.seal_groove_reservation_solid,
    }
    imported = {}
    for name, source in exports.items():
        path = tmp_path / f"{name}.step"
        cq.exporters.export(source, str(path))
        assert path.exists() and path.stat().st_size > 0
        round_tripped = cq.importers.importStep(str(path))
        assert round_tripped.solids().size() == 1
        assert round_tripped.val().isValid()
        assert round_tripped.val().Volume() > 0.0
        imported[name] = round_tripped

    fill_bb = imported["fill_closure_reservation"].val().BoundingBox()
    assert float(fill_bb.xlen) == pytest.approx(FILL_CLOSURE_RESERVATION_DIAMETER_MM, abs=2e-5)
    assert float(fill_bb.ylen) == pytest.approx(FILL_CLOSURE_RESERVATION_DIAMETER_MM, abs=2e-5)
    assert float(fill_bb.zlen) == pytest.approx(FILL_CLOSURE_RESERVATION_HEIGHT_MM, abs=2e-5)

    interface_manifest_path = tmp_path / "water_reservoir_interfaces.json"
    interface_manifest_path.write_text(json.dumps(interfaces.manifest(), sort_keys=True), encoding="utf-8")
    reloaded_interfaces = json.loads(interface_manifest_path.read_text(encoding="utf-8"))
    assert reloaded_interfaces == interfaces.manifest()
    assert reloaded_interfaces["source_realized_reservoir_sha256"] == realized.manifest_sha256
    assert reloaded_interfaces["fluid_identity"] == "FRESH_WATER"
    assert reloaded_interfaces["physical_validation_eligible"] is False

    closure_manifest_path = tmp_path / "water_reservoir_closure.json"
    closure_manifest_path.write_text(json.dumps(closure.manifest(), sort_keys=True), encoding="utf-8")
    reloaded_closure = json.loads(closure_manifest_path.read_text(encoding="utf-8"))
    assert reloaded_closure == closure.manifest()
    assert reloaded_closure["source_interface_manifest_sha256"] == interfaces.manifest_sha256
    assert reloaded_closure["fluid_identity"] == "FRESH_WATER"
    assert reloaded_closure["physical_validation_eligible"] is False
