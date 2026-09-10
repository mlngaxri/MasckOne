from __future__ import annotations

"""Conservative over-travel screen for standard metal-dome tactile candidates.

A standard 7 mm F-series dome is attractive for force repeatability and cost, but a
direct rigid plunger is incompatible with Masck One's much longer button stroke. This
screen deliberately uses the dome's *full published height* as an optimistic upper
bound on usable collapse travel. Real travel is smaller, so any over-travel reported
here is a lower bound, not an exaggerated failure.

Vendor values are captured design inputs, not a frozen production BOM. Physical coupon
work remains mandatory before any dome architecture is selected.
"""

from dataclasses import dataclass
import json

from masck_one import primary_control_haptic as haptic

SCHEMA = "MASCK_ONE_PRIMARY_CONTROL_DOME_OVERTRAVEL_SCREEN_V1"
SOURCE_MAIN_SHA = "ac59fcd59f50b019cb972bfc526c2daea784bd17"

BENCHMARK_VENDOR = "Snaptron"
BENCHMARK_PART = "F07110"
BENCHMARK_SOURCE = "https://www.snaptron.com/products/standard-domes/f-series/"
BENCHMARK_CAPTURE_DATE = "2026-09-10"
BENCHMARK_DIAMETER_MM = 7.00
BENCHMARK_HEIGHT_MM = 0.36
BENCHMARK_TRIP_FORCE_GF = 110.0
BENCHMARK_MAX_ACTUATOR_DIAMETER_MM = 1.75

M_SERIES_SOURCE = "https://www.snaptron.com/products/standard-domes/m-series/"
M_SERIES_DESIGNED_OVERTRAVEL_MM = 0.005 * 25.4

# Existing stack places the dome support plane at the old tactile-rim datum. A 0.36 mm
# dome therefore leaves only a 0.01 mm nominal rigid-tip gap at rest.
DOME_SUPPORT_FROM_REST_MM = haptic.TACTILE_RIM_FROM_REST_MM
DIRECT_RIGID_PLUNGER_REST_GAP_MM = (
    haptic.STEM_LENGTH_MM - (DOME_SUPPORT_FROM_REST_MM - BENCHMARK_HEIGHT_MM)
)


