"""Validate the actual persisted campaign, not just helper implementations."""
import json
from pathlib import Path
import pytest
from masck_one.adversarial_fit_study import validate_manifest, replay, code_identity, CAPABILITIES

RESULTS=Path(__file__).resolve().parents[1]/'analysis/fit_proof/campaign_3ccd912'


def read(name):return json.loads((RESULTS/name).read_text())


def test_actual_campaign_manifest_and_visuals_are_complete():
    m=validate_manifest(RESULTS)
    assert m['synthetic_cases']==50 and m['adaptive_evaluations']==108
    assert m['initial_pose_cases']==183 and m['physical_results'] is None
    assert m['provenance']['code_hashes']==code_identity()
    for name in ['morphology_comparison.svg','nearest_boundary.svg','false_seat_surface.svg',
                 'initial_to_solved.svg','capture_slices.svg','parameter_sensitivity.svg']:
        assert name in m['artifacts']
        text=(RESULTS/name).read_text()
        assert '<svg' in text
        assert any(s in text.lower() for s in ('synthetic','unknown','conditional'))


def test_every_capability_uses_identical_case_ids_and_keeps_unknowns():
    cases={w['id'] for w in read('case_set.json')};d=read('adaptability.json')
    assert len(cases)==50 and len(d['candidates'])==9
    for row in d['candidates']:
        assert {r['case'] for r in row['cases']}==cases
        assert row['cost']==CAPABILITIES[row['capability']]['cost']
        assert row['actual_whole_fit_cases_resolved']==row['actual_capture_cases_resolved']==0
    assert d['recommendation']=='NO_DIGITAL_ADAPTABILITY_CHANGE_JUSTIFIED_YET'


@pytest.mark.parametrize('name',['adversary','eye_spacing_candidate','eye_spacing_failure',
    'false_surface','eyes_hide_mouth','asymmetry','initial_to_solved','nominal'])
def test_persisted_witness_regenerates(name):
    old=read('witnesses/'+name+'.json');new=replay(old)
    assert old['parameters']==new['parameters']
    assert old['classification']['PASSIVE_CAPTURE_STATUS']==new['classification']['PASSIVE_CAPTURE_STATUS']=='UNKNOWN'
    # Independent optimizer convergence comparison, not a human fit tolerance.
    assert new['measurements']['max_mm']==pytest.approx(old['measurements']['max_mm'],abs=1e-5)
    assert new['registration']['rigid_invariant_bound']['lower_bound_mm']==pytest.approx(
        old['registration']['rigid_invariant_bound']['lower_bound_mm'],abs=1e-10)


def test_nominal_and_coupled_capture_do_not_gain_physical_paths():
    d=read('capture.json')
    assert len(d['rows'])==147 and len(d['morphology_plus_pose_cases'])==36
    assert all(r['PASSIVE_CAPTURE_STATUS']=='UNKNOWN' for r in d['rows']+d['morphology_plus_pose_cases'])
    assert all(not r['continuous_acquisition_proved'] for r in d['rows']+d['morphology_plus_pose_cases'])


def test_adaptive_bound_is_proof_only_under_declared_capacity():
    w=read('witnesses/adversary.json')
    assert w['registration']['rigid_invariant_bound']['lower_bound_mm']>9.
    assert w['classification']['FINAL_REGISTRATION_FEASIBILITY']=='PROVEN_DIGITAL_FAILURE'
    assert w['classification']['capacity_is_qualified'] is False
    assert w['classification']['whole_product_fit']=='UNKNOWN'


def test_projected_receipt_never_claims_actual_anatomical_clearance():
    rows=read('projected_screens.json');assert len(rows)==3
    for row in rows:
        r=row['receipt'];assert r['whole_fit']=='UNKNOWN' and not r['physical_validation']
        assert r['required_domain']['every_cell_access_status']=='UNKNOWN'
        assert all(z['anatomical_depth']=='UNKNOWN' for z in r['zones'].values())
        assert any(z['status']=='PROJECTED_PROTECTED_CONFLICT' for z in r['zones'].values())
