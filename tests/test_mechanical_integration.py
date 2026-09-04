from masck_one.authority import load_authority
from masck_one.mechanical_integration import (
    ACTUATOR_PLACEMENTS,
    LOWER_SERVICE_CUT_CENTER,
    LOWER_SERVICE_CUT_XYZ_MM,
    SCHEMA,
    build_mechanical_integration,
    intersection_volume_mm3,
)


def _integration():
    authority = load_authority()
    return authority, build_mechanical_integration(authority)


def test_whole_product_integration_builds_deterministically():
    _, first = _integration()
    _, second = _integration()
    assert first.manifest()["schema"] == SCHEMA
    assert first.package_sha256 == second.package_sha256
    assert first.authority_revision == second.authority_revision
    assert len(first.parts) >= 18


def test_owned_actuation_and_reaction_geometry_clear_all_authority_keepouts():
    _, integration = _integration()
    assert integration.collision_checks
    assert all(check.passes for check in integration.collision_checks)
    checked_ids = {check.first_id for check in integration.collision_checks}
    assert {placement[0] for placement in ACTUATOR_PLACEMENTS}.issubset(checked_ids)
    assert {f"REACTION-{placement[0]}" for placement in ACTUATOR_PLACEMENTS}.issubset(checked_ids)


def test_reaction_members_really_intersect_perimeter_frame():
    _, integration = _integration()
    parts = {part.part_id: part for part in integration.parts}
    frame = parts["FRAME-PERIMETER-REACTION"]
    for zone_id, _, _ in ACTUATOR_PLACEMENTS:
        reaction = parts[f"REACTION-{zone_id}"]
        assert intersection_volume_mm3(reaction.solid, frame.solid) > 0.0


def test_retention_chain_is_geometrically_connected_in_closed_state():
    _, integration = _integration()
    parts = {part.part_id: part for part in integration.parts}
    frame = parts["FRAME-PERIMETER-REACTION"]
    halo = parts["RETENTION-HALO-OCCIPITAL-CROWN"]
    left = parts["RETENTION-YOKE-LEFT"]
    right = parts["RETENTION-YOKE-RIGHT-FIXED"]
    latch = parts["QUICK-RELEASE-LATCH-MOVING"]
    assert intersection_volume_mm3(left.solid, frame.solid) > 0.0
    assert intersection_volume_mm3(left.solid, halo.solid) > 0.0
    assert intersection_volume_mm3(right.solid, frame.solid) > 0.0
    assert intersection_volume_mm3(right.solid, halo.solid) > 0.0
    assert intersection_volume_mm3(latch.solid, right.solid) > 0.0


def test_cartridge_uses_real_service_motion_not_teleportation():
    _, integration = _integration()
    motions = {motion.motion_id: motion for motion in integration.service_motions}
    motion = motions["SERVICE-WASTE-CARTRIDGE-DOWNWARD"]
    assert len(motion.waypoints_xyz_mm) == 4
    assert all(
        motion.waypoints_xyz_mm[index + 1][1] < motion.waypoints_xyz_mm[index][1]
        for index in range(len(motion.waypoints_xyz_mm) - 1)
    )
    parts = {part.part_id: part for part in integration.parts}
    obstacles = (
        parts["EXTERIOR-SHELL-MECHANICAL-SERVICE-STATE"],
        parts["FRAME-PERIMETER-REACTION"],
        parts["RETENTION-HALO-OCCIPITAL-CROWN"],
        parts["RETENTION-YOKE-LEFT"],
        parts["RETENTION-YOKE-RIGHT-FIXED"],
    )
    assert all(
        volume == 0.0
        for volumes in motion.collision_volumes(obstacles).values()
        for volume in volumes
    )


def test_lower_service_cut_is_bounded_and_not_promoted_to_final_exterior():
    _, integration = _integration()
    assert LOWER_SERVICE_CUT_XYZ_MM == (82.0, 45.0, 28.0)
    assert LOWER_SERVICE_CUT_CENTER == (0.0, -102.0, 7.0)
    parts = {part.part_id: part for part in integration.parts}
    assert "REQUIRES_EXTERIOR_CONVERGENCE" in parts["EXTERIOR-SHELL-MECHANICAL-SERVICE-STATE"].geometry_status
    assert "UNRESOLVED" in parts["LOWER-SERVICE-DOOR-ENVELOPE"].evidence_status


def test_quick_release_withdrawal_is_unpowered_geometry_only():
    authority, integration = _integration()
    motions = {motion.motion_id: motion for motion in integration.service_motions}
    motion = motions["SERVICE-QUICK-RELEASE-OUTBOARD"]
    assert motion.waypoints_xyz_mm[-1][0] > motion.waypoints_xyz_mm[0][0]
    assert "UNPOWERED" in motion.evidence_status
    assert "UNVALIDATED" in motion.evidence_status
    assert authority.get("safety", "quick_release", "time_status") == "FROZEN_SAFETY_REQUIREMENT"
    assert authority.get("safety", "quick_release", "force_status") == "VALIDATION_GATED"


def test_external_lane_unknowns_fail_closed_instead_of_getting_fake_geometry():
    _, integration = _integration()
    unresolved = {item.reservation_id: item for item in integration.unresolved}
    required = {
        "FRESH-FLUID-63-SEGMENT-REALIZED-ROUTES",
        "CLEANSER-STORAGE-REALIZED-GEOMETRY",
        "PCB-DRY-BAY-AND-HARNESS-GEOMETRY",
        "HMI-STACK-AND-SEAL-GEOMETRY",
        "BATTERY-SWELLING-ALLOWANCE",
        "WARM-COOL-THERMAL-HARDWARE",
        "WASTE-BACKFLOW-AND-TUBE-REALIZED-GEOMETRY",
    }
    assert required == set(unresolved)
    assert all(item.required_for for item in unresolved.values())


def test_mass_cg_and_pitch_ledger_never_promotes_partial_mass_to_whole_product_pass():
    authority, integration = _integration()
    mass = integration.mass_manifest(authority)
    assert mass["known_dry_mass_g"] == authority.get("battery_reference", "mass_g")
    assert mass["complete_dry_mass_g"] is None
    assert mass["loaded_mass_g"] is None
    assert mass["whole_product_cg_xyz_mm"] is None
    assert mass["whole_product_pitch_moment_Nm"] is None
    assert mass["gate_status"].startswith("BLOCKED_")
    assert mass["comparison_semantics"] == "KNOWN_PARTIAL_MASS_MUST_NOT_BE_COMPARED_AS_WHOLE_PRODUCT_PASS"


def test_assembly_sequence_requires_dependencies_before_final_shell_closure():
    _, integration = _integration()
    assert integration.assembly_sequence[-1].startswith("9 perform final shell closure only after")
    assert "fluidics" in integration.assembly_sequence[-2]
    assert "PCB/HMI" in integration.assembly_sequence[-2]
