"""Interval-based cosmetic evidence comparison; no biological operating thresholds.

The 0..1 coordinate is an explicitly calibrated semantic scale. Equal thirds
encode the three questionnaire answer bins, NOT biological measurement cutoffs.
Uncertainty is a bounded interval, never an invented probability/confidence level.
"""
from dataclasses import dataclass, asdict
from .regional_cleansing import Answers, Observation, Profile, Level, ControlError, finite, QUESTIONS

FEATURES={'surface_oil_proxy':'current_oil','hydration_deficit_proxy':'current_dry'}

@dataclass(frozen=True)
class Interval:
    low: float
    high: float

    def __post_init__(self):
        finite(self.low,'interval low');finite(self.high,'interval high')
        if not 0<=self.low<=self.high<=1:raise ControlError('invalid semantic interval')

    @property
    def width(self):return self.high-self.low

UNKNOWN=Interval(0,1)
BINS={Level.LOW:Interval(0,1/3),Level.MODERATE:Interval(1/3,2/3),Level.HIGH:Interval(2/3,1),Level.UNKNOWN:UNKNOWN}


def digest_ok(value):return isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value)

@dataclass(frozen=True)
class Calibration:
    calibration_id: str
    sensor_id: str
    feature: str
    units: str
    raw_zero: float
    raw_one: float
    max_age_s: float
    valid_from_s: float
    valid_until_s: float
    source_digest: str
    conditions: tuple[tuple[str,float,float],...]=()
    scope: str='OFF_FACE_SIMULATION'

    def __post_init__(self):
        for key in ('raw_zero','raw_one'):finite(getattr(self,key),key,nonnegative=False)
        for key in ('max_age_s','valid_from_s','valid_until_s'):finite(getattr(self,key),key)
        if self.raw_zero==self.raw_one or self.max_age_s<=0 or self.valid_until_s<self.valid_from_s:raise ControlError('invalid calibration span')
        if not all((self.calibration_id,self.sensor_id,self.units)) or self.feature not in FEATURES or not digest_ok(self.source_digest):raise ControlError('incomplete calibration identity')
        if self.scope!='OFF_FACE_SIMULATION':raise ControlError('human observation calibration not qualified by this module')
        seen=set()
        for name,lo,hi in self.conditions:
            finite(lo,'condition low',False);finite(hi,'condition high',False)
            if lo>hi or not name or name in seen:raise ControlError('invalid condition limits')
            seen.add(name)

@dataclass(frozen=True)
class QuantitativeObservation:
    region: str
    feature: str
    measured_value: float
    units: str
    uncertainty_bound: float
    sensor_id: str
    calibration_id: str
    acquired_s: float
    valid_until_s: float
    conditions: tuple[tuple[str,float],...]
    quality: str
    confounders: tuple[str,...]=()
    phase: str='PRE_WET'
    uncertainty_kind: str='ABSOLUTE_BOUND'

    def __post_init__(self):
        finite(self.measured_value,'measurement',False);finite(self.uncertainty_bound,'uncertainty')
        finite(self.acquired_s,'acquisition');finite(self.valid_until_s,'expiry')
        if self.valid_until_s<self.acquired_s or self.feature not in FEATURES:raise ControlError('invalid observation domain/time')
        if self.uncertainty_kind!='ABSOLUTE_BOUND':raise ControlError('uncertainty kind must be explicit bounded interval')
        if self.quality not in ('ACCEPTED','LOW','UNRELIABLE','UNKNOWN'):raise ControlError('unknown observation quality')
        if not all((self.region,self.sensor_id,self.calibration_id,self.units)):raise ControlError('incomplete observation identity')
        if len(dict(self.conditions))!=len(self.conditions):raise ControlError('duplicate acquisition condition')
        for key,value in self.conditions:finite(value,'condition '+key,False)


