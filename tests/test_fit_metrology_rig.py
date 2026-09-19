"""Test equipment only. Geometry checks never create a bench result."""
import pytest
from masck_one.fit_metrology_rig import build,valid,jaw_continuous_clearance,surface_specs,surface_part,Variation,matrix

@pytest.fixture(scope='module')
def assembly():return build()

def test_all_equipment_is_single_positive_brep(assembly):
    parts,cal=assembly
    assert all(valid(p.shape) for p in parts+[cal])
    assert all(p.manifest()['mass_g'] is None for p in parts)

def test_empty_profiles_never_become_coupons(assembly):
    host=next(p for p in assembly[0] if p.id=='COUPON_HOST')
    assert host.dimensions['coupon_state']=='EMPTY_UNKNOWN'
    assert host.dimensions['source_owner_geometry'] is None

def test_jaws_continuously_clear_host(assembly):
    results,_=jaw_continuous_clearance(assembly[0])
    assert all(r['status']=='CONTINUOUS_REFERENCE_CLEAR' for r in results.values())
    assert all(r['end_clearance_mm']>39 for r in results.values())

def test_no_manufactured_overlap(assembly):
    parts,_=assembly
    for i,a in enumerate(parts):
        for b in parts[:i]:
            ba,bb=a.world.BoundingBox(),b.world.BoundingBox()
            if any(getattr(ba,d+'max')<=getattr(bb,d+'min')+1e-8 or getattr(bb,d+'max')<=getattr(ba,d+'min')+1e-8 for d in 'xyz'):continue
            assert sum(s.Volume() for s in a.world.intersect(b.world).Solids())<1e-6,(a.id,b.id)

def test_controlled_pose_not_product_adjustment():
    with pytest.raises(ValueError):build((11,0,0,0,0,0))
    m=matrix((1,2,3,0,0,0));assert [r[3] for r in m[:3]]==[1,2,3]

def test_witness_surfaces_source_bound():
    s=surface_specs();assert len(s)==6
    assert all(len(v['witness_sha256'])==64 for v in s.values())
    assert s['EYE_NEAREST_NONPASSING']['variation'].eye_spacing-s['EYE_NEAREST_CANDIDATE']['variation'].eye_spacing<.00005

def test_nominal_surface_and_calibration_not_anatomy():
    p=surface_part('TEST',Variation(),nx=7,ny=7)
    assert valid(p.shape)
    assert p.dimensions['sampled_approximation_max_mm']<1e-7
    assert not p.dimensions['anatomical_validation_eligible']
