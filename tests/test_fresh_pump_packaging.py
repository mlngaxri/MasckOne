from dataclasses import replace

import pytest

from masck_one.boundary_release import build_verified_interface_boundary_topology
from masck_one.cleanser_storage import build_cleanser_storage_architecture
from masck_one.fresh_pump_packaging import (
    PUMP_ROUTING_STATUS,
    PUMP_SERVICE_STATUS,
    FreshPumpPackagingError,
    ROUTE_SERVICE_STATUS,
    ROUTE_IDS,
    STATION_IDS,
    build_fresh_pump_packaging_architecture,
)
from masck_one.interface_attachment import build_interface_attachment_architecture
from masck_one.model import build_model
from masck_one.structural_frame import build_structural_frame_topology
from masck_one.water_reservoir import build_water_reservoir_architecture


@pytest.fixture(scope="module")
def built():
    model = build_model()
    boundaries = build_verified_interface_boundary_topology(
        model.authority,
        model.facial_surface,
        model.coverage_mesh,
        model.compliant_interface_topology,
    )
    attachment = build_interface_attachment_architecture(model.authority, boundaries)
    frame = build_structural_frame_topology(model.authority, attachment)
    water = build_water_reservoir_architecture(model.authority)
    cleanser = build_cleanser_storage_architecture(model.authority)
    architecture = build_fresh_pump_packaging_architecture(model.authority, water, cleanser, frame)
    return model.authority, water, cleanser, frame, architecture


def test_dual_stations_bind_exact_sources_and_frame_reservation(built):
    _, water, cleanser, frame, architecture = built
    assert tuple(item.station_id for item in architecture.stations) == STATION_IDS
    assert tuple(item.fluid_identity for item in architecture.stations) == ("FRESH_WATER", "CLEANSER")
    assert architecture.source_water_architecture_sha256 == water.architecture_sha256
    assert architecture.source_cleanser_architecture_sha256 == cleanser.architecture_sha256
    assert architecture.source_structural_frame_sha256 == frame.topology_sha256


def test_routes_are_complete_separate_and_unresolved(built):
    *_, architecture = built
    assert tuple(item.route_id for item in architecture.routes) == ROUTE_IDS
    assert tuple(item.fluid_identity for item in architecture.routes) == (
        "FRESH_WATER",
        "FRESH_WATER",
        "CLEANSER",
        "CLEANSER",
    )
    assert all("UNRESOLVED" in item.geometry_status for item in architecture.routes)
    assert all("VALIDATION_GATED" in item.hydraulic_status for item in architecture.routes)


def test_supplier_and_routing_geometry_are_not_invented(built):
    *_, architecture = built
    for station in architecture.stations:
        assert station.package_candidate_id is None
        assert station.envelope_mm is None
        assert station.placement_xyz_mm is None
        assert station.tubing_inner_diameter_mm is None
        assert station.minimum_bend_radius_mm is None
        assert station.connector_standard is None
    with pytest.raises(FreshPumpPackagingError, match="cannot invent pump selection"):
        replace(architecture.stations[0], envelope_mm=(30.0, 15.0, 4.0))


def test_cross_connection_and_missing_route_fail_closed(built):
    *_, architecture = built
    crossed = list(architecture.routes)
    crossed[0] = replace(crossed[0], target_interface_id=STATION_IDS[1])
    with pytest.raises(FreshPumpPackagingError, match="cannot cross"):
        replace(architecture, routes=tuple(crossed))
    with pytest.raises(FreshPumpPackagingError, match="complete controlled route order"):
        replace(architecture, routes=architecture.routes[:-1])


def test_station_source_and_outlet_bindings_cannot_cross(built):
    *_, architecture = built
    stations = list(architecture.stations)
    stations[0] = replace(stations[0], source_port_id=stations[1].source_port_id)
    with pytest.raises(FreshPumpPackagingError, match="source and outlet bindings cannot cross"):
        replace(architecture, stations=tuple(stations))


def test_station_identity_swap_and_mutable_containers_fail_closed(built):
    *_, architecture = built
    with pytest.raises(FreshPumpPackagingError, match="controlled water/cleanser order"):
        replace(architecture, stations=tuple(reversed(architecture.stations)))
    with pytest.raises(FreshPumpPackagingError, match="immutable two-station tuple"):
        replace(architecture, stations=list(architecture.stations))
    with pytest.raises(FreshPumpPackagingError, match="immutable tuple"):
        replace(architecture, routes=list(architecture.routes))


