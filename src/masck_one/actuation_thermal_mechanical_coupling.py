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
class ActuationThermalMechanicalCoupling:
    """Traceable measured points relevant to thermal/mechanical coexistence."""

    point_count: int
    hottest_point: ThermalMechanicalPoint
    minimum_force_point: ThermalMechanicalPoint
    maximum_displacement_error_point: ThermalMechanicalPoint
    hottest_continuous_force_shortfall_point: ThermalMechanicalPoint | None
    hottest_transient_force_shortfall_point: ThermalMechanicalPoint | None


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
    canonical = lambda point: (point.zone_id, point.axis_angle_deg, point.record_id)
    hottest = max(points, key=lambda point: (point.temperature_C, canonical(point)))
    minimum_force = min(points, key=lambda point: (point.force_N, canonical(point)))
    maximum_error = max(points, key=lambda point: (abs(point.displacement_error_mm), canonical(point)))

    continuous_shortfalls = tuple(point for point in points if point.continuous_force_margin_N < 0.0)
    transient_shortfalls = tuple(point for point in points if point.transient_force_margin_N < 0.0)
    hottest_continuous_shortfall = max(continuous_shortfalls, key=lambda point: (point.temperature_C, canonical(point))) if continuous_shortfalls else None
    hottest_transient_shortfall = max(transient_shortfalls, key=lambda point: (point.temperature_C, canonical(point))) if transient_shortfalls else None

    return ActuationThermalMechanicalCoupling(
        point_count=len(points),
        hottest_point=hottest,
        minimum_force_point=minimum_force,
        maximum_displacement_error_point=maximum_error,
        hottest_continuous_force_shortfall_point=hottest_continuous_shortfall,
        hottest_transient_force_shortfall_point=hottest_transient_shortfall,
    )
