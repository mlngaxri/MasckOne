import pytest

from masck_one.realized_fresh_water_pump import (
    PACKAGE_CLEARANCE_RESERVATION_MM,
    build_current_fresh_pump_sources,
    build_realized_fresh_water_pump,
)


@pytest.fixture(scope="module")
def release_geometry():
    sources = build_current_fresh_pump_sources()
    return sources, build_realized_fresh_water_pump(sources)


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
