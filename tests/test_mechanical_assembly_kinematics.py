import hashlib
import json

import pytest

from masck_one.authority import load_authority
from masck_one.mechanical_assembly_kinematics import (
    SCHEMA,
    build_mechanical_assembly_kinematics,
)


@pytest.fixture(scope="module")
def assembly():
    return build_mechanical_assembly_kinematics(load_authority())


def test_assembly_kinematics_is_deterministic_and_bound_to_candidate(assembly):
    assert assembly.manifest()["schema"] == SCHEMA
    payload = assembly.manifest(include_sha=False)
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    assert assembly.kinematics_sha256 == digest
    assert len(assembly.realization_sha256) == 64


def test_sequence_is_contiguous_and_every_motion_has_real_world_waypoints(assembly):
    assert tuple(motion.sequence_index for motion in assembly.motions) == tuple(range(1, 10))
    for motion in assembly.motions:
        assert len(motion.waypoints_xyz_mm) >= 4
        assert motion.waypoints_xyz_mm[0] != motion.waypoints_xyz_mm[-1]
        assert motion.waypoints_xyz_mm[-1] == pytest.approx(motion.moving_part.centroid_xyz_mm)


def test_frame_and_actuator_modules_insert_from_wearer_side_without_teleportation(assembly):
    frame = assembly.motions[0]
    assert frame.motion_id == "ASSEMBLE-FRAME-FROM-WEARER-SIDE"
    assert frame.waypoints_xyz_mm[0][2] < frame.waypoints_xyz_mm[-1][2]

    modules = assembly.motions[1:5]
    assert len(modules) == 4
    assert all("ACTUATOR-REACTION-MODULE" in motion.moving_part.part_id for motion in modules)
    assert all(motion.waypoints_xyz_mm[0][2] < motion.waypoints_xyz_mm[-1][2] for motion in modules)
    assert all("FRAME-PERIMETER-REACTION" in motion.required_final_contact_ids for motion in modules)


def test_retention_build_order_uses_yokes_then_halo_then_latch(assembly):
    assert assembly.motions[5].motion_id == "ASSEMBLE-LEFT-YOKE-FROM-WEARER-LEFT"
    assert assembly.motions[6].motion_id == "ASSEMBLE-RIGHT-YOKE-FROM-WEARER-RIGHT"
    assert assembly.motions[7].motion_id == "ASSEMBLE-HALO-FROM-POSTERIOR"
    assert assembly.motions[8].motion_id == "ASSEMBLE-QUICK-RELEASE-LATCH-INBOARD"
    assert set(assembly.motions[7].required_final_contact_ids) == {
        "RETENTION-YOKE-LEFT",
        "RETENTION-YOKE-RIGHT-FIXED",
    }
    assert assembly.motions[8].required_final_contact_ids == ("RETENTION-YOKE-RIGHT-FIXED",)


def test_candidate_assembly_has_no_prefinal_collision_and_all_required_final_mates_exist(assembly):
    failures = [result.manifest() for result in assembly.failures]
    assert not failures, f"Assembly kinematics still contain collisions or missing final engagement: {failures}"


def test_downstream_lane_owned_assembly_remains_blocked_not_fabricated(assembly):
    assert "FLUID_TUBE_PUMP_MANIFOLD_INSTALLATION_AFTER_CELL4_REALIZED_ROUTE_RELEASE" in assembly.blocked_downstream_steps
    assert "PCB_HARNESS_HMI_WARM_COOL_INSTALLATION_AFTER_MANUAL_B_RELEASE" in assembly.blocked_downstream_steps
    assert "FINAL_EXTERIOR_CLOSURE_AFTER_ALL_SERVICE_SWEEPS_CLEAR" in assembly.blocked_downstream_steps
    assert "NOT_FASTENER_TOLERANCE_ERGONOMIC_OR_PHYSICAL_ASSEMBLY_VALIDATION" in assembly.evidence_status
