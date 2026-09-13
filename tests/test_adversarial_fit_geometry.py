"""Geometry-screen semantics. These tests confer no human fit evidence."""
import cadquery as cq
import pytest
from masck_one.adversarial_fit_geometry import common, protected_screen


@pytest.mark.parametrize('radius',[1.,2.,3.])
def test_exact_boundary_near_miss_and_intersection(radius):
    # Synthetic kernel fixture, not an anatomical aperture or a new safety limit.
    slab=cq.Workplane('XY').box(20,20,2).val()
    hole=cq.Workplane('XY').circle(radius+2).extrude(4,both=True).val()
    obstacle=slab.cut(hole)
    probe=cq.Workplane('XY').circle(radius).extrude(4,both=True).val()
    assert common(probe.translate((2-.01,0,0)),obstacle)<1e-7
    assert common(probe.translate((2+.01,0,0)),obstacle)>1e-7


def test_projected_domain_does_not_become_registered_anatomy():
    r,refs,s=protected_screen()
    assert s.isValid() and len(refs)==5
    assert all(x.isValid() for x in refs.values())
    assert all(v['rigid_clearance_mm']>0 for v in r['zones'].values())
    assert all(v['anatomical_depth']=='UNKNOWN' for v in r['zones'].values())
    assert r['whole_fit']=='UNKNOWN' and not r['physical_validation']
    assert r['required_domain']['every_cell_access_status']=='UNKNOWN'
    ids=sum(r['required_domain']['required_cells_by_source_region'].values(),[])
    assert len(ids)==len(set(ids)) and len(ids)>0
    from masck_one.adversarial_fit_proof import registration_pose_limits
    assert r['pose_validation']=={'status':'VALIDATED_RELEASED_OWNER_POSE',
                                  'limits':registration_pose_limits()}


@pytest.mark.parametrize('pose',[
    (5.000001,0,0,0,0,0),(4,4,0,0,0,0),(-5.000001,0,0,0,0,0),
    (0,0,1e-12,0,0,0),(0,0,-1e-12,0,0,0),
    (0,0,0,4.000001,0,0),(0,0,0,0,-4.000001,0),(0,0,0,0,0,4.000001),
    (float('nan'),0,0,0,0,0),(0,0,0,float('inf'),0,0),
    (0,0,0,0,0),(0,)*7,(True,0,0,0,0,0),None,'000000',
])
def test_invalid_pose_rejected_before_build_or_transform(pose,monkeypatch):
    from masck_one import adversarial_fit_geometry as geometry
    from masck_one.adversarial_fit_proof import FitProofError
    def forbidden():raise AssertionError('invalid pose reached CAD construction')
    monkeypatch.setattr(geometry,'build_model',forbidden)
    with pytest.raises(FitProofError):geometry.protected_screen(pose=pose)


@pytest.mark.parametrize('pose',[(3,4,0,4,-4,4),(-5,0,0,-4,4,-4),(0,0,0,0,0,0)])
def test_exact_released_pose_boundaries_are_inclusive(pose):
    from masck_one.adversarial_fit_proof import validate_owner_pose
    actual,receipt=validate_owner_pose(pose)
    assert actual==pose and receipt['limits']['z_status']=='OWNER_FIXED_ZERO'


def test_valid_nonzero_pose_screen_uses_released_limits():
    r,refs,s=protected_screen(pose=(3,4,0,4,-4,4))
    assert r['pose']==[3,4,0,4,-4,4]
    assert r['pose_validation']['status']=='VALIDATED_RELEASED_OWNER_POSE'
    assert len(refs)==5 and s.isValid()
    assert r['whole_fit']=='UNKNOWN' and not r['physical_validation']


def test_model_cannot_inject_expanded_authority():
    from copy import deepcopy
    from types import SimpleNamespace
    from masck_one.authority import load_authority
    from masck_one.adversarial_fit_proof import FitProofError
    data=deepcopy(load_authority().data)
    data['geometry']['misregistration']['translation_radial_max_mm']=500
    fake=SimpleNamespace(authority=SimpleNamespace(data=data))
    with pytest.raises(FitProofError,match='authority'):
        protected_screen(model=fake)
