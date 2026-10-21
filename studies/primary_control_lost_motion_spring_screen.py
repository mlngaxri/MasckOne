from __future__ import annotations

"""First-order package screen for the tactile-cartridge lost-motion spring.

The spring is not a supplier selection or force validation. The screen answers only
whether a small, always-preloaded compression spring can plausibly absorb the relative
post-snap travel without reaching solid height or adding a large force ramp.

The linear rate uses the standard round-wire compression-spring relation. End effects,
curvature correction, residual stress, manufacturing tolerance, fatigue and dynamics
are intentionally outside this digital screen.
"""

from dataclasses import dataclass
import json
import math

SCHEMA = "MASCK_ONE_PRIMARY_CONTROL_LOST_MOTION_SPRING_SCREEN_V1"

SHEAR_MODULUS_SEED_N_PER_MM2 = 77_000.0
WIRE_DIAMETER_MM = 0.14
MEAN_COIL_DIAMETER_MM = 2.50
ACTIVE_COILS = 3.0
TOTAL_COILS_SEED = 5.0
SPRING_OD_MM = MEAN_COIL_DIAMETER_MM + WIRE_DIAMETER_MM

INSTALLED_REST_LENGTH_MM = 1.54
FREE_LENGTH_SEED_MM = 1.58
RELATIVE_POST_SNAP_TRAVEL_MM = 0.70
MIN_SOLID_CLEARANCE_MM = 0.10
MAX_INCREMENTAL_FORCE_OVER_RELATIVE_TRAVEL_N = 0.10


class LostMotionSpringScreenError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class LostMotionSpringScreen:
    spring_rate_N_per_mm: float
    rest_preload_compression_mm: float
    rest_preload_force_proxy_N: float
    minimum_operating_length_mm: float
    solid_height_mm: float
    solid_height_clearance_mm: float
    incremental_force_over_relative_travel_N: float
    package_viable_for_coupon: bool

    def validate(self) -> "LostMotionSpringScreen":
        values = (
            self.spring_rate_N_per_mm,
            self.rest_preload_compression_mm,
            self.rest_preload_force_proxy_N,
            self.minimum_operating_length_mm,
            self.solid_height_mm,
            self.solid_height_clearance_mm,
            self.incremental_force_over_relative_travel_N,
        )
        if any(not math.isfinite(value) for value in values):
            raise LostMotionSpringScreenError("spring screen requires finite values")
        if self.spring_rate_N_per_mm <= 0.0:
            raise LostMotionSpringScreenError("spring rate must be positive")
        if self.rest_preload_compression_mm <= 0.0:
            raise LostMotionSpringScreenError("spring must remain preloaded at rest")
        if self.solid_height_clearance_mm < MIN_SOLID_CLEARANCE_MM:
            raise LostMotionSpringScreenError("spring reaches solid height too closely at full lost motion")
        if self.incremental_force_over_relative_travel_N > MAX_INCREMENTAL_FORCE_OVER_RELATIVE_TRAVEL_N:
            raise LostMotionSpringScreenError("lost-motion spring adds too much post-snap force in first-order screen")
        if not self.package_viable_for_coupon:
            raise LostMotionSpringScreenError("spring package is not viable for coupon")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": SCHEMA,
            "inputs": {
                "shear_modulus_seed_N_per_mm2": SHEAR_MODULUS_SEED_N_PER_MM2,
                "wire_diameter_mm": WIRE_DIAMETER_MM,
                "mean_coil_diameter_mm": MEAN_COIL_DIAMETER_MM,
                "active_coils": ACTIVE_COILS,
                "total_coils_seed": TOTAL_COILS_SEED,
                "spring_od_mm": SPRING_OD_MM,
                "free_length_seed_mm": FREE_LENGTH_SEED_MM,
                "installed_rest_length_mm": INSTALLED_REST_LENGTH_MM,
                "relative_post_snap_travel_mm": RELATIVE_POST_SNAP_TRAVEL_MM,
            },
            "derived": {
                "spring_rate_N_per_mm": self.spring_rate_N_per_mm,
                "rest_preload_compression_mm": self.rest_preload_compression_mm,
                "rest_preload_force_proxy_N": self.rest_preload_force_proxy_N,
                "minimum_operating_length_mm": self.minimum_operating_length_mm,
                "solid_height_mm": self.solid_height_mm,
                "solid_height_clearance_mm": self.solid_height_clearance_mm,
                "incremental_force_over_relative_travel_N": self.incremental_force_over_relative_travel_N,
                "package_viable_for_coupon": self.package_viable_for_coupon,
            },
            "acoustic_rule": (
                "SPRING_MUST_REMAIN_PRELOADED_AND_POLYMER_ISOLATED; NO_DIRECT_METAL_TO_SHELL_REACTION_PATH; "
                "RING_TWANG_AND_RETURN_NOISE_REQUIRE_PHYSICAL_MEASUREMENT"
            ),
            "physical_validation_eligible": False,
            "physical_validation": (
                "OPEN_SUPPLIER_SPRING_RATE_FORCE_TOLERANCE_BUCKLING_FATIGUE_SET_CORROSION_TEMPERATURE_"
                "DYNAMIC_RING_TWANG_RETURN_SPEED_AND_SUBJECTIVE_FEEL"
            ),
        }


def build_screen() -> LostMotionSpringScreen:
    rate = (
        SHEAR_MODULUS_SEED_N_PER_MM2
        * WIRE_DIAMETER_MM**4
        / (8.0 * MEAN_COIL_DIAMETER_MM**3 * ACTIVE_COILS)
    )
    preload = FREE_LENGTH_SEED_MM - INSTALLED_REST_LENGTH_MM
    minimum_length = INSTALLED_REST_LENGTH_MM - RELATIVE_POST_SNAP_TRAVEL_MM
    solid_height = TOTAL_COILS_SEED * WIRE_DIAMETER_MM
    solid_clearance = minimum_length - solid_height
    incremental_force = rate * RELATIVE_POST_SNAP_TRAVEL_MM
    viable = (
        preload > 0.0
        and solid_clearance >= MIN_SOLID_CLEARANCE_MM
        and incremental_force <= MAX_INCREMENTAL_FORCE_OVER_RELATIVE_TRAVEL_N
    )
    return LostMotionSpringScreen(
        spring_rate_N_per_mm=round(rate, 9),
        rest_preload_compression_mm=round(preload, 9),
        rest_preload_force_proxy_N=round(rate * preload, 9),
        minimum_operating_length_mm=round(minimum_length, 9),
        solid_height_mm=round(solid_height, 9),
        solid_height_clearance_mm=round(solid_clearance, 9),
        incremental_force_over_relative_travel_N=round(incremental_force, 9),
        package_viable_for_coupon=viable,
    ).validate()


if __name__ == "__main__":
    print(json.dumps(build_screen().manifest(), indent=2, sort_keys=True))
