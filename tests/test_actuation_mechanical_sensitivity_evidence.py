from dataclasses import replace

import pytest

from masck_one.actuation_mechanical_sensitivity import reduce_measured_mechanical_sensitivity
from masck_one.actuation_mechanical_sensitivity_evidence import validate_mechanical_sensitivity_evidence
from masck_one.actuation_parameters import ActuationParameterError
from tests.test_actuation_mechanical_sensitivity import _parameters, _sweep


def test_accepts_current_sensitivity_evidence():
    parameters = _parameters()
    sweep = _sweep(parameters)
    evidence = reduce_measured_mechanical_sensitivity(sweep, parameters)
    assert validate_mechanical_sensitivity_evidence(sweep, parameters, evidence) is evidence


def test_rejects_mutated_sensitivity_extremum():
    parameters = _parameters()
    sweep = _sweep(parameters)
    evidence = reduce_measured_mechanical_sensitivity(sweep, parameters)
    stale = replace(
        evidence,
        maximum_abs_force_sensitivity=replace(
            evidence.maximum_abs_force_sensitivity,
            force_slope_N_per_deg=evidence.maximum_abs_force_sensitivity.force_slope_N_per_deg + 1.0,
        ),
    )
    with pytest.raises(ActuationParameterError, match="stale or disagrees"):
        validate_mechanical_sensitivity_evidence(sweep, parameters, stale)


def test_rejects_evidence_from_different_measured_sweep():
    parameters = _parameters()
    sweep = _sweep(parameters)
    records = list(sweep.records)
    records[0] = replace(
        records[0],
        record=replace(records[0].record, measured_force_N=records[0].record.measured_force_N + 0.01),
    )
    changed = type(sweep)(parameters.parameter_sha256, tuple(records))
    evidence = reduce_measured_mechanical_sensitivity(sweep, parameters)
    with pytest.raises(ActuationParameterError, match="stale or disagrees"):
        validate_mechanical_sensitivity_evidence(changed, parameters, evidence)


def test_rejects_wrong_evidence_type():
    parameters = _parameters()
    with pytest.raises(TypeError, match="ActuationMechanicalSensitivityEnvelope"):
        validate_mechanical_sensitivity_evidence(_sweep(parameters), parameters, object())
