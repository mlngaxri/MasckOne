from __future__ import annotations

import pytest

from masck_one.cartridge_device_service import (
    BOLT_RETRACTION_MM,
    POPPET_RADIAL_PRELOAD_SEED_MM,
    SCHEMA,
    SHUTTLE_TRAVEL_Y_MM,
    WET_NOSE_RETRACTION_MM,
    build_cartridge_device_service,
)
from masck_one.realized_waste_cartridge import volume


@pytest.fixture(scope="module")
def service():
    return build_cartridge_device_service()


def test_device_service_selects_one_coordinated_release(service):
    manifest = service.manifest()
    assert manifest["schema"] == SCHEMA
    assert manifest["selected_architecture"] == "ONE_GUIDED_SHUTTLE_OPPOSED_BOLTS_FLOATING_WET_NOSE_PASSIVE_POPPET"
    assert manifest["interaction_sequence"] == [
        "BROAD_OBLIQUE_APPROACH", "FORGIVING_CAPTURE", "SELF_CENTER",
        "LOW_DRAG_GUIDANCE", "PROGRESSIVE_LOCAL_TAKEUP", "ONE_LOCKED_FINAL_STATE",
    ]
    assert manifest["kinematics"]["shuttle_travel_mm"] == SHUTTLE_TRAVEL_Y_MM
    assert manifest["kinematics"]["bolt_retraction_mm_each"] == BOLT_RETRACTION_MM
    assert manifest["kinematics"]["wet_nose_retraction_mm"] == WET_NOSE_RETRACTION_MM


def test_receiver_and_service_states_are_valid_and_collision_free(service):
    assert service.receiver.val().isValid()
    assert len(service.receiver.val().Solids()) == 1
    for moving, fixed in (
        (service.shuttle_locked, service.receiver),
        (service.shuttle_service, service.receiver),
        (service.left_locked, service.receiver),
        (service.right_locked, service.receiver),
        (service.left_service, service.receiver),
        (service.right_service, service.receiver),
        (service.wet_locked, service.receiver),
        (service.wet_service, service.receiver),
        (service.left_locked, service.shuttle_locked),
        (service.right_locked, service.shuttle_locked),
        (service.wet_locked, service.shuttle_locked),
        (service.left_service, service.shuttle_service),
        (service.right_service, service.shuttle_service),
        (service.wet_service, service.shuttle_service),
    ):
        assert volume(moving.intersect(fixed)) <= 1e-7


def test_removed_state_wet_closure_is_geometry_only(service):
    manifest = service.manifest()
    wet = manifest["wet_interface"]
    assert POPPET_RADIAL_PRELOAD_SEED_MM > 0
    assert wet["removed_state_closure"] == "COMPLIANT_PASSIVE_POPPET_GEOMETRIC_SEED"
    assert wet["wet_nose_retracts_before_cartridge_motion"] is True
    assert wet["leakage_validated"] is False
    assert wet["closing_force_validated"] is False
    assert service.poppet_free.val().isValid()
    assert service.poppet_closed_service.val().isValid()
    assert service.poppet_open_locked.val().isValid()


def test_local_dependencies_close_without_promoting_frame_or_physics(service):
    manifest = service.manifest()
    claims = manifest["digital_claims"]
    assert claims["device_side_key_bolt_capture_realized"] is True
    assert claims["coordinated_wet_disconnect_realized"] is True
    assert claims["removed_state_port_closure_geometry_realized"] is True
    assert claims["local_locked_and_service_states_collision_checked"] is True
    assert claims["released_shell_package_oblique_corridor_clear"] is True
    assert claims["whole_device_frame_installed_path_proven"] is False
    assert manifest["structural_support"]["receiver_one_connected_brep"] is True
    assert manifest["structural_support"]["frame_counterpart_consumed"] is False
    assert manifest["physical_validation_eligible"] is False
