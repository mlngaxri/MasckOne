"""Synthetic records test logic only. They are not accepted product evidence."""
from copy import deepcopy
from pathlib import Path
import pytest
from masck_one.core_sketch_contracts import (
    CoreSketchError, PHASES, CONTACT_CLASSES, INVALIDATION_EVENTS, digest,
    load_manifest, validate_convergence, assess_completion, validate_plan,
    assess_readiness, invalidate, assess_contacts, assess_integrity,
)
from masck_one.core_sketch_resources import Bound, fixed, read, screen, assess_resources
from masck_one.authority import load_authority

ROOT = Path(__file__).resolve().parents[1]


def evidence(classes, scope, prefix):
    return [dict(id=prefix+c, **{'class':c}, scope=scope, accepted=True, result='PASS') for c in classes]


def completed(scope='REDUCED_REGION_SURROGATE'):
    plan=deepcopy(load_manifest(ROOT)['completion']['example_unresolved_am_plan'])
    plan['scope']=scope
    if scope=='REDUCED_REGION_SURROGATE':
        plan['regions']=[r for r in plan['regions'] if r['id']=='left_cheek']
        for s in plan['stages']:s['regions']={'left_cheek':s['regions']['left_cheek']}
    ctx=digest(plan); ev=[]; rows={}
    base={'BENCH'} if scope=='REDUCED_REGION_SURROGATE' else {'BENCH','HUMAN'}
    for s in plan['stages']:
        rows[s['id']]={}
        for region, obligation in s['regions'].items():
            e=evidence(base|({'REG_CLAIM'} if s['kind']=='FACIAL_SPF' else set()),ctx+'/'+s['id']+'/'+region,s['id']+region)
            ev+=e
            rows[s['id']][region]={'state':'PROTECTED_PRESERVED' if obligation['requirement']=='PROTECTED' else 'COMPLETE','uncovered_subregions':[],'evidence_ids':[v['id'] for v in e]}
    registration=evidence(base,ctx+'/whole_face_registration','registration');ev+=registration
    obs={'plan_digest':ctx,'completed_order':[s['id'] for s in plan['stages']],'routine_state':'NORMAL_RELEASE_COMPLETED','stages':rows,'registration_evidence':[v['id'] for v in registration]}
    products=[dict(id=s['product_binding'],trust='VALIDATED',context_digest=ctx) for s in plan['stages'] if 'product_binding' in s]
    return plan,obs,products,ev


def ready():
    plan=completed()[0]
    for stage in plan['stages']:
        if 'product_binding' in stage:stage['product_binding']='p'
    binding={'routine_id':'synthetic','routine_revision':'1','schedule_context':'PM:test','stage_ids':[s['id'] for s in plan['stages']],'plan_digest':digest(plan),
      'product_bindings':[{'id':'p','sku':'synthetic','market':'test','identity_version':'1','slot':'a'}],
      'hardware_revision':'test','profile_revision':'test','authority_digest':'test-only'}
    expected=binding['product_bindings'][0]
    request={'plan':plan,'binding':binding,'thermal_stage':False,'resources':{'water_ml':1,'waste_free_ml':1,'usable_energy_Wh':1},'dose_requirements':{'p':{'min_ml':1,'max_ml':2}}}
    current={'binding':deepcopy(binding),'epoch':0,'invalidations':[],'faults':[],'wear_state':'CONFIRMED_ELIGIBLE',
      'stage_eligibility':{s['id']:'ELIGIBLE_FOR_EXACT_PLAN' for s in plan['stages']},
      'local':{k:True for k in ['clock_valid','profile_cache_verified','progress_known','controller_available']},
      'service':{k:'VERIFIED_COMPLETE' for k in ['cleaning','changeover','dry_path_service']},'resources':dict(request['resources']),
      'products':[{'id':'p','binding':deepcopy(expected),'trust':'VALIDATED','context_digest':digest(binding),'identity_status':'RESOLVED'}],
      'doses':[{'product_binding':'p','binding':deepcopy(expected),'dose_id':'dose-test','state':'SEALED_PREPARED','preservation':'VERIFIED','expires_at_s':100,'quantity_ml':1}]}
    receipt={'epoch':0,'binding_digest':digest(binding),'dose_digest':digest(current['doses']),'request_digest':digest(request),
       'prepared_at_s':0,'expires_at_s':100,'observations_expire_at_s':50,'service_receipt_id':'service-test'}
    for f in ['service','products','resources','stage_eligibility']:receipt[f+'_digest']=digest(current[f])
    return request,receipt,current


def test_positive_logic_distinguishes_reduced_from_whole_face():
    r=assess_completion(*completed());assert r['reduced_sequence_complete'] and not r['whole_routine_complete']
    r=assess_completion(*completed('WHOLE_FACE_CONCEPTUAL'));assert r['whole_routine_complete'] and not r['hardware_execution_authorized']


