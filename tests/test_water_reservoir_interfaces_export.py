import json

import cadquery as cq
import pytest

from masck_one.authority import load_authority
from masck_one.realized_water_reservoir import build_realized_water_reservoir
from masck_one.water_reservoir_interfaces import (
    FILL_CLOSURE_RESERVATION_DIAMETER_MM,
    FILL_CLOSURE_RESERVATION_HEIGHT_MM,
    build_water_reservoir_interface_geometry,
)


def test_water_service_release_references_round_trip_through_step_and_manifest(tmp_path):
    authority = load_authority()
    realized = build_realized_water_reservoir(authority)
    interfaces = build_water_reservoir_interface_geometry(authority, realized)

    exports = {
        "ported_body": interfaces.body_with_pickup_port_solid,
        "ported_lid": interfaces.lid_with_fill_vent_ports_solid,
        "fill_closure_reservation": interfaces.fill_closure_reservation_solid,
        "vent_path": interfaces.vent_path_solid,
        "pickup_passage": interfaces.pickup_passage_solid,
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

    manifest_path = tmp_path / "water_reservoir_interfaces.json"
    manifest_path.write_text(json.dumps(interfaces.manifest(), sort_keys=True), encoding="utf-8")
    reloaded = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert reloaded == interfaces.manifest()
    assert reloaded["source_realized_reservoir_sha256"] == realized.manifest_sha256
    assert reloaded["fluid_identity"] == "FRESH_WATER"
    assert reloaded["physical_validation_eligible"] is False
