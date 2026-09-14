"""Synthetic control numbers below are NOT human treatment settings."""
from dataclasses import replace
import pytest
from masck_one.regional_cleansing import *
from masck_one.cleansing_fit import DIMENSIONS, FitStudy, select_study


def answers(**changes):
    data={q[0]:('LOW' if q[2]=='LEVEL' else 'NO') for q in QUESTIONNAIRE}
    data['answer_confidence']='YES';data.update(changes)
    return Answers(data,acquired_s=0,valid_until_s=10,context_digest='f'*64)


def observations(region='A',oil=Level.LOW,dry=Level.LOW):
    return [Observation(region,'surface_oil_proxy',oil,0,10,'SYNTHETIC',quality='ACCEPTED'),
            Observation(region,'hydration_deficit_proxy',dry,0,10,'SYNTHETIC',quality='ACCEPTED')]


def profile(a=None,o=None):
    return estimate(['A'],a or answers(),observations() if o is None else o,now=1,accepted_calibrations={'SYNTHETIC'})['A']


def envelope(family='BASELINE'):
    return Envelope('SYNTHETIC_FIXTURE_ONLY','a'*64,family,
        Burden(contact_s=10,load_Ns=10,tangential_mm=10,shear_proxy_Nmm=10,
               cleanser_ml=10,cleanser_residence_s=10,water_ml=10,passes=2),
        max_force_N=1,max_stroke_mm=1,min_rinse_ml=1,max_sample_gap_s=1,history_window_s=10)


def ledger(region='A',cells=frozenset({'a','b'})):
    return RegionalLedger(Region(region,cells),envelope(),prior=Burden(),placement_ok=True,session_id='synthetic_session')


def stage_receipt(l,stage,cells=None):
    return StageEvidence(l.session_id,l.region.region_id,l.region.domain_id,stage,
        frozenset(l.region.cells if cells is None else cells),l.sequence,l.event_chain,'d'*64)


def cover(l,cells=None):
    cells=l.region.cells if cells is None else cells
    l.record_cells(cells,evidence=stage_receipt(l,'CLEAN',cells))


def rinse(l):
    l.record_stage(stage_receipt(l,'RINSE'));l.rinsed()


def finished(l):
    l.ingest(Tick(1,1,'CLEAN',True,.1,1,.1,1))
    cover(l);l.cleansed()
    l.ingest(Tick(2,2,'RINSE',water_ml=1));rinse(l)
    l.ingest(Tick(3,3,'RECOVER'))
    l.rinsed_recovered(recovery_receipt=stage_receipt(l,'RECOVER'));l.complete()


def test_twenty_discriminating_questions_no_ethnicity_or_disease():
    assert len(QUESTIONNAIRE)==20
    with pytest.raises(ControlError):estimate(['A'],Answers({'ethnicity':'anything'}))


def test_disagreement_does_not_average_into_more_action():
    p=profile(answers(current_oil='HIGH'),observations(oil=Level.LOW,dry=Level.HIGH))
    assert p.consistency=='DISAGREEMENT'
    assert p.family=='GENTLE_REVIEW'
    assert p.confidence=='LOW'


def test_oil_and_dryness_are_independent_not_opposites():
    p=profile(answers(current_oil='HIGH',current_dry='HIGH'),observations(oil=Level.HIGH,dry=Level.HIGH))
    assert p.consistency=='AGREEMENT' and p.family=='GENTLE_REVIEW'


@pytest.mark.parametrize('key',['exfoliation','hair_removal','other_stress','product_reactivity','recent_cleanse','multiple_cleanses'])
def test_reported_risk_cannot_be_cancelled_by_sensor(key):
    assert profile(answers(**{key:'YES'})).family=='GENTLE_REVIEW'


@pytest.mark.parametrize('key',['water_stings','discomfort_now','changed_product','hair_obstruction'])
def test_unknown_critical_answer_cannot_relax_known_stop(key):
    assert profile(answers(**{key:'YES'})).family=='BLOCKED_REVIEW'
    assert profile(answers(**{key:'UNKNOWN'})).family=='BLOCKED_REVIEW'


def test_uncertain_evidence_and_sensor_expiry():
    assert profile(answers(answer_confidence='UNKNOWN')).family=='GENTLE_REVIEW'
    assert profile(o=[]).family=='GENTLE_REVIEW'
    assert estimate(['A'],replace(answers(),valid_until_s=20),observations(),now=11,accepted_calibrations={'SYNTHETIC'})['A'].family=='GENTLE_REVIEW'
    assert profile(answers(product_film='YES')).apparent_oil==Level.UNKNOWN
    assert profile(o=[replace(x,phase='WET') for x in observations()]).confidence=='LOW'
    assert profile(o=[replace(x,calibration_id='UNKNOWN') for x in observations()]).confidence=='LOW'


