"""CS-018 finite contact topology proof, not a physical routine controller.

Search proves accessibility and contact-free paths only within the supplied
closed graph. It does not prove deposition, stability under loads or film survival.
Unknown geometry/evidence removes an edge; it never supplies a free motion.
"""
from dataclasses import dataclass
from itertools import combinations
from collections import deque
import math


class TopologyError(ValueError):
    pass


@dataclass(frozen=True)
class Cell:
    id: str
    required_layers: tuple[str, ...]
    protected: bool = False
    registration: str | None = None


@dataclass(frozen=True)
class Participant:
    id: str
    source_identity: str
    classification: str
    reaction_role: bool = False


@dataclass(frozen=True)
class Configuration:
    id: str
    contacts: tuple[tuple[str, tuple[str, ...]], ...]
    blocked_access: tuple[tuple[str, tuple[str, ...]], ...]
    reaction: tuple[str, ...] | None
    reachable: tuple[str, ...] | None
    emergency_independent: bool | None
    detached: bool = False


@dataclass(frozen=True)
class Transition:
    id: str
    start: str
    end: str
    moving: tuple[str, ...]
    swept_contact_cells: tuple[str, ...] | None
    protected_common_mm3: float | None
    reaction_during: tuple[str, ...] | None
    continuous_evidence: str | None
    group: str
    # Dirty contact may leave; a clean applicator cannot cross the dirty path
    # without an explicit separation certificate.
    crosses_dirty: bool = False
    separation_evidence: str | None = None
    normal_release: bool = False
    standoff_evidence: str | None = None


@dataclass(frozen=True)
class Problem:
    cells: tuple[Cell, ...]
    participants: tuple[Participant, ...]
    configurations: tuple[Configuration, ...]
    transitions: tuple[Transition, ...]
    initial: str
    # Each alternative names a complete topological path to an external
    # reaction. Certificates do not assert force capacity or human support.
    support_certificates: tuple[tuple[tuple[str, ...], str], ...]
    scope: str = 'OFF_FACE_DIGITAL_GRAPH'


def _ids(items, label):
    result = {x.id: x for x in items}
    if len(result) != len(items) or any(not i for i in result):
        raise TopologyError('duplicate/empty ' + label)
    return result


def validate(p):
    cells = _ids(p.cells, 'cell'); parts = _ids(p.participants, 'participant')
    states = _ids(p.configurations, 'configuration'); _ids(p.transitions, 'transition')
    if p.initial not in states or not cells: raise TopologyError('missing initial/domain')
    for c in p.cells:
        if c.protected and c.required_layers: raise TopologyError('protected cell is a treatment target')
        if len(set(c.required_layers)) != len(c.required_layers): raise TopologyError('duplicate layer')
    for x in p.participants:
        if not x.source_identity: raise TopologyError('missing source identity')
        if x.reaction_role and x.classification != 'MATERIAL':
            raise TopologyError('reference/unknown cannot carry reaction')
    for s in p.configurations:
        for mapping in (s.contacts, s.blocked_access):
            if len(dict(mapping)) != len(mapping): raise TopologyError('duplicate contact participant')
            for pid, ids in mapping:
                if pid not in parts or not set(ids) <= cells.keys(): raise TopologyError('unknown contact identity')
        if s.reachable is not None and not set(s.reachable) <= cells.keys(): raise TopologyError('unknown reachable cell')
    for ids, evidence in p.support_certificates:
        if not ids or not evidence: raise TopologyError('uncertified support path')
        if any(i not in parts or not parts[i].reaction_role for i in ids):
            raise TopologyError('invalid reaction participant')
    for t in p.transitions:
        if t.start not in states or t.end not in states or not set(t.moving) <= parts.keys():
            raise TopologyError('unknown transition identity')
        if t.swept_contact_cells is not None and not set(t.swept_contact_cells) <= cells.keys():
            raise TopologyError('unknown swept cell')
        v=t.protected_common_mm3
        if v is not None and (isinstance(v,bool) or not math.isfinite(v) or v<0):
            raise TopologyError('invalid protected common')
    return cells, parts, states


def _contact(s):
    return set().union(*(set(c) for _,c in s.contacts)) if s.contacts else set()


def _supported(p, ids):
    return ids is not None and any(set(path) <= set(ids) for path,_ in p.support_certificates)


def state_defects(p, s, finished):
    bad=[]
    if s.emergency_independent is not True: bad.append('EMERGENCY_NOT_INDEPENDENT')
    if not s.detached and not _supported(p,s.reaction): bad.append('SUPPORT_UNPROVED')
    if _contact(s) & {c.id for c in p.cells if c.protected}: bad.append('PROTECTED_CONTACT')
    if _contact(s) & finished: bad.append('CONTACT_AFTER_APPLICATION')
    return bad


def edge_defects(p, t, finished):
    bad=[]
    if not t.continuous_evidence: bad.append('CONTINUOUS_PATH_UNKNOWN')
    if t.swept_contact_cells is None: bad.append('SWEPT_CONTACT_UNKNOWN')
    elif set(t.swept_contact_cells)&finished: bad.append('WIPE_AFTER_APPLICATION')
    if t.protected_common_mm3 is None: bad.append('PROTECTED_PATH_UNKNOWN')
    elif t.protected_common_mm3>1e-7: bad.append('PROTECTED_COLLISION')
    if not _supported(p,t.reaction_during): bad.append('SUPPORT_LOSS_DURING_TRANSFER')
    if t.crosses_dirty and not t.separation_evidence: bad.append('DIRTY_CLEAN_CROSSING')
    if t.normal_release and not t.standoff_evidence: bad.append('NO_PRIOR_STANDOFF')
    return bad


