from dataclasses import replace

import pytest

from masck_one.actuation_mechanical_curvature import reduce_measured_mechanical_curvature
from masck_one.actuation_mechanical_curvature_evidence import validate_mechanical_curvature_evidence
from masck_one.actuation_parameters import ActuationParameterError
from tests.test_actuation_mechanical_curvature import _parameters, _sweep


def test_accepts_current_curvature_evidence():
    parameters = _parameters()
    sweep = _sweep(parameters)
    evidence = reduce_measured_mechanical_curvature(sweep, parameters)
    assert validate_mechanical_curvature_evidence(sweep, parameters, evidence) is evidence


def test_rejects_mutated_curvature_extremum():
    parameters = _parameters()
    sweep = _sweep(parameters)
    evidence = reduce_measured_mechanical_curvature(sweep, parameters)
    stale = replace(
        evidence,
        maximum_abs_force_curvature=replace(
            evidence.maximum_abs_force_curvature,
            force_curvature_N_per_deg2=evidence.maximum_abs_force_curvature.force_curvature_N_per_deg2 + 1.0,
        ),
    )
    with pytest.raises(ActuationParameterError, match="stale or disagrees"):
        validate_mechanical_curvature_evidence(sweep, parameters, stale)


def test_rejects_evidence_from_different_measured_sweep():
    parameters = _parameters()
    sweep = _sweep(parameters)
    records = list(sweep.records)
    records[0] = replace(records[0], record=replace(records[0].record, measured_force_N=records[0].record.measured_force_N + 0.01))
    changed = type(sweep)(parameters.parameter_sha256, tuple(records))
    evidence = reduce_measured_mechanical_curvature(sweep, parameters)
    with pytest.raises(ActuationParameterError, match="stale or disagrees"):
        validate_mechanical_curvature_evidence(changed, parameters, evidence)


def test_rejects_wrong_evidence_type():
    parameters = _parameters()
    with pytest.raises(TypeError, match="ActuationMechanicalCurvatureEnvelope"):
        validate_mechanical_curvature_evidence(_sweep(parameters), parameters, object())
