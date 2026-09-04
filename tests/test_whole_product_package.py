import copy

import pytest

from masck_one.authority import load_authority
from masck_one.model import build_model
from masck_one.whole_product_package import (
    Aabb,
    CANONICAL_FRAME_ID,
    KNOWN_PACKAGE_IDS,
    REQUIRED_UNRESOLVED_CLASSES,
    ServiceMotion,
    WholeProductPackageError,
    build_whole_product_package,
    service_motion_blockers,
)


def test_aabb_overlap_gap_and_translation_are_deterministic():
    a = Aabb(0.0, 10.0, 0.0, 10.0, 0.0, 10.0)
    b = Aabb(8.0, 18.0, 2.0, 7.0, 3.0, 9.0)
    assert a.overlap_volume_mm3(b) == pytest.approx(2.0 * 5.0 * 6.0)
    assert a.minimum_axis_gap_mm(b) == 0.0

    c = b.translated(20.0, 0.0, 0.0)
    assert a.overlap_volume_mm3(c) == 0.0
    assert a.minimum_axis_gap_mm(c) == pytest.approx(18.0)


def test_service_motion_samples_include_exact_start_and_end():
    motion = ServiceMotion(
        motion_id="TEST_AXIS_MOTION",
        package_id="WASTE_CARTRIDGE_ENVELOPE",
        axis_xyz=(0, -1, 0),
        travel_mm=60.0,
        steps=12,
        access_status="BLOCKED_TEST",
        trajectory_status="DIGITAL_TEST",
    )
    offsets = motion.sample_offsets_mm()
    assert len(offsets) == 13
    assert offsets[0] == (0.0, 0.0, 0.0)
    assert offsets[-1] == (0.0, -60.0, 0.0)


def test_service_motion_rejects_diagonal_or_noncanonical_axes():
    with pytest.raises(WholeProductPackageError):
        ServiceMotion(
            motion_id="BAD",
            package_id="WASTE_CARTRIDGE_ENVELOPE",
            axis_xyz=(1, 1, 0),
            travel_mm=10.0,
            steps=2,
            access_status="BLOCKED_TEST",
            trajectory_status="DIGITAL_TEST",
        )


def test_whole_product_registry_uses_only_current_model_geometry_and_keeps_unknowns_blocked():
    model = build_model(load_authority())
    package = build_whole_product_package(model)

    assert package.coordinate_frame_id == CANONICAL_FRAME_ID
    assert tuple(item.package_id for item in package.packages) == KNOWN_PACKAGE_IDS
    assert package.unresolved_classes == REQUIRED_UNRESOLVED_CLASSES
    assert package.mass_cg.status == "BLOCKED_INCOMPLETE_CONTROLLED_MASS_LEDGER"
    assert package.mass_cg.dry_total_g is None
    assert package.mass_cg.loaded_total_g is None

    battery = next(item for item in package.packages if item.package_id == "BATTERY_REFERENCE_ENVELOPE")
    assert battery.mass_g == pytest.approx(22.0)
    assert "BENCHMARK" in battery.mass_provenance

    shell = next(item for item in package.packages if item.package_id == "RIGID_SHELL")
    assert shell.mass_g is None
    assert shell.aabb.volume_mm3 > 0.0


def test_mass_cg_known_subset_does_not_masquerade_as_full_product_result():
    package = build_whole_product_package(build_model(load_authority()))
    assert package.mass_cg.known_mass_g == pytest.approx(22.0)
    assert package.mass_cg.known_cg_mm is not None
    assert package.mass_cg.known_pitch_moment_Nm is not None
    assert package.mass_cg.known_pitch_moment_Nm >= 0.0
    assert len(package.mass_cg.unresolved_mass_package_ids) == len(KNOWN_PACKAGE_IDS) - 1
    assert package.mass_cg.unresolved_loaded_mass_terms


def test_collision_ledger_has_every_unique_pair_without_claiming_physical_clearance():
    package = build_whole_product_package(build_model(load_authority()))
    expected_pairs = len(KNOWN_PACKAGE_IDS) * (len(KNOWN_PACKAGE_IDS) - 1) // 2
    assert len(package.collision_records) == expected_pairs
    assert all(
        record.status in {
            "AABB_OVERLAP_REQUIRES_SHAPE_LEVEL_REVIEW",
            "AABB_CLEAR_DIGITAL_BROAD_PHASE_ONLY",
        }
        for record in package.collision_records
    )


def test_service_sweeps_do_not_hide_existing_package_intersections():
    package = build_whole_product_package(build_model(load_authority()))
    for motion in package.service_motions:
        blockers = service_motion_blockers(package, motion.motion_id)
        assert isinstance(blockers, tuple)
        assert motion.package_id not in blockers


def test_manifest_is_stable_and_tampering_changes_hash():
    package = build_whole_product_package(build_model(load_authority()))
    first = package.package_sha256
    second = package.package_sha256
    assert first == second
    assert len(first) == 64

    payload = copy.deepcopy(package.manifest(include_sha=False))
    payload["unresolved_classes"][0] = "TAMPERED"
    import hashlib
    import json

    altered = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    assert altered != first


def test_authority_targets_are_consumed_without_promotion():
    authority = load_authority()
    package = build_whole_product_package(build_model(authority))
    assert package.mass_cg.dry_target_max_g == pytest.approx(
        float(authority.get("mass", "dry_target_max_g"))
    )
    assert package.mass_cg.loaded_absolute_max_g == pytest.approx(
        float(authority.get("mass", "loaded_absolute_max_g"))
    )
    assert package.mass_cg.cg_z_max_mm == pytest.approx(float(authority.get("mass", "cg_z_max_mm")))
    assert package.mass_cg.pitch_torque_max_Nm == pytest.approx(
        float(authority.get("mass", "pitch_torque_max_Nm"))
    )
