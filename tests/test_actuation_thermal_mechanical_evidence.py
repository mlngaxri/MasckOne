from dataclasses import replace

import pytest

from masck_one.actuation_parameters import ActuationParameterError, ImpedanceTestRecord, build_actuation_parameter_set
from masck_one.actuation_sweep_contract import build_actuation_displacement_contract
from masck_one.actuation_thermal_mechanical_coupling import reduce_measured_thermal_mechanical_coupling
from masck_one.actuation_thermal_mechanical_evidence import validate_thermal_mechanical_coupling_evidence
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
                record_id=f"BOUNDARY-{zone_id}-{angle:g}",
                source_parameter_sha256=parameters.parameter_sha256,
                specimen_id="COUPLED-BOUNDARY",
                source_kind="MEASURED",
                frequency_hz=parameters.clean_frequency_baseline_hz,
                commanded_displacement_pp_mm=parameters.displacement_pp_baseline_mm,
                axis_angle_deg=angle,
                measured_force_N=0.25 + zone_index * 0.02 + angle_index * 0.01,
                measured_displacement_pp_mm=parameters.displacement_pp_baseline_mm + zone_index * 0.002,
                measured_phase_deg=0.0,
                measured_temperature_C=28.0 + zone_index + angle_index * 0.25,
                evidence_uri=f"evidence://bench/boundary/{zone_id}/{angle:g}",
            )))
    sweep = FourZoneImpedanceSweep(parameters.parameter_sha256, tuple(records))
    return parameters, sweep, reduce_measured_thermal_mechanical_coupling(sweep, parameters)


def test_current_coupling_matches_current_measured_sweep():
    parameters, sweep, coupling = _evidence()
    validate_thermal_mechanical_coupling_evidence(coupling, sweep, parameters)


def test_mutated_coupling_extremum_fails_closed_at_consumption_boundary():
    parameters, sweep, coupling = _evidence()
    object.__setattr__(coupling, "point_count", coupling.point_count - 1)
    with pytest.raises(ActuationParameterError, match="does not match"):
        validate_thermal_mechanical_coupling_evidence(coupling, sweep, parameters)


def test_coupling_from_different_measured_sweep_is_rejected():
    parameters, sweep, coupling = _evidence()
    first = sweep.records[0]
    changed_record = replace(first.record, measured_temperature_C=float(first.record.measured_temperature_C) + 1.0)
    changed_sweep = FourZoneImpedanceSweep(
        sweep.source_parameter_sha256,
        (ZoneImpedanceRecord(first.zone_id, changed_record),) + sweep.records[1:],
    )
    with pytest.raises(ActuationParameterError, match="does not match"):
        validate_thermal_mechanical_coupling_evidence(coupling, changed_sweep, parameters)


def test_source_sweep_is_revalidated_before_coupling_comparison():
    parameters, sweep, coupling = _evidence()
    object.__setattr__(sweep, "records", (sweep.records[0],) + sweep.records)
    with pytest.raises(ActuationParameterError, match="Duplicate four-zone sweep point"):
        validate_thermal_mechanical_coupling_evidence(coupling, sweep, parameters)


def test_mutated_parameter_invariants_fail_before_coexistence_reduction():
    parameters, sweep, coupling = _evidence()
    object.__setattr__(parameters, "axis_angle_doe_deg", (parameters.axis_angle_baseline_deg, parameters.axis_angle_baseline_deg))
    with pytest.raises(ActuationParameterError, match="Axis-angle DOE must be unique"):
        validate_thermal_mechanical_coupling_evidence(coupling, sweep, parameters)


def test_mutated_parameter_cannot_claim_physical_validation_at_evidence_boundary():
    parameters, sweep, coupling = _evidence()
    object.__setattr__(parameters, "physical_validation_eligible", True)
    with pytest.raises(ActuationParameterError, match="cannot be physical validation evidence"):
        validate_thermal_mechanical_coupling_evidence(coupling, sweep, parameters)


def test_wrong_coupling_type_is_rejected():
    parameters, sweep, _ = _evidence()
    with pytest.raises(ActuationParameterError, match="exact ActuationThermalMechanicalCoupling"):
        validate_thermal_mechanical_coupling_evidence(object(), sweep, parameters)
