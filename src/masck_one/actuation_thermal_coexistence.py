"""Measured actuation temperature evidence for treatment/thermal coexistence.

This module deliberately reports observed temperature extrema only. It does not
invent a thermal acceptance threshold or convert bench evidence into a physical
qualification claim.
"""
from __future__ import annotations

from dataclasses import dataclass

from .actuation_parameters import ActuationParameterError, ActuationParameterSet
from .actuation_zone_sweep import FourZoneImpedanceSweep, ZoneImpedanceRecord


@dataclass(frozen=True, slots=True)
class ActuationThermalEnvelope:
    """Traceable measured temperature extrema across the complete four-zone DOE."""

    point_count: int
    min_temperature_C: float
    min_temperature_zone_id: str
    min_temperature_axis_angle_deg: float
    min_temperature_record_id: str
    max_temperature_C: float
    max_temperature_zone_id: str
    max_temperature_axis_angle_deg: float
    max_temperature_record_id: str


def reduce_measured_actuation_thermal_envelope(
    sweep: FourZoneImpedanceSweep,
    parameters: ActuationParameterSet,
) -> ActuationThermalEnvelope:
    """Reduce a complete measured sweep to traceable temperature extrema.

    The sweep's existing validator remains the authority for completeness,
    parameter provenance, command envelope and evidence-kind consistency.
    """
    if type(sweep) is not FourZoneImpedanceSweep:
        raise ActuationParameterError("Actuation thermal envelope requires exact FourZoneImpedanceSweep evidence")
    if type(parameters) is not ActuationParameterSet:
        raise ActuationParameterError("Actuation thermal envelope requires exact ActuationParameterSet evidence")
    sweep.validate(parameters)
    if any(item.record.source_kind != "MEASURED" for item in sweep.records):
        raise ActuationParameterError("Actuation thermal envelope requires a complete measured four-zone sweep")

    points: list[tuple[ZoneImpedanceRecord, float]] = []
    for item in sweep.records:
        temperature = item.record.measured_temperature_C
        if temperature is None:
            raise ActuationParameterError("Measured sweep lost required temperature observation")
        points.append((item, float(temperature)))

    minimum = min(points, key=lambda point: (point[1], point[0].zone_id, point[0].record.axis_angle_deg, point[0].record.record_id))
    maximum = max(points, key=lambda point: (point[1], point[0].zone_id, point[0].record.axis_angle_deg, point[0].record.record_id))
    return ActuationThermalEnvelope(
        point_count=len(points),
        min_temperature_C=minimum[1],
        min_temperature_zone_id=minimum[0].zone_id,
        min_temperature_axis_angle_deg=float(minimum[0].record.axis_angle_deg),
        min_temperature_record_id=minimum[0].record.record_id,
        max_temperature_C=maximum[1],
        max_temperature_zone_id=maximum[0].zone_id,
        max_temperature_axis_angle_deg=float(maximum[0].record.axis_angle_deg),
        max_temperature_record_id=maximum[0].record.record_id,
    )
