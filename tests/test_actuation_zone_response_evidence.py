from dataclasses import replace

import pytest

from masck_one.actuation_parameters import ActuationParameterError
from masck_one.actuation_zone_response_evidence import (
    MeasuredActuationResponseEvidence,
    build_measured_actuation_response_evidence,
    validate_measured_actuation_response_evidence,
)
from masck_one.actuation_zone_sweep import FourZoneImpedanceSweep
from tests.test_actuation_zone_system_response import _parameters, _sweep


def test_accepts_current_measured_response_evidence():
    parameters = _parameters()
    sweep = _sweep(parameters)
    evidence = build_measured_actuation_response_evidence(sweep, parameters)
    assert validate_measured_actuation_response_evidence(sweep, parameters, evidence) is evidence


def test_rejects_mutated_system_response():
    parameters = _parameters()
    sweep = _sweep(parameters)
    evidence = build_measured_actuation_response_evidence(sweep, parameters)
    stale = replace(
        evidence,
        system_response=replace(evidence.system_response, min_force_N=evidence.system_response.min_force_N + 0.01),
    )
    with pytest.raises(ActuationParameterError, match="stale or disagrees"):
        validate_measured_actuation_response_evidence(sweep, parameters, stale)


def test_rejects_different_sweep_even_when_numeric_reduction_is_identical():
    parameters = _parameters()
    sweep = _sweep(parameters)
    evidence = build_measured_actuation_response_evidence(sweep, parameters)
    records = list(sweep.records)
    records[0] = replace(records[0], record=replace(records[0].record, record_id="SYS-REPEAT-NEW-ID"))
    changed = FourZoneImpedanceSweep(parameters.parameter_sha256, tuple(records))

    # The engineering extrema are intentionally identical. Provenance still changed.
    assert changed.measured_response_by_zone(parameters) == sweep.measured_response_by_zone(parameters)
    assert changed.measured_system_response(parameters) == sweep.measured_system_response(parameters)
    assert changed.sweep_sha256 != sweep.sweep_sha256
    with pytest.raises(ActuationParameterError, match="stale or disagrees"):
        validate_measured_actuation_response_evidence(changed, parameters, evidence)


def test_rejects_mutated_zone_response():
    parameters = _parameters()
    sweep = _sweep(parameters)
    evidence = build_measured_actuation_response_evidence(sweep, parameters)
    zones = list(evidence.zone_responses)
    zones[0] = replace(zones[0], max_force_N=zones[0].max_force_N + 0.01)
    stale = replace(evidence, zone_responses=tuple(zones))
    with pytest.raises(ActuationParameterError, match="stale or disagrees"):
        validate_measured_actuation_response_evidence(sweep, parameters, stale)


def test_rejects_wrong_evidence_type():
    parameters = _parameters()
    with pytest.raises(TypeError, match="exact MeasuredActuationResponseEvidence"):
        validate_measured_actuation_response_evidence(_sweep(parameters), parameters, object())
