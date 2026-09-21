"""Adjacent-angle mechanical sensitivity from measured four-zone actuation evidence.

This reducer quantifies how force, displacement, phase, and temperature change with
carrier angle while preserving the two measured records behind every slope. It does
not define a new acceptance threshold or claim physical qualification.
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
    phase_delta_deg: float
    phase_slope_deg_per_deg: float
    temperature_delta_C: float
    temperature_slope_C_per_deg: float


@dataclass(frozen=True, slots=True)
class ZoneMechanicalSensitivityExtrema:
    """Worst measured adjacent-angle sensitivities retained independently per zone."""
    zone_id: str
    maximum_abs_force_sensitivity: ZoneMechanicalSensitivity
    maximum_abs_displacement_sensitivity: ZoneMechanicalSensitivity
    maximum_abs_phase_sensitivity: ZoneMechanicalSensitivity
    maximum_abs_temperature_sensitivity: ZoneMechanicalSensitivity


@dataclass(frozen=True, slots=True)
class ActuationMechanicalSensitivityEnvelope:
    interval_count: int
    sensitivities: tuple[ZoneMechanicalSensitivity, ...]
    zone_extrema: tuple[ZoneMechanicalSensitivityExtrema, ...]
    maximum_abs_force_sensitivity: ZoneMechanicalSensitivity
    maximum_abs_displacement_sensitivity: ZoneMechanicalSensitivity
    maximum_abs_phase_sensitivity: ZoneMechanicalSensitivity
    maximum_abs_temperature_sensitivity: ZoneMechanicalSensitivity


def _signed_phase_delta_deg(lower_deg: float, upper_deg: float) -> float:
    """Return the shortest signed phase change, avoiding a false 360-degree wrap jump."""
    delta = (upper_deg - lower_deg + 180.0) % 360.0 - 180.0
    if delta == -180.0 and upper_deg - lower_deg > 0.0:
        return 180.0
    return delta


def _interval(
    zone_id: str,
    lower: ThermalMechanicalPoint,
    upper: ThermalMechanicalPoint,
    lower_phase_deg: float,
    upper_phase_deg: float,
) -> ZoneMechanicalSensitivity:
    delta_angle = upper.axis_angle_deg - lower.axis_angle_deg
    if delta_angle <= 0.0:
        raise ActuationParameterError(f"Mechanical sensitivity requires strictly increasing carrier angles for {zone_id}")
    force_delta = upper.force_N - lower.force_N
    displacement_delta = upper.displacement_pp_mm - lower.displacement_pp_mm
    phase_delta = _signed_phase_delta_deg(lower_phase_deg, upper_phase_deg)
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
        phase_delta_deg=phase_delta,
        phase_slope_deg_per_deg=phase_delta / delta_angle,
        temperature_delta_C=temperature_delta,
        temperature_slope_C_per_deg=temperature_delta / delta_angle,
    )


def _canonical(item: ZoneMechanicalSensitivity) -> tuple[str, float, float, str, str]:
    return (item.zone_id, item.lower_angle_deg, item.upper_angle_deg, item.lower_record_id, item.upper_record_id)


def _maximum(items: tuple[ZoneMechanicalSensitivity, ...], attribute: str) -> ZoneMechanicalSensitivity:
    return max(items, key=lambda item: (abs(getattr(item, attribute)), _canonical(item)))


def reduce_measured_mechanical_sensitivity(
    sweep: FourZoneImpedanceSweep,
    parameters: ActuationParameterSet,
) -> ActuationMechanicalSensitivityEnvelope:
    """Reduce adjacent-angle measured sensitivities without losing record provenance."""
    coupling = reduce_measured_thermal_mechanical_coupling(sweep, parameters)
    phase_by_record_id = {item.record.record_id: float(item.record.measured_phase_deg) for item in sweep.records}
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
        sensitivities.extend(
            _interval(
                zone_id,
                lower,
                upper,
                phase_by_record_id[lower.record_id],
                phase_by_record_id[upper.record_id],
            )
            for lower, upper in zip(points, points[1:])
        )

    result = tuple(sensitivities)
    if not result or coupling.point_count == 0:
        raise ActuationParameterError("Mechanical sensitivity requires measured four-zone evidence")

    zone_extrema = []
    for zone_id in sorted(by_zone):
        zone_items = tuple(item for item in result if item.zone_id == zone_id)
        if not zone_items:
            raise ActuationParameterError(f"Mechanical sensitivity has no adjacent-angle evidence for {zone_id}")
        zone_extrema.append(ZoneMechanicalSensitivityExtrema(
            zone_id=zone_id,
            maximum_abs_force_sensitivity=_maximum(zone_items, "force_slope_N_per_deg"),
            maximum_abs_displacement_sensitivity=_maximum(zone_items, "displacement_slope_mm_per_deg"),
            maximum_abs_phase_sensitivity=_maximum(zone_items, "phase_slope_deg_per_deg"),
            maximum_abs_temperature_sensitivity=_maximum(zone_items, "temperature_slope_C_per_deg"),
        ))

    return ActuationMechanicalSensitivityEnvelope(
        interval_count=len(result),
        sensitivities=result,
        zone_extrema=tuple(zone_extrema),
        maximum_abs_force_sensitivity=_maximum(result, "force_slope_N_per_deg"),
        maximum_abs_displacement_sensitivity=_maximum(result, "displacement_slope_mm_per_deg"),
        maximum_abs_phase_sensitivity=_maximum(result, "phase_slope_deg_per_deg"),
        maximum_abs_temperature_sensitivity=_maximum(result, "temperature_slope_C_per_deg"),
    )
