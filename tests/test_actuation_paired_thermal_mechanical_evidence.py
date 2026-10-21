from dataclasses import replace

import pytest

from masck_one.actuation_parameters import ActuationParameterError, ImpedanceTestRecord, build_actuation_parameter_set
from masck_one.actuation_sweep_contract import build_actuation_displacement_contract
from masck_one.actuation_thermal_coexistence import reduce_measured_actuation_thermal_envelope
from masck_one.actuation_thermal_evidence import validate_paired_thermal_mechanical_evidence
from masck_one.actuation_thermal_mechanical_coupling import reduce_measured_thermal_mechanical_coupling
from masck_one.actuation_zone_sweep import FourZoneImpedanceSweep, ZoneImpedanceRecord
from masck_one.actuator_coupling import build_actuator_coupling_architecture
from masck_one.actuator_frames import ZONE_IDS, build_actuator_frame_architecture
from masck_one.boundary_release import build_verified_interface_boundary_topology
from masck_one.interface_attachment import build_interface_attachment_architecture
from masck_one.model import build_model
from masck_one.structural_frame import build_structural_frame_topology


def _evidence():
    model = build_model()
    boundaries = build_verified_interface_boundary_topology(model.authority, model.facial_surface, model.coverage_mesh, model.compliant_interface_topology)
    attachment = build_interface_attachment_architecture(model.authority, boundaries)
    frame = build_structural_frame_topology(model.authority, attachment)
    actuators = build_actuator_frame_architecture(model.authority, frame)
    displacement = build_actuation_displacement_contract(model.authority, actuators)
    architecture = build_actuator_coupling_architecture(model.authority, actuators, displacement, frame, model.compliant_interface_topology)
    parameters = build_actuation_parameter_set(model.authority, actuators, displacement, architecture)
    records = []
    for zone_index, zone_id in enumerate(ZONE_IDS):
        for angle_index, angle in enumerate(parameters.axis_angle_doe_deg):
            records.append(ZoneImpedanceRecord(zone_id, ImpedanceTestRecord(
                record_id=f"PAIR-{zone_id}-{angle:g}", source_parameter_sha256=parameters.parameter_sha256,
                specimen_id="PAIR-EVIDENCE", source_kind="MEASURED",
                frequency_hz=parameters.clean_frequency_baseline_hz,
                commanded_displacement_pp_mm=parameters.displacement_pp_baseline_mm,
                axis_angle_deg=angle, measured_force_N=0.30 + zone_index * 0.01,
                measured_displacement_pp_mm=parameters.displacement_pp_baseline_mm + angle_index * 0.001,
                measured_phase_deg=0.0, measured_temperature_C=28.0 + zone_index + angle_index * 0.25,
                evidence_uri=f"evidence://bench/pair/{zone_id}/{angle:g}",
            )))
    sweep = FourZoneImpedanceSweep(parameters.parameter_sha256, tuple(records))
    return parameters, sweep


def test_current_paired_evidence_is_accepted():
    parameters, sweep = _evidence()
    envelope = reduce_measured_actuation_thermal_envelope(sweep, parameters)
    coupling = reduce_measured_thermal_mechanical_coupling(sweep, parameters)
    validate_paired_thermal_mechanical_evidence(envelope, coupling, sweep, parameters)


def test_stale_coupling_is_rejected_when_thermal_envelope_is_current():
    parameters, sweep = _evidence()
    envelope = reduce_measured_actuation_thermal_envelope(sweep, parameters)
    coupling = reduce_measured_thermal_mechanical_coupling(sweep, parameters)
    corrupted = replace(coupling, point_count=coupling.point_count + 1)
    with pytest.raises(ActuationParameterError, match="does not match"):
        validate_paired_thermal_mechanical_evidence(envelope, corrupted, sweep, parameters)


def test_wrong_coupling_type_is_rejected():
    parameters, sweep = _evidence()
    envelope = reduce_measured_actuation_thermal_envelope(sweep, parameters)
    with pytest.raises(ActuationParameterError, match="exact ActuationThermalMechanicalCoupling"):
        validate_paired_thermal_mechanical_evidence(envelope, object(), sweep, parameters)
