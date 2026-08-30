from dataclasses import replace

import pytest

from masck_one.actuator_frames import ActuatorFrameArchitecture, ActuatorFrameError, build_actuator_frame_architecture
from masck_one.boundary_release import build_verified_interface_boundary_topology
from masck_one.interface_attachment import build_interface_attachment_architecture
from masck_one.model import build_model
from masck_one.structural_frame import build_structural_frame_topology


def _architecture():
    model = build_model()
    boundaries = build_verified_interface_boundary_topology(
        model.authority,
        model.facial_surface,
        model.coverage_mesh,
        model.compliant_interface_topology,
    )
    attachment = build_interface_attachment_architecture(model.authority, boundaries)
    frame = build_structural_frame_topology(model.authority, attachment)
    architecture = build_actuator_frame_architecture(model.authority, frame)
    return model.authority, frame, architecture


def _complete(architecture):
    frames = tuple(
        replace(
            frame,
            origin_xyz_mm=(float(index), 0.0, 0.0),
            axis_azimuth_deg=0.0,
            structural_mount_datum_id=f"TEST_MOUNT_{index}",
            actuator_envelope_mm=(10.0, 10.0, 10.0),
        )
        for index, frame in enumerate(architecture.frames)
    )
    return replace(architecture, frames=frames)


def test_uppercase_source_digest_is_not_a_second_architecture_identity():
    _, _, architecture = _architecture()
    with pytest.raises(ActuatorFrameError, match="lowercase canonical SHA-256"):
        ActuatorFrameArchitecture(
            source_structural_frame_sha256=architecture.source_structural_frame_sha256.upper(),
            source_registered_mesh_sha256=architecture.source_registered_mesh_sha256,
            source_authority_revision=architecture.source_authority_revision,
            frames=architecture.frames,
            independent_zone_count=architecture.independent_zone_count,
            physical_validation_eligible=False,
            evidence_status=architecture.evidence_status,
        )


def test_hard_sweep_gate_rejects_stale_complete_architecture():
    authority, structural_frame, architecture = _architecture()
    complete = _complete(architecture)
    stale = replace(complete, source_structural_frame_sha256="a" * 64)
    with pytest.raises(ActuatorFrameError, match="stale for the current structural-frame topology"):
        stale.require_sweep_ready(structural_frame=structural_frame, authority=authority)


def test_hard_sweep_gate_rejects_stale_registered_mesh_on_complete_architecture():
    authority, structural_frame, architecture = _architecture()
    complete = _complete(architecture)
    stale = replace(complete, source_registered_mesh_sha256="b" * 64)
    with pytest.raises(ActuatorFrameError, match="registered-mesh provenance is stale"):
        stale.require_sweep_ready(structural_frame=structural_frame, authority=authority)


def test_hard_sweep_gate_accepts_current_complete_architecture():
    authority, structural_frame, architecture = _architecture()
    complete = _complete(architecture)
    complete.require_sweep_ready(structural_frame=structural_frame, authority=authority)
