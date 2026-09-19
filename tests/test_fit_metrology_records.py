from copy import deepcopy
import pytest
from masck_one.fit_metrology_records import *


def fixture():
    # Explicitly SYNTHETIC method fixtures, not real qualified limits or receipts.
    sources={'rig':'a'*64,'surface':'b'*64,'owner_coupon':'c'*64}
    c={'max_residual_mm':{'sparse':1.,'field':1.},'required_support_ids':['L','R'],
       'required_field_cells':['A','B'],'required_sparse_ids':['EL','ER','M'],'required_force_channels':[], 'trajectory_max_gap_s':.1}
    cr={'id':'SYNTHETIC_CRITERIA','sha256':canonical_hash(c)};c['receipt']=cr
    cal={'id':'SYNTHETIC_CAL','sha256':'d'*64};method={'id':'SYNTHETIC_METHOD','sha256':'e'*64}
    registry={r['id']:{**r,'qualified':True,'evidence_class':'BENCH','kind':kind}
        for r,kind in [(cr,'BENCH_CRITERIA'),(cal,'CALIBRATION'),(method,'MEASUREMENT_METHOD')]}
    pose=[estimate(0,.001,'mm' if i<3 else 'deg') for i in range(6)]
    r=empty_record();r.update(record_origin='SYNTHETIC_TEST_FIXTURE',run_id='TEST',rig_revision='R1',fixture_revision='F1',
        source_main='f'*40,surface_witness_id='NOMINAL',source_identities=sources,coupon_identities={'pair':'c'*64},
        calibration_receipt=cal,processing_receipt=method,criteria_receipt=cr,repeat_index=0,
        commanded_initial_pose=[0]*6,measured_initial_pose=pose,final_pose=pose,
        disengagement={'time_s':0.,'constrained_dofs':[],'clamps_clear':True,'jaws_clear':True,'guard_contact':False},
        trajectory=[{'time_s':t,'pose':pose} for t in (-.1,0,.1)],trajectory_max_gap_s=.1,
        contact_sequence=[],support_observations={k:{'displacement':estimate(0,.001)} for k in ['L','R']},
        sparse_residuals={k:estimate(.1,.01) for k in ['EL','ER','M']},field_residuals={k:estimate(.2,.01) for k in ['A','B']},
        required_field_cells=['A','B'],full_field_file={'path':'TEST_SCAN','sha256':'1'*64},
        protected_surrogate_contacts=False,support_loss=False,multiple_terminal_states=False,
        calibration_error_mm=estimate(0,.001),fixture_deflection_mm=estimate(0,.001))
    context={'schema':SOURCE_CONTEXT_REVISION,'source_main':r['source_main'],
             'rig_revision':r['rig_revision'],'fixture_revision':r['fixture_revision'],
             'surface_witness_id':r['surface_witness_id'],'mode':r['mode'],
             'source_identities':deepcopy(sources),'coupon_identities':deepcopy(r['coupon_identities'])}
    return r,c,registry,context


def test_nominal_calibration_no_physical_result():
    x=analyze(*fixture());assert x['status']=='BENCH_CRITERION_PASS';assert x['physical_result'] is None

@pytest.mark.parametrize('field,value',[
 ('field_residuals',None),('source_identities',{}),('full_field_file',None),('support_observations',None),
 ('fixture_deflection_mm',None),('measured_initial_pose',None),('trajectory',[]),('calibration_receipt',None)])
def test_missing_never_zero(field,value):
    r,c,g,s=fixture();r[field]=value;assert analyze(r,c,g,s)['status']=='MISSING_REQUIRED_EVIDENCE'


def test_sparse_success_cannot_hide_surface_failure():
    r,c,g,s=fixture();r['field_residuals']['B']=estimate(12,.01)
    out=analyze(r,c,g,s);assert out['status']=='BENCH_CRITERION_FAIL';assert out['diagnostics']['full_field_exceeds_sparse_resolved']

@pytest.mark.parametrize('field',['protected_surrogate_contacts','support_loss','multiple_terminal_states'])
def test_observed_failures(field):
    r,c,g,s=fixture();r[field]=True;assert analyze(r,c,g,s)['status']=='BENCH_CRITERION_FAIL'


def test_constraint_remaining_invalidates_capture():
    r,c,g,s=fixture();r['disengagement']['constrained_dofs']=['ROLL'];assert analyze(r,c,g,s)['status']=='MISSING_REQUIRED_EVIDENCE'


def test_source_mismatch():
    r,c,g,s=fixture();r['source_identities']['rig']='9'*64;assert analyze(r,c,g,s)['status']=='MISSING_REQUIRED_EVIDENCE'


def test_bias_or_fixture_uncertainty_prevents_pass():
    for field in ['calibration_error_mm','fixture_deflection_mm']:
        r,c,g,s=fixture();r[field]=estimate(.8,.5);assert analyze(r,c,g,s)['status']=='INCONCLUSIVE'


def test_uncertainty_larger_than_difference():
    r,c,g,s=fixture();r['field_residuals']={k:estimate(.3,1) for k in ['A','B']}
    out=analyze(r,c,g,s);assert out['status']=='INCONCLUSIVE';assert not out['diagnostics']['full_field_exceeds_sparse_resolved']