def interpret_observation(observation,now,calibrations,accepted_legacy):
    """Keep raw values even when rejected. No saturation/clamping or fallback calibration."""
    finite(now,'evaluation time')
    raw=asdict(observation);reasons=[]
    if isinstance(observation,Observation):
        usable=observation.usable(now,accepted_legacy)
        return {'raw':raw,'interval':BINS[observation.value] if usable else UNKNOWN,
                'quality':'SUPPORTED' if usable else 'UNAVAILABLE',
                'reasons':() if usable else ('LEGACY_OBSERVATION_UNUSABLE',),
                'kind':'ORDINAL_LEGACY_ADAPTER_NO_QUANTITATIVE_PRECISION'}
    if not isinstance(observation,QuantitativeObservation):raise ControlError('unknown observation type')
    c=calibrations.get(observation.calibration_id)
    if c is None:return {'raw':raw,'interval':UNKNOWN,'quality':'UNAVAILABLE','reasons':('UNACCEPTED_CALIBRATION',)}
    if not isinstance(c,Calibration) or c.calibration_id!=observation.calibration_id:raise ControlError('mislabeled calibration')
    if (observation.sensor_id,observation.feature,observation.units)!=(c.sensor_id,c.feature,c.units):reasons.append('SENSOR_FEATURE_UNIT_MISMATCH')
    if not c.valid_from_s<=observation.acquired_s<=now<=c.valid_until_s:reasons.append('CALIBRATION_OR_CLOCK_INVALID')
    if now>observation.valid_until_s or now-observation.acquired_s>c.max_age_s:reasons.append('STALE_OBSERVATION')
    if observation.phase!='PRE_WET':reasons.append('WRONG_PHASE')
    if observation.confounders:reasons.extend(observation.confounders)
    conditions=dict(observation.conditions)
    for key,lo,hi in c.conditions:
        if key not in conditions or not lo<=conditions[key]<=hi:reasons.append('CONDITION_'+key)
    if observation.quality in ('UNRELIABLE','UNKNOWN'):reasons.append('UNRELIABLE_READING')
    bounds=sorted(((observation.measured_value-observation.uncertainty_bound-c.raw_zero)/(c.raw_one-c.raw_zero),
                   (observation.measured_value+observation.uncertainty_bound-c.raw_zero)/(c.raw_one-c.raw_zero)))
    if bounds[0]<0 or bounds[1]>1:reasons.append('OUTSIDE_CALIBRATED_RANGE')
    interval=UNKNOWN if reasons else Interval(*bounds)
    quality='UNAVAILABLE' if reasons else 'LOW' if observation.quality=='LOW' or interval.width>2/3 else 'SUPPORTED'
    return {'raw':raw,'interval':interval,'quality':quality,'reasons':tuple(sorted(set(reasons))),
            'semantic_point':(observation.measured_value-c.raw_zero)/(c.raw_one-c.raw_zero),
            'calibration_digest':c.source_digest,'kind':'CALIBRATED_INTERVAL'}


def compare(survey,observation,*,survey_quality,observation_quality):
    gap=max(0.,observation.low-survey.high,survey.low-observation.high)
    nominal_delta=(observation.low+observation.high-survey.low-survey.high)/2
    # One answer-bin gap distinguishes adjacent variation from separated answers.
    # It is an explainability convention, not a clinical difference threshold.
    severity='COMPATIBLE' if gap==0 else 'MINOR_VARIATION' if gap<1/3 else 'MATERIAL_CONTRADICTION'
    if survey_quality!='SUPPORTED' or observation_quality!='SUPPORTED':
        confidence='LOW';status='INSUFFICIENT'
    else:confidence='SUPPORTED_COMPARISON';status=severity
    return {'status':status,'interval_severity':severity,'confidence':confidence,
        'interval_gap':gap,'gap_in_answer_bins':3*gap,'signed_midpoint_difference':nominal_delta,
        'survey_interval':asdict(survey),'observation_interval':asdict(observation),
        'uncertainty_is_not_probability':True}


def explanation_level(interval,quality):
    if quality=='UNAVAILABLE':return Level.UNKNOWN
    value=(interval.low+interval.high)/2
    return Level.LOW if value<1/3 else Level.MODERATE if value<2/3 else Level.HIGH


