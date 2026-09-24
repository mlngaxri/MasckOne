"""Hostile numerical proofs, not anthropometric or physical acceptance tests."""
from dataclasses import replace
import math
from pathlib import Path
import numpy as np
import pytest
from masck_one.adversarial_fit_proof import (
    Variation, FitProofError, face, solve_registration, pair_distance_lower_bound,
    capacity_result, assess, alignment_rank, transform, nominal_landmarks, warp,
    source_snapshot, boundary_search,
)


def test_nominal_registration_is_not_whole_fit_or_physical_evidence():
    r=solve_registration(Variation(),multistart=False)
    assert r['max_residual_mm']<1e-6
    assert capacity_result(r,0)=='CANDIDATE_WITHIN_ASSUMED_CAPACITY'
    assert r['whole_fit']=='UNKNOWN' and r['landmark_residual_acceptance_mm'] is None
    assert assess({})['decision']=='D_DIGITAL_INDETERMINATE'


@pytest.mark.parametrize('change',[
    {'face_width':12},{'face_width':-12},{'cheek_prominence':10},{'cheek_prominence':-6},
    {'bridge_projection':10},{'asymmetry':6},{'nasal_width':4},{'mouth_y':6},
    {'mouth_width':6},{'brow_projection':8},{'forehead_curvature':6},
    {'lower_face_projection':8},{'chin_projection':8},{'jaw_width':8},
    {'cheek_curvature':4},{'local_curvature':4},
])
def test_variations_retain_independent_unknowns(change):
    v=Variation(**change);f=face(v)
    assert f['parameters']=={k:getattr(v,k) for k in f['parameters']}
    assert not f['anatomical_validation_eligible'] and f['population_percentile'] is None
    assert all(b['class']=='SYNTHETIC_ADVERSARIAL_EXPLORATION' for b in f['bounds'].values())


def test_pair_invariant_rejects_rigid_spacing_contradiction():
    a=np.array([[-10.,0,0],[10.,0,0]]);b=np.array([[-6.,0,0],[6.,0,0]])
    r=pair_distance_lower_bound(a,b)
    assert r['lower_bound_mm']==4
    # No translation or rotation can evade the same triangle-inequality bound.
    assert pair_distance_lower_bound(transform(a,[3,5,2,3,4,5]),b)['lower_bound_mm']==pytest.approx(4)


def test_moderate_combination_can_exceed_either_individual():
    a=solve_registration(Variation(face_width=8),multistart=False)
    b=solve_registration(Variation(eye_spacing=6),multistart=False)
    combined=solve_registration(Variation(face_width=8,eye_spacing=6),multistart=False)
    threshold=max(a['max_residual_mm'],b['max_residual_mm'])+1e-4
    assert capacity_result(a,threshold)=='CANDIDATE_WITHIN_ASSUMED_CAPACITY'
    assert capacity_result(b,threshold)=='CANDIDATE_WITHIN_ASSUMED_CAPACITY'
    assert capacity_result(combined,threshold)=='PROVEN_RIGID_CAPACITY_FAILURE'


@pytest.mark.parametrize('pose',[(5,0,0,0,0,0),(0,0,0,4,4,4),(0,0,9,0,0,0)])
def test_initial_pose_does_not_invent_capture_or_extra_z(pose):
    r=solve_registration(Variation(),initial=pose,multistart=False)
    assert math.hypot(*r['pose'][:2])<=5+1e-6
    assert r['pose'][2]==0 and r['passive_alignment']=='UNKNOWN'
    assert all(abs(x)<=4+1e-6 for x in r['pose'][3:])


def test_eye_only_alignment_leaves_a_rigid_mode_and_cannot_certify_mouth():
    points=np.array(list(nominal_landmarks().values()))
    rank=alignment_rank(points[:2])
    assert rank['rank']==5 and rank['unconstrained_rigid_modes']==1
    assert alignment_rank(points)['rank']==6
    # A false seated surrogate: exact eye datums with an independently moved mouth.
    false=points.copy();false[-1,1]+=8
    assert np.max(np.linalg.norm(false[:2]-points[:2],axis=1))==0
    assert pair_distance_lower_bound(false,points)['lower_bound_mm']>0


