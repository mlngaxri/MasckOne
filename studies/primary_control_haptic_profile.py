from __future__ import annotations

"""Architecture-level haptic screen for the Masck One primary control.

The target is not a copied consumer mechanism. It is a measurable force/travel
signature consistent with the MASCK brand authority: low slack, clean force build,
a single crisp transition, progressive soft landing, controlled return and no hard
shell impact in normal travel.

All force values are provisional design references from the brand contract. This
module does not establish measured switch force, acoustics, lifetime, sealing or
subjective feel.
"""

from dataclasses import dataclass
import json
from pathlib import Path

from masck_one.brand_identity import load_brand_identity

SCHEMA = "MASCK_ONE_PRIMARY_CONTROL_HAPTIC_PROFILE_V1"
SOURCE_MAIN_SHA = "42fa11818184cde998c6df25d7c46d4fb0e4c3eb"

REST_PRELOAD_N = 0.22
TRANSITION_END_MM = 0.61
NORMAL_BOTTOM_FORCE_PROXY_N = 1.445
RETURN_HYSTERESIS_PROXY_N = 0.10
FIRST_BUMPER_STIFFNESS_PROXY_N_PER_MM = 2.2
SECOND_BUMPER_STIFFNESS_PROXY_N_PER_MM = 6.5


@dataclass(frozen=True, slots=True)
class HapticProfile:
    peak_force_N: float
    peak_travel_mm: float
    post_transition_force_N: float
    first_landing_start_mm: float
    second_landing_start_mm: float
    nominal_bottom_mm: float
    hard_stop_mm: float

    def force_proxy(self, travel_mm: float) -> float:
        x = max(0.0, float(travel_mm))
        if x <= self.peak_travel_mm:
            # Smooth monotonic pre-travel proxy with zero initial slope.
            s = x / self.peak_travel_mm if self.peak_travel_mm else 0.0
            smooth = 3.0 * s**2 - 2.0 * s**3
            return REST_PRELOAD_N + (self.peak_force_N - REST_PRELOAD_N) * smooth
        if x <= TRANSITION_END_MM:
            u = (x - self.peak_travel_mm) / (TRANSITION_END_MM - self.peak_travel_mm)
            return self.peak_force_N + (self.post_transition_force_N - self.peak_force_N) * u
        force = self.post_transition_force_N
        if x > self.first_landing_start_mm:
            force += FIRST_BUMPER_STIFFNESS_PROXY_N_PER_MM * (x - self.first_landing_start_mm)
        if x > self.second_landing_start_mm:
            force += SECOND_BUMPER_STIFFNESS_PROXY_N_PER_MM * (x - self.second_landing_start_mm)
        return force


def load_profile() -> HapticProfile:
    brand = load_brand_identity()
    ref = brand.data["interaction_signature"]["primary_control"]["candidate_mechanical_reference"]
    return HapticProfile(
        peak_force_N=float(ref["force_peak_N"]),
        peak_travel_mm=float(ref["force_peak_travel_mm"]),
        post_transition_force_N=float(ref["post_transition_force_N"]),
        first_landing_start_mm=float(ref["first_landing_start_mm"]),
        second_landing_start_mm=float(ref["second_landing_start_mm"]),
        nominal_bottom_mm=float(ref["nominal_bottom_travel_mm"]),
        hard_stop_mm=float(ref["hard_stop_travel_mm"]),
    )


def build_manifest() -> dict[str, object]:
    profile = load_profile()
    peak_drop = profile.peak_force_N - profile.post_transition_force_N
    travel_after_bottom = profile.hard_stop_mm - profile.nominal_bottom_mm
    bottom_force = profile.force_proxy(profile.nominal_bottom_mm)
    return {
        "schema": SCHEMA,
        "source_main_sha": SOURCE_MAIN_SHA,
        "profile": {
            "rest_preload_N": REST_PRELOAD_N,
            "peak_force_N": profile.peak_force_N,
            "peak_travel_mm": profile.peak_travel_mm,
            "transition_end_mm": TRANSITION_END_MM,
            "post_transition_force_N": profile.post_transition_force_N,
            "first_landing_start_mm": profile.first_landing_start_mm,
            "second_landing_start_mm": profile.second_landing_start_mm,
            "nominal_bottom_mm": profile.nominal_bottom_mm,
            "hard_stop_mm": profile.hard_stop_mm,
            "normal_bottom_force_proxy_N": bottom_force,
            "return_hysteresis_proxy_N": RETURN_HYSTERESIS_PROXY_N,
        },
        "derived": {
            "force_break_drop_N": peak_drop,
            "force_break_fraction_of_peak": peak_drop / profile.peak_force_N,
            "normal_bottom_to_hard_stop_reserve_mm": travel_after_bottom,
            "stage1_compression_at_nominal_bottom_mm": max(0.0, profile.nominal_bottom_mm - profile.first_landing_start_mm),
            "stage2_compression_at_nominal_bottom_mm": max(0.0, profile.nominal_bottom_mm - profile.second_landing_start_mm),
        },
        "digital_checks": {
            "single_force_break_before_landing": profile.peak_travel_mm < TRANSITION_END_MM < profile.first_landing_start_mm,
            "two_progressive_landing_stages": profile.first_landing_start_mm < profile.second_landing_start_mm < profile.nominal_bottom_mm,
            "hard_stop_not_normal_bottom": travel_after_bottom >= 0.10,
            "force_break_is_perceptible_architecture_proxy": peak_drop >= 0.25,
            "normal_bottom_force_is_finite": 0.0 < bottom_force < 3.0,
        },
        "interpretation": (
            "TARGET SIGNATURE ONLY: CONTROLLED PRETRAVEL -> ONE FORCE BREAK -> DAMPED TWO-STAGE LANDING -> "
            "INDEPENDENT HARD STOP. NO ACOUSTIC OR SUBJECTIVE THOCK CLAIM IS MADE."
        ),
        "physical_validation_eligible": False,
        "physical_validation": (
            "OPEN_NONLINEAR_SPRING_FORCE_HYSTERESIS_BUMPER_RATE_TEMPERATURE_WET_AGING_GUIDE_FRICTION_"
            "BUTTON_WOBBLE_SOUND_PRESSURE_SPECTRUM_RING_DECAY_LIFETIME_AND_SUBJECTIVE_FEEL"
        ),
    }


def write_manifest(path: str | Path) -> dict[str, object]:
    payload = build_manifest()
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    print(json.dumps(build_manifest(), indent=2, sort_keys=True))
