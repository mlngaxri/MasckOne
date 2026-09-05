import cadquery as cq
import pytest

from masck_one.realized_fresh_water_pump import (
    PACKAGE_CLEARANCE_RESERVATION_MM,
    build_current_fresh_pump_sources,
    build_realized_fresh_water_pump,
)
from masck_one.realized_waste_backbone import ArcXY, Line3, build_cell4_waste_backbone
from masck_one.realized_waste_backbone_release import AUTHORED_AGAINST_MAIN_SHA


@pytest.fixture(scope="module")
def release_geometry():
    sources = build_current_fresh_pump_sources()
    return sources, build_realized_fresh_water_pump(sources)


@pytest.fixture(scope="module")
def released_waste_geometry():
    # Geometry-only reconstruction. The released waste package independently proves
    # current-source binding in its own release tests. Reusing the immutable released
    # centerline builder here avoids a second whole-product source-graph reconstruction
    # while preserving the exact route geometry used by this collision regression.
    return build_cell4_waste_backbone(
        source_git_sha=AUTHORED_AGAINST_MAIN_SHA,
        source_waste_pump_architecture_sha256="0" * 64,
    )


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


def test_complete_local_service_reservation_clears_released_product_packages(release_geometry):
    sources, realized = release_geometry
    model = sources.model
    service = realized.service_clearance_solid

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


def test_reference_package_and_support_preserve_positive_released_package_separation(release_geometry):
    sources, realized = release_geometry
    model = sources.model

    for local_shape in (realized.package_reference_solid, realized.support_cradle_solid):
        for package in (
            model.shell.solid,
            *(actuator.solid for actuator in model.actuator_envelopes),
            model.water_reservoir_envelope.solid,
            model.waste_cartridge_envelope.solid,
            model.battery_reference_envelope.solid,
        ):
            assert local_shape.val().intersect(package.val()).Volume() <= 1e-7
            assert local_shape.val().distance(package.val()) >= PACKAGE_CLEARANCE_RESERVATION_MM


def test_port_reservations_do_not_consume_released_water_reservoir_or_shell(release_geometry):
    sources, realized = release_geometry
    model = sources.model

    for port in (realized.inlet_port_reservation_solid, realized.outlet_port_reservation_solid):
        assert port.val().intersect(model.water_reservoir_envelope.solid.val()).Volume() <= 1e-7
        assert port.val().intersect(model.shell.solid.val()).Volume() <= 1e-7
        assert port.val().distance(model.water_reservoir_envelope.solid.val()) >= PACKAGE_CLEARANCE_RESERVATION_MM
        assert port.val().distance(model.shell.solid.val()) >= PACKAGE_CLEARANCE_RESERVATION_MM


def test_complete_pump_service_reservation_clears_authority_derived_planar_hard_envelopes(
    release_geometry,
):
    sources, realized = release_geometry
    service = realized.service_clearance_solid.val()
    margins: list[float] = []

    for protected in sources.model.protected_volumes.all:
        # Protected-volume Z depth is intentionally unresolved, so extrude the exact
        # authority-derived XY hard envelope far through the complete pump package.
        prism = _protected_zone_prism(protected.zone)
        assert service.intersect(prism.val()).Volume() <= 1e-7
        margins.append(float(service.distance(prism.val())))

    assert min(margins) > 4.5


def test_complete_pump_service_reservation_clears_every_released_mixed_waste_service_envelope(
    release_geometry,
    released_waste_geometry,
):
    _, realized = release_geometry
    service_solid = realized.service_clearance_solid.val()

    residual_margins: list[float] = []
    for route in released_waste_geometry.routes:
        for primitive in route.centerline:
            centerline_distance = float(service_solid.distance(_primitive_edge(primitive)))
            residual_margin = centerline_distance - route.service_envelope_radius_mm
            residual_margins.append(residual_margin)
            assert residual_margin > 0.0, (
                f"fresh-water pump service reservation consumes released mixed-waste service envelope "
                f"for {route.route_id}: residual={residual_margin:.6f} mm"
            )

    assert min(residual_margins) == pytest.approx(6.3, abs=1e-9)
