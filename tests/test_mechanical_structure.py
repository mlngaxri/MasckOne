import math

from masck_one.authority import load_authority
from masck_one.mechanical_structure import (
    ACTUATOR_ZONE_CANDIDATES,
    RELEASE_DOG_LENGTH_MM,
    RELEASE_DOG_TRAVEL_MM,
    SCHEMA,
    build_manual_a_mechanical_structure,
)
from masck_one.model import build_model


def _build():
    authority = load_authority()
    model = build_model(authority)
    return authority, model, build_manual_a_mechanical_structure(authority, model)


def _intersection_mm3(first, second):
    value = float(first.val().intersect(second.val()).Volume())
    return 0.0 if value < 1e-8 else value


def test_structure_is_deterministic_and_source_bound():
    authority, model, first = _build()
    _, _, second = _build()
    assert first.manifest()["schema"] == SCHEMA
    assert first.package_sha256 == second.package_sha256
    first.validate_current_sources(authority, model)
    assert len(first.source_model_sha256) == 64


def test_four_independent_zones_preserve_full_authority_angle_doe_and_single_axis_semantics():
    authority, _, structure = _build()
    expected_doe = tuple(float(value) for value in authority.get("actuation", "clean", "axis_angle_doe_deg"))
    assert int(authority.number("actuation", "count")) == 4
    assert len(structure.actuator_zones) == 4
    assert tuple(zone.zone_id for zone in structure.actuator_zones) == tuple(item[0] for item in ACTUATOR_ZONE_CANDIDATES)
    for zone in structure.actuator_zones:
        assert zone.angle_doe_deg == expected_doe
        assert "ONE_LINEAR_AXIS_PER_ZONE" in zone.manifest()["single_axis_semantics"]
        assert zone.envelope.solid.val().isValid()
        assert zone.mount_collar.solid.val().isValid()
        assert zone.reaction_shoe.solid.val().isValid()
        assert _intersection_mm3(zone.reaction_shoe.solid, structure.frame.solid) > 0.0
        assert _intersection_mm3(zone.mount_collar.solid, zone.reaction_shoe.solid) > 0.0


def test_release_uses_real_voids_capture_parts_and_unpowered_hard_travel_not_material_overlap():
    _, _, structure = _build()
    release = structure.release
    assert math.isclose(release.dog_travel_mm, RELEASE_DOG_TRAVEL_MM, rel_tol=0.0, abs_tol=1e-12)
    assert RELEASE_DOG_LENGTH_MM == 18.0
    assert release.dog_final_clears_tongue
    assert release.tongue_clearance_xy_mm[0] > 0.0
    assert release.tongue_clearance_xy_mm[1] > 0.0
    assert release.dog_radial_clearance_mm > 0.0

    assert _intersection_mm3(release.left_frame_clevis.solid, release.left_rear_lug.solid) == 0.0
    assert _intersection_mm3(release.left_pivot_pin.solid, release.left_frame_clevis.solid) == 0.0
    assert _intersection_mm3(release.left_pivot_pin.solid, release.left_rear_lug.solid) == 0.0
    assert _intersection_mm3(release.right_frame_socket.solid, release.right_rear_tongue.solid) == 0.0
    assert _intersection_mm3(release.dog_and_grip.solid, release.right_frame_socket.solid) == 0.0
    assert _intersection_mm3(release.dog_and_grip.solid, release.right_rear_tongue.solid) == 0.0

    manifest = release.manifest()
    assert manifest["power_dependency"] is None
    assert manifest["firmware_dependency"] is None
    assert manifest["release_force_N"] is None
    assert manifest["release_time_s"] is None
    assert "PHYSICAL_GATE" in manifest["release_force_status"]
    assert "PHYSICAL_GATE" in manifest["release_time_status"]


def test_release_dog_full_withdrawal_is_sampled_and_required_clear():
    _, _, structure = _build()
    release_checks = tuple(item for item in structure.clearance_results if item.check_id.startswith("CLEAR_RELEASE_"))
    assert release_checks
    states = {item.state for item in release_checks}
    assert "DOG_X_PLUS_0_MM" in states
    assert f"DOG_X_PLUS_{RELEASE_DOG_TRAVEL_MM:g}_MM" in states
    assert all(item.passes for item in release_checks), tuple(item.check_id for item in release_checks if not item.passes)


def test_full_mechanical_candidate_has_no_required_protected_or_shell_interference():
    _, _, structure = _build()
    assert structure.clearance_results
    assert structure.all_required_clear, structure.conflict_ids
    assert not structure.conflict_ids


def test_mass_and_physical_evidence_firewall_remains_closed():
    _, _, structure = _build()
    manifest = structure.manifest()
    assert manifest["physical_validation_eligible"] is False
    assert structure.unresolved_physical_gates
    assert any("FRAME_MATERIAL" in item for item in structure.unresolved_physical_gates)
    assert any("EMERGENCY_RELEASE_FORCE" in item for item in structure.unresolved_physical_gates)
    assert any("WHOLE_RETENTION_HEADFORM_REMOVAL_SWEEP" in item for item in structure.unresolved_physical_gates)
    assert any("ACTUATOR_FORCE" in item for item in structure.unresolved_physical_gates)
    for part in (structure.frame, structure.halo):
        assert part.manifest()["mass_g"] is None
        assert part.manifest()["mass_status"].startswith("UNRESOLVED_")
