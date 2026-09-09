from __future__ import annotations

from studies.treatment_terminal_preload_material_trade import build_manifest


def test_integral_polymer_flexure_is_selected_as_simpler_v1_digital_candidate():
    manifest = build_manifest()
    assert manifest["selected_v1_digital_candidate"] == "INTEGRAL_RELIEVED_ENGINEERED_POLYMER_FLEXURE"
    checks = manifest["digital_screen_checks"]
    assert checks["preload_exceeds_continuous_reference"] is True
    assert checks["polymer_preload_deflection_below_0p20_mm"] is True
    assert checks["polymer_linear_stress_proxy_below_25_MPa"] is True
    assert checks["backup_engages_before_transient_reference"] is True
    assert manifest["physical_validation_eligible"] is False
    assert manifest["physical_validation"].startswith("OPEN_")


def test_polymer_candidate_reduces_part_and_acoustic_paths_without_claiming_material_closure():
    manifest = build_manifest()
    polymer = manifest["integral_polymer_candidate"]
    metal = manifest["spring_metal_candidate"]
    assert "ZERO_EXTRA_SPRING_PARTS" in polymer["advantages"]
    assert "NO_INSERT_ROOT_RATTLE" in polymer["advantages"]
    assert "POTENTIAL_HIGH_Q_RINGING_PATH" in metal["penalties"]
    assert "CREEP_AND_TEMPERATURE_SENSITIVITY_MUST_BE_PROVED" in polymer["penalties"]
