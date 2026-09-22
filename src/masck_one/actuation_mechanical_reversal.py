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


def _strict_sign_reversal(lower: float, upper: float) -> bool:
    """Return true only when two measured slopes have opposite non-zero signs."""
    return (lower < 0.0 < upper) or (upper < 0.0 < lower)


def _reversal(lower: ZoneMechanicalSensitivity, upper: ZoneMechanicalSensitivity) -> ZoneMechanicalSlopeReversal:
    if lower.zone_id != upper.zone_id or lower.upper_record_id != upper.lower_record_id:
        raise ActuationParameterError("Mechanical slope reversal requires consecutive intervals from one actuator zone")
    if lower.upper_angle_deg != upper.lower_angle_deg:
        raise ActuationParameterError("Mechanical slope reversal intervals must share one measured center angle")
    return ZoneMechanicalSlopeReversal(
        lower.zone_id,
        lower.lower_angle_deg,
        lower.upper_angle_deg,
        upper.upper_angle_deg,
        lower.lower_record_id,
        lower.upper_record_id,
        upper.upper_record_id,
        _strict_sign_reversal(lower.force_slope_N_per_deg, upper.force_slope_N_per_deg),
        _strict_sign_reversal(lower.displacement_slope_mm_per_deg, upper.displacement_slope_mm_per_deg),
        _strict_sign_reversal(lower.phase_slope_deg_per_deg, upper.phase_slope_deg_per_deg),
        _strict_sign_reversal(lower.temperature_slope_C_per_deg, upper.temperature_slope_C_per_deg),
    )


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
        intervals = sorted(
            by_zone[zone_id],
            key=lambda item: (item.lower_angle_deg, item.upper_angle_deg, item.lower_record_id),
        )
        if len(intervals) < 2:
            raise ActuationParameterError(f"Mechanical slope reversal requires at least three measured carrier angles for {zone_id}")
        reversals.extend(_reversal(lower, upper) for lower, upper in zip(intervals, intervals[1:]))

    result = tuple(reversals)
    if not result:
        raise ActuationParameterError("Mechanical slope reversal requires measured three-point carrier-angle evidence")
    triplets = {(item.lower_angle_deg, item.center_angle_deg, item.upper_angle_deg) for item in result}
    zones = {item.zone_id for item in result}
    if len(zones) != 4 or len(result) != 4 * len(triplets):
        raise ActuationParameterError("Mechanical slope reversal requires complete four-zone angle-triplet evidence")

    return ActuationMechanicalReversalEnvelope(
        sensitivity.source_parameter_sha256,
        sensitivity.source_sweep_sha256,
        len(triplets),
        len(result),
        result,
        sum(item.force_reversal for item in result),
        sum(item.displacement_reversal for item in result),
        sum(item.phase_reversal for item in result),
        sum(item.temperature_reversal for item in result),
    )
