import pytest

from masck_one.model import build_model
from masck_one.realized_water_reservoir import build_realized_water_reservoir
from masck_one.water_reservoir_interfaces import build_water_reservoir_interface_geometry


CELL3_RIGHT_LATCH_WITHDRAWAL_BOUNDS = (
    (73.5, -5.0, -22.5),
    (100.0, 5.0, -15.5),
)


def _aabb_disjoint(a_min, a_max, b_min, b_max) -> bool:
    return any(a_max[index] < b_min[index] or b_max[index] < a_min[index] for index in range(3))


@pytest.fixture(scope="module")
def screened():
    model = build_model()
    realized = build_realized_water_reservoir(model.authority)
    interfaces = build_water_reservoir_interface_geometry(model.authority, realized)
    return model, realized, interfaces


def test_external_water_service_reservations_clear_current_released_rigid_packages(screened):
    model, realized, interfaces = screened
    required_mm = realized.package_clearance_reservation_mm
    reservations = (
        interfaces.fill_closure_reservation_solid,
        interfaces.vent_external_barrier_reservation_solid,
        interfaces.pickup_connector_reservation_solid,
    )

    for reservation in reservations:
        assert reservation.val().distance(model.shell.solid.val()) >= required_mm
        for actuator in model.actuator_envelopes:
            assert reservation.val().distance(actuator.solid.val()) >= required_mm
        assert reservation.val().distance(model.waste_cartridge_envelope.solid.val()) >= required_mm
        assert reservation.val().distance(model.battery_reference_envelope.solid.val()) >= required_mm


def test_external_water_service_reservations_are_disjoint_from_current_cell3_latch_sweep(screened):
    _, _, interfaces = screened
    latch_min, latch_max = CELL3_RIGHT_LATCH_WITHDRAWAL_BOUNDS
    for reservation in (
        interfaces.fill_closure_reservation_solid,
        interfaces.vent_external_barrier_reservation_solid,
        interfaces.pickup_connector_reservation_solid,
    ):
        bb = reservation.val().BoundingBox()
        service_min = (float(bb.xmin), float(bb.ymin), float(bb.zmin))
        service_max = (float(bb.xmax), float(bb.ymax), float(bb.zmax))
        assert _aabb_disjoint(service_min, service_max, latch_min, latch_max)
        assert service_max[0] < latch_min[0]


def test_fill_reservation_keeps_positive_margin_beyond_current_package_clearance(screened):
    model, realized, interfaces = screened
    distance_mm = interfaces.fill_closure_reservation_solid.val().distance(model.shell.solid.val())
    assert distance_mm >= realized.package_clearance_reservation_mm
    assert distance_mm - realized.package_clearance_reservation_mm > 0.0
