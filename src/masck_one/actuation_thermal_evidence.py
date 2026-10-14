"""Consumption-time integrity checks for measured actuation thermal evidence."""
from __future__ import annotations

from .actuation_parameters import ActuationParameterError, ActuationParameterSet
from .actuation_thermal_coexistence import (
    ActuationThermalEnvelope,
    reduce_measured_actuation_thermal_envelope,
)
from .actuation_thermal_mechanical_coupling import ActuationThermalMechanicalCoupling
from .actuation_thermal_mechanical_evidence import validate_thermal_mechanical_coupling_evidence
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


def validate_paired_thermal_mechanical_evidence(
    envelope: ActuationThermalEnvelope,
    coupling: ActuationThermalMechanicalCoupling,
    sweep: FourZoneImpedanceSweep,
    parameters: ActuationParameterSet,
) -> None:
    """Fail closed unless thermal and mechanical views are current and mutually coherent.

    Treatment integration may consume the standalone thermal envelope beside the coupled
    massage/thermal reduction. Both must therefore describe the same measured sweep, not
    merely be individually plausible artifacts produced at different times. Each side is
    validated through its own consumption boundary before shared extrema are compared, so
    future strengthening of either evidence contract is inherited here automatically.
    """
    validate_actuation_thermal_envelope_evidence(envelope, sweep, parameters)
    validate_thermal_mechanical_coupling_evidence(coupling, sweep, parameters)

    if (
        envelope.point_count != coupling.point_count
        or envelope.max_temperature_C != coupling.hottest_point.temperature_C
        or envelope.max_temperature_zone_id != coupling.hottest_point.zone_id
        or envelope.max_temperature_axis_angle_deg != coupling.hottest_point.axis_angle_deg
        or envelope.max_temperature_record_id != coupling.hottest_point.record_id
    ):
        raise ActuationParameterError(
            "Paired thermal and mechanical reductions disagree on shared measured thermal evidence"
        )
