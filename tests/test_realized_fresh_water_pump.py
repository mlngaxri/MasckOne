from dataclasses import replace

import pytest

from masck_one.fresh_pump_packaging import (
    FLUID_FRESH_WATER,
    INTERFACE_WATER_PUMP_OUTLET,
    ROUTE_WATER_MANIFOLD,
    ROUTE_WATER_SOURCE,
    STATION_WATER,
)
from masck_one.realized_fresh_water_pump import (
    INLET_DATUM_ID,
    OUTLET_DATUM_ID,
    PACKAGE_CLEARANCE_RESERVATION_MM,
    PACKAGE_ENVELOPE_XYZ_MM,
    PORT_DATUM_IDS,
    PORT_LUMEN_DIAMETER_SEED_MM,
    PORT_RESERVATION_DIAMETER_MM,
    RealizedFreshWaterPumpError,
    build_current_fresh_pump_sources,
    build_realized_fresh_water_pump,
)
from masck_one.water_reservoir import PORT_PICKUP


@pytest.fixture(scope="module")
def sources():
    return build_current_fresh_pump_sources()


@pytest.fixture(scope="module")
def realized(sources):
    return build_realized_fresh_water_pump(sources)


def test_realized_water_pump_binds_exact_unresolved_source_architecture(sources, realized):
    assert realized.source_fresh_pump_architecture_sha256 == sources.architecture.architecture_sha256
    assert realized.source_water_architecture_sha256 == sources.water.architecture_sha256
    assert realized.validate_current_sources(sources) == sources.architecture
    assert realized.station_id == STATION_WATER
    assert realized.fluid_identity == FLUID_FRESH_WATER
    assert realized.supplier_package_candidate_id is None
    assert realized.supplier_package_evidence_sha256 is None

    source_station = sources.architecture.stations[0]
    assert source_station.station_id == STATION_WATER
    assert source_station.fluid_identity == FLUID_FRESH_WATER
    assert source_station.package_candidate_id is None
    assert source_station.package_evidence_sha256 is None
    assert source_station.envelope_mm is None
    assert source_station.placement_xyz_mm is None
    assert source_station.orientation_axis_xyz is None
    assert source_station.tubing_inner_diameter_mm is None
    assert source_station.minimum_bend_radius_mm is None
    assert source_station.connector_standard is None


def test_reference_package_support_ports_and_clearance_are_valid_deterministic_breps(realized):
    for shape in (
        realized.package_reference_solid,
        realized.support_cradle_solid,
        realized.inlet_port_reservation_solid,
        realized.outlet_port_reservation_solid,
        realized.service_clearance_solid,
    ):
        assert shape.solids().size() == 1
        assert shape.val().isValid()
        assert shape.val().Volume() > 0.0

    assert realized.reference_envelope_volume_mm3 == pytest.approx(
        PACKAGE_ENVELOPE_XYZ_MM[0] * PACKAGE_ENVELOPE_XYZ_MM[1] * PACKAGE_ENVELOPE_XYZ_MM[2],
        abs=1e-9,
    )
    assert realized.package_reference_solid.val().intersect(realized.support_cradle_solid.val()).Volume() <= 1e-7
    assert realized.package_reference_solid.val().distance(realized.support_cradle_solid.val()) == pytest.approx(0.4, abs=1e-9)

    for shape in (
        realized.package_reference_solid,
        realized.support_cradle_solid,
        realized.inlet_port_reservation_solid,
        realized.outlet_port_reservation_solid,
    ):
        assert shape.val().cut(realized.service_clearance_solid.val()).Volume() <= 1e-7

    manifest = realized.manifest()
    assert manifest["service_clearance"]["reservation_mm"] == PACKAGE_CLEARANCE_RESERVATION_MM
    assert manifest["service_clearance"]["replacement_trajectory_world_mm"] is None
    assert manifest["support"]["cavity_classification"] == "WET_DRAINABLE"
    assert manifest["support"]["drain_dry_path"] == "OPEN_AT_BOTH_Y_ENDS_NO_ENCLOSED_SUPPORT_CAVITY"
    assert manifest["support"]["frame_join_geometry"] is None
    assert manifest["support"]["retention_geometry"] is None


def test_port_datums_preserve_exact_fresh_water_routes_without_claiming_connector_selection(realized):
    assert tuple(port.datum_id for port in realized.port_datums) == PORT_DATUM_IDS
    inlet, outlet = realized.port_datums

    assert inlet.datum_id == INLET_DATUM_ID
    assert inlet.route_id == ROUTE_WATER_SOURCE
    assert inlet.source_interface_id == PORT_PICKUP
    assert inlet.target_interface_id == STATION_WATER

    assert outlet.datum_id == OUTLET_DATUM_ID == INTERFACE_WATER_PUMP_OUTLET
    assert outlet.route_id == ROUTE_WATER_MANIFOLD
    assert outlet.source_interface_id == INTERFACE_WATER_PUMP_OUTLET
    assert outlet.target_interface_id == "MANIFOLD-INLET-WATER-I23"

    for port in realized.port_datums:
        assert port.fluid_identity == FLUID_FRESH_WATER
        assert port.lumen_diameter_seed_mm == PORT_LUMEN_DIAMETER_SEED_MM
        assert port.reservation_diameter_mm == PORT_RESERVATION_DIAMETER_MM
        assert port.lumen_area_seed_mm2 == pytest.approx(3.141592653589793, abs=1e-12)
        assert "NOT_CONNECTOR_OR_TUBING_SELECTION" in port.status

    routing = realized.manifest()["routing"]
    assert routing["source_to_pump_centerline"] is None
    assert routing["pump_to_manifold_centerline"] is None
    assert routing["tubing_inner_diameter_mm"] is None
    assert routing["minimum_bend_radius_mm"] is None
    assert routing["connector_standard"] is None


def test_evidence_firewall_rejects_stale_sources_supplier_promotion_and_wrong_fluid(sources, realized):
    with pytest.raises(RealizedFreshWaterPumpError, match="stale for current fresh-pump architecture"):
        replace(realized, source_fresh_pump_architecture_sha256="0" * 64).validate_current_sources(sources)
    with pytest.raises(RealizedFreshWaterPumpError, match="selected supplier package"):
        replace(realized, supplier_package_candidate_id="UNCONTROLLED-PUMP")
    with pytest.raises(RealizedFreshWaterPumpError, match="FRESH_WATER"):
        replace(realized, fluid_identity="CLEANSER")
    with pytest.raises(RealizedFreshWaterPumpError, match="cannot become physical validation"):
        replace(realized, physical_validation_eligible=True)


def test_manifest_is_deterministic_and_contains_no_unearned_performance_claims(realized):
    manifest = realized.manifest()
    assert manifest["manifest_sha256"] == realized.manifest_sha256
    assert manifest["fluid_identity"] == "FRESH_WATER"
    assert manifest["supplier_package_candidate_id"] is None
    assert manifest["supplier_package_evidence_sha256"] is None
    assert manifest["physical_validation_eligible"] is False
    assert all(value is None for value in manifest["performance_claims"].values())
