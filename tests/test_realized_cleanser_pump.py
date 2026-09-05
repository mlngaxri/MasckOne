from dataclasses import replace

import cadquery as cq
import pytest

from masck_one.fresh_pump_packaging import (
    FLUID_CLEANSER,
    INTERFACE_CLEANSER_PUMP_OUTLET,
    ROUTE_CLEANSER_MANIFOLD,
    ROUTE_CLEANSER_SOURCE,
    STATION_CLEANSER,
)
from masck_one.realized_cleanser_pump import (
    INLET_DATUM_ID,
    OUTLET_DATUM_ID,
    PACKAGE_ENVELOPE_XYZ_MM,
    PORT_AXIS_WORLD,
    PORT_DATUM_IDS,
    SERVICE_CLEARANCE_BOUNDS_WORLD_MM,
    SUPPLIER_DIMENSIONAL_SCREENING_REFERENCES,
    RealizedCleanserPumpError,
    build_current_cleanser_pump_sources,
    build_realized_cleanser_pump,
)
from masck_one.realized_waste_backbone import ArcXY, Line3, build_cell4_waste_backbone
from masck_one.cleanser_storage import PORT_OUTLET


@pytest.fixture(scope="module")
def sources():
    return build_current_cleanser_pump_sources()


@pytest.fixture(scope="module")
def realized(sources):
    return build_realized_cleanser_pump(sources)


def _protected_zone_prism(zone) -> cq.Workplane:
    prism = (
        cq.Workplane("XY")
        .workplane(offset=-100.0)
        .center(zone.center.x, zone.center.y)
        .ellipse(zone.envelope_width_mm / 2.0, zone.envelope_height_mm / 2.0)
        .extrude(200.0)
    )
    if zone.angle_deg:
        prism = prism.rotate(
            (zone.center.x, zone.center.y, 0.0),
            (zone.center.x, zone.center.y, 1.0),
            zone.angle_deg,
        )
    return prism


def _primitive_edge(primitive: Line3 | ArcXY) -> cq.Edge:
    if type(primitive) is Line3:
        return cq.Edge.makeLine(
            cq.Vector(*primitive.start.as_tuple()),
            cq.Vector(*primitive.end.as_tuple()),
        )
    if type(primitive) is ArcXY:
        midpoint = primitive.point_at(
            float(primitive.start_angle_deg) + 0.5 * float(primitive.sweep_angle_deg)
        )
        return cq.Edge.makeThreePointArc(
            cq.Vector(*primitive.start.as_tuple()),
            cq.Vector(*midpoint.as_tuple()),
            cq.Vector(*primitive.end.as_tuple()),
        )
    raise AssertionError(f"uncontrolled released waste primitive type: {type(primitive)!r}")


def test_cleanser_pump_binds_exact_controlled_station_without_supplier_selection(sources, realized):
    assert realized.validate_current_sources(sources) == sources.architecture
    assert realized.station_id == STATION_CLEANSER
    assert realized.fluid_identity == FLUID_CLEANSER
    assert realized.source_cleanser_architecture_sha256 == sources.cleanser.architecture_sha256
    station = sources.architecture.stations[1]
    assert station.station_id == STATION_CLEANSER
    assert station.fluid_identity == FLUID_CLEANSER
    assert station.source_port_id == PORT_OUTLET
    assert station.pump_outlet_interface_id == INTERFACE_CLEANSER_PUMP_OUTLET
    assert station.package_candidate_id is None
    assert station.package_evidence_sha256 is None
    assert station.envelope_mm is None
    assert station.placement_xyz_mm is None
    assert station.orientation_axis_xyz is None
    assert station.tubing_inner_diameter_mm is None
    assert station.minimum_bend_radius_mm is None
    assert station.connector_standard is None
    assert realized.supplier_package_candidate_id is None
    assert realized.supplier_package_evidence_sha256 is None


def test_cleanser_pump_geometry_is_distinct_valid_and_drainable(realized):
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
        abs=1e-8,
    )
    assert realized.package_reference_solid.val().intersect(
        realized.support_cradle_solid.val()
    ).Volume() <= 1e-7
    assert realized.package_reference_solid.val().distance(
        realized.support_cradle_solid.val()
    ) == pytest.approx(0.4, abs=1e-9)

    manifest = realized.manifest()
    assert manifest["support"]["cavity_classification"] == "WET_DRAINABLE"
    assert manifest["support"]["drain_dry_path"] == "OPEN_AT_BOTH_Y_ENDS_NO_ENCLOSED_SUPPORT_CAVITY"
    assert manifest["support"]["frame_join_geometry"] is None
    assert manifest["support"]["retention_geometry"] is None
    assert manifest["service_clearance"]["bounds_world_mm"] == {
        key: list(value) for key, value in SERVICE_CLEARANCE_BOUNDS_WORLD_MM.items()
    }


