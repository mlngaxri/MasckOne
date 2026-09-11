"""Executable RR-1..4 off-face metrology. No biological acceptance constants.

All uncertainty values are absolute bounds supplied by the measurement method,
not silently assumed Gaussian standard deviations. Qualification is an external,
source-bound input. This module cannot qualify its own criteria.
"""
from dataclasses import dataclass, asdict
from hashlib import sha256
import json
import math
from pathlib import Path


class MeasurementError(ValueError):
    pass


def finite(value):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
        raise MeasurementError('nonfinite/non-numeric measurement')
    return float(value)


@dataclass(frozen=True)
class Measurement:
    value: float | None
    uncertainty: float | None
    unit: str
    method_id: str | None
    artifact_id: str | None

    def interval(self):
        if self.value is None or self.uncertainty is None: return None
        v,u=finite(self.value),finite(self.uncertainty)
        if u<0:raise MeasurementError('negative uncertainty')
        if not self.unit:raise MeasurementError('missing unit')
        return (v-u,v+u)


def quantity(data, unit='g'):
    if data is None:return None
    m=Measurement(**data)
    if m.unit!=unit:raise MeasurementError('unit mismatch')
    interval=m.interval()
    if m.value is not None and m.value<0:raise MeasurementError('negative quantity')
    return interval


MASS_OUTPUTS=('coupon_gain','recovered','collector','hardware_retained')
CELL_STATES={'CONTINUOUS','THIN_OR_DISCONTINUOUS','POOLED','OCCLUDED','WIPED_OR_REMOVED','UNKNOWN'}
FAILURE_OBSERVATIONS={'POOLED','OCCLUDED','WIPED_OR_REMOVED','THIN_OR_DISCONTINUOUS'}
STAGES={
    'RR-1':('BASELINE','POSITIVE_CONTROL','NEGATIVE_CONTROL'),
    'RR-2':('BASELINE','CONTACT','CLEAN','RINSE_RECOVER','POST_RINSE_RESIDUAL','APPLICATION_CLEAR','THIN_LEAVE_ON'),
    'RR-3':('BASELINE','CONTACT','CLEAN','RINSE_RECOVER','POST_RINSE_RESIDUAL','APPLICATION_CLEAR',
            'THIN_LEAVE_ON','INTERMEDIATE_SETTLE','THICK_LEAVE_ON','FINAL_LEAVE_ON'),
    'RR-4':('BASELINE','CONTACT','CLEAN','RINSE_RECOVER','POST_RINSE_RESIDUAL','APPLICATION_CLEAR',
            'THIN_LEAVE_ON','INTERMEDIATE_SETTLE','THICK_LEAVE_ON','FINAL_LEAVE_ON',
            'FINAL_SETTLE','RELEASE','POST_RELEASE'),
}


def mass_balance(layer):
    """Commanded mass is intentionally excluded from conservation accounting."""
    measured=layer.get('measured',{})
    values={key:quantity(measured.get(key)) for key in ('delivered',)+MASS_OUTPUTS}
    missing=[key for key,v in values.items() if v is None]
    if missing:return {'status':'INCONCLUSIVE','missing':missing,'unresolved_residual_g':None}
    incoming=values['delivered'];outputs=[values[k] for k in MASS_OUTPUTS]
    residual=(incoming[0]-sum(v[1] for v in outputs),incoming[1]-sum(v[0] for v in outputs))
    return {'status':'BALANCE_INTERVAL_CONTAINS_ZERO' if residual[0]<=0<=residual[1]
                    else 'INCONSISTENT_MASS_BALANCE',
            'unresolved_residual_g':list(residual),
            'interpretation':'Unaccounted mass interval, not assumed leakage or evaporation',
            'commanded_g_used_as_measurement':False}


