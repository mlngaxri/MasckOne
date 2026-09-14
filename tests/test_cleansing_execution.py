"""Hostile software-only completion, burden and hardware-interface cases."""
from dataclasses import replace
import pytest
from masck_one.regional_cleansing import *
from masck_one.cleansing_requirements import *
from masck_one.cleansing_prescription import resolve
from test_regional_cleansing import ledger, envelope, stage_receipt, cover, rinse, finished
from test_cleansing_personalization import infer, factors, answers, readings


def session():
    a=ledger('A',frozenset({'a1','a2'}));b=ledger('B',frozenset({'b1','b2'}))
    return SessionLedger({'A':a.region,'B':b.region},{'A':a,'B':b},water_limit_ml=20,cleanser_limit_ml=20)


def footprint(s):
    return ChannelFootprint('SYNTHETIC_CHANNEL','a'*64,tuple((r,l.region.domain_id,l.region.cells) for r,l in s.ledgers.items()))


def test_commands_elapsed_time_and_bare_cell_names_are_not_completion_evidence():
    l=ledger();l.ingest(Tick(1,1,'CLEAN'))
    assert set(l.cell_status().values())=={'IN_PROGRESS_UNPROVED'}
    with pytest.raises(ControlError):l.record_cells(l.region.cells)
    with pytest.raises(ControlError):l.cleansed()
    with pytest.raises(ControlError):l.record_stage(replace(stage_receipt(l,'CLEAN'),basis='COMMAND_ISSUED'))
    assert not l.covered


@pytest.mark.parametrize('field,value',[
    ('session_id','other'),('domain_id','other'),('region_id','other'),('sequence',True),
    ('sequence',2),('telemetry_chain','0'*64),('source_digest',''),('stage','RINSE'),
    ('cells',frozenset({'unregistered'})),('evidence_class','BENCH'),('basis','ELAPSED_TIME')])
def test_stage_receipts_cannot_cross_identity_scope_or_basis(field,value):
    l=ledger();l.ingest(Tick(1,1,'CLEAN'))
    with pytest.raises(ControlError):l.record_stage(replace(stage_receipt(l,'CLEAN'),**{field:value}))
    assert l.stage_cells['CLEAN']==set()


def test_rinse_and_recovery_have_independent_spatial_holes():
    l=ledger();l.ingest(Tick(1,1,'CLEAN'));cover(l);l.cleansed()
    l.ingest(Tick(2,2,'RINSE',water_ml=1))
    with pytest.raises(ControlError):l.rinsed()
    l.record_stage(stage_receipt(l,'RINSE',{'a'}))
    with pytest.raises(ControlError):l.rinsed()
    l.record_stage(stage_receipt(l,'RINSE',{'b'}));l.rinsed()
    l.ingest(Tick(3,3,'RECOVER'));l.record_stage(stage_receipt(l,'RECOVER',{'a'}))
    with pytest.raises(ControlError):l.recovered()
    with pytest.raises(ControlError):l.complete()
    l.record_stage(stage_receipt(l,'RECOVER',{'b'}));l.recovered();l.complete()
    assert l.receipt()['stage_cells']=={'CLEAN':['a','b'],'RINSE':['a','b'],'RECOVER':['a','b']}


def test_recovery_cannot_skip_rinse_even_if_endpoint_would_look_dry():
    l=ledger();l.ingest(Tick(1,1,'CLEAN'));cover(l);l.cleansed()
    l.ingest(Tick(2,2,'RECOVER'))
    assert 'STAGE_ORDER' in l.faults
    with pytest.raises(ControlError):l.record_stage(stage_receipt(l,'RECOVER'))


