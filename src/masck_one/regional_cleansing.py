"""Deterministic cosmetic evidence and regional budget kernel.

No diagnosis, ML, device I/O or human-use envelope. Numerical envelopes are
explicit off-face simulation inputs. Missing qualified limits cannot actuate.
Whole-routine completion belongs to the canonical Core Sketch consumer.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
from hashlib import sha256
import json
import math
from typing import Mapping

VERSION = 'MASCK_REGIONAL_CLEANSING_CONTRACT_2'

class ControlError(ValueError):
    pass


def finite(v, name, nonnegative=True):
    if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or (nonnegative and v<0):
        raise ControlError('invalid '+name)
    return float(v)


class Level(str,Enum):
    UNKNOWN='UNKNOWN'
    LOW='LOW'
    MODERATE='MODERATE'
    HIGH='HIGH'


from .cleansing_onboarding import QUESTIONS as ONBOARDING_QUESTIONS
QUESTIONNAIRE=tuple((q.id,q.prompt,q.answer_family,q.regional,q.variable) for q in ONBOARDING_QUESTIONS)
QUESTIONS={q[0]:q for q in QUESTIONNAIRE}


@dataclass(frozen=True)
class Answers:
    global_values: Mapping[str,str]
    regional_values: Mapping[str,Mapping[str,str]]=field(default_factory=dict)

    per_answer_confidence: Mapping[str,str]=field(default_factory=dict)

    def validate(self, regions):
        allowed_keys={key for key in QUESTIONS}|{r+'.'+key for r in regions for key in QUESTIONS}
        for key,value in self.per_answer_confidence.items():
            if key not in allowed_keys or value not in ('CERTAIN','UNSURE','UNKNOWN'):raise ControlError('invalid answer confidence')
        for scope, values in [('GLOBAL',self.global_values),*self.regional_values.items()]:
            if scope!='GLOBAL' and scope not in regions:raise ControlError('unknown questionnaire region')
            for key,value in values.items():
                if key not in QUESTIONS:raise ControlError('unrecognized question: '+key)
                q=QUESTIONS[key]
                allowed={v.value for v in Level} if q[2]=='LEVEL' else {'YES','NO','UNKNOWN'}
                if value not in allowed:raise ControlError('invalid answer: '+key)
                if scope!='GLOBAL' and not q[3]:raise ControlError('nonregional question overridden')

    def get(self,key,region):
        value=self.regional_values.get(region,{}).get(key,self.global_values.get(key,'UNKNOWN'))
        clarity=self.per_answer_confidence.get(region+'.'+key,self.per_answer_confidence.get(key,'CERTAIN'))
        # Uncertain denial cannot erase a possible caution; a reported concern remains.
        if QUESTIONS[key][2]=='YES_NO' and value=='NO' and clarity!='CERTAIN':return 'UNKNOWN'
        return value


@dataclass(frozen=True)
class Observation:
    region: str
    feature: str
    value: Level
    acquired_s: float
    valid_until_s: float
    calibration_id: str
    phase: str='PRE_WET'
    confounders: tuple[str,...]=()
    quality: str='UNKNOWN'

    def usable(self,now,accepted_calibrations):
        finite(now,'observation time');finite(self.acquired_s,'acquisition');finite(self.valid_until_s,'expiry')
        if not isinstance(self.value,Level):raise ControlError('untyped observation level')
        if self.feature not in ('surface_oil_proxy','hydration_deficit_proxy'):raise ControlError('unsupported observation feature')
        if self.valid_until_s<self.acquired_s:raise ControlError('reversed observation validity')
        return (self.calibration_id in accepted_calibrations and self.quality=='ACCEPTED'
                and self.acquired_s<=now<=self.valid_until_s and self.phase=='PRE_WET'
                and not self.confounders and self.value!=Level.UNKNOWN)


@dataclass(frozen=True)
class Profile:
    region: str
    oil_tendency: Level
    dry_tendency: Level
    apparent_oil: Level
    apparent_dryness: Level
    consistency: str
    confidence: str
    family: str
    reasons: tuple[str,...]
    review_required: bool
    sensitivity_risk: str
    barrier_stress_risk: str
    recent_burden_risk: str
    version: str=VERSION
    survey_confidence: str='UNKNOWN'
    observation_confidence: str='UNKNOWN'
    dimensions: Mapping=field(default_factory=dict)
    comparisons: Mapping=field(default_factory=dict)
    relative_request: Mapping=field(default_factory=dict)
    followups: tuple=()
    confounders: tuple=()
    regional_variation: tuple=()
    decision: str='UNRESOLVED'
    user_message: str=''


def estimate(regions,answers: Answers,observations=(),*,now=0,accepted_calibrations=frozenset(),calibrations=None):
    from .cleansing_evidence import infer
    return infer(regions,answers,observations,now=now,accepted_calibrations=accepted_calibrations,calibrations=calibrations or {})


@dataclass(frozen=True)
class Burden:
    contact_s: float=0
    load_Ns: float=0
    tangential_mm: float=0
    shear_proxy_Nmm: float=0
    cleanser_ml: float=0
    cleanser_residence_s: float=0
    water_ml: float=0
    passes: int=0

    def __post_init__(self):
        for k,v in asdict(self).items():finite(v,k)
        if type(self.passes) is not int:raise ControlError('integer passes required')

    def plus(self,other):return Burden(**{k:getattr(self,k)+getattr(other,k) for k in asdict(self)})
    def within(self,maximum):return all(getattr(self,k)<=getattr(maximum,k) for k in asdict(self))


@dataclass(frozen=True)
class Envelope:
    policy_id: str
    source_digest: str
    family: str
    maximum: Burden
    max_force_N: float
    max_stroke_mm: float
    min_rinse_ml: float
    max_sample_gap_s: float
    evidence_scope: str='OFF_FACE_SIMULATION'

    def __post_init__(self):
        if self.evidence_scope!='OFF_FACE_SIMULATION':raise ControlError('human-use envelopes are not implemented')
        if self.family not in ('BASELINE','GENTLE_REVIEW'):raise ControlError('unsupported envelope family')
        if len(self.source_digest)!=64 or any(c not in '0123456789abcdef' for c in self.source_digest):raise ControlError('policy digest required')
        if not self.policy_id:raise ControlError('policy identity required')
        for k in ('max_force_N','max_stroke_mm','min_rinse_ml','max_sample_gap_s'):finite(getattr(self,k),k)
        if self.min_rinse_ml<=0 or self.max_sample_gap_s<=0:raise ControlError('rinse and telemetry limits required')
        if self.min_rinse_ml>self.maximum.water_ml:raise ControlError('rinse cannot fit water budget')


def check_policy_families(policies):
    if 'GENTLE_REVIEW' in policies and 'BASELINE' not in policies:
        raise ControlError('baseline comparison required for gentle ceiling')
    for key,p in policies.items():
        if key!=p.family:raise ControlError('mislabeled policy')
    if 'GENTLE_REVIEW' in policies and 'BASELINE' in policies:
        g,b=policies['GENTLE_REVIEW'],policies['BASELINE']
        if not g.maximum.within(b.maximum) or g.max_force_N>b.max_force_N or g.max_stroke_mm>b.max_stroke_mm:
            raise ControlError('uncertainty cannot increase any action ceiling')
        # Reducing mechanical action must not remove necessary rinse.
        if g.min_rinse_ml<b.min_rinse_ml:raise ControlError('gentle policy cannot silently reduce rinse requirement')


@dataclass(frozen=True)
class Region:
    region_id: str
    cells: frozenset[str]
    classification: str='REQUIRED'
    exclusion_reason: str=''

    def __post_init__(self):
        if not self.region_id or not self.cells:raise ControlError('explicit region/cells required')
        if self.classification not in ('REQUIRED','PROTECTED','EXCLUDED'):raise ControlError('unknown region classification')
        if self.classification!='REQUIRED' and not self.exclusion_reason:raise ControlError('omission requires reason')


@dataclass(frozen=True)
class Tick:
    sequence: int
    at_s: float
    action: str
    contact: bool=False
    force_upper_N: float=0
    tangential_mm: float=0
    stroke_upper_mm: float=0
    cleanser_ml: float=0
    water_ml: float=0
    placement_ok: bool=True

    def __post_init__(self):
        if type(self.sequence) is not int or self.sequence<1:raise ControlError('ordered sequence required')
        for k in ('at_s','force_upper_N','tangential_mm','stroke_upper_mm','cleanser_ml','water_ml'):finite(getattr(self,k),k)
        if type(self.contact) is not bool or type(self.placement_ok) is not bool:raise ControlError('explicit placement/contact required')
        if self.action not in ('IDLE','CLEAN','RINSE','RECOVER'):raise ControlError('unsupported action')
        if not self.contact and (self.force_upper_N or self.tangential_mm or self.stroke_upper_mm):raise ControlError('motion/load without contact')
        if self.action!='CLEAN' and (self.cleanser_ml or self.tangential_mm or self.stroke_upper_mm):raise ControlError('cleaning hidden in another action')


@dataclass(frozen=True)
class RecoveryEvidence:
    region_id: str
    sequence: int
    source_digest: str
    evidence_class: str='DIGITAL_SIMULATION'

    def matches(self,region,sequence):
        return (self.region_id==region and self.sequence==sequence and
                self.evidence_class=='DIGITAL_SIMULATION' and
                isinstance(self.source_digest,str) and len(self.source_digest)==64 and
                all(c in '0123456789abcdef' for c in self.source_digest))


class RegionalLedger:
    """Pure simulation monitor. Actual overrun is recorded and latched, never erased.

    Tick values are conservative measured interval bounds, not desired commands.
    A missing/late sample blocks; software is not an independent physical cutoff.
    """
    def __init__(self,region: Region,envelope: Envelope|None,*,start_s=0,prior: Burden|None=None,placement_ok=False):
        self.region=region;self.envelope=envelope;self.at_s=finite(start_s,'start')
        self.event_chain=sha256(json.dumps({'region':asdict(region),'start_s':start_s,'prior':asdict(prior) if prior else None},sort_keys=True,default=sorted).encode()).hexdigest()
        self.total=prior or Burden();self.sequence=0;self.active=False;self.wet=False
        self.rinse_ml=0.;self.covered=set();self.state='NOT_STARTED';self.faults=[];self.last_action='IDLE'
        if region.classification!='REQUIRED':self.state=region.classification
        elif envelope is None:self.block('UNQUALIFIED_LIMITS')
        elif prior is None:self.block('UNKNOWN_RECENT_BURDEN')
        elif not placement_ok:self.block('INCOMPLETE_PLACEMENT')
        elif not prior.within(envelope.maximum):self.block('RECENT_BURDEN_EXHAUSTED')

    def block(self,reason):
        if reason not in self.faults:self.faults.append(reason)
        self.state='BLOCKED'

    def permits(self,increment: Burden,*,force_upper_N,stroke_upper_mm,now_s=None):
        finite(force_upper_N,'force');finite(stroke_upper_mm,'stroke')
        p=self.envelope
        if now_s is None:return False
        finite(now_s,'command time')
        return bool(p and self.at_s<=now_s<=self.at_s+p.max_sample_gap_s and not self.faults and self.state in ('NOT_STARTED','IN_PROGRESS')
            and force_upper_N<=p.max_force_N and stroke_upper_mm<=p.max_stroke_mm
            and self.total.plus(increment).within(p.maximum))

    def ingest(self,tick: Tick):
        if tick.sequence!=self.sequence+1 or tick.at_s<=self.at_s:
            self.block('STALE_OR_REPLAYED_TELEMETRY');raise ControlError('nonmonotonic telemetry')
        self.event_chain=sha256((self.event_chain+json.dumps(asdict(tick),sort_keys=True,allow_nan=False)).encode()).hexdigest()
        dt=tick.at_s-self.at_s
        was_wet=self.wet
        pass_start=tick.action=='CLEAN' and not self.active
        increment=Burden(dt if tick.contact else 0,tick.force_upper_N*dt if tick.contact else 0,
            tick.tangential_mm,tick.force_upper_N*tick.tangential_mm,tick.cleanser_ml,
            dt if was_wet or tick.cleanser_ml>0 else 0,tick.water_ml,int(pass_start))
        self.total=self.total.plus(increment)
        self.sequence=tick.sequence;self.at_s=tick.at_s
        self.last_action=tick.action
        self.active=tick.action=='CLEAN';self.wet=was_wet or tick.cleanser_ml>0
        if tick.action=='RINSE':self.rinse_ml+=tick.water_ml
        if tick.cleanser_ml>0:self.rinse_ml=0  # No earlier water can rinse a later dose.
        if self.region.classification!='REQUIRED':self.block('ACTION_ON_NONTARGET')
        if not tick.placement_ok:self.block('PLACEMENT_LOST')
        if tick.action=='CLEAN' and self.state not in ('NOT_STARTED','IN_PROGRESS'):
            self.block('REPEATED_OR_UNAUTHORIZED_CLEAN')
        if tick.action in ('RINSE','RECOVER') and self.state not in ('CLEANSED','BLOCKED','RINSED_RECOVERED'):
            self.block('STAGE_ORDER')
        p=self.envelope
        if p is None:self.block('UNQUALIFIED_LIMITS')
        else:
            if dt>p.max_sample_gap_s:self.block('TELEMETRY_GAP')
            if tick.force_upper_N>p.max_force_N or tick.stroke_upper_mm>p.max_stroke_mm:self.block('INSTANTANEOUS_LIMIT')
            if not self.total.within(p.maximum):self.block('CUMULATIVE_LIMIT')
        if not self.faults and tick.action=='CLEAN':self.state='IN_PROGRESS'
        return self.state

    def record_cells(self,cells):
        cells=set(cells)
        if self.state!='IN_PROGRESS' or not cells or not cells<=self.region.cells:raise ControlError('invalid regional coverage receipt')
        self.covered.update(cells)

    def cleansed(self):
        if self.state!='IN_PROGRESS' or self.covered!=set(self.region.cells):raise ControlError('required cell missing')
        self.state='CLEANSED';self.active=False

    def rinsed_recovered(self,*,recovery_receipt,physical_validation=False):
        if physical_validation:raise ControlError('simulation cannot create physical evidence')
        if (self.state!='CLEANSED' or self.last_action!='RECOVER' or not isinstance(recovery_receipt,RecoveryEvidence)
            or not recovery_receipt.matches(self.region.region_id,self.sequence) or self.envelope is None
            or self.rinse_ml<self.envelope.min_rinse_ml):
            raise ControlError('rinse/recovery incomplete')
        self.wet=False;self.state='RINSED_RECOVERED'

    def complete(self):
        if self.state!='RINSED_RECOVERED' or self.wet or self.faults:raise ControlError('regional completion blocked')
        self.state='COMPLETE'

    def receipt(self):
        payload={'version':VERSION,'region':self.region.region_id,'cells':sorted(self.region.cells),
            'covered_cells':sorted(self.covered),'state':self.state,'event_chain':self.event_chain,'burden':asdict(self.total),
            'faults':self.faults[:],'last_sequence':self.sequence,'at_s':self.at_s,
            'policy_digest':self.envelope.source_digest if self.envelope else None,
            'evidence_class':'DIGITAL_SIMULATION','human_use_eligible':False,
            'whole_routine_complete':False}
        payload['digest']=sha256(json.dumps(payload,sort_keys=True,allow_nan=False).encode()).hexdigest()
        return payload


def simulated_cleansing_complete(expected_regions,ledgers):
    """Only this cleansing simulation; never whole-routine/physical completion."""
    if not isinstance(expected_regions,Mapping) or set(expected_regions)!=set(ledgers) or not expected_regions:return False
    return all(l.region==expected_regions[r] and l.region.region_id==r and (l.state=='COMPLETE' if l.region.classification=='REQUIRED'
               else l.state==l.region.classification) for r,l in ledgers.items()) and any(
                   l.region.classification=='REQUIRED' for l in ledgers.values())


def shared_channel_permitted(footprint,ledgers):
    """All touched regions constrain a shared actuator or outlet; no averaging."""
    if not footprint or not set(footprint)<=set(ledgers):return False
    return all(ledgers[r].state in ('NOT_STARTED','IN_PROGRESS') and not ledgers[r].faults for r in footprint)


def plan(profiles,regions,policies,*,placement,history,factor_policy=None):
    check_policy_families(policies)
    if set(profiles)!=set(regions):raise ControlError('profile/required region mismatch')
    result={};seen=set()
    for key,region in regions.items():
        if seen & region.cells:raise ControlError('same coverage cell assigned twice')
        seen.update(region.cells)
        if key!=region.region_id:raise ControlError('region identity mismatch')
        profile=profiles[key]
        if profile.region!=key:raise ControlError('profile assigned to wrong region')
        from .cleansing_prescription import resolve
        resolved=resolve(profile,policies.get('BASELINE'),factor_policy)
        p=resolved['envelope']
        ledger=RegionalLedger(region,p,placement_ok=placement.get(key) is True,prior=history.get(key))
        if profile.family=='BLOCKED_REVIEW':ledger.block('PROFILE_REVIEW')
        result[key]=ledger
    return result


class SessionLedger:
    """Common supply and shared-action coupling for the off-face simulation."""
    def __init__(self,expected_regions,ledgers,*,water_limit_ml=None,cleanser_limit_ml=None):
        if set(expected_regions)!=set(ledgers):raise ControlError('session region inventory mismatch')
        self.expected=dict(expected_regions);self.ledgers=dict(ledgers)
        self.water_limit=water_limit_ml;self.cleanser_limit=cleanser_limit_ml
        if water_limit_ml is None or cleanser_limit_ml is None:
            for l in self.ledgers.values():l.block('UNKNOWN_SESSION_RESOURCE')
        else:finite(water_limit_ml,'session water');finite(cleanser_limit_ml,'session cleanser')

    def ingest(self,region,tick):
        if region not in self.ledgers:raise ControlError('unregistered execution region')
        state=self.ledgers[region].ingest(tick)
        if self.water_limit is None or self.cleanser_limit is None:return 'BLOCKED'
        # Includes prior known consumption, never silently resets across regions.
        if (sum(l.total.water_ml for l in self.ledgers.values())>self.water_limit or
            sum(l.total.cleanser_ml for l in self.ledgers.values())>self.cleanser_limit):
            for l in self.ledgers.values():l.block('SHARED_RESOURCE_EXHAUSTED')
            return 'BLOCKED'
        return state

    def authorize_shared(self,footprint,increment,*,force_upper_N,stroke_upper_mm,now_s):
        if self.water_limit is None or self.cleanser_limit is None or not shared_channel_permitted(footprint,self.ledgers):return False
        if (sum(l.total.water_ml for l in self.ledgers.values())+len(footprint)*increment.water_ml>self.water_limit or
            sum(l.total.cleanser_ml for l in self.ledgers.values())+len(footprint)*increment.cleanser_ml>self.cleanser_limit):return False
        return all(self.ledgers[r].permits(increment,force_upper_N=force_upper_N,
            stroke_upper_mm=stroke_upper_mm,now_s=now_s) for r in footprint)

    def complete(self):return simulated_cleansing_complete(self.expected,self.ledgers)


def prescription(profile,envelope=None,*,factor_policy=None):
    """Compatibility view; use factor_policy for the selected multidimensional path."""
    if factor_policy is not None:
        from .cleansing_prescription import resolve
        return resolve(profile,envelope,factor_policy)
    if envelope is not None and (profile.family=='BLOCKED_REVIEW' or envelope.family!=profile.family):
        raise ControlError('prescription/envelope mismatch')
    return {'region':profile.region,'version':VERSION,'family':profile.family,
        'confidence':profile.confidence,'review_required':profile.review_required,
        'explanations':list(profile.reasons),'human_use_eligible':False,
        'state':'BLOCKED_UNQUALIFIED_PERSONALIZATION' if envelope else 'BLOCKED_UNQUALIFIED_LIMITS',
        'cleanser_exposure_max_ml':envelope.maximum.cleanser_ml if envelope else None,
        'water_exposure_max_ml':envelope.maximum.water_ml if envelope else None,
        'contact_load_max_N':envelope.max_force_N if envelope else None,
        'stroke_max_mm':envelope.max_stroke_mm if envelope else None,
        'tangential_path_max_mm':envelope.maximum.tangential_mm if envelope else None,
        'contact_time_max_s':envelope.maximum.contact_s if envelope else None,
        'passes_max':envelope.maximum.passes if envelope else None,
        'rinse_min_ml':envelope.min_rinse_ml if envelope else None,
        'recovery_required':True,'commanded_duration_s':None,
        'stop_conditions':['PLACEMENT_LOST','INSTANTANEOUS_LIMIT','CUMULATIVE_LIMIT','TELEMETRY_GAP',
                           'REPEATED_OR_UNAUTHORIZED_CLEAN','SHARED_RESOURCE_EXHAUSTED']}
