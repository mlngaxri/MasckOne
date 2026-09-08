from __future__ import annotations

from studies.treatment_datum_preload_mount import (
    BACKUP_TRAVEL_SEED_MM,
    CONTINUOUS_REACTION_REFERENCE_N,
    NORMAL_PRELOAD_TARGET_N,
    TRANSIENT_REACTION_REFERENCE_N,
    build_manifest,
    load_path_screen,
    spring_leaf_screen,
)


def test_preload_seed_keeps_normal_reaction_closed_against_master_datum():
    screen = load_path_screen()
    assert NORMAL_PRELOAD_TARGET_N > CONTINUOUS_REACTION_REFERENCE_N
    assert screen["continuous_contact_margin_N"] > 0.0
    assert screen["continuous_reaction_keeps_master_datum_closed"] is True


def test_close_backup_intervenes_before_leaf_is_asked_to_carry_transient_reference():
    spring = spring_leaf_screen()
    assert BACKUP_TRAVEL_SEED_MM == 0.04
    assert spring["force_when_backup_first_engages_N"] > NORMAL_PRELOAD_TARGET_N
    assert spring["force_when_backup_first_engages_N"] < TRANSIENT_REACTION_REFERENCE_N
    assert load_path_screen()["backup_engages_before_leaf_would_carry_full_transient"] is True


def test_spring_screen_is_finite_positive_and_remains_an_analysis_proxy():
    spring = spring_leaf_screen()
    for key, value in spring.items():
        assert value > 0.0, key
    # At this seed the preload deflection is deliberately below a quarter millimetre;
    # exact nonlinear strain/fatigue still remains open in the manifest.
    assert spring["preload_deflection_seed_mm"] < 0.25


def test_manifest_separates_buttery_functions_from_working_reaction():
    manifest = build_manifest()
    assert manifest["physical_validation_eligible"] is False
    assert "DETERMINISTIC_DATUMING" in manifest["reason_for_superseding_four_face_taper_as_baseline"]
    roles = manifest["mechanical_separation_of_functions"]
    assert roles["rail"].endswith("ONLY")
    assert "NORMAL_WORKING_REACTION" in roles["master_datums"]
    assert "TAKE_UP_CLEARANCE" in roles["preload_shoes"]
    assert "WITHOUT_SHARP_CLACK" in roles["lossy_backups"]
    assert "NOT_LATERAL_40HZ_REACTION" in roles["axial_detent"]
    assert manifest["physical_validation"].startswith("OPEN_")