@pytest.mark.parametrize('state',['UNREACHABLE','OCCLUDED','PENDING','PARTIAL','UNSUPPORTED'])
def test_one_hole_cannot_hide_under_aggregate_coverage(state):
    p,o,ps,e=completed('WHOLE_FACE_CONCEPTUAL');o['aggregate_coverage']=100
    o['stages']['moisturise']['left_cheek']['state']=state
    assert not assess_completion(p,o,ps,e)['whole_routine_complete']


def test_subregion_hole_and_required_region_deletion_fail():
    p,o,ps,e=completed();o['stages']['moisturise']['left_cheek']['uncovered_subregions']=['support-shadow']
    assert not assess_completion(p,o,ps,e)['reduced_sequence_complete']
    p,o,ps,e=completed('WHOLE_FACE_CONCEPTUAL');p['regions']=p['regions'][1:]
    with pytest.raises(CoreSketchError):validate_plan(p)


def test_no_spf_promotion_from_non_claim_evidence():
    p,o,ps,e=completed();e=[r for r in e if r['class']!='REG_CLAIM']
    assert not assess_completion(p,o,ps,e)['reduced_sequence_complete']


@pytest.mark.parametrize('mutation',['product','source','release','protection','community'])
def test_completion_fails_closed(mutation):
    p,o,ps,e=completed('WHOLE_FACE_CONCEPTUAL')
    if mutation=='product':ps[0]['trust']='CHARACTERISED'
    if mutation=='source':o['plan_digest']='old'
    if mutation=='release':o['routine_state']='INTERRUPTED'
    if mutation=='protection':o['stages']['clean']['eye_protected']['state']='COMPLETE'
    if mutation=='community':ps[0]['promoted_by']='COMMUNITY'
    assert not assess_completion(p,o,ps,e)['whole_routine_complete']


def test_all_contact_classes_are_conservatively_blocked_until_inventory():
    m=load_manifest(ROOT);cs=m['contact']['classes'];regions={r['id'] for r in m['completion']['region_catalog'] if r['kind']=='CONCEPTUAL_SKIN'}
    assert not assess_contacts(cs,regions,[])['model_consistent']
    with pytest.raises(CoreSketchError):assess_contacts(cs[:-1],regions,[])
    assert set(c['id'] for c in cs)==CONTACT_CLASSES


def test_readiness_positive_and_offline_equivalence():
    req,receipt,current=ready();assert assess_readiness(req,receipt,current,10)['start_ready']
    current['internet_available']=False;current['cloud_available']=False
    assert assess_readiness(req,receipt,current,10)['start_ready']


@pytest.mark.parametrize('event',sorted(INVALIDATION_EVENTS))
def test_each_invalidation_revokes_cached_readiness(event):
    req,receipt,current=ready();current['cached_ready']=True
    current=invalidate(current,event)
    assert 'cached_ready' not in current
    assert not assess_readiness(req,receipt,current,10)['prepared_ready']


@pytest.mark.parametrize('field',['doses','products','service','resources','binding'])
def test_changed_actual_prepared_state_revokes_readiness(field):
    req,receipt,current=ready()
    if field=='doses':current[field][0]['dose_id']='another-dose'
    elif field=='products':current[field][0]['trust']='RESTRICTED'
    elif field=='service':current[field]['cleaning']='INTERRUPTED'
    elif field=='resources':current[field]['usable_energy_Wh']=0
    else:current[field]['routine_revision']='2'
    assert not assess_readiness(req,receipt,current,10)['prepared_ready']


def test_expiry_unknown_resource_and_thermal_requirement():
    req,receipt,c=ready();assert not assess_readiness(req,receipt,c,50)['prepared_ready']
    c['resources']['water_ml']=None;assert not assess_readiness(req,receipt,c,10)['prepared_ready']
    req['thermal_stage']=True
    with pytest.raises(CoreSketchError):assess_readiness(req,receipt,c,10)


@pytest.mark.parametrize('bad',[True,-1,float('nan'),float('inf')])
def test_nonfinite_and_boolean_quantities_cannot_pass(bad):
    req,receipt,c=ready();c['doses'][0]['quantity_ml']=bad
    with pytest.raises(CoreSketchError):assess_readiness(req,receipt,c,10)
    with pytest.raises(CoreSketchError):read([bad,bad],'bad')


def test_manifest_covers_all_p0_and_rejects_two_writers_and_false_physical_promotion():
    m=load_manifest(ROOT);backlog=(ROOT/'docs/CORE_SKETCH_EXECUTION_BACKLOG.md').read_text()
    assert validate_convergence(m,backlog)['p0_count']>0
    bad=deepcopy(m);bad['interfaces'][1]['contract_paths']=bad['interfaces'][0]['contract_paths'];bad['interfaces'][1]['writing_owner']='another-owner'
    with pytest.raises(CoreSketchError):validate_convergence(bad,backlog)
    bad=deepcopy(m);item=next(x for x in bad['p0_items'] if x['id']=='CS-010');item['state']='CLOSED';item['subsystem_ci']='PASS'
    with pytest.raises(CoreSketchError):validate_convergence(bad,backlog)
    item['state']='PROVE';item['physical_validation']='VALIDATED'
    with pytest.raises(CoreSketchError):validate_convergence(bad,backlog)


