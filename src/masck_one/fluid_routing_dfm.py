from __future__ import annotations

"""Fail-closed Cell 5 manufacturability audit for released fluid routing.

No fresh tubing, channel, connector, manifold body, or new mixed-waste geometry is
created here. The audit reconciles released topology with released mixed-waste
centerlines and records the digital DFM closure still required for MVP freeze.
"""

from dataclasses import dataclass
from hashlib import sha1, sha256
import json
import math
from pathlib import Path
import re

from .authority import Authority, load_authority
from .boundary_release import build_verified_interface_boundary_topology
from .cleanser_storage import CleanserStorageArchitecture, build_cleanser_storage_architecture
from .distribution_geometry import DistributionGeometryArchitecture, build_distribution_geometry_architecture
from .distribution_manifold import DistributionManifoldArchitecture, build_distribution_manifold_architecture
from .fluid_routing_checks import QUANTITATIVE_CLOSURE_STATUS, FluidRoutingClosureArchitecture, build_fluid_routing_closure_architecture
from .fresh_pump_packaging import FreshPumpPackagingArchitecture, build_fresh_pump_packaging_architecture
from .interface_attachment import build_interface_attachment_architecture
from .model import MasckOneModel, build_model
from .realized_waste_backbone import RealizedWasteBackbone
from .realized_waste_backbone_release import Cell4WasteBackboneRelease, build_current_cell4_waste_backbone_release
from .structural_frame import StructuralFrameTopology, build_structural_frame_topology
from .water_reservoir import WaterReservoirArchitecture, build_water_reservoir_architecture
from .waste_acquisition import WasteAcquisitionArchitecture, build_waste_acquisition_architecture
from .waste_cartridge import WasteCartridgeArchitecture, build_waste_cartridge_architecture
from .waste_pump_packaging import WastePumpPackagingArchitecture, build_waste_pump_packaging_architecture

SCHEMA = "MASCK_ONE_CELL5_FLUID_ROUTING_DFM_AUDIT_V1"
SOURCE_MAIN_SHA = "21cf8c4fb8ca0d20ddb58f90bcee6275bc98ca30"
AUTHORITY_REVISION = "2026-08-30-R1"
AUTHORITY_BLOB_SHA = "2608dda483b995539de422290371c219668a1527"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
EVIDENCE_STATUS = (
    "DIGITAL_FLUID_ROUTING_DFM_MATURITY_ONLY_NOT_FLOW_PRESSURE_METERING_PRIMING_"
    "LEAKAGE_RECOVERY_HYGIENE_DRYING_WET_SERVICE_DURABILITY_OR_PHYSICAL_VALIDATION"
)

SOURCE_GIT_BLOB_IDENTITIES = (
    ("config/masck_one_authority.yaml", "2608dda483b995539de422290371c219668a1527"),
    ("src/masck_one/model.py", "9e7fa6c71ac28cc45ebb502444bf6c0ea49f7894"),
    ("src/masck_one/structural_frame.py", "bda5ba87d232c0e6a22e200975a80414a10c9a83"),
    ("src/masck_one/water_reservoir.py", "6c14a37d07855550f0bd502e8308ed46682bc19c"),
    ("src/masck_one/cleanser_storage.py", "5e087ca8b05da8352ad4800b2ef8280ea8ddcf29"),
    ("src/masck_one/fresh_pump_packaging.py", "40cb6fb4c3efbfcf25ed0b7d7a75a4269d90a1b4"),
    ("src/masck_one/distribution_manifold.py", "8f2a6c784b51734aba4d1f3809015707fc328405"),
    ("src/masck_one/distribution_geometry.py", "d2dd8b47bb6a2aa1edf57ac0632778228add7997"),
    ("src/masck_one/fluid_routing_checks.py", "3253a9ac45c7a5d6b54923dabe6c04d48ba99433"),
    ("src/masck_one/waste_acquisition.py", "7108fcfbe2baeaa9a343199a6817122ac2aea7ab"),
    ("src/masck_one/waste_pump_architecture.py", "ace02ee529070465b11832f475771125636312cb"),
    ("src/masck_one/waste_pump_packaging.py", "43587520a8c6cdc9ca8cfe362d2aac9589364fdc"),
    ("src/masck_one/waste_cartridge.py", "9dc0fe8a0ed92083c68406da3993e57e767e2483"),
    ("src/masck_one/realized_waste_backbone.py", "6aa79d9a613e278f32da85b4654c0e35cc09b7ca"),
    ("src/masck_one/realized_waste_backbone_release.py", "86f2b12d8721ce0fb233d7b026aed3154de9c964"),
)