def test_stale_source_and_physical_promotion_are_rejected(built):
    authority, water, cleanser, frame, architecture = built
    stations = list(architecture.stations)
    stations[0] = replace(stations[0], source_architecture_sha256="a" * 64)
    with pytest.raises(FreshPumpPackagingError, match="stale for current water"):
        replace(architecture, source_water_architecture_sha256="a" * 64, stations=tuple(stations)).validate_current_sources(
            authority=authority, water=water, cleanser=cleanser, frame=frame
        )
    with pytest.raises(FreshPumpPackagingError, match="cannot be physical validation"):
        replace(architecture, physical_validation_eligible=True)


def test_builder_rejects_storage_contracts_stale_for_current_authority(built):
    authority, water, cleanser, frame, _ = built
    with pytest.raises(FreshPumpPackagingError, match="water architecture is stale"):
        build_fresh_pump_packaging_architecture(
            authority,
            replace(water, source_authority_revision="STALE-AUTHORITY"),
            cleanser,
            frame,
        )
    with pytest.raises(FreshPumpPackagingError, match="cleanser architecture is stale"):
        build_fresh_pump_packaging_architecture(
            authority,
            water,
            replace(cleanser, source_authority_revision="STALE-AUTHORITY"),
            frame,
        )
    with pytest.raises(FreshPumpPackagingError, match="exact Authority"):
        build_fresh_pump_packaging_architecture(object(), water, cleanser, frame)


def test_hostile_string_aliases_fail_at_identity_boundary(built):
    class LyingStr(str):
        pass

    *_, architecture = built
    with pytest.raises(FreshPumpPackagingError, match="unknown pump station"):
        replace(architecture.stations[0], station_id=LyingStr(STATION_IDS[0]))
    with pytest.raises(FreshPumpPackagingError, match="canonical lowercase SHA-256"):
        replace(architecture, source_water_architecture_sha256=LyingStr("a" * 64))


def test_status_tokens_cannot_be_spoofed_by_substring_aliases(built):
    *_, architecture = built
    with pytest.raises(FreshPumpPackagingError, match="package selection must remain unresolved"):
        replace(architecture.stations[0], package_status="NOT_UNRESOLVED_BUT_CONTAINS_TOKEN")
    with pytest.raises(FreshPumpPackagingError, match="metering performance must remain validation gated"):
        replace(architecture.stations[0], metering_performance_status="NOT_VALIDATION_GATED_BUT_CONTAINS_TOKEN")
    with pytest.raises(FreshPumpPackagingError, match="route geometry must remain unresolved"):
        replace(architecture.routes[0], geometry_status="NOT_UNRESOLVED_BUT_CONTAINS_TOKEN")
    with pytest.raises(FreshPumpPackagingError, match="route hydraulics must remain validation gated"):
        replace(architecture.routes[0], hydraulic_status="NOT_VALIDATION_GATED_BUT_CONTAINS_TOKEN")


def test_routing_and_service_states_are_controlled_and_fail_closed(built):
    *_, architecture = built
    station = architecture.stations[0]
    route = architecture.routes[0]

    assert station.routing_status == PUMP_ROUTING_STATUS
    assert station.service_status == PUMP_SERVICE_STATUS
    assert route.service_status == ROUTE_SERVICE_STATUS

    with pytest.raises(FreshPumpPackagingError, match="routing status"):
        replace(station, routing_status="VALIDATED")
    with pytest.raises(FreshPumpPackagingError, match="service status"):
        replace(station, service_status="SERVICE_VERIFIED")
    with pytest.raises(FreshPumpPackagingError, match="service status"):
        replace(route, service_status="SERVICE_VERIFIED")

    class LyingStr(str):
        pass

    with pytest.raises(FreshPumpPackagingError, match="routing status"):
        replace(station, routing_status=LyingStr(station.routing_status))
    with pytest.raises(FreshPumpPackagingError, match="service status"):
        replace(station, service_status=LyingStr(station.service_status))
    with pytest.raises(FreshPumpPackagingError, match="service status"):
        replace(route, service_status=LyingStr(route.service_status))


def test_architecture_evidence_status_is_controlled_and_fail_closed(built):
    *_, architecture = built
    with pytest.raises(FreshPumpPackagingError, match="evidence status"):
        replace(architecture, evidence_status="ARBITRARY_NONBLANK_STATUS")

    class LyingStr(str):
        pass

    with pytest.raises(FreshPumpPackagingError, match="evidence status"):
        replace(architecture, evidence_status=LyingStr(architecture.evidence_status))


def test_manifest_is_deterministic_and_not_physical_evidence(built):
    authority, water, cleanser, frame, architecture = built
    second = build_fresh_pump_packaging_architecture(authority, water, cleanser, frame)
    assert architecture.manifest() == second.manifest()
    assert architecture.architecture_sha256 == second.architecture_sha256
    assert architecture.physical_validation_eligible is False
    assert "NOT_PACKAGE_SELECTION" in architecture.evidence_status
