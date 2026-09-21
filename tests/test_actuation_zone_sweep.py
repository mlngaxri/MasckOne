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
    kwargs = {}
    if source_kind == "MEASURED":
        kwargs = {
            "measured_force_N": 0.20 + angle / 1000.0,
            "measured_displacement_pp_mm": parameters.displacement_pp_baseline_mm + (angle - parameters.axis_angle_baseline_deg) / 1000.0,
            "measured_phase_deg": 0.0,
            "measured_temperature_C": 30.0,
            "evidence_uri": f"evidence://bench/impedance/{zone_id}/{angle:g}{suffix}",
        }
    record = ImpedanceTestRecord(
        record_id=f"IMP-{zone_id}-{angle:g}{suffix}",
        source_parameter_sha256=parameters.parameter_sha256,
        specimen_id="COUPON-001" if source_kind == "MEASURED" else "SYNTHETIC-NO-SPECIMEN",
        source_kind=source_kind,
        frequency_hz=parameters.clean_frequency_baseline_hz,
        commanded_displacement_pp_mm=parameters.displacement_pp_baseline_mm,
        axis_angle_deg=angle,
        **kwargs,
    )
    return ZoneImpedanceRecord(zone_id=zone_id, record=record)


def _complete(parameters, *, source_kind="PREDICTED"):
    return tuple(_point(parameters, zone_id, angle, source_kind=source_kind) for zone_id in ZONE_IDS for angle in parameters.axis_angle_doe_deg)


def test_complete_four_zone_axis_angle_matrix_is_accepted():
    parameters = _parameters()
    sweep = FourZoneImpedanceSweep(parameters.parameter_sha256, _complete(parameters))
    sweep.validate(parameters)
    assert sweep.point_count == 4 * len(parameters.axis_angle_doe_deg) == 20


def test_sweep_manifest_and_digest_are_deterministic_across_record_order():
    parameters = _parameters()
    records = _complete(parameters)
    forward = FourZoneImpedanceSweep(parameters.parameter_sha256, records)
    reverse = FourZoneImpedanceSweep(parameters.parameter_sha256, tuple(reversed(records)))
    assert forward.sweep_sha256 == reverse.sweep_sha256
    assert forward.manifest() == reverse.manifest()
    assert forward.manifest()["sweep_sha256"] == forward.sweep_sha256
    assert len(forward.sweep_sha256) == 64


def test_sweep_digest_changes_when_impedance_evidence_changes():
    parameters = _parameters()
    records = list(_complete(parameters))
    baseline = FourZoneImpedanceSweep(parameters.parameter_sha256, tuple(records))
    first = records[0]
    records[0] = ZoneImpedanceRecord(first.zone_id, replace(first.record, specimen_id="SYNTHETIC-ALTERNATE"))
    changed = FourZoneImpedanceSweep(parameters.parameter_sha256, tuple(records))
    assert changed.sweep_sha256 != baseline.sweep_sha256


def test_measured_response_reduction_reports_zone_extrema_without_qualification_claim():
    parameters = _parameters()
    sweep = FourZoneImpedanceSweep(parameters.parameter_sha256, _complete(parameters, source_kind="MEASURED"))
    response = sweep.measured_response_by_zone(parameters)
    assert tuple(response) == ZONE_IDS
    for zone_id in ZONE_IDS:
        zone = response[zone_id]
        assert zone.point_count == len(parameters.axis_angle_doe_deg)
        assert zone.min_force_N == pytest.approx(0.25)
        assert zone.max_force_N == pytest.approx(0.272)
        assert zone.min_displacement_pp_mm == pytest.approx(0.509)
        assert zone.max_displacement_pp_mm == pytest.approx(0.531)
        assert zone.max_abs_displacement_error_mm == pytest.approx(0.011)
        assert zone.min_continuous_force_margin_N == pytest.approx(zone.min_force_N - parameters.continuous_force_requirement_N)
        assert zone.min_transient_force_margin_N == pytest.approx(zone.min_force_N - parameters.transient_force_requirement_N)


def test_force_margins_preserve_signed_shortfall_instead_of_claiming_pass():
    parameters = _parameters()
    sweep = FourZoneImpedanceSweep(parameters.parameter_sha256, _complete(parameters, source_kind="MEASURED"))
    for zone in sweep.measured_response_by_zone(parameters).values():
        assert zone.min_continuous_force_margin_N == pytest.approx(0.05)
        assert zone.min_transient_force_margin_N == pytest.approx(-0.35)


def test_predicted_sweep_cannot_masquerade_as_measured_response():
    parameters = _parameters()
    sweep = FourZoneImpedanceSweep(parameters.parameter_sha256, _complete(parameters))
    with pytest.raises(ActuationParameterError, match="complete measured four-zone sweep"):
        sweep.measured_response_by_zone(parameters)


def test_missing_zone_angle_point_fails_closed():
    parameters = _parameters()
    sweep = FourZoneImpedanceSweep(parameters.parameter_sha256, _complete(parameters)[:-1])
    with pytest.raises(ActuationParameterError, match="must cover every controlled zone"):
        sweep.validate(parameters)


def test_duplicate_zone_angle_point_fails_closed_at_construction():
    parameters = _parameters()
    records = _complete(parameters)
    duplicate = ZoneImpedanceRecord(records[0].zone_id, replace(records[0].record, record_id="IMP-DUPLICATE"))
    with pytest.raises(ActuationParameterError, match="Duplicate four-zone sweep point"):
        FourZoneImpedanceSweep(parameters.parameter_sha256, records + (duplicate,))


def test_duplicate_record_id_fails_closed_at_construction():
    parameters = _parameters()
    records = _complete(parameters)
    duplicate_id = ZoneImpedanceRecord(records[1].zone_id, replace(records[1].record, record_id=records[0].record.record_id))
    forged = (records[0], duplicate_id) + records[2:]
    with pytest.raises(ActuationParameterError, match="record IDs must be unique"):
        FourZoneImpedanceSweep(parameters.parameter_sha256, forged)


def test_sweep_container_and_identity_fail_closed_at_construction():
    parameters = _parameters()
    with pytest.raises(ActuationParameterError, match="canonical lowercase SHA-256"):
        FourZoneImpedanceSweep("NOT-A-SHA", _complete(parameters))
    with pytest.raises(ActuationParameterError, match="immutable tuple"):
        FourZoneImpedanceSweep(parameters.parameter_sha256, list(_complete(parameters)))
    with pytest.raises(ActuationParameterError, match="empty evidence"):
        FourZoneImpedanceSweep(parameters.parameter_sha256, ())
    with pytest.raises(ActuationParameterError, match="non-zone impedance evidence"):
        FourZoneImpedanceSweep(parameters.parameter_sha256, (object(),))


def test_sweep_rejects_record_from_different_parameter_identity_at_construction():
    parameters = _parameters()
    records = list(_complete(parameters))
    records[0] = ZoneImpedanceRecord(
        records[0].zone_id,
        replace(records[0].record, source_parameter_sha256="0" * 64),
    )
    with pytest.raises(ActuationParameterError, match="record parameter identity must match"):
        FourZoneImpedanceSweep(parameters.parameter_sha256, tuple(records))


def test_stale_sweep_parameter_identity_fails_closed_at_construction():
    parameters = _parameters()
    with pytest.raises(ActuationParameterError, match="record parameter identity must match"):
        FourZoneImpedanceSweep("0" * 64, _complete(parameters))


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
