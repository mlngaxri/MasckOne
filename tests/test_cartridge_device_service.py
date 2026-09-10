from __future__ import annotations

from hashlib import sha1
from pathlib import Path

import pytest

from masck_one.cartridge_device_service import (
    BOLT_RETRACTION_MM,
    CAM_CENTERLINE_TOL_MM,
    CAM_FOLLOWER_DIAMETER_MM,
    CAM_RADIAL_CLEARANCE_MM,
    CAM_SLOT_LENGTH_MM,
    CAM_SLOT_WIDTH_MM,
    MAX_CAM_RADIAL_CLEARANCE_MM,
    POPPET_RADIAL_PRELOAD_SEED_MM,
    SCHEMA,
    SHUTTLE_TRAVEL_Y_MM,
    WET_NOSE_RETRACTION_MM,
    CartridgeDeviceServiceError,
    build_cartridge_device_service,
    cam_follower_state,
)
from masck_one.realized_waste_cartridge import volume
import masck_one.waste_cartridge_dfm as released_dfm


RELEASED_DFM_BLOB_SHA = "f9788cce30c14600c8a624509153596e46c1e478"


@pytest.fixture(scope="module")
def service():
    return build_cartridge_device_service()


def test_device_service_selects_one_coordinated_release(service):
    manifest = service.manifest()
    assert manifest["schema"] == SCHEMA
    assert (
        manifest["selected_architecture"]
        == "ONE_GUIDED_SHUTTLE_OPPOSED_BOLTS_FLOATING_WET_NOSE_PASSIVE_POPPET"
    )
    assert manifest["interaction_sequence"] == [
        "BROAD_OBLIQUE_APPROACH",
        "FORGIVING_CAPTURE",
        "SELF_CENTER",
        "LOW_DRAG_GUIDANCE",
        "PROGRESSIVE_LOCAL_TAKEUP",
        "ONE_LOCKED_FINAL_STATE",
    ]
    assert manifest["kinematics"]["shuttle_travel_mm"] == SHUTTLE_TRAVEL_Y_MM
    assert manifest["kinematics"]["bolt_retraction_mm_each"] == BOLT_RETRACTION_MM
    assert manifest["kinematics"]["wet_nose_retraction_mm"] == WET_NOSE_RETRACTION_MM


def test_cam_slots_are_analytically_coupled_over_complete_stroke_with_bounded_play(service):
    manifest = service.manifest()
    cam = manifest["kinematics"]["cam_coupling"]

    assert CAM_SLOT_WIDTH_MM > CAM_FOLLOWER_DIAMETER_MM
    assert 0.0 < CAM_RADIAL_CLEARANCE_MM <= MAX_CAM_RADIAL_CLEARANCE_MM
    assert cam["proof"] == "ANALYTIC_STRAIGHT_SLOT_CENTERLINE_OVER_COMPLETE_NORMALIZED_STROKE"
    assert cam["max_centerline_residual_mm"] <= CAM_CENTERLINE_TOL_MM
    assert cam["max_slot_center_travel_utilization"] < 1.0
    assert manifest["digital_claims"]["cam_follower_centerline_coupling_analytic"] is True
    assert manifest["digital_claims"]["continuous_rigid_collision_proven"] is False

    locked = cam_follower_state(0.0)
    service_state = cam_follower_state(1.0)
    assert (
        service_state["left_bolt"]["follower_world_x_mm"]
        - locked["left_bolt"]["follower_world_x_mm"]
    ) == pytest.approx(-BOLT_RETRACTION_MM)
    assert (
        service_state["right_bolt"]["follower_world_x_mm"]
        - locked["right_bolt"]["follower_world_x_mm"]
    ) == pytest.approx(BOLT_RETRACTION_MM)
    assert (
        service_state["wet_nose"]["follower_world_x_mm"]
        - locked["wet_nose"]["follower_world_x_mm"]
    ) == pytest.approx(-WET_NOSE_RETRACTION_MM)

    for index in range(41):
        for channel in cam_follower_state(index / 40.0).values():
            assert channel["centerline_residual_mm"] <= CAM_CENTERLINE_TOL_MM
            assert (
                abs(channel["along_slot_mm"]) + CAM_FOLLOWER_DIAMETER_MM / 2.0
                <= CAM_SLOT_LENGTH_MM / 2.0
            )


def test_cam_progress_rejects_nonphysical_states():
    for progress in (-0.001, 1.001, float("nan"), True):
        with pytest.raises(CartridgeDeviceServiceError):
            cam_follower_state(progress)


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


def test_cartridge_lane_preserves_released_dfm_authority_blob():
    path = Path(released_dfm.__file__)
    data = path.read_bytes()
    actual = sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
    assert actual == RELEASED_DFM_BLOB_SHA


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
