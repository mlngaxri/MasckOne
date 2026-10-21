from __future__ import annotations

"""Conservative geometry screen for the current primary-control tactile spring.

This is intentionally NOT a nonlinear snap-through simulation. It asks a narrower
question: is the current short-beam geometry even in the same stiffness order as the
provisional force/travel target before relying on geometric instability to save it?

The screen treats each formed beam as a fixed-free bending beam, which is a deliberately
compliance-favouring simplification relative to a beam joined at both ends. It also uses
110 GPa, below common stainless spring-metal moduli. Passing this screen would not prove
a tactile curve. Failing it prevents the repo from claiming that the target curve is
geometry-derived.
"""

from dataclasses import dataclass, asdict
import json
import math
from pathlib import Path

from masck_one import primary_control_haptic as haptic
from masck_one.brand_identity import load_brand_identity

SCHEMA = "MASCK_ONE_PRIMARY_CONTROL_SPRING_GEOMETRY_SCREEN_V1"
SOURCE_MAIN_SHA = "ac59fcd59f50b019cb972bfc526c2daea784bd17"
CONSERVATIVE_ELASTIC_MODULUS_N_PER_MM2 = 110_000.0
BEAM_COUNT = 4
MAX_CREDIBLE_PROXY_TO_TARGET_RATIO = 20.0


@dataclass(frozen=True, slots=True)
class SpringGeometryScreen:
    beam_length_mm: float
    beam_width_mm: float
    beam_thickness_mm: float
    second_moment_mm4: float
    one_beam_bending_stiffness_N_per_mm: float
    four_beam_bending_stiffness_N_per_mm: float
    target_average_rise_stiffness_N_per_mm: float
    proxy_to_target_ratio: float
    equivalent_thickness_at_current_length_mm: float
    equivalent_length_at_current_thickness_mm: float
    geometry_force_credibility_pass: bool

    def manifest(self) -> dict[str, object]:
        return {
            "schema": SCHEMA,
            "source_main_sha": SOURCE_MAIN_SHA,
            "method": (
                "COMPLIANCE_FAVOURING_FIXED_FREE_LINEAR_BENDING_SCREEN_ONLY; "
                "NOT_NONLINEAR_SNAP_THROUGH_FEA_AND_NOT_FORCE_TRAVEL_VALIDATION"
            ),
            "inputs": {
                "conservative_elastic_modulus_N_per_mm2": CONSERVATIVE_ELASTIC_MODULUS_N_PER_MM2,
                "beam_count": BEAM_COUNT,
                "tactile_spring_thickness_mm": haptic.TACTILE_SPRING_THICKNESS_MM,
                "tactile_beam_width_mm": haptic.TACTILE_BEAM_WIDTH_MM,
                "tactile_ring_id_mm": haptic.TACTILE_RING_ID_MM,
                "tactile_center_diameter_mm": haptic.TACTILE_CENTER_DIAMETER_MM,
                "tactile_preform_rise_mm": haptic.TACTILE_PREFORM_RISE_MM,
            },
            "derived": asdict(self),
            "decision": (
                "REJECT_CURRENT_SHORT_BEAM_GEOMETRY_AS_FORCE_DERIVED_TACTILE_SOLUTION"
                if not self.geometry_force_credibility_pass
                else "PASS_ORDER_OF_MAGNITUDE_SCREEN_ONLY"
            ),
            "required_next_evidence": [
                "SELECT_LOWER_STIFFNESS_REPEATABLE_ENERGY_ARCHITECTURE_OR_LONGER_COMPLIANT_GEOMETRY",
                "NONLINEAR_FORCE_TRAVEL_ANALYSIS_WITH_MATERIAL_AND_FORMING_ASSUMPTIONS",
                "TOLERANCE_AND_TEMPERATURE_SENSITIVITY",
                "PHYSICAL_FORCE_TRAVEL_HYSTERESIS_AND_LIFETIME_COUPON",
            ],
            "physical_validation_eligible": False,
        }


def build_screen() -> SpringGeometryScreen:
    brand = load_brand_identity()
    reference = brand.data["interaction_signature"]["primary_control"]["candidate_mechanical_reference"]
    peak_force = float(reference["force_peak_N"])
    peak_travel = float(reference["force_peak_travel_mm"])
    rest_preload = 0.22
    if not peak_force > rest_preload > 0.0 or not peak_travel > 0.0:
        raise ValueError("provisional force/travel reference must remain positive and ordered")

    center_radius = haptic.TACTILE_CENTER_DIAMETER_MM / 2.0
    ring_inner_radius = haptic.TACTILE_RING_ID_MM / 2.0
    radial_gap = ring_inner_radius - center_radius
    beam_length = radial_gap + 0.34
    if beam_length <= 0.0:
        raise ValueError("positive tactile beam length required")

    width = haptic.TACTILE_BEAM_WIDTH_MM
    thickness = haptic.TACTILE_SPRING_THICKNESS_MM
    inertia = width * thickness**3 / 12.0
    one_beam_k = 3.0 * CONSERVATIVE_ELASTIC_MODULUS_N_PER_MM2 * inertia / beam_length**3
    four_beam_k = BEAM_COUNT * one_beam_k
    target_average_k = (peak_force - rest_preload) / peak_travel
    ratio = four_beam_k / target_average_k

    equivalent_t = thickness * (target_average_k / four_beam_k) ** (1.0 / 3.0)
    equivalent_l = beam_length * (four_beam_k / target_average_k) ** (1.0 / 3.0)

    values = [
        beam_length,
        width,
        thickness,
        inertia,
        one_beam_k,
        four_beam_k,
        target_average_k,
        ratio,
        equivalent_t,
        equivalent_l,
    ]
    if any(not math.isfinite(value) or value <= 0.0 for value in values):
        raise ValueError("spring screen produced non-positive or non-finite result")

    return SpringGeometryScreen(
        beam_length_mm=beam_length,
        beam_width_mm=width,
        beam_thickness_mm=thickness,
        second_moment_mm4=inertia,
        one_beam_bending_stiffness_N_per_mm=one_beam_k,
        four_beam_bending_stiffness_N_per_mm=four_beam_k,
        target_average_rise_stiffness_N_per_mm=target_average_k,
        proxy_to_target_ratio=ratio,
        equivalent_thickness_at_current_length_mm=equivalent_t,
        equivalent_length_at_current_thickness_mm=equivalent_l,
        geometry_force_credibility_pass=ratio <= MAX_CREDIBLE_PROXY_TO_TARGET_RATIO,
    )


def write_manifest(path: str | Path) -> dict[str, object]:
    payload = build_screen().manifest()
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    print(json.dumps(build_screen().manifest(), indent=2, sort_keys=True))