def test_combination_regions_keep_separate_decisions():
    a=answers();a=replace(a,regional_values={'B':{'current_dry':'HIGH','usual_dry':'HIGH'}})
    p=estimate(['A','B'],a,observations()+observations('B',dry=Level.HIGH),now=1,accepted_calibrations={'SYNTHETIC'})
    assert p['A'].family=='BASELINE' and p['B'].family=='GENTLE_REVIEW'


def test_unknown_limits_history_and_placement_block():
    r=Region('A',frozenset({'a'}))
    assert RegionalLedger(r,None).state=='BLOCKED'
    assert RegionalLedger(r,envelope(),placement_ok=True).faults==['UNKNOWN_RECENT_BURDEN']
    assert RegionalLedger(r,envelope(),prior=Burden()).state=='BLOCKED'
    with pytest.raises(ControlError):replace(envelope(),evidence_scope='HUMAN')


def test_gentle_ceiling_is_componentwise_and_rinse_preserved():
    base=envelope();g=replace(base,family='GENTLE_REVIEW')
    check_policy_families({'BASELINE':base,'GENTLE_REVIEW':g})
    for field_name in ('contact_s','load_Ns','tangential_mm','shear_proxy_Nmm','cleanser_ml','cleanser_residence_s','water_ml','passes'):
        maximum=replace(g.maximum,**{field_name:getattr(g.maximum,field_name)+1})
        with pytest.raises(ControlError):check_policy_families({'BASELINE':base,'GENTLE_REVIEW':replace(g,maximum=maximum)})
    with pytest.raises(ControlError):check_policy_families({'BASELINE':base,'GENTLE_REVIEW':replace(g,min_rinse_ml=.5)})


def test_region_hole_rinse_and_recovery_cannot_be_skipped():
    l=ledger();l.ingest(Tick(1,1,'CLEAN',True,.1,1,.1,1));cover(l,{'a'})
    with pytest.raises(ControlError):l.cleansed()
    cover(l,{'b'});l.cleansed()
    with pytest.raises(ControlError):l.complete()
    with pytest.raises(ControlError):l.rinsed_recovered(recovery_receipt='synthetic')
    l.ingest(Tick(2,2,'RINSE',water_ml=1))
    with pytest.raises(ControlError):l.rinsed_recovered(recovery_receipt='')
    with pytest.raises(ControlError):l.rinsed_recovered(recovery_receipt='synthetic',physical_validation=True)


def test_completed_region_cannot_keep_cleaning_for_another():
    a,b=ledger(),ledger('B');finished(a)
    assert not simulated_cleansing_complete({'A':a.region,'B':b.region},{'A':a,'B':b})
    assert not shared_channel_permitted({'A','B'},{'A':a,'B':b})
    assert not a.permits(Burden(contact_s=.1),force_upper_N=.1,stroke_upper_mm=.1)
    a.ingest(Tick(4,4,'CLEAN',True,.1,.1,.1))
    assert a.state=='BLOCKED' and 'REPEATED_OR_UNAUTHORIZED_CLEAN' in a.faults


def test_observed_excess_is_recorded_even_after_stop():
    l=ledger();l.ingest(Tick(1,1,'CLEAN',True,2,12,2,12))
    assert l.state=='BLOCKED' and l.total.cleanser_ml==12
    l.ingest(Tick(2,2,'IDLE'))
    assert l.total.cleanser_residence_s==2 and l.total.cleanser_ml==12


def test_residence_accumulates_during_rinse_and_idle_until_recovery():
    l=ledger();l.ingest(Tick(1,1,'CLEAN',cleanser_ml=1));cover(l);l.cleansed()
    l.ingest(Tick(2,2,'IDLE'));l.ingest(Tick(3,3,'RINSE',water_ml=1));rinse(l)
    assert l.total.cleanser_residence_s==3
    l.ingest(Tick(4,4,'RECOVER'))
    l.rinsed_recovered(recovery_receipt=stage_receipt(l,'RECOVER'));l.complete()
    l.ingest(Tick(5,5,'IDLE'))
    assert l.total.cleanser_residence_s==4


def test_replayed_and_missing_telemetry_latch():
    l=ledger();l.ingest(Tick(1,1,'CLEAN'))
    with pytest.raises(ControlError):l.ingest(Tick(1,1,'CLEAN'))
    assert l.state=='BLOCKED'
    l=ledger();l.ingest(Tick(1,2,'IDLE'));assert 'TELEMETRY_GAP' in l.faults


