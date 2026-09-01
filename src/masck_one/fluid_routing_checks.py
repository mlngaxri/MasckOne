"""Iteration 28 complete fresh/waste routing closure and quantitative-check ledger.

The controlled digital interface graph can be closed before physical route geometry
exists. Bend radius, dead volume and service clearance remain explicitly blocked.
The waste route preserves the Iteration 26 passive backflow barrier as two distinct
mixed-phase segments rather than collapsing it into a pump-to-cartridge alias.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import re

from .authority import Authority
from .cleanser_storage import CleanserStorageArchitecture
from .coverage import FacialCoverageMesh
from .distribution_geometry import DistributionGeometryArchitecture, DistributionGeometryError
from .distribution_manifold import DistributionManifoldArchitecture, DistributionManifoldError
from .fresh_pump_packaging import FLUID_CLEANSER, FLUID_FRESH_WATER, FreshPumpPackagingArchitecture, FreshPumpPackagingError
from .protected_volumes import ProtectedVolumeSet
from .structural_frame import StructuralFrameTopology
from .water_reservoir import WaterReservoirArchitecture
from .waste_acquisition import PHASE_MIXED_WASTE, WasteAcquisitionArchitecture, WasteAcquisitionError
from .waste_cartridge import WasteCartridgeArchitecture, WasteCartridgeError
from .waste_pump_packaging import WastePumpPackagingArchitecture, WastePumpPackagingError

class FluidRoutingClosureError(ValueError):
    pass

SYSTEM_FRESH = "FRESH"
SYSTEM_WASTE = "WASTE"
SYSTEM_IDS = (SYSTEM_FRESH, SYSTEM_WASTE)
PHASE_IDS = (FLUID_FRESH_WATER, FLUID_CLEANSER, PHASE_MIXED_WASTE)
STAGE_FRESH_SOURCE_TO_PUMP = "FRESH_SOURCE_TO_PUMP"
STAGE_FRESH_PUMP_TO_MANIFOLD = "FRESH_PUMP_TO_MANIFOLD"
STAGE_FRESH_MANIFOLD_BRANCH = "FRESH_MANIFOLD_BRANCH"
STAGE_FRESH_BRANCH_TO_OUTLET = "FRESH_BRANCH_TO_OUTLET"
STAGE_FRESH_OUTLET_TO_GROOVE = "FRESH_OUTLET_TO_GROOVE"
STAGE_WASTE_REGION_TO_PUMP_INLET = "WASTE_REGION_TO_PUMP_INLET"
STAGE_WASTE_ACQUISITION_TO_PUMP = "WASTE_ACQUISITION_TO_PUMP"
STAGE_WASTE_PUMP_TO_BACKFLOW_BARRIER = "WASTE_PUMP_TO_BACKFLOW_BARRIER"
STAGE_WASTE_BACKFLOW_BARRIER_TO_CARTRIDGE = "WASTE_BACKFLOW_BARRIER_TO_CARTRIDGE"
# Historical export retained only so older consumers fail semantically rather than at import.
STAGE_WASTE_PUMP_TO_CARTRIDGE = "WASTE_PUMP_TO_CARTRIDGE_OBSOLETE"
STAGE_WASTE_CARTRIDGE_TO_RETENTION = "WASTE_CARTRIDGE_TO_RETENTION"
STAGE_IDS = (
    STAGE_FRESH_SOURCE_TO_PUMP, STAGE_FRESH_PUMP_TO_MANIFOLD, STAGE_FRESH_MANIFOLD_BRANCH,
    STAGE_FRESH_BRANCH_TO_OUTLET, STAGE_FRESH_OUTLET_TO_GROOVE, STAGE_WASTE_REGION_TO_PUMP_INLET,
    STAGE_WASTE_ACQUISITION_TO_PUMP, STAGE_WASTE_PUMP_TO_BACKFLOW_BARRIER,
    STAGE_WASTE_BACKFLOW_BARRIER_TO_CARTRIDGE, STAGE_WASTE_CARTRIDGE_TO_RETENTION,
)
TOPOLOGY_STATUS = "DIGITAL_INTERFACE_CONTINUITY_CONFIRMED_ONLY_NOT_PHYSICAL_ROUTING_GEOMETRY"
BEND_RADIUS_STATUS = "BLOCKED_PENDING_CONTROLLED_CENTERLINES_TUBING_SELECTION_AND_MINIMUM_BEND_SPECIFICATION"
DEAD_VOLUME_STATUS = "BLOCKED_PENDING_CONTROLLED_CENTERLINE_LENGTH_AND_INTERNAL_CROSS_SECTION_GEOMETRY"
SERVICE_CLEARANCE_STATUS = "BLOCKED_PENDING_COMPLETE_3D_ASSEMBLY_SERVICE_TRAJECTORIES_AND_DEFORMATION_ENVELOPES"
QUANTITATIVE_CLOSURE_STATUS = "NOT_CLOSED_BEND_RADIUS_DEAD_VOLUME_AND_SERVICE_CLEARANCE_REQUIRE_REALIZED_GEOMETRY"
ARCHITECTURE_EVIDENCE_STATUS = "DIGITAL_FLUID_INTERFACE_GRAPH_CLOSURE_ONLY_NOT_BEND_RADIUS_DEAD_VOLUME_SERVICE_CLEARANCE_HYDRAULIC_LEAKAGE_RECOVERY_HYGIENE_OR_PHYSICAL_EVIDENCE"
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")

def _exact(value, expected, *, label):
    if type(value) is not str or value != expected:
        raise FluidRoutingClosureError(f"{label} must use its controlled exact state")

def _text(value, *, label):
    if type(value) is not str or not value or value != value.strip():
        raise FluidRoutingClosureError(f"{label} must be exact built-in nonblank text")
    return value

def _sha(value, *, label):
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
        raise FluidRoutingClosureError(f"{label} must be canonical lowercase SHA-256")
    return value

def _real(value, *, label, nonnegative=False):
    if type(value) not in (int, float):
        raise FluidRoutingClosureError(f"{label} must be an exact finite numeric scalar")
    try: result = float(value)
    except (OverflowError, ValueError) as exc: raise FluidRoutingClosureError(f"{label} must be representable as a finite float") from exc
    if not math.isfinite(result): raise FluidRoutingClosureError(f"{label} must be finite")
    if result == 0.0: result = 0.0
    if nonnegative and result < 0.0: raise FluidRoutingClosureError(f"{label} must be non-negative")
    return result

def _digest(payload):
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()

@dataclass(frozen=True, slots=True)
class RoutingSegmentCheck:
    segment_id: str; system: str; phase_identity: str; stage: str; source_interface_id: str; target_interface_id: str
    centerline_length_mm: float | None; inner_diameter_mm: float | None; minimum_bend_radius_spec_mm: float | None
    realized_minimum_bend_radius_mm: float | None; dead_volume_mL: float | None; service_clearance_mm: float | None
    topology_status: str; bend_radius_status: str; dead_volume_status: str; service_clearance_status: str
    def __post_init__(self): self.validate_invariants()
    def validate_invariants(self):
        _text(self.segment_id, label="routing segment ID")
        if type(self.system) is not str or self.system not in SYSTEM_IDS: raise FluidRoutingClosureError("routing segment system must be exact FRESH or WASTE")
        if type(self.phase_identity) is not str or self.phase_identity not in PHASE_IDS: raise FluidRoutingClosureError("routing segment phase identity is not controlled")
        if self.system == SYSTEM_FRESH and self.phase_identity not in (FLUID_FRESH_WATER, FLUID_CLEANSER): raise FluidRoutingClosureError("fresh routing segment cannot use mixed-waste phase semantics")
        if self.system == SYSTEM_WASTE and self.phase_identity != PHASE_MIXED_WASTE: raise FluidRoutingClosureError("waste routing segment must retain mixed-phase semantics")
        if type(self.stage) is not str or self.stage not in STAGE_IDS: raise FluidRoutingClosureError("routing segment stage is not controlled")
        _text(self.source_interface_id, label="routing segment source interface"); _text(self.target_interface_id, label="routing segment target interface")
        if self.source_interface_id == self.target_interface_id: raise FluidRoutingClosureError("routing segment cannot alias source and target interfaces")
        unresolved=(self.centerline_length_mm,self.inner_diameter_mm,self.minimum_bend_radius_spec_mm,self.realized_minimum_bend_radius_mm,self.dead_volume_mL,self.service_clearance_mm)
        if any(v is not None for v in unresolved): raise FluidRoutingClosureError("Iteration 28 cannot invent route length, diameter, bend radius, dead volume, or service clearance")
        _exact(self.topology_status,TOPOLOGY_STATUS,label="routing topology status"); _exact(self.bend_radius_status,BEND_RADIUS_STATUS,label="bend-radius status"); _exact(self.dead_volume_status,DEAD_VOLUME_STATUS,label="dead-volume status"); _exact(self.service_clearance_status,SERVICE_CLEARANCE_STATUS,label="service-clearance status")
    def manifest(self):
        self.validate_invariants(); return {k:getattr(self,k) for k in self.__dataclass_fields__}

@dataclass(frozen=True, slots=True)
class _SegmentSpec:
    segment_id:str; system:str; phase_identity:str; stage:str; source_interface_id:str; target_interface_id:str

def _expected_segment_specs(*, fresh_pump, manifold, distribution, acquisition, waste_pump, cartridge):
    specs=[]
    fresh_stage={"SOURCE_TO_PUMP":STAGE_FRESH_SOURCE_TO_PUMP,"PUMP_TO_MANIFOLD":STAGE_FRESH_PUMP_TO_MANIFOLD}
    for route in fresh_pump.routes:
        stage=fresh_stage.get(route.stage)
        if stage is None: raise FluidRoutingClosureError("fresh-pump route exposes an uncontrolled stage")
        specs.append(_SegmentSpec(route.route_id,SYSTEM_FRESH,route.fluid_identity,stage,route.source_interface_id,route.target_interface_id))
    outlet_by_id={x.outlet_id:x for x in manifold.outlets}
    if len(outlet_by_id)!=len(manifold.outlets): raise FluidRoutingClosureError("manifold outlet identities cannot repeat")
    route_by_id={x.route_id:x for x in fresh_pump.routes}
    for branch in manifold.branches:
        upstream=route_by_id.get(branch.upstream_route_id)
        if upstream is None: raise FluidRoutingClosureError("manifold branch references a missing fresh-pump route")
        if upstream.target_interface_id!=branch.inlet_interface_id: raise FluidRoutingClosureError("fresh pump-to-manifold handoff is discontinuous")
        if upstream.fluid_identity!=branch.fluid_identity: raise FluidRoutingClosureError("fresh pump-to-manifold handoff crosses fluid identity")
        specs.append(_SegmentSpec(f"I28-{branch.branch_id}-INTERNAL",SYSTEM_FRESH,branch.fluid_identity,STAGE_FRESH_MANIFOLD_BRANCH,branch.inlet_interface_id,branch.branch_id))
        for outlet_id in branch.outlet_ids:
            outlet=outlet_by_id.get(outlet_id)
            if outlet is None: raise FluidRoutingClosureError("manifold branch references a missing outlet")
            if outlet.fluid_identity!=branch.fluid_identity or outlet.branch_id!=branch.branch_id: raise FluidRoutingClosureError("manifold branch-to-outlet handoff crosses branch or fluid identity")
            specs.append(_SegmentSpec(f"I28-{branch.branch_id}-TO-{outlet_id}",SYSTEM_FRESH,branch.fluid_identity,STAGE_FRESH_BRANCH_TO_OUTLET,branch.branch_id,outlet_id))
    groove_by_outlet={x.outlet_id:x for x in distribution.grooves}
    if len(groove_by_outlet)!=len(distribution.grooves): raise FluidRoutingClosureError("distribution groove outlet identities cannot repeat")
    for outlet in manifold.outlets:
        groove=groove_by_outlet.get(outlet.outlet_id)
        if groove is None: raise FluidRoutingClosureError("manifold outlet has no distribution groove handoff")
        specs.append(_SegmentSpec(f"I28-{outlet.outlet_id}-TO-{groove.groove_id}",SYSTEM_FRESH,outlet.fluid_identity,STAGE_FRESH_OUTLET_TO_GROOVE,outlet.outlet_id,groove.groove_id))
    for region in acquisition.regions:
        specs.append(_SegmentSpec(f"I28-WASTE-REGION-{region.region_id}-TO-PUMP-INLET",SYSTEM_WASTE,PHASE_MIXED_WASTE,STAGE_WASTE_REGION_TO_PUMP_INLET,f"WASTE-REGION-{region.region_id}",region.destination))
    if not acquisition.regions: raise FluidRoutingClosureError("waste acquisition exposes no regional routes")
    expected_waste_inlet=acquisition.regions[0].destination
    if any(r.destination!=expected_waste_inlet for r in acquisition.regions): raise FluidRoutingClosureError("waste regional routes do not converge on one controlled pump inlet")
    if waste_pump.routes[0].source_interface_id!=expected_waste_inlet: raise FluidRoutingClosureError("waste acquisition-to-pump handoff is discontinuous")
    waste_stage={
        "ACQUISITION_TO_PUMP":STAGE_WASTE_ACQUISITION_TO_PUMP,
        "PUMP_TO_PASSIVE_BACKFLOW_BARRIER":STAGE_WASTE_PUMP_TO_BACKFLOW_BARRIER,
        "PASSIVE_BACKFLOW_BARRIER_TO_CARTRIDGE_HANDOFF":STAGE_WASTE_BACKFLOW_BARRIER_TO_CARTRIDGE,
    }
    previous_target=None
    for route in waste_pump.routes:
        stage=waste_stage.get(route.stage)
        if stage is None: raise FluidRoutingClosureError("waste-pump route exposes an uncontrolled stage")
        if previous_target is not None and route.source_interface_id!=previous_target: raise FluidRoutingClosureError("waste pump/backflow route chain is discontinuous")
        specs.append(_SegmentSpec(route.route_id,SYSTEM_WASTE,PHASE_MIXED_WASTE,stage,route.source_interface_id,route.target_interface_id))
        previous_target=route.target_interface_id
    if waste_pump.routes[-1].target_interface_id!=cartridge.interfaces.inlet_interface_id: raise FluidRoutingClosureError("waste backflow-barrier-to-cartridge handoff is discontinuous")
    specs.append(_SegmentSpec("I28-WASTE-CARTRIDGE-INLET-TO-RETENTION-REGION",SYSTEM_WASTE,PHASE_MIXED_WASTE,STAGE_WASTE_CARTRIDGE_TO_RETENTION,cartridge.interfaces.inlet_interface_id,cartridge.interfaces.retention_region_id))
    return tuple(specs)

def _checks_from_specs(specs):
    return tuple(RoutingSegmentCheck(s.segment_id,s.system,s.phase_identity,s.stage,s.source_interface_id,s.target_interface_id,None,None,None,None,None,None,TOPOLOGY_STATUS,BEND_RADIUS_STATUS,DEAD_VOLUME_STATUS,SERVICE_CLEARANCE_STATUS) for s in specs)

@dataclass(frozen=True, slots=True)
class FluidRoutingClosureArchitecture:
    source_fresh_pump_sha256:str; source_manifold_sha256:str; source_distribution_sha256:str; source_waste_acquisition_sha256:str; source_waste_pump_sha256:str; source_waste_cartridge_sha256:str; source_structural_frame_sha256:str; source_authority_revision:str
    maximum_initial_prime_mL:float; maximum_initial_prime_status:str; segments:tuple[RoutingSegmentCheck,...]; total_route_dead_volume_mL:float|None; minimum_route_service_clearance_mm:float|None; quantitative_closure_status:str; physical_validation_eligible:bool; evidence_status:str
    def __post_init__(self): self.validate_invariants()
    def validate_invariants(self):
        for label,value in (("source fresh-pump architecture",self.source_fresh_pump_sha256),("source manifold architecture",self.source_manifold_sha256),("source distribution architecture",self.source_distribution_sha256),("source waste-acquisition architecture",self.source_waste_acquisition_sha256),("source waste-pump architecture",self.source_waste_pump_sha256),("source waste-cartridge architecture",self.source_waste_cartridge_sha256),("source structural-frame topology",self.source_structural_frame_sha256)): _sha(value,label=label)
        _text(self.source_authority_revision,label="source authority revision"); prime=_real(self.maximum_initial_prime_mL,label="maximum initial prime",nonnegative=True); _exact(self.maximum_initial_prime_status,"VALIDATION_GATED",label="maximum initial prime status")
        if type(self.segments) is not tuple or not self.segments or any(type(x) is not RoutingSegmentCheck for x in self.segments): raise FluidRoutingClosureError("routing checks must be an immutable nonempty tuple of exact records")
        ids=tuple(x.segment_id for x in self.segments)
        if len(ids)!=len(set(ids)): raise FluidRoutingClosureError("routing segment IDs cannot repeat")
        for x in self.segments: x.validate_invariants()
        if self.total_route_dead_volume_mL is not None: raise FluidRoutingClosureError("total route dead volume cannot close before individual route geometry")
        if self.minimum_route_service_clearance_mm is not None: raise FluidRoutingClosureError("minimum route service clearance cannot close before complete assembly geometry")
        _exact(self.quantitative_closure_status,QUANTITATIVE_CLOSURE_STATUS,label="quantitative routing closure status")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible: raise FluidRoutingClosureError("Iteration 28 digital routing closure is not physical validation evidence")
        _exact(self.evidence_status,ARCHITECTURE_EVIDENCE_STATUS,label="routing closure evidence status"); object.__setattr__(self,"maximum_initial_prime_mL",prime)
    def validate_current_sources(self, *, authority, water, cleanser, fresh_pump, manifold, distribution, coverage, protected, acquisition, waste_pump, cartridge, frame):
        self.validate_invariants()
        expected=((authority,Authority,"authority"),(water,WaterReservoirArchitecture,"water"),(cleanser,CleanserStorageArchitecture,"cleanser"),(fresh_pump,FreshPumpPackagingArchitecture,"fresh pump"),(manifold,DistributionManifoldArchitecture,"manifold"),(distribution,DistributionGeometryArchitecture,"distribution"),(coverage,FacialCoverageMesh,"coverage"),(protected,ProtectedVolumeSet,"protected volumes"),(acquisition,WasteAcquisitionArchitecture,"waste acquisition"),(waste_pump,WastePumpPackagingArchitecture,"waste pump"),(cartridge,WasteCartridgeArchitecture,"waste cartridge"),(frame,StructuralFrameTopology,"structural frame"))
        for value,t,label in expected:
            if type(value) is not t: raise FluidRoutingClosureError(f"{label} must use its exact controlled architecture type")
        try:
            fresh_pump.validate_current_sources(authority=authority,water=water,cleanser=cleanser,frame=frame); manifold.validate_current_sources(authority=authority,pump=fresh_pump,water=water,cleanser=cleanser,frame=frame); distribution.validate_current_sources(authority=authority,manifold=manifold,pump=fresh_pump,water=water,cleanser=cleanser,frame=frame,coverage=coverage,protected=protected)
        except (FreshPumpPackagingError,DistributionManifoldError,DistributionGeometryError) as exc: raise FluidRoutingClosureError("fresh-fluid routing source chain is stale") from exc
        try:
            acquisition.validate_current_sources(authority=authority,distribution=distribution); waste_pump.validate_current_sources(authority=authority,acquisition=acquisition,distribution=distribution,frame=frame); cartridge.validate_current_sources(authority=authority,pump=waste_pump,acquisition=acquisition,distribution=distribution,frame=frame)
        except (WasteAcquisitionError,WastePumpPackagingError,WasteCartridgeError) as exc: raise FluidRoutingClosureError("waste routing source chain is stale") from exc
        expected_hashes=(fresh_pump.architecture_sha256,manifold.architecture_sha256,distribution.architecture_sha256,acquisition.architecture_sha256,waste_pump.architecture_sha256,cartridge.architecture_sha256,frame.topology_sha256)
        actual_hashes=(self.source_fresh_pump_sha256,self.source_manifold_sha256,self.source_distribution_sha256,self.source_waste_acquisition_sha256,self.source_waste_pump_sha256,self.source_waste_cartridge_sha256,self.source_structural_frame_sha256)
        if actual_hashes!=expected_hashes: raise FluidRoutingClosureError("routing closure is stale for current upstream architecture hashes")
        revision=_text(authority.get("project","authority_revision"),label="current authority revision")
        if self.source_authority_revision!=revision: raise FluidRoutingClosureError("routing closure is stale for current authority revision")
        clean=authority.get("fluid","clean_cycle")
        if type(clean) is not dict: raise FluidRoutingClosureError("clean-cycle authority must be an exact mapping")
        expected_prime=_real(clean.get("maximum_initial_prime_mL"),label="authority maximum initial prime",nonnegative=True); _exact(clean.get("status"),"VALIDATION_GATED",label="clean-cycle authority status")
        if self.maximum_initial_prime_mL!=expected_prime: raise FluidRoutingClosureError("maximum initial-prime requirement is stale")
        expected_specs=_expected_segment_specs(fresh_pump=fresh_pump,manifold=manifold,distribution=distribution,acquisition=acquisition,waste_pump=waste_pump,cartridge=cartridge)
        actual_specs=tuple(_SegmentSpec(x.segment_id,x.system,x.phase_identity,x.stage,x.source_interface_id,x.target_interface_id) for x in self.segments)
        if actual_specs!=expected_specs: raise FluidRoutingClosureError("routing segment ledger is stale, incomplete, reordered, crossed, or aliased")
    def manifest(self, *, include_sha=True):
        self.validate_invariants(); payload={"source_fresh_pump_sha256":self.source_fresh_pump_sha256,"source_manifold_sha256":self.source_manifold_sha256,"source_distribution_sha256":self.source_distribution_sha256,"source_waste_acquisition_sha256":self.source_waste_acquisition_sha256,"source_waste_pump_sha256":self.source_waste_pump_sha256,"source_waste_cartridge_sha256":self.source_waste_cartridge_sha256,"source_structural_frame_sha256":self.source_structural_frame_sha256,"source_authority_revision":self.source_authority_revision,"maximum_initial_prime_mL":self.maximum_initial_prime_mL,"maximum_initial_prime_status":self.maximum_initial_prime_status,"segments":[x.manifest() for x in self.segments],"total_route_dead_volume_mL":self.total_route_dead_volume_mL,"minimum_route_service_clearance_mm":self.minimum_route_service_clearance_mm,"quantitative_closure_status":self.quantitative_closure_status,"physical_validation_eligible":self.physical_validation_eligible,"evidence_status":self.evidence_status}
        if include_sha: payload["architecture_sha256"]=self.architecture_sha256
        return payload
    @property
    def architecture_sha256(self): return _digest(self.manifest(include_sha=False))

def build_fluid_routing_closure_architecture(authority,water,cleanser,fresh_pump,manifold,distribution,coverage,protected,acquisition,waste_pump,cartridge,frame):
    clean=authority.get("fluid","clean_cycle")
    if type(clean) is not dict: raise FluidRoutingClosureError("clean-cycle authority must be an exact mapping")
    maximum_prime=_real(clean.get("maximum_initial_prime_mL"),label="authority maximum initial prime",nonnegative=True); _exact(clean.get("status"),"VALIDATION_GATED",label="clean-cycle authority status")
    specs=_expected_segment_specs(fresh_pump=fresh_pump,manifold=manifold,distribution=distribution,acquisition=acquisition,waste_pump=waste_pump,cartridge=cartridge)
    architecture=FluidRoutingClosureArchitecture(fresh_pump.architecture_sha256,manifold.architecture_sha256,distribution.architecture_sha256,acquisition.architecture_sha256,waste_pump.architecture_sha256,cartridge.architecture_sha256,frame.topology_sha256,_text(authority.get("project","authority_revision"),label="authority revision"),maximum_prime,"VALIDATION_GATED",_checks_from_specs(specs),None,None,QUANTITATIVE_CLOSURE_STATUS,False,ARCHITECTURE_EVIDENCE_STATUS)
    architecture.validate_current_sources(authority=authority,water=water,cleanser=cleanser,fresh_pump=fresh_pump,manifold=manifold,distribution=distribution,coverage=coverage,protected=protected,acquisition=acquisition,waste_pump=waste_pump,cartridge=cartridge,frame=frame)
    return architecture
