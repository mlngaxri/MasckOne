from dataclasses import replace

import pytest

from masck_one.actuation_parameters import ActuationParameterError, ImpedanceTestRecord, build_actuation_parameter_set
from masck_one.actuation_sweep_contract import build_actuation_displacement_contract
from masck_one.actuation_thermal_coexistence import reduce_measured_actuation_thermal_envelope
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
                record_id=f"THERM-{zone_id}-{angle:g}",
                source_parameter_sha256=parameters.parameter_sha256,
                specimen_id="COUPON-THERMAL-COEXISTENCE",
                source_kind="MEASURED",
                frequency_hz=parameters.clean_frequency_baseline_hz,
                commanded_displacement_pp_mm=parameters.displacement_pp_baseline_mm,
                axis_angle_deg=angle,
                measured_force_N=0.30,
                measured_displacement_pp_mm=parameters.displacement_pp_baseline_mm,
                measured_phase_deg=0.0,
                measured_temperature_C=28.0 + zone_index + angle_index * 0.25,
                evidence_uri=f"evidence://bench/thermal-coexistence/{zone_id}/{angle:g}",
            )))
    return FourZoneImpedanceSweep(parameters.parameter_sha256, tuple(records))


def test_thermal_envelope_preserves_extrema_zone_angle_and_record_traceability():
    parameters = _parameters()
    envelope = reduce_measured_actuation_thermal_envelope(_sweep(parameters), parameters)
    assert envelope.point_count == 4 * len(parameters.axis_angle_doe_deg)
    assert envelope.min_temperature_C == pytest.approx(28.0)
    assert envelope.min_temperature_zone_id == ZONE_IDS[0]
    assert envelope.min_temperature_axis_angle_deg == parameters.axis_angle_doe_deg[0]
    assert envelope.min_temperature_record_id == f"THERM-{ZONE_IDS[0]}-{parameters.axis_angle_doe_deg[0]:g}"
    assert envelope.max_temperature_C == pytest.approx(32.0)
    assert envelope.max_temperature_zone_id == ZONE_IDS[-1]
    assert envelope.max_temperature_axis_angle_deg == parameters.axis_angle_doe_deg[-1]
    assert envelope.max_temperature_record_id == f"THERM-{ZONE_IDS[-1]}-{parameters.axis_angle_doe_deg[-1]:g}"


def test_thermal_envelope_is_order_independent():
    parameters = _parameters()
    sweep = _sweep(parameters)
    reversed_sweep = FourZoneImpedanceSweep(parameters.parameter_sha256, tuple(reversed(sweep.records)))
    assert reduce_measured_actuation_thermal_envelope(sweep, parameters) == reduce_measured_actuation_thermal_envelope(reversed_sweep, parameters)


def test_predicted_sweep_cannot_enter_measured_thermal_envelope():
    parameters = _parameters()
    measured = _sweep(parameters)
    predicted = FourZoneImpedanceSweep(parameters.parameter_sha256, tuple(
        ZoneImpedanceRecord(item.zone_id, replace(
            item.record,
            source_kind="PREDICTED",
            specimen_id="SYNTHETIC-NO-SPECIMEN",
            measured_force_N=None,
            measured_displacement_pp_mm=None,
            measured_phase_deg=None,
            measured_temperature_C=None,
            evidence_uri=None,
        )) for item in measured.records
    ))
    with pytest.raises(ActuationParameterError, match="complete measured four-zone sweep"):
        reduce_measured_actuation_thermal_envelope(predicted, parameters)


def test_stale_parameter_identity_is_rejected_before_temperature_reduction():
    parameters = _parameters()
    sweep = _sweep(parameters)
    stale = replace(parameters, source_authority_revision=parameters.source_authority_revision + "-stale")
    with pytest.raises(ActuationParameterError, match="stale"):
        reduce_measured_actuation_thermal_envelope(sweep, stale)
