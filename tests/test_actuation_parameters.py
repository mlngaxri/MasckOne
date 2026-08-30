from dataclasses import replace
from functools import lru_cache

import pytest

from masck_one.actuation_parameters import (
    ActuationParameterError,
    ImpedanceTestRecord,
    build_actuation_parameter_set,
)
from masck_one.actuation_sweep_contract import build_actuation_displacement_contract
from masck_one.actuator_coupling import build_actuator_coupling_architecture
from masck_one.actuator_frames import build_actuator_frame_architecture
from masck_one.boundary_release import build_verified_interface_boundary_topology
from masck_one.interface_attachment import build_interface_attachment_architecture
from masck_one.model import build_model
from masck_one.structural_frame import build_structural_frame_topology


@lru_cache(maxsize=1)
def _inputs():
    model = build_model()
    boundaries = build_verified_interface_boundary_topology(model.authority, model.facial_surface, model.coverage_mesh, model.compliant_interface_topology)
    attachment = build_interface_attachment_architecture(model.authority, boundaries)
    frame = build_structural_frame_topology(model.authority, attachment)
    actuators = build_actuator_frame_architecture(model.authority, frame)
    displacement = build_actuation_displacement_contract(model.authority, actuators)
    coupling = build_actuator_coupling_architecture(model.authority, actuators, displacement, frame, model.compliant_interface_topology)
    parameters = build_actuation_parameter_set(model.authority, actuators, displacement, coupling)
    return model, actuators, displacement, coupling, parameters


def test_parameter_set_is_exactly_authority_bound_and_does_not_invent_frequency_doe():
    model, actuators, displacement, coupling, parameters = _inputs()
    assert parameters.clean_frequency_baseline_hz == 40.0
    assert parameters.displacement_pp_baseline_mm == 0.52
    assert parameters.axis_angle_doe_deg == (50.0, 55.0, 61.0, 67.0, 72.0)
    assert parameters.frequency_sensitivity_points_hz is None
    assert parameters.physical_validation_eligible is False
    parameters.validate_current_sources(authority=model.authority, actuator_architecture=actuators, displacement_contract=displacement, coupling_architecture=coupling)


def test_frequency_doe_cannot_be_invented():
    *_, parameters = _inputs()
    with pytest.raises(ActuationParameterError, match="frequency DOE"):
        replace(parameters, frequency_sensitivity_points_hz=(20.0, 40.0, 80.0))


def test_stale_coupling_and_wrong_peak_to_peak_value_fail_closed():
    model, actuators, displacement, coupling, parameters = _inputs()
    stale = replace(parameters, source_coupling_architecture_sha256="0" * 64)
    with pytest.raises(ActuationParameterError, match="stale for the coupling"):
        stale.validate_current_sources(authority=model.authority, actuator_architecture=actuators, displacement_contract=displacement, coupling_architecture=coupling)
    wrong = replace(parameters, displacement_pp_baseline_mm=0.26)
    with pytest.raises(ActuationParameterError, match="no longer matches machine authority"):
        wrong.validate_current_sources(authority=model.authority, actuator_architecture=actuators, displacement_contract=displacement, coupling_architecture=coupling)


def test_predicted_impedance_record_cannot_contain_measured_evidence():
    *_, parameters = _inputs()
    with pytest.raises(ActuationParameterError, match="masquerade as measured"):
        ImpedanceTestRecord(
            record_id="IMP-PRED-001",
            source_parameter_sha256=parameters.parameter_sha256,
            specimen_id="SYNTHETIC-NO-SPECIMEN",
            source_kind="PREDICTED",
            frequency_hz=40.0,
            commanded_displacement_pp_mm=0.52,
            axis_angle_deg=61.0,
            measured_force_N=0.2,
        )


def test_measured_impedance_record_requires_complete_observations_and_provenance():
    *_, parameters = _inputs()
    with pytest.raises(ActuationParameterError, match="require force"):
        ImpedanceTestRecord(
            record_id="IMP-MEAS-001",
            source_parameter_sha256=parameters.parameter_sha256,
            specimen_id="COUPON-001",
            source_kind="MEASURED",
            frequency_hz=40.0,
            commanded_displacement_pp_mm=0.52,
            axis_angle_deg=61.0,
        )
    record = ImpedanceTestRecord(
        record_id="IMP-MEAS-002",
        source_parameter_sha256=parameters.parameter_sha256,
        specimen_id="COUPON-001",
        source_kind="MEASURED",
        frequency_hz=40.0,
        commanded_displacement_pp_mm=0.52,
        axis_angle_deg=61.0,
        measured_force_N=0.21,
        measured_displacement_pp_mm=0.49,
        measured_phase_deg=14.0,
        measured_temperature_C=24.0,
        evidence_uri="evidence://bench/impedance/COUPON-001/run-002",
    )
    assert record.source_kind == "MEASURED"


def test_noncanonical_hash_and_physical_evidence_promotion_are_rejected():
    *_, parameters = _inputs()
    with pytest.raises(ActuationParameterError, match="canonical lowercase"):
        replace(parameters, source_actuator_architecture_sha256="A" * 64)
    with pytest.raises(ActuationParameterError, match="cannot be physical validation"):
        replace(parameters, physical_validation_eligible=True)
