from dataclasses import replace
import math
import cadquery as cq
import pytest
import masck_one.realized_waste_cartridge as module
from masck_one.realized_waste_cartridge import (
    build_realized_waste_cartridge, LinerSeed, volume, cylinder, box,
    RealizedWasteCartridgeError,
)
from masck_one.waste_cartridge_analysis import local_bolt_sweeps, require_installed_service_clear, wall_separation

@pytest.fixture(scope='module')
def cartridge(): return build_realized_waste_cartridge()

def test_connected_capacity_is_actual_free_space_clear_of_released_shell_and_all_protected_zones(cartridge):
    cartridge.validate()
    assert cartridge.installed_geometric_free_capacity_mL >= 35
    assert len(cartridge.installed_free_cavity_reference.val().Solids()) == 1
    assert volume(cartridge.installed_free_cavity_reference.intersect(cartridge.dry_retention_reference)) == pytest.approx(0,abs=1e-7)
    assert volume(cartridge.installed_free_cavity_reference.intersect(cartridge.vent_clearance_reference)) == pytest.approx(0,abs=1e-7)
    assert wall_separation(cartridge)['minimum_nested_side_separation_mm'] > .10

@pytest.mark.parametrize('field,value', [
    ('wall_mm',float('nan')),('floor_mm',float('inf')),('lid_mm',0),
    ('wall_mm',.01),('draft_deg',0),('collar_width_mm',float('-inf')),
])
def test_nonfinite_or_collapsed_seed_is_rejected(field,value):
    with pytest.raises(RealizedWasteCartridgeError): replace(LinerSeed(),**{field:value})

def test_package_and_dry_sockets_cannot_be_counted_as_cavity(cartridge):
    for fake in (cartridge.model.waste_cartridge_envelope.solid,
                 cartridge.installed_free_cavity_reference.union(cartridge.retention_pockets_reference)):
        poisoned=replace(cartridge,installed_free_cavity_reference=fake)
        with pytest.raises(RealizedWasteCartridgeError): poisoned.validate()

def test_capacity_reduction_and_disconnected_void_cannot_be_promoted(cartridge):
    shortened=cartridge.installed_free_cavity_reference.cut(box((200,200,3),(0,-80,-.35)))
    assert volume(shortened)/1000 < 35
    with pytest.raises(RealizedWasteCartridgeError):
        replace(cartridge,installed_free_cavity_reference=shortened).validate()

@pytest.mark.parametrize('field,value',[
    ('fluid_identity','FRESH_WATER'),('route_id','ROUTE_PUMP_TO_CARTRIDGE'),
    ('physical_validation_eligible',True),('source_backbone_manifest_sha256','0'*64),
])
def test_wrong_fluid_backflow_bypass_and_false_physical_or_source_receipts_fail(cartridge,field,value):
    with pytest.raises(RealizedWasteCartridgeError): replace(cartridge,**{field:value}).validate()

def test_deleted_device_parts_and_filled_inlet_are_rejected(cartridge):
    with pytest.raises(RealizedWasteCartridgeError):
        replace(cartridge,device_parts={}).validate()
    plugged=cartridge.body_solid.union(cylinder((-37,-82,14),(1,0,0),2,2.4))
    with pytest.raises(RealizedWasteCartridgeError): replace(cartridge,body_solid=plugged).validate()

def test_stale_source_is_rejected_before_geometry(monkeypatch):
    monkeypatch.setattr(module,'SOURCE_GIT_BLOB_IDENTITIES',(('config/masck_one_authority.yaml','0'*40),))
    with pytest.raises(RealizedWasteCartridgeError,match='source moved'): build_realized_waste_cartridge()

def test_bolt_retraction_is_continuous_but_does_not_promote_device_service(cartridge):
    assert len(local_bolt_sweeps(cartridge)) == 2
    with pytest.raises(RealizedWasteCartridgeError,match='installed service remains blocked'):
        require_installed_service_clear(cartridge)

def test_positive_bolts_block_unauthorized_axial_cartridge_movement(cartridge):
    moved=cartridge.closure_solid.translate((0,0,-1))
    assert all(volume(moved.intersect(cartridge.device_parts[n+'_bolt']))>1e-4 for n in ('left','right'))
    assert all(volume(moved.intersect(cartridge.device_parts[n+'_bolt'].translate((s*2,0,0))))<1e-7
               for n,s in [('left',-1),('right',1)])

def test_key_blocks_reversed_orientation(cartridge):
    wrong=cartridge.closure_solid.rotate((0,-80,0),(0,-80,1),180)
    assert volume(wrong.intersect(cartridge.device_parts['key_tongue'])) > 1e-4
    assert volume(cartridge.closure_solid.intersect(cartridge.device_parts['key_tongue'])) < 1e-7

def test_manifest_separates_candidate_material_and_references_from_physical_evidence(cartridge):
    report=cartridge.manifest()
    assert report['parts']['cavity']['role']=='REFERENCE_ONLY'
    assert report['parts']['body']['role']=='CANDIDATE_MATERIAL'
    assert report['retained_capacity_mL'] is None
    assert report['physical_validation_eligible'] is False
    assert report['development_assembly_material_eligible'] is False
    assert report['digital_mvp_cartridge_dfm_ready'] is False
    assert report['continuous_service_motion_realized'] is False

def test_body_closure_and_cavity_step_roundtrip(cartridge,tmp_path):
    for name in ('body_solid','closure_solid','installed_free_cavity_reference'):
        s=getattr(cartridge,name);path=tmp_path/(name+'.step')
        cq.exporters.export(s,str(path));t=cq.importers.importStep(str(path))
        assert t.val().isValid() and len(t.val().Solids())==1
        assert volume(t)==pytest.approx(volume(s),rel=0,abs=1e-4)

def test_rebuild_repeats_source_bound_geometry_within_kernel_resolution(cartridge):
    again=build_realized_waste_cartridge()
    assert again.source_backbone_manifest_sha256==cartridge.source_backbone_manifest_sha256
    assert set(again.review_shapes())==set(cartridge.review_shapes())
    for name,s in again.review_shapes().items():
        original=cartridge.review_shapes()[name]
        assert len(s.val().Solids())==len(original.val().Solids())
        assert volume(s)==pytest.approx(volume(original),rel=0,abs=1e-8)
