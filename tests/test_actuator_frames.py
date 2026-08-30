from dataclasses import replace

import pytest

from masck_one.actuator_frames import (
    ActuatorFrameArchitecture,
    ActuatorFrameError,
    ZONE_IDS,
    build_actuator_frame_architecture,
)
from masck_one.authority import load_authority
from masck_one.interface_attachment import build_interface_attachment_architecture
from masck_one.interface_topology import build_interface_topology
from masck_one.structural_frame import build_structural_frame_topology


def _authority_and_frame():
    authority = load_authority()
    interface = build_interface_topology(authority)
    attachment = build_interface_attachment_architecture(authority, interface)
    frame = build_structural_frame_topology(authority, attachment)
    return authority, frame


def test_four_zone_contract_is_authority_bound_and_explicitly_not_sweep_ready():
    authority, structural_frame = _authority_and_frame()
    architecture = build_actuator_frame_architecture(authority, structural_frame)
    assert tuple(frame.zone_id for frame in architecture.frames) == ZONE_IDS
    assert architecture.independent_zone_count == 4
    assert architecture.source_structural_frame_sha256 == structural_frame.topology_sha256
    assert architecture.source_registered_mesh_sha256 == structural_frame.source_registered_mesh_sha256
    assert architecture.sweep_ready is False
    assert architecture.physical_validation_eligible is False
    assert all(frame.origin_xyz_mm is None for frame in architecture.frames)
    assert all(frame.actuator_envelope_mm is None for frame in architecture.frames)


def test_sweep_analysis_hard_fails_while_geometry_or_supplier_envelope_is_unresolved():
    authority, structural_frame = _authority_and_frame()
    architecture = build_actuator_frame_architecture(authority, structural_frame)
    with pytest.raises(ActuatorFrameError, match="sweep/collision analysis is blocked"):
        architecture.require_sweep_ready()


def test_valid_but_stale_structural_topology_hash_is_rejected():
    authority, structural_frame = _authority_and_frame()
    architecture = build_actuator_frame_architecture(authority, structural_frame)
    stale = replace(architecture, source_structural_frame_sha256="a" * 64)
    with pytest.raises(ActuatorFrameError, match="stale for the current structural-frame topology"):
        stale.validate_current_sources(structural_frame=structural_frame, authority=authority)


def test_registered_mesh_provenance_cannot_drift_independently():
    authority, structural_frame = _authority_and_frame()
    architecture = build_actuator_frame_architecture(authority, structural_frame)
    stale = replace(architecture, source_registered_mesh_sha256="b" * 64)
    with pytest.raises(ActuatorFrameError, match="registered-mesh provenance is stale"):
        stale.validate_current_sources(structural_frame=structural_frame, authority=authority)


def test_manifest_identity_changes_when_mount_contract_changes():
    authority, structural_frame = _authority_and_frame()
    architecture = build_actuator_frame_architecture(authority, structural_frame)
    first = architecture.frames[0]
    changed_first = replace(first, origin_status="UNRESOLVED_CHANGED_CONTRACT")
    changed = replace(architecture, frames=(changed_first,) + architecture.frames[1:])
    assert changed.architecture_sha256 != architecture.architecture_sha256


def test_digital_actuator_contract_cannot_claim_physical_validation():
    authority, structural_frame = _authority_and_frame()
    architecture = build_actuator_frame_architecture(authority, structural_frame)
    with pytest.raises(ActuatorFrameError, match="cannot be physical evidence"):
        ActuatorFrameArchitecture(
            source_structural_frame_sha256=architecture.source_structural_frame_sha256,
            source_registered_mesh_sha256=architecture.source_registered_mesh_sha256,
            source_authority_revision=architecture.source_authority_revision,
            frames=architecture.frames,
            independent_zone_count=architecture.independent_zone_count,
            physical_validation_eligible=True,
            evidence_status=architecture.evidence_status,
        )
