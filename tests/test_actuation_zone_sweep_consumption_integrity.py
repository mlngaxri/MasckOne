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
    boundaries = build_verified_interface_boundary_topology(
        model.authority, model.facial_surface, model.coverage_mesh, model.compliant_interface_topology
    )
    attachment = build_interface_attachment_architecture(model.authority, boundaries)
    frame = build_structural_frame_topology(model.authority, attachment)
    actuators = build_actuator_frame_architecture(model.authority, frame)
    displacement = build_actuation_displacement_contract(model.authority, actuators)
    coupling = build_actuator_coupling_architecture(
        model.authority, actuators, displacement, frame, model.compliant_interface_topology
    )
    return build_actuation_parameter_set(model.authority, actuators, displacement, coupling)


def _point(parameters, zone_id, angle):
    return ZoneImpedanceRecord(
        zone_id,
        ImpedanceTestRecord(
            record_id=f"IMP-{zone_id}-{angle:g}",
            source_parameter_sha256=parameters.parameter_sha256,
            specimen_id="SYNTHETIC-NO-SPECIMEN",
            source_kind="PREDICTED",
            frequency_hz=parameters.clean_frequency_baseline_hz,
            commanded_displacement_pp_mm=parameters.displacement_pp_baseline_mm,
            axis_angle_deg=angle,
        ),
    )


def _sweep(parameters):
    records = tuple(
        _point(parameters, zone_id, angle)
        for zone_id in ZONE_IDS
        for angle in parameters.axis_angle_doe_deg
    )
    return FourZoneImpedanceSweep(parameters.parameter_sha256, records)


def test_validate_rechecks_unique_record_provenance_after_low_level_mutation():
    parameters = _parameters()
    sweep = _sweep(parameters)
    records = list(sweep.records)
    records[1] = ZoneImpedanceRecord(
        records[1].zone_id,
        replace(records[1].record, record_id=records[0].record.record_id),
    )
    object.__setattr__(sweep, "records", tuple(records))

    with pytest.raises(ActuationParameterError, match="record IDs must be unique"):
        sweep.validate(parameters)


def test_validate_rechecks_nested_zone_evidence_type_after_low_level_mutation():
    parameters = _parameters()
    sweep = _sweep(parameters)
    corrupted = sweep.records[0]
    object.__setattr__(corrupted, "record", object())

    with pytest.raises(ActuationParameterError, match="exact ImpedanceTestRecord"):
        sweep.validate(parameters)


def test_validate_rejects_coordinated_parameter_identity_corruption():
    parameters = _parameters()
    sweep = _sweep(parameters)

    # Simulate hostile low-level mutation of the frozen authority object followed by
    # coordinated rebinding of the sweep and every record to the resulting digest.
    # Digest agreement alone must not make an invalid authority object consumable.
    object.__setattr__(parameters, "physical_validation_eligible", True)
    corrupted_sha = parameters.parameter_sha256
    object.__setattr__(sweep, "source_parameter_sha256", corrupted_sha)
    for item in sweep.records:
        object.__setattr__(item.record, "source_parameter_sha256", corrupted_sha)

    with pytest.raises(ActuationParameterError, match="cannot be physical validation evidence"):
        sweep.validate(parameters)


def test_validate_rejects_coordinated_invalid_force_authority():
    parameters = _parameters()
    sweep = _sweep(parameters)

    object.__setattr__(parameters, "transient_force_requirement_N", 0.1)
    corrupted_sha = parameters.parameter_sha256
    object.__setattr__(sweep, "source_parameter_sha256", corrupted_sha)
    for item in sweep.records:
        object.__setattr__(item.record, "source_parameter_sha256", corrupted_sha)

    with pytest.raises(ActuationParameterError, match="Transient force requirement cannot be below continuous"):
        sweep.validate(parameters)