def test_same_cell_cannot_be_cleaned_while_another_is_unfinished():
    l=ledger();l.ingest(Tick(1,1,'CLEAN',cells=frozenset({'a'})));cover(l,{'a'})
    assert l.cell_status()=={'a':'CLEANSED','b':'NOT_STARTED'}
    assert not l.permits(Burden(),force_upper_N=0,stroke_upper_mm=0,now_s=1,cells={'a','b'})
    assert l.permits(Burden(),force_upper_N=0,stroke_upper_mm=0,now_s=1,cells={'b'})
    l.ingest(Tick(2,2,'CLEAN',cells=frozenset({'a','b'})))
    assert 'REPEATED_COMPLETE_CELL' in l.faults


def test_unknown_tick_footprint_and_contact_after_completion_latch():
    l=ledger();l.ingest(Tick(1,1,'CLEAN',cells=frozenset({'outside'})))
    assert 'UNKNOWN_TELEMETRY_FOOTPRINT' in l.faults
    l=ledger();finished(l);l.ingest(Tick(4,4,'IDLE',contact=True,force_upper_N=.1))
    assert 'CONTACT_AFTER_COMPLETION' in l.faults and l.state=='BLOCKED'


def test_history_is_bounded_and_contextual_not_a_successful_log_entry():
    r=Region('A',frozenset({'a'}));p=infer();h=RecentHistory('A',r.domain_id,-10,0,Burden(),'e'*64,'BOUNDED','SIMULATED_OBSERVED_BOUND')
    def run(history):return plan(p,{'A':r},{'BASELINE':envelope()},placement={'A':True},history={'A':history},factor_policy=factors(),session_id='S')['A']
    assert run(h).state=='NOT_STARTED'
    for bad in (None,Burden(),replace(h,quality='UNKNOWN'),replace(h,upper_bound=None),
                replace(h,provenance='SOFTWARE_LOG'),replace(h,provenance='USER_REPORT'),
                replace(h,window_start_s=-9),replace(h,window_end_s=-1),replace(h,region_id='B'),
                replace(h,domain_id='elsewhere'),replace(h,evidence_class='HUMAN')):
        assert run(bad).state=='BLOCKED'
    assert resolve(p['A'],replace(envelope(),history_window_s=None),factors())['envelope'] is None


def test_recent_burden_reduces_action_but_does_not_debit_current_reservoir():
    a=RegionalLedger(Region('A',frozenset({'a'})),envelope(),prior=Burden(cleanser_ml=8),placement_ok=True,session_id='S')
    s=SessionLedger({'A':a.region},{'A':a},water_limit_ml=2,cleanser_limit_ml=1)
    s.ingest('A',Tick(1,1,'CLEAN',cleanser_ml=1))
    assert a.total.cleanser_ml==9 and a.session.cleanser_ml==1 and not a.faults
    assert not a.permits(Burden(cleanser_ml=2),force_upper_N=0,stroke_upper_mm=0,now_s=1)


@pytest.mark.parametrize('field',['contact_s','load_Ns','tangential_mm','shear_proxy_Nmm','cleanser_ml','cleanser_residence_s','water_ml','passes'])
def test_every_budget_is_local_and_exhaustible(field):
    s=session();a=s.ledgers['A'];b=s.ledgers['B']
    a.total=replace(a.total,**{field:getattr(a.envelope.maximum,field)})
    inc=replace(Burden(),**{field:1})
    assert not a.permits(inc,force_upper_N=0,stroke_upper_mm=0,now_s=0)
    assert b.permits(inc,force_upper_N=0,stroke_upper_mm=0,now_s=0)
    assert not authorize_footprint(s,footprint(s),{'A':inc,'B':inc},force_upper_N={'A':0,'B':0},stroke_upper_mm={'A':0,'B':0},now_s=0)


def test_shared_footprint_must_include_every_affected_region_and_cell():
    s=session();f=footprint(s)
    with pytest.raises(ControlError):authorize_footprint(s,f,{'A':Burden()},force_upper_N={'A':0},stroke_upper_mm={'A':0},now_s=0)
    for bad in (replace(f,regions=()),replace(f,source_digest=''),
                replace(f,regions=(('A','wrong',frozenset({'a1'})),)),
                replace(f,regions=(('A',s.expected['A'].domain_id,frozenset({'outside'})),))):
        with pytest.raises(ControlError):bad.validate(s.expected)
    protected={'A':replace(s.expected['A'],classification='PROTECTED',exclusion_reason='aperture')}
    with pytest.raises(ControlError):replace(f,regions=(f.regions[0],)).validate(protected)


