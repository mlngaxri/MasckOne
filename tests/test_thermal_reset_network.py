from copy import deepcopy
import pytest
from masck_one.thermal_reset_physics import Store,dock_transient


def network(**changes):
    store=Store(5000.,.77,.875,140.,2.,6.,1.)
    state=dict(store_enthalpy_J=300.,plate_delta_K=4.,plate_heat_capacity_J_K=2.5,
               back_delta_K=-3.,back_heat_capacity_J_K=1.)
    kwargs=dict(contact_W_K={'L':.6,'R':.6},store_plate_W_K={'L':.22,'R':.22},
        sink_heat_capacity_J_K=160.,sink_ambient_W_K=.144,ambient_delta_K=-5.,
        plate_back_W_K=.012,back_ambient_W_K=.04,plate_ambient_W_K=.006,
        duration_s=600.)
    kwargs.update(changes)
    return dock_transient({'L':store,'R':store},{'L':state,'R':deepcopy(state)},**kwargs)


def test_shared_sink_conserves_all_energy_and_time_refinement():
    a=network();b=network(step_s=.1)
    assert abs(a['energy_balance_residual_J'])<1e-7
    assert a['zones']['L']['store_enthalpy_J']==pytest.approx(b['zones']['L']['store_enthalpy_J'],abs=1e-5)
    assert a['zones']['L']==a['zones']['R']
    assert a['heat_rejected_to_ambient_J']>0
    assert a['endpoint_is_not_hardware_readiness']
    assert not a['physical_readiness']


def test_unequal_contacts_are_not_averaged_and_charge_is_not_free():
    a=network(contact_W_K={'L':.03,'R':.6})
    assert a['zones']['L']['store_enthalpy_J']>a['zones']['R']['store_enthalpy_J']+30
    charged=network(charging_heat_W=.5)
    assert charged['charging_heat_J']==pytest.approx(300.,abs=1e-7)
    assert charged['final_sink_delta_K']>network()['final_sink_delta_K']


def test_ambient_above_solidus_cannot_be_declared_reset():
    a=network(ambient_delta_K=2.,duration_s=1800.)
    assert not a['both_stores_below_solidus_at_end']
    assert all(x['first_solidus_crossing_s'] is None for x in a['zones'].values())
    with pytest.raises(ValueError):network(step_s=1.)
    with pytest.raises(ValueError):network(contact_W_K={'L':.6})


def test_reset_endpoint_preserves_sink_and_plate_energy():
    a=network(duration_s=1800.)
    endpoint=a['first_both_stores_below_solidus']
    assert endpoint is not None
    assert endpoint['total_energy_relative_to_solidus_J']==pytest.approx(
        a['initial_total_energy_relative_to_solidus_J']+endpoint['charging_heat_J']-
        endpoint['heat_rejected_to_ambient_J'],abs=1e-7)
    assert endpoint['heat_rejected_to_ambient_J']<600.  # some heat still resides in finite sink
