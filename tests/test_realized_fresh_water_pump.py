import pytest

from masck_one.authority import load_authority
from masck_one.realized_fresh_water_pump import (
    AUTHORED_MAIN_SHA,
    CAVITY_CLASSIFICATION,
    DONOR_PR85_HEAD,
    FLUID_IDENTITY,
    INLET_POINT,
    MANIFOLD_INLET_ID,
    OUTLET_POINT,
    PUMP_CENTER,
    PUMP_SIZE_XYZ_MM,
    PUMP_STATION_ID,
    ROUTING_STATUS,
    SERVICE_SIZE_XYZ_MM,
    build_realized_fresh_water_pump,
)


def test_current_main_cell9_pump_port_preserves_exact_identity_and_datums():
    pump = build_realized_fresh_water_pump(load_authority())
    manifest = pump.manifest()

    assert AUTHORED_MAIN_SHA == "d02bce5b5cb43e33febd6e1a40fdc98f3893efca"
    assert DONOR_PR85_HEAD == "668727ad2676a7d41f095878ff5d9110c8f7a44a"
    assert manifest["fluid_identity"] == FLUID_IDENTITY == "FRESH_WATER"
    assert manifest["pump_station_id"] == PUMP_STATION_ID == "PUMP-STATION-WATER"
    assert manifest["source_interface_id"] == "WATER-PORT-PICKUP"
    assert manifest["downstream_interface_id"] == MANIFOLD_INLET_ID == "MANIFOLD-INLET-WATER-I23"
    assert pump.inlet_datum.point.as_tuple() == INLET_POINT.as_tuple() == (-31.0, -7.0, 7.0)
    assert pump.outlet_datum.point.as_tuple() == OUTLET_POINT.as_tuple() == (-31.0, -13.0, 7.0)


def test_supplier_family_package_and_drainable_cradle_are_real_breps():
    pump = build_realized_fresh_water_pump(load_authority())

    assert pump.package_solid.solids().size() == 1
    assert pump.package_solid.val().isValid()
    assert pump.package_solid.val().Volume() == pytest.approx(6150.0, abs=1e-7)
    assert pump.package_solid.val().Center().toTuple() == pytest.approx(PUMP_CENTER.as_tuple(), abs=1e-9)
    assert pump.package_solid.val().intersect(pump.support_cradle_solid.val()).Volume() == pytest.approx(0.0, abs=1e-7)
    assert pump.manifest()["support"]["cavity_classification"] == CAVITY_CLASSIFICATION == "WET_DRAINABLE"
    assert pump.manifest()["support"]["both_y_ends_open"] is True


def test_service_reservation_contains_package_and_local_interface_reservations():
    pump = build_realized_fresh_water_pump(load_authority())
    service = pump.service_reservation_solid.val()

    assert pump.manifest()["service_reservation_size_xyz_mm"] == list(SERVICE_SIZE_XYZ_MM)
    for solid in (pump.package_solid, pump.inlet_reservation_solid, pump.outlet_reservation_solid):
        outside = solid.val().cut(service).Volume()
        assert outside == pytest.approx(0.0, abs=1e-7)


def test_routing_and_supplier_claims_remain_fail_closed():
    pump = build_realized_fresh_water_pump(load_authority())
    manifest = pump.manifest()

    assert manifest["routing_status"] == ROUTING_STATUS
    assert manifest["package"]["supplier_package_candidate_id"] is None
    assert manifest["package"]["supplier_package_evidence_sha256"] is None
    assert manifest["selected_tubing_id_mm"] is None
    assert manifest["selected_minimum_bend_radius_mm"] is None
    assert manifest["selected_connector_standard"] is None
    assert manifest["physical_validation_eligible"] is False
    assert "NOT_SUPPLIER_SELECTION" in manifest["evidence_status"]


def test_manifest_is_deterministic():
    a = build_realized_fresh_water_pump(load_authority())
    b = build_realized_fresh_water_pump(load_authority())
    assert a.manifest() == b.manifest()
    assert a.manifest_sha256 == b.manifest_sha256
