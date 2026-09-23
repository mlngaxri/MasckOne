"""Consumption-time integrity checks for measured actuation thermal evidence."""
from __future__ import annotations

from .actuation_parameters import ActuationParameterError, ActuationParameterSet
from .actuation_thermal_coexistence import (
    ActuationThermalEnvelope,
    reduce_measured_actuation_thermal_envelope,
)
from .actuation_zone_sweep import FourZoneImpedanceSweep


def validate_actuation_thermal_envelope_evidence(
    envelope: ActuationThermalEnvelope,
    sweep: FourZoneImpedanceSweep,
    parameters: ActuationParameterSet,
) -> None:
    """Fail closed unless thermal evidence still matches its measured source sweep.

    The reduction is immutable by convention, but frozen dataclasses and their source
    authority can still be altered through low-level mutation. Revalidating authority
    and recomputing the complete envelope prevents stale or altered temperature extrema,
    cross-zone spreads, angle sensitivities, and provenance from being consumed as
    current massage/thermal coexistence evidence.
    """
    if type(envelope) is not ActuationThermalEnvelope:
        raise ActuationParameterError(
            "Actuation thermal evidence requires exact ActuationThermalEnvelope"
        )
    if type(sweep) is not FourZoneImpedanceSweep:
        raise ActuationParameterError(
            "Actuation thermal evidence requires exact FourZoneImpedanceSweep source evidence"
        )
    if type(parameters) is not ActuationParameterSet:
        raise ActuationParameterError(
            "Actuation thermal evidence requires exact ActuationParameterSet authority"
        )

    parameters.__post_init__()
    expected = reduce_measured_actuation_thermal_envelope(sweep, parameters)
    if envelope != expected:
        raise ActuationParameterError(
            "Actuation thermal envelope evidence does not match the current measured sweep reduction"
        )
