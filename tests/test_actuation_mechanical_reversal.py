from dataclasses import replace

from masck_one.actuation_mechanical_reversal import reduce_measured_mechanical_reversals
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
    angles = tuple(sorted(parameters.axis_angle_doe_deg))
    for zone_index, zone_id in enumerate(ZONE_IDS):
        for angle_index, angle in enumerate(angles):
            records.append(ZoneImpedanceRecord(zone_id, ImpedanceTestRecord(
                record_id=f"REV-{zone_id}-{angle:g}", source_parameter_sha256=parameters.parameter_sha256,
                specimen_id="COUPLED-REVERSAL", source_kind="MEASURED",
                frequency_hz=parameters.clean_frequency_baseline_hz,
                commanded_displacement_pp_mm=parameters.displacement_pp_baseline_mm, axis_angle_deg=angle,
                measured_force_N=0.25 + zone_index * 0.01 + angle_index * 0.01,
                measured_displacement_pp_mm=parameters.displacement_pp_baseline_mm + angle_index * 0.002,
                measured_phase_deg=10.0 + angle_index, measured_temperature_C=28.0 + angle_index * 0.1,
                evidence_uri=f"evidence://bench/reversal/{zone_id}/{angle:g}")))
    return FourZoneImpedanceSweep(parameters.parameter_sha256, tuple(records))


def test_monotonic_measured_response_has_no_false_reversals():
    parameters = _parameters(); sweep = _sweep(parameters)
    result = reduce_measured_mechanical_reversals(sweep, parameters)
    assert result.source_parameter_sha256 == parameters.parameter_sha256
    assert result.source_sweep_sha256 == sweep.sweep_sha256
    assert result.zone_triplet_count == len(ZONE_IDS) * result.triplet_count
    assert result.force_reversal_count == 0
    assert result.displacement_reversal_count == 0
    assert result.phase_reversal_count == 0
    assert result.temperature_reversal_count == 0


def test_local_force_peak_is_exposed_with_exact_three_record_provenance():
    parameters = _parameters(); sweep = _sweep(parameters)
    zone_id = sorted(ZONE_IDS)[0]; angles = tuple(sorted(parameters.axis_angle_doe_deg)); center = angles[len(angles) // 2]
    records = tuple(
        ZoneImpedanceRecord(item.zone_id, replace(item.record, measured_force_N=float(item.record.measured_force_N) + 0.10))
        if item.zone_id == zone_id and float(item.record.axis_angle_deg) == center else item
        for item in sweep.records
    )
    result = reduce_measured_mechanical_reversals(FourZoneImpedanceSweep(parameters.parameter_sha256, records), parameters)
    hits = tuple(item for item in result.reversals if item.zone_id == zone_id and item.force_reversal)
    assert hits
    hit = next(item for item in hits if item.center_angle_deg == center)
    assert hit.lower_record_id == f"REV-{zone_id}-{hit.lower_angle_deg:g}"
    assert hit.center_record_id == f"REV-{zone_id}-{center:g}"
    assert hit.upper_record_id == f"REV-{zone_id}-{hit.upper_angle_deg:g}"


def test_reversal_reduction_is_order_independent():
    parameters = _parameters(); sweep = _sweep(parameters)
    reverse = FourZoneImpedanceSweep(parameters.parameter_sha256, tuple(reversed(sweep.records)))
    assert reduce_measured_mechanical_reversals(sweep, parameters) == reduce_measured_mechanical_reversals(reverse, parameters)