def repeatability(samples):
    """Observed range/uncertainty separation of labeled controls, not validation."""
    ranges={};within={}
    for label, rows in sorted(samples.items()):
        ms=[Measurement(**x) for x in rows]
        iv=[m.interval() for m in ms]
        if len(ms)<2 or any(x is None for x in iv):
            return {'status':'INCONCLUSIVE','reason':'Missing repeated measured controls'}
        if len({(m.unit,m.method_id) for m in ms})!=1 or ms[0].method_id is None:
            raise MeasurementError('mixed or missing repeatability method')
        ranges[label]=[min(x[0] for x in iv),max(x[1] for x in iv)]
        within[label]=max(m.value for m in ms)-min(m.value for m in ms)
    if len(ranges)<2:return {'status':'INCONCLUSIVE','reason':'No contrasting control'}
    method_units={(m['unit'],m['method_id']) for rows in samples.values() for m in rows}
    if len(method_units)!=1:raise MeasurementError('incomparable control methods')
    pairs=[]
    labels=list(ranges)
    for i,a in enumerate(labels):
        for b in labels[i+1:]:
            x,y=ranges[a],ranges[b]
            pairs.append({'a':a,'b':b,'separated':x[1]<y[0] or y[1]<x[0]})
    return {'status':'OBSERVED_CONTROL_SEPARATION' if all(x['separated'] for x in pairs)
            else 'METHOD_CANNOT_DISTINGUISH_CONTROLS','ranges':ranges,'observed_spans':within,
            'comparisons':pairs,'qualification_created':False,
            'limitation':'Observed replicates only; precision criterion and campaign size require qualification'}


def register_fiducials(before, after):
    """Least-squares 2-D rigid registration of calibrated/rectified coordinates.

    Coordinates must already use the same metrology plane. Raw perspective images
    of the curved coupon require independent optical/surface calibration.
    """
    import numpy as np
    if set(before)!=set(after) or len(before)<3:raise MeasurementError('at least three matching fiducials')
    keys=sorted(before)
    a=np.array([[finite(x) for x in before[k]] for k in keys]);b=np.array([[finite(x) for x in after[k]] for k in keys])
    if a.shape!=(len(keys),2) or b.shape!=a.shape:raise MeasurementError('2D fiducials required')
    ac=a-a.mean(axis=0);bc=b-b.mean(axis=0)
    if np.linalg.matrix_rank(ac)<2 or np.linalg.matrix_rank(bc)<2:raise MeasurementError('collinear fiducials')
    u,_,vt=np.linalg.svd(ac.T@bc);r=u@vt
    if np.linalg.det(r)<0:
        u[:,-1]*=-1;r=u@vt
    t=b.mean(axis=0)-a.mean(axis=0)@r
    errors=np.linalg.norm(a@r+t-b,axis=1)
    return {'row_vector_rotation':r.tolist(),'translation':t.tolist(),
            'max_residual':float(errors.max()),'rms_residual':float(np.sqrt(np.mean(errors**2))),
            'registration_accepted':None,'criterion':'External calibrated method bound required'}


def _receipt_valid(receipt, registry):
    if not isinstance(receipt,dict):return False
    canonical=registry.get(receipt.get('id'))
    return canonical==receipt and receipt.get('evidence_class')=='BENCH' and \
        isinstance(receipt.get('artifact_sha256'),str) and len(receipt['artifact_sha256'])==64 and \
        receipt.get('scope')=='OFF_FACE_METHOD_QUALIFICATION' and receipt.get('independent_review') is True


