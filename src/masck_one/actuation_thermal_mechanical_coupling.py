"""Coupled thermal/mechanical reduction for measured four-zone actuation evidence.

This module keeps temperature, force and displacement observations tied to the same
bench record. It reports measured coexistence evidence only and does not invent a
thermal threshold or declare physical qualification.
"""
from __future__ import annotations

from dataclasses import dataclass

from .actuation_parameters import ActuationParameterError, ActuationParameterSet
from .actuation_zone_sweep import FourZoneImpedanceSweep, ZoneImpedanceRecord


@dataclass(frozen=True, slots=True)
class ThermalMechanicalPoint:
    zone_id: str
    axis_angle_deg: float
    record_id: str
    temperature_C: float
    force_N: float
    displacement_pp_mm: float
    displacement_error_mm: float
    continuous_force_margin_N: float
    transient_force_margin_N: float


@dataclass(frozen=True, slots=True)
class ZoneThermalMechanicalEnvelope:
    """Measured coupled extrema for one physical actuator zone."""

    zone_id: str
    point_count: int
    hottest_point: ThermalMechanicalPoint
    minimum_force_point: ThermalMechanicalPoint
    maximum_displacement_error_point: ThermalMechanicalPoint
    hottest_continuous_force_shortfall_point: ThermalMechanicalPoint | None
    hottest_transient_force_shortfall_point: ThermalMechanicalPoint | None


@dataclass(frozen=True, slots=True)
class AngleThermalMechanicalSpread:
    """Cross-zone thermal/mechanical spread at one shared carrier angle."""

    axis_angle_deg: float
    point_count: int
    hottest_point: ThermalMechanicalPoint
    coolest_point: ThermalMechanicalPoint
    minimum_force_point: ThermalMechanicalPoint
    maximum_force_point: ThermalMechanicalPoint
    minimum_displacement_point: ThermalMechanicalPoint
    maximum_displacement_point: ThermalMechanicalPoint
    maximum_displacement_error_point: ThermalMechanicalPoint
    temperature_span_C: float
    force_span_N: float
    displacement_span_mm: float
    hottest_zone_is_minimum_force_zone: bool
    hottest_zone_is_maximum_displacement_error_zone: bool


@dataclass(frozen=True, slots=True)
class ActuationThermalMechanicalCoupling:
    """Traceable measured points relevant to thermal/mechanical coexistence."""

    point_count: int
    hottest_point: ThermalMechanicalPoint
    minimum_force_point: ThermalMechanicalPoint
    maximum_displacement_error_point: ThermalMechanicalPoint
    hottest_continuous_force_shortfall_point: ThermalMechanicalPoint | None
    hottest_transient_force_shortfall_point: ThermalMechanicalPoint | None
    zone_envelopes: tuple[ZoneThermalMechanicalEnvelope, ...]
    angle_spreads: tuple[AngleThermalMechanicalSpread, ...]
    maximum_temperature_span_angle: AngleThermalMechanicalSpread
    maximum_force_span_angle: AngleThermalMechanicalSpread
    maximum_displacement_span_angle: AngleThermalMechanicalSpread


def _point(item: ZoneImpedanceRecord, parameters: ActuationParameterSet) -> ThermalMechanicalPoint:
    record = item.record
    if record.measured_temperature_C is None or record.measured_force_N is None or record.measured_displacement_pp_mm is None:
        raise ActuationParameterError("Measured coexistence evidence requires temperature, force and displacement observations")
    force = float(record.measured_force_N)
    displacement = float(record.measured_displacement_pp_mm)
    return ThermalMechanicalPoint(
        zone_id=item.zone_id,
        axis_angle_deg=float(record.axis_angle_deg),
        record_id=record.record_id,
        temperature_C=float(record.measured_temperature_C),
        force_N=force,
        displacement_pp_mm=displacement,
        displacement_error_mm=displacement - parameters.displacement_pp_baseline_mm,
        continuous_force_margin_N=force - parameters.continuous_force_requirement_N,
        transient_force_margin_N=force - parameters.transient_force_requirement_N,
    )


def _canonical(point: ThermalMechanicalPoint) -> tuple[str, float, str]:
    return (point.zone_id, point.axis_angle_deg, point.record_id)


def _reduce_zone(zone_id: str, points: tuple[ThermalMechanicalPoint, ...]) -> ZoneThermalMechanicalEnvelope:
    if not points:
        raise ActuationParameterError(f"Measured coexistence evidence missing actuator zone {zone_id}")
    hottest = max(points, key=lambda point: (point.temperature_C, _canonical(point)))
    minimum_force = min(points, key=lambda point: (point.force_N, _canonical(point)))
    maximum_error = max(points, key=lambda point: (abs(point.displacement_error_mm), _canonical(point)))
    continuous_shortfalls = tuple(point for point in points if point.continuous_force_margin_N < 0.0)
    transient_shortfalls = tuple(point for point in points if point.transient_force_margin_N < 0.0)
    return ZoneThermalMechanicalEnvelope(
        zone_id=zone_id,
        point_count=len(points),
        hottest_point=hottest,
        minimum_force_point=minimum_force,
        maximum_displacement_error_point=maximum_error,
        hottest_continuous_force_shortfall_point=max(continuous_shortfalls, key=lambda point: (point.temperature_C, _canonical(point))) if continuous_shortfalls else None,
        hottest_transient_force_shortfall_point=max(transient_shortfalls, key=lambda point: (point.temperature_C, _canonical(point))) if transient_shortfalls else None,
    )


