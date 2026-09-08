from dataclasses import replace
import pytest
from masck_one.realized_waste_cartridge import build_realized_waste_cartridge, box, volume, RealizedWasteCartridgeError
from masck_one import cartridge_service_corridor as service

@pytest.fixture(scope='module')
def candidate():
    return build_realized_waste_cartridge()

@pytest.fixture(scope='module')
def corridor(candidate):
    return service.build_service_corridor(candidate)

def test_continuous_corridor_covers_all_material_and_clears_bound_shell_packages_and_frame(corridor):
    report,shapes=corridor
    assert report['material_outside_enclosures_mm3']==0
    assert report['frame_source_blob']==service.FRAME_SOURCE_BLOB
    assert set(shapes)=={'oblique_service_enclosures','oblique_service_sweeps'}
    assert len(shapes['oblique_service_sweeps'].val().Solids())==3
    assert 'CELL6_CURRENT_FRAME_CANDIDATE' in report['obstacle_intersections_mm3']
    assert all(v==0 for row in report['obstacle_intersections_mm3'].values() for v in row)
    assert report['continuous_installed_device_path_proven'] is False
    assert report['physical_validation_eligible'] is False
    assert report['wearer_present'] is False

def test_missing_enclosure_cannot_fake_continuous_coverage(candidate,corridor):
    enclosures=corridor[1]['oblique_service_enclosures'].val().Solids()
    with pytest.raises(RealizedWasteCartridgeError,match='does not contain'):
        service.require_material_coverage(candidate,enclosures[:1])

def test_pure_posterior_sweep_remains_rejected(candidate):
    with pytest.raises(RealizedWasteCartridgeError,match='corridor collision'):
        service.build_service_corridor(candidate,(0,0,-45))

def test_stale_frame_source_and_nonfinite_motion_fail_closed(candidate,monkeypatch):
    with pytest.raises(RealizedWasteCartridgeError,match='invalid service translation'):
        service.build_service_corridor(candidate,(0,float('nan'),-45))
    monkeypatch.setattr(service,'FRAME_SOURCE_BLOB','0'*40)
    with pytest.raises(RealizedWasteCartridgeError,match='stale frame'):
        service.build_service_corridor(candidate)

def test_key_is_blind_to_fluid_and_seal_reference_is_real_material(candidate):
    floor=box((1.8,1.0,.3),(-35.8,-80.5,16.6))
    roof=box((1.8,1.0,.2),(-35.8,-80.5,17.85))
    for land in (floor,roof,candidate.seal_land_reference):
        assert volume(land.cut(candidate.closure_solid))<1e-7
    through=box((2.4,1.2,3),(-36,-80.5,17.2))
    bad=replace(candidate,closure_solid=candidate.closure_solid.cut(through))
    with pytest.raises(RealizedWasteCartridgeError):
        bad.validate()
