from masck_one.authority import load_authority
from masck_one.model import build_model
from masck_one.realized_cleanser_storage import (
    PACKAGE_CLEARANCE_RESERVATION_MM,
    build_realized_cleanser_storage,
)


def _distance(a, b) -> float:
    return float(a.val().distance(b.val()))


def test_cleanser_material_package_clears_released_shell_and_other_controlled_packages():
    model = build_model()
    cleanser = build_realized_cleanser_storage(model.authority)

    other_packages = (
        model.shell.solid,
        *tuple(component.solid for component in model.actuator_envelopes),
        model.water_reservoir_envelope.solid,
        model.waste_cartridge_envelope.solid,
        model.battery_reference_envelope.solid,
    )
    for cleanser_material in (
        cleanser.body_solid,
        cleanser.cradle_solid,
        cleanser.retention_key_solid,
    ):
        for package in other_packages:
            assert _distance(cleanser_material, package) >= PACKAGE_CLEARANCE_RESERVATION_MM


def test_cleanser_service_sweeps_clear_released_package_geometry_with_reserved_margin():
    model = build_model()
    cleanser = build_realized_cleanser_storage(model.authority)

    other_packages = (
        model.shell.solid,
        *tuple(component.solid for component in model.actuator_envelopes),
        model.water_reservoir_envelope.solid,
        model.waste_cartridge_envelope.solid,
        model.battery_reference_envelope.solid,
    )
    for service_sweep in (
        cleanser.cassette_service_sweep_solid,
        cleanser.key_service_sweep_solid,
    ):
        for package in other_packages:
            assert _distance(service_sweep, package) >= PACKAGE_CLEARANCE_RESERVATION_MM


def test_cleanser_external_service_reservations_do_not_collapse_into_fresh_water_package():
    model = build_model()
    cleanser = build_realized_cleanser_storage(load_authority())
    fresh_water = model.water_reservoir_envelope.solid

    for reservation in (
        cleanser.refill_closure_reservation_solid,
        cleanser.purge_connector_reservation_solid,
        cleanser.outlet_connector_reservation_solid,
        cleanser.drain_path_reference_solid,
    ):
        assert _distance(reservation, fresh_water) >= PACKAGE_CLEARANCE_RESERVATION_MM
