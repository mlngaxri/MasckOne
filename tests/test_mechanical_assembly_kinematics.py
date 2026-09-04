import hashlib
import json

import pytest

from masck_one.authority import load_authority
from masck_one.mechanical_assembly_kinematics import (
    SCHEMA,
    build_mechanical_assembly_kinematics,
)
from masck_one.mechanical_integration import build_mechanical_realization


@pytest.fixture(scope="module")
def assembly():
    return build_mechanical_assembly_kinematics(load_authority())


def test_assembly_kinematics_is_deterministic_and_bound_to_canonical_structure(assembly):
    assert assembly.manifest()["schema"] == SCHEMA
    payload = assembly.manifest(include_sha=False)
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    assert assembly.kinematics_sha256 == digest
    assert len(assembly.realization_sha256) == 64
    assert len(assembly.source_structure_sha256) == 64
    realization = build_mechanical_realization(load_authority())
    assert assembly.realization_sha256 == realization.realization_sha256
    assert assembly.source_structure_sha256 == realization.source_structure_sha256


def test_sequence_is_contiguous_and_every_motion_has_real_world_waypoints(assembly):
    assert tuple(motion.sequence_index for motion in assembly.motions) == tuple(range(1, 9))
    for motion in assembly.motions:
        assert len(motion.waypoints_xyz_mm) >= 4
        assert motion.waypoints_xyz_mm[0] != motion.waypoints_xyz_mm[-1]
        assert motion.waypoints_xyz_mm[-1] == pytest.approx(motion.moving_part.centroid_xyz_mm)


def test_frame_and_actuator_modules_insert_from_wearer_side_without_teleportation(assembly):
    frame = assembly.motions[0]
    assert frame.motion_id == "ASSEMBLE-FRAME-BRIDGE-PACKAGE-FROM-WEARER-SIDE"
    assert frame.waypoints_xyz_mm[0][2] < frame.waypoints_xyz_mm[-1][2]
    assert frame.required_final_contact_ids == ("LIVE-MAIN-RIGID-SHELL",)

    modules = assembly.motions[1:5]
    assert len(modules) == 4
    assert all("ACTUATOR-REACTION-MODULE" in motion.moving_part.part_id for motion in modules)
    assert all(motion.waypoints_xyz_mm[0][2] < motion.waypoints_xyz_mm[-1][2] for motion in modules)
    assert all(
        "FRAME-ASSEMBLY-WITH-BRIDGES-AND-RETENTION-FEATURES" in motion.required_final_contact_ids
        for motion in modules
    )


def test_retention_assembly_uses_clearance_capture_then_pin_and_dog_insertion(assembly):
    halo = assembly.motions[5]
    pivot = assembly.motions[6]
    dog = assembly.motions[7]

    assert halo.motion_id == "ASSEMBLE-HALO-CAPTURE-FEATURES-FROM-POSTERIOR"
    assert halo.required_final_contact_ids == ()
    assert "CAPTURE_VERIFIED_BY_INVARIANTS" in halo.status

    assert pivot.motion_id == "ASSEMBLE-LEFT-CAPTIVE-PIVOT-PIN-THROUGH-ALIGNED-BORES"
    assert pivot.required_final_contact_ids == ()
    assert pivot.waypoints_xyz_mm[0][1] > pivot.waypoints_xyz_mm[-1][1]
    assert "CLEARANCE_BORES" in pivot.status

    assert dog.motion_id == "ASSEMBLE-QUICK-RELEASE-DOG-INBOARD-THROUGH-ALIGNED-BORES"
    assert dog.required_final_contact_ids == ()
    assert dog.waypoints_xyz_mm[0][0] > dog.waypoints_xyz_mm[-1][0]
    assert "CLEARANCE_BORE_ALIGNMENT" in dog.status


def test_candidate_assembly_has_no_prefinal_collision_and_all_material_final_mates_are_valid(assembly):
    failures = [result.manifest() for result in assembly.failures]
    assert not failures, f"Assembly kinematics still contain collisions or invalid final states: {failures}"

    clearance_fit_motions = {
        "ASSEMBLE-HALO-CAPTURE-FEATURES-FROM-POSTERIOR",
        "ASSEMBLE-LEFT-CAPTIVE-PIVOT-PIN-THROUGH-ALIGNED-BORES",
        "ASSEMBLE-QUICK-RELEASE-DOG-INBOARD-THROUGH-ALIGNED-BORES",
    }
    for result in assembly.collision_results:
        if result.motion_id in clearance_fit_motions:
            assert result.required_final_contact is False
            assert result.sample_intersection_mm3[-1] == 0.0


def test_capture_invariants_close_geometry_without_promoting_physical_validation(assembly):
    assert not assembly.capture_failures, [item.manifest() for item in assembly.capture_failures]
    invariants = {item.invariant_id: item for item in assembly.capture_invariants}
    expected = {
        "FRAME-SHELL-BRIDGES-HAVE-POSITIVE-GEOMETRIC-ENGAGEMENT",
        "LEFT-PIVOT-RADIAL-CLEARANCE",
        "RIGHT-DOG-RADIAL-CLEARANCE",
        "RIGHT-TONGUE-CHANNEL-MIN-XY-CLEARANCE",
        "DOG-FULL-WITHDRAWAL-CLEARS-RIGHT-TONGUE",
        "ACCIDENTAL-ACTUATION-GUARD-ATTACHES-TO-RIGHT-SOCKET",
    }
    assert set(invariants) == expected
    assert all(item.passes for item in invariants.values())
    assert invariants["LEFT-PIVOT-RADIAL-CLEARANCE"].value > 0.0
    assert invariants["RIGHT-DOG-RADIAL-CLEARANCE"].value > 0.0
    assert invariants["RIGHT-TONGUE-CHANNEL-MIN-XY-CLEARANCE"].value > 0.0
    assert invariants["DOG-FULL-WITHDRAWAL-CLEARS-RIGHT-TONGUE"].value is True
    assert invariants["ACCIDENTAL-ACTUATION-GUARD-ATTACHES-TO-RIGHT-SOCKET"].value > 0.0
    forbidden_positive_claims = (
        "PHYSICAL_VALIDATION_COMPLETE",
        "PHYSICAL_LOAD_CAPACITY_VALIDATED",
        "RELEASE_FORCE_VALIDATED",
        "RELEASE_TIME_VALIDATED",
    )
    assert all(
        not any(claim in item.evidence_status for claim in forbidden_positive_claims)
        for item in invariants.values()
    )


def test_downstream_lane_owned_assembly_remains_blocked_not_fabricated(assembly):
    assert "FLUID_TUBE_PUMP_MANIFOLD_INSTALLATION_AFTER_CELL4_REALIZED_ROUTE_RELEASE" in assembly.blocked_downstream_steps
    assert "PCB_HARNESS_HMI_WARM_COOL_INSTALLATION_AFTER_MANUAL_B_RELEASE" in assembly.blocked_downstream_steps
    assert "BATTERY_SERVICE_REQUIRES_RETENTION_REMOVED_UNTIL_DRY_BAY_AND_HARNESS_GEOMETRY_RELEASE" in assembly.blocked_downstream_steps
    assert "FINAL_EXTERIOR_CLOSURE_AFTER_ALL_SERVICE_SWEEPS_CLEAR" in assembly.blocked_downstream_steps
    assert "NOT_FASTENER_TOLERANCE_ERGONOMIC_OR_PHYSICAL_ASSEMBLY_VALIDATION" in assembly.evidence_status
