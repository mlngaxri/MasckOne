import pytest

from masck_one.model import build_model
from masck_one.realized_water_reservoir import build_realized_water_reservoir
from masck_one.water_reservoir_closure import build_water_reservoir_closure_geometry
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
    closure = build_water_reservoir_closure_geometry(model.authority, realized, interfaces)
    return model, realized, closure


def test_closed_closure_material_clears_current_released_rigid_packages(screened):
    model, realized, closure = screened
    required_mm = realized.package_clearance_reservation_mm
    for material in (
        closure.closure_body_solid,
        closure.closure_lid_solid,
        closure.retention_key_solid,
    ):
        assert material.val().distance(model.shell.solid.val()) >= required_mm
        for actuator in model.actuator_envelopes:
            assert material.val().distance(actuator.solid.val()) >= required_mm
        assert material.val().distance(model.waste_cartridge_envelope.solid.val()) >= required_mm
        assert material.val().distance(model.battery_reference_envelope.solid.val()) >= required_mm


def test_post_withdrawal_closure_service_sweeps_clear_current_released_rigid_packages(screened):
    model, realized, closure = screened
    required_mm = realized.package_clearance_reservation_mm
    for sweep in (
        closure.module_service_sweep_solid,
        closure.lid_service_sweep_solid,
        closure.key_service_sweep_solid,
    ):
        assert sweep.val().distance(model.shell.solid.val()) >= required_mm
        for actuator in model.actuator_envelopes:
            assert sweep.val().distance(actuator.solid.val()) >= required_mm
        assert sweep.val().distance(model.waste_cartridge_envelope.solid.val()) >= required_mm
        assert sweep.val().distance(model.battery_reference_envelope.solid.val()) >= required_mm


def test_closure_material_and_service_sweeps_are_disjoint_from_current_cell3_latch_reservation(screened):
    _, _, closure = screened
    latch_min, latch_max = CELL3_RIGHT_LATCH_WITHDRAWAL_BOUNDS
    for shape in (
        closure.closure_body_solid,
        closure.closure_lid_solid,
        closure.retention_key_solid,
        closure.module_service_sweep_solid,
        closure.lid_service_sweep_solid,
        closure.key_service_sweep_solid,
    ):
        bb = shape.val().BoundingBox()
        bounds_min = (float(bb.xmin), float(bb.ymin), float(bb.zmin))
        bounds_max = (float(bb.xmax), float(bb.ymax), float(bb.zmax))
        assert _aabb_disjoint(bounds_min, bounds_max, latch_min, latch_max)
        assert bounds_max[0] < latch_min[0]


def test_key_service_sweep_retains_positive_x_margin_to_cell3_latch(screened):
    _, _, closure = screened
    bb = closure.key_service_sweep_solid.val().BoundingBox()
    assert float(bb.xmax) < CELL3_RIGHT_LATCH_WITHDRAWAL_BOUNDS[0][0]
    assert CELL3_RIGHT_LATCH_WITHDRAWAL_BOUNDS[0][0] - float(bb.xmax) > 0.0
