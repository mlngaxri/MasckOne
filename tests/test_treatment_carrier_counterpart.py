from __future__ import annotations

from masck_one.treatment_carrier_counterpart import (
    RIGID_END_STOP_GAP_MM,
    SOFT_LANDING_PROBE_MM,
    build_treatment_carrier_counterparts,
)


def test_treatment_carrier_counterparts_realize_four_positive_female_shoes():
    architecture = build_treatment_carrier_counterparts()
    assert len(architecture.counterparts) == 4
    assert architecture.physical_validation_eligible is False
    assert RIGID_END_STOP_GAP_MM > SOFT_LANDING_PROBE_MM

    for item in architecture.counterparts:
        assert item.shoe.val().isValid()
        assert len(item.shoe.val().Solids()) == 1
        assert item.shoe.val().Volume() > 0.0
        assert max(item.nominal_source_intersections_mm3.values()) == 0.0
        assert item.soft_landing_intersections_mm3["landing"] > 0.0
        assert item.soft_landing_intersections_mm3["detent"] > 0.0
        assert item.soft_landing_intersections_mm3["rigid_rail"] == 0.0
        assert item.rigid_stop_intersection_mm3 > 0.0
        assert item.lateral_preload_intersection_mm3 > 0.0
        assert item.lateral_rail_intersection_mm3 == 0.0
        assert min(item.vertical_capture_intersections_mm3) > 0.0


def test_treatment_carrier_manifest_keeps_physical_claims_open():
    manifest = build_treatment_carrier_counterparts().manifest()
    assert manifest["mechanical_status"].endswith("POSTERIOR_SADDLE_AND_WHOLE_CARRIER_SWEEP_OPEN")
    assert manifest["physical_validation_eligible"] is False
    for item in manifest["counterparts"]:
        assert item["continuous_whole_carrier_service_sweep"] == "OPEN"
        assert item["force_friction_stiffness_fatigue_wear_acoustics"] == "PHYSICAL_VALIDATION_OPEN"
