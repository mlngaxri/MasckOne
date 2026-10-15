"""Synthetic inventory and electrical envelope arithmetic; no physical evidence."""
from copy import deepcopy
from pathlib import Path
import pytest
from masck_one.authority import load_authority
from masck_one.mass_balance import WATER_DENSITY_G_ML
from masck_one.core_sketch_contracts import CoreSketchError, load_manifest
from masck_one.core_sketch_resources import Bound, fixed, assess_resources, assess_electrical_envelope

ROOT = Path(__file__).resolve().parents[1]


def scenario():
    return deepcopy(load_manifest(ROOT)['resources']['scenarios'][0])


def test_consumed_water_is_not_prepared_on_head_charge():
    s = scenario()
    unknown = assess_resources(load_authority(), s)
    assert unknown['bounds']['session_water_ml']['low'] == 4
    assert unknown['bounds']['prepared_water_charge_ml'] == {
        'low': 4, 'high': None, 'unknowns': ['prepared_water_charge_ml']}
    s['inputs']['prepared_water_charge_ml'] = [6.5, 6.5]
    filled = assess_resources(load_authority(), s)
    assert filled['bounds']['wearable_session_fluid_mass_g']['low'] == pytest.approx(
        unknown['bounds']['wearable_session_fluid_mass_g']['low'] + 2.5 * WATER_DENSITY_G_ML)
    assert filled['bounds']['loaded_mass_g']['high'] is None
    assert filled['cg_z_mm'] is None
    s['inputs']['prepared_water_charge_ml'] = [3, 3]
    assert assess_resources(load_authority(), s)['screens']['water_demand_vs_prepared_charge'] == 'VIOLATES_LIMIT'


@pytest.mark.parametrize('key', ['optical_selected', 'thermal_selected'])
def test_missing_choice_cannot_remove_optional_load(key):
    s = scenario()
    del s[key]
    r = assess_resources(load_authority(), s)
    assert key + ':UNRESOLVED' in r['blockers']
    if key == 'optical_selected':
        assert 'optical_hardware_mass_g' in r['bounds']['dry_mass_g']['unknowns']
    else:
        assert r['bounds']['thermal_state_required_J']['high'] is None
        assert r['bounds']['dock_reset_energy_J']['high'] is None


@pytest.mark.parametrize('value', [0, 1, '', 'false', [], {}])
@pytest.mark.parametrize('key', ['optical_selected', 'thermal_selected'])
def test_selection_must_not_use_truthiness(key, value):
    s = scenario()
    s[key] = value
    with pytest.raises(CoreSketchError):
        assess_resources(load_authority(), s)


def electrical():
    plan = deepcopy(load_manifest(ROOT)['completion']['example_unresolved_am_plan'])
    envelope = {'background': {'average_power_W': [2, 2], 'peak_power_W': [4, 4]},
        'stages': [{'id': row['id'], 'duration_s': [10, 20],
            'average_power_W': [3, 5], 'peak_power_W': [6, 8]} for row in plan['stages']]}
    return plan, envelope


def test_background_runs_for_entire_sequential_routine_and_peak_lower_is_not_sum():
    p, e = electrical()
    r = assess_electrical_envelope(p, e)
    n = len(p['stages'])
    assert r['bounds']['routine_duration_s']['low'] == 10 * n
    assert r['bounds']['electrical_energy_Wh']['low'] == pytest.approx(50 * n / 3600)
    assert r['bounds']['electrical_energy_Wh']['high'] == pytest.approx(140 * n / 3600)
    assert r['bounds']['peak_power_W'] == {'low': 6, 'high': 12, 'unknowns': []}
    assert not r['hardware_execution_authorized']


@pytest.mark.parametrize('change', ['remove', 'extra', 'duplicate'])
def test_electrical_inventory_exactly_covers_selected_routine(change):
    p, e = electrical()
    if change == 'remove': e['stages'].pop()
    if change == 'extra': e['stages'].append(dict(e['stages'][0], id='extra'))
    if change == 'duplicate': e['stages'].append(dict(e['stages'][0]))
    with pytest.raises(CoreSketchError): assess_electrical_envelope(p, e)


def test_unknown_background_and_duration_do_not_disappear_even_with_zero_power():
    p, e = electrical()
    e['background'] = {}
    assert assess_electrical_envelope(p, e)['bounds']['electrical_energy_Wh']['high'] is None
    p, e = electrical()
    e['stages'][0]['duration_s'] = None
    e['stages'][0]['average_power_W'] = [0, 0]
    e['background']['average_power_W'] = [0, 0]
    r = assess_electrical_envelope(p, e)
    assert r['bounds']['electrical_energy_Wh']['high'] is None
    assert 'routine_duration_s:UNRESOLVED' in r['blockers']


@pytest.mark.parametrize('operation', [lambda: fixed(1e308) + fixed(1e308),
    lambda: fixed(1e308) * fixed(1e308), lambda: fixed(10**1000),
    lambda: Bound(float('nan'), None, ('x',))])
def test_nonfinite_inputs_and_derived_overflow_are_rejected(operation):
    with pytest.raises(CoreSketchError): operation()


def test_inconsistent_power_bounds_reject():
    p, e = electrical()
    e['stages'][0]['average_power_W'] = [9, 10]
    with pytest.raises(CoreSketchError): assess_electrical_envelope(p, e)


def test_prepared_charge_relational_screen_distinguishes_crossing_and_violation():
    s = scenario()
    s['inputs']['wearable_purge_water_ml'] = [0, 0]
    s['inputs']['prepared_water_charge_ml'] = [0, 6]
    assert assess_resources(load_authority(), s)['screens']['water_demand_vs_prepared_charge'] == 'INTERVAL_CROSSES_LIMIT'
    s['inputs']['prepared_water_charge_ml'] = [5, 6]
    assert assess_resources(load_authority(), s)['screens']['water_demand_vs_prepared_charge'] == 'WITHIN_MODEL_BOUND_NOT_PHYSICAL_PASS'
    # An unknown demand upper cannot conceal a known lower exceeding all charge.
    s['inputs']['wearable_purge_water_ml'] = None
    s['inputs']['prepared_water_charge_ml'] = [0, 3]
    assert assess_resources(load_authority(), s)['screens']['water_demand_vs_prepared_charge'] == 'VIOLATES_LIMIT'