@pytest.mark.parametrize('field',['registered_face','protected_geometry','support','seal',
    'required_region_access','treatment_reach','thermal_reach','passive_constraints','emergency_release'])
def test_unknown_never_becomes_pass(field):
    keys=assess({})['unknown'];e={k:'PASS' for k in keys};e[field]='UNKNOWN'
    assert assess(e)['decision']=='D_DIGITAL_INDETERMINATE'


def test_required_region_failure_does_not_hide_behind_seating():
    e={k:'PASS' for k in assess({})['unknown']};e['required_region_access']='FAIL'
    assert assess(e)['decision']=='C_ARCHITECTURAL_FIT_DEFECT'


def test_missing_or_stale_sources_fail_closed(tmp_path):
    with pytest.raises(FileNotFoundError):source_snapshot(tmp_path)
    root=Path(__file__).resolve().parents[1];d=source_snapshot(root)
    import json
    p=tmp_path/'analysis/fit_proof';p.mkdir(parents=True)
    (p/'sources.json').write_text(json.dumps(d))
    with pytest.raises(FitProofError,match='source'):source_snapshot(tmp_path)


@pytest.mark.parametrize('value',[float('nan'),float('inf'),True,99])
def test_invalid_synthetic_parameters_are_not_faces(value):
    with pytest.raises(FitProofError):Variation(asymmetry=value)


def test_same_vector_same_geometry_identity():
    assert face(Variation(asymmetry=2))==face(Variation(asymmetry=2))


def test_normal_extension_is_counterfactual_not_current_adjustment():
    r=solve_registration(Variation(bridge_projection=4),extra_z_mm=10,multistart=False)
    assert r['pose_limits']['z_status']=='ABSTRACT_CAPABILITY_ONLY'
    assert r['adjustments']['existing_product_adjustments']==[]


@pytest.mark.parametrize('pair',[(0,1),(2,3),(0,4)])
def test_eye_nasal_mouth_near_capacity_boundary_is_local_not_aggregate(pair):
    p=np.array(list(nominal_landmarks().values()))[list(pair)]
    direction=(p[1]-p[0])/np.linalg.norm(p[1]-p[0])
    just_inside=p.copy();just_outside=p.copy()
    just_inside[1]+=direction*(6-1e-5);just_outside[1]+=direction*(6+1e-5)
    assert pair_distance_lower_bound(just_inside,p)['lower_bound_mm']<3
    assert pair_distance_lower_bound(just_outside,p)['lower_bound_mm']>3
    # Three millimetres here is a test capacity, not an anatomy/safety bound.


def test_asymmetry_can_hide_in_good_landmarks_while_surface_remains_unresolved():
    from masck_one.adversarial_fit_campaign import surface_demand
    v=Variation(asymmetry=8);r=solve_registration(v,multistart=False)
    demand=surface_demand(v,r)
    assert r['max_residual_mm']<1
    assert demand['maximum_absolute_z_mm']>3
    assert demand['seal_support_feasible']=='UNKNOWN'


def test_capture_serializes_and_does_not_promote_numerical_endpoint():
    import json
    from masck_one.adversarial_fit_campaign import capture_slices
    result=capture_slices(Variation(),grid=2)
    json.dumps(result,allow_nan=False)
    assert result['unknown']==12 and result['robustly_recoverable_proven']==0
    assert all(r['physically_recoverable'] is None and not r['continuous_path_proved'] for r in result['rows'])


def test_source_mesh_and_generated_mesh_are_reference_only():
    f=face(Variation(),include_mesh=True)
    assert f['surface']['kind']=='PLANAR_DEVELOPMENT_REFERENCE'
    assert not f['folded_cells'] and f['mesh_status']=='VALID_SYNTHETIC_REFERENCE_MESH'
