from dataclasses import replace

import pytest

from masck_one.actuation_mechanical_sensitivity import reduce_measured_mechanical_sensitivity
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


def _sweep(parameters):
    records = []
    for zone_index, zone_id in enumerate(ZONE_IDS):
        for angle_index, angle in enumerate(parameters.axis_angle_doe_deg):
            phase_deg = ((170.0 + angle_index * 20.0 + 180.0) % 360.0) - 180.0
            records.append(ZoneImpedanceRecord(zone_id, ImpedanceTestRecord(
                record_id=f"SENS-{zone_id}-{angle:g}", source_parameter_sha256=parameters.parameter_sha256,
                specimen_id="COUPLED-SENSITIVITY", source_kind="MEASURED",
                frequency_hz=parameters.clean_frequency_baseline_hz,
                commanded_displacement_pp_mm=parameters.displacement_pp_baseline_mm, axis_angle_deg=angle,
                measured_force_N=0.25 + zone_index * 0.02 + angle_index * 0.01,
                measured_displacement_pp_mm=parameters.displacement_pp_baseline_mm + zone_index * 0.002 + angle_index * 0.005,
                measured_phase_deg=phase_deg, measured_temperature_C=28.0 + zone_index + angle_index * 0.25,
                evidence_uri=f"evidence://bench/sensitivity/{zone_id}/{angle:g}",
            )))
    return FourZoneImpedanceSweep(parameters.parameter_sha256, tuple(records))


def test_sensitivity_preserves_adjacent_measured_record_provenance():
    parameters = _parameters(); result = reduce_measured_mechanical_sensitivity(_sweep(parameters), parameters)
    angles = tuple(sorted(parameters.axis_angle_doe_deg))
    assert result.interval_count == len(ZONE_IDS) * (len(angles) - 1)
    for item in result.sensitivities:
        assert item.upper_angle_deg > item.lower_angle_deg
        assert item.lower_record_id == f"SENS-{item.zone_id}-{item.lower_angle_deg:g}"
        assert item.upper_record_id == f"SENS-{item.zone_id}-{item.upper_angle_deg:g}"
        assert item.force_delta_N == pytest.approx(0.01)
        assert item.displacement_delta_mm == pytest.approx(0.005)
        assert item.phase_delta_deg == pytest.approx(20.0)
        assert item.temperature_delta_C == pytest.approx(0.25)
        assert item.force_slope_N_per_deg == pytest.approx(item.force_delta_N / item.angle_delta_deg)
        assert item.displacement_slope_mm_per_deg == pytest.approx(item.displacement_delta_mm / item.angle_delta_deg)
        assert item.phase_slope_deg_per_deg == pytest.approx(item.phase_delta_deg / item.angle_delta_deg)
        assert item.temperature_slope_C_per_deg == pytest.approx(item.temperature_delta_C / item.angle_delta_deg)


def test_phase_sensitivity_uses_shortest_signed_delta_across_wrap():
    parameters = _parameters(); result = reduce_measured_mechanical_sensitivity(_sweep(parameters), parameters)
    wrapped = [item for item in result.sensitivities if item.lower_angle_deg == min(parameters.axis_angle_doe_deg)]
    assert wrapped
    assert all(item.phase_delta_deg == pytest.approx(20.0) for item in wrapped)
    assert all(abs(item.phase_delta_deg) < 180.0 for item in result.sensitivities)


def test_sensitivity_reduction_is_order_independent():
    parameters = _parameters(); sweep = _sweep(parameters)
    reversed_sweep = FourZoneImpedanceSweep(parameters.parameter_sha256, tuple(reversed(sweep.records)))
    assert reduce_measured_mechanical_sensitivity(sweep, parameters) == reduce_measured_mechanical_sensitivity(reversed_sweep, parameters)


def test_worst_sensitivities_remain_traceable_to_measured_interval():
    parameters = _parameters(); result = reduce_measured_mechanical_sensitivity(_sweep(parameters), parameters)
    for item in (result.maximum_abs_force_sensitivity, result.maximum_abs_displacement_sensitivity, result.maximum_abs_phase_sensitivity, result.maximum_abs_temperature_sensitivity):
        assert item.zone_id in ZONE_IDS
        assert item.lower_record_id.startswith(f"SENS-{item.zone_id}-")
        assert item.upper_record_id.startswith(f"SENS-{item.zone_id}-")


def test_per_zone_extrema_keep_all_four_zones_visible_and_traceable():
    parameters = _parameters(); result = reduce_measured_mechanical_sensitivity(_sweep(parameters), parameters)
    assert tuple(item.zone_id for item in result.zone_extrema) == tuple(sorted(ZONE_IDS))
    for extrema in result.zone_extrema:
        candidates = (
            extrema.maximum_abs_force_sensitivity,
            extrema.maximum_abs_displacement_sensitivity,
            extrema.maximum_abs_phase_sensitivity,
            extrema.maximum_abs_temperature_sensitivity,
        )
        assert all(item.zone_id == extrema.zone_id for item in candidates)
        assert all(item.lower_record_id.startswith(f"SENS-{extrema.zone_id}-") for item in candidates)
        assert all(item.upper_record_id.startswith(f"SENS-{extrema.zone_id}-") for item in candidates)


def test_per_zone_extrema_are_order_independent():
    parameters = _parameters(); sweep = _sweep(parameters)
    reversed_sweep = FourZoneImpedanceSweep(parameters.parameter_sha256, tuple(reversed(sweep.records)))
    forward = reduce_measured_mechanical_sensitivity(sweep, parameters)
    reverse = reduce_measured_mechanical_sensitivity(reversed_sweep, parameters)
    assert forward.zone_extrema == reverse.zone_extrema


def test_predicted_evidence_is_rejected_before_sensitivity_reduction():
    parameters = _parameters(); measured = _sweep(parameters)
    predicted = FourZoneImpedanceSweep(parameters.parameter_sha256, tuple(ZoneImpedanceRecord(item.zone_id, replace(
        item.record, source_kind="PREDICTED", specimen_id="SYNTHETIC-NO-SPECIMEN", measured_force_N=None,
        measured_displacement_pp_mm=None, measured_phase_deg=None, measured_temperature_C=None, evidence_uri=None,
    )) for item in measured.records))
    with pytest.raises(ActuationParameterError, match="complete measured four-zone sweep"):
        reduce_measured_mechanical_sensitivity(predicted, parameters)


def test_stale_parameter_identity_is_rejected_before_sensitivity_reduction():
    parameters = _parameters(); sweep = _sweep(parameters)
    stale = replace(parameters, source_authority_revision=parameters.source_authority_revision + "-stale")
    with pytest.raises(ActuationParameterError, match="stale"):
        reduce_measured_mechanical_sensitivity(sweep, stale)
