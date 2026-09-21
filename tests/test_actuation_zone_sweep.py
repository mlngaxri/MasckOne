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


def _point(parameters, zone_id, angle, *, source_kind="PREDICTED", suffix=""):
    record = ImpedanceTestRecord(
        record_id=f"IMP-{zone_id}-{angle:g}{suffix}",
        source_parameter_sha256=parameters.parameter_sha256,
        specimen_id="SYNTHETIC-NO-SPECIMEN",
        source_kind=source_kind,
        frequency_hz=parameters.clean_frequency_baseline_hz,
        commanded_displacement_pp_mm=parameters.displacement_pp_baseline_mm,
        axis_angle_deg=angle,
    )
    return ZoneImpedanceRecord(zone_id=zone_id, record=record)


def _complete(parameters):
    return tuple(_point(parameters, zone_id, angle) for zone_id in ZONE_IDS for angle in parameters.axis_angle_doe_deg)


def test_complete_four_zone_axis_angle_matrix_is_accepted():
    parameters = _parameters()
    sweep = FourZoneImpedanceSweep(parameters.parameter_sha256, _complete(parameters))
    sweep.validate(parameters)
    assert sweep.point_count == 4 * len(parameters.axis_angle_doe_deg) == 20


def test_missing_zone_angle_point_fails_closed():
    parameters = _parameters()
    sweep = FourZoneImpedanceSweep(parameters.parameter_sha256, _complete(parameters)[:-1])
    with pytest.raises(ActuationParameterError, match="must cover every controlled zone"):
        sweep.validate(parameters)


def test_duplicate_zone_angle_point_fails_closed():
    parameters = _parameters()
    records = _complete(parameters)
    duplicate = ZoneImpedanceRecord(records[0].zone_id, replace(records[0].record, record_id="IMP-DUPLICATE"))
    sweep = FourZoneImpedanceSweep(parameters.parameter_sha256, records + (duplicate,))
    with pytest.raises(ActuationParameterError, match="Duplicate four-zone sweep point"):
        sweep.validate(parameters)


def test_stale_parameter_identity_fails_closed():
    parameters = _parameters()
    sweep = FourZoneImpedanceSweep("0" * 64, _complete(parameters))
    with pytest.raises(ActuationParameterError, match="stale"):
        sweep.validate(parameters)


def test_unapproved_command_inside_matrix_fails_closed():
    parameters = _parameters()
    records = list(_complete(parameters))
    records[0] = ZoneImpedanceRecord(records[0].zone_id, replace(records[0].record, frequency_hz=41.0))
    with pytest.raises(ActuationParameterError, match="CLEAN baseline"):
        FourZoneImpedanceSweep(parameters.parameter_sha256, tuple(records)).validate(parameters)


def test_mixed_predicted_and_measured_evidence_fails_closed():
    parameters = _parameters()
    records = list(_complete(parameters))
    base = records[0]
    measured = replace(
        base.record,
        source_kind="MEASURED",
        specimen_id="COUPON-001",
        measured_force_N=0.2,
        measured_displacement_pp_mm=0.52,
        measured_phase_deg=0.0,
        evidence_uri="evidence://bench/impedance/COUPON-001/run-001",
    )
    records[0] = ZoneImpedanceRecord(base.zone_id, measured)
    with pytest.raises(ActuationParameterError, match="cannot mix predicted and measured"):
        FourZoneImpedanceSweep(parameters.parameter_sha256, tuple(records)).validate(parameters)


def test_unknown_zone_and_non_record_evidence_are_rejected():
    parameters = _parameters()
    with pytest.raises(ActuationParameterError, match="Unknown actuator zone"):
        ZoneImpedanceRecord("ACTUATOR_ZONE_FIFTH", _complete(parameters)[0].record)
    with pytest.raises(ActuationParameterError, match="exact ImpedanceTestRecord"):
        ZoneImpedanceRecord(ZONE_IDS[0], object())