def test_optional_force_absent_is_explicit():
    r,c,g,s=fixture();assert r['force_channels'] is None;assert analyze(r,c,g,s)['status']=='BENCH_CRITERION_PASS'


def test_required_force_missing_and_saturated():
    for f in [None,{'LOAD':{'value':3,'uncertainty':.1,'units':'N','quality':'SATURATED'}}]:
        r,c,g,s=fixture();c['required_force_channels']=['LOAD'];c.pop('receipt')
        receipt={'id':'OTHER','sha256':canonical_hash(c)};c['receipt']=receipt;r['criteria_receipt']=receipt
        g['OTHER']={**receipt,'qualified':True,'evidence_class':'BENCH','kind':'BENCH_CRITERIA'}
        r['force_channels']=f;assert analyze(r,c,g,s)['status']=='MISSING_REQUIRED_EVIDENCE'


def test_cad_cannot_qualify_a_measurement():
    r,c,g,s=fixture();g['SYNTHETIC_CAL']['evidence_class']='DIGITAL';assert analyze(r,c,g,s)['status']=='MISSING_REQUIRED_EVIDENCE'


def test_criteria_mutation_is_rejected():
    r,c,g,s=fixture();c['max_residual_mm']['field']=100;assert analyze(r,c,g,s)['status']=='MISSING_REQUIRED_EVIDENCE'


def test_repeatability_is_descriptive_not_qualification():
    rows=[{'repeat_kind':'REMOUNT','metric':estimate(x,.01)} for x in (.1,.11,.12)]
    out=repeatability(rows)['REMOUNT'];assert out['status']=='INCONCLUSIVE';assert out['observed_range']==pytest.approx(.02)


def test_blank_template_has_no_result():
    out=analyze(empty_record(),{}, {}, {});assert out['status']=='MISSING_REQUIRED_EVIDENCE';assert out['physical_result'] is None


def test_run_cannot_hide_unmeasured_patch():
    r,c,g,s=fixture();r['required_field_cells']=['A'];r['field_residuals'].pop('B')
    assert analyze(r,c,g,s)['status']=='MISSING_REQUIRED_EVIDENCE'


@pytest.mark.parametrize('field,value',[
    ('source_main','a'*40),('rig_revision','OTHER_RIG'),('fixture_revision','OTHER_FIXTURE'),
    ('surface_witness_id','OTHER_SURFACE'),('mode','IMPOSED'),
    ('coupon_identities',{'unrelated':'not-a-hash'}),('coupon_identities',{'pair':'9'*64}),
    ('coupon_identities',{}),('physical_result','BENCH_CRITERION_PASS'),
])
def test_article_metadata_and_coupons_cannot_be_swapped(field,value):
    r,c,g,s=fixture();r[field]=value
    out=analyze(r,c,g,s)
    assert out['status']=='MISSING_REQUIRED_EVIDENCE' and out['physical_result'] is None


@pytest.mark.parametrize('value',['false','true',0,1,[],{}])
def test_guard_contact_requires_observed_boolean(value):
    r,c,g,s=fixture();r['disengagement']['guard_contact']=value
    assert analyze(r,c,g,s)['status']=='MISSING_REQUIRED_EVIDENCE'


@pytest.mark.parametrize('field',['source_main','rig_revision','fixture_revision','surface_witness_id','mode','coupon_identities','source_identities','schema'])
def test_independent_context_cannot_omit_required_identity(field):
    r,c,g,s=fixture();s.pop(field)
    assert analyze(r,c,g,s)['status']=='MISSING_REQUIRED_EVIDENCE'


def test_legacy_hash_map_and_record_revision_fail_closed():
    r,c,g,s=fixture()
    assert analyze(r,c,g,s['source_identities'])['status']=='MISSING_REQUIRED_EVIDENCE'
    r['schema']='FIT_METROLOGY_RECORD_1'
    assert analyze(r,c,g,s)['status']=='MISSING_REQUIRED_EVIDENCE'


def attested_fixture():
    # Synthetic test of the measured-origin code path, never a bench result.
    r,c,g,s=fixture();r['record_origin']='BENCH_MEASURED'
    receipt={'id':'SYNTHETIC_RUN_ATTESTATION','sha256':run_payload_hash(r,s)}
    g[receipt['id']]={**receipt,'qualified':True,'kind':'BENCH_RUN','evidence_class':'BENCH'}
    r['run_receipt']=receipt
    return r,c,g,s,{'TEST_SCAN':'1'*64}


def test_relabelled_synthetic_record_does_not_create_measured_pass():
    r,c,g,s=fixture();r['record_origin']='BENCH_MEASURED'
    out=analyze(r,c,g,s,{'TEST_SCAN':'1'*64})
    assert out['status']=='MISSING_REQUIRED_EVIDENCE'
    assert out['physical_result'] is None and not out['run_attestation_verified']


