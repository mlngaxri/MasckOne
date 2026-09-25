from dataclasses import replace

import pytest

from masck_one.actuation_mechanical_reversal import reduce_measured_mechanical_reversals
from masck_one.actuation_mechanical_reversal_evidence import validate_mechanical_reversal_evidence
from masck_one.actuation_parameters import ActuationParameterError
from tests.test_actuation_mechanical_reversal import _parameters, _sweep


def test_accepts_current_reversal_evidence():
    parameters = _parameters()
    sweep = _sweep(parameters)
    evidence = reduce_measured_mechanical_reversals(sweep, parameters)
    assert validate_mechanical_reversal_evidence(sweep, parameters, evidence) is evidence


def test_rejects_mutated_reversal_classification():
    parameters = _parameters()
    sweep = _sweep(parameters)
    evidence = reduce_measured_mechanical_reversals(sweep, parameters)
    first = evidence.reversals[0]
    stale = replace(
        evidence,
        reversals=(replace(first, force_reversal=not first.force_reversal),) + evidence.reversals[1:],
    )
    with pytest.raises(ActuationParameterError, match="stale or disagrees"):
        validate_mechanical_reversal_evidence(sweep, parameters, stale)


def test_rejects_evidence_from_different_measured_sweep():
    parameters = _parameters()
    sweep = _sweep(parameters)
    records = list(sweep.records)
    records[0] = replace(
        records[0],
        record=replace(records[0].record, measured_force_N=records[0].record.measured_force_N + 0.01),
    )
    changed = type(sweep)(parameters.parameter_sha256, tuple(records))
    evidence = reduce_measured_mechanical_reversals(sweep, parameters)
    with pytest.raises(ActuationParameterError, match="stale or disagrees"):
        validate_mechanical_reversal_evidence(changed, parameters, evidence)


def test_rejects_wrong_evidence_type():
    parameters = _parameters()
    with pytest.raises(TypeError, match="ActuationMechanicalReversalEnvelope"):
        validate_mechanical_reversal_evidence(_sweep(parameters), parameters, object())