def test_ports_retain_only_cleanser_routes_and_mirrored_local_direction(realized):
    assert tuple(item.datum_id for item in realized.port_datums) == PORT_DATUM_IDS
    inlet, outlet = realized.port_datums
    assert inlet.datum_id == INLET_DATUM_ID
    assert inlet.route_id == ROUTE_CLEANSER_SOURCE
    assert inlet.source_interface_id == PORT_OUTLET
    assert inlet.target_interface_id == STATION_CLEANSER
    assert outlet.datum_id == OUTLET_DATUM_ID == INTERFACE_CLEANSER_PUMP_OUTLET
    assert outlet.route_id == ROUTE_CLEANSER_MANIFOLD
    assert outlet.source_interface_id == INTERFACE_CLEANSER_PUMP_OUTLET
    assert outlet.target_interface_id == "MANIFOLD-INLET-CLEANSER-I23"
    for item in realized.port_datums:
        assert item.fluid_identity == FLUID_CLEANSER
        assert item.axis_world == PORT_AXIS_WORLD

    routing = realized.manifest()["routing"]
    assert routing["source_to_pump_centerline"] is None
    assert routing["pump_to_manifold_centerline"] is None
    assert routing["tubing_inner_diameter_mm"] is None
    assert routing["minimum_bend_radius_mm"] is None
    assert routing["connector_standard"] is None


def test_supplier_dimensions_are_screening_only_and_performance_claims_stay_empty(realized):
    assert len(SUPPLIER_DIMENSIONAL_SCREENING_REFERENCES) == 3
    for reference in SUPPLIER_DIMENSIONAL_SCREENING_REFERENCES:
        assert "NOT_CLEANSER_SUITABILITY_OR_SELECTION" in reference["selection_status"]

    manifest = realized.manifest()
    assert manifest["supplier_dimensional_screening"]["selection_status"] == "NO_CLEANSER_PUMP_SELECTED"
    assert all(value is None for value in manifest["performance_claims"].values())
    assert manifest["fresh_water_identity_unchanged"] is True
    assert "PASSIVE_BACKFLOW_PROTECTION" in manifest["mixed_waste_architecture_unchanged"]
    assert manifest["physical_validation_eligible"] is False


def test_stale_sources_wrong_fluid_and_evidence_promotion_fail_closed(sources, realized):
    with pytest.raises(RealizedCleanserPumpError, match="stale for current pump architecture"):
        replace(realized, source_fresh_pump_architecture_sha256="0" * 64).validate_current_sources(sources)
    with pytest.raises(RealizedCleanserPumpError, match="CLEANSER"):
        replace(realized, fluid_identity="FRESH_WATER")
    with pytest.raises(RealizedCleanserPumpError, match="cannot become physical validation"):
        replace(realized, physical_validation_eligible=True)


def test_complete_service_reservation_clears_released_product_and_protected_packages(sources, realized):
    service = realized.service_clearance_solid
    model = sources.model
    packages = (
        model.shell.solid,
        *(actuator.solid for actuator in model.actuator_envelopes),
        model.water_reservoir_envelope.solid,
        model.waste_cartridge_envelope.solid,
        model.battery_reference_envelope.solid,
    )
    for package in packages:
        assert service.val().intersect(package.val()).Volume() <= 1e-7
        assert service.val().distance(package.val()) > 0.0

    hard_margins = []
    for protected in model.protected_volumes.all:
        prism = _protected_zone_prism(protected.zone)
        assert service.val().intersect(prism.val()).Volume() <= 1e-7
        hard_margins.append(float(service.val().distance(prism.val())))
    assert min(hard_margins) > 4.5


def test_complete_service_reservation_clears_released_mixed_waste_route_envelopes(realized):
    # Geometry-only reconstruction reuses the released route builder; source-release
    # freshness is already governed by the dedicated waste release tests on main.
    waste = build_cell4_waste_backbone(
        source_git_sha="0" * 40,
        source_waste_pump_architecture_sha256="0" * 64,
    )
    service = realized.service_clearance_solid.val()
    for route in waste.routes:
        for primitive in route.centerline:
            residual = float(service.distance(_primitive_edge(primitive))) - route.service_envelope_radius_mm
            assert residual > 0.0


def test_cleanser_pump_step_round_trip_and_manifest_are_deterministic(tmp_path, realized):
    exports = {
        "package": realized.package_reference_solid,
        "support": realized.support_cradle_solid,
        "inlet": realized.inlet_port_reservation_solid,
        "outlet": realized.outlet_port_reservation_solid,
        "service": realized.service_clearance_solid,
    }
    for name, source in exports.items():
        path = tmp_path / f"{name}.step"
        cq.exporters.export(source, str(path))
        loaded = cq.importers.importStep(str(path))
        assert loaded.solids().size() == 1
        assert loaded.val().isValid()
        assert loaded.val().Volume() == pytest.approx(source.val().Volume(), rel=2e-6, abs=2e-5)

    first = realized.manifest()
    second = realized.manifest()
    assert first == second
    assert first["manifest_sha256"] == realized.manifest_sha256
