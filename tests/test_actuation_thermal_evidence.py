from dataclasses import replace

import pytest

from masck_one.actuation_parameters import ActuationParameterError, ImpedanceTestRecord, build_actuation_parameter_set
from masck_one.actuation_sweep_contract import build_actuation_displacement_contract
from masck_one.actuation_thermal_coexistence import reduce_measured_actuation_thermal_envelope
from masck_one.actuation_thermal_evidence import validate_actuation_thermal_envelope_evidence
from masck_one.actuation_zone_sweep import FourZoneImpedanceSweep, ZoneImpedanceRecord
from masck_one.actuator_coupling import build_actuator_coupling_architecture
from masck_one.actuator_frames import ZONE_IDS, build_actuator_frame_architecture
from masck_one.boundary_release import build_verified_interface_boundary_topology
from masck_one.interface_attachment import build_interface_attachment_architecture
from masck_one.model import build_model
from masck_one.structural_frame import build_structural_frame_topology


def _parameters():
    model = build_model()
    boundaries = build_verified_interface_boundary_topology(model.authority, model.facial_surface, model.coverage_mesh, model.compliant_interface_topology)
    attachment = build_interface_attachment_architecture(model.authority, boundaries)
    frame = build_structural_frame_topology(model.authority, attachment)
    actuators = build_actuator_frame_architecture(model.authority, frame)
    displacement = build_actuation_displacement_contract(model.authority, actuators)
    coupling = build_actuator_coupling_architecture(model.authority, actuators, displacement, frame, model.compliant_interface_topology)
    return build_actuation_parameter_set(model.authority, actuators, displacement, coupling)


def _sweep(parameters):
    records = []
    for zone_index, zone_id in enumerate(ZONE_IDS):
        for angle_index, angle in enumerate(parameters.axis_angle_doe_deg):
            records.append(ZoneImpedanceRecord(zone_id, ImpedanceTestRecord(
                record_id=f"THERMAL-{zone_id}-{angle:g}",
                source_parameter_sha256=parameters.parameter_sha256,
                specimen_id="THERMAL-EVIDENCE",
                source_kind="MEASURED",
                frequency_hz=parameters.clean_frequency_baseline_hz,
                commanded_displacement_pp_mm=parameters.displacement_pp_baseline_mm,
                axis_angle_deg=angle,
                measured_force_N=0.30 + zone_index * 0.01,
                measured_displacement_pp_mm=parameters.displacement_pp_baseline_mm,
                measured_phase_deg=0.0,
                measured_temperature_C=28.0 + zone_index + angle_index * 0.25,
                evidence_uri=f"evidence://bench/thermal/{zone_id}/{angle:g}",
            )))
    return FourZoneImpedanceSweep(parameters.parameter_sha256, tuple(records))


def test_current_thermal_envelope_is_accepted():
    parameters = _parameters()
    sweep = _sweep(parameters)
    envelope = reduce_measured_actuation_thermal_envelope(sweep, parameters)
    validate_actuation_thermal_envelope_evidence(envelope, sweep, parameters)


def test_mutated_thermal_envelope_is_rejected():
    parameters = _parameters()
    sweep = _sweep(parameters)
    envelope = reduce_measured_actuation_thermal_envelope(sweep, parameters)
    corrupted = replace(envelope, max_temperature_C=envelope.max_temperature_C + 1.0)
    with pytest.raises(ActuationParameterError, match="does not match"):
        validate_actuation_thermal_envelope_evidence(corrupted, sweep, parameters)


def test_envelope_from_different_measured_sweep_is_rejected():
    parameters = _parameters()
    sweep = _sweep(parameters)
    envelope = reduce_measured_actuation_thermal_envelope(sweep, parameters)
    first = sweep.records[0]
    altered_record = replace(first.record, measured_temperature_C=first.record.measured_temperature_C + 0.5)
    altered = FourZoneImpedanceSweep(sweep.source_parameter_sha256, (ZoneImpedanceRecord(first.zone_id, altered_record),) + sweep.records[1:])
    with pytest.raises(ActuationParameterError, match="does not match"):
        validate_actuation_thermal_envelope_evidence(envelope, altered, parameters)


def test_corrupted_parameter_authority_is_rejected_before_reduction():
    parameters = _parameters()
    sweep = _sweep(parameters)
    envelope = reduce_measured_actuation_thermal_envelope(sweep, parameters)
    object.__setattr__(parameters, "axis_angle_doe_deg", (61.0, 61.0, 65.0))
    with pytest.raises(ActuationParameterError):
        validate_actuation_thermal_envelope_evidence(envelope, sweep, parameters)


def test_wrong_evidence_type_is_rejected():
    parameters = _parameters()
    sweep = _sweep(parameters)
    with pytest.raises(ActuationParameterError, match="exact ActuationThermalEnvelope"):
        validate_actuation_thermal_envelope_evidence(object(), sweep, parameters)
