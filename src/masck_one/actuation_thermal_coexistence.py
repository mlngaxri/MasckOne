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
class ZoneThermalEnvelope:
    """Traceable measured temperature range for one actuator zone."""

    zone_id: str
    point_count: int
    min_temperature_C: float
    min_temperature_axis_angle_deg: float
    min_temperature_record_id: str
    max_temperature_C: float
    max_temperature_axis_angle_deg: float
    max_temperature_record_id: str
    temperature_span_C: float


@dataclass(frozen=True, slots=True)
class AngleThermalSpread:
    """Cross-zone temperature spread at one shared axis-angle DOE point."""

    axis_angle_deg: float
    point_count: int
    min_temperature_C: float
    min_temperature_zone_id: str
    min_temperature_record_id: str
    max_temperature_C: float
    max_temperature_zone_id: str
    max_temperature_record_id: str
    cross_zone_span_C: float


@dataclass(frozen=True, slots=True)
class ZoneAngleThermalSensitivity:
    """Measured local temperature slope between adjacent DOE angles for one zone."""

    zone_id: str
    lower_axis_angle_deg: float
    upper_axis_angle_deg: float
    lower_record_id: str
    upper_record_id: str
    temperature_delta_C: float
    temperature_slope_C_per_deg: float


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
    zone_envelopes: tuple[ZoneThermalEnvelope, ...]
    angle_spreads: tuple[AngleThermalSpread, ...]
    max_cross_zone_span_C: float
    max_cross_zone_span_axis_angle_deg: float
    max_cross_zone_span_min_zone_id: str
    max_cross_zone_span_min_record_id: str
    max_cross_zone_span_max_zone_id: str
    max_cross_zone_span_max_record_id: str
    angle_sensitivities: tuple[ZoneAngleThermalSensitivity, ...]
    max_abs_temperature_slope_C_per_deg: float
    max_abs_temperature_slope_zone_id: str
    max_abs_temperature_slope_lower_axis_angle_deg: float
    max_abs_temperature_slope_upper_axis_angle_deg: float
    max_abs_temperature_slope_lower_record_id: str
    max_abs_temperature_slope_upper_record_id: str


def reduce_measured_actuation_thermal_envelope(
    sweep: FourZoneImpedanceSweep,
    parameters: ActuationParameterSet,
) -> ActuationThermalEnvelope:
    """Reduce a complete measured sweep to traceable system, zone and angle extrema."""
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

    zone_envelopes: list[ZoneThermalEnvelope] = []
    angle_sensitivities: list[ZoneAngleThermalSensitivity] = []
    for zone_id in sorted({item.zone_id for item, _ in points}):
        zone_points = [point for point in points if point[0].zone_id == zone_id]
        zone_minimum = min(zone_points, key=lambda point: (point[1], point[0].record.axis_angle_deg, point[0].record.record_id))
        zone_maximum = max(zone_points, key=lambda point: (point[1], point[0].record.axis_angle_deg, point[0].record.record_id))
        zone_envelopes.append(ZoneThermalEnvelope(
            zone_id=zone_id,
            point_count=len(zone_points),
            min_temperature_C=zone_minimum[1],
            min_temperature_axis_angle_deg=float(zone_minimum[0].record.axis_angle_deg),
            min_temperature_record_id=zone_minimum[0].record.record_id,
            max_temperature_C=zone_maximum[1],
            max_temperature_axis_angle_deg=float(zone_maximum[0].record.axis_angle_deg),
            max_temperature_record_id=zone_maximum[0].record.record_id,
            temperature_span_C=zone_maximum[1] - zone_minimum[1],
        ))
        ordered_zone_points = sorted(zone_points, key=lambda point: (float(point[0].record.axis_angle_deg), point[0].record.record_id))
        for lower, upper in zip(ordered_zone_points, ordered_zone_points[1:]):
            lower_angle = float(lower[0].record.axis_angle_deg)
            upper_angle = float(upper[0].record.axis_angle_deg)
            angle_delta = upper_angle - lower_angle
            if angle_delta <= 0.0:
                raise ActuationParameterError("Thermal sensitivity requires strictly increasing unique DOE angles")
            temperature_delta = upper[1] - lower[1]
            angle_sensitivities.append(ZoneAngleThermalSensitivity(
                zone_id=zone_id,
                lower_axis_angle_deg=lower_angle,
                upper_axis_angle_deg=upper_angle,
                lower_record_id=lower[0].record.record_id,
                upper_record_id=upper[0].record.record_id,
                temperature_delta_C=temperature_delta,
                temperature_slope_C_per_deg=temperature_delta / angle_delta,
            ))

    angle_spreads: list[AngleThermalSpread] = []
    for angle in sorted({float(item.record.axis_angle_deg) for item, _ in points}):
        angle_points = [point for point in points if float(point[0].record.axis_angle_deg) == angle]
        angle_minimum = min(angle_points, key=lambda point: (point[1], point[0].zone_id, point[0].record.record_id))
        angle_maximum = max(angle_points, key=lambda point: (point[1], point[0].zone_id, point[0].record.record_id))
        angle_spreads.append(AngleThermalSpread(
            axis_angle_deg=angle,
            point_count=len(angle_points),
            min_temperature_C=angle_minimum[1],
            min_temperature_zone_id=angle_minimum[0].zone_id,
            min_temperature_record_id=angle_minimum[0].record.record_id,
            max_temperature_C=angle_maximum[1],
            max_temperature_zone_id=angle_maximum[0].zone_id,
            max_temperature_record_id=angle_maximum[0].record.record_id,
            cross_zone_span_C=angle_maximum[1] - angle_minimum[1],
        ))
    worst_spread = max(angle_spreads, key=lambda spread: (spread.cross_zone_span_C, -spread.axis_angle_deg))
    worst_sensitivity = max(angle_sensitivities, key=lambda item: (abs(item.temperature_slope_C_per_deg), item.zone_id, -item.lower_axis_angle_deg))

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
        zone_envelopes=tuple(zone_envelopes),
        angle_spreads=tuple(angle_spreads),
        max_cross_zone_span_C=worst_spread.cross_zone_span_C,
        max_cross_zone_span_axis_angle_deg=worst_spread.axis_angle_deg,
        max_cross_zone_span_min_zone_id=worst_spread.min_temperature_zone_id,
        max_cross_zone_span_min_record_id=worst_spread.min_temperature_record_id,
        max_cross_zone_span_max_zone_id=worst_spread.max_temperature_zone_id,
        max_cross_zone_span_max_record_id=worst_spread.max_temperature_record_id,
        angle_sensitivities=tuple(angle_sensitivities),
        max_abs_temperature_slope_C_per_deg=abs(worst_sensitivity.temperature_slope_C_per_deg),
        max_abs_temperature_slope_zone_id=worst_sensitivity.zone_id,
        max_abs_temperature_slope_lower_axis_angle_deg=worst_sensitivity.lower_axis_angle_deg,
        max_abs_temperature_slope_upper_axis_angle_deg=worst_sensitivity.upper_axis_angle_deg,
        max_abs_temperature_slope_lower_record_id=worst_sensitivity.lower_record_id,
        max_abs_temperature_slope_upper_record_id=worst_sensitivity.upper_record_id,
    )