class DomeOvertravelScreenError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class DomeOvertravelScreen:
    rest_gap_mm: float
    optimistic_max_dome_travel_mm: float
    lower_bound_extra_travel_to_nominal_bottom_mm: float
    lower_bound_extra_travel_to_hard_stop_mm: float
    m_series_overtravel_allowance_mm: float
    direct_f_series_viable: bool
    direct_m_series_allowance_sufficient: bool
    required_lost_motion_to_nominal_bottom_mm: float
    required_lost_motion_to_hard_stop_mm: float

    def validate(self) -> "DomeOvertravelScreen":
        if not 0.0 <= self.rest_gap_mm <= 0.05:
            raise DomeOvertravelScreenError("benchmark stack should preserve near-zero tactile pre-travel")
        if self.optimistic_max_dome_travel_mm != BENCHMARK_HEIGHT_MM:
            raise DomeOvertravelScreenError("screen must use published height as optimistic travel ceiling")
        if self.lower_bound_extra_travel_to_nominal_bottom_mm <= 0.50:
            raise DomeOvertravelScreenError("expected substantial direct-dome overtravel was not reproduced")
        if self.lower_bound_extra_travel_to_hard_stop_mm <= self.lower_bound_extra_travel_to_nominal_bottom_mm:
            raise DomeOvertravelScreenError("hard stop must demand more lost motion than nominal bottom")
        if self.direct_f_series_viable:
            raise DomeOvertravelScreenError("standard F-series direct rigid actuation cannot be promoted")
        if self.direct_m_series_allowance_sufficient:
            raise DomeOvertravelScreenError("M-series published overtravel is still insufficient for this stroke")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": SCHEMA,
            "source_main_sha": SOURCE_MAIN_SHA,
            "benchmark": {
                "vendor": BENCHMARK_VENDOR,
                "part": BENCHMARK_PART,
                "source": BENCHMARK_SOURCE,
                "capture_date": BENCHMARK_CAPTURE_DATE,
                "diameter_mm": BENCHMARK_DIAMETER_MM,
                "published_height_mm": BENCHMARK_HEIGHT_MM,
                "published_trip_force_gf": BENCHMARK_TRIP_FORCE_GF,
                "max_recommended_actuator_diameter_mm": BENCHMARK_MAX_ACTUATOR_DIAMETER_MM,
            },
            "m_series_reference": {
                "source": M_SERIES_SOURCE,
                "published_designed_overtravel_mm": self.m_series_overtravel_allowance_mm,
            },
            "current_stack": {
                "dome_support_from_rest_mm": DOME_SUPPORT_FROM_REST_MM,
                "direct_rigid_plunger_rest_gap_mm": self.rest_gap_mm,
                "nominal_bottom_mm": haptic.NOMINAL_BOTTOM_MM,
                "hard_stop_mm": haptic.HARD_STOP_MM,
            },
            "conservative_screen": {
                "optimistic_max_dome_travel_mm": self.optimistic_max_dome_travel_mm,
                "lower_bound_extra_travel_to_nominal_bottom_mm": self.lower_bound_extra_travel_to_nominal_bottom_mm,
                "lower_bound_extra_travel_to_hard_stop_mm": self.lower_bound_extra_travel_to_hard_stop_mm,
                "direct_f_series_viable": self.direct_f_series_viable,
                "direct_m_series_allowance_sufficient": self.direct_m_series_allowance_sufficient,
            },
            "required_architecture_change": {
                "lost_motion_or_compliance_to_nominal_bottom_mm_min": self.required_lost_motion_to_nominal_bottom_mm,
                "lost_motion_or_compliance_to_hard_stop_mm_min": self.required_lost_motion_to_hard_stop_mm,
                "direction": (
                    "NO_RIGID_DIRECT_PLUNGER. IF_STANDARD_DOME_IS_RETAINED_USE_A_CENTERED_SUB_1P75_MM_ACTUATOR_WITH_"
                    "DELIBERATE_POST_SNAP_LOST_MOTION_OR_COMPLIANCE_AND_A_VENTED_HARD_SUPPORT_PLANE."
                ),
            },
            "physical_validation_eligible": False,
            "physical_validation": (
                "OPEN_DOME_TRAVEL_RELEASE_FORCE_TACTILE_RATIO_ACTUATOR_COMPLIANCE_DAMPING_VENTING_OFF_AXIS_"
                "LIFE_TEMPERATURE_ACOUSTICS_AND_SUBJECTIVE_FEEL"
            ),
        }


def build_screen() -> DomeOvertravelScreen:
    rest_gap = DIRECT_RIGID_PLUNGER_REST_GAP_MM
    max_travel = BENCHMARK_HEIGHT_MM
    extra_nominal = haptic.NOMINAL_BOTTOM_MM - rest_gap - max_travel
    extra_hard = haptic.HARD_STOP_MM - rest_gap - max_travel
    m_overtravel = M_SERIES_DESIGNED_OVERTRAVEL_MM
    return DomeOvertravelScreen(
        rest_gap_mm=round(rest_gap, 9),
        optimistic_max_dome_travel_mm=max_travel,
        lower_bound_extra_travel_to_nominal_bottom_mm=round(extra_nominal, 9),
        lower_bound_extra_travel_to_hard_stop_mm=round(extra_hard, 9),
        m_series_overtravel_allowance_mm=round(m_overtravel, 9),
        direct_f_series_viable=False,
        direct_m_series_allowance_sufficient=m_overtravel >= extra_nominal,
        required_lost_motion_to_nominal_bottom_mm=round(max(0.0, extra_nominal), 9),
        required_lost_motion_to_hard_stop_mm=round(max(0.0, extra_hard), 9),
    ).validate()


if __name__ == "__main__":
    print(json.dumps(build_screen().manifest(), indent=2, sort_keys=True))
