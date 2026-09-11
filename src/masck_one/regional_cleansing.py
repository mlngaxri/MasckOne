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
    acquired_s: float|None=None
    valid_until_s: float|None=None
    context_digest: str|None=None

    def validate(self, regions):
        if self.acquired_s is not None or self.valid_until_s is not None:
            finite(self.acquired_s,'survey acquisition');finite(self.valid_until_s,'survey expiry')
            if self.valid_until_s<self.acquired_s:raise ControlError('reversed survey validity')
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
    history_window_s: float|None=None
    personalization_digest: str|None=None

    def __post_init__(self):
        if self.personalization_digest is not None and (len(self.personalization_digest)!=64 or any(c not in '0123456789abcdef' for c in self.personalization_digest)):raise ControlError('invalid personalization binding')
        if self.evidence_scope!='OFF_FACE_SIMULATION':raise ControlError('human-use envelopes are not implemented')
        if self.history_window_s is not None:
            finite(self.history_window_s,'history window')
            if self.history_window_s<=0:raise ControlError('positive history window required')
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
    domain_id: str='CONCEPTUAL_UNREGISTERED'

    def __post_init__(self):
        if not self.region_id or not self.domain_id or not self.cells or any(not isinstance(c,str) or not c for c in self.cells):raise ControlError('explicit region/cells required')
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
    cells: frozenset[str]|None=None

    def __post_init__(self):
        if type(self.sequence) is not int or self.sequence<1:raise ControlError('ordered sequence required')
        for k in ('at_s','force_upper_N','tangential_mm','stroke_upper_mm','cleanser_ml','water_ml'):finite(getattr(self,k),k)
        if type(self.contact) is not bool or type(self.placement_ok) is not bool:raise ControlError('explicit placement/contact required')
        if self.cells is not None and (not self.cells or any(not isinstance(c,str) or not c for c in self.cells)):raise ControlError('invalid telemetry footprint')
        if self.action not in ('IDLE','CLEAN','RINSE','RECOVER'):raise ControlError('unsupported action')
        if not self.contact and (self.force_upper_N or self.tangential_mm or self.stroke_upper_mm):raise ControlError('motion/load without contact')
        if self.action!='CLEAN' and (self.cleanser_ml or self.tangential_mm or self.stroke_upper_mm):raise ControlError('cleaning hidden in another action')


@dataclass(frozen=True)
class StageEvidence:
    session_id: str
    region_id: str
    domain_id: str
    stage: str
    cells: frozenset[str]
    sequence: int
    telemetry_chain: str
    source_digest: str
    evidence_class: str='DIGITAL_SIMULATION'
    basis: str='SIMULATED_OBSERVATION'


@dataclass(frozen=True)
class RecentHistory:
    region_id: str
    domain_id: str
    window_start_s: float
    window_end_s: float
    upper_bound: Burden|None
    source_digest: str
    quality: str
    provenance: str
    evidence_class: str='DIGITAL_SIMULATION'

    def bounded_for(self,region,*,now_s,window_s):
        from .cleansing_evidence import digest_ok
        finite(self.window_start_s,'history start',False);finite(self.window_end_s,'history end',False)
        # A software log or reported event alone is not a measured upper bound.
        if (self.region_id!=region.region_id or self.domain_id!=region.domain_id or window_s is None or
            self.window_start_s>now_s-window_s or self.window_end_s!=now_s or
            self.quality!='BOUNDED' or self.provenance!='SIMULATED_OBSERVED_BOUND' or
            self.evidence_class!='DIGITAL_SIMULATION' or not digest_ok(self.source_digest)):
            return None
        return self.upper_bound if isinstance(self.upper_bound,Burden) else None


