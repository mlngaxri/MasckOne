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
