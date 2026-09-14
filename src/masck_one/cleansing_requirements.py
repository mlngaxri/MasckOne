"""Algorithm-to-hardware requirements. No device driver, CAD or sensor selection."""
from dataclasses import dataclass
from .regional_cleansing import Burden, ControlError, finite
from .cleansing_evidence import digest_ok


@dataclass(frozen=True)
class ChannelFootprint:
    channel_id: str
    source_digest: str
    # Exact continuous affected cells, including motion between dwell positions.
    regions: tuple[tuple[str,str,frozenset[str]],...]
    evidence_class: str='DIGITAL_SIMULATION'

    def validate(self,expected):
        if not self.channel_id or not digest_ok(self.source_digest) or self.evidence_class!='DIGITAL_SIMULATION':
            raise ControlError('unbound channel footprint')
        if not self.regions or len({r for r,_,_ in self.regions})!=len(self.regions):raise ControlError('unknown/duplicate footprint')
        for r,domain,cells in self.regions:
            if (r not in expected or domain!=expected[r].domain_id or not cells or
                not cells<=expected[r].cells or expected[r].classification!='REQUIRED'):
                raise ControlError('footprint includes unknown, protected, excluded or misbound cells')


def authorize_footprint(session,footprint,increments,*,force_upper_N,stroke_upper_mm,now_s):
    """Every affected region authorizes its own increment. No average or spare borrowing."""
    footprint.validate(session.expected)
    ids={r for r,_,_ in footprint.regions}
    if set(increments)!=ids or set(force_upper_N)!=ids or set(stroke_upper_mm)!=ids:
        raise ControlError('incomplete per-region action bounds')
    if session.water_limit is None or session.cleanser_limit is None:return False
    for r,_,cells in footprint.regions:
        if not session.ledgers[r].permits(increments[r],force_upper_N=force_upper_N[r],
            stroke_upper_mm=stroke_upper_mm[r],now_s=now_s,cells=cells):return False
    # Conservative sum of delivered regional upper bounds; no assumed allocation efficiency.
    water=sum(l.session.water_ml for l in session.ledgers.values())+sum(b.water_ml for b in increments.values())
    cleanser=sum(l.session.cleanser_ml for l in session.ledgers.values())+sum(b.cleanser_ml for b in increments.values())
    rinse_reserve=sum(max(0,l.envelope.min_rinse_ml-l.rinse_ml) for l in session.ledgers.values()
                      if l.envelope and l.region.classification=='REQUIRED' and l.state not in ('RINSED','RECOVERED','COMPLETE'))
    return water+rinse_reserve<=session.water_limit and cleanser<=session.cleanser_limit


def ingest_footprint(session,footprint,ticks):
    """Observe all effects of a shared action, including any overrun. Not an actuator API."""
    footprint.validate(session.expected)
    if set(ticks)!={r for r,_,_ in footprint.regions}:raise ControlError('shared telemetry omitted a region')
    for r,_,cells in footprint.regions:
        t=ticks[r];l=session.ledgers[r]
        if t.cells!=cells:raise ControlError('shared telemetry footprint mismatch')
        if t.sequence!=l.sequence+1 or t.at_s<=l.at_s:
            for row in session.ledgers.values():row.block('SHARED_TELEMETRY_INVALID')
            raise ControlError('shared telemetry replay/gap')
    for r,_,_ in footprint.regions:session.ingest(r,ticks[r])
    if any(session.ledgers[r].faults for r,_,_ in footprint.regions):
        for r,_,_ in footprint.regions:session.ledgers[r].block('SHARED_ACTION_FAULT')
        return False
    return True


def control_partition(profiles,regions):
    """Minimum distinct demand classes for this snapshot, not a motor count.

    Sharing one lower common ceiling is permitted, but cannot prove completion
    of the higher-demand region. Completion evidence stays cell-specific.
    """
    if set(profiles)!=set(regions):raise ControlError('profile/domain inventory mismatch')
    groups={}
    for r,p in profiles.items():
        if p.region!=r:raise ControlError('misbound profile')
        if regions[r].classification!='REQUIRED':continue
        key=tuple(p.relative_request.get(k) for k in ('cleanser','mechanical','contact_time','passes'))+(p.decision=='BLOCKED_REVIEW',)
        groups.setdefault(key,[]).append(r)
    return {'independent_demand_classes':len(groups),'groups':[{'request':list(k),'regions':sorted(v)} for k,v in sorted(groups.items())],
        'physical_actuator_count':None,'coverage_granularity':'ALL_REQUIRED_CELLS',
        'sharing_rule':'Intersection of all affected ceilings; completed/exhausted cells must be unloadable or bypassable.',
        'multiplexing_rule':'Reposition only with contact/flow disabled or authorize every continuously swept cell.',
        'four_channel_sufficiency':'Requires source-bound footprints and stage-specific coverage evidence; never inferred from a zone count.'}


