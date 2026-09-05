from dataclasses import replace
import math

import cadquery as cq
import pytest

from masck_one.model import build_model
from masck_one.realized_passive_backflow import (
    AUTHORED_AGAINST_MAIN_SHA,
    DRAIN_DRY_CLEARANCE_XYZ_MM,
    MIXED_PHASE_CONSTITUENTS,
    PACKAGE_BOUNDS_WORLD_MM,
    PACKAGE_ENVELOPE_XYZ_MM,
    ROUTE_GRAPH_ANCHOR_WORLD_MM,
    ROUTE_INTERFACE_RESERVATION_DIAMETER_MM,
    ROUTE_LUMEN_DIAMETER_SEED_MM,
    SERVICE_CLEARANCE_BOUNDS_WORLD_MM,
    SERVICE_CLEARANCE_XYZ_MM,
    SOURCE_REALIZED_WASTE_BACKBONE_BLOB_SHA,
    SOURCE_REALIZED_WASTE_RELEASE_BLOB_SHA,
    SOURCE_WASTE_PUMP_ARCHITECTURE_BLOB_SHA,
    SUPPORT_CAVITY_CLASSIFICATION,
    RealizedPassiveBackflowError,
    build_realized_passive_backflow_package,
)
from masck_one.realized_waste_backbone_release import (
    build_current_cell4_waste_backbone_release,
)
from masck_one.waste_acquisition import PHASE_MIXED_WASTE
from masck_one.waste_pump_architecture import (
    BARRIER_PERFORMANCE_STATUS,
    BARRIER_SELECTION_STATUS,
    BARRIER_WASTE,
    INTERFACE_BARRIER_OUTLET,
    INTERFACE_CARTRIDGE_INLET_I27,
    INTERFACE_PUMP_OUTLET,
    ROUTE_BARRIER_TO_CARTRIDGE,
    ROUTE_PUMP_TO_BARRIER,
)


KERNEL_TOL_MM = 2e-6
KERNEL_ZERO_MM3 = 1e-7


@pytest.fixture(scope="module")
def release():
    return build_current_cell4_waste_backbone_release()


@pytest.fixture(scope="module")
def package(release):
    return build_realized_passive_backflow_package(release)


@pytest.fixture(scope="module")
def model():
    return build_model()


def _bounds(shape: cq.Workplane) -> tuple[float, float, float, float, float, float]:
    bb = shape.val().BoundingBox()
    return (
        float(bb.xmin),
        float(bb.xmax),
        float(bb.ymin),
        float(bb.ymax),
        float(bb.zmin),
        float(bb.zmax),
    )


def _assert_bounds(
    shape: cq.Workplane,
    expected: tuple[float, float, float, float, float, float],
) -> None:
    actual = _bounds(shape)
    assert actual == pytest.approx(expected, abs=KERNEL_TOL_MM)


def _assert_one_valid_positive(shape: cq.Workplane) -> None:
    assert shape.solids().size() == 1
    assert shape.val().isValid()
    assert float(shape.val().Volume()) > 0.0


def test_passive_backflow_package_is_source_bound_to_released_mixed_waste_topology(
    release,
    package,
):
    package.validate_source_release(release)

    assert package.authored_against_git_sha == AUTHORED_AGAINST_MAIN_SHA
    assert (
        package.source_waste_pump_architecture_sha256
        == release.source_waste_pump_architecture_sha256
    )
    assert package.source_backbone_realization_sha256 == release.realization.manifest_sha256
    assert package.source_authority_revision == release.realization.authority_revision
    assert package.fluid_identity == PHASE_MIXED_WASTE
    assert tuple(item.fluid_identity for item in package.interface_datums) == (
        PHASE_MIXED_WASTE,
        PHASE_MIXED_WASTE,
    )

    by_id = {route.route_id: route for route in release.realization.routes}
    upstream = by_id[ROUTE_PUMP_TO_BARRIER]
    downstream = by_id[ROUTE_BARRIER_TO_CARTRIDGE]
    assert upstream.target_interface_id == BARRIER_WASTE
    assert downstream.source_interface_id == INTERFACE_BARRIER_OUTLET
    assert upstream.centerline[-1].end.as_tuple() == ROUTE_GRAPH_ANCHOR_WORLD_MM
    assert downstream.centerline[0].start.as_tuple() == ROUTE_GRAPH_ANCHOR_WORLD_MM


def test_passive_backflow_source_blob_bindings_are_exact(package):
    manifest = package.manifest()
    assert manifest["source_blob_bindings"] == {
        "waste_pump_architecture.py": SOURCE_WASTE_PUMP_ARCHITECTURE_BLOB_SHA,
        "realized_waste_backbone.py": SOURCE_REALIZED_WASTE_BACKBONE_BLOB_SHA,
        "realized_waste_backbone_release.py": SOURCE_REALIZED_WASTE_RELEASE_BLOB_SHA,
    }