def test_independent_run_receipt_binds_payload_and_source_context():
    r,c,g,s,artifacts=attested_fixture();out=analyze(r,c,g,s,artifacts)
    assert out['status']=='BENCH_CRITERION_PASS' and out['run_attestation_verified']
    assert out['run_payload_sha256']==r['run_receipt']['sha256']
    assert out['source_context_sha256']==canonical_hash(s)
    # The helper receipt is only a synthetic software fixture.


@pytest.mark.parametrize('field,value',[
    ('run_id','DIFFERENT_RUN'),('repeat_index',1),('record_origin','SYNTHETIC_TEST_FIXTURE'),
    ('contact_sequence',[{'time_s':0.,'contact':'OTHER'}]),('support_loss',True),
    ('full_field_file',{'path':'OTHER_SCAN','sha256':'2'*64}),
])
def test_changed_observation_cannot_reuse_run_attestation(field,value):
    r,c,g,s,a=attested_fixture();r[field]=value;out=analyze(r,c,g,s,a)
    assert not out['run_attestation_verified']
    assert out['physical_result'] is None


def test_matching_record_and_context_edit_still_invalidates_attestation():
    r,c,g,s,a=attested_fixture()
    r['rig_revision']=s['rig_revision']='OTHER_RIG'
    out=analyze(r,c,g,s,a)
    assert out['status']=='MISSING_REQUIRED_EVIDENCE' and not out['run_attestation_verified']


@pytest.mark.parametrize('mutation',[
    {'qualified':False},{'kind':'MEASUREMENT_METHOD'},{'evidence_class':'DIGITAL'},
])
def test_unqualified_or_wrong_evidence_cannot_attest_run(mutation):
    r,c,g,s,a=attested_fixture();g[r['run_receipt']['id']].update(mutation)
    assert analyze(r,c,g,s,a)['physical_result'] is None


@pytest.mark.parametrize('bad_hash',['z'*64,' '*64,123,None])
def test_receipt_hash_must_be_real_hexadecimal(bad_hash):
    r,c,g,s=fixture();r['calibration_receipt']['sha256']=bad_hash
    g['SYNTHETIC_CAL']['sha256']=bad_hash
    assert analyze(r,c,g,s)['status']=='MISSING_REQUIRED_EVIDENCE'


def test_run_receipt_does_not_replace_independent_scan_hash():
    r,c,g,s,a=attested_fixture()
    for artifacts in [None,{}, {'TEST_SCAN':'2'*64}]:
        out=analyze(r,c,g,s,artifacts)
        assert out['status']=='MISSING_REQUIRED_EVIDENCE' and out['physical_result'] is None


def test_shipped_templates_remain_unknown_and_match_schemas():
    import json
    from pathlib import Path
    from jsonschema import Draft202012Validator
    folder=Path(__file__).resolve().parents[1]/'analysis/fit_proof/metrology'
    record=json.loads((folder/'run_record_template.json').read_text())
    context=json.loads((folder/'source_context_template.json').read_text())
    assert record==empty_record() and context==empty_source_context()
    for data,schema in [(record,'run_record.schema.json'),(context,'source_context.schema.json')]:
        Draft202012Validator(json.loads((folder/schema).read_text())).validate(data)
    result=analyze(record,{}, {},context)
    assert result['status']=='MISSING_REQUIRED_EVIDENCE' and result['physical_result'] is None


@pytest.mark.parametrize('scan_state',['MATCHING','MODIFIED','OUTSIDE_RECORD_DIRECTORY'])
def test_cli_independently_hashes_scan_and_enforces_artifact_directory(tmp_path,scan_state):
    import json,os,subprocess,sys
    from pathlib import Path
    # Entire experiment, registry and attestation are synthetic test fixtures.
    r,c,g,s,a=attested_fixture()
    directory=tmp_path/'run';directory.mkdir()
    content=b'SYNTHETIC SOFTWARE TEST SCAN; NO BENCH MEASUREMENT'
    relative='../scan.txt' if scan_state=='OUTSIDE_RECORD_DIRECTORY' else 'scan.txt'
    scan=directory/relative;scan.write_bytes(content)
    r['full_field_file']={'path':relative,'sha256':sha256(content).hexdigest()}
    receipt={'id':'SYNTHETIC_CLI_ATTESTATION','sha256':run_payload_hash(r,s)}
    g[receipt['id']]={**receipt,'qualified':True,'kind':'BENCH_RUN','evidence_class':'BENCH'}
    r['run_receipt']=receipt
    if scan_state=='MODIFIED':scan.write_bytes(b'CHANGED SYNTHETIC SCAN')
    paths=[]
    for name,value in [('record',r),('criteria',c),('registry',g),('context',s)]:
        path=directory/(name+'.json');path.write_text(json.dumps(value));paths.append(str(path))
    env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[1]/'src'))
    result=subprocess.run([sys.executable,'-m','masck_one.fit_metrology_records',*paths],
                          env=env,check=True,capture_output=True,text=True)
    out=json.loads(result.stdout)
    assert out['run_attestation_verified']
    assert out['status']==('BENCH_CRITERION_PASS' if scan_state=='MATCHING' else 'MISSING_REQUIRED_EVIDENCE')
    if scan_state!='MATCHING':assert out['physical_result'] is None
