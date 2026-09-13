from __future__ import annotations

from studies.treatment_terminal_preload_material_trade import build_manifest


def test_captured_parallel_spring_is_selected_as_current_v1_digital_candidate():
    manifest = build_manifest()
    assert manifest["selected_v1_digital_candidate"] == "CAPTURED_AXIS_TUNED_PARALLEL_LEAF_SPRING_CASSETTES"
    checks = manifest["digital_screen_checks"]
    assert checks["preload_exceeds_continuous_reference"] is True
    assert checks["x_entry_force_below_0p015_N"] is True
    assert checks["z_entry_force_below_0p015_N"] is True
    assert checks["x_backup_before_transient"] is True
    assert checks["z_backup_before_transient"] is True
    assert checks["one_third_preload_loss_consumes_ideal_margin"] is True
    assert manifest["physical_validation_eligible"] is False
    assert manifest["physical_validation"].startswith("OPEN_")


def test_polymer_is_retained_as_simplification_backup_not_parallel_truth():
    manifest = build_manifest()
    polymer = manifest["integral_polymer_candidate"]
    spring = manifest["captured_parallel_spring_candidate"]
    assert "LOWEST_PART_COUNT" in polymer["advantages"]
    assert "AGED_PRELOAD_RELAXATION_DIRECTLY_CONSUMES_NO_GAP_CONTACT_MARGIN" in polymer["penalties"]
    assert polymer["promotion_gate"].startswith("ONLY_PROMOTE_OVER_SPRING_CASSETTE")
    assert "PARALLEL_LEAVES_LIMIT_SHOE_PITCH_AND_EDGE_LOADING" in spring["advantages"]
    assert "DOG_BONE_ROOT_CAN_BE_GEOMETRICALLY_CAPTURED_WITHOUT_LOOSE_INSERT_PLAY" in spring["advantages"]
    assert "LOSSY_CARRIER_SURROUND_AT_CAPTURE_ROOT_TO_REDUCE_RING_TRANSMISSION" in spring["risk_controls"]


def test_relaxation_sensitivity_fails_closed_before_claiming_buttery_retention():
    manifest = build_manifest()
    sensitivity = manifest["preload_retention_sensitivity"]
    assert sensitivity["ideal_preload_loss_fraction_at_zero_margin"] > 0.33
    assert sensitivity["ideal_preload_loss_fraction_at_zero_margin"] < 0.34
    rows = sensitivity["rows"]
    by_loss = {round(row["preload_loss_fraction"], 6): row for row in rows}
    assert by_loss[0.2]["ideal_contact_margin_positive"] is True
    assert by_loss[0.3]["ideal_contact_margin_positive"] is True
    assert by_loss[0.4]["ideal_contact_margin_positive"] is False
