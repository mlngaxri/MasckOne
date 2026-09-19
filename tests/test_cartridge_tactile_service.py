from __future__ import annotations

from masck_one.cartridge_tactile_service import (
    KEY_PAD_BOTTOM_PRELOAD_SEED_MM,
    KEY_PAD_PRELOAD_SEED_PER_SIDE_MM,
    LEGACY_RADIAL_GUIDE_CLEARANCE_MM,
    MAX_KEY_PRELOAD_SEED_MM,
    MIN_KEY_PRELOAD_SEED_MM,
    NEW_RADIAL_GUIDE_CLEARANCE_MM,
    SCHEMA,
    build_cartridge_tactile_service,
)


def test_tactile_service_reduces_local_bolt_guide_play_without_tight_capture_nose():
    service = build_cartridge_tactile_service()
    manifest = service.manifest()
    bolt = manifest["bolt_guidance"]
    # The service manifest intentionally canonicalizes dimensional reporting to
    # 1e-9 mm. Compare the engineering value at that same deterministic precision
    # instead of requiring binary floating-point identity (1.36 - 1.30 is not
    # exactly representable). This changes no clearance requirement or tolerance.
    expected_guide_clearance_mm = round(NEW_RADIAL_GUIDE_CLEARANCE_MM, 9)

    assert manifest["schema"] == SCHEMA
    assert NEW_RADIAL_GUIDE_CLEARANCE_MM < LEGACY_RADIAL_GUIDE_CLEARANCE_MM
    assert service.guide_radial_clearance_mm == expected_guide_clearance_mm
    assert bolt["legacy_radial_clearance_mm"] == LEGACY_RADIAL_GUIDE_CLEARANCE_MM
    assert bolt["new_radial_clearance_mm"] == expected_guide_clearance_mm
    assert service.capture_pocket_radial_clearance_mm > service.guide_radial_clearance_mm
    assert bolt["debris_relief_count_per_guide"] == 2


def test_refined_bolts_and_guides_are_connected_positive_manufactured_geometry():
    service = build_cartridge_tactile_service()
    for shape in (
        service.left_bolt,
        service.right_bolt,
        service.left_bolt_guide,
        service.right_bolt_guide,
    ):
        solid = shape.val()
        assert solid.isValid()
        assert len(solid.Solids()) == 1
        assert solid.Volume() > 0.0


def test_key_takeup_has_small_free_preload_seed_but_zero_rigid_installed_overlap():
    service = build_cartridge_tactile_service()
    manifest = service.manifest()
    key = manifest["blind_key_takeup"]

    assert MIN_KEY_PRELOAD_SEED_MM <= KEY_PAD_PRELOAD_SEED_PER_SIDE_MM <= MAX_KEY_PRELOAD_SEED_MM
    assert MIN_KEY_PRELOAD_SEED_MM <= KEY_PAD_BOTTOM_PRELOAD_SEED_MM <= MAX_KEY_PRELOAD_SEED_MM
    assert service.pad_root_removed_mm3 > 0.0
    assert service.key_free_interference_mm3 > 0.0
    assert service.key_installed_interference_mm3 == 0.0
    assert key["free_and_installed_geometry_separate"] is True
    assert key["force_validated"] is False


def test_tactile_service_does_not_promote_missing_frame_or_physical_service_evidence():
    service = build_cartridge_tactile_service()
    manifest = service.manifest()

    assert manifest["physical_validation_eligible"] is False
    assert "FRAME_BREP" in " ".join(manifest["known_blockers"])
    assert "FINAL_SEAT" in " ".join(manifest["known_blockers"])
    assert "PRECISION_FEEL_ONLY" in manifest["tactile_reference_rule"]
    assert "SUBJECTIVE_FEEL" in manifest["physical_validation"]