def hardware_contract():
    return {
        'id':'LANE1_CLEANSING_CAPABILITIES_2','authority_class':'NONAUTHORITATIVE_IMPLEMENTATION_REQUIREMENTS',
        'independent_controls':[
            'Chemical delivery/exposure can stop without forcing extra mechanical action.',
            'Mechanical contact/action can stop on every completed or exhausted cell.',
            'Rinse and recovery remain distinct observable stages after cleaning stops.',
            'Instantaneous force/stroke and cumulative budgets have an independent physical limit path.'],
        'allowed_sharing':[
            'Common pumps, supplies or motors with evidenced isolation, multiplexing and complete footprint accounting.',
            'Regions with different profiles may share their componentwise stricter ceiling.',
            'One moving applicator may visit multiple cells if its complete path is accounted for.'],
        'minimum_granularity':'Independent authorization of every affected region; cell-specific stage evidence. Not one motor per region.',
        'placement':['Registered domain/cell identity','Supported placement state for every affected cell','Unknown/outlier blocks that required region'],
        'observations':['Pre-wet oil and dryness proxies only after separate calibration and confounder characterization',
            'Measured value, units, uncertainty bound, sensor/calibration identities, conditions, timestamp, expiry, quality'],
        'execution_telemetry':['Observed contact interval','Force upper bound','Absolute tangential path',
            'Stroke upper bound','Delivered cleanser/water upper bounds','Pass transitions','Complete affected cells'],
        'completion_evidence':['Stage-specific observed outcome for every required cell',
            'Rinse quantity alone is insufficient','Recovery command alone is insufficient',
            'Region, domain, stage, sequence and telemetry-chain binding'],
        'fail_closed':['Unknown limits or placement','Missing/late observation bounds','Unknown affected cells',
            'Any exhausted affected budget','Invalid required region','Unqualified rinse/recovery evidence'],
        'fault_cleanup':'Independent qualified fault/cleanup and emergency release remain hardware-owner requirements; this module never bypasses a latched fault.',
        'not_required':['Skin-type classifier','Disease inference','Facial imagery','Ethnicity','ML','Cloud','Beauty score',
            'A dedicated actuator or oil sensor for every coverage cell'],
        'future_boundary':{'accepted_context':'Versioned raw answers/observations and bounded recent history only',
            'not_control_authority':['Community suggestions','ML product advice','Saved preferences','Log/calendar entries'],
            'upstream_owners_unchanged':['Routine OS','Product identity','Prepared-session validity','Product preservation']},
        'unresolved':['Physical sensor observability','Qualified calibration/answer mapping',
            'Absolute operating limits and relative factor table','Cleansing outcome evidence',
            'Registered whole-face footprint and minimum installed channel count'],
        'human_use_eligible':False}


def export_contract(output_dir):
    """Deterministic UI/firmware handoff with exact code and authority identities."""
    import json
    import subprocess
    from pathlib import Path
    from hashlib import sha256
    from dataclasses import fields
    from .cleansing_onboarding import form_contract
    from .cleansing_evidence import QuantitativeObservation, Calibration
    from .regional_cleansing import StageEvidence, RecentHistory, Tick, Envelope, VERSION
    from .cleansing_prescription import FactorPolicy
    root=Path(__file__).resolve().parents[2]
    def git(*args):return subprocess.check_output(['git',*args],cwd=root,text=True).strip()
    paths=[f'src/masck_one/{n}.py' for n in ('regional_cleansing','cleansing_onboarding','cleansing_evidence',
           'cleansing_prescription','cleansing_requirements')]+[
        'config/masck_one_authority.yaml','schemas/masck_one_authority.schema.json',
        'config/masck_brand_authority.yaml','docs/contracts/core_sketch_p0_convergence_v1.json',
        'docs/REGIONAL_CLEANSING_CONTROLLER.md']
    sources={p:{'sha256':sha256((root/p).read_bytes()).hexdigest(),'git_blob':git('hash-object',p)} for p in paths}
    data={'id':'LANE1_CLEANSING_INTELLIGENCE_2','version':VERSION,'source_head':git('rev-parse','HEAD'),
        'source_worktree_clean':not bool(git('status','--porcelain','--',*paths)),
        'sources':sources,'authority_is_read_only':True,'onboarding':form_contract(),
        'hardware':hardware_contract(),'human_use_eligible':False,'whole_routine_complete':False,
        'contract_fields':{cls.__name__:[f.name for f in fields(cls)] for cls in (
            QuantitativeObservation,Calibration,StageEvidence,RecentHistory,Tick,Envelope,FactorPolicy)},
        'qualified_human_limits':None,'accepted_physical_calibrations':[],
        'evidence_classes':{'implementation':'DIGITAL_SOFTWARE','outcomes':'DIGITAL_SIMULATION',
            'clinical_or_cosmetic_validation':False},
        'selected_path':['interpret_form','estimate','resolve','plan','authorize_footprint',
                         'ingest_footprint','record_stage','rinsed','recovered','complete'],
        'supersedes':'PR154 exact categorical equality and combined rinse/recovery completion entry',
        'reused_unchanged':'PR154 off-face geometry; no hardware is generated by this export.'}
    target=Path(output_dir);target.mkdir(parents=True,exist_ok=True)
    path=target/'cleansing_intelligence.json'
    path.write_text(json.dumps(data,sort_keys=True,indent=2,allow_nan=False)+'\n')
    return path


if __name__=='__main__':
    import sys
    if len(sys.argv)!=2:raise SystemExit('Usage: python -m masck_one.cleansing_requirements OUTPUT_DIRECTORY')
    print(export_contract(sys.argv[1]))
