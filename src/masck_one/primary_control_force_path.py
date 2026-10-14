"""Necessary quasi-static force bounds for a passive series-spring button.

This is deliberately independent of a guessed dome force/travel curve. A spring
that cannot reach even the low end of the captured typical trip-force range
before coil bind cannot justify a post-collapse kinematic branch. Passing this
screen alone would not prove a working switch, travel limit or subjective feel.
"""

from dataclasses import asdict, dataclass
import math


class ButtonForcePathError(ValueError):
    pass


@dataclass(frozen=True)
class SeriesSpringInputs:
    shear_modulus_seed_N_mm2: float
    wire_mm: float
    mean_coil_mm: float
    active_coils: float
    total_coils: float
    free_length_mm: float
    installed_length_mm: float
    rest_gap_mm: float
    hard_travel_mm: float
    dome_height_mm: float
    trip_nominal_N: float
    trip_typical_tolerance_N: float
    allowed_postcollapse_increment_N: float

    def validate(self) -> None:
        values = asdict(self)
        if any(not math.isfinite(value) for value in values.values()):
            raise ButtonForcePathError("force-path dimensions and loads must be finite")
        if any(value <= 0.0 for value in values.values()):
            raise ButtonForcePathError("force-path inputs must be positive")
        if self.total_coils < self.active_coils:
            raise ButtonForcePathError("total coils cannot be fewer than active coils")
        if self.mean_coil_mm <= self.wire_mm:
            raise ButtonForcePathError("coil inside diameter must be positive")
        if not self.free_length_mm > self.installed_length_mm > self.total_coils * self.wire_mm:
            raise ButtonForcePathError("spring must fit with positive rest preload and coil clearance")
        if self.hard_travel_mm <= self.rest_gap_mm + self.dome_height_mm:
            raise ButtonForcePathError("this screen requires a positive postcollapse travel interval")
        if self.trip_nominal_N <= self.trip_typical_tolerance_N:
            raise ButtonForcePathError("captured typical trip-force range must remain positive")


def evaluate_series_spring(inputs: SeriesSpringInputs) -> dict[str, object]:
    inputs.validate()
    p = inputs
    rate = p.shear_modulus_seed_N_mm2 * p.wire_mm**4 / (8 * p.mean_coil_mm**3 * p.active_coils)
    solid = p.total_coils * p.wire_mm
    rest_compression = p.free_length_mm - p.installed_length_mm
    elastic_compression_limit = p.free_length_mm - solid
    # Zero dome deflection maximises relative spring compression for any cap pose.
    # Coil bind is excluded as a valid load path: its force is not this linear rate.
    available_compression = min(
        elastic_compression_limit,
        rest_compression + p.hard_travel_mm - p.rest_gap_mm,
    )
    max_elastic_force = rate * available_compression
    lowest_typical_trip = p.trip_nominal_N - p.trip_typical_tolerance_N
    postcollapse_travel_lower_bound = p.hard_travel_mm - p.rest_gap_mm - p.dome_height_mm
    rate_required = lowest_typical_trip / available_compression
    rate_allowed = p.allowed_postcollapse_increment_N / postcollapse_travel_lower_bound
    reaches_trip = max_elastic_force >= lowest_typical_trip
    return {
        "schema": "MASCK_ONE_BUTTON_SERIES_FORCE_PATH_V1",
        "scope": "PASSIVE_OFF_FACE_MECHANICAL_SCREEN",
        "inputs": asdict(p),
        "spring_rate_N_per_mm": rate,
        "rest_preload_force_N": rate * rest_compression,
        "solid_height_mm": solid,
        "maximum_elastic_force_before_bind_or_stop_N": max_elastic_force,
        "lowest_captured_typical_trip_N": lowest_typical_trip,
        "force_margin_to_typical_low_N": max_elastic_force - lowest_typical_trip,
        "compression_required_for_typical_low_trip_mm": lowest_typical_trip / rate,
        "available_elastic_compression_upper_bound_mm": available_compression,
        "coil_bind_cap_travel_if_dome_locked_mm": p.rest_gap_mm + p.installed_length_mm - solid,
        "coil_bind_may_precede_cap_hard_stop": p.rest_gap_mm + p.installed_length_mm - solid < p.hard_travel_mm,
        "postcollapse_travel_lower_bound_mm": postcollapse_travel_lower_bound,
        "minimum_rate_to_reach_typical_low_trip_N_per_mm": rate_required,
        "maximum_rate_for_postcollapse_increment_N_per_mm": rate_allowed,
        "rate_only_repair_has_feasible_interval": rate_required <= rate_allowed,
        "minimum_postcollapse_increment_if_rate_repaired_N": rate_required * postcollapse_travel_lower_bound,
        "reaches_typical_trip_before_bind_or_stop": reaches_trip,
        "decision": "NECESSARY_FORCE_BOUND_ONLY" if reaches_trip else "REJECTED_SERIES_FORCE_PATH",
        "functional_architecture_eligible": False,
        "physical_validation_eligible": False,
        "evidence": {
            "source": "https://www.snaptron.com/products/standard-domes/f-series/",
            "captured_part": "F06130",
            "supplier_trip_range_status": "PUBLISHED_TYPICAL_NOT_QUALIFIED_LOWER_BOUND",
            "spring_modulus_rate": "ASSUMED_INPUT_FIRST_ORDER_MODEL",
            "dome_height": "GEOMETRIC_UPPER_BOUND_NOT_PERMITTED_TRAVEL",
            "postcollapse_branch": "CONDITIONAL_ON_TRIP_NOT_AN_OBSERVED_STATE",
            "coil_bind_location": "LOCKED_DOME_BOUND_NOT_PREDICTED_ACTUAL_TRAVEL",
        },
    }
