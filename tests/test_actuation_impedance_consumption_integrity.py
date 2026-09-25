import pytest

from masck_one.actuation_parameters import ActuationParameterError, ImpedanceTestRecord, build_actuation_parameter_set
from masck_one.actuation_sweep_contract import build_actuation_displacement_contract
from masck_one.actuator_coupling import build_actuator_coupling_architecture
from masck_one.actuator_frames import build_actuator_frame_architecture
from masck_one.boundary_release import build_verified_interface_boundary_topology
from masck_one.interface_attachment import build_interface_attachment_architecture
from masck_one.model import build_model
from masck_one.structural_frame import build_structural_frame_topology


def _parameters():
    model = build_model()
    boundaries = build_verified_interface_boundary_topology(
        model.authority, model.facial_surface, model.coverage_mesh, model.compliant_interface_topology
    )
    attachment = build_interface_attachment_architecture(model.authority, boundaries)
    frame = build_structural_frame_topology(model.authority, attachment)
    actuators = build_actuator_frame_architecture(model.authority, frame)
    displacement = build_actuation_displacement_contract(model.authority, actuators)
    coupling = build_actuator_coupling_architecture(
        model.authority, actuators, displacement, frame, model.compliant_interface_topology
    )
    return build_actuation_parameter_set(model.authority, actuators, displacement, coupling)


def _measured(parameters):
    return ImpedanceTestRecord(
        record_id="IMP-MEAS-CONSUME-001",
        source_parameter_sha256=parameters.parameter_sha256,
        specimen_id="COUPON-001",
        source_kind="MEASURED",
        frequency_hz=parameters.clean_frequency_baseline_hz,
        commanded_displacement_pp_mm=parameters.displacement_pp_baseline_mm,
        axis_angle_deg=parameters.axis_angle_baseline_deg,
        measured_force_N=0.21,
        measured_displacement_pp_mm=0.49,
        measured_phase_deg=14.0,
        measured_temperature_C=24.0,
        evidence_uri="evidence://bench/impedance/COUPON-001/run-consume-001",
    )


def test_command_envelope_revalidates_measured_values_after_low_level_mutation():
    parameters = _parameters()
    record = _measured(parameters)
    object.__setattr__(record, "measured_force_N", float("nan"))

    with pytest.raises(ActuationParameterError, match="measured force"):
        record.validate_command_envelope(parameters)


def test_command_envelope_revalidates_measured_provenance_after_low_level_mutation():
    parameters = _parameters()
    record = _measured(parameters)
    object.__setattr__(record, "evidence_uri", None)

    with pytest.raises(ActuationParameterError, match="require evidence provenance"):
        record.validate_command_envelope(parameters)


def test_command_envelope_rejects_predicted_record_mutated_to_carry_measurements():
    parameters = _parameters()
    record = ImpedanceTestRecord(
        record_id="IMP-PRED-CONSUME-001",
        source_parameter_sha256=parameters.parameter_sha256,
        specimen_id="SYNTHETIC-NO-SPECIMEN",
        source_kind="PREDICTED",
        frequency_hz=parameters.clean_frequency_baseline_hz,
        commanded_displacement_pp_mm=parameters.displacement_pp_baseline_mm,
        axis_angle_deg=parameters.axis_angle_baseline_deg,
    )
    object.__setattr__(record, "measured_force_N", 0.21)

    with pytest.raises(ActuationParameterError, match="masquerade as measured"):
        record.validate_command_envelope(parameters)
