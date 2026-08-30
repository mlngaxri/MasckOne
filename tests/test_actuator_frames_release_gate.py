from dataclasses import replace
import pytest
from masck_one.actuator_frames import ActuatorFrameArchitecture, ActuatorFrameError, build_actuator_frame_architecture
from masck_one.boundary_release import build_verified_interface_boundary_topology
from masck_one.interface_attachment import build_interface_attachment_architecture
from masck_one.model import build_model
from masck_one.structural_frame import build_structural_frame_topology

def _architecture():
    model=build_model(); boundaries=build_verified_interface_boundary_topology(model.authority,model.facial_surface,model.coverage_mesh,model.compliant_interface_topology); attachment=build_interface_attachment_architecture(model.authority,boundaries); frame=build_structural_frame_topology(model.authority,attachment); architecture=build_actuator_frame_architecture(model.authority,frame); return model.authority,frame,architecture

def _complete(architecture):
    frames=tuple(replace(frame,origin_xyz_mm=(float(index),0.0,0.0),axis_azimuth_deg=0.0,structural_mount_datum_id=f"TEST_MOUNT_{index}",actuator_envelope_mm=(10.0,10.0,10.0)) for index,frame in enumerate(architecture.frames)); return replace(architecture,frames=frames)

def test_uppercase_source_digest_is_not_a_second_architecture_identity():
    _,_,a=_architecture()
    with pytest.raises(ActuatorFrameError,match="lowercase canonical SHA-256"): ActuatorFrameArchitecture(source_structural_frame_sha256=a.source_structural_frame_sha256.upper(),source_registered_mesh_sha256=a.source_registered_mesh_sha256,source_authority_revision=a.source_authority_revision,frames=a.frames,independent_zone_count=a.independent_zone_count,physical_validation_eligible=False,evidence_status=a.evidence_status)

def test_hard_sweep_gate_rejects_stale_complete_architecture():
    authority,frame,a=_architecture(); stale=replace(_complete(a),source_structural_frame_sha256="a"*64)
    with pytest.raises(ActuatorFrameError,match="stale for the current structural-frame topology"): stale.require_sweep_ready(structural_frame=frame,authority=authority)

def test_hard_sweep_gate_rejects_stale_registered_mesh_on_complete_architecture():
    authority,frame,a=_architecture(); stale=replace(_complete(a),source_registered_mesh_sha256="b"*64)
    with pytest.raises(ActuatorFrameError,match="registered-mesh provenance is stale"): stale.require_sweep_ready(structural_frame=frame,authority=authority)

def test_hard_sweep_gate_rejects_stale_authority_revision_on_complete_architecture():
    authority,frame,a=_architecture(); stale=replace(_complete(a),source_authority_revision="STALE-REVISION")
    with pytest.raises(ActuatorFrameError,match="authority revision is stale"): stale.require_sweep_ready(structural_frame=frame,authority=authority)

def test_blank_mount_datum_cannot_masquerade_as_resolved():
    _,_,a=_architecture()
    with pytest.raises(ActuatorFrameError,match="mount datum identity must be a nonblank string"): replace(a.frames[0],structural_mount_datum_id="   ")

@pytest.mark.parametrize("field,value",[("origin_xyz_mm",(True,0.0,0.0)),("axis_azimuth_deg",True),("actuator_envelope_mm",(True,10.0,10.0))])
def test_boolean_numeric_aliases_cannot_resolve_actuator_geometry(field,value):
    _,_,a=_architecture()
    with pytest.raises(ActuatorFrameError): replace(a.frames[0],**{field:value})

@pytest.mark.parametrize("field,value",[("axis_angle_baseline_deg",True),("axis_angle_doe_deg",(50.0,55.0,True,67.0,72.0))])
def test_boolean_numeric_aliases_cannot_corrupt_actuator_angle_contract(field,value):
    _,_,a=_architecture()
    with pytest.raises(ActuatorFrameError,match="real finite numerics"): replace(a.frames[0],**{field:value})

@pytest.mark.parametrize("field,value",[("structural_mount_datum_id",17),("origin_status",17),("axis_status",True),("mount_status",object()),("envelope_status","   ")])
def test_nontext_or_blank_frame_metadata_fails_closed(field,value):
    _,_,a=_architecture()
    with pytest.raises(ActuatorFrameError): replace(a.frames[0],**{field:value})

@pytest.mark.parametrize("field,value",[("source_structural_frame_sha256",17),("source_registered_mesh_sha256",True),("source_authority_revision",17),("evidence_status",object()),("physical_validation_eligible",0),("independent_zone_count",True)])
def test_noncanonical_architecture_metadata_fails_with_contract_error(field,value):
    _,_,a=_architecture()
    with pytest.raises(ActuatorFrameError): replace(a,**{field:value})

def test_hard_sweep_gate_accepts_current_complete_architecture():
    authority,frame,a=_architecture(); _complete(a).require_sweep_ready(structural_frame=frame,authority=authority)
