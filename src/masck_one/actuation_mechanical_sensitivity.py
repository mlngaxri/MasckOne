"""Adjacent-angle mechanical sensitivity from measured four-zone actuation evidence.

This reducer quantifies how force and displacement change with carrier angle while
preserving the two measured records behind every slope. It does not define a new
acceptance threshold or claim physical qualification.
"""
from __future__ import annotations

from dataclasses import dataclass

from .actuation_parameters import ActuationParameterError, ActuationParameterSet
from .actuation_thermal_mechanical_coupling import ThermalMechanicalPoint, reduce_measured_thermal_mechanical_coupling
from .actuation_zone_sweep import FourZoneImpedanceSweep


@dataclass(frozen=True, slots=True)
class ZoneMechanicalSensitivity:
    zone_id: str
    lower_angle_deg: float
    upper_angle_deg: float
    lower_record_id: str
    upper_record_id: str
    angle_delta_deg: float
    force_delta_N: float
    force_slope_N_per_deg: float
    displacement_delta_mm: float
    displacement_slope_mm_per_deg: float
    temperature_delta_C: float
    temperature_slope_C_per_deg: float


@dataclass(frozen=True, slots=True)
class ActuationMechanicalSensitivityEnvelope:
    interval_count: int
    sensitivities: tuple[ZoneMechanicalSensitivity, ...]
    maximum_abs_force_sensitivity: ZoneMechanicalSensitivity
    maximum_abs_displacement_sensitivity: ZoneMechanicalSensitivity
    maximum_abs_temperature_sensitivity: ZoneMechanicalSensitivity


def _interval(zone_id: str, lower: ThermalMechanicalPoint, upper: ThermalMechanicalPoint) -> ZoneMechanicalSensitivity:
    delta_angle = upper.axis_angle_deg - lower.axis_angle_deg
    if delta_angle <= 0.0:
        raise ActuationParameterError(f"Mechanical sensitivity requires strictly increasing carrier angles for {zone_id}")
    force_delta = upper.force_N - lower.force_N
    displacement_delta = upper.displacement_pp_mm - lower.displacement_pp_mm
    temperature_delta = upper.temperature_C - lower.temperature_C
    return ZoneMechanicalSensitivity(
        zone_id=zone_id,
        lower_angle_deg=lower.axis_angle_deg,
        upper_angle_deg=upper.axis_angle_deg,
        lower_record_id=lower.record_id,
        upper_record_id=upper.record_id,
        angle_delta_deg=delta_angle,
        force_delta_N=force_delta,
        force_slope_N_per_deg=force_delta / delta_angle,
        displacement_delta_mm=displacement_delta,
        displacement_slope_mm_per_deg=displacement_delta / delta_angle,
        temperature_delta_C=temperature_delta,
        temperature_slope_C_per_deg=temperature_delta / delta_angle,
    )


def _canonical(item: ZoneMechanicalSensitivity) -> tuple[str, float, float, str, str]:
    return (item.zone_id, item.lower_angle_deg, item.upper_angle_deg, item.lower_record_id, item.upper_record_id)


def reduce_measured_mechanical_sensitivity(
    sweep: FourZoneImpedanceSweep,
    parameters: ActuationParameterSet,
) -> ActuationMechanicalSensitivityEnvelope:
    """Reduce adjacent-angle measured sensitivities without losing record provenance."""
    coupling = reduce_measured_thermal_mechanical_coupling(sweep, parameters)
    by_zone: dict[str, list[ThermalMechanicalPoint]] = {}
    for point in tuple(
        ThermalMechanicalPoint(
            zone_id=item.zone_id,
            axis_angle_deg=float(item.record.axis_angle_deg),
            record_id=item.record.record_id,
            temperature_C=float(item.record.measured_temperature_C),
            force_N=float(item.record.measured_force_N),
            displacement_pp_mm=float(item.record.measured_displacement_pp_mm),
            displacement_error_mm=float(item.record.measured_displacement_pp_mm) - parameters.displacement_pp_baseline_mm,
            continuous_force_margin_N=float(item.record.measured_force_N) - parameters.continuous_force_requirement_N,
            transient_force_margin_N=float(item.record.measured_force_N) - parameters.transient_force_requirement_N,
        )
        for item in sweep.records
    ):
        by_zone.setdefault(point.zone_id, []).append(point)

    sensitivities: list[ZoneMechanicalSensitivity] = []
    for zone_id in sorted(by_zone):
        points = sorted(by_zone[zone_id], key=lambda point: (point.axis_angle_deg, point.record_id))
        if len(points) < 2:
            raise ActuationParameterError(f"Mechanical sensitivity requires at least two measured carrier angles for {zone_id}")
        sensitivities.extend(_interval(zone_id, lower, upper) for lower, upper in zip(points, points[1:]))

    result = tuple(sensitivities)
    if not result or coupling.point_count == 0:
        raise ActuationParameterError("Mechanical sensitivity requires measured four-zone evidence")
    return ActuationMechanicalSensitivityEnvelope(
        interval_count=len(result),
        sensitivities=result,
        maximum_abs_force_sensitivity=max(result, key=lambda item: (abs(item.force_slope_N_per_deg), _canonical(item))),
        maximum_abs_displacement_sensitivity=max(result, key=lambda item: (abs(item.displacement_slope_mm_per_deg), _canonical(item))),
        maximum_abs_temperature_sensitivity=max(result, key=lambda item: (abs(item.temperature_slope_C_per_deg), _canonical(item))),
    )
