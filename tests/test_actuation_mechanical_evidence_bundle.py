from dataclasses import replace

import pytest

from masck_one.actuation_mechanical_evidence_bundle import (
    build_measured_massage_mechanics_evidence_bundle,
    validate_measured_massage_mechanics_evidence_bundle,
)
from masck_one.actuation_parameters import ActuationParameterError
from masck_one.actuation_zone_sweep import FourZoneImpedanceSweep
from tests.test_actuation_zone_system_response import _parameters, _sweep


def test_accepts_atomic_current_mechanics_bundle():
    parameters = _parameters()
    sweep = _sweep(parameters)
    evidence = build_measured_massage_mechanics_evidence_bundle(sweep, parameters)
    assert evidence.source_parameter_sha256 == parameters.parameter_sha256
    assert evidence.source_sweep_sha256 == sweep.sweep_sha256
    assert validate_measured_massage_mechanics_evidence_bundle(sweep, parameters, evidence) is evidence


def test_rejects_forged_parameter_provenance_before_consuming_nested_views():
    parameters = _parameters()
    sweep = _sweep(parameters)
    evidence = build_measured_massage_mechanics_evidence_bundle(sweep, parameters)
    forged = replace(evidence, source_parameter_sha256="0" * 64)

    with pytest.raises(ActuationParameterError, match="current actuation parameter set"):
        validate_measured_massage_mechanics_evidence_bundle(sweep, parameters, forged)


def test_rejects_forged_sweep_provenance_before_consuming_nested_views():
    parameters = _parameters()
    sweep = _sweep(parameters)
    evidence = build_measured_massage_mechanics_evidence_bundle(sweep, parameters)
    forged = replace(evidence, source_sweep_sha256="0" * 64)

    with pytest.raises(ActuationParameterError, match="current four-zone sweep"):
        validate_measured_massage_mechanics_evidence_bundle(sweep, parameters, forged)


def test_rejects_response_from_different_measurement_capture_with_same_extrema():
    parameters = _parameters()
    sweep = _sweep(parameters)
    evidence = build_measured_massage_mechanics_evidence_bundle(sweep, parameters)
    records = list(sweep.records)
    records[0] = replace(records[0], record=replace(records[0].record, record_id="BUNDLE-NEW-CAPTURE"))
    changed = FourZoneImpedanceSweep(parameters.parameter_sha256, tuple(records))

    assert changed.measured_system_response(parameters) == sweep.measured_system_response(parameters)
    with pytest.raises(ActuationParameterError, match="current four-zone sweep"):
        validate_measured_massage_mechanics_evidence_bundle(changed, parameters, evidence)


def test_rejects_mixed_sensitivity_view():
    parameters = _parameters()
    sweep = _sweep(parameters)
    evidence = build_measured_massage_mechanics_evidence_bundle(sweep, parameters)
    worst = evidence.sensitivity.maximum_abs_force_sensitivity
    stale_sensitivity = replace(
        evidence.sensitivity,
        maximum_abs_force_sensitivity=replace(worst, force_slope_N_per_deg=worst.force_slope_N_per_deg + 0.001),
    )
    mixed = replace(evidence, sensitivity=stale_sensitivity)
    with pytest.raises(ActuationParameterError, match="stale or disagrees"):
        validate_measured_massage_mechanics_evidence_bundle(sweep, parameters, mixed)


def test_rejects_mixed_curvature_view():
    parameters = _parameters()
    sweep = _sweep(parameters)
    evidence = build_measured_massage_mechanics_evidence_bundle(sweep, parameters)
    worst = evidence.curvature.maximum_abs_force_curvature
    stale_curvature = replace(
        evidence.curvature,
        maximum_abs_force_curvature=replace(worst, force_curvature_N_per_deg2=worst.force_curvature_N_per_deg2 + 0.001),
    )
    mixed = replace(evidence, curvature=stale_curvature)
    with pytest.raises(ActuationParameterError, match="stale or disagrees"):
        validate_measured_massage_mechanics_evidence_bundle(sweep, parameters, mixed)


def test_rejects_wrong_bundle_type():
    parameters = _parameters()
    with pytest.raises(TypeError, match="exact MeasuredMassageMechanicsEvidenceBundle"):
        validate_measured_massage_mechanics_evidence_bundle(_sweep(parameters), parameters, object())