def test_nonfinite_negative_and_hidden_motion_rejected():
    for value in (float('nan'),float('inf'),-1,True):
        with pytest.raises(ControlError):Burden(contact_s=value)
    with pytest.raises(ControlError):Tick(1,1,'RINSE',True,.1,1,.1)
    with pytest.raises(ControlError):Tick(1,1,'CLEAN',False,1)


def test_simulation_receipt_never_whole_routine_or_physical():
    l=ledger();finished(l);r=l.receipt()
    assert simulated_cleansing_complete({'A':l.region},{'A':l})
    assert not simulated_cleansing_complete({'A':l.region,'B':Region('B',frozenset({'z'}))},{'A':l})
    assert not r['human_use_eligible'] and not r['whole_routine_complete']
    assert r['evidence_class']=='DIGITAL_SIMULATION'


def test_synthetic_small_large_asymmetric_fit_and_hair_outliers():
    # Dimensionless-looking numerical study coordinates; no human size recommendation.
    bounds={k:(1,3) for k in DIMENSIONS};c=FitStudy('SYNTHETIC',bounds,'b'*64,frozenset({'CLEAR'}))
    for size in (1,3):assert select_study({k:size for k in DIMENSIONS},'CLEAR',[c])['matching_studies']
    outside={k:2 for k in DIMENSIONS};outside['left_right_asymmetry']=4
    assert not select_study(outside,'CLEAR',[c])['matching_studies']
    assert not select_study({k:2 for k in DIMENSIONS},'OBSTRUCTED',[c])['matching_studies']
    assert not select_study({k:2 for k in DIMENSIONS},'CLEAR')['human_fit_validated']


def test_required_region_cannot_be_relabeled_excluded():
    l=RegionalLedger(Region('A',frozenset({'a'}),'EXCLUDED','invented'),None)
    expected={'A':Region('A',frozenset({'a'}))}
    assert not simulated_cleansing_complete(expected,{'A':l})


def test_joint_water_budget_and_no_stale_command():
    a,b=ledger(),ledger('B');s=SessionLedger({'A':a.region,'B':b.region},{'A':a,'B':b},water_limit_ml=1,cleanser_limit_ml=2)
    assert not s.authorize_shared({'A','B'},Burden(water_ml=1),force_upper_N=0,stroke_upper_mm=0,now_s=0)
    assert not a.permits(Burden(),force_upper_N=0,stroke_upper_mm=0,now_s=5)
    s.ingest('A',Tick(1,1,'CLEAN',water_ml=1));s.ingest('B',Tick(1,1,'CLEAN',water_ml=1))
    assert a.state==b.state=='BLOCKED'
    assert a.total.water_ml+b.total.water_ml==2


def test_unknown_prescription_never_supplies_hidden_defaults():
    r=prescription(profile())
    assert r['contact_load_max_N'] is None and r['commanded_duration_s'] is None
    assert r['state']=='BLOCKED_UNQUALIFIED_LIMITS'


def test_recovery_receipt_cannot_belong_to_another_region_or_sequence():
    l=ledger();l.ingest(Tick(1,1,'CLEAN'));cover(l);l.cleansed()
    l.ingest(Tick(2,2,'RINSE',water_ml=1));rinse(l);l.ingest(Tick(3,3,'RECOVER'))
    good=stage_receipt(l,'RECOVER')
    for receipt in (replace(good,region_id='B'),replace(good,sequence=2),replace(good,evidence_class='HUMAN'),True):
        with pytest.raises(ControlError):l.rinsed_recovered(recovery_receipt=receipt)


def test_misbound_profile_policy_and_downgrade_without_baseline_rejected():
    with pytest.raises(ControlError):prescription(profile(answers(exfoliation='YES')),envelope())
    with pytest.raises(ControlError):check_policy_families({'GENTLE_REVIEW':envelope('GENTLE_REVIEW')})
    with pytest.raises(ControlError):plan({'A':replace(profile(),region='B')},{'A':Region('A',frozenset({'a'}))},
        {'BASELINE':envelope()},placement={'A':True},history={'A':Burden()})


def test_event_history_hash_distinguishes_equal_final_burden():
    a,b=ledger(),ledger()
    a.ingest(Tick(1,1,'CLEAN',water_ml=1));a.ingest(Tick(2,2,'CLEAN',water_ml=2))
    b.ingest(Tick(1,1,'CLEAN',water_ml=2));b.ingest(Tick(2,2,'CLEAN',water_ml=1))
    assert a.total==b.total and a.receipt()['event_chain']!=b.receipt()['event_chain']
