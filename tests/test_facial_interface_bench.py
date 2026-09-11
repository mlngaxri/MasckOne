"""Hostile geometry checks for the unpowered inert-surrogate fixture only."""
from pathlib import Path
import json
import pytest
from masck_one.facial_interface_bench import (
    build, Parameters, FacialInterfaceError, common_volume, translation_bound, box,
)
from masck_one.facial_interface_occlusion import verify_sources, rectangle_clip

@pytest.fixture(scope='module')
def specimen():
    return build()


def test_valid_separate_material_and_continuous_clearance(specimen):
    material, refs, report = specimen
    assert len(material) == 14
    assert not set(material) & set(refs)
    assert all(s.isValid() and len(s.Solids()) == 1 and s.Volume() > 0 for s in material.values())
    assert not report['collision_blockers']
    assert max(report['collision_volumes_mm3'].values()) <= 1e-7
    assert {'NORMAL_LIFT','NORMAL_CASSETTE_SERVICE','DELIVERY_SCAN','SHUTTER_TRANSLATION'} <= refs.keys()


def test_each_required_coupon_cell_is_accessible_without_aggregate(specimen):
    _, refs, report = specimen
    cells=report['cell_access_fractions']
    assert len(cells) == 12
    assert all(abs(v-1) < 1e-7 for v in cells.values())
    # A small obstruction in just one cell must register even if global access is high.
    blocked=refs['CHEEK_COUPON_X0_Y0']
    assert common_volume(blocked, refs['DELIVERY_ACCESS']) > 0
    assert common_volume(blocked, refs['CHEEK_COUPON_X2_Y3']) == 0


def test_parking_pins_provide_positive_capture_not_overlap_attachment(specimen):
    m, _, _ = specimen
    head=m['clean_cassette'].translate((0,0,14))
    for side in ('left','right'):
        pin=m['parking_pin_'+side]
        assert common_volume(head,pin) == 0
        assert common_volume(head.translate((0,0,-.5)),pin) > 0


def test_endpoint_only_release_cannot_pass():
    moving=box(1,1,1,(0,0,0)); obstacle=box(1,1,1,(0,0,5))
    assert common_volume(moving,obstacle)==0
    assert common_volume(moving.translate((0,0,10)),obstacle)==0
    assert common_volume(translation_bound(moving,(0,0,10)),obstacle)>0


def test_unknown_mass_and_physical_completion_are_not_promoted(specimen):
    _, _, r=specimen
    assert r['wearable_added_mass_g'] is None
    assert r['bench_mass_g'] is None
    assert not r['whole_face_complete'] and not r['human_use_eligible']
    assert r['physical_evidence']=='NOT_PERFORMED'
    assert r['wearable_reaction_path'].startswith('BLOCKED')


@pytest.mark.parametrize('value',[float('nan'),float('inf'),0,-1,True])
def test_nonfinite_or_invalid_geometry_rejected(value):
    with pytest.raises(FacialInterfaceError):Parameters(normal_lift_mm=value)


def test_consumed_source_drift_is_not_silently_rebound(tmp_path):
    path=tmp_path/'docs/contracts';path.mkdir(parents=True)
    (tmp_path/'producer.py').write_text('changed')
    (path/'facial_interface_sources.json').write_text(json.dumps({'sources':[{
        'owner':'main','path':'producer.py','sha256':'stale'}]}))
    with pytest.raises(FacialInterfaceError,match='producer changed'):verify_sources(tmp_path)


def test_released_bindings_and_analytic_clipping():
    verify_sources(Path(__file__).resolve().parents[1])
    assert rectangle_clip([(0,0),(2,0),(0,2)],(0,1,0,1)) == 1
    assert rectangle_clip([(0,0),(2,0),(0,2)],(3,4,3,4)) == 0
