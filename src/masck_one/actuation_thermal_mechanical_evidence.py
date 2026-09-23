"""Consumption-time integrity checks for coupled massage/thermal evidence."""
from __future__ import annotations

from .actuation_parameters import ActuationParameterError, ActuationParameterSet
from .actuation_thermal_mechanical_coupling import (
    ActuationThermalMechanicalCoupling,
    reduce_measured_thermal_mechanical_coupling,
)
from .actuation_zone_sweep import FourZoneImpedanceSweep


def validate_thermal_mechanical_coupling_evidence(
    coupling: ActuationThermalMechanicalCoupling,
    sweep: FourZoneImpedanceSweep,
    parameters: ActuationParameterSet,
) -> None:
    """Fail closed unless a reduced coexistence result still matches its source sweep.

    The reducer output is immutable by convention, but frozen dataclasses can still be
    modified through low-level mutation. Recomputing from the authority-bound measured
    sweep at a consumption boundary prevents stale or altered extrema, margins, and
    zone/angle attribution from being treated as valid coexistence evidence.
    """
    if type(coupling) is not ActuationThermalMechanicalCoupling:
        raise ActuationParameterError(
            "Thermal/mechanical evidence requires exact ActuationThermalMechanicalCoupling"
        )
    if type(sweep) is not FourZoneImpedanceSweep:
        raise ActuationParameterError(
            "Thermal/mechanical evidence requires exact FourZoneImpedanceSweep source evidence"
        )
    if type(parameters) is not ActuationParameterSet:
        raise ActuationParameterError(
            "Thermal/mechanical evidence requires exact ActuationParameterSet authority"
        )

    expected = reduce_measured_thermal_mechanical_coupling(sweep, parameters)
    if coupling != expected:
        raise ActuationParameterError(
            "Thermal/mechanical coupling evidence does not match the current measured sweep reduction"
        )
