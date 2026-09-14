"""Dimensionless synthetic evidence and off-face policies, never human settings."""
from dataclasses import replace
import pytest
from masck_one.regional_cleansing import Answers, ControlError, estimate, prescription, plan, Region, Burden, RecentHistory
from masck_one.cleansing_onboarding import VERSION, QUESTIONS, form_contract, interpret_form
from masck_one.cleansing_evidence import Calibration, QuantitativeObservation, Interval, compare
from masck_one.cleansing_prescription import FactorPolicy, DIMENSIONS, resolve
from test_regional_cleansing import answers, envelope


def calibrations():
    return {f:Calibration(f,'SYNTHETIC',f,'synthetic_coordinate',0,1,10,0,20,'b'*64,
                         (('fixture_condition',0,1),))
            for f in ('surface_oil_proxy','hydration_deficit_proxy')}


def readings(region='A',oil=.8,dry=.1,uncertainty=.02):
    return [QuantitativeObservation(region,f,v,'synthetic_coordinate',uncertainty,'SYNTHETIC',f,0,10,
                (('fixture_condition',.5),),'ACCEPTED')
            for f,v in zip(calibrations(),(oil,dry))]


def infer(a=None,o=None,regions=('A',),now=1):
    a=a or answers(current_oil='HIGH')
    if a.acquired_s is None:a=replace(a,acquired_s=0,valid_until_s=10,context_digest='f'*64)
    return estimate(regions,a,readings() if o is None else o,
                    now=now,calibrations=calibrations())


def factors():
    return FactorPolicy('SYNTHETIC_ORDINAL_FACTORS','c'*64,tuple((k,(.5,.75,1)) for k in DIMENSIONS))


def caps(p):return tuple(p.relative_request[k] for k in DIMENSIONS)


def test_question_content_is_renderable_and_every_question_earns_its_place():
    form=form_contract()
    assert form['demographic_inputs']==[] and len(form['questions'])==20
    assert len({q.id for q in QUESTIONS})==20
    assert all(q.purpose and q.distinction and q.period and q.variable for q in QUESTIONS)
    assert all(q['initial_value'] is None and q['choices'][-1]['value']=='UNKNOWN' for q in form['questions'])
    assert not next(q for q in form['questions'] if q['id']=='recent_cleanse')['context_available']
    assert not next(q for q in form['questions'] if q['id']=='changed_product')['context_available']


def test_missing_ui_context_unknown_answers_and_no_demographic_backdoor():
    payload={'version':VERSION,'global_values':answers().global_values}
    a=interpret_form(payload,regions=['A'])
    assert a.get('recent_cleanse','A')=='UNKNOWN' and a.get('changed_product','A')=='UNKNOWN'
    assert infer(a)['A'].decision=='BLOCKED_REVIEW'
    valid=interpret_form(payload,regions=['A'],history_window_label='synthetic interval',prepared_cleanser_label='fixture fluid')
    assert valid.get('changed_product','A')=='NO'
    for key in ('ethnicity','age','community_settings','ml_prediction','override_limits','saved_profile'):
        with pytest.raises(ControlError):interpret_form({**payload,key:{}},regions=['A'])
        with pytest.raises(ControlError):infer(Answers({**answers().global_values,key:'HIGH'}))
    with pytest.raises(ControlError):interpret_form({**payload,'version':'OLD'},regions=['A'])


def test_near_high_reading_is_not_a_material_contradiction():
    p=infer(o=readings(oil=.64,uncertainty=.03))['A']
    assert p.comparisons['current_oil']['status']=='COMPATIBLE'
    p=infer(o=readings(oil=.60,uncertainty=.01))['A']
    assert p.comparisons['current_oil']['status']=='MINOR_VARIATION'
    assert p.decision=='PERSONALIZED_WITH_VARIATION'
    assert p.comparisons['current_oil']['interval_gap']<1/3


def test_large_conflict_is_targeted_conservative_review_not_automatic_stop():
    p=infer(o=readings(oil=.10,dry=.88))['A']
    assert p.consistency=='DISAGREEMENT' and p.decision=='CONSERVATIVE_REVIEW'
    assert caps(p)==(0,0,0,0)
    assert ('REVIEW_ANSWER','A','current_oil') in p.followups
    assert ('REVIEW_ANSWER','A','current_dry') in p.followups
    assert resolve(p,envelope(),factors())['status']=='SIMULATION_PLAN_ONLY'
    assert not resolve(p,envelope(),factors())['human_use_eligible']


def test_low_quality_does_not_outvote_supported_evidence():
    reference=infer()['A']
    low=infer(o=[replace(o,quality='LOW') for o in readings()])['A']
    assert low.observation_confidence=='LOW' and low.consistency=='INSUFFICIENT'
    assert all(a<=b for a,b in zip(caps(low),caps(reference)))
    survey_low=infer(Answers(answers(current_oil='HIGH').global_values,per_answer_confidence={'current_oil':'UNSURE'}))['A']
    assert survey_low.survey_confidence=='LOW' and survey_low.relative_request['cleanser']==0
    # Wide intervals overlapping both endpoints do not create a confident agreement.
    p=infer(o=readings(oil=.5,dry=.5,uncertainty=.4))['A']
    assert p.observation_confidence=='LOW' and p.confidence=='LOW'