def infer(regions,answers: Answers,observations,*,now,accepted_calibrations,calibrations):
    if not regions or len(set(regions))!=len(regions):raise ControlError('regions must be nonempty and unique')
    answers.validate(regions);finite(now,'evaluation time')
    interpreted={r:{} for r in regions}
    for o in observations:
        if o.region not in interpreted:raise ControlError('unregistered physical region')
        if o.feature in interpreted[o.region]:raise ControlError('ambiguous duplicate physical observation')
        interpreted[o.region][o.feature]=interpret_observation(o,now,calibrations,accepted_calibrations)
    result={}
    for r in regions:
        get=lambda key:answers.get(key,r)
        reasons=[];follow=[];confounders=[];survey={};survey_quality={}
        for key in ('usual_oil','usual_dry','current_oil','current_dry'):
            clarity=answers.per_answer_confidence.get(r+'.'+key,answers.per_answer_confidence.get(key,
                'CERTAIN' if get('answer_confidence')=='YES' else 'UNSURE'))
            missing_local=get('left_right_difference')=='YES' and key.startswith('current_') and key not in answers.regional_values.get(r,{})
            known=get(key)!='UNKNOWN' and clarity=='CERTAIN' and not missing_local
            survey[key]=BINS[Level(get(key))] if known else UNKNOWN
            survey_quality[key]='SUPPORTED' if known else 'LOW'
            if not known:follow.append(('REVIEW_ANSWER',r,key));reasons.append('SURVEY_UNCERTAIN_'+key)
        for key in ('product_film','wet_or_sweaty','environment_changed'):
            if get(key)!='NO':confounders.append(key)
        comparisons={};obs={}
        for feature,key in FEATURES.items():
            info=dict(interpreted[r].get(feature,{'raw':None,'interval':UNKNOWN,'quality':'UNAVAILABLE','reasons':('MISSING_OBSERVATION',)}))
            if confounders:info.update(interval=UNKNOWN,quality='UNAVAILABLE',reasons=tuple(confounders))
            obs[feature]=info
            comparisons[key]=compare(survey[key],info['interval'],survey_quality=survey_quality[key],observation_quality=info['quality'])
            status=comparisons[key]['status']
            if status=='MATERIAL_CONTRADICTION':
                reasons.append('CONFLICT_'+key);follow.extend([('REVIEW_ANSWER',r,key),('REPEAT_OBSERVATION',r,feature)])
            elif status=='MINOR_VARIATION':reasons.append('MINOR_'+key)
            elif status=='INSUFFICIENT':follow.append(('REPEAT_OBSERVATION',r,feature))
        if get('recent_cleanse')=='NO' and get('multiple_cleanses')=='YES':
            reasons.append('CONTRADICTORY_RECENT_CLEANSING')
            follow.extend([('REVIEW_ANSWER',r,'recent_cleanse'),('REVIEW_ANSWER',r,'multiple_cleanses')])
        critical=('water_stings','discomfort_now','changed_product','hair_obstruction')
        blocked=any(get(k)!='NO' for k in critical)
        for key in critical:
            if get(key)!='NO':follow.append(('REVIEW_ANSWER',r,key));reasons.append('REVIEW_BEFORE_CONTACT_'+key)
        def risk(keys):
            values=[get(k) for k in keys]
            return 'PRESENT' if 'YES' in values else 'UNKNOWN' if 'UNKNOWN' in values else 'NOT_REPORTED'
        sensitivity=risk(('water_stings','discomfort_now','product_reactivity'))
        stress=risk(('exfoliation','hair_removal','other_stress'))
        recent=risk(('recent_cleanse','multiple_cleanses'))
        for key in ('flaking_now','product_reactivity','exfoliation','hair_removal','other_stress','recent_cleanse','multiple_cleanses'):
            if get(key)=='YES':reasons.append('CAUTION_'+key)
        # Information-loss monotonicity: unknown oil contributes zero demand;
        # unknown dryness/risk contributes the most restrictive supported request.
        oil=obs['surface_oil_proxy'];dry=obs['hydration_deficit_proxy']
        oil_lower=min(survey['current_oil'].low,oil['interval'].low if oil['quality']=='SUPPORTED' else 0)
        dry_upper=max(survey['usual_dry'].high,survey['current_dry'].high,
                      dry['interval'].high if dry['quality']=='SUPPORTED' else 1)
        chemical_need=0 if oil_lower<1/3 else 1 if oil_lower<2/3 else 2
        dryness_ceiling=2 if dry_upper<=1/3 else 1 if dry_upper<=2/3 else 0
        caution=any(v!='NOT_REPORTED' for v in (sensitivity,stress,recent)) or get('flaking_now')!='NO'
        risk_ceiling=0 if caution else 2
        mechanical=min(dryness_ceiling,risk_ceiling)
        relative={'cleanser':min(chemical_need,dryness_ceiling,risk_ceiling),
                  'mechanical':mechanical,'contact_time':mechanical,'passes':min(dryness_ceiling,risk_ceiling),
                  'water':'KEEP_QUALIFIED_REQUIREMENT','rinse':'REQUIRED_UNREDUCED','recovery':'REQUIRED'}
        if blocked:relative={**relative,**{k:0 for k in ('cleanser','mechanical','contact_time','passes')}}
        statuses=[v['status'] for v in comparisons.values()]
        consistency='DISAGREEMENT' if 'MATERIAL_CONTRADICTION' in statuses else 'MINOR_VARIATION' if 'MINOR_VARIATION' in statuses else 'AGREEMENT' if statuses==['COMPATIBLE','COMPATIBLE'] else 'INSUFFICIENT'
        confidence='HIGH_COMPARISON_ONLY' if consistency=='AGREEMENT' else 'LOW'
        decision='BLOCKED_REVIEW' if blocked else 'REPEAT_OBSERVATION' if confounders else 'CONSERVATIVE_REVIEW' if consistency in ('DISAGREEMENT','INSUFFICIENT') or caution else 'PERSONALIZED_WITH_VARIATION' if consistency=='MINOR_VARIATION' else 'PERSONALIZED'
        # Compatibility families remain a restrictive adapter for the previous API.
        family='BLOCKED_REVIEW' if blocked else 'BASELINE' if consistency=='AGREEMENT' and not caution and dryness_ceiling==2 else 'GENTLE_REVIEW'
        for key in ('usual_oil','usual_dry'):
            if survey_quality[key]=='SUPPORTED' and survey_quality[key.replace('usual','current')]=='SUPPORTED' and get(key)!=get(key.replace('usual','current')):
                reasons.append('BASELINE_CURRENT_DIFFERENCE_'+key)
        if blocked:message='Please review the highlighted answers before cleansing.'
        elif confounders:message='Masck needs a new reading because the current conditions do not support this comparison.'
        elif consistency=='DISAGREEMENT':message='Your answers and readings differ here. A lower-action profile is proposed while the highlighted information is reviewed.'
        elif consistency=='MINOR_VARIATION':message='Your answers and readings are close. Small differences are kept within the conservative profile.'
        elif consistency=='INSUFFICIENT':message='Masck cannot confirm this area yet. Review the highlighted answers or repeat its reading.'
        else:message='Your answers and Masck’s observations broadly agree.'
        dimensions={**{k:{'interval':asdict(v),'answer':get(k),'quality':survey_quality[k]} for k,v in survey.items()},
                    **{k:{**v,'interval':asdict(v['interval'])} for k,v in obs.items()},
                    'oil_demand_lower_bound':oil_lower,'dryness_caution_upper_bound':dry_upper}
        result[r]=Profile(r,Level(get('usual_oil')),Level(get('usual_dry')),
            explanation_level(oil['interval'],oil['quality']),explanation_level(dry['interval'],dry['quality']),
            consistency,confidence,family,tuple(sorted(set(reasons))),decision!='PERSONALIZED',sensitivity,stress,recent,
            survey_confidence='SUPPORTED' if all(q=='SUPPORTED' for q in survey_quality.values()) else 'LOW',
            observation_confidence='SUPPORTED' if all(v['quality']=='SUPPORTED' for v in obs.values()) else 'LOW',
            dimensions=dimensions,comparisons=comparisons,relative_request=relative,followups=tuple(sorted(set(follow))),
            confounders=tuple(confounders),decision=decision,user_message=message)
    # Variation is relational information only, never an intensity multiplier.
    from dataclasses import replace
    for r,p in list(result.items()):
        others=tuple(k for k,q in result.items() if k!=r and any(p.dimensions[d]['interval']!=q.dimensions[d]['interval'] for d in ('current_oil','current_dry')))
        result[r]=replace(p,regional_variation=others)
    return result
