"""Measured carrier-angle slope-reversal evidence for four-zone massage actuation.

A response extremum can be hidden by magnitude-only sensitivity and curvature summaries.
This reducer identifies sign reversals between consecutive measured carrier-angle
slopes without introducing a tuning threshold or claiming physical qualification.
"""
from __future__ import annotations

from dataclasses import dataclass

from .actuation_mechanical_sensitivity import ZoneMechanicalSensitivity, reduce_measured_mechanical_sensitivity
from .actuation_parameters import ActuationParameterError, ActuationParameterSet
from .actuation_zone_sweep import FourZoneImpedanceSweep


@dataclass(frozen=True, slots=True)
class ZoneMechanicalSlopeReversal:
    zone_id: str
    lower_angle_deg: float
    center_angle_deg: float
    upper_angle_deg: float
    lower_record_id: str
    center_record_id: str
    upper_record_id: str
    force_reversal: bool
    displacement_reversal: bool
    phase_reversal: bool
    temperature_reversal: bool
    force_turning_point: str
    displacement_turning_point: str
    phase_turning_point: str
    temperature_turning_point: str


@dataclass(frozen=True, slots=True)
class ActuationMechanicalReversalEnvelope:
    source_parameter_sha256: str
    source_sweep_sha256: str
    triplet_count: int
    zone_triplet_count: int
    reversals: tuple[ZoneMechanicalSlopeReversal, ...]
    force_reversal_count: int
    displacement_reversal_count: int
    phase_reversal_count: int
    temperature_reversal_count: int
    force_peak_count: int
    force_trough_count: int
    displacement_peak_count: int
    displacement_trough_count: int
    phase_peak_count: int
    phase_trough_count: int
    temperature_peak_count: int
    temperature_trough_count: int


def _turning_point(lower: float, upper: float) -> str:
    """Classify a strict measured turning point without a tolerance or inferred threshold."""
    if lower > 0.0 > upper:
        return "PEAK"
    if lower < 0.0 < upper:
        return "TROUGH"
    return "NONE"


def _reversal(lower: ZoneMechanicalSensitivity, upper: ZoneMechanicalSensitivity) -> ZoneMechanicalSlopeReversal:
    if lower.zone_id != upper.zone_id or lower.upper_record_id != upper.lower_record_id:
        raise ActuationParameterError("Mechanical slope reversal requires consecutive intervals from one actuator zone")
    if lower.upper_angle_deg != upper.lower_angle_deg:
        raise ActuationParameterError("Mechanical slope reversal intervals must share one measured center angle")
    force = _turning_point(lower.force_slope_N_per_deg, upper.force_slope_N_per_deg)
    displacement = _turning_point(lower.displacement_slope_mm_per_deg, upper.displacement_slope_mm_per_deg)
    phase = _turning_point(lower.phase_slope_deg_per_deg, upper.phase_slope_deg_per_deg)
    temperature = _turning_point(lower.temperature_slope_C_per_deg, upper.temperature_slope_C_per_deg)
    return ZoneMechanicalSlopeReversal(
        lower.zone_id, lower.lower_angle_deg, lower.upper_angle_deg, upper.upper_angle_deg,
        lower.lower_record_id, lower.upper_record_id, upper.upper_record_id,
        force != "NONE", displacement != "NONE", phase != "NONE", temperature != "NONE",
        force, displacement, phase, temperature,
    )


def _validate_complete_four_zone_triplets(result: tuple[ZoneMechanicalSlopeReversal, ...]) -> tuple[tuple[float, float, float], ...]:
    """Fail closed unless every angle triplet has four zones and independent measured provenance."""
    by_triplet: dict[tuple[float, float, float], list[ZoneMechanicalSlopeReversal]] = {}
    for item in result:
        key = (item.lower_angle_deg, item.center_angle_deg, item.upper_angle_deg)
        by_triplet.setdefault(key, []).append(item)
    for key, items in by_triplet.items():
        zone_ids = tuple(item.zone_id for item in items)
        if len(items) != 4 or len(set(zone_ids)) != 4:
            raise ActuationParameterError(
                f"Mechanical slope reversal angle triplet {key} requires exactly four unique controlled zones"
            )
        record_ids = tuple(
            record_id
            for item in items
            for record_id in (item.lower_record_id, item.center_record_id, item.upper_record_id)
        )
        if len(set(record_ids)) != len(record_ids):
            raise ActuationParameterError(
                f"Mechanical slope reversal angle triplet {key} requires unique measured record provenance across zones"
            )
    return tuple(sorted(by_triplet))


def reduce_measured_mechanical_reversals(
    sweep: FourZoneImpedanceSweep,
    parameters: ActuationParameterSet,
) -> ActuationMechanicalReversalEnvelope:
    """Expose measured local response extrema through adjacent-slope sign reversals."""
    sensitivity = reduce_measured_mechanical_sensitivity(sweep, parameters)
    by_zone: dict[str, list[ZoneMechanicalSensitivity]] = {}
    for item in sensitivity.sensitivities:
        by_zone.setdefault(item.zone_id, []).append(item)

    reversals: list[ZoneMechanicalSlopeReversal] = []
    for zone_id in sorted(by_zone):
        intervals = sorted(by_zone[zone_id], key=lambda item: (item.lower_angle_deg, item.upper_angle_deg, item.lower_record_id))
        if len(intervals) < 2:
            raise ActuationParameterError(f"Mechanical slope reversal requires at least three measured carrier angles for {zone_id}")
        reversals.extend(_reversal(lower, upper) for lower, upper in zip(intervals, intervals[1:]))

    result = tuple(reversals)
    if not result:
        raise ActuationParameterError("Mechanical slope reversal requires measured three-point carrier-angle evidence")
    triplets = _validate_complete_four_zone_triplets(result)

    def count(metric: str, classification: str) -> int:
        return sum(getattr(item, f"{metric}_turning_point") == classification for item in result)

    return ActuationMechanicalReversalEnvelope(
        sensitivity.source_parameter_sha256, sensitivity.source_sweep_sha256,
        len(triplets), len(result), result,
        sum(item.force_reversal for item in result),
        sum(item.displacement_reversal for item in result),
        sum(item.phase_reversal for item in result),
        sum(item.temperature_reversal for item in result),
        count("force", "PEAK"), count("force", "TROUGH"),
        count("displacement", "PEAK"), count("displacement", "TROUGH"),
        count("phase", "PEAK"), count("phase", "TROUGH"),
        count("temperature", "PEAK"), count("temperature", "TROUGH"),
    )
