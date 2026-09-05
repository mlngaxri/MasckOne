import cadquery as cq
import pytest

from masck_one.realized_fresh_water_pump import (
    PACKAGE_CLEARANCE_RESERVATION_MM,
    build_current_fresh_pump_sources,
    build_realized_fresh_water_pump,
)
from masck_one.realized_waste_backbone import ArcXY, Line3
from masck_one.realized_waste_backbone_release import build_current_cell4_waste_backbone_release


@pytest.fixture(scope="module")
def release_geometry():
    sources = build_current_fresh_pump_sources()
    return sources, build_realized_fresh_water_pump(sources)


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


def test_complete_pump_service_reservation_clears_every_released_mixed_waste_service_envelope(
    release_geometry,
):
    _, realized = release_geometry
    waste_release = build_current_cell4_waste_backbone_release()
    service_solid = realized.service_clearance_solid.val()

    residual_margins: list[float] = []
    for route in waste_release.realization.routes:
        for primitive in route.centerline:
            centerline_distance = float(service_solid.distance(_primitive_edge(primitive)))
            residual_margin = centerline_distance - route.service_envelope_radius_mm
            residual_margins.append(residual_margin)
            assert residual_margin > 0.0, (
                f"fresh-water pump service reservation consumes released mixed-waste service envelope "
                f"for {route.route_id}: residual={residual_margin:.6f} mm"
            )

    assert min(residual_margins) == pytest.approx(6.3, abs=1e-9)