def _reduce_angle(angle: float, points: tuple[ThermalMechanicalPoint, ...]) -> AngleThermalMechanicalSpread:
    angle_points = tuple(point for point in points if point.axis_angle_deg == angle)
    if not angle_points:
        raise ActuationParameterError(f"Measured coexistence evidence missing carrier angle {angle:g}")
    hottest = max(angle_points, key=lambda point: (point.temperature_C, _canonical(point)))
    coolest = min(angle_points, key=lambda point: (point.temperature_C, _canonical(point)))
    minimum_force = min(angle_points, key=lambda point: (point.force_N, _canonical(point)))
    maximum_force = max(angle_points, key=lambda point: (point.force_N, _canonical(point)))
    minimum_displacement = min(angle_points, key=lambda point: (point.displacement_pp_mm, _canonical(point)))
    maximum_displacement = max(angle_points, key=lambda point: (point.displacement_pp_mm, _canonical(point)))
    maximum_error = max(angle_points, key=lambda point: (abs(point.displacement_error_mm), _canonical(point)))
    return AngleThermalMechanicalSpread(
        axis_angle_deg=angle,
        point_count=len(angle_points),
        hottest_point=hottest,
        coolest_point=coolest,
        minimum_force_point=minimum_force,
        maximum_force_point=maximum_force,
        minimum_displacement_point=minimum_displacement,
        maximum_displacement_point=maximum_displacement,
        maximum_displacement_error_point=maximum_error,
        temperature_span_C=hottest.temperature_C - coolest.temperature_C,
        force_span_N=maximum_force.force_N - minimum_force.force_N,
        displacement_span_mm=maximum_displacement.displacement_pp_mm - minimum_displacement.displacement_pp_mm,
        hottest_zone_is_minimum_force_zone=hottest.zone_id == minimum_force.zone_id,
        hottest_zone_is_maximum_displacement_error_zone=hottest.zone_id == maximum_error.zone_id,
    )


def reduce_measured_thermal_mechanical_coupling(
    sweep: FourZoneImpedanceSweep,
    parameters: ActuationParameterSet,
) -> ActuationThermalMechanicalCoupling:
    """Locate coupled measured worst cases without separating observations by record."""
    if type(sweep) is not FourZoneImpedanceSweep:
        raise ActuationParameterError("Thermal/mechanical coupling requires exact FourZoneImpedanceSweep evidence")
    if type(parameters) is not ActuationParameterSet:
        raise ActuationParameterError("Thermal/mechanical coupling requires exact ActuationParameterSet evidence")
    sweep.validate(parameters)
    if any(item.record.source_kind != "MEASURED" for item in sweep.records):
        raise ActuationParameterError("Thermal/mechanical coupling requires a complete measured four-zone sweep")

    points = tuple(_point(item, parameters) for item in sweep.records)
    hottest = max(points, key=lambda point: (point.temperature_C, _canonical(point)))
    minimum_force = min(points, key=lambda point: (point.force_N, _canonical(point)))
    maximum_error = max(points, key=lambda point: (abs(point.displacement_error_mm), _canonical(point)))

    continuous_shortfalls = tuple(point for point in points if point.continuous_force_margin_N < 0.0)
    transient_shortfalls = tuple(point for point in points if point.transient_force_margin_N < 0.0)
    hottest_continuous_shortfall = max(continuous_shortfalls, key=lambda point: (point.temperature_C, _canonical(point))) if continuous_shortfalls else None
    hottest_transient_shortfall = max(transient_shortfalls, key=lambda point: (point.temperature_C, _canonical(point))) if transient_shortfalls else None

    zone_ids = tuple(sorted({point.zone_id for point in points}))
    zone_envelopes = tuple(_reduce_zone(zone_id, tuple(point for point in points if point.zone_id == zone_id)) for zone_id in zone_ids)
    angles = tuple(sorted({point.axis_angle_deg for point in points}))
    angle_spreads = tuple(_reduce_angle(angle, points) for angle in angles)
    maximum_temperature_span_angle = max(angle_spreads, key=lambda spread: (spread.temperature_span_C, -spread.axis_angle_deg))
    maximum_force_span_angle = max(angle_spreads, key=lambda spread: (spread.force_span_N, -spread.axis_angle_deg))
    maximum_displacement_span_angle = max(angle_spreads, key=lambda spread: (spread.displacement_span_mm, -spread.axis_angle_deg))

    return ActuationThermalMechanicalCoupling(
        point_count=len(points),
        hottest_point=hottest,
        minimum_force_point=minimum_force,
        maximum_displacement_error_point=maximum_error,
        hottest_continuous_force_shortfall_point=hottest_continuous_shortfall,
        hottest_transient_force_shortfall_point=hottest_transient_shortfall,
        zone_envelopes=zone_envelopes,
        angle_spreads=angle_spreads,
        maximum_temperature_span_angle=maximum_temperature_span_angle,
        maximum_force_span_angle=maximum_force_span_angle,
        maximum_displacement_span_angle=maximum_displacement_span_angle,
    )
