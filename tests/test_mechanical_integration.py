from masck_one.authority import load_authority
from masck_one.mechanical_integration import (
    ACTUATOR_PLACEMENTS,
    CLOSED_BASELINE_BLOCKERS,
    REMAINING_BLOCKERS,
    SCHEMA,
    build_mechanical_realization,
    intersection_volume_mm3,
)
from masck_one.mechanical_structure import build_manual_a_mechanical_structure
from masck_one.model import build_model


def _build():
    authority = load_authority()
    return authority, build_mechanical_realization(authority)


def test_realization_is_deterministic_bound_to_live_main_and_single_structure_source():
    authority, first = _build()
    _, second = _build()
    model = build_model(authority)
    structure = build_manual_a_mechanical_structure(authority, model)
    assert first.manifest()["schema"] == SCHEMA
    assert first.realization_sha256 == second.realization_sha256
    assert first.baseline_package.package_sha256 == second.baseline_package.package_sha256
    assert first.source_structure_sha256 == structure.package_sha256
    assert first.manifest()["source_structure_sha256"] == structure.package_sha256


def test_manual_a_closes_only_owned_geometry_classes_and_preserves_physical_gates():
    _, realization = _build()
    assert realization.closed_baseline_blockers == CLOSED_BASELINE_BLOCKERS
    assert realization.remaining_blockers == REMAINING_BLOCKERS
    assert "STRUCTURAL_FRAME_3D_MEMBERS" not in realization.remaining_blockers
    assert "RETENTION_AND_EMERGENCY_RELEASE" not in realization.remaining_blockers
    assert "FRESH_FLUID_REALIZED_CENTERLINES" in realization.remaining_blockers
    assert "PCB_DRY_BAY_AND_HARNESS" in realization.remaining_blockers
    assert realization.unresolved_physical_gates
    assert any("EMERGENCY_RELEASE_FORCE" in gate for gate in realization.unresolved_physical_gates)
    assert "NOT_PHYSICAL_CAPACITY_OR_VALIDATION" in realization.manifest()["closed_baseline_blocker_semantics"]


def test_projected_actuation_uses_canonical_structure_clearance_results():
    authority, realization = _build()
    structure = build_manual_a_mechanical_structure(authority, build_model(authority))
    assert realization.shape_checks
    assert all(check.passes for check in realization.shape_checks)
    assert len(realization.shape_checks) == len(structure.clearance_results)
    assert tuple(check.check_id for check in realization.shape_checks) == tuple(
        check.check_id for check in structure.clearance_results
    )
    assert tuple(zone_id for zone_id, _, _ in ACTUATOR_PLACEMENTS) == (
        "ACTUATOR-ZONE-A",
        "ACTUATOR-ZONE-B",
        "ACTUATOR-ZONE-C",
        "ACTUATOR-ZONE-D",
    )


def test_projected_reaction_members_have_positive_shape_intersection_with_frame():
    _, realization = _build()
    parts = {part.part_id: part for part in realization.realized_parts}
    frame = parts["FRAME-PERIMETER-REACTION"]
    for zone_id, _, _ in ACTUATOR_PLACEMENTS:
        reaction = parts[f"REACTION-{zone_id}"]
        assert intersection_volume_mm3(reaction.solid, frame.solid) > 0.0


def test_retention_projection_preserves_real_capture_void_semantics_not_overlap_proxy():
    authority, realization = _build()
    parts = {part.part_id: part for part in realization.realized_parts}
    structure = build_manual_a_mechanical_structure(authority, build_model(authority))
    frame = parts["FRAME-PERIMETER-REACTION"]
    halo = parts["RETENTION-HALO-OCCIPITAL-CROWN"]
    left = parts["RETENTION-YOKE-LEFT"]
    right = parts["RETENTION-YOKE-RIGHT-FIXED"]
    latch = parts["QUICK-RELEASE-LATCH-MOVING"]
    guard = parts["QUICK-RELEASE-GUARD"]

    assert intersection_volume_mm3(left.solid, frame.solid) > 0.0
    assert intersection_volume_mm3(left.solid, halo.solid) > 0.0
    assert intersection_volume_mm3(right.solid, frame.solid) > 0.0
    assert intersection_volume_mm3(right.solid, halo.solid) > 0.0
    assert intersection_volume_mm3(latch.solid, right.solid) == 0.0
    assert intersection_volume_mm3(latch.solid, guard.solid) == 0.0
    assert structure.release.dog_final_clears_tongue
    assert structure.release.dog_radial_clearance_mm > 0.0
    assert structure.release.tongue_clearance_xy_mm[0] > 0.0
    assert structure.release.tongue_clearance_xy_mm[1] > 0.0