def test_package_is_honest_screening_geometry_not_component_selection(package):
    assert package.selected_component_id is None
    assert package.selected_component_evidence_sha256 is None
    assert package.selected_component_geometry is None
    assert package.cracking_pressure_kPa is None
    assert package.reverse_leakage_mL_min is None
    assert package.selection_status == BARRIER_SELECTION_STATUS
    assert package.performance_status == BARRIER_PERFORMANCE_STATUS
    assert package.physical_validation_eligible is False

    manifest = package.manifest()
    assert manifest["package"]["selected_component_id"] is None
    assert manifest["package"]["selected_component_geometry"] is None
    assert manifest["performance_claims"]["reverse_flow_blocking_validated"] is False
    assert manifest["performance_claims"]["mixed_phase_foam_behavior"] is None
    assert manifest["mixed_phase_constituents"] == list(MIXED_PHASE_CONSTITUENTS)
    assert manifest["topology_order"] == [
        "ACQUISITION",
        "WASTE_PUMP",
        "PASSIVE_BACKFLOW_PROTECTION",
        "CARTRIDGE",
    ]


def test_route_graph_interfaces_are_exact_and_selected_port_spacing_remains_unresolved(
    package,
):
    upstream, downstream = package.interface_datums
    assert (
        upstream.route_id,
        upstream.source_interface_id,
        upstream.target_interface_id,
    ) == (
        ROUTE_PUMP_TO_BARRIER,
        INTERFACE_PUMP_OUTLET,
        BARRIER_WASTE,
    )
    assert (
        downstream.route_id,
        downstream.source_interface_id,
        downstream.target_interface_id,
    ) == (
        ROUTE_BARRIER_TO_CARTRIDGE,
        INTERFACE_BARRIER_OUTLET,
        INTERFACE_CARTRIDGE_INLET_I27,
    )
    for datum in package.interface_datums:
        assert datum.center_world_mm == ROUTE_GRAPH_ANCHOR_WORLD_MM
        assert datum.selected_port_separation_mm is None
        assert datum.connector_standard is None
        assert datum.lumen_diameter_seed_mm == ROUTE_LUMEN_DIAMETER_SEED_MM
        assert datum.reservation_diameter_mm == ROUTE_INTERFACE_RESERVATION_DIAMETER_MM

    graph = package.manifest()["route_graph_anchor"]
    assert graph["co_located_graph_interfaces"] is True
    assert graph["selected_device_port_separation_mm"] is None
    assert graph["connector_standard"] is None


def test_package_support_drain_and_service_geometry_are_deterministic(package):
    for shape in (
        package.package_screening_solid,
        package.support_cradle_solid,
        package.upstream_route_anchor_solid,
        package.downstream_route_anchor_solid,
        package.drain_dry_clearance_solid,
        package.service_clearance_solid,
    ):
        _assert_one_valid_positive(shape)

    _assert_bounds(
        package.package_screening_solid,
        (
            PACKAGE_BOUNDS_WORLD_MM["x"][0],
            PACKAGE_BOUNDS_WORLD_MM["x"][1],
            PACKAGE_BOUNDS_WORLD_MM["y"][0],
            PACKAGE_BOUNDS_WORLD_MM["y"][1],
            PACKAGE_BOUNDS_WORLD_MM["z"][0],
            PACKAGE_BOUNDS_WORLD_MM["z"][1],
        ),
    )
    _assert_bounds(
        package.service_clearance_solid,
        (
            SERVICE_CLEARANCE_BOUNDS_WORLD_MM["x"][0],
            SERVICE_CLEARANCE_BOUNDS_WORLD_MM["x"][1],
            SERVICE_CLEARANCE_BOUNDS_WORLD_MM["y"][0],
            SERVICE_CLEARANCE_BOUNDS_WORLD_MM["y"][1],
            SERVICE_CLEARANCE_BOUNDS_WORLD_MM["z"][0],
            SERVICE_CLEARANCE_BOUNDS_WORLD_MM["z"][1],
        ),
    )

    assert package.package_envelope_volume_mm3 == math.prod(PACKAGE_ENVELOPE_XYZ_MM)
    assert package.support_cavity_classification == SUPPORT_CAVITY_CLASSIFICATION
    assert package.manifest()["support"]["cavity_classification"] == "WET_DRAINABLE"
    assert package.manifest()["support"]["selected_device_internal_cavity_geometry"] is None
    assert package.manifest()["service_clearance"]["replacement_trajectory_world_mm"] is None
    assert package.manifest()["drain_dry"]["xyz_mm"] == list(DRAIN_DRY_CLEARANCE_XYZ_MM)
    assert package.manifest()["service_clearance"]["xyz_mm"] == list(SERVICE_CLEARANCE_XYZ_MM)


