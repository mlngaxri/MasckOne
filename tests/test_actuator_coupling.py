from dataclasses import replace

import pytest

from masck_one.actuation_sweep_contract import build_actuation_displacement_contract
from masck_one.actuator_coupling import (
    ActuatorCouplingArchitecture,
    ActuatorCouplingError,
    build_actuator_coupling_architecture,
)
from masck_one.actuator_frames import ZONE_IDS, build_actuator_frame_architecture
from masck_one.boundary_release import build_verified_interface_boundary_topology
from masck_one.interface_attachment import build_interface_attachment_architecture
from masck_one.model import build_model
from masck_one.structural_frame import build_structural_frame_topology
from masck_one.sweep_geometry import AABB, LinearSweep


def _inputs():
    model = build_model()
    boundaries = build_verified_interface_boundary_topology(
        model.authority,
        model.facial_surface,
        model.coverage_mesh,
        model.compliant_interface_topology,
    )
    attachment = build_interface_attachment_architecture(model.authority, boundaries)
    frame = build_structural_frame_topology(model.authority, attachment)
    actuator_architecture = build_actuator_frame_architecture(model.authority, frame)
    displacement = build_actuation_displacement_contract(model.authority, actuator_architecture)
    coupling = build_actuator_coupling_architecture(
        model.authority,
        actuator_architecture,
        displacement,
        frame,
        model.compliant_interface_topology,
    )
    return model, frame, actuator_architecture, displacement, coupling


def test_builds_four_zone_provenance_bound_coupling_architecture():
    model, frame, actuator_architecture, displacement, coupling = _inputs()
    assert tuple(zone.zone_id for zone in coupling.zones) == ZONE_IDS
    assert coupling.source_actuator_architecture_sha256 == actuator_architecture.architecture_sha256
    assert coupling.source_displacement_contract_sha256 == displacement.contract_sha256
    assert coupling.source_structural_frame_sha256 == frame.topology_sha256
    assert coupling.source_interface_topology_sha256 == model.compliant_interface_topology.topology_sha256
    assert coupling.physical_validation_eligible is False
    assert len(coupling.architecture_sha256) == 64
    assert all(not target.startswith("INTERFACE_OPENING_") for zone in coupling.zones for target in zone.target_contact_zone_ids)


def test_bilateral_contract_rejects_asymmetric_role_mapping():
    *_, coupling = _inputs()
    zones = list(coupling.zones)
    zones[1] = replace(zones[1], target_contact_zone_ids=("INTERFACE_GENERAL_FACE",))
    with pytest.raises(ActuatorCouplingError, match="symmetric target-role"):
        replace(coupling, zones=tuple(zones))


def test_stale_interface_and_structural_sources_fail_closed():
    model, frame, actuator_architecture, displacement, coupling = _inputs()
    stale_interface = replace(coupling, source_interface_topology_sha256="0" * 64)
    with pytest.raises(ActuatorCouplingError, match="stale for the compliant interface"):
        stale_interface.validate_current_sources(
            authority=model.authority,
            actuator_architecture=actuator_architecture,
            displacement_contract=displacement,
            structural_frame=frame,
            interface_topology=model.compliant_interface_topology,
        )
    stale_frame = replace(coupling, source_structural_frame_sha256="1" * 64)
    with pytest.raises(ActuatorCouplingError, match="stale for the structural frame"):
        stale_frame.validate_current_sources(
            authority=model.authority,
            actuator_architecture=actuator_architecture,
            displacement_contract=displacement,
            structural_frame=frame,
            interface_topology=model.compliant_interface_topology,
        )


def test_sweep_analysis_remains_blocked_until_iteration17_geometry_is_resolved():
    model, frame, actuator_architecture, displacement, coupling = _inputs()
    with pytest.raises(ActuatorCouplingError, match="sweep/collision analysis remains blocked"):
        coupling.require_sweep_analysis_ready(
            authority=model.authority,
            actuator_architecture=actuator_architecture,
            displacement_contract=displacement,
            structural_frame=frame,
            interface_topology=model.compliant_interface_topology,
        )


def _sweeps(*, colliding: bool):
    geometry_sha = "a" * 64
    sweeps = {}
    for index, zone_id in enumerate(ZONE_IDS):
        x = 0.0 if colliding and index == 0 else 20.0 + 20.0 * index
        sweeps[zone_id] = LinearSweep(
            source_id=zone_id,
            start_box=AABB((x, 0.0, 0.0), (x + 1.0, 1.0, 1.0), "MASCK_ONE_GLOBAL"),
            translation_xyz_mm=(1.0, 0.0, 0.0),
            source_geometry_sha256=geometry_sha,
            rotation_invariant=True,
        )
    expected = {zone_id: geometry_sha for zone_id in ZONE_IDS}
    return sweeps, expected


def test_collision_assertion_detects_continuous_sweep_interference():
    *_, coupling = _inputs()
    sweeps, expected = _sweeps(colliding=True)
    keepout = AABB((1.5, -1.0, -1.0), (2.5, 2.0, 2.0), "MASCK_ONE_GLOBAL")
    with pytest.raises(ActuatorCouplingError, match="interference detected"):
        coupling.assert_no_rigid_body_interference(
            sweeps_by_zone=sweeps,
            keepouts=(keepout,),
            expected_geometry_sha256_by_zone=expected,
        )


def test_collision_assertion_accepts_explicit_nonintersecting_synthetic_fixture_without_promoting_evidence():
    *_, coupling = _inputs()
    sweeps, expected = _sweeps(colliding=False)
    keepout = AABB((-10.0, -10.0, -10.0), (-5.0, -5.0, -5.0), "MASCK_ONE_GLOBAL")
    coupling.assert_no_rigid_body_interference(
        sweeps_by_zone=sweeps,
        keepouts=(keepout,),
        expected_geometry_sha256_by_zone=expected,
    )
    assert coupling.physical_validation_eligible is False


def test_collision_assertion_rejects_missing_zone_and_stale_geometry_identity():
    *_, coupling = _inputs()
    sweeps, expected = _sweeps(colliding=False)
    missing = dict(sweeps)
    missing.pop(ZONE_IDS[-1])
    with pytest.raises(ActuatorCouplingError, match="exactly one sweep"):
        coupling.assert_no_rigid_body_interference(
            sweeps_by_zone=missing,
            keepouts=(AABB((-10.0, -10.0, -10.0), (-5.0, -5.0, -5.0), "MASCK_ONE_GLOBAL"),),
            expected_geometry_sha256_by_zone=expected,
        )
    stale_expected = dict(expected)
    stale_expected[ZONE_IDS[0]] = "b" * 64
    with pytest.raises(Exception, match="stale"):
        coupling.assert_no_rigid_body_interference(
            sweeps_by_zone=sweeps,
            keepouts=(AABB((-10.0, -10.0, -10.0), (-5.0, -5.0, -5.0), "MASCK_ONE_GLOBAL"),),
            expected_geometry_sha256_by_zone=stale_expected,
        )


def test_constructor_rejects_noncanonical_source_hash_and_evidence_promotion():
    *_, coupling = _inputs()
    with pytest.raises(ActuatorCouplingError, match="canonical SHA-256"):
        replace(coupling, source_registered_mesh_sha256="A" * 64)
    with pytest.raises(ActuatorCouplingError, match="cannot be physical validation evidence"):
        replace(coupling, physical_validation_eligible=True)
