from masck_one.model import build_model
from masck_one.realized_water_reservoir import build_realized_water_reservoir


# Current Cell 3 candidate interface reservation. This is a candidate-source screen,
# not merged geometry authority or whole-head removal evidence.
CELL3_RIGHT_LATCH_WITHDRAWAL_BOUNDS = (
    (73.5, -5.0, -22.5),
    (100.0, 5.0, -15.5),
)


def _aabb_disjoint(a_min, a_max, b_min, b_max) -> bool:
    return any(a_max[i] < b_min[i] or b_max[i] < a_min[i] for i in range(3))


def test_realized_reservoir_and_removal_sweep_clear_current_released_rigid_packages():
    model = build_model()
    realized = build_realized_water_reservoir(model.authority)
    required_mm = realized.package_clearance_reservation_mm

    for reservoir_shape in (realized.outer_envelope_solid.val(), realized.service_sweep_solid.val()):
        assert reservoir_shape.distance(model.shell.solid.val()) >= required_mm
        for actuator in model.actuator_envelopes:
            assert reservoir_shape.distance(actuator.solid.val()) >= required_mm
        assert reservoir_shape.distance(model.waste_cartridge_envelope.solid.val()) >= required_mm
        assert reservoir_shape.distance(model.battery_reference_envelope.solid.val()) >= required_mm


def test_reservoir_service_sweep_is_broad_phase_disjoint_from_current_cell3_latch_reservation():
    realized = build_realized_water_reservoir(build_model().authority)
    bb = realized.service_sweep_solid.val().BoundingBox()
    service_min = (float(bb.xmin), float(bb.ymin), float(bb.zmin))
    service_max = (float(bb.xmax), float(bb.ymax), float(bb.zmax))
    latch_min, latch_max = CELL3_RIGHT_LATCH_WITHDRAWAL_BOUNDS

    assert _aabb_disjoint(service_min, service_max, latch_min, latch_max)
    assert service_max[0] < latch_min[0]
    assert service_min[1] > latch_max[1]
