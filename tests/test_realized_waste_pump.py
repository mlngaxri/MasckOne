from dataclasses import replace
import math

import cadquery as cq
import pytest

from masck_one.model import build_model
from masck_one.realized_waste_backbone import WASTE_ID_SEED_MM
from masck_one.realized_waste_backbone_release import (
    build_current_cell4_waste_backbone_release,
)
from masck_one.realized_waste_pump import (
    DRAIN_DRY_STATUS,
    HYDRAULIC_STATUS,
    MIXED_PHASE_CONSTITUENTS,
    PACKAGE_BOUNDS_WORLD_MM,
    PACKAGE_ENVELOPE_XYZ_MM,
    PACKAGE_STATUS,
    PHYSICAL_EVIDENCE_STATUS,
    SERVICE_CLEARANCE_BOUNDS_WORLD_MM,
    SUPPORT_CAVITY_CLASSIFICATION,
    SUPPORT_PACKAGE_BASE_GAP_SEED_MM,
    RealizedWastePumpError,
    build_realized_waste_pump_package,
)
from masck_one.waste_acquisition import PHASE_MIXED_WASTE
from masck_one.waste_pump_architecture import (
    BARRIER_WASTE,
    INTERFACE_BARRIER_OUTLET,
    INTERFACE_PUMP_OUTLET,
    ROUTE_ACQUISITION_TO_PUMP,
    ROUTE_BARRIER_TO_CARTRIDGE,
    ROUTE_PUMP_TO_BARRIER,
    STATION_WASTE,
)


@pytest.fixture(scope="module")
def release_and_package():
    release = build_current_cell4_waste_backbone_release()
    package = build_realized_waste_pump_package(release)
    return release, package


@pytest.fixture(scope="module")
def current_model():
    return build_model()


def _bounds(shape: cq.Workplane) -> tuple[float, float, float, float, float, float]:
    box = shape.val().BoundingBox()
    return (
        float(box.xmin),
        float(box.xmax),
        float(box.ymin),
        float(box.ymax),
        float(box.zmin),
        float(box.zmax),
    )


def test_package_is_actual_world_coordinate_geometry_with_exact_mixed_waste_identity(
    release_and_package,
):
    release, package = release_and_package
    package.validate_current_backbone(release)

    assert package.physical_validation_eligible is False
    assert package.port_datums[0].fluid_identity == PHASE_MIXED_WASTE
    assert package.port_datums[1].fluid_identity == PHASE_MIXED_WASTE

    manifest = package.manifest()
    assert manifest["station_id"] == STATION_WASTE
    assert manifest["fluid_identity"] == PHASE_MIXED_WASTE
    assert tuple(manifest["mixed_phase_constituents_for_physical_reasoning"]) == MIXED_PHASE_CONSTITUENTS
    assert manifest["package"]["envelope_xyz_mm"] == list(PACKAGE_ENVELOPE_XYZ_MM)
    assert manifest["package"]["bounds_world_mm"] == {
        axis: list(value) for axis, value in PACKAGE_BOUNDS_WORLD_MM.items()
    }
    assert manifest["package"]["supplier_candidate"] is None
    assert manifest["package"]["selected_internal_wet_path_geometry"] is None
    assert manifest["package"]["status"] == PACKAGE_STATUS
    assert manifest["hydraulic_status"] == HYDRAULIC_STATUS
    assert manifest["evidence_status"] == PHYSICAL_EVIDENCE_STATUS

    assert _bounds(package.package_screening_solid) == pytest.approx(
        (-60.0, -48.0, -52.0, -44.0, 8.0, 16.0),
        abs=2e-6,
    )
    for solid in (
        package.package_screening_solid,
        package.support_cradle_solid,
        package.inlet_port_reservation_solid,
        package.outlet_port_reservation_solid,
        package.drain_dry_clearance_solid,
        package.service_clearance_solid,
    ):
        assert solid.solids().size() == 1
        assert solid.val().isValid()
        assert solid.val().Volume() > 0.0


def test_route_anchor_ports_preserve_order_and_do_not_bypass_passive_backflow(
    release_and_package,
):
    release, package = release_and_package
    inlet, outlet = package.port_datums

    assert inlet.route_id == ROUTE_ACQUISITION_TO_PUMP
    assert inlet.target_interface_id == STATION_WASTE
    assert outlet.route_id == ROUTE_PUMP_TO_BARRIER
    assert outlet.source_interface_id == INTERFACE_PUMP_OUTLET
    assert outlet.target_interface_id == BARRIER_WASTE
    assert inlet.center_world_mm == outlet.center_world_mm == (-48.0, -44.0, 16.0)
    assert inlet.lumen_diameter_seed_mm == WASTE_ID_SEED_MM
    assert outlet.lumen_diameter_seed_mm == WASTE_ID_SEED_MM
    assert inlet.lumen_area_seed_mm2 == pytest.approx(
        math.pi * (WASTE_ID_SEED_MM / 2.0) ** 2
    )

    route_ids = tuple(route.route_id for route in release.realization.routes)
    assert route_ids == (
        ROUTE_ACQUISITION_TO_PUMP,
        ROUTE_PUMP_TO_BARRIER,
        ROUTE_BARRIER_TO_CARTRIDGE,
    )
    assert release.realization.routes[2].source_interface_id == INTERFACE_BARRIER_OUTLET

    manifest = package.manifest()
    assert manifest["topology_guard"]["passive_backflow_component_geometry"] is None
    assert manifest["topology_guard"]["passive_backflow_performance"] == "VALIDATION_GATED"