def analyze(run, qualification_registry=None, artifact_root=None):
    """Verdict never treats a command, CAD result or missing value as a measurement."""
    registry=qualification_registry or {};unknown=[];fail=[]
    case=run.get('campaign')
    if case not in STAGES:raise MeasurementError('unknown RR campaign')
    evidence=run.get('evidence_class')
    if evidence not in {'NONE','SYNTHETIC','BENCH'}:raise MeasurementError('unsupported evidence promotion')
    domain=run.get('required_cells',[])
    if not domain or len(domain)!=len(set(domain)):raise MeasurementError('empty/duplicate required domain')
    if set(domain)&set(run.get('protected_cells',[])):raise MeasurementError('protected domain treated as required')
    if run.get('scope')!='OFF_FACE_INERT_ANALOG':raise MeasurementError('not an off-face record')
    events=run.get('events',[])
    observed=[e.get('stage') for e in events]
    if observed!=list(STAGES[case]):unknown.append('STAGE_SEQUENCE_INCOMPLETE_OR_OUT_OF_ORDER')
    if any(not e.get('artifact_id') for e in events):unknown.append('STAGE_MEASUREMENT_MISSING')
    artifacts=run.get('artifacts',{})
    def artifact_ok(identity):
        a=artifacts.get(identity,{})
        if not identity or not a.get('sha256'):return False
        if evidence=='SYNTHETIC':return a.get('synthetic') is True
        if artifact_root is None:return False
        base=Path(artifact_root).resolve();p=(base/a.get('path','')).resolve()
        return p.is_relative_to(base) and p.is_file() and sha256(p.read_bytes()).hexdigest()==a['sha256']
    if evidence=='BENCH':
        if not artifacts or any(not artifact_ok(k) for k in artifacts):unknown.append('ARTIFACT_BYTES_UNVERIFIED')
        if any(not artifact_ok(e.get('artifact_id')) for e in events):unknown.append('EVENT_ARTIFACT_UNVERIFIED')
    method=run.get('method',{})
    qualified=_receipt_valid(method.get('qualification'),registry)
    if not qualified:unknown.append('METHOD_REPEATABILITY_NOT_QUALIFIED')
    if method.get('tracer_confounded') is not False:unknown.append('TRACER_METHOD_CONFOUNDED_OR_UNKNOWN')
    if method.get('curved_surface_calibration') is not True:unknown.append('CURVED_SURFACE_IMAGE_CALIBRATION_UNKNOWN')
    balances=[]
    for layer in run.get('layers',[]):
        b=mass_balance(layer);balances.append({'layer':layer['id'],**b})
        if b['status']=='INCONCLUSIVE':unknown.append('MASS_MISSING:'+layer['id'])
        elif b['status']=='INCONSISTENT_MASS_BALANCE':fail.append('MASS_BALANCE:'+layer['id'])
        for key,data in layer.get('measured',{}).items():
            if data is not None and (not data.get('method_id') or not artifact_ok(data.get('artifact_id'))):
                unknown.append('UNBOUND_MEASUREMENT:'+layer['id']+':'+key)
    expected_layers={'RR-1':0,'RR-2':1,'RR-3':3,'RR-4':3}[case]
    if len(run.get('layers',[]))!=expected_layers:unknown.append('ORDERED_LAYER_MEASUREMENTS_MISSING')
    maps=run.get('cell_maps',{})
    mandatory_maps=['AFTER_THIN'] if case=='RR-2' else (['AFTER_THIN','AFTER_THICK','BEFORE_RELEASE'] if case in {'RR-3','RR-4'} else [])
    if case=='RR-4':mandatory_maps+=['AFTER_RELEASE']
    for name in mandatory_maps:
        cells=maps.get(name,{})
        if set(cells)!=set(domain):unknown.append('CELL_DOMAIN_MISMATCH:'+name)
        for cid in domain:
            entry=cells.get(cid,{})
            state=entry.get('state','UNKNOWN')
            if state not in CELL_STATES:raise MeasurementError('unknown spatial class')
            if state=='UNKNOWN':unknown.append('UNKNOWN_CELL:'+name+':'+cid)
            elif state in FAILURE_OBSERVATIONS:fail.append(state+':'+name+':'+cid)
            if not entry.get('method_id') or not artifact_ok(entry.get('artifact_id')):
                unknown.append('UNBOUND_SPATIAL_MEASUREMENT:'+name+':'+cid)
    checks=('support_continuity','no_protected_migration','no_first_leave_on_carryover')
    for key in checks:
        item=run.get('observations',{}).get(key,{})
        if item.get('value') is False:fail.append(key.upper())
        elif item.get('value') is not True:unknown.append('UNKNOWN:'+key)
        if not artifact_ok(item.get('artifact_id')):unknown.append('UNBOUND:'+key)
    metrics={}
    if case=='RR-1':
        metrics['repeatability']=repeatability(run.get('repeatability_samples',{}))
        if metrics['repeatability']['status']!='OBSERVED_CONTROL_SEPARATION':unknown.append('CONTROL_DISTINCTION_UNRESOLVED')
    if case=='RR-4':
        reg=run.get('registration',{})
        try:metrics['registration']=register_fiducials(reg.get('before',{}),reg.get('after',{}))
        except MeasurementError:unknown.append('IMAGE_REGISTRATION_MISSING_OR_INVALID')
        if not artifact_ok(reg.get('before_artifact')) or not artifact_ok(reg.get('after_artifact')):
            unknown.append('REGISTRATION_IMAGE_BYTES_UNBOUND')
    # Continuous numerical criteria are independent of qualitative detection.
    criteria=run.get('criteria',[])
    if not criteria:unknown.append('NO_PREDECLARED_QUALIFIED_CRITERIA')
    for c in criteria:
        if not _receipt_valid(c.get('qualification'),registry):
            unknown.append('UNQUALIFIED_CRITERION:'+c.get('id','?'));continue
        m=Measurement(**c['measurement']);iv=m.interval();bound=c.get('bound')
        if iv is None or bound is None:unknown.append('MISSING_CRITERION_VALUE:'+c['id']);continue
        finite(bound)
        if c['comparison']=='LE':passed=iv[1]<=bound;failed=iv[0]>bound
        elif c['comparison']=='GE':passed=iv[0]>=bound;failed=iv[1]<bound
        else:raise MeasurementError('unknown criterion operator')
        if failed:fail.append('CRITERION:'+c['id'])
        elif not passed:unknown.append('CRITERION_UNCERTAINTY:'+c['id'])
        if not artifact_ok(m.artifact_id):unknown.append('UNBOUND_CRITERION:'+c['id'])
    # Unqualified qualitative observations are suspected defects, not validated
    # performance decisions. A qualified method can still fail despite other gaps.
    decision='FAIL' if fail and qualified else ('INCONCLUSIVE' if unknown or fail else 'PASS')
    return {'schema':'MASCK_RR_ANALYSIS_1','run_id':run.get('run_id'),
            'result':decision if evidence=='BENCH' else 'NO_PHYSICAL_RESULT',
            'analysis_decision':decision,'evidence_class':evidence,
            'detected_defects':sorted(set(fail)),'unknowns':sorted(set(unknown)),
            'mass_balances':balances,'metrics':metrics,'g1_passed':False,
            'whole_face_complete':False,'spf_protection_evidence':False,
            'human_use_eligible':False}


