from dataclasses import replace

import pytest

from masck_one.actuation_parameters import ActuationParameterError, ImpedanceTestRecord, build_actuation_parameter_set
from masck_one.actuation_sweep_contract import build_actuation_displacement_contract
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


def _measured_point(parameters, zone_id, angle, *, force, displacement):
    return ZoneImpedanceRecord(zone_id, ImpedanceTestRecord(
        record_id=f"SYS-{zone_id}-{angle:g}", source_parameter_sha256=parameters.parameter_sha256,
        specimen_id="COUPON-SYSTEM", source_kind="MEASURED", frequency_hz=parameters.clean_frequency_baseline_hz,
        commanded_displacement_pp_mm=parameters.displacement_pp_baseline_mm, axis_angle_deg=angle,
        measured_force_N=force, measured_displacement_pp_mm=displacement, measured_phase_deg=0.0,
        measured_temperature_C=30.0, evidence_uri=f"evidence://bench/system/{zone_id}/{angle:g}",
    ))


def _sweep(parameters):
    records = []
    for zone_index, zone_id in enumerate(ZONE_IDS):
        for angle_index, angle in enumerate(parameters.axis_angle_doe_deg):
            records.append(_measured_point(
                parameters, zone_id, angle,
                force=0.30 + zone_index * 0.01 + angle_index * 0.001,
                displacement=parameters.displacement_pp_baseline_mm + zone_index * 0.001 + angle_index * 0.002,
            ))
    return FourZoneImpedanceSweep(parameters.parameter_sha256, tuple(records))


def test_system_response_preserves_worst_case_zone_and_axis_angle():
    parameters = _parameters()
    sweep = _sweep(parameters)
    response = sweep.measured_system_response(parameters)
    assert response.point_count == 4 * len(parameters.axis_angle_doe_deg)
    assert response.min_force_N == pytest.approx(0.30)
    assert response.min_force_zone_id == ZONE_IDS[0]
    assert response.min_force_axis_angle_deg == parameters.axis_angle_doe_deg[0]
    assert response.max_force_N == pytest.approx(0.334)
    assert response.max_force_zone_id == ZONE_IDS[-1]
    assert response.max_force_axis_angle_deg == parameters.axis_angle_doe_deg[-1]
    assert response.max_abs_displacement_error_mm == pytest.approx(0.011)
    assert response.max_error_zone_id == ZONE_IDS[-1]
    assert response.max_error_axis_angle_deg == parameters.axis_angle_doe_deg[-1]
    assert response.min_continuous_force_margin_N == pytest.approx(0.30 - parameters.continuous_force_requirement_N)
    assert response.min_transient_force_margin_N == pytest.approx(0.30 - parameters.transient_force_requirement_N)


def test_system_response_is_order_independent_for_unique_extrema():
    parameters = _parameters()
    sweep = _sweep(parameters)
    reversed_sweep = FourZoneImpedanceSweep(parameters.parameter_sha256, tuple(reversed(sweep.records)))
    assert sweep.measured_system_response(parameters) == reversed_sweep.measured_system_response(parameters)


def test_predicted_evidence_cannot_enter_system_measured_response():
    parameters = _parameters()
    measured = _sweep(parameters)
    records = []
    for item in measured.records:
        record = replace(
            item.record, source_kind="PREDICTED", specimen_id="SYNTHETIC-NO-SPECIMEN",
            measured_force_N=None, measured_displacement_pp_mm=None, measured_phase_deg=None,
            measured_temperature_C=None, evidence_uri=None,
        )
        records.append(ZoneImpedanceRecord(item.zone_id, record))
    predicted = FourZoneImpedanceSweep(parameters.parameter_sha256, tuple(records))
    with pytest.raises(ActuationParameterError, match="complete measured four-zone sweep"):
        predicted.measured_system_response(parameters)