REQ_FRESH_ROUTE_GEOMETRY = "FRESH_ROUTE_CENTERLINES_AND_CROSS_SECTIONS"
REQ_MANIFOLD_BODY_TOOLING = "MANIFOLD_BODY_BRANCH_AND_TOOL_ACCESS"
REQ_CONNECTOR_REACH = "CONNECTOR_MATING_REACH_AND_TOOL_ACCESS"
REQ_BEND_RETENTION = "BEND_STRAIN_RELIEF_AND_ROUTE_RETENTION"
REQ_DEAD_LEG_DRAIN = "DEAD_LEG_DRAIN_AND_PURGE_GEOMETRY"
REQ_ASSEMBLY_SERVICE = "ROUTE_ASSEMBLY_AND_SERVICE_SEQUENCE"
REQ_TOLERANCE_SEPARATION = "ROUTE_TOLERANCE_AND_SEPARATION"
REQUIREMENT_IDS = (
    REQ_FRESH_ROUTE_GEOMETRY,
    REQ_MANIFOLD_BODY_TOOLING,
    REQ_CONNECTOR_REACH,
    REQ_BEND_RETENTION,
    REQ_DEAD_LEG_DRAIN,
    REQ_ASSEMBLY_SERVICE,
    REQ_TOLERANCE_SEPARATION,
)

_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_SHA64 = re.compile(r"^[0-9a-f]{64}$")
_REPO_ROOT = Path(__file__).resolve().parents[2]


class FluidRoutingDfmError(ValueError):
    pass