class RegionalLedger:
    """Pure simulation monitor. Actual overrun is recorded and latched, never erased.

    Tick values are conservative measured interval bounds, not desired commands.
    A missing/late sample blocks; software is not an independent physical cutoff.
    """
    def __init__(self,region: Region,envelope: Envelope|None,*,start_s=0,prior: Burden|None=None,placement_ok=False,session_id=None):
        self.region=region;self.envelope=envelope;self.at_s=finite(start_s,'start');self.session_id=session_id
        self.event_chain=sha256(json.dumps({'version':VERSION,'session_id':session_id,'region':asdict(region),'start_s':start_s,
            'envelope':asdict(envelope) if envelope else None,'prior':asdict(prior) if prior else None},sort_keys=True,default=sorted).encode()).hexdigest()
        self.total=prior or Burden();self.session=Burden();self.sequence=0;self.active=False;self.wet=False
        self.rinse_ml=0.;self.covered=set();self.state='NOT_STARTED';self.faults=[];self.last_action='IDLE'
        self.stage_cells={k:set() for k in ('CLEAN','RINSE','RECOVER')}
        self.last_cells=set();self.started_cells=set();self.evidence_digests=[];self.history_source=None
        if region.classification!='REQUIRED':self.state=region.classification
        elif envelope is None:self.block('UNQUALIFIED_LIMITS')
        elif prior is None:self.block('UNKNOWN_RECENT_BURDEN')
        elif not placement_ok:self.block('INCOMPLETE_PLACEMENT')
        elif not prior.within(envelope.maximum):self.block('RECENT_BURDEN_EXHAUSTED')
        elif not isinstance(session_id,str) or not session_id:self.block('UNBOUND_SESSION')

    def _event(self,kind,payload):
        encoded=json.dumps({'kind':kind,'payload':payload},sort_keys=True,allow_nan=False,default=sorted)
        self.event_chain=sha256((self.event_chain+encoded).encode()).hexdigest()

    def block(self,reason):
        if reason not in self.faults:
            self.faults.append(reason);self._event('FAULT',reason)
        self.state='BLOCKED'

    def permits(self,increment: Burden,*,force_upper_N,stroke_upper_mm,now_s=None,cells=None):
        finite(force_upper_N,'force');finite(stroke_upper_mm,'stroke')
        p=self.envelope
        footprint=set(self.region.cells if cells is None else cells)
        if not footprint or not footprint<=self.region.cells or footprint & self.stage_cells['CLEAN']:return False
        if now_s is None:return False
        finite(now_s,'command time')
        return bool(p and self.at_s<=now_s<=self.at_s+p.max_sample_gap_s and not self.faults and self.state in ('NOT_STARTED','IN_PROGRESS')
            and force_upper_N<=p.max_force_N and stroke_upper_mm<=p.max_stroke_mm
            and self.total.plus(increment).within(p.maximum)
            and self.total.water_ml+increment.water_ml+p.min_rinse_ml<=p.maximum.water_ml)

    def ingest(self,tick: Tick):
        if tick.sequence!=self.sequence+1 or tick.at_s<=self.at_s:
            self.block('STALE_OR_REPLAYED_TELEMETRY');raise ControlError('nonmonotonic telemetry')
        self._event('TELEMETRY',asdict(tick))
        dt=tick.at_s-self.at_s
        was_wet=self.wet
        pass_start=tick.action=='CLEAN' and not self.active
        increment=Burden(dt if tick.contact else 0,tick.force_upper_N*dt if tick.contact else 0,
            tick.tangential_mm,tick.force_upper_N*tick.tangential_mm,tick.cleanser_ml,
            dt if was_wet or tick.cleanser_ml>0 else 0,tick.water_ml,int(pass_start))
        self.total=self.total.plus(increment);self.session=self.session.plus(increment)
        self.sequence=tick.sequence;self.at_s=tick.at_s
        self.last_action=tick.action
        self.last_cells=set(self.region.cells if tick.cells is None else tick.cells)
        if not self.last_cells<=self.region.cells:self.block('UNKNOWN_TELEMETRY_FOOTPRINT')
        if tick.action=='CLEAN':self.started_cells.update(self.last_cells & self.region.cells)
        if tick.contact and self.state in ('RECOVERED','COMPLETE'):self.block('CONTACT_AFTER_COMPLETION')
        if tick.water_ml and tick.action not in ('CLEAN','RINSE'):self.block('UNDECLARED_WATER_FLOW')
        if tick.action=='CLEAN' and self.last_cells & self.stage_cells['CLEAN']:self.block('REPEATED_COMPLETE_CELL')
        self.active=tick.action=='CLEAN';self.wet=was_wet or tick.cleanser_ml>0
        if tick.action=='RINSE':self.rinse_ml+=tick.water_ml
        if tick.cleanser_ml>0:self.rinse_ml=0  # No earlier water can rinse a later dose.
        if self.region.classification!='REQUIRED':self.block('ACTION_ON_NONTARGET')
        if not tick.placement_ok:self.block('PLACEMENT_LOST')
        if tick.action=='CLEAN' and self.state not in ('NOT_STARTED','IN_PROGRESS'):
            self.block('REPEATED_OR_UNAUTHORIZED_CLEAN')
        if tick.action=='RINSE' and self.state not in ('CLEANSED','BLOCKED'):self.block('STAGE_ORDER')
        if tick.action=='RECOVER' and self.state not in ('RINSED','BLOCKED'):self.block('STAGE_ORDER')
        p=self.envelope
        if p is None:self.block('UNQUALIFIED_LIMITS')
        else:
            if dt>p.max_sample_gap_s:self.block('TELEMETRY_GAP')
            if tick.force_upper_N>p.max_force_N or tick.stroke_upper_mm>p.max_stroke_mm:self.block('INSTANTANEOUS_LIMIT')
            if not self.total.within(p.maximum):self.block('CUMULATIVE_LIMIT')
        if not self.faults and tick.action=='CLEAN':self.state='IN_PROGRESS'
        return self.state

    def record_stage(self,evidence):
        from .cleansing_evidence import digest_ok
        if not isinstance(evidence,StageEvidence):raise ControlError('stage-specific observed evidence required')
        required_state={'CLEAN':'IN_PROGRESS','RINSE':'CLEANSED','RECOVER':'RINSED'}
        if (self.faults or self.state!=required_state.get(evidence.stage) or
            evidence.session_id!=self.session_id or type(evidence.sequence) is not int or
            evidence.region_id!=self.region.region_id or evidence.domain_id!=self.region.domain_id or
            evidence.stage!=self.last_action or evidence.sequence!=self.sequence or
            evidence.telemetry_chain!=self.event_chain or not evidence.cells or
            not evidence.cells<=self.last_cells or evidence.evidence_class!='DIGITAL_SIMULATION' or
            evidence.basis!='SIMULATED_OBSERVATION' or not digest_ok(evidence.source_digest)):
            raise ControlError('unbound or unobserved stage evidence')
        self.stage_cells[evidence.stage].update(evidence.cells)
        if evidence.stage=='CLEAN':self.covered.update(evidence.cells)
        self.evidence_digests.append(evidence.source_digest)
        self._event('STAGE_EVIDENCE',asdict(evidence))

    def record_cells(self,cells,*,evidence=None):
        if not isinstance(evidence,StageEvidence) or evidence.stage!='CLEAN' or set(cells)!=set(evidence.cells):
            raise ControlError('bare coverage or command receipt cannot prove cleansing')
        self.record_stage(evidence)

    def cleansed(self):
        if self.state!='IN_PROGRESS' or self.stage_cells['CLEAN']!=set(self.region.cells):raise ControlError('required clean cell missing')
        self.state='CLEANSED';self.active=False;self._event('STATE',self.state)

    def rinsed(self):
        if (self.state!='CLEANSED' or self.stage_cells['RINSE']!=set(self.region.cells) or
            self.last_action!='RINSE' or self.envelope is None or self.rinse_ml<self.envelope.min_rinse_ml):
            raise ControlError('required rinse cell or measured rinse quantity missing')
        self.state='RINSED';self._event('STATE',self.state)

    def recovered(self):
        if self.state!='RINSED' or self.stage_cells['RECOVER']!=set(self.region.cells) or self.last_action!='RECOVER':
            raise ControlError('required recovery cell missing')
        self.wet=False;self.state='RECOVERED';self._event('STATE',self.state)

    def rinsed_recovered(self,*,recovery_receipt,physical_validation=False):
        # Strict compatibility entry: it can no longer bypass an independent rinse.
        if physical_validation:raise ControlError('simulation cannot create physical evidence')
        self.record_stage(recovery_receipt);self.recovered()

    def complete(self):
        if self.state!='RECOVERED' or self.wet or self.faults:raise ControlError('regional completion blocked')
        self.state='COMPLETE';self._event('STATE',self.state)

    def cell_status(self):
        result={}
        for cell in sorted(self.region.cells):
            if self.state in ('BLOCKED','PROTECTED','EXCLUDED'):status=self.state
            elif self.state=='COMPLETE':status='COMPLETE'
            elif cell in self.stage_cells['RECOVER']:status='RECOVERED'
            elif cell in self.stage_cells['RINSE']:status='RINSED'
            elif cell in self.stage_cells['CLEAN']:status='CLEANSED'
            elif cell in self.started_cells:status='IN_PROGRESS_UNPROVED'
            else:status='NOT_STARTED'
            result[cell]=status
        return result

    def receipt(self):
        payload={'version':VERSION,'session_id':self.session_id,'region':self.region.region_id,'cell_status':self.cell_status(),'cells':sorted(self.region.cells),
            'covered_cells':sorted(self.covered),'stage_cells':{k:sorted(v) for k,v in self.stage_cells.items()},
            'domain_id':self.region.domain_id,'stage_evidence_digests':self.evidence_digests[:],
            'session_burden':asdict(self.session),'recent_history_source':self.history_source,'state':self.state,'event_chain':self.event_chain,'burden':asdict(self.total),
            'faults':self.faults[:],'last_sequence':self.sequence,'at_s':self.at_s,
            'policy_digest':self.envelope.source_digest if self.envelope else None,
            'personalization_digest':self.envelope.personalization_digest if self.envelope else None,
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


def plan(profiles,regions,policies,*,placement,history,factor_policy=None,start_s=0,session_id=None):
    check_policy_families(policies)
    if set(policies)-{'BASELINE'}:raise ControlError('selected planner requires baseline hard envelope plus explicit factor policy; legacy family tables cannot be silently ignored')
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
        h=history.get(key)
        prior=h.bounded_for(region,now_s=start_s,window_s=p.history_window_s) if isinstance(h,RecentHistory) and p else None
        ledger=RegionalLedger(region,p,start_s=start_s,placement_ok=placement.get(key) is True,prior=prior,session_id=session_id)
        if isinstance(h,RecentHistory):
            ledger.history_source=asdict(h);ledger._event('HISTORY',asdict(h))
        if profile.family=='BLOCKED_REVIEW':ledger.block('PROFILE_REVIEW')
        result[key]=ledger
    return result


class SessionLedger:
    """Common supply and shared-action coupling for the off-face simulation."""
    def __init__(self,expected_regions,ledgers,*,water_limit_ml=None,cleanser_limit_ml=None):
        if set(expected_regions)!=set(ledgers):raise ControlError('session region inventory mismatch')
        if any(l.region!=expected_regions[r] for r,l in ledgers.items()):raise ControlError('session domain mismatch')
        if len({l.session_id for l in ledgers.values() if l.region.classification=='REQUIRED'})>1:raise ControlError('mixed execution sessions')
        self.expected=dict(expected_regions);self.ledgers=dict(ledgers)
        self.water_limit=water_limit_ml;self.cleanser_limit=cleanser_limit_ml
        if water_limit_ml is None or cleanser_limit_ml is None:
            for l in self.ledgers.values():l.block('UNKNOWN_SESSION_RESOURCE')
        else:finite(water_limit_ml,'session water');finite(cleanser_limit_ml,'session cleanser')

    def ingest(self,region,tick):
        if region not in self.ledgers:raise ControlError('unregistered execution region')
        state=self.ledgers[region].ingest(tick)
        if self.water_limit is None or self.cleanser_limit is None:return 'BLOCKED'
        # Prior exposure constrains each region; only this session debits its supply.
        if (sum(l.session.water_ml for l in self.ledgers.values())>self.water_limit or
            sum(l.session.cleanser_ml for l in self.ledgers.values())>self.cleanser_limit):
            for l in self.ledgers.values():l.block('SHARED_RESOURCE_EXHAUSTED')
            return 'BLOCKED'
        return state

    def authorize_shared(self,footprint,increment,*,force_upper_N,stroke_upper_mm,now_s):
        if self.water_limit is None or self.cleanser_limit is None or not shared_channel_permitted(footprint,self.ledgers):return False
        if (sum(l.session.water_ml for l in self.ledgers.values())+len(footprint)*increment.water_ml>self.water_limit or
            sum(l.session.cleanser_ml for l in self.ledgers.values())+len(footprint)*increment.cleanser_ml>self.cleanser_limit):return False
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
