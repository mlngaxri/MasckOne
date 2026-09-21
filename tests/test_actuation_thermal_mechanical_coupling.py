from dataclasses import replace

import pytest

from masck_one.actuation_parameters import ActuationParameterError, ImpedanceTestRecord, build_actuation_parameter_set
from masck_one.actuation_sweep_contract import build_actuation_displacement_contract
from masck_one.actuation_thermal_mechanical_coupling import reduce_measured_thermal_mechanical_coupling
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
                record_id=f"COUPLED-{zone_id}-{angle:g}", source_parameter_sha256=parameters.parameter_sha256,
                specimen_id="COUPLED-THERMAL-MECHANICAL", source_kind="MEASURED",
                frequency_hz=parameters.clean_frequency_baseline_hz,
                commanded_displacement_pp_mm=parameters.displacement_pp_baseline_mm, axis_angle_deg=angle,
                measured_force_N=0.25 + zone_index * 0.02 + angle_index * 0.01,
                measured_displacement_pp_mm=parameters.displacement_pp_baseline_mm + angle_index * 0.005,
                measured_phase_deg=0.0, measured_temperature_C=28.0 + zone_index + angle_index * 0.25,
                evidence_uri=f"evidence://bench/coupled/{zone_id}/{angle:g}",
            )))
    return FourZoneImpedanceSweep(parameters.parameter_sha256, tuple(records))


def test_coupled_reduction_keeps_hottest_point_mechanics_on_same_record():
    parameters = _parameters(); result = reduce_measured_thermal_mechanical_coupling(_sweep(parameters), parameters)
    hottest = result.hottest_point
    assert result.point_count == len(ZONE_IDS) * len(parameters.axis_angle_doe_deg)
    assert hottest.zone_id == ZONE_IDS[-1]
    assert hottest.axis_angle_deg == max(parameters.axis_angle_doe_deg)
    assert hottest.record_id == f"COUPLED-{ZONE_IDS[-1]}-{max(parameters.axis_angle_doe_deg):g}"
    assert hottest.temperature_C == pytest.approx(32.0)
    assert hottest.force_N == pytest.approx(0.25 + (len(ZONE_IDS) - 1) * 0.02 + (len(parameters.axis_angle_doe_deg) - 1) * 0.01)


def test_coupled_reduction_preserves_each_zone_extrema_on_original_records():
    parameters = _parameters(); result = reduce_measured_thermal_mechanical_coupling(_sweep(parameters), parameters)
    assert tuple(envelope.zone_id for envelope in result.zone_envelopes) == tuple(sorted(ZONE_IDS))
    assert all(envelope.point_count == len(parameters.axis_angle_doe_deg) for envelope in result.zone_envelopes)
    for envelope in result.zone_envelopes:
        assert envelope.hottest_point.zone_id == envelope.zone_id
        assert envelope.hottest_point.axis_angle_deg == max(parameters.axis_angle_doe_deg)
        assert envelope.hottest_point.record_id == f"COUPLED-{envelope.zone_id}-{max(parameters.axis_angle_doe_deg):g}"
        assert envelope.minimum_force_point.zone_id == envelope.zone_id
        assert envelope.minimum_force_point.axis_angle_deg == min(parameters.axis_angle_doe_deg)
        assert envelope.maximum_displacement_error_point.zone_id == envelope.zone_id
        assert envelope.maximum_displacement_error_point.axis_angle_deg == max(parameters.axis_angle_doe_deg)


def test_angle_spreads_keep_cross_zone_thermal_and_force_evidence_together():
    parameters = _parameters(); result = reduce_measured_thermal_mechanical_coupling(_sweep(parameters), parameters)
    assert tuple(spread.axis_angle_deg for spread in result.angle_spreads) == tuple(sorted(parameters.axis_angle_doe_deg))
    assert all(spread.point_count == len(ZONE_IDS) for spread in result.angle_spreads)
    for spread in result.angle_spreads:
        assert spread.hottest_point.zone_id == ZONE_IDS[-1]
        assert spread.coolest_point.zone_id == ZONE_IDS[0]
        assert spread.minimum_force_point.zone_id == ZONE_IDS[0]
        assert spread.maximum_force_point.zone_id == ZONE_IDS[-1]
        assert spread.temperature_span_C == pytest.approx(len(ZONE_IDS) - 1)
        assert spread.force_span_N == pytest.approx((len(ZONE_IDS) - 1) * 0.02)
        assert spread.hottest_zone_is_minimum_force_zone is False
        assert spread.hottest_point.record_id.endswith(f"-{spread.axis_angle_deg:g}")
        assert spread.minimum_force_point.record_id.endswith(f"-{spread.axis_angle_deg:g}")