def test_open_support_preserves_actual_low_point_drain_dry_free_space(package):
    assert (
        package.package_screening_solid.val()
        .intersect(package.support_cradle_solid.val())
        .Volume()
        <= KERNEL_ZERO_MM3
    )
    assert (
        package.drain_dry_clearance_solid.val()
        .intersect(package.package_screening_solid.val())
        .Volume()
        <= KERNEL_ZERO_MM3
    )
    assert (
        package.drain_dry_clearance_solid.val()
        .intersect(package.support_cradle_solid.val())
        .Volume()
        <= KERNEL_ZERO_MM3
    )

    drain = package.drain_dry_clearance_solid.val().BoundingBox()
    support = package.support_cradle_solid.val().BoundingBox()
    body = package.package_screening_solid.val().BoundingBox()
    assert drain.ymax == pytest.approx(support.ymax, abs=KERNEL_TOL_MM)
    assert drain.zmax < body.zmin


def test_stationary_service_reservation_contains_all_local_reference_geometry(package):
    service = package.service_clearance_solid.val()
    for shape in (
        package.package_screening_solid,
        package.support_cradle_solid,
        package.upstream_route_anchor_solid,
        package.downstream_route_anchor_solid,
        package.drain_dry_clearance_solid,
    ):
        outside = float(shape.val().cut(service).Volume())
        assert outside <= KERNEL_ZERO_MM3


def test_released_main_package_and_service_clear_current_rigid_geometry(model, package):
    # Digital B-rep collision/reservation checks only. They do not prove assembly,
    # deformation, wet serviceability, reverse-flow performance, or physical safety.
    package_shape = package.package_screening_solid.val()
    service_shape = package.service_clearance_solid.val()

    assert package_shape.intersect(model.shell.solid.val()).Volume() <= KERNEL_ZERO_MM3
    assert service_shape.intersect(model.shell.solid.val()).Volume() <= KERNEL_ZERO_MM3
    assert package_shape.distance(model.shell.solid.val()) >= 4.0
    assert service_shape.distance(model.shell.solid.val()) >= 2.0

    for actuator in model.actuator_envelopes:
        assert service_shape.intersect(actuator.solid.val()).Volume() <= KERNEL_ZERO_MM3
    for component in (
        model.water_reservoir_envelope,
        model.waste_cartridge_envelope,
        model.battery_reference_envelope,
    ):
        assert service_shape.intersect(component.solid.val()).Volume() <= KERNEL_ZERO_MM3


def test_selected_component_or_performance_promotion_fails_closed(package):
    with pytest.raises(RealizedPassiveBackflowError):
        replace(package, selected_component_id="uncontrolled_check_valve").validate_invariants()
    with pytest.raises(RealizedPassiveBackflowError):
        replace(package, cracking_pressure_kPa=1.0).validate_invariants()
    with pytest.raises(RealizedPassiveBackflowError):
        replace(package, physical_validation_eligible=True).validate_invariants()


def test_stale_backbone_realization_digest_fails_closed(release, package):
    stale = replace(package, source_backbone_realization_sha256="0" * 64)
    with pytest.raises(RealizedPassiveBackflowError):
        stale.validate_source_release(release)


def test_passive_backflow_manifest_is_reproducible(package):
    first = package.manifest()
    second = package.manifest()
    assert first == second
    assert first["manifest_sha256"] == package.manifest_sha256


@pytest.mark.parametrize(
    "attribute",
    (
        "package_screening_solid",
        "support_cradle_solid",
        "upstream_route_anchor_solid",
        "downstream_route_anchor_solid",
        "drain_dry_clearance_solid",
        "service_clearance_solid",
    ),
)
def test_passive_backflow_step_roundtrip(tmp_path, package, attribute):
    source = getattr(package, attribute)
    path = tmp_path / f"{attribute}.step"
    cq.exporters.export(source, str(path))
    imported = cq.importers.importStep(str(path))
    _assert_one_valid_positive(imported)

    source_bb = source.val().BoundingBox()
    imported_bb = imported.val().BoundingBox()
    assert imported_bb.xmin == pytest.approx(source_bb.xmin, abs=KERNEL_TOL_MM)
    assert imported_bb.xmax == pytest.approx(source_bb.xmax, abs=KERNEL_TOL_MM)
    assert imported_bb.ymin == pytest.approx(source_bb.ymin, abs=KERNEL_TOL_MM)
    assert imported_bb.ymax == pytest.approx(source_bb.ymax, abs=KERNEL_TOL_MM)
    assert imported_bb.zmin == pytest.approx(source_bb.zmin, abs=KERNEL_TOL_MM)
    assert imported_bb.zmax == pytest.approx(source_bb.zmax, abs=KERNEL_TOL_MM)
