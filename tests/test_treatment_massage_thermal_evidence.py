from dataclasses import replace

import pytest

from masck_one.actuation_parameters import ActuationParameterError
from masck_one.treatment_massage_thermal_evidence import (
    build_treatment_massage_thermal_evidence,
    validate_treatment_massage_thermal_evidence,
)
from tests.test_actuation_zone_system_response import _parameters, _sweep


def test_accepts_current_atomic_treatment_evidence():
    parameters = _parameters()
    sweep = _sweep(parameters)
    evidence = build_treatment_massage_thermal_evidence(sweep, parameters)
    assert validate_treatment_massage_thermal_evidence(sweep, parameters, evidence) is evidence


def test_rejects_mixed_mechanics_view():
    parameters = _parameters()
    sweep = _sweep(parameters)
    evidence = build_treatment_massage_thermal_evidence(sweep, parameters)
    worst = evidence.mechanics.sensitivity.maximum_abs_force_sensitivity
    stale_sensitivity = replace(
        evidence.mechanics.sensitivity,
        maximum_abs_force_sensitivity=replace(
            worst, force_slope_N_per_deg=worst.force_slope_N_per_deg + 0.001
        ),
    )
    mixed = replace(
        evidence,
        mechanics=replace(evidence.mechanics, sensitivity=stale_sensitivity),
    )
    with pytest.raises(ActuationParameterError):
        validate_treatment_massage_thermal_evidence(sweep, parameters, mixed)


def test_rejects_mixed_thermal_view():
    parameters = _parameters()
    sweep = _sweep(parameters)
    evidence = build_treatment_massage_thermal_evidence(sweep, parameters)
    mixed = replace(
        evidence,
        thermal=replace(evidence.thermal, max_temperature_C=evidence.thermal.max_temperature_C + 0.1),
    )
    with pytest.raises(ActuationParameterError):
        validate_treatment_massage_thermal_evidence(sweep, parameters, mixed)


def test_rejects_mixed_coupling_view():
    parameters = _parameters()
    sweep = _sweep(parameters)
    evidence = build_treatment_massage_thermal_evidence(sweep, parameters)
    mixed = replace(
        evidence,
        coupling=replace(
            evidence.coupling,
            hottest_point=replace(
                evidence.coupling.hottest_point,
                temperature_C=evidence.coupling.hottest_point.temperature_C + 0.1,
            ),
        ),
    )
    with pytest.raises(ActuationParameterError):
        validate_treatment_massage_thermal_evidence(sweep, parameters, mixed)


def test_rejects_wrong_treatment_evidence_type():
    parameters = _parameters()
    with pytest.raises(TypeError, match="exact TreatmentMassageThermalEvidence"):
        validate_treatment_massage_thermal_evidence(_sweep(parameters), parameters, object())