def test_angle_spread_worst_cases_are_deterministic_and_order_independent():
    parameters = _parameters(); sweep = _sweep(parameters)
    reversed_sweep = FourZoneImpedanceSweep(parameters.parameter_sha256, tuple(reversed(sweep.records)))
    forward = reduce_measured_thermal_mechanical_coupling(sweep, parameters)
    reverse = reduce_measured_thermal_mechanical_coupling(reversed_sweep, parameters)
    assert forward.angle_spreads == reverse.angle_spreads
    assert forward.maximum_temperature_span_angle == reverse.maximum_temperature_span_angle
    assert forward.maximum_force_span_angle == reverse.maximum_force_span_angle
    assert forward.maximum_temperature_span_angle.axis_angle_deg == min(parameters.axis_angle_doe_deg)
    assert forward.maximum_force_span_angle.axis_angle_deg == min(parameters.axis_angle_doe_deg)


def test_zone_coupled_envelopes_are_order_independent():
    parameters = _parameters(); sweep = _sweep(parameters)
    reversed_sweep = FourZoneImpedanceSweep(parameters.parameter_sha256, tuple(reversed(sweep.records)))
    forward = reduce_measured_thermal_mechanical_coupling(sweep, parameters)
    reverse = reduce_measured_thermal_mechanical_coupling(reversed_sweep, parameters)
    assert forward.zone_envelopes == reverse.zone_envelopes


def test_coupled_reduction_reports_signed_shortfalls_without_qualification_claim():
    parameters = _parameters(); result = reduce_measured_thermal_mechanical_coupling(_sweep(parameters), parameters)
    assert result.minimum_force_point.continuous_force_margin_N == pytest.approx(0.25 - parameters.continuous_force_requirement_N)
    assert result.minimum_force_point.transient_force_margin_N == pytest.approx(0.25 - parameters.transient_force_requirement_N)
    assert result.hottest_transient_force_shortfall_point is not None
    if 0.25 >= parameters.continuous_force_requirement_N:
        assert result.hottest_continuous_force_shortfall_point is None


def test_coupled_reduction_is_order_independent():
    parameters = _parameters(); sweep = _sweep(parameters)
    reversed_sweep = FourZoneImpedanceSweep(parameters.parameter_sha256, tuple(reversed(sweep.records)))
    assert reduce_measured_thermal_mechanical_coupling(sweep, parameters) == reduce_measured_thermal_mechanical_coupling(reversed_sweep, parameters)


def test_predicted_evidence_cannot_enter_coupled_measured_reduction():
    parameters = _parameters(); measured = _sweep(parameters)
    predicted = FourZoneImpedanceSweep(parameters.parameter_sha256, tuple(ZoneImpedanceRecord(item.zone_id, replace(
        item.record, source_kind="PREDICTED", specimen_id="SYNTHETIC-NO-SPECIMEN", measured_force_N=None,
        measured_displacement_pp_mm=None, measured_phase_deg=None, measured_temperature_C=None, evidence_uri=None,
    )) for item in measured.records))
    with pytest.raises(ActuationParameterError, match="complete measured four-zone sweep"):
        reduce_measured_thermal_mechanical_coupling(predicted, parameters)


def test_stale_parameter_identity_is_rejected_before_coupled_reduction():
    parameters = _parameters(); sweep = _sweep(parameters)
    stale = replace(parameters, source_authority_revision=parameters.source_authority_revision + "-stale")
    with pytest.raises(ActuationParameterError, match="stale"):
        reduce_measured_thermal_mechanical_coupling(sweep, stale)
