"""Measured bench records only; no human-fit, treatment or production verdict.

Uncertainty is a bounded interval supplied by a qualified measurement method.
Worst-case interval addition avoids an unjustified independence assumption.
No numeric acceptance limit is shipped. A separate qualification registry must
bind criteria, calibration and processing methods to actual BENCH receipts.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import argparse
import json
import math
import re

STATUSES=('BENCH_CRITERION_PASS','BENCH_CRITERION_FAIL','INCONCLUSIVE','MISSING_REQUIRED_EVIDENCE')
DOFS=('X','Y','Z','ROLL','PITCH','YAW')
REVISION='FIT_METROLOGY_RECORD_2'
SOURCE_CONTEXT_REVISION='FIT_METROLOGY_SOURCE_CONTEXT_1'


def canonical_hash(value):
    return sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def finite(x):return not isinstance(x,bool) and isinstance(x,(float,int)) and math.isfinite(x)


def valid_hash(value,length=64):
    return isinstance(value,str) and re.fullmatch('[0-9a-f]{'+str(length)+'}',value) is not None


def identity_map(value,required=True):
    return (isinstance(value,dict) and (bool(value) or not required)
            and all(isinstance(k,str) and bool(k.strip()) and valid_hash(v) for k,v in value.items()))


def empty_source_context():
    """Independent article manifest. Empty fields never qualify a bench record."""
    return {'schema':SOURCE_CONTEXT_REVISION,'source_main':None,'rig_revision':None,
            'fixture_revision':None,'surface_witness_id':None,'mode':None,
            'source_identities':{},'coupon_identities':{}}


def run_payload_hash(record,source_context):
    """Bind every observation and article identity; exclude only the self receipt."""
    return canonical_hash({'record':{k:v for k,v in record.items() if k!='run_receipt'},
                           'source_context':source_context})


def estimate(value, uncertainty, units='mm'):
    if not finite(value) or not finite(uncertainty) or uncertainty<0:raise ValueError('finite value and nonnegative bounded uncertainty required')
    return {'value':float(value),'uncertainty':float(uncertainty),'units':units,'quality':'VALID'}


def interval(e,units='mm'):
    if not isinstance(e,dict) or e.get('quality')!='VALID' or e.get('units')!=units:raise ValueError('missing/invalid measurement')
    v,u=e.get('value'),e.get('uncertainty')
    if not finite(v) or not finite(u) or u<0:raise ValueError('invalid uncertainty')
    return v-u,v+u


def qualified(receipt,registry,kind):
    """Registry is supplied independently of the run; run booleans are not trust."""
    if (not isinstance(receipt,dict) or not isinstance(registry,dict)
            or not isinstance(receipt.get('id'),str) or not receipt['id'].strip()
            or not valid_hash(receipt.get('sha256'))):return False
    known=registry.get(receipt.get('id'))
    return (isinstance(known,dict) and known.get('sha256')==receipt.get('sha256')
            and known.get('evidence_class')=='BENCH' and known.get('kind')==kind
            and known.get('qualified') is True)


def empty_record():
    return {'schema':REVISION,'record_origin':'NO_PHYSICAL_RESULT','run_id':None,
        'rig_revision':None,'fixture_revision':None,'source_main':None,
        'surface_witness_id':None,'source_identities':{},'coupon_identities':{},
        'calibration_receipt':None,'processing_receipt':None,'criteria_receipt':None,'run_receipt':None,
        'mode':'ACQUISITION','repeat_index':None,'commanded_initial_pose':None,
        'measured_initial_pose':None,'final_pose':None,
        'disengagement':{'time_s':None,'constrained_dofs':None,'clamps_clear':None,'jaws_clear':None,'guard_contact':None},
        'trajectory':None,'trajectory_max_gap_s':None,'contact_sequence':None,
        'support_observations':None,'force_channels':None,
        'sparse_residuals':None,'field_residuals':None,'required_field_cells':None,
        'full_field_file':None,'protected_surrogate_contacts':None,
        'support_loss':None,'multiple_terminal_states':None,
        'calibration_error_mm':None,'fixture_deflection_mm':None,
        'environment':{},'missing_data_reasons':{},'physical_result':None}


def analyze(record,criteria,registry,expected_sources,artifact_hashes=None):
    """expected_sources is an independently supplied, versioned article context.

    A BENCH_RUN registry receipt must attest the exact record/context payload
    before any measured-result field can be populated. Registry qualification
    itself remains an external evidence-authority responsibility.
    """
    missing=[];ambiguous=[];fail=[];diagnostics={};metrics={}
    def need(ok,reason):
        if not ok:missing.append(reason)
    need(record.get('schema')==REVISION,'record schema')
    need(record.get('record_origin') in ('BENCH_MEASURED','SYNTHETIC_TEST_FIXTURE'),'no physical measurements supplied')
    need(record.get('physical_result') is None,'input cannot supply its own physical verdict')
    for key in ('run_id','rig_revision','fixture_revision','source_main','surface_witness_id'):
        need(isinstance(record.get(key),str) and bool(record[key].strip()),key)
    context=expected_sources if isinstance(expected_sources,dict) else {}
    need(context.get('schema')==SOURCE_CONTEXT_REVISION,'independent source context required')
    need(valid_hash(context.get('source_main'),40),'invalid expected release commit')
    for key in ('source_main','rig_revision','fixture_revision','surface_witness_id','mode'):
        expected=context.get(key)
        need(isinstance(expected,str) and bool(expected.strip()) and record.get(key)==expected,
             'source context mismatch: '+key)
    supplied=record.get('source_identities')
    need(identity_map(context.get('source_identities')),'invalid expected source hashes')
    need(supplied==context.get('source_identities'),'source identity/hash mismatch or absent')
    coupons=context.get('coupon_identities')
    need(identity_map(coupons,required=record.get('mode')=='ACQUISITION'),'expected coupon identities absent or invalid')
    need(record.get('coupon_identities')==coupons,'coupon identity/hash mismatch or absent')
    need(isinstance(record.get('repeat_index'),int) and not isinstance(record.get('repeat_index'),bool) and record['repeat_index']>=0,'repeat index')
    for field,kind in [('calibration_receipt','CALIBRATION'),('processing_receipt','MEASUREMENT_METHOD'),('criteria_receipt','BENCH_CRITERIA')]:
        need(qualified(record.get(field),registry,kind),field+' not independently qualified')
    need(criteria.get('receipt')==record.get('criteria_receipt'),'criteria receipt mismatch')
    # A receipt must bind the actual criteria, not just a reused identifier.
    expected_criteria_hash=canonical_hash({k:v for k,v in criteria.items() if k!='receipt'})
    need(record.get('criteria_receipt',{}).get('sha256')==expected_criteria_hash if isinstance(record.get('criteria_receipt'),dict) else False,'criteria content hash')
    attestation=record.get('run_receipt')
    run_hash=run_payload_hash(record,context)
    attested=(qualified(attestation,registry,'BENCH_RUN')
              and attestation.get('sha256')==run_hash)
    if record.get('record_origin')=='BENCH_MEASURED':
        need(attested,'measured run not independently attested at exact record/context hash')
    for p in ('measured_initial_pose','final_pose'):
        v=record.get(p)
        try:
            if not isinstance(v,list) or len(v)!=6:raise ValueError()
            for i,e in enumerate(v):interval(e,'mm' if i<3 else 'deg')
        except ValueError:missing.append(p+' independent six-axis measurement')
    mode=record.get('mode')
    need(mode in ('IMPOSED','ACQUISITION'),'mode')
    d=record.get('disengagement') or {}
    if mode=='ACQUISITION':
        need(bool(record.get('coupon_identities')),'source-bound coupons absent')
        need(d.get('constrained_dofs')==[],'stage still constrains tested DOF or constraint state unknown')
        need(d.get('clamps_clear') is True and d.get('jaws_clear') is True,'fixture release unobserved')
        need(isinstance(d.get('guard_contact'),bool),'guard contact unobserved or not boolean')
        if d.get('guard_contact') is True:fail.append('guard/fixture contact invalidates acquisition')
        tr=record.get('trajectory');gap=record.get('trajectory_max_gap_s')
        allowed_gap=criteria.get('trajectory_max_gap_s')
        need(finite(allowed_gap) and allowed_gap>0,'qualified trajectory sampling bound absent')
        try:
            if not isinstance(tr,list) or len(tr)<3 or not finite(d.get('time_s')):raise ValueError()
            times=[r['time_s'] for r in tr]
            if not all(finite(t) for t in times) or any(b<=a for a,b in zip(times,times[1:])):raise ValueError()
            if times[0]>d['time_s'] or times[-1]<=d['time_s']:raise ValueError()
            for row in tr:
                if len(row['pose'])!=6:raise ValueError()
                for i,e in enumerate(row['pose']):interval(e,'mm' if i<3 else 'deg')
            actual_gap=max(b-a for a,b in zip(times,times[1:]))
            if not finite(gap) or abs(gap-actual_gap)>1e-9:raise ValueError()
            if finite(allowed_gap) and actual_gap>allowed_gap:ambiguous.append('trajectory undersampled for qualified method')
            if tr[-1]['pose']!=record.get('final_pose'):raise ValueError()
            initial_samples=[x for x in tr if x['time_s']==d['time_s']]
            if len(initial_samples)!=1 or initial_samples[0]['pose']!=record.get('measured_initial_pose'):raise ValueError()
        except (ValueError,TypeError,KeyError):missing.append('incomplete or inconsistent trajectory')
    supports=record.get('support_observations')
    for key in criteria.get('required_support_ids') or []:
        try:interval(supports[key]['displacement'])
        except (ValueError,TypeError,KeyError):missing.append('support channel missing: '+key)
    need(isinstance(criteria.get('required_support_ids'),list) and (mode!='ACQUISITION' or bool(criteria['required_support_ids'])),'support requirements unknown')
    need(isinstance(record.get('contact_sequence'),list),'contact sequence missing')
    for key in ('protected_surrogate_contacts','support_loss','multiple_terminal_states'):
        v=record.get(key);need(isinstance(v,bool),key+' unobserved')
        if v is True:fail.append(key)
    for name in criteria.get('required_force_channels') or []:
        try:interval(record['force_channels'][name],'N')
        except (ValueError,TypeError,KeyError):missing.append('force missing/saturated: '+name)
    try:
        cal=interval(record.get('calibration_error_mm'));fixture=interval(record.get('fixture_deflection_mm'))
        extra=max(abs(x) for x in cal)+max(abs(x) for x in fixture)
        metrics['combined_calibration_fixture_bound_mm']=extra
    except ValueError:
        extra=None;missing.append('fixture compliance/calibration uncertainty not separated')
    required=criteria.get('required_field_cells')
    need(record.get('required_field_cells')==required,'run cannot redefine required full-field domain')
    field=record.get('field_residuals');sparse=record.get('sparse_residuals')
    need(isinstance(required,list) and len(required)>0 and len(set(required))==len(required),'required full-field domain unknown')
    need(isinstance(field,dict) and isinstance(required,list) and set(required)<=set(field),'missing full-field cells')
    needed_sparse=criteria.get('required_sparse_ids')
    need(isinstance(sparse,dict) and bool(needed_sparse) and set(needed_sparse)<=set(sparse),'missing sparse datums')
    full_file=record.get('full_field_file')
    need(isinstance(full_file,dict) and valid_hash(full_file.get('sha256'))
         and isinstance(full_file.get('path'),str) and bool(full_file['path'].strip()),'full-field scan artifact absent')
    if record.get('record_origin')=='BENCH_MEASURED':
        need(isinstance(full_file,dict) and bool(artifact_hashes) and artifact_hashes.get(full_file.get('path'))==full_file.get('sha256'),'measured scan bytes not independently hashed')
    for name,values,ids in [('sparse',sparse,needed_sparse),('field',field,required)]:
        if not isinstance(values,dict) or not ids:continue
        ranges=[]
        for id in ids:
            try:
                low,high=interval(values.get(id))
                if high<0:raise ValueError()
                if extra is not None:ranges.append((max(0,low-extra),high+extra))
            except ValueError:missing.append(name+' invalid/missing residual '+id)
        if len(ranges)==len(ids):
            metrics[name+'_max_interval_mm']=[max(x[0] for x in ranges),max(x[1] for x in ranges)]
    if all(k+'_max_interval_mm' in metrics for k in ('sparse','field')):
        s=metrics['sparse_max_interval_mm'];f=metrics['field_max_interval_mm']
        diagnostics['full_field_exceeds_sparse_resolved']=f[0]>s[1]
        diagnostics['difference_interval_mm']=[f[0]-s[1],f[1]-s[0]]
        diagnostics['meaning']='measurement discrepancy, not a human fit threshold'
    limits=criteria.get('max_residual_mm',{})
    for name in ('sparse','field'):
        limit=limits.get(name);bounds=metrics.get(name+'_max_interval_mm')
        need(finite(limit) and limit>=0,'qualified '+name+' criterion absent')
        if bounds and finite(limit):
            if bounds[0]>limit:fail.append(name+' residual exceeds qualified bench criterion')
            elif bounds[1]>limit:ambiguous.append(name+' uncertainty straddles criterion')
    if missing:status='MISSING_REQUIRED_EVIDENCE'
    elif fail:status='BENCH_CRITERION_FAIL'
    elif ambiguous:status='INCONCLUSIVE'
    else:status='BENCH_CRITERION_PASS'
    return {'schema':REVISION,'run_id':record.get('run_id'),'status':status,
            'missing':sorted(set(missing)),'failures':sorted(set(fail)),'inconclusive':sorted(set(ambiguous)),
            'metrics':metrics,'diagnostics':diagnostics,'record_sha256':canonical_hash(record),
            'criteria_sha256':expected_criteria_hash,'source_context_sha256':canonical_hash(context),
            'run_payload_sha256':run_hash,'run_attestation_verified':attested,
            'physical_result':status if record.get('record_origin')=='BENCH_MEASURED' and attested and not missing else None,
            'scope':'QUALIFIED_OFF_FACE_BENCH_CRITERION_ONLY'}


def repeatability(records):
    """Separate stationary instrument, remount and acquisition repeats; no fake power."""
    groups={}
    for r in records:
        kind=r.get('repeat_kind')
        if kind not in ('STATIONARY_INSTRUMENT','REMOUNT','ACQUISITION'):raise ValueError('repeat kind')
        groups.setdefault(kind,[]).append(r)
    result={}
    for kind,rows in groups.items():
        if len(rows)<3:result[kind]={'status':'INCONCLUSIVE','reason':'fewer than three exploratory repeats'};continue
        try:
            intervals=[interval(r['metric']) for r in rows]
            lo=min(x[0] for x in intervals);hi=max(x[1] for x in intervals)
            centers=[r['metric']['value'] for r in rows]
            result[kind]={'status':'INCONCLUSIVE','n':len(rows),'observed_range':max(centers)-min(centers),
                          'conservative_span':hi-lo,'qualified_repeatability_limit':None,
                          'reason':'descriptive only until repeatability method is qualified; three is not a power claim'}
        except (ValueError,KeyError):result[kind]={'status':'MISSING_REQUIRED_EVIDENCE'}
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('record',type=Path);p.add_argument('criteria',type=Path);p.add_argument('registry',type=Path);p.add_argument('sources',type=Path)
    a=p.parse_args();inputs=[json.loads(x.read_text()) for x in (a.record,a.criteria,a.registry,a.sources)]
    artifacts={};entry=inputs[0].get('full_field_file') or {}
    if entry.get('path'):
        path=(a.record.parent/entry['path']).resolve()
        if path.is_relative_to(a.record.parent.resolve()) and path.is_file():artifacts[entry['path']]=sha256(path.read_bytes()).hexdigest()
    print(json.dumps(analyze(*inputs,artifact_hashes=artifacts),indent=2))


if __name__=='__main__':main()
