"""Separate relative personalization, absolute limits and current execution budget."""
from dataclasses import dataclass, asdict, replace
from math import floor
import json
from hashlib import sha256
from .regional_cleansing import Burden, Envelope, ControlError, finite
from .cleansing_evidence import digest_ok

DIMENSIONS=('cleanser','mechanical','contact_time','passes')

@dataclass(frozen=True)
class FactorPolicy:
    policy_id: str
    source_digest: str
    # Per dimension: MINIMUM, REDUCED, REFERENCE; values come from an evidence table.
    factors: tuple[tuple[str,tuple[float,float,float]],...]
    scope: str='OFF_FACE_SIMULATION'
    fallback_contexts: tuple[str,...]=()

    def __post_init__(self):
        if self.scope!='OFF_FACE_SIMULATION' or not self.policy_id or not digest_ok(self.source_digest):raise ControlError('unqualified relative factor policy')
        if set(dict(self.factors))!=set(DIMENSIONS) or len(self.factors)!=len(DIMENSIONS):raise ControlError('factor dimensions missing/duplicated')
        if len(set(self.fallback_contexts))!=len(self.fallback_contexts) or not set(self.fallback_contexts)<= {'product_film','wet_or_sweaty','environment_changed'}:raise ControlError('unknown fallback context')
        for dimension,values in self.factors:
            if len(values)!=3:raise ControlError('three explicit ordinal factors required')
            for v in values:finite(v,dimension+' factor')
            if not 0<=values[0]<=values[1]<=values[2]<=1:raise ControlError('factors may not amplify absolute ceilings')


def resolve(profile,absolute: Envelope|None,factor_policy: FactorPolicy|None):
    """No numeric fallback. No uncertainty multiplier and no rinse discount."""
    proposal={k:profile.relative_request.get(k) for k in DIMENSIONS}
    base={'region':profile.region,'profile_version':profile.version,'personalization':proposal,
          'decision':profile.decision,'human_use_eligible':False,'review_required':profile.review_required,
          'explanation':profile.user_message,'followups':list(profile.followups),'envelope':None}
    if profile.decision=='BLOCKED_REVIEW' or profile.family=='BLOCKED_REVIEW':return {**base,'status':'BLOCKED_PROFILE_REVIEW'}
    fallback=profile.decision=='REPEAT_OBSERVATION'
    if fallback and (factor_policy is None or not profile.confounders or not set(profile.confounders)<=set(factor_policy.fallback_contexts)):
        return {**base,'status':'BLOCKED_CURRENT_OBSERVATION_CONTEXT'}
    if profile.decision not in ('PERSONALIZED','PERSONALIZED_WITH_VARIATION','CONSERVATIVE_REVIEW','REPEAT_OBSERVATION'):raise ControlError('unrecognized profile decision')
    if absolute is None or factor_policy is None:return {**base,'status':'BLOCKED_UNQUALIFIED_LIMITS'}
    if absolute.evidence_scope!='OFF_FACE_SIMULATION' or factor_policy.scope!='OFF_FACE_SIMULATION':raise ControlError('unsupported evidence scope')
    if absolute.history_window_s is None:return {**base,'status':'BLOCKED_UNQUALIFIED_HISTORY_WINDOW'}
    factors=dict(factor_policy.factors)
    for k,level in proposal.items():
        if type(level) is not int or not 0<=level<=2:raise ControlError('unknown personalization request')
    chosen={k:factors[k][0 if fallback else level] for k,level in proposal.items()}
    m=absolute.maximum;c=chosen['cleanser'];a=chosen['mechanical'];t=chosen['contact_time'];p=chosen['passes']
    bounded=Burden(contact_s=m.contact_s*t,load_Ns=m.load_Ns*a*t,
        tangential_mm=m.tangential_mm*a,shear_proxy_Nmm=m.shear_proxy_Nmm*a*a,
        cleanser_ml=m.cleanser_ml*c,cleanser_residence_s=m.cleanser_residence_s*c,
        water_ml=m.water_ml,passes=floor(m.passes*p))
    # Keep the qualified rinse minimum, supply ceiling and telemetry timing.
    binding=sha256(json.dumps({'profile':asdict(profile),'absolute':asdict(absolute),'factors':asdict(factor_policy)},sort_keys=True,allow_nan=False).encode()).hexdigest()
    output=replace(absolute,policy_id=absolute.policy_id+'/'+factor_policy.policy_id,personalization_digest=binding,
        maximum=bounded,max_force_N=absolute.max_force_N*a,max_stroke_mm=absolute.max_stroke_mm*a)
    if not bounded.within(m):raise ControlError('personalization exceeds hard bounds')
    status='SIMULATION_PLAN_ONLY'
    if bounded.passes<1 or bounded.contact_s<=0 or bounded.cleanser_ml<=0:
        status='BLOCKED_NO_FEASIBLE_CLEANSING_RECIPE'
    return {**base,'status':status,'envelope':output if status=='SIMULATION_PLAN_ONLY' else None,
        'execution_mode':'QUALIFIED_CONTEXT_FALLBACK' if fallback else 'BOUNDED_REGIONAL_PROPOSAL',
        'personalization_confirmed':not fallback and profile.consistency in ('AGREEMENT','MINOR_VARIATION'),
        'factors':chosen,'absolute_source_digest':absolute.source_digest,'factor_source_digest':factor_policy.source_digest,
        'limits':asdict(output),'rinse_required':True,'recovery_required':True,
        'recipe_target_values':'UNQUALIFIED_NO_COMMANDS_GENERATED'}