def solve(p, max_nodes=100000):
    """Exact finite search. Minimize independent motion groups, then edge count.

    A painted cell here means access was possible in order, not that any product
    was actually applied. Every physical completion flag remains false.
    """
    import heapq
    _,_,states=validate(p)
    required=tuple(c for c in p.cells if c.required_layers)
    missing=[c.id for c in required if not c.registration]
    common={'physical_complete':False,'human_use_eligible':False,'scope':p.scope,
            'proof':'FINITE_GRAPH_ACCESS_ONLY_NOT_DEPOSITION_OR_LOAD_CAPACITY'}
    if missing:
        return {**common,'status':'BLOCKED_MISSING_REGISTRATION',
                'witness':{'cells':[missing[0]],'kind':'MISSING_SOURCE_EVIDENCE',
                           'minimality':'ONE_REQUIRED_UNREGISTERED_CELL_SUFFICES'},
                'all_missing_cells':missing}
    counts=tuple(0 for _ in required)
    # Heap tie-breaker is deterministic, independent of set iteration/hash seed.
    queue=[(0,0,0,p.initial,counts,frozenset(),())]; serial=0;seen=set();rejects={}; solutions=[]
    while queue:
        groups_n,steps,_,sid,counts,groups,path=heapq.heappop(queue)
        key=(sid,counts,groups)
        if key in seen: continue
        if len(seen)>=max_nodes:
            return {**common,'status':'INCONCLUSIVE_SEARCH_LIMIT','visited':len(seen)}
        seen.add(key);s=states[sid]
        finished={c.id for c,n in zip(required,counts) if n>0}
        bad=state_defects(p,s,finished)
        if bad:
            rejects[sid]=sorted(set(rejects.get(sid,[])+bad));continue
        if all(n==len(c.required_layers) for c,n in zip(required,counts)) and s.detached:
            solutions.append((groups_n,steps,path));break
        if not s.detached and s.reachable is not None:
            occluded=_contact(s)|set().union(*(set(x) for _,x in s.blocked_access)) if s.blocked_access else _contact(s)
            # Global stage barrier: no later product while an earlier layer is
            # still required elsewhere. Application itself cannot create support.
            unfinished=[n for c,n in zip(required,counts) if n<len(c.required_layers)]
            level=min(unfinished) if unfinished else None
            next_counts=list(counts); reached=[]
            for i,(c,n) in enumerate(zip(required,counts)):
                if n==level and n<len(c.required_layers) and c.id in s.reachable and c.id not in occluded:
                    next_counts[i]+=1;reached.append(c.id+':'+c.required_layers[n])
            if reached:
                serial+=1
                heapq.heappush(queue,(groups_n,steps,serial,sid,tuple(next_counts),groups,path+({'access':reached,'at':sid},)))
        for t in sorted(p.transitions,key=lambda x:x.id):
            if t.start!=sid:continue
            bad=edge_defects(p,t,finished)+state_defects(p,states[t.end],finished)
            if bad:
                rejects[t.id]=sorted(set(rejects.get(t.id,[])+bad));continue
            g=groups|{t.group};serial+=1
            heapq.heappush(queue,(len(g),steps+1,serial,t.end,counts,g,path+({'transition':t.id},)))
    if solutions:
        g,n,path=solutions[0]
        return {**common,'status':'ACCESS_SEQUENCE_EXISTS','motion_groups':g,'transitions':n,
                'path':path,'visited':len(seen),'rejected_edges':rejects}
    return {**common,'status':'NO_SEQUENCE_IN_SUPPLIED_GRAPH','visited':len(seen),
            'rejected_edges':rejects,'witness':support_trap_witness(p)}


def support_trap_witness(p):
    """Minimum-cardinality required-cell transversal of all supported states.

    If each usable attached state contacts one of these required cells, no state
    can contain the final layer everywhere. This is a bounded topology theorem,
    not a proof against unmodeled future hardware. Enumeration capped at 20 cells.
    """
    targets={c.id for c in p.cells if c.required_layers}
    states=[s for s in p.configurations if not s.detached and _supported(p,s.reaction)]
    sets=[_contact(s)&targets for s in states]
    if not states or any(not x for x in sets):
        return {'kind':'EDGE_OR_SOURCE_CONSTRAINT','minimality':'NOT_CLAIMED',
                'next_capability':'Supply registered continuous paths, access and support evidence for rejected edges'}
    domain=sorted(set.union(*sets))
    if len(domain)>20:return {'kind':'SUPPORT_CONTACT_TRAP','cells':domain,'minimality':'NOT_COMPUTED'}
    for count in range(1,len(domain)+1):
        for subset in combinations(domain,count):
            if all(set(subset)&x for x in sets):
                owners=sorted({pid for s in states for pid,cs in s.contacts if set(cs)&set(subset)})
                return {'kind':'SUPPORT_CONTACT_TRAP','phase':'FINAL_LAYER_BEFORE_RELEASE',
                        'cells':list(subset),'participants':owners,'minimality':'MINIMUM_CARDINALITY_CELL_TRANSVERSAL',
                        'state_contacts':{s.id:sorted(x) for s,x in zip(states,sets)},
                        'next_capability':'At least one registered supported application state clear of every required final-layer cell'}
    raise AssertionError('finite transversal not found')