def test_service_motions_use_world_coordinate_samples_and_are_collision_clear():
    _, realization = _build()
    parts = {part.part_id: part for part in realization.realized_parts}
    sweeps = {sweep.sweep_id: sweep for sweep in realization.service_sweeps}

    cartridge = sweeps["CARTRIDGE-DOWNWARD-REMOVAL"]
    assert all(
        cartridge.waypoints_xyz_mm[i + 1][1] < cartridge.waypoints_xyz_mm[i][1]
        for i in range(len(cartridge.waypoints_xyz_mm) - 1)
    )
    cartridge_obstacles = (
        parts["SERVICE-STATE-SHELL"],
        parts["FRAME-PERIMETER-REACTION"],
        parts["RETENTION-HALO-OCCIPITAL-CROWN"],
        parts["RETENTION-YOKE-LEFT"],
        parts["RETENTION-YOKE-RIGHT-FIXED"],
        parts["QUICK-RELEASE-GUARD"],
    )
    assert all(
        value == 0.0
        for values in cartridge.collision_volumes(cartridge_obstacles).values()
        for value in values
    )

    release = sweeps["QUICK-RELEASE-OUTBOARD-WITHDRAWAL"]
    assert release.waypoints_xyz_mm[-1][0] > release.waypoints_xyz_mm[0][0]
    assert "UNPOWERED" in release.status
    assert "PHYSICAL_VALIDATION" in release.status

    battery = sweeps["BATTERY-BENCHMARK-REARWARD-REMOVAL"]
    assert "REQUIRES_RETENTION_REMOVED" in battery.status


def test_service_cut_is_explicit_handoff_not_fake_exterior_closure():
    _, realization = _build()
    parts = {part.part_id: part for part in realization.realized_parts}
    service_shell = parts["SERVICE-STATE-SHELL"]
    door = parts["LOWER-SERVICE-DOOR-ENVELOPE"]
    assert "HANDOFF_REQUIRES_MANUAL_B" in service_shell.evidence_status
    assert "SEAL_LATCH_TOLERANCE_INGRESS_AND_CMF_UNRESOLVED" in door.evidence_status
    assert "SEALS_DOORS_LATCHES" in realization.remaining_blockers


def test_mass_cg_pitch_stays_fail_closed_in_integration_projection():
    authority, realization = _build()
    mass = realization.mass_cg_manifest(authority)
    assert mass["known_mass_g"] == authority.get("battery_reference", "mass_g")
    assert mass["dry_total_g"] is None
    assert mass["loaded_total_g"] is None
    assert mass["whole_product_cg_mm"] is None
    assert mass["whole_product_pitch_moment_Nm"] is None
    assert mass["status"].startswith("BLOCKED_")
    assert "CANNOT_ESTABLISH_WHOLE_PRODUCT_PASS" in mass["comparison_semantics"]
    assert "MECHANICAL_MASS_CG_LEDGER" in mass["comparison_semantics"]


def test_final_assembly_closure_is_dependency_ordered_not_teleportation():
    _, realization = _build()
    assert realization.assembly_sequence[0].startswith("1 establish")
    assert "perimeter reaction frame" in realization.assembly_sequence[1]
    assert "insert cartridge" in realization.assembly_sequence[5]
    assert "remove retention assembly" in realization.assembly_sequence[6]
    assert "fluid routes" in realization.assembly_sequence[7]
    assert realization.assembly_sequence[-1].startswith(
        "9 close final shell/service surfaces only after"
    )
