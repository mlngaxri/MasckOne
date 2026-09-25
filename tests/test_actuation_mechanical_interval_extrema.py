from dataclasses import replace

from masck_one.actuation_mechanical_sensitivity import reduce_measured_mechanical_sensitivity
from masck_one.actuation_parameters import ImpedanceTestRecord, build_actuation_parameter_set
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
                record_id=f"INTERVAL-{zone_id}-{angle:g}",
                source_parameter_sha256=parameters.parameter_sha256,
                specimen_id="COUPLED-INTERVAL",
                source_kind="MEASURED",
                frequency_hz=parameters.clean_frequency_baseline_hz,
                commanded_displacement_pp_mm=parameters.displacement_pp_baseline_mm,
                axis_angle_deg=angle,
                measured_force_N=0.25 + zone_index * 0.02 + angle_index * 0.01 * (zone_index + 1),
                measured_displacement_pp_mm=parameters.displacement_pp_baseline_mm + angle_index * 0.002 * (zone_index + 1),
                measured_phase_deg=10.0 + angle_index * 2.0 * (zone_index + 1),
                measured_temperature_C=28.0 + zone_index + angle_index * 0.1 * (zone_index + 1),
                evidence_uri=f"evidence://bench/interval/{zone_id}/{angle:g}",
            )))
    return FourZoneImpedanceSweep(parameters.parameter_sha256, tuple(records))


def test_angle_interval_extrema_keep_all_zones_and_exact_interval_provenance():
    parameters = _parameters()
    result = reduce_measured_mechanical_sensitivity(_sweep(parameters), parameters)
    angles = tuple(sorted(parameters.axis_angle_doe_deg))
    assert len(result.angle_interval_extrema) == len(angles) - 1
    for interval in result.angle_interval_extrema:
        assert interval.zone_count == len(ZONE_IDS)
        candidates = tuple(item for item in result.sensitivities if item.lower_angle_deg == interval.lower_angle_deg and item.upper_angle_deg == interval.upper_angle_deg)
        assert len(candidates) == len(ZONE_IDS)
        for selected, attribute in (
            (interval.maximum_abs_force_sensitivity, "force_slope_N_per_deg"),
            (interval.maximum_abs_displacement_sensitivity, "displacement_slope_mm_per_deg"),
            (interval.maximum_abs_phase_sensitivity, "phase_slope_deg_per_deg"),
            (interval.maximum_abs_temperature_sensitivity, "temperature_slope_C_per_deg"),
        ):
            assert selected in candidates
            assert abs(getattr(selected, attribute)) == max(abs(getattr(item, attribute)) for item in candidates)
            assert selected.lower_record_id == f"INTERVAL-{selected.zone_id}-{interval.lower_angle_deg:g}"
            assert selected.upper_record_id == f"INTERVAL-{selected.zone_id}-{interval.upper_angle_deg:g}"


def test_angle_interval_extrema_are_order_independent_and_sweep_bound():
    parameters = _parameters()
    sweep = _sweep(parameters)
    reversed_sweep = FourZoneImpedanceSweep(parameters.parameter_sha256, tuple(reversed(sweep.records)))
    forward = reduce_measured_mechanical_sensitivity(sweep, parameters)
    reverse = reduce_measured_mechanical_sensitivity(reversed_sweep, parameters)
    assert forward.angle_interval_extrema == reverse.angle_interval_extrema
    assert forward.source_sweep_sha256 == reverse.source_sweep_sha256 == sweep.sweep_sha256


def test_interval_extrema_change_when_one_zone_has_a_local_mechanical_knee():
    parameters = _parameters()
    sweep = _sweep(parameters)
    angles = tuple(sorted(parameters.axis_angle_doe_deg))
    target_zone = ZONE_IDS[0]
    target_angle = angles[-1]
    changed = []
    for item in sweep.records:
        if item.zone_id == target_zone and item.record.axis_angle_deg == target_angle:
            changed.append(ZoneImpedanceRecord(item.zone_id, replace(item.record, measured_force_N=float(item.record.measured_force_N) + 0.20)))
        else:
            changed.append(item)
    result = reduce_measured_mechanical_sensitivity(FourZoneImpedanceSweep(parameters.parameter_sha256, tuple(changed)), parameters)
    final_interval = next(item for item in result.angle_interval_extrema if item.upper_angle_deg == target_angle)
    assert final_interval.maximum_abs_force_sensitivity.zone_id == target_zone
    assert final_interval.maximum_abs_force_sensitivity.upper_record_id == f"INTERVAL-{target_zone}-{target_angle:g}"
