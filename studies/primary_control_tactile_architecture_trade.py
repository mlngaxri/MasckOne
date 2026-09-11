from __future__ import annotations

"""Architecture trade for the primary-control tactile generator.

The current custom four-short-beam spring fails the order-of-magnitude geometry screen.
This study does not silently replace it with another unvalidated custom spring. Instead,
it records a current commercially standard stamped-dome benchmark whose published
size, force and life are close enough to justify physical coupons.

Vendor data are design inputs only and must be verified against a current controlled
datasheet / drawing before release. No supplier part is selected for production here.
"""

from dataclasses import dataclass, asdict
import json
from pathlib import Path

from masck_one import primary_control_haptic as haptic
from masck_one.brand_identity import load_brand_identity
from studies.primary_control_spring_geometry_screen import build_screen

SCHEMA = "MASCK_ONE_PRIMARY_CONTROL_TACTILE_ARCHITECTURE_TRADE_V1"
SOURCE_MAIN_SHA = "ac59fcd59f50b019cb972bfc526c2daea784bd17"
STANDARD_GRAVITY_M_PER_S2 = 9.80665

# Current public benchmark captured 2026-09-10. This is not a frozen production BOM.
BENCHMARK_VENDOR = "Snaptron"
BENCHMARK_PART = "F07110"
BENCHMARK_SOURCE = "https://www.snaptron.com/products/standard-domes/f-series/"
BENCHMARK_CAPTURE_DATE = "2026-09-10"
BENCHMARK_DIAMETER_MM = 7.00
BENCHMARK_HEIGHT_MM = 0.36
BENCHMARK_CAVITY_MM = 6.35
BENCHMARK_TRIP_FORCE_GF = 110.0
BENCHMARK_TRIP_FORCE_TOLERANCE_GF = 30.0
BENCHMARK_PUBLISHED_LIFE_CYCLES = 5_000_000
BENCHMARK_MAX_RECOMMENDED_ACTUATOR_FRACTION = 0.25


@dataclass(frozen=True, slots=True)
class StandardDomeBenchmark:
    nominal_trip_force_N: float
    low_trip_force_N: float
    high_trip_force_N: float
    target_peak_force_N: float
    target_inside_published_force_band: bool
    fits_barrel_bore: bool
    max_recommended_actuator_diameter_mm: float
    current_stem_too_large_as_direct_actuator: bool
    published_life_cycles: int

    def manifest(self) -> dict[str, object]:
        spring_screen = build_screen()
        return {
            "schema": SCHEMA,
            "source_main_sha": SOURCE_MAIN_SHA,
            "rejected_custom_geometry": {
                "architecture": "CURRENT_FOUR_SHORT_BEAM_FORMED_SPRING",
                "reason": "FAILS_COMPLIANCE_FAVOURING_ORDER_OF_MAGNITUDE_STIFFNESS_SCREEN",
                "proxy_to_target_ratio": spring_screen.proxy_to_target_ratio,
            },
            "standard_dome_benchmark": {
                "vendor": BENCHMARK_VENDOR,
                "part": BENCHMARK_PART,
                "source": BENCHMARK_SOURCE,
                "capture_date": BENCHMARK_CAPTURE_DATE,
                "published_inputs": {
                    "diameter_mm": BENCHMARK_DIAMETER_MM,
                    "height_mm": BENCHMARK_HEIGHT_MM,
                    "recommended_cavity_mm": BENCHMARK_CAVITY_MM,
                    "trip_force_gf": BENCHMARK_TRIP_FORCE_GF,
                    "trip_force_tolerance_gf": BENCHMARK_TRIP_FORCE_TOLERANCE_GF,
                    "life_cycles_up_to": BENCHMARK_PUBLISHED_LIFE_CYCLES,
                },
                "derived": asdict(self),
                "status": "BENCHMARK_FOR_COUPON_AND_PACKAGE_STUDY_NOT_PRODUCTION_SELECTION",
            },
            "architecture_direction": (
                "PREFER_STANDARD_STAMPED_TACTILE_ELEMENT_OVER_CUSTOM_SHORT_BEAM_SPRING_IF_COUPON_CONFIRMS_FEEL; "
                "USE_SMALL_CENTERED_NONCONDUCTIVE_ACTUATOR_AND_LOSSY_OVERLAY_OR_CONSTRAINED_LAYER_TO_CONTROL_SOUND; "
                "DO_NOT_USE_THE_FULL_7_18_MM_STEM_FACE_AS_DOME_ACTUATOR"
            ),
            "sensor_trade": {
                "option_a": "KEEP_CONTACTLESS_HALL_SENSING_AND_RELOCATE_OR_SHIELD_MAGNETIC_PATH_FROM_METAL_DOME",
                "option_b": "USE_DOME_ELECTRICALLY_AS_THE_SWITCH_AND_DELETE_HALL_MAGNET_IF_DRY_SIDE_RELIABILITY_WINS",
                "selected": "OPEN_UNTIL_PACKAGE_COST_WET_RELIABILITY_AND_FEEL_COUPON",
            },
            "required_physical_evidence": [
                "FORCE_TRAVEL_HYSTERESIS_AND_RETURN",
                "TACTILE_RATIO_AND_SUBJECTIVE_FEEL",
                "ACTUATOR_GEOMETRY_SENSITIVITY",
                "ACOUSTIC_RING_AND_SHELL_COUPLING",
                "DAMPING_OVERLAY_EFFECT",
                "OFF_AXIS_AND_CONTAMINATION_ROBUSTNESS",
                "LIFE_AND_TEMPERATURE",
                "SENSOR_PATH_INTERFERENCE_OR_ELECTRICAL_SWITCH_RELIABILITY",
            ],
            "physical_validation_eligible": False,
        }


def build_benchmark() -> StandardDomeBenchmark:
    brand = load_brand_identity()
    target = brand.data["interaction_signature"]["primary_control"]["candidate_mechanical_reference"]
    target_peak = float(target["force_peak_N"])

    newtons_per_gf = STANDARD_GRAVITY_M_PER_S2 / 1000.0
    nominal = BENCHMARK_TRIP_FORCE_GF * newtons_per_gf
    low = (BENCHMARK_TRIP_FORCE_GF - BENCHMARK_TRIP_FORCE_TOLERANCE_GF) * newtons_per_gf
    high = (BENCHMARK_TRIP_FORCE_GF + BENCHMARK_TRIP_FORCE_TOLERANCE_GF) * newtons_per_gf
    max_actuator = BENCHMARK_DIAMETER_MM * BENCHMARK_MAX_RECOMMENDED_ACTUATOR_FRACTION

    return StandardDomeBenchmark(
        nominal_trip_force_N=nominal,
        low_trip_force_N=low,
        high_trip_force_N=high,
        target_peak_force_N=target_peak,
        target_inside_published_force_band=low <= target_peak <= high,
        fits_barrel_bore=BENCHMARK_DIAMETER_MM < haptic.BARREL_BORE_DIAMETER_MM,
        max_recommended_actuator_diameter_mm=max_actuator,
        current_stem_too_large_as_direct_actuator=haptic.STEM_DIAMETER_MM > max_actuator,
        published_life_cycles=BENCHMARK_PUBLISHED_LIFE_CYCLES,
    )


def write_manifest(path: str | Path) -> dict[str, object]:
    payload = build_benchmark().manifest()
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    print(json.dumps(build_benchmark().manifest(), indent=2, sort_keys=True))