def test_shared_telemetry_is_complete_and_overrun_remains_recorded():
    s=session();f=footprint(s)
    ticks={r:Tick(1,1,'CLEAN',cleanser_ml=12,cells=l.region.cells) for r,l in s.ledgers.items()}
    with pytest.raises(ControlError):ingest_footprint(s,f,{'A':ticks['A']})
    assert s.ledgers['A'].sequence==0
    assert not ingest_footprint(s,f,ticks)
    assert all(l.total.cleanser_ml==12 and 'SHARED_ACTION_FAULT' in l.faults for l in s.ledgers.values())


def test_rinse_reserve_not_spent_on_cleaning():
    s=session();s.water_limit=2
    assert not authorize_footprint(s,footprint(s),{'A':Burden(water_ml=.1),'B':Burden()},
        force_upper_N={'A':0,'B':0},stroke_upper_mm={'A':0,'B':0},now_s=0)


def test_source_and_session_change_invalidate_receipt_chain():
    a=ledger();b=RegionalLedger(a.region,replace(envelope(),max_force_N=.9),prior=Burden(),placement_ok=True,session_id=a.session_id)
    c=RegionalLedger(a.region,envelope(),prior=Burden(),placement_ok=True,session_id='other')
    assert len({a.event_chain,b.event_chain,c.event_chain})==3
    a.ingest(Tick(1,1,'CLEAN'));chain=a.event_chain;cover(a)
    assert a.event_chain!=chain


def test_demand_classes_do_not_require_one_actuator_per_coverage_cell():
    a=Answers(answers(current_oil='HIGH').global_values,{
        'B':{'current_oil':'LOW'},'C':{'current_oil':'MODERATE','current_dry':'MODERATE'},
        'D':{'current_dry':'HIGH'},'E':{'current_dry':'HIGH'}})
    p=infer(a,readings()+readings('B',oil=.1)+readings('C',oil=.5,dry=.5)+readings('D',dry=.8)+readings('E',dry=.8),('A','B','C','D','E'))
    regions={r:Region(r,frozenset(r+str(i) for i in range(4))) for r in p}
    result=control_partition(p,regions)
    assert result['independent_demand_classes']==4 and result['physical_actuator_count'] is None
    assert sum(len(r.cells) for r in regions.values())==20
    contract=hardware_contract()
    assert not contract['human_use_eligible'] and 'ML' in contract['not_required']


def test_no_combination_of_partial_regions_is_whole_face_completion():
    s=session();a,b=s.ledgers.values();finished(a)
    b.ingest(Tick(1,1,'CLEAN'));cover(b);b.cleansed()
    assert not s.complete()
    assert not a.receipt()['whole_routine_complete']
    assert a.receipt()['human_use_eligible'] is False


def test_contract_export_is_deterministic_and_source_bound(tmp_path):
    import json
    from hashlib import sha256
    from pathlib import Path
    p=export_contract(tmp_path/'one');q=export_contract(tmp_path/'two')
    assert p.read_bytes()==q.read_bytes()
    data=json.loads(p.read_text());root=Path(__file__).resolve().parents[1]
    assert not data['human_use_eligible'] and not data['whole_routine_complete']
    assert data['qualified_human_limits'] is None and data['accepted_physical_calibrations']==[]
    for path,source in data['sources'].items():assert source['sha256']==sha256((root/path).read_bytes()).hexdigest()
    assert 'uncertainty_bound' in data['contract_fields']['QuantitativeObservation']
    assert 'session_id' in data['contract_fields']['StageEvidence']