def template(campaign='RR-4'):
    cells=[f'CHEEK_COUPON_X{i}_Y{j}' for i in range(3) for j in range(4)]
    empty=asdict(Measurement(None,None,'g',None,None))
    layers=['THIN_ANALOG','THICK_ANALOG','FINAL_ANALOG'][:{'RR-1':0,'RR-2':1,'RR-3':3,'RR-4':3}[campaign]]
    return {'schema':'MASCK_RR_RUN_1','run_id':None,'campaign':campaign,'scope':'OFF_FACE_INERT_ANALOG',
            'evidence_class':'NONE','case':None,'geometry_revision':None,'coupon_radius_mm':None,
            'required_cells':cells,'protected_cells':['BOUNDARY_LEFT','BOUNDARY_RIGHT'],
            'events':[{'stage':s,'timestamp':None,'artifact_id':None} for s in STAGES[campaign]],
            'method':{'qualification':None,'tracer_confounded':None,'curved_surface_calibration':None},
            'layers':[{'id':k,'surrogate_identity':None,'measured_properties':None,'commanded_g':None,
                       'measured':{m:dict(empty) for m in ('delivered',)+MASS_OUTPUTS}} for k in layers],
            'cell_maps':{name:{c:{'state':'UNKNOWN','method_id':None,'artifact_id':None} for c in cells}
                         for name in ('AFTER_THIN','AFTER_THICK','BEFORE_RELEASE','AFTER_RELEASE')},
            'observations':{k:{'value':None,'artifact_id':None} for k in
                            ('support_continuity','no_protected_migration','no_first_leave_on_carryover')},
            'registration':{'before':{},'after':{},'before_artifact':None,'after_artifact':None},
            'repeatability_samples':{},'criteria':[],'artifacts':{},
            'qualification_registry':'Independent method receipts; no built-in acceptance thresholds'}


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['init','analyze']);parser.add_argument('path',type=Path)
    parser.add_argument('--registry',type=Path);parser.add_argument('--artifacts',type=Path)
    args=parser.parse_args()
    if args.action=='init':
        args.path.mkdir(parents=True,exist_ok=True)
        for rr in STAGES:(args.path/(rr+'.json')).write_text(json.dumps(template(rr),indent=2)+'\n')
        (args.path/'qualification_registry.json').write_text('{}\n')
    else:
        registry=json.loads(args.registry.read_text()) if args.registry else {}
        print(json.dumps(analyze(json.loads(args.path.read_text()),registry,args.artifacts),indent=2,sort_keys=True))
