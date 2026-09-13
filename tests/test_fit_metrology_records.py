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
    return r,c,registry,sources


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
    r,c,g,s=fixture();r['source_identities']=dict(s,rig='9'*64);assert analyze(r,c,g,s)['status']=='MISSING_REQUIRED_EVIDENCE'


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