@pytest.mark.parametrize('change,reason',[
    ({'units':'other'},'SENSOR_FEATURE_UNIT_MISMATCH'),
    ({'sensor_id':'other'},'SENSOR_FEATURE_UNIT_MISMATCH'),
    ({'calibration_id':'other'},'UNACCEPTED_CALIBRATION'),
    ({'acquired_s':2},'CALIBRATION_OR_CLOCK_INVALID'),
    ({'valid_until_s':.5},'STALE_OBSERVATION'),
    ({'conditions':()},'CONDITION_fixture_condition'),
    ({'conditions':(('fixture_condition',2),)},'CONDITION_fixture_condition'),
    ({'phase':'WET'},'WRONG_PHASE'),
    ({'confounders':('SWEAT',)},'SWEAT'),
    ({'quality':'UNRELIABLE'},'UNRELIABLE_READING'),
    ({'measured_value':2},'OUTSIDE_CALIBRATED_RANGE'),
])
def test_invalid_physical_evidence_retains_raw_value_without_default(change,reason):
    o=readings();o[0]=replace(o[0],**change)
    p=infer(o=o)['A'];d=p.dimensions['surface_oil_proxy']
    assert d['quality']=='UNAVAILABLE' and reason in d['reasons']
    assert d['interval']=={'low':0,'high':1} and d['raw'] is not None
    assert p.relative_request['cleanser']==0


@pytest.mark.parametrize('key',['wet_or_sweaty','product_film','environment_changed'])
def test_acquisition_confounders_request_repeat_without_claiming_personalization(key):
    p=infer(answers(current_oil='HIGH',**{key:'YES'}))['A']
    assert p.decision=='REPEAT_OBSERVATION'
    assert resolve(p,envelope(),factors())['envelope'] is None
    assert p.observation_confidence=='LOW'


def test_missing_or_uncertain_answers_never_become_no_or_low():
    p=infer(Answers({}))['A']
    assert p.decision=='BLOCKED_REVIEW' and p.dimensions['current_oil']['interval']=={'low':0,'high':1}
    for key in ('water_stings','discomfort_now','hair_obstruction','changed_product'):
        a=Answers(answers().global_values,per_answer_confidence={key:'UNSURE'})
        assert infer(a)['A'].decision=='BLOCKED_REVIEW'


def test_regional_combination_and_baseline_current_difference_are_natural():
    a=Answers(answers(current_oil='HIGH').global_values,{
        'B':{'current_oil':'LOW','current_dry':'HIGH','usual_dry':'HIGH'},
        'C':{'usual_oil':'HIGH','current_oil':'LOW','current_dry':'HIGH'},
        'D':{'usual_dry':'HIGH','current_oil':'HIGH','current_dry':'LOW'}})
    o=readings()+readings('B',oil=.1,dry=.85)+readings('C',oil=.1,dry=.85)+readings('D')
    p=infer(a,o,('A','B','C','D'))
    assert all(v.consistency=='AGREEMENT' for v in p.values())
    assert p['A'].relative_request['cleanser']>p['B'].relative_request['cleanser']
    assert p['C'].relative_request['mechanical']==p['D'].relative_request['mechanical']==0
    assert 'B' in p['A'].regional_variation
    assert 'BASELINE_CURRENT_DIFFERENCE_usual_oil' in p['C'].reasons


def test_asymmetry_requires_local_current_answers_without_changing_other_regions():
    p=infer(answers(left_right_difference='YES'))['A']
    assert p.survey_confidence=='LOW'
    a=Answers(answers(left_right_difference='YES').global_values,{'A':{'current_oil':'HIGH','current_dry':'LOW'}})
    assert infer(a)['A'].comparisons['current_oil']['status']=='COMPATIBLE'


@pytest.mark.parametrize('key',['exfoliation','product_reactivity','recent_cleanse','multiple_cleanses','hair_removal','flaking_now'])
def test_known_or_unknown_burden_limits_all_action_dimensions(key):
    for value in ('YES','UNKNOWN'):
        p=infer(answers(current_oil='HIGH',**{key:value}))['A']
        assert caps(p)==(0,0,0,0)
    p=infer(answers(current_oil='HIGH',recent_cleanse='NO',multiple_cleanses='YES'))['A']
    assert 'CONTRADICTORY_RECENT_CLEANSING' in p.reasons


def test_more_oil_does_not_increase_mechanics_time_or_passes():
    low=infer(answers(),readings(oil=.1))['A'];high=infer()['A']
    assert low.relative_request['cleanser']<high.relative_request['cleanser']
    for k in ('mechanical','contact_time','passes'):assert low.relative_request[k]==high.relative_request[k]


