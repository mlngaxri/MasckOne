"""Second-order carrier-angle response from measured four-zone actuation evidence.

Adjacent slopes can hide a sharp change in response around an intermediate carrier
angle. This reducer compares consecutive measured sensitivity intervals and retains
all three source records behind each slope-change estimate. It introduces no new
acceptance threshold and does not claim physical qualification.
"""
from __future__ import annotations

from dataclasses import dataclass

from .actuation_mechanical_sensitivity import (
    ZoneMechanicalSensitivity,
    reduce_measured_mechanical_sensitivity,
)
from .actuation_parameters import ActuationParameterError, ActuationParameterSet
from .actuation_zone_sweep import FourZoneImpedanceSweep


@dataclass(frozen=True, slots=True)
class ZoneMechanicalCurvature:
    zone_id: str
    lower_angle_deg: float
    center_angle_deg: float
    upper_angle_deg: float
    lower_record_id: str
    center_record_id: str
    upper_record_id: str
    interval_center_delta_deg: float
    force_slope_change_N_per_deg: float
    force_curvature_N_per_deg2: float
    displacement_slope_change_mm_per_deg: float
    displacement_curvature_mm_per_deg2: float
    phase_slope_change_deg_per_deg: float
    phase_curvature_deg_per_deg2: float
    temperature_slope_change_C_per_deg: float
    temperature_curvature_C_per_deg2: float


@dataclass(frozen=True, slots=True)
class ZoneMechanicalCurvatureExtrema:
    """Worst measured nonlinear response retained independently for one actuator zone."""
    zone_id: str
    maximum_abs_force_curvature: ZoneMechanicalCurvature
    maximum_abs_displacement_curvature: ZoneMechanicalCurvature
    maximum_abs_phase_curvature: ZoneMechanicalCurvature
    maximum_abs_temperature_curvature: ZoneMechanicalCurvature


@dataclass(frozen=True, slots=True)
class AngleTripletCurvatureExtrema:
    """Worst measured zone curvature retained independently for one angle triplet."""
    lower_angle_deg: float
    center_angle_deg: float
    upper_angle_deg: float
    zone_count: int
    maximum_abs_force_curvature: ZoneMechanicalCurvature
    maximum_abs_displacement_curvature: ZoneMechanicalCurvature
    maximum_abs_phase_curvature: ZoneMechanicalCurvature
    maximum_abs_temperature_curvature: ZoneMechanicalCurvature


@dataclass(frozen=True, slots=True)
class ActuationMechanicalCurvatureEnvelope:
    source_parameter_sha256: str
    source_sweep_sha256: str
    triplet_count: int
    curvatures: tuple[ZoneMechanicalCurvature, ...]
    per_zone_extrema: tuple[ZoneMechanicalCurvatureExtrema, ...]
    angle_triplet_extrema: tuple[AngleTripletCurvatureExtrema, ...]
    maximum_abs_force_curvature: ZoneMechanicalCurvature
    maximum_abs_displacement_curvature: ZoneMechanicalCurvature
    maximum_abs_phase_curvature: ZoneMechanicalCurvature
    maximum_abs_temperature_curvature: ZoneMechanicalCurvature


def _curvature(lower: ZoneMechanicalSensitivity, upper: ZoneMechanicalSensitivity) -> ZoneMechanicalCurvature:
    if lower.zone_id != upper.zone_id or lower.upper_record_id != upper.lower_record_id:
        raise ActuationParameterError("Mechanical curvature requires consecutive intervals from one actuator zone")
    if lower.upper_angle_deg != upper.lower_angle_deg:
        raise ActuationParameterError("Mechanical curvature intervals must share the same measured center angle")
    lower_center = 0.5 * (lower.lower_angle_deg + lower.upper_angle_deg)
    upper_center = 0.5 * (upper.lower_angle_deg + upper.upper_angle_deg)
    center_delta = upper_center - lower_center
    if center_delta <= 0.0:
        raise ActuationParameterError("Mechanical curvature requires increasing interval centers")
    force_change = upper.force_slope_N_per_deg - lower.force_slope_N_per_deg
    displacement_change = upper.displacement_slope_mm_per_deg - lower.displacement_slope_mm_per_deg
    phase_change = upper.phase_slope_deg_per_deg - lower.phase_slope_deg_per_deg
    temperature_change = upper.temperature_slope_C_per_deg - lower.temperature_slope_C_per_deg
    return ZoneMechanicalCurvature(
        zone_id=lower.zone_id,
        lower_angle_deg=lower.lower_angle_deg,
        center_angle_deg=lower.upper_angle_deg,
        upper_angle_deg=upper.upper_angle_deg,
        lower_record_id=lower.lower_record_id,
        center_record_id=lower.upper_record_id,
        upper_record_id=upper.upper_record_id,
        interval_center_delta_deg=center_delta,
        force_slope_change_N_per_deg=force_change,
        force_curvature_N_per_deg2=force_change / center_delta,
        displacement_slope_change_mm_per_deg=displacement_change,
        displacement_curvature_mm_per_deg2=displacement_change / center_delta,
        phase_slope_change_deg_per_deg=phase_change,
        phase_curvature_deg_per_deg2=phase_change / center_delta,
        temperature_slope_change_C_per_deg=temperature_change,
        temperature_curvature_C_per_deg2=temperature_change / center_delta,
    )