def test_open_cradle_and_low_point_corridor_keep_wet_station_drainable(
    release_and_package,
):
    _, package = release_and_package
    manifest = package.manifest()

    assert manifest["support"]["cavity_classification"] == SUPPORT_CAVITY_CLASSIFICATION
    assert SUPPORT_CAVITY_CLASSIFICATION == "WET_DRAINABLE"
    assert manifest["support"]["package_base_gap_seed_mm"] == SUPPORT_PACKAGE_BASE_GAP_SEED_MM
    assert manifest["drain_dry"]["status"] == DRAIN_DRY_STATUS

    assert package.drain_dry_clearance_solid.val().intersect(
        package.support_cradle_solid.val()
    ).Volume() == pytest.approx(0.0, abs=1e-7)
    assert package.drain_dry_clearance_solid.val().intersect(
        package.package_screening_solid.val()
    ).Volume() == pytest.approx(0.0, abs=1e-7)


def test_stationary_service_reservation_contains_package_support_and_drain_clearance(
    release_and_package,
):
    _, package = release_and_package
    expected = SERVICE_CLEARANCE_BOUNDS_WORLD_MM
    assert _bounds(package.service_clearance_solid) == pytest.approx(
        (
            expected["x"][0],
            expected["x"][1],
            expected["y"][0],
            expected["y"][1],
            expected["z"][0],
            expected["z"][1],
        ),
        abs=2e-6,
    )
    for solid in (
        package.package_screening_solid,
        package.support_cradle_solid,
        package.drain_dry_clearance_solid,
    ):
        assert solid.val().cut(package.service_clearance_solid.val()).Volume() == pytest.approx(
            0.0,
            abs=1e-7,
        )
    assert package.manifest()["service"]["replacement_trajectory"] is None


def test_package_service_and_route_anchor_ports_clear_current_released_rigid_packages(
    release_and_package,
    current_model,
):
    _, package = release_and_package
    screened = (
        current_model.shell.solid,
        *tuple(item.solid for item in current_model.actuator_envelopes),
        current_model.water_reservoir_envelope.solid,
        current_model.waste_cartridge_envelope.solid,
        current_model.battery_reference_envelope.solid,
    )

    for other in screened:
        assert package.package_screening_solid.val().intersect(other.val()).Volume() == pytest.approx(
            0.0,
            abs=1e-7,
        )
        assert package.support_cradle_solid.val().intersect(other.val()).Volume() == pytest.approx(
            0.0,
            abs=1e-7,
        )
        assert package.service_clearance_solid.val().intersect(other.val()).Volume() == pytest.approx(
            0.0,
            abs=1e-7,
        )

    for port in (
        package.inlet_port_reservation_solid,
        package.outlet_port_reservation_solid,
    ):
        assert port.val().intersect(current_model.shell.solid.val()).Volume() == pytest.approx(
            0.0,
            abs=1e-7,
        )
        for actuator in current_model.actuator_envelopes:
            assert port.val().intersect(actuator.solid.val()).Volume() == pytest.approx(
                0.0,
                abs=1e-7,
            )


def test_service_reservation_stays_separate_from_passive_barrier_handoff_service_radius(
    release_and_package,
):
    release, _ = release_and_package
    barrier_route = release.realization.routes[2]
    barrier_point = barrier_route.centerline[0].start
    bounds = SERVICE_CLEARANCE_BOUNDS_WORLD_MM

    dx = max(bounds["x"][0] - barrier_point.x, 0.0, barrier_point.x - bounds["x"][1])
    dy = max(bounds["y"][0] - barrier_point.y, 0.0, barrier_point.y - bounds["y"][1])
    dz = max(bounds["z"][0] - barrier_point.z, 0.0, barrier_point.z - bounds["z"][1])
    point_to_service_box_mm = math.sqrt(dx * dx + dy * dy + dz * dz)

    assert point_to_service_box_mm >= barrier_route.service_envelope_radius_mm
    assert barrier_route.target_interface_id != STATION_WASTE


def test_source_binding_fails_closed_when_backbone_realization_changes(
    release_and_package,
):
    release, package = release_and_package
    stale = replace(package, source_backbone_realization_sha256="0" * 64)
    with pytest.raises(RealizedWastePumpError, match="stale for realized waste backbone"):
        stale.validate_current_backbone(release)


def test_manifest_is_deterministic_and_reference_solids_round_trip_step(
    release_and_package,
    tmp_path,
):
    _, package = release_and_package
    first = package.manifest()
    second = package.manifest()
    assert first == second
    assert first["manifest_sha256"] == package.manifest_sha256

    solids = {
        "package": package.package_screening_solid,
        "cradle": package.support_cradle_solid,
        "inlet": package.inlet_port_reservation_solid,
        "outlet": package.outlet_port_reservation_solid,
        "drain_dry": package.drain_dry_clearance_solid,
        "service": package.service_clearance_solid,
    }
    for name, solid in solids.items():
        path = tmp_path / f"{name}.step"
        cq.exporters.export(solid, str(path))
        reimported = cq.importers.importStep(str(path))
        assert reimported.solids().size() == 1
        assert reimported.val().isValid()
        assert reimported.val().Volume() == pytest.approx(
            solid.val().Volume(),
            rel=1e-7,
            abs=1e-6,
        )
