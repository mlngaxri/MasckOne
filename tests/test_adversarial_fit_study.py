"""Exercise the campaign paths and refuse unsupported physical conclusions."""
from copy import deepcopy
import json
from pathlib import Path
import numpy as np
import pytest
from masck_one import adversarial_fit_proof as core
from masck_one.adversarial_fit_study import (
    Variation, FitProofError, endpoint_status, source_status, make_witness, replay,
    sparse_registration, metrics, false_seat_search, capability_registration,
    CAPABILITIES, pareto_front, build_case_set, write_manifest, validate_manifest,
)


def test_actual_adversarial_search_repeats_seed_and_bound():
    a=core.adversarial_search(generations=2,population=6)
    b=core.adversarial_search(generations=2,population=6)
    assert a==b and a['evaluations']==18
    nom=np.array(list(core.nominal_landmarks().values()))
    exact=core.pair_distance_lower_bound(core.warp(nom,Variation(**a['variation'])),nom)
    assert a['lower_bound_mm']==exact['lower_bound_mm']
    assert a['lower_bound_mm']>0 and not a['global_optimum_claimed']


def test_full_case_stencil_is_stable_and_not_population():
    cases=build_case_set()
    assert len(cases)==50 and cases==build_case_set()
    assert len(set(n for n,v in cases))==len(cases)
    assert sum(n.startswith('COUPLED') for n,v in cases)==16


def test_witness_replay_preserves_numerical_meaning():
    w=make_witness('ASYMMETRY',Variation(asymmetry=8))
    r=replay(json.loads(json.dumps(w)))
    assert r==w
    assert w['measurements']['max_mm']<1
    assert w['measurements']['surface']['z_span_mm']>9
    assert w['classification']['whole_product_fit']=='UNKNOWN'


@pytest.mark.parametrize('key',['snapshot_digest','main','code_hashes'])
def test_stale_witness_does_not_replay(key):
    w=make_witness('NOMINAL',Variation());w['provenance'][key]='stale'
    with pytest.raises(FitProofError,match='stale'):replay(w)


def test_missing_parameter_is_not_default_nominal():
    w=make_witness('NOMINAL',Variation());del w['parameters']['asymmetry']
    with pytest.raises(FitProofError,match='complete'):replay(w)


def test_false_eye_seating_does_not_certify_mouth():
    v=Variation(mouth_y=10);r=sparse_registration(v);m=metrics(v,r['pose'])
    assert r['observed_max_residual_mm']<.01
    assert m['residual_norm_mm']['MOUTH']>9
    assert m['max_mm']>m['rms_mm']
    assert r['whole_fit']=='UNKNOWN'


def test_false_surface_adversary_preserves_full_field():
    v=Variation(asymmetry=8);r=core.solve_registration(v,multistart=False)
    s=false_seat_search([('ASYMMETRY',v,r)])
    assert s['strongest']['metrics']['max_mm']<1
    assert s['strongest']['metrics']['surface']['maximum_absolute_z_mm']>4
    assert not s['false_seated_physical_state_proven']


def test_optimizer_failure_is_not_impossibility(monkeypatch):
    class Bad:
        x=np.array([100.,100.,0.,0.,0.,0.,0.])
        success=False
    monkeypatch.setattr(core,'minimize',lambda *a,**kw:Bad())
    r=core.solve_registration(Variation(),multistart=False)
    s=endpoint_status(r,3.)
    assert s['FINAL_REGISTRATION_FEASIBILITY']=='NUMERICAL_INDETERMINATE'
    assert s['PASSIVE_CAPTURE_STATUS']=='UNKNOWN'


def test_analytic_failure_survives_numerical_unknown():
    r={'status':'NUMERICAL_INDETERMINATE','rigid_invariant_bound':{'lower_bound_mm':4.}}
    s=endpoint_status(r,3.)
    assert s['FINAL_REGISTRATION_FEASIBILITY']=='PROVEN_DIGITAL_FAILURE'
    assert not s['capacity_is_qualified'] and s['whole_product_fit']=='UNKNOWN'


def test_missing_source_is_unknown_and_not_executable(tmp_path):
    assert source_status(tmp_path)['status']=='UNKNOWN_SOURCE_GEOMETRY'
    assert source_status(tmp_path)['may_execute'] is False


def test_geometric_endpoint_never_promotes_capture():
    s=endpoint_status(core.solve_registration(Variation()),0.)
    assert s['FINAL_REGISTRATION_FEASIBILITY']=='NUMERICAL_CANDIDATE'
    assert s['PASSIVE_CAPTURE_STATUS']=='UNKNOWN' and not s['continuous_acquisition_proved']


@pytest.mark.parametrize('name',['GLOBAL_Z10','XY8','ANGLES6','BILATERAL_Z5','LOCAL_NORMAL5'])
def test_capability_is_not_an_authority_change_or_actual_fit(name):
    r=capability_registration(Variation(bridge_projection=8),CAPABILITIES[name])
    assert r['residual_mm'] is not None
    assert r['whole_fit']=='UNKNOWN' and r['passive_capture']=='UNKNOWN'
    if name in ('BILATERAL_Z5','LOCAL_NORMAL5'):
        assert r['rigid_lower_bound_mm'] is None # Rigid invariant cannot be reused after deformation.


def test_componentwise_pareto_rejects_costly_equivalent_and_unknown():
    def row(n,c,v,unknown=0):return {'capability':n,'cost':[c]*6,'within_assumed_capacity':{'3.0':v},'worst_attempted_residual_mm':4.,'numerical_unknowns':unknown}
    assert pareto_front([row('simple',0,4),row('wasteful',1,4),row('unknown',0,9,1)],3.)==['simple']


def test_manifest_detects_missing_modified_and_path_escape(tmp_path):
    (tmp_path/'a.json').write_text('{}');write_manifest(tmp_path,{'decision':'D_DIGITAL_INDETERMINATE'})
    assert validate_manifest(tmp_path)['decision']=='D_DIGITAL_INDETERMINATE'
    (tmp_path/'a.json').write_text('{"fake":true}')
    with pytest.raises(FitProofError):validate_manifest(tmp_path)
    m=json.loads((tmp_path/'manifest.json').read_text());m['artifacts']={'../escape':'no'}
    (tmp_path/'manifest.json').write_text(json.dumps(m))
    with pytest.raises(FitProofError):validate_manifest(tmp_path)


def test_no_failure_bracket_is_not_a_failure():
    r=core.boundary_search('eye_spacing',1.,100.,steps=1)
    assert r['status']=='NO_FAILURE_BRACKET'


def test_context_hash_exception_cannot_apply_to_geometry(tmp_path):
    p=tmp_path/'analysis/fit_proof';p.mkdir(parents=True)
    geom=tmp_path/'src';geom.mkdir();(geom/'x.py').write_text('changed')
    from hashlib import sha256
    (p/'sources.json').write_text(json.dumps({'consumed_files':[{'path':'src/x.py','sha256':'stale',
        'accepted_original_context_sha256':sha256(b'changed').hexdigest()}]}))
    with pytest.raises(FitProofError):core.source_snapshot(tmp_path)