def test_information_loss_is_componentwise_monotonic_in_ordinal_and_absolute_limits():
    for oil in (.1,.5,.8):
        for dry in (.1,.5,.8):
            a=answers(current_oil='LOW' if oil<1/3 else 'MODERATE' if oil<2/3 else 'HIGH',
                      current_dry='LOW' if dry<1/3 else 'MODERATE' if dry<2/3 else 'HIGH')
            base=infer(a,readings(oil=oil,dry=dry,uncertainty=.01))['A']
            lower=[infer(a,readings(oil=oil,dry=dry,uncertainty=.09))['A'],
                   infer(a,[replace(o,quality='LOW') for o in readings(oil=oil,dry=dry)])['A'],
                   infer(a,[])['A'],infer(Answers({**a.global_values,'answer_confidence':'UNKNOWN'}),readings(oil=oil,dry=dry))['A']]
            b=resolve(base,envelope(),factors())['envelope']
            for p in lower:
                assert all(x<=y for x,y in zip(caps(p),caps(base)))
                q=resolve(p,envelope(),factors())['envelope']
                assert q.maximum.within(b.maximum) and q.max_force_N<=b.max_force_N and q.max_stroke_mm<=b.max_stroke_mm
                assert q.min_rinse_ml==b.min_rinse_ml


def test_prescription_has_no_numeric_fallback_and_factors_cannot_amplify():
    p=infer()['A']
    for a,f in ((None,None),(envelope(),None),(None,factors())):
        assert resolve(p,a,f)['envelope'] is None
    for bad in ((.5,.4,1),(.5,.75,1.01),(-1,.5,1),(float('nan'),.5,1)):
        with pytest.raises(ControlError):replace(factors(),factors=tuple((k,bad) for k in DIMENSIONS))
    with pytest.raises(ControlError):replace(factors(),scope='HUMAN')
    with pytest.raises(ControlError):replace(next(iter(calibrations().values())),scope='HUMAN')
    with pytest.raises(ControlError):resolve(replace(p,decision='ML_APPROVED'),envelope(),factors())
    with pytest.raises(ControlError):resolve(replace(p,relative_request={'cleanser':4}),envelope(),factors())


def test_plan_cannot_bypass_factor_qualification_or_misbind_region():
    p=infer();regions={'A':Region('A',frozenset({'a'}))}
    assert plan(p,regions,{'BASELINE':envelope()},placement={'A':True},history={'A':Burden()})['A'].state=='BLOCKED'
    assert plan(p,regions,{'BASELINE':envelope()},placement={'A':True},history={'A':RecentHistory('A',regions['A'].domain_id,-10,0,Burden(),'e'*64,'BOUNDED','SIMULATED_OBSERVED_BOUND')},factor_policy=factors(),session_id='synthetic_session')['A'].state=='NOT_STARTED'


def test_quantitative_nonfinite_units_bounds_and_duplicates_are_rejected():
    for x in (float('nan'),float('inf'),True):
        with pytest.raises(ControlError):replace(readings()[0],measured_value=x)
    with pytest.raises(ControlError):replace(readings()[0],uncertainty_bound=-1)
    with pytest.raises(ControlError):infer(o=readings()+[readings()[0]])
    with pytest.raises(ControlError):infer(o=readings('UNREGISTERED'))
    with pytest.raises(ControlError):Interval(.8,.1)


def test_stale_survey_cannot_be_resurrected_by_fresh_physical_observation():
    for a in (replace(answers(),valid_until_s=.5),replace(answers(),acquired_s=2),
              replace(answers(),context_digest=None),Answers(answers().global_values)):
        p=estimate(['A'],a,readings(),now=1,calibrations=calibrations())['A']
        assert p.decision=='BLOCKED_REVIEW' and 'SURVEY_CONTEXT_STALE_OR_UNBOUND' in p.reasons
        assert resolve(p,envelope(),factors())['envelope'] is None


def test_explicit_context_fallback_is_not_faked_personalization():
    p=infer(answers(product_film='YES'))['A']
    assert resolve(p,envelope(),factors())['envelope'] is None
    policy=replace(factors(),fallback_contexts=('product_film',))
    r=resolve(p,envelope(),policy)
    assert r['execution_mode']=='QUALIFIED_CONTEXT_FALLBACK'
    assert not r['personalization_confirmed'] and set(r['factors'].values())=={.5}
    assert r['envelope'] is not None and not r['human_use_eligible']
    wet=infer(answers(product_film='YES',wet_or_sweaty='YES'))['A']
    assert resolve(wet,envelope(),policy)['envelope'] is None


def test_affine_calibration_span_cannot_overflow_into_false_low_signal():
    with pytest.raises(ControlError):replace(next(iter(calibrations().values())),raw_zero=-1e308,raw_one=1e308)
    with pytest.raises(ControlError):estimate(['A'],answers(),[object()],calibrations=calibrations())


def test_different_personalization_tables_have_distinct_execution_bindings():
    p=infer()['A'];one=resolve(p,envelope(),factors())['envelope']
    policy=replace(factors(),factors=tuple((k,(.4,.7,.9)) for k in DIMENSIONS))
    two=resolve(p,envelope(),policy)['envelope']
    assert one.source_digest==two.source_digest and one.personalization_digest!=two.personalization_digest
    assert two.maximum.within(one.maximum)