def test_unknown_budget_is_not_zero_or_a_pass_and_internal_transfer_not_added():
    authority=load_authority();s=load_manifest(ROOT)['resources']['scenarios'][0];r=assess_resources(authority,s)
    assert r['bounds']['loaded_mass_g']['high'] is None
    assert r['screens']['loaded_mass']=='UNRESOLVED' and r['cg_z_mm'] is None
    assert r['bounds']['loaded_mass_g']==r['bounds']['post_recovery_conservative_inventory_g']
    assert r['minimum_bulk_product_slots']==2
    assert screen(fixed(authority.number('mass','loaded_absolute_max_g')),authority.number('mass','loaded_absolute_max_g'),strict=True)=='VIOLATES_LIMIT'
    assert (read(None,'unmeasured')+fixed(2)).high is None
    assert (read(None,'unmeasured')*fixed(0)).high is None


def test_all_four_routine_families_include_expanded_resources():
    a=load_authority();ss=load_manifest(ROOT)['resources']['scenarios']
    results=[assess_resources(a,s) for s in ss]
    assert [r['minimum_bulk_product_slots'] for r in results]==[2,3,5,4]
    assert all(not r['model_consistent'] for r in results)
    assert results[2]['bounds']['thermal_state_required_J']['high'] is None
    assert a.number('mass','cg_z_max_mm') < 30


def test_ready_cannot_execute_unavailable_stage_or_removed_required_product():
    req,receipt,c=ready();c['stage_eligibility']['moisturise']='UNSUPPORTED'
    assert not assess_readiness(req,receipt,c,10)['prepared_ready']
    req,receipt,c=ready();req['plan']['stages'][0]['product_binding']='unprepared-product'
    assert not assess_readiness(req,receipt,c,10)['prepared_ready']


def integrity_fixture():
    products=[];ev=[];routes=[]
    for i in ['cleanser','leaveon']:
        e=evidence({'BENCH','SUPPLIER'},'context/'+i,i);ev+=e
        products.append({'id':i,'identity':{'status':'RESOLVED'},'behavior':{'state':'CHARACTERISED','profile_binding':'test'},
         'compatibility':{'state':'PRESERVATION_VERIFIED'},'contamination':{'state':'VERIFIED_CLEAN'},
         'application':{'trust':'VALIDATED','promoted_by':'QUALIFIED_REVIEW'},'evidence_ids':[x['id'] for x in e]})
        routes.append({'id':i,'product':i,'nodes':[i+'-source',i+'-outlet'],'dead_volume_ml':0.01,'kind':'DELIVERY','source_binding_verified':True})
    return products,routes,ev,'context'


def test_integrity_rejects_shared_path_pumpability_and_passive_bypass():
    p,r,e,ctx=integrity_fixture();assert assess_integrity(p,r,e,ctx)['model_consistent']
    r[1]['nodes'][1]=r[0]['nodes'][1]
    assert not assess_integrity(p,r,e,ctx)['model_consistent']
    p,r,e,ctx=integrity_fixture();p[1]['application']['trust']='PUMPABLE'
    assert not assess_integrity(p,r,e,ctx)['model_consistent']
    p,r,e,ctx=integrity_fixture();r[0]['kind']='MIXED_WASTE'
    assert not assess_integrity(p,r,e,ctx)['model_consistent']
    p,r,e,ctx=integrity_fixture();r[0]['source_binding_verified']=False
    assert not assess_integrity(p,r,e,ctx)['model_consistent']


def test_trial_template_cannot_create_bench_or_spf_evidence():
    import json
    from masck_one.core_sketch_trial import assess_trial
    protocol=json.loads((ROOT/'docs/contracts/reduced_region_protocol.json').read_text())
    trial=json.loads((ROOT/'docs/contracts/reduced_region_trial_template.json').read_text())
    assert not assess_trial(protocol,trial)['candidate_for_independent_bench_review']
    protocol['independent_review_record']='SYNTHETIC_TEST_ONLY'
    protocol['limits']={'max_mass_balance_error_g':0.1,'max_carryover_fraction':0.1,'min_film_retention_fraction':0.8,'max_protected_deposit_g':0.01}
    trial['protocol_digest']=digest(protocol)
    trial['completed_order']=[s['id'] for s in trial['stages']]
    for s in trial['stages']:
        s['photograph_records']=['synthetic'];s['balance_calibration_record']='synthetic';s['unknown_or_occluded_cells']=[]
        for cell in s['cells']:
            for k in cell:
                if k!='id':cell[k]=0
            cell['covered']=True;cell['film_retention_fraction']=1
    r=assess_trial(protocol,trial)
    assert r['candidate_for_independent_bench_review'] and not r['spf_validated'] and not r['whole_face_complete']
    trial['stages'][-1]['cells'][0]['film_retention_fraction']=0.5
    assert not assess_trial(protocol,trial)['candidate_for_independent_bench_review']
