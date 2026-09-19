from __future__ import annotations

from masck_one import primary_control_haptic as haptic
from studies.primary_control_tactile_architecture_trade import (
    BENCHMARK_DIAMETER_MM,
    BENCHMARK_PART,
    BENCHMARK_VENDOR,
    SCHEMA,
    build_benchmark,
)


def test_standard_dome_benchmark_is_package_and_force_relevant_not_selected_bom():
    benchmark = build_benchmark()
    manifest = benchmark.manifest()

    assert manifest["schema"] == SCHEMA
    assert manifest["standard_dome_benchmark"]["vendor"] == BENCHMARK_VENDOR
    assert manifest["standard_dome_benchmark"]["part"] == BENCHMARK_PART
    assert manifest["standard_dome_benchmark"]["status"].endswith("NOT_PRODUCTION_SELECTION")
    assert benchmark.target_inside_published_force_band is True
    assert benchmark.fits_barrel_bore is True
    assert BENCHMARK_DIAMETER_MM < haptic.BARREL_BORE_DIAMETER_MM


def test_current_full_stem_face_is_rejected_as_standard_dome_actuator():
    benchmark = build_benchmark()

    assert benchmark.current_stem_too_large_as_direct_actuator is True
    assert benchmark.max_recommended_actuator_diameter_mm < haptic.STEM_DIAMETER_MM


def test_standard_dome_trade_keeps_sensor_and_physical_evidence_open():
    manifest = build_benchmark().manifest()

    assert manifest["sensor_trade"]["selected"].startswith("OPEN_")
    assert manifest["physical_validation_eligible"] is False
    assert "FORCE_TRAVEL_HYSTERESIS_AND_RETURN" in manifest["required_physical_evidence"]
    assert "ACOUSTIC_RING_AND_SHELL_COUPLING" in manifest["required_physical_evidence"]
    assert "SENSOR_PATH_INTERFERENCE_OR_ELECTRICAL_SWITCH_RELIABILITY" in manifest["required_physical_evidence"]
