import cadquery as cq
import pytest

from masck_one.realized_fresh_water_pump import build_current_realized_fresh_water_pump


def test_fresh_water_pump_reference_and_service_solids_round_trip_through_step(tmp_path):
    realized = build_current_realized_fresh_water_pump()
    exports = {
        "package_reference": realized.package_reference_solid,
        "support_cradle": realized.support_cradle_solid,
        "inlet_port_reservation": realized.inlet_port_reservation_solid,
        "outlet_port_reservation": realized.outlet_port_reservation_solid,
        "service_clearance": realized.service_clearance_solid,
    }

    for name, source in exports.items():
        path = tmp_path / f"{name}.step"
        cq.exporters.export(source, str(path))
        assert path.exists() and path.stat().st_size > 0
        round_tripped = cq.importers.importStep(str(path))
        assert round_tripped.solids().size() == 1
        assert round_tripped.val().isValid()
        assert round_tripped.val().Volume() == pytest.approx(source.val().Volume(), rel=2e-6, abs=2e-5)
        source_bb = source.val().BoundingBox()
        loaded_bb = round_tripped.val().BoundingBox()
        assert loaded_bb.xmin == pytest.approx(source_bb.xmin, abs=2e-6)
        assert loaded_bb.xmax == pytest.approx(source_bb.xmax, abs=2e-6)
        assert loaded_bb.ymin == pytest.approx(source_bb.ymin, abs=2e-6)
        assert loaded_bb.ymax == pytest.approx(source_bb.ymax, abs=2e-6)
        assert loaded_bb.zmin == pytest.approx(source_bb.zmin, abs=2e-6)
        assert loaded_bb.zmax == pytest.approx(source_bb.zmax, abs=2e-6)


def test_fresh_water_pump_manifest_round_trip_is_deterministic():
    realized = build_current_realized_fresh_water_pump()
    manifest = realized.manifest()
    assert manifest["manifest_sha256"] == realized.manifest_sha256
    assert manifest["station_id"] == "PUMP-STATION-WATER"
    assert manifest["fluid_identity"] == "FRESH_WATER"
    assert manifest["reference_package"]["evidence_role"] == (
        "FIT_AND_COLLISION_REFERENCE_ONLY_NOT_SELECTED_PUMP_DIMENSIONS_OR_MASS"
    )
    assert manifest["physical_validation_eligible"] is False
