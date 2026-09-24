import math
from dataclasses import replace
import pytest
from masck_one.thermal_reset_hardware import Parameters,cassette,build_thermal_reset_hardware,intersection
from masck_one.thermal_reset_physics import Store,FixtureInputs,transient,local_energy_budget,dewpoint_screen,dock_reset


def test_actual_void_excludes_fins_floor_lid_and_is_connected():
    parts,refs,m=cassette()
    void=refs['PCM_INTERNAL_VOID']
    assert len(void.Solids())==1 and void.isValid()
    assert 5000 < void.Volume() < 24*40*8
    for part in parts.values():assert intersection(part,void)<1e-7
    thicker=cassette(replace(Parameters(),fin_thickness_mm=.6))[2]['cavity_mm3']
    assert thicker<m['cavity_mm3']-350


def test_bench_components_and_full_continuous_withdrawal():
    parts,refs,m=build_thermal_reset_hardware()
    assert len(parts)==14
    for p in parts.values():assert p.isValid() and len(p.Solids())==1 and p.Volume()>0
    assert all(v==0 for v in m['internal_and_bench_motion_intersections_mm3'].values())
    assert not (set(parts)&set(refs))
    assert m['human_use_eligible'] is False
    assert m['whole_product_installation'].startswith('OPEN')


def test_invalid_dimensions_and_local_energy_cannot_be_hidden():
    for v in (float('nan'),float('inf'),0,-1):
        with pytest.raises(ValueError):Parameters(choke_length_mm=v)
    budget=local_energy_budget({'LEFT':500.,'RIGHT':500.},{'LEFT':600.,'RIGHT':100.})
    assert budget['global_margin_J']>0
    assert budget['all_stores_have_planning_reserve'] is False
    assert budget['minimum_margin_J']==-100.


def test_passive_reset_fails_when_ambient_or_charging_removes_driving_difference():
    assert dock_reset(300.,-1.,616.,1000.,.018,5.,.8,4.5)['reset_s'] is None
    a=dock_reset(300.,5.,616.,1000.,.018,5.,.8,4.5)
    b=dock_reset(300.,5.,616.,1000.,.018,5.,.8,4.5,.5)
    assert a['reset_s']>0 and b['reset_s'] is None


def test_dewpoint_domain_and_sensor_uncertainty():
    d=dewpoint_screen(25.,100.,25.,1.)
    assert d['dewpoint_C']==pytest.approx(25.) and d['state']=='CONDENSATION_POSSIBLE'
    assert dewpoint_screen(30.,90.,24.,1.)['state']=='CONDENSATION_LIKELY'
    with pytest.raises(ValueError):dewpoint_screen(25.,0.,20.,1.)


def test_transient_conserves_every_energy_path_and_preserves_exhaustion():
    store=Store(5000.,.77,.875,140.,2.,6.,1.)
    p=FixtureInputs(store,1.,.2,4.18,8.,.25,.35,.2,.006,.012,.04,1.,.01,.01,-5.,8.,107.,0.)
    a=transient(p,[('COOL',30.,0.),('WARM',10.,3.)])
    b=transient(p,[('COOL',30.,0.),('WARM',10.,3.)],step_s=.01)
    assert abs(a['energy_balance_residual_J'])<1e-7
    assert a['heater_energy_J']==pytest.approx(30.,abs=1e-8)
    assert a['phases'][-1]['store_enthalpy_J']==pytest.approx(b['phases'][-1]['store_enthalpy_J'],abs=1e-5)
    exhausted=transient(replace(p,initial_store_enthalpy_J=600.),[('COOL',5.,0.)])
    assert exhausted['store_exhaustion_s'] is not None
    assert exhausted['phases'][-1]['latent_planning_margin_J']<0