def _canonical(item: ZoneMechanicalCurvature) -> tuple[str, float, float, float, str, str, str]:
    return (
        item.zone_id, item.lower_angle_deg, item.center_angle_deg, item.upper_angle_deg,
        item.lower_record_id, item.center_record_id, item.upper_record_id,
    )


def _maximum(items: tuple[ZoneMechanicalCurvature, ...], attribute: str) -> ZoneMechanicalCurvature:
    return max(items, key=lambda item: (abs(getattr(item, attribute)), _canonical(item)))


def _zone_extrema(items: tuple[ZoneMechanicalCurvature, ...]) -> tuple[ZoneMechanicalCurvatureExtrema, ...]:
    by_zone: dict[str, list[ZoneMechanicalCurvature]] = {}
    for item in items:
        by_zone.setdefault(item.zone_id, []).append(item)
    return tuple(
        ZoneMechanicalCurvatureExtrema(
            zone_id=zone_id,
            maximum_abs_force_curvature=_maximum(tuple(by_zone[zone_id]), "force_curvature_N_per_deg2"),
            maximum_abs_displacement_curvature=_maximum(tuple(by_zone[zone_id]), "displacement_curvature_mm_per_deg2"),
            maximum_abs_phase_curvature=_maximum(tuple(by_zone[zone_id]), "phase_curvature_deg_per_deg2"),
            maximum_abs_temperature_curvature=_maximum(tuple(by_zone[zone_id]), "temperature_curvature_C_per_deg2"),
        )
        for zone_id in sorted(by_zone)
    )


def _angle_triplet_extrema(items: tuple[ZoneMechanicalCurvature, ...]) -> tuple[AngleTripletCurvatureExtrema, ...]:
    by_triplet: dict[tuple[float, float, float], list[ZoneMechanicalCurvature]] = {}
    for item in items:
        key = (item.lower_angle_deg, item.center_angle_deg, item.upper_angle_deg)
        by_triplet.setdefault(key, []).append(item)
    extrema: list[AngleTripletCurvatureExtrema] = []
    for key in sorted(by_triplet):
        triplet = tuple(by_triplet[key])
        zone_ids = {item.zone_id for item in triplet}
        if len(zone_ids) != 4 or len(triplet) != 4:
            raise ActuationParameterError(
                f"Mechanical curvature angle triplet {key} requires exactly four controlled zones"
            )
        extrema.append(AngleTripletCurvatureExtrema(
            lower_angle_deg=key[0], center_angle_deg=key[1], upper_angle_deg=key[2], zone_count=len(zone_ids),
            maximum_abs_force_curvature=_maximum(triplet, "force_curvature_N_per_deg2"),
            maximum_abs_displacement_curvature=_maximum(triplet, "displacement_curvature_mm_per_deg2"),
            maximum_abs_phase_curvature=_maximum(triplet, "phase_curvature_deg_per_deg2"),
            maximum_abs_temperature_curvature=_maximum(triplet, "temperature_curvature_C_per_deg2"),
        ))
    return tuple(extrema)


def reduce_measured_mechanical_curvature(
    sweep: FourZoneImpedanceSweep,
    parameters: ActuationParameterSet,
) -> ActuationMechanicalCurvatureEnvelope:
    """Locate nonlinear carrier-angle regions using only validated measured evidence."""
    sensitivity = reduce_measured_mechanical_sensitivity(sweep, parameters)
    by_zone: dict[str, list[ZoneMechanicalSensitivity]] = {}
    for item in sensitivity.sensitivities:
        by_zone.setdefault(item.zone_id, []).append(item)

    curvatures: list[ZoneMechanicalCurvature] = []
    for zone_id in sorted(by_zone):
        intervals = sorted(by_zone[zone_id], key=lambda item: (item.lower_angle_deg, item.upper_angle_deg, item.lower_record_id))
        if len(intervals) < 2:
            raise ActuationParameterError(f"Mechanical curvature requires at least three measured carrier angles for {zone_id}")
        curvatures.extend(_curvature(lower, upper) for lower, upper in zip(intervals, intervals[1:]))

    result = tuple(curvatures)
    if not result:
        raise ActuationParameterError("Mechanical curvature requires measured three-point carrier-angle evidence")
    return ActuationMechanicalCurvatureEnvelope(
        source_parameter_sha256=sensitivity.source_parameter_sha256,
        source_sweep_sha256=sensitivity.source_sweep_sha256,
        triplet_count=len(result),
        curvatures=result,
        per_zone_extrema=_zone_extrema(result),
        angle_triplet_extrema=_angle_triplet_extrema(result),
        maximum_abs_force_curvature=_maximum(result, "force_curvature_N_per_deg2"),
        maximum_abs_displacement_curvature=_maximum(result, "displacement_curvature_mm_per_deg2"),
        maximum_abs_phase_curvature=_maximum(result, "phase_curvature_deg_per_deg2"),
        maximum_abs_temperature_curvature=_maximum(result, "temperature_curvature_C_per_deg2"),
    )
