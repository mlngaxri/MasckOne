from dataclasses import replace

import pytest

from masck_one.actuation_mechanical_curvature import reduce_measured_mechanical_curvature
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
            records.append(ZoneImpedanceRecord(zone_id, ImpedanceTestRecord(
                record_id=f"CURV-{zone_id}-{angle:g}", source_parameter_sha256=parameters.parameter_sha256,
                specimen_id="COUPLED-CURVATURE", source_kind="MEASURED",
                frequency_hz=parameters.clean_frequency_baseline_hz,
                commanded_displacement_pp_mm=parameters.displacement_pp_baseline_mm, axis_angle_deg=angle,
                measured_force_N=0.25 + zone_index * 0.02 + angle_index * 0.01,
                measured_displacement_pp_mm=parameters.displacement_pp_baseline_mm + zone_index * 0.002 + angle_index * 0.005,
                measured_phase_deg=10.0 + angle_index * 5.0,
                measured_temperature_C=28.0 + zone_index + angle_index * 0.25,
                evidence_uri=f"evidence://bench/curvature/{zone_id}/{angle:g}",
            )))
    return FourZoneImpedanceSweep(parameters.parameter_sha256, tuple(records))


def test_curvature_preserves_three_record_provenance_and_sweep_identity():
    parameters = _parameters(); sweep = _sweep(parameters)
    result = reduce_measured_mechanical_curvature(sweep, parameters)
    angles = tuple(sorted(parameters.axis_angle_doe_deg))
    assert result.source_parameter_sha256 == parameters.parameter_sha256
    assert result.source_sweep_sha256 == sweep.sweep_sha256
    assert result.triplet_count == len(ZONE_IDS) * (len(angles) - 2)
    for item in result.curvatures:
        assert item.lower_angle_deg < item.center_angle_deg < item.upper_angle_deg
        assert item.lower_record_id == f"CURV-{item.zone_id}-{item.lower_angle_deg:g}"
        assert item.center_record_id == f"CURV-{item.zone_id}-{item.center_angle_deg:g}"
        assert item.upper_record_id == f"CURV-{item.zone_id}-{item.upper_angle_deg:g}"
        assert item.interval_center_delta_deg > 0.0


def test_curvature_is_zero_for_linear_response_over_uniform_or_nonuniform_doe_spacing():
    parameters = _parameters(); sweep = _sweep(parameters)
    records = tuple(ZoneImpedanceRecord(item.zone_id, replace(
        item.record,
        measured_force_N=0.25 + 0.001 * float(item.record.axis_angle_deg),
        measured_displacement_pp_mm=parameters.displacement_pp_baseline_mm + 0.0005 * float(item.record.axis_angle_deg),
        measured_phase_deg=10.0 + 0.2 * float(item.record.axis_angle_deg),
        measured_temperature_C=28.0 + 0.05 * float(item.record.axis_angle_deg),
    )) for item in sweep.records)
    result = reduce_measured_mechanical_curvature(FourZoneImpedanceSweep(parameters.parameter_sha256, records), parameters)
    for item in result.curvatures:
        assert item.force_curvature_N_per_deg2 == pytest.approx(0.0, abs=1e-12)
        assert item.displacement_curvature_mm_per_deg2 == pytest.approx(0.0, abs=1e-12)
        assert item.phase_curvature_deg_per_deg2 == pytest.approx(0.0, abs=1e-12)
        assert item.temperature_curvature_C_per_deg2 == pytest.approx(0.0, abs=1e-12)


def test_local_force_knee_is_exposed_with_exact_three_record_evidence():
    parameters = _parameters(); sweep = _sweep(parameters)
    zone_id = sorted(ZONE_IDS)[0]
    angles = tuple(sorted(parameters.axis_angle_doe_deg))
    center = angles[len(angles) // 2]
    records = tuple(ZoneImpedanceRecord(item.zone_id, replace(
        item.record, measured_force_N=float(item.record.measured_force_N) + 0.05,
    )) if item.zone_id == zone_id and float(item.record.axis_angle_deg) == center else item for item in sweep.records)
    changed = FourZoneImpedanceSweep(parameters.parameter_sha256, records)
    result = reduce_measured_mechanical_curvature(changed, parameters)
    worst = result.maximum_abs_force_curvature
    assert worst.zone_id == zone_id
    assert center in (worst.lower_angle_deg, worst.center_angle_deg, worst.upper_angle_deg)
    assert worst.lower_record_id.startswith(f"CURV-{zone_id}-")
    assert worst.center_record_id.startswith(f"CURV-{zone_id}-")
    assert worst.upper_record_id.startswith(f"CURV-{zone_id}-")
    assert abs(worst.force_curvature_N_per_deg2) > 0.0


def test_per_zone_curvature_extrema_keep_all_four_actuators_visible():
    parameters = _parameters(); sweep = _sweep(parameters)
    result = reduce_measured_mechanical_curvature(sweep, parameters)
    assert tuple(item.zone_id for item in result.per_zone_extrema) == tuple(sorted(ZONE_IDS))
    for extrema in result.per_zone_extrema:
        zone_items = tuple(item for item in result.curvatures if item.zone_id == extrema.zone_id)
        for worst, attribute in (
            (extrema.maximum_abs_force_curvature, "force_curvature_N_per_deg2"),
            (extrema.maximum_abs_displacement_curvature, "displacement_curvature_mm_per_deg2"),
            (extrema.maximum_abs_phase_curvature, "phase_curvature_deg_per_deg2"),
            (extrema.maximum_abs_temperature_curvature, "temperature_curvature_C_per_deg2"),
        ):
            assert worst.zone_id == extrema.zone_id
            assert abs(getattr(worst, attribute)) == max(abs(getattr(item, attribute)) for item in zone_items)
            assert worst.lower_record_id.startswith(f"CURV-{extrema.zone_id}-")
            assert worst.center_record_id.startswith(f"CURV-{extrema.zone_id}-")
            assert worst.upper_record_id.startswith(f"CURV-{extrema.zone_id}-")


def test_curvature_reduction_is_order_independent():
    parameters = _parameters(); sweep = _sweep(parameters)
    reverse = FourZoneImpedanceSweep(parameters.parameter_sha256, tuple(reversed(sweep.records)))
    assert reduce_measured_mechanical_curvature(sweep, parameters) == reduce_measured_mechanical_curvature(reverse, parameters)


def test_predicted_and_stale_evidence_fail_before_curvature_reduction():
    parameters = _parameters(); measured = _sweep(parameters)
    predicted = FourZoneImpedanceSweep(parameters.parameter_sha256, tuple(ZoneImpedanceRecord(item.zone_id, replace(
        item.record, source_kind="PREDICTED", specimen_id="SYNTHETIC-NO-SPECIMEN", measured_force_N=None,
        measured_displacement_pp_mm=None, measured_phase_deg=None, measured_temperature_C=None, evidence_uri=None,
    )) for item in measured.records))
    with pytest.raises(ActuationParameterError, match="complete measured four-zone sweep"):
        reduce_measured_mechanical_curvature(predicted, parameters)
    stale = replace(parameters, source_authority_revision=parameters.source_authority_revision + "-stale")
    with pytest.raises(ActuationParameterError, match="stale"):
        reduce_measured_mechanical_curvature(measured, stale)