def _text(value: object, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise FluidRoutingDfmError(f"{label} must be exact nonblank text")
    return value


def _bool(value: object, label: str) -> bool:
    if type(value) is not bool:
        raise FluidRoutingDfmError(f"{label} must be an exact bool")
    return value


def _count(value: object, label: str, allow_zero: bool = False) -> int:
    if type(value) is not int:
        raise FluidRoutingDfmError(f"{label} must be an exact integer")
    if (allow_zero and value < 0) or (not allow_zero and value <= 0):
        raise FluidRoutingDfmError(f"{label} is outside its allowed range")
    return value


def _finite(value: object, label: str, positive: bool = False) -> float:
    if type(value) not in (int, float):
        raise FluidRoutingDfmError(f"{label} must be an exact finite numeric scalar")
    try:
        result = float(value)
    except (OverflowError, ValueError) as exc:
        raise FluidRoutingDfmError(f"{label} must be representable as a finite float") from exc
    if not math.isfinite(result) or (positive and result <= 0.0):
        raise FluidRoutingDfmError(f"{label} must be finite" + (" and positive" if positive else ""))
    return result


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def _require_sources_current() -> None:
    for relative_path, expected in SOURCE_GIT_BLOB_IDENTITIES:
        path = _REPO_ROOT / relative_path
        if not path.is_file():
            raise FluidRoutingDfmError(f"fluid-routing DFM source missing: {relative_path}")
        actual = _git_blob_sha(path)
        if actual != expected:
            raise FluidRoutingDfmError(
                f"fluid-routing DFM source moved at {relative_path}; expected {expected}, got {actual}"
            )


def _require_authority(authority: Authority) -> None:
    if type(authority) is not Authority:
        raise FluidRoutingDfmError("audit requires exact Authority type")
    canonical = load_authority()
    if authority.data != canonical.data:
        raise FluidRoutingDfmError("supplied authority differs from released machine authority")
    if str(authority.get("project", "authority_revision")) != AUTHORITY_REVISION:
        raise FluidRoutingDfmError("authority revision moved")


@dataclass(frozen=True, slots=True)
class CurrentFluidRoutingSources:
    model: MasckOneModel
    water: WaterReservoirArchitecture
    cleanser: CleanserStorageArchitecture
    frame: StructuralFrameTopology
    fresh_pump: FreshPumpPackagingArchitecture
    manifold: DistributionManifoldArchitecture
    distribution: DistributionGeometryArchitecture
    acquisition: WasteAcquisitionArchitecture
    waste_pump: WastePumpPackagingArchitecture
    cartridge: WasteCartridgeArchitecture
    closure: FluidRoutingClosureArchitecture
    waste_release: Cell4WasteBackboneRelease

    def validate(self) -> None:
        exact = (
            (self.model, MasckOneModel, "model"),
            (self.water, WaterReservoirArchitecture, "water"),
            (self.cleanser, CleanserStorageArchitecture, "cleanser"),
            (self.frame, StructuralFrameTopology, "frame"),
            (self.fresh_pump, FreshPumpPackagingArchitecture, "fresh pump"),
            (self.manifold, DistributionManifoldArchitecture, "manifold"),
            (self.distribution, DistributionGeometryArchitecture, "distribution"),
            (self.acquisition, WasteAcquisitionArchitecture, "waste acquisition"),
            (self.waste_pump, WastePumpPackagingArchitecture, "waste pump"),
            (self.cartridge, WasteCartridgeArchitecture, "cartridge"),
            (self.closure, FluidRoutingClosureArchitecture, "routing closure"),
            (self.waste_release, Cell4WasteBackboneRelease, "waste release"),
        )
        for value, expected, label in exact:
            if type(value) is not expected:
                raise FluidRoutingDfmError(f"{label} must use its exact released type")
        _require_authority(self.model.authority)
        self.closure.validate_current_sources(
            authority=self.model.authority,
            water=self.water,
            cleanser=self.cleanser,
            fresh_pump=self.fresh_pump,
            manifold=self.manifold,
            distribution=self.distribution,
            coverage=self.model.coverage_mesh,
            protected=self.model.protected_volumes,
            acquisition=self.acquisition,
            waste_pump=self.waste_pump,
            cartridge=self.cartridge,
            frame=self.frame,
        )
        self.waste_release.validate_invariants()
        realized = tuple(
            (r.route_id, r.stage, r.source_interface_id, r.target_interface_id)
            for r in self.waste_release.realization.routes
        )
        topology = tuple(
            (r.route_id, r.stage, r.source_interface_id, r.target_interface_id)
            for r in self.waste_pump.routes
        )
        if realized != topology:
            raise FluidRoutingDfmError("released waste centerlines no longer bind current waste topology")


def build_current_fluid_routing_sources(model: MasckOneModel | None = None) -> CurrentFluidRoutingSources:
    _require_sources_current()
    model = model or build_model()
    _require_authority(model.authority)
    boundaries = build_verified_interface_boundary_topology(
        model.authority, model.facial_surface, model.coverage_mesh, model.compliant_interface_topology
    )
    attachment = build_interface_attachment_architecture(model.authority, boundaries)
    frame = build_structural_frame_topology(model.authority, attachment)
    water = build_water_reservoir_architecture(model.authority)
    cleanser = build_cleanser_storage_architecture(model.authority)
    fresh_pump = build_fresh_pump_packaging_architecture(model.authority, water, cleanser, frame)
    manifold = build_distribution_manifold_architecture(model.authority, fresh_pump, water, cleanser, frame)
    distribution = build_distribution_geometry_architecture(
        model.authority, manifold, fresh_pump, water, cleanser, frame, model.coverage_mesh, model.protected_volumes
    )
    acquisition = build_waste_acquisition_architecture(model.authority, distribution)
    waste_pump = build_waste_pump_packaging_architecture(model.authority, acquisition, distribution, frame)
    cartridge = build_waste_cartridge_architecture(
        model.authority, waste_pump, acquisition, distribution, frame
    )
    closure = build_fluid_routing_closure_architecture(
        model.authority, water, cleanser, fresh_pump, manifold, distribution,
        model.coverage_mesh, model.protected_volumes, acquisition, waste_pump, cartridge, frame
    )
    sources = CurrentFluidRoutingSources(
        model, water, cleanser, frame, fresh_pump, manifold, distribution, acquisition,
        waste_pump, cartridge, closure, build_current_cell4_waste_backbone_release()
    )
    sources.validate()
    return sources


@dataclass(frozen=True, slots=True)
class FluidRoutingDfmRequirement:
    requirement_id: str
    severity: str
    owner: str
    current_state: str
    closure_required: str
    evidence_status: str = "DIGITAL_DFM_REQUIREMENT_ONLY"

    def validate(self) -> None:
        if self.requirement_id not in REQUIREMENT_IDS:
            raise FluidRoutingDfmError("uncontrolled fluid-routing DFM requirement")
        if self.severity != "P0":
            raise FluidRoutingDfmError("fluid-routing digital freeze blockers must remain P0")
        if self.owner != "CELL4_WET_SYSTEMS":
            raise FluidRoutingDfmError("fluid-routing producer ownership must remain Cell 4")
        _text(self.current_state, "current state")
        _text(self.closure_required, "closure required")
        if self.evidence_status != "DIGITAL_DFM_REQUIREMENT_ONLY":
            raise FluidRoutingDfmError("DFM requirement cannot imply physical validation")

    def manifest(self) -> dict[str, object]:
        self.validate()
        return {
            "requirement_id": self.requirement_id,
            "severity": self.severity,
            "owner": self.owner,
            "current_state": self.current_state,
            "closure_required": self.closure_required,
            "evidence_status": self.evidence_status,
        }


@dataclass(frozen=True, slots=True)
class FluidRoutingDfmAudit:
    schema: str
    source_main_sha: str
    authority_revision: str
    authority_blob_sha: str
    coordinate_frame_id: str
    source_routing_closure_sha256: str
    source_waste_realization_sha256: str
    fresh_route_count: int
    realized_fresh_route_count: int
    manifold_branch_count: int
    realized_manifold_branch_count: int
    distribution_groove_count: int
    dimensioned_distribution_groove_count: int
    selected_connector_standard_count: int
    realized_waste_route_count: int
    realized_waste_min_bend_radius_mm: float
    selected_waste_min_bend_requirement_mm: None
    released_waste_geometric_dead_volume_mL: float
    routing_quantitative_closure_status: str
    mold_draft_nominal_deg: float
    rib_thickness_ratio_range: tuple[float, float]
    requirements: tuple[FluidRoutingDfmRequirement, ...]
    digital_mvp_fluid_routing_dfm_ready: bool
    production_moldability_eligible: bool
    physical_validation_eligible: bool
    evidence_status: str

    def validate(self) -> None:
        if self.schema != SCHEMA:
            raise FluidRoutingDfmError("unexpected fluid-routing DFM schema")
        if self.source_main_sha != SOURCE_MAIN_SHA or _SHA40.fullmatch(self.source_main_sha) is None:
            raise FluidRoutingDfmError("audit is stale for released main")
        if self.authority_revision != AUTHORITY_REVISION:
            raise FluidRoutingDfmError("audit authority revision is stale")
        if self.authority_blob_sha != AUTHORITY_BLOB_SHA or _SHA40.fullmatch(self.authority_blob_sha) is None:
            raise FluidRoutingDfmError("audit authority blob is stale")
        if self.coordinate_frame_id != WORLD_FRAME_ID:
            raise FluidRoutingDfmError("audit must use authority world frame")
        for label, value in (
            ("routing closure identity", self.source_routing_closure_sha256),
            ("waste realization identity", self.source_waste_realization_sha256),
        ):
            if type(value) is not str or _SHA64.fullmatch(value) is None:
                raise FluidRoutingDfmError(f"{label} must be canonical SHA-256")
        fresh = _count(self.fresh_route_count, "fresh route count")
        fresh_real = _count(self.realized_fresh_route_count, "realized fresh route count", True)
        branches = _count(self.manifold_branch_count, "manifold branch count")
        branches_real = _count(self.realized_manifold_branch_count, "realized manifold branch count", True)
        grooves = _count(self.distribution_groove_count, "distribution groove count")
        grooves_real = _count(self.dimensioned_distribution_groove_count, "dimensioned groove count", True)
        connectors = _count(self.selected_connector_standard_count, "connector count", True)
        waste = _count(self.realized_waste_route_count, "realized waste route count")
        bend = _finite(self.realized_waste_min_bend_radius_mm, "realized waste minimum bend", True)
        dead = _finite(self.released_waste_geometric_dead_volume_mL, "waste geometric dead volume", True)
        if fresh_real > fresh or branches_real > branches or grooves_real > grooves:
            raise FluidRoutingDfmError("realization counts cannot exceed released topology")
        if self.selected_waste_min_bend_requirement_mm is not None:
            raise FluidRoutingDfmError("audit cannot invent selected waste minimum bend")
        if self.routing_quantitative_closure_status != QUANTITATIVE_CLOSURE_STATUS:
            raise FluidRoutingDfmError("routing quantitative closure state changed")
        draft = _finite(self.mold_draft_nominal_deg, "mold draft", True)
        if type(self.rib_thickness_ratio_range) is not tuple or len(self.rib_thickness_ratio_range) != 2:
            raise FluidRoutingDfmError("rib ratio range must be exact two-tuple")
        rib0 = _finite(self.rib_thickness_ratio_range[0], "rib minimum", True)
        rib1 = _finite(self.rib_thickness_ratio_range[1], "rib maximum", True)
        if rib0 > rib1:
            raise FluidRoutingDfmError("rib ratio range is reversed")
        if type(self.requirements) is not tuple:
            raise FluidRoutingDfmError("requirements must be immutable")
        if tuple(r.requirement_id for r in self.requirements) != REQUIREMENT_IDS:
            raise FluidRoutingDfmError("requirement identity or order changed")
        if len({r.requirement_id for r in self.requirements}) != len(self.requirements):
            raise FluidRoutingDfmError("requirements must be unique")
        for requirement in self.requirements:
            if type(requirement) is not FluidRoutingDfmRequirement:
                raise FluidRoutingDfmError("requirement type changed")
            requirement.validate()
        if _bool(self.digital_mvp_fluid_routing_dfm_ready, "DFM readiness"):
            raise FluidRoutingDfmError("released fluid routing is not digitally DFM-ready")
        if _bool(self.production_moldability_eligible, "moldability eligibility"):
            raise FluidRoutingDfmError("digital audit cannot establish production moldability")
        if _bool(self.physical_validation_eligible, "physical eligibility"):
            raise FluidRoutingDfmError("digital audit cannot become physical validation evidence")
        if self.evidence_status != EVIDENCE_STATUS:
            raise FluidRoutingDfmError("evidence boundary changed")
        object.__setattr__(self, "fresh_route_count", fresh)
        object.__setattr__(self, "realized_fresh_route_count", fresh_real)
        object.__setattr__(self, "manifold_branch_count", branches)
        object.__setattr__(self, "realized_manifold_branch_count", branches_real)
        object.__setattr__(self, "distribution_groove_count", grooves)
        object.__setattr__(self, "dimensioned_distribution_groove_count", grooves_real)
        object.__setattr__(self, "selected_connector_standard_count", connectors)
        object.__setattr__(self, "realized_waste_route_count", waste)
        object.__setattr__(self, "realized_waste_min_bend_radius_mm", bend)
        object.__setattr__(self, "released_waste_geometric_dead_volume_mL", dead)
        object.__setattr__(self, "mold_draft_nominal_deg", draft)
        object.__setattr__(self, "rib_thickness_ratio_range", (rib0, rib1))

    def validate_current_sources(self, sources: CurrentFluidRoutingSources | None = None) -> CurrentFluidRoutingSources:
        self.validate()
        _require_sources_current()
        sources = sources or build_current_fluid_routing_sources()
        if type(sources) is not CurrentFluidRoutingSources:
            raise FluidRoutingDfmError("sources must use exact CurrentFluidRoutingSources type")
        sources.validate()
        fresh_real = sum(
            1 for station in sources.fresh_pump.stations
            if station.tubing_inner_diameter_mm is not None
            or station.minimum_bend_radius_mm is not None
            or station.connector_standard is not None
        )
        branch_real = sum(
            1 for branch in sources.manifold.branches
            if branch.nominal_inner_diameter_mm is not None
            or branch.metering_restriction_geometry_mm is not None
            or branch.centerline_xyz_mm is not None
        )
        groove_real = sum(
            1 for groove in sources.distribution.grooves
            if any(v is not None for v in (groove.width_mm, groove.depth_mm, groove.length_mm))
        )
        connector_count = sum(1 for station in sources.fresh_pump.stations if station.connector_standard is not None)
        routes = sources.waste_release.realization.routes
        bends = tuple(r.realized_min_bend_radius_mm for r in routes if r.realized_min_bend_radius_mm is not None)
        if not bends:
            raise FluidRoutingDfmError("released waste realization lost bend geometry")
        if any(r.minimum_bend_requirement_mm is not None for r in routes):
            raise FluidRoutingDfmError("selected waste bend requirement appeared; fresh DFM review required")
        expected = (
            sources.closure.architecture_sha256,
            sources.waste_release.realization.manifest_sha256,
            len(sources.fresh_pump.routes), fresh_real,
            len(sources.manifold.branches), branch_real,
            len(sources.distribution.grooves), groove_real,
            connector_count, len(routes), min(float(v) for v in bends),
            float(sources.waste_release.realization.total_geometric_dead_volume_mL),
            sources.closure.quantitative_closure_status,
        )
        actual = (
            self.source_routing_closure_sha256, self.source_waste_realization_sha256,
            self.fresh_route_count, self.realized_fresh_route_count,
            self.manifold_branch_count, self.realized_manifold_branch_count,
            self.distribution_groove_count, self.dimensioned_distribution_groove_count,
            self.selected_connector_standard_count, self.realized_waste_route_count,
            self.realized_waste_min_bend_radius_mm, self.released_waste_geometric_dead_volume_mL,
            self.routing_quantitative_closure_status,
        )
        if actual != expected:
            raise FluidRoutingDfmError("audit is stale for current released routing maturity")
        return sources

    @property
    def manifest_sha256(self) -> str:
        return sha256(json.dumps(self.manifest(False), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()

    def manifest(self, include_sha: bool = True) -> dict[str, object]:
        self.validate()
        payload = {
            "schema": self.schema,
            "source_main_sha": self.source_main_sha,
            "authority_revision": self.authority_revision,
            "authority_blob_sha": self.authority_blob_sha,
            "coordinate_frame_id": self.coordinate_frame_id,
            "source_routing_closure_sha256": self.source_routing_closure_sha256,
            "source_waste_realization_sha256": self.source_waste_realization_sha256,
            "released_maturity": {
                "fresh_route_count": self.fresh_route_count,
                "realized_fresh_route_count": self.realized_fresh_route_count,
                "manifold_branch_count": self.manifold_branch_count,
                "realized_manifold_branch_count": self.realized_manifold_branch_count,
                "distribution_groove_count": self.distribution_groove_count,
                "dimensioned_distribution_groove_count": self.dimensioned_distribution_groove_count,
                "selected_connector_standard_count": self.selected_connector_standard_count,
                "realized_waste_route_count": self.realized_waste_route_count,
                "realized_waste_min_bend_radius_mm": self.realized_waste_min_bend_radius_mm,
                "selected_waste_min_bend_requirement_mm": None,
                "released_waste_geometric_dead_volume_mL": self.released_waste_geometric_dead_volume_mL,
                "routing_quantitative_closure_status": self.routing_quantitative_closure_status,
            },
            "manufacturing_rules": {
                "mold_draft_nominal_deg": self.mold_draft_nominal_deg,
                "rib_thickness_ratio_range": list(self.rib_thickness_ratio_range),
                "rule_role": "RELEASED_DESIGN_RULES_NOT_PRODUCTION_PROCESS_CAPABILITY",
            },
            "requirements": [r.manifest() for r in self.requirements],
            "release_blocker_count": len(self.requirements),
            "digital_mvp_fluid_routing_dfm_ready": self.digital_mvp_fluid_routing_dfm_ready,
            "production_moldability_eligible": self.production_moldability_eligible,
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            payload["manifest_sha256"] = self.manifest_sha256
        return payload


def build_fluid_routing_dfm_audit(sources: CurrentFluidRoutingSources | None = None) -> FluidRoutingDfmAudit:
    _require_sources_current()
    sources = sources or build_current_fluid_routing_sources()
    if type(sources) is not CurrentFluidRoutingSources:
        raise FluidRoutingDfmError("sources must use exact CurrentFluidRoutingSources type")
    sources.validate()
    if sources.closure.quantitative_closure_status != QUANTITATIVE_CLOSURE_STATUS:
        raise FluidRoutingDfmError("routing quantitative maturity advanced; new DFM review required")

    fresh_real = sum(
        1 for station in sources.fresh_pump.stations
        if station.tubing_inner_diameter_mm is not None
        or station.minimum_bend_radius_mm is not None
        or station.connector_standard is not None
    )
    branch_real = sum(
        1 for branch in sources.manifold.branches
        if branch.nominal_inner_diameter_mm is not None
        or branch.metering_restriction_geometry_mm is not None
        or branch.centerline_xyz_mm is not None
    )
    groove_real = sum(
        1 for groove in sources.distribution.grooves
        if any(v is not None for v in (groove.width_mm, groove.depth_mm, groove.length_mm))
    )
    connector_count = sum(1 for station in sources.fresh_pump.stations if station.connector_standard is not None)
    waste: RealizedWasteBackbone = sources.waste_release.realization
    bends = tuple(r.realized_min_bend_radius_mm for r in waste.routes if r.realized_min_bend_radius_mm is not None)
    if not bends or any(r.minimum_bend_requirement_mm is not None for r in waste.routes):
        raise FluidRoutingDfmError("released waste bend maturity changed")

    manufacturing = sources.model.authority.get("manufacturing")
    if type(manufacturing) is not dict:
        raise FluidRoutingDfmError("manufacturing authority must be an exact mapping")
    draft = _finite(manufacturing.get("mold_draft_nominal_deg"), "authority mold draft", True)
    rib_raw = manufacturing.get("rib_thickness_ratio_range")
    if type(rib_raw) is not list or len(rib_raw) != 2:
        raise FluidRoutingDfmError("authority rib ratio range must be exact two-item list")
    rib_range = (_finite(rib_raw[0], "rib minimum", True), _finite(rib_raw[1], "rib maximum", True))

    requirements = (
        FluidRoutingDfmRequirement(
            REQ_FRESH_ROUTE_GEOMETRY, "P0", "CELL4_WET_SYSTEMS",
            "All four fresh routes remain interface topology only; no world-coordinate source-to-pump or pump-to-manifold tube/channel centerlines, cross-sections or route retention are released.",
            "Realize source-bound FRESH_WATER and CLEANSER centerlines plus explicit tube/channel cross-section intent through current package/manifold datums. Keep hydraulics validation-gated.",
        ),
        FluidRoutingDfmRequirement(
            REQ_MANIFOLD_BODY_TOOLING, "P0", "CELL4_WET_SYSTEMS",
            "The two manifold branches have no body, cover, branch bores, restrictions or internal centerlines; all 24 distribution grooves remain dimensionless centerline intent.",
            "Realize a deterministic manifold part split and internal branch/outlet network with accessible joining or secondary-operation strategy, then apply authority draft/rib rules or controlled exceptions.",
        ),
        FluidRoutingDfmRequirement(
            REQ_CONNECTOR_REACH, "P0", "CELL4_WET_SYSTEMS",
            "Fresh routes have no connector standard and mixed-waste handoffs have interface identities but no selected connector/fitting mating geometry; active pump candidates provide local reservations only.",
            "For each separable source, pump, manifold, passive-barrier and cartridge handoff, realize connector or integral-junction boundaries, insertion axis, engagement/retention and required hand/tool reach.",
        ),
        FluidRoutingDfmRequirement(
            REQ_BEND_RETENTION, "P0", "CELL4_WET_SYSTEMS",
            "Released mixed-waste centerlines contain 8 mm geometric bends but no selected minimum-bend requirement, bend margin, service margin, strain relief or route retention; fresh routes have no bend geometry.",
            "Bind each route to explicit tubing/channel manufacturing intent, minimum bend requirement and positive clip/retention/strain-relief architecture, then compare complete route geometry without inferring fatigue or kink performance.",
        ),
        FluidRoutingDfmRequirement(
            REQ_DEAD_LEG_DRAIN, "P0", "CELL4_WET_SYSTEMS",
            "Mixed-waste dead volume is geometric seed accounting only; fresh route/manifold dead volume and branch pocket geometry are unresolved and groove intent cannot establish drainability or cleanability.",
            "Publish geometric lumen/cavity accounting, identify intentional blind volumes, and provide connected drain/purge geometry for serviceable wet regions while keeping hygiene/drying/purge effectiveness physical gates.",
        ),
        FluidRoutingDfmRequirement(
            REQ_ASSEMBLY_SERVICE, "P0", "CELL4_WET_SYSTEMS",
            "Route service states are reservation-only; complete tube/manifold installation, connector operation, replacement, clip access and strain-relief trajectories are unresolved.",
            "Prove a non-teleporting assembly/service sequence for manifold, tubes/channels, connectors, clips and wet packages against current whole-product geometry with no circular service dependency.",
        ),
        FluidRoutingDfmRequirement(
            REQ_TOLERANCE_SEPARATION, "P0", "CELL4_WET_SYSTEMS",
            "No released route owns critical connector engagement, clip capture, manifold seam/bore, tube/channel placement or route-to-structure tolerance stacks; service AABBs remain conservative reservations.",
            "Publish critical min-max fit/placement stacks for connector engagement, route retention, manifold joins and route-to-shell/frame separation, distinguishing exact B-rep clearance from reservations.",
        ),
    )
    audit = FluidRoutingDfmAudit(
        SCHEMA, SOURCE_MAIN_SHA, AUTHORITY_REVISION, AUTHORITY_BLOB_SHA, WORLD_FRAME_ID,
        sources.closure.architecture_sha256, waste.manifest_sha256,
        len(sources.fresh_pump.routes), fresh_real,
        len(sources.manifold.branches), branch_real,
        len(sources.distribution.grooves), groove_real,
        connector_count, len(waste.routes), min(float(v) for v in bends), None,
        float(waste.total_geometric_dead_volume_mL), sources.closure.quantitative_closure_status,
        draft, rib_range, requirements, False, False, False, EVIDENCE_STATUS,
    )
    audit.validate_current_sources(sources)
    return audit
