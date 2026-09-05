from masck_one.authority import load_authority
from masck_one.cleanser_service_interfaces import build_cleanser_service_geometry
from masck_one.model import build_model
from masck_one.realized_cleanser_storage import PACKAGE_CLEARANCE_RESERVATION_MM, build_realized_cleanser_storage


def _distance(a, b) -> float:
    return float(a.val().distance(b.val()))


def test_cleanser_service_material_and_motion_clear_released_package_geometry():
    authority = load_authority()
    model = build_model(authority)
    storage = build_realized_cleanser_storage(authority)
    geometry = build_cleanser_service_geometry(authority)

    released_packages = (
        model.shell.solid,
        *(actuator.solid for actuator in model.actuator_envelopes),
        model.water_reservoir_envelope.solid,
        model.waste_cartridge_envelope.solid,
        model.battery_reference_envelope.solid,
    )
    new_material = (
        geometry.ported_body_solid,
        geometry.service_closure_solid,
        geometry.service_retention_key_solid,
    )
    service_motion = (
        geometry.service_closure_sweep_solid,
        geometry.service_key_sweep_solid,
    )

    for shape in (*new_material, *service_motion):
        for package in released_packages:
            assert _distance(shape, package) >= PACKAGE_CLEARANCE_RESERVATION_MM

    # The successor body replaces, rather than coexists with, the source cassette body.
    # It must still remain inside the source cradle and clear the source cassette key.
    assert geometry.ported_body_solid.val().intersect(storage.cradle_solid.val()).Volume() <= 1e-7
    assert geometry.ported_body_solid.val().intersect(storage.retention_key_solid.val()).Volume() <= 1e-7
    assert geometry.service_closure_solid.val().intersect(storage.cradle_solid.val()).Volume() <= 1e-7
    assert geometry.service_retention_key_solid.val().intersect(storage.cradle_solid.val()).Volume() <= 1e-7


def test_nonmaterial_vent_and_seal_service_references_do_not_intrude_into_fresh_water_package():
    authority = load_authority()
    model = build_model(authority)
    geometry = build_cleanser_service_geometry(authority)
    fresh_water = model.water_reservoir_envelope.solid

    for reference in (
        geometry.fill_seal_reference_solid,
        geometry.purge_seal_reference_solid,
        geometry.vent_barrier_reservation_solid,
    ):
        assert _distance(reference, fresh_water) >= PACKAGE_CLEARANCE_RESERVATION_MM
