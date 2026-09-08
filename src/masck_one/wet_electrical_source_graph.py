from __future__ import annotations

"""Fail-closed Cell 4 wet/electrical integration source graph.

The graph records released-main integration truth only. Canonical fluid domains are
kept separate from producer-specific fluid/phase identities so FRESH_WATER,
CLEANSER, and MIXED_WASTE cannot alias while exact released route-interface IDs and
the released mixed-waste phase descriptor remain visible as provenance.
"""

from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha1, sha256
import json
from pathlib import Path
import re

from .authority import Authority, load_authority
from .cleanser_storage import PORT_OUTLET as CLEANSER_PORT_OUTLET
from .distribution_manifold import (
    BRANCH_CLEANSER,
    BRANCH_FRESH_WATER,
    INLET_CLEANSER,
    INLET_FRESH_WATER,
)
from .fresh_pump_packaging import (
    FLUID_CLEANSER,
    FLUID_FRESH_WATER,
    INTERFACE_CLEANSER_PUMP_OUTLET,
    INTERFACE_WATER_PUMP_OUTLET,
    ROUTE_CLEANSER_MANIFOLD,
    ROUTE_CLEANSER_SOURCE,
    ROUTE_WATER_MANIFOLD,
    ROUTE_WATER_SOURCE,
    STATION_CLEANSER,
    STATION_WATER,
)
from .model import MasckOneModel, build_model
from .waste_acquisition import PHASE_MIXED_WASTE, ROUTE_DESTINATION
from .waste_pump_architecture import (
    BARRIER_WASTE,
    INTERFACE_BARRIER_OUTLET,
    INTERFACE_CARTRIDGE_INLET_I27,
    INTERFACE_PUMP_OUTLET,
    ROUTE_ACQUISITION_TO_PUMP,
    ROUTE_BARRIER_TO_CARTRIDGE,
    ROUTE_PUMP_TO_BARRIER,
    ROUTE_STAGES as WASTE_ROUTE_STAGES,
    STATION_WASTE,
)
from .water_reservoir import PORT_PICKUP as WATER_PORT_PICKUP


SCHEMA = "MASCK_ONE_CELL4_WET_ELECTRICAL_SOURCE_GRAPH_V2"
SOURCE_MAIN_SHA = "b3be4c2483f45b2b8dfff6f0c3d9810c2b8511dc"
AUTHORITY_REVISION = "2026-08-30-R1"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"

FLUID_DOMAIN_FRESH_WATER = "FRESH_WATER"
FLUID_DOMAIN_CLEANSER = "CLEANSER"
FLUID_DOMAIN_MIXED_WASTE = "MIXED_WASTE"
CANONICAL_FLUID_DOMAINS = (
    FLUID_DOMAIN_FRESH_WATER,
    FLUID_DOMAIN_CLEANSER,
    FLUID_DOMAIN_MIXED_WASTE,
)
RELEASED_FLUID_IDENTITY_BY_DOMAIN = {
    FLUID_DOMAIN_FRESH_WATER: FLUID_FRESH_WATER,
    FLUID_DOMAIN_CLEANSER: FLUID_CLEANSER,
    FLUID_DOMAIN_MIXED_WASTE: PHASE_MIXED_WASTE,
}
MANIFOLD_INLET_BRANCH_BINDING_BY_DOMAIN = {
    FLUID_DOMAIN_FRESH_WATER: (INLET_FRESH_WATER, BRANCH_FRESH_WATER),
    FLUID_DOMAIN_CLEANSER: (INLET_CLEANSER, BRANCH_CLEANSER),
}

EVIDENCE_STATUS = (
    "DIGITAL_WET_ELECTRICAL_INTEGRATION_SOURCE_GRAPH_ONLY_NOT_PACKAGE_SELECTION_"
    "HYDRAULIC_ELECTRICAL_THERMAL_HYGIENE_SERVICE_OR_PHYSICAL_EVIDENCE"
)

SOURCE_GIT_BLOB_IDENTITIES: tuple[tuple[str, str], ...] = (
    ("config/masck_one_authority.yaml", "2608dda483b995539de422290371c219668a1527"),
    ("src/masck_one/model.py", "9e7fa6c71ac28cc45ebb502444bf6c0ea49f7894"),
    ("src/masck_one/export.py", "a834333ec153a1bf28bb6713003291db6af7237d"),
    ("src/masck_one/water_reservoir.py", "6c14a37d07855550f0bd502e8308ed46682bc19c"),
    ("src/masck_one/cleanser_storage.py", "5e087ca8b05da8352ad4800b2ef8280ea8ddcf29"),
    ("src/masck_one/fresh_pump_packaging.py", "40cb6fb4c3efbfcf25ed0b7d7a75a4269d90a1b4"),
    ("src/masck_one/distribution_manifold.py", "8f2a6c784b51734aba4d1f3809015707fc328405"),
    ("src/masck_one/distribution_geometry.py", "d2dd8b47bb6a2aa1edf57ac0632778228add7997"),
    ("src/masck_one/waste_acquisition.py", "7108fcfbe2baeaa9a343199a6817122ac2aea7ab"),
    ("src/masck_one/waste_pump_architecture.py", "ace02ee529070465b11832f475771125636312cb"),
    ("src/masck_one/waste_pump_packaging.py", "43587520a8c6cdc9ca8cfe362d2aac9589364fdc"),
    ("src/masck_one/realized_waste_backbone.py", "6aa79d9a613e278f32da85b4654c0e35cc09b7ca"),
    ("src/masck_one/realized_waste_backbone_release.py", "86f2b12d8721ce0fb233d7b026aed3154de9c964"),
    ("src/masck_one/waste_cartridge.py", "9dc0fe8a0ed92083c68406da3993e57e767e2483"),
    ("src/masck_one/waste_cartridge_dfm.py", "f9788cce30c14600c8a624509153596e46c1e478"),
)

UNRELEASED_REALIZATION_PATHS = (
    "src/masck_one/realized_cleanser_storage.py",
    "src/masck_one/realized_fresh_water_pump.py",
    "src/masck_one/realized_cleanser_pump.py",
    "src/masck_one/realized_waste_pump.py",
    "src/masck_one/realized_passive_backflow.py",
)

PHYSICAL_MATERIAL_NAMES = ("rigid_shell",)
REFERENCE_REVIEW_NAMES = (
    "nasal_lobe_membrane_reference",
    "actuator_envelope_1",
    "actuator_envelope_2",
    "actuator_envelope_3",
    "actuator_envelope_4",
    "water_reservoir_envelope",
    "waste_cartridge_envelope",
    "battery_reference_envelope",
    "visual_eye_left",
    "visual_eye_right",
    "visual_mouth",
    "visual_nostril_left",
    "visual_nostril_right",
)
CURRENT_EXPORT_MANUAL_EXCLUSIONS = ("waste_cartridge_envelope",)

BLOCKER_ASSEMBLY_BOUNDARY = "CELL4-BLOCKER-PHYSICAL-REFERENCE-ASSEMBLY-BOUNDARY"
BLOCKER_FRESH_ROUTE_GEOMETRY = "CELL4-BLOCKER-FRESH-PUMP-ROUTE-GEOMETRY"
BLOCKER_DRY_SIDE = "CELL4-BLOCKER-DRY-SIDE-PACKAGE"
BLOCKER_HARNESS = "CELL4-BLOCKER-HARNESS-BULKHEAD"
BLOCKER_HMI_WARM_THERMAL = "CELL4-BLOCKER-HMI-WARM-THERMAL"
BLOCKER_IDS = (
    BLOCKER_ASSEMBLY_BOUNDARY,
    BLOCKER_FRESH_ROUTE_GEOMETRY,
    BLOCKER_DRY_SIDE,
    BLOCKER_HARNESS,
    BLOCKER_HMI_WARM_THERMAL,
)

WATER_RESERVOIR_NODE = "WATER_RESERVOIR"
CLEANSER_STORAGE_NODE = "CLEANSER_STORAGE"
WASTE_ACQUISITION_NODE = "WASTE_ACQUISITION"
WASTE_CARTRIDGE_NODE = "WASTE_CARTRIDGE"

EXPECTED_ROUTE_GRAPH = (
    (
        ROUTE_WATER_SOURCE,
        FLUID_DOMAIN_FRESH_WATER,
        FLUID_FRESH_WATER,
        WATER_PORT_PICKUP,
        STATION_WATER,
        "SOURCE_TO_PUMP",
    ),
    (
        ROUTE_WATER_MANIFOLD,
        FLUID_DOMAIN_FRESH_WATER,
        FLUID_FRESH_WATER,
        INTERFACE_WATER_PUMP_OUTLET,
        INLET_FRESH_WATER,
        "PUMP_TO_MANIFOLD",
    ),
    (
        ROUTE_CLEANSER_SOURCE,
        FLUID_DOMAIN_CLEANSER,
        FLUID_CLEANSER,
        CLEANSER_PORT_OUTLET,
        STATION_CLEANSER,
        "SOURCE_TO_PUMP",
    ),
    (
        ROUTE_CLEANSER_MANIFOLD,
        FLUID_DOMAIN_CLEANSER,
        FLUID_CLEANSER,
        INTERFACE_CLEANSER_PUMP_OUTLET,
        INLET_CLEANSER,
        "PUMP_TO_MANIFOLD",
    ),
    (
        ROUTE_ACQUISITION_TO_PUMP,
        FLUID_DOMAIN_MIXED_WASTE,
        PHASE_MIXED_WASTE,
        ROUTE_DESTINATION,
        STATION_WASTE,
        WASTE_ROUTE_STAGES[0],
    ),
    (
        ROUTE_PUMP_TO_BARRIER,
        FLUID_DOMAIN_MIXED_WASTE,
        PHASE_MIXED_WASTE,
        INTERFACE_PUMP_OUTLET,
        BARRIER_WASTE,
        WASTE_ROUTE_STAGES[1],
    ),
    (
        ROUTE_BARRIER_TO_CARTRIDGE,
        FLUID_DOMAIN_MIXED_WASTE,
        PHASE_MIXED_WASTE,
        INTERFACE_BARRIER_OUTLET,
        INTERFACE_CARTRIDGE_INLET_I27,
        WASTE_ROUTE_STAGES[2],
    ),
)

_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_REPO_ROOT = Path(__file__).resolve().parents[2]


class WetElectricalSourceGraphError(ValueError):
    pass


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def _require_current_sources() -> None:
    for relative_path, expected in SOURCE_GIT_BLOB_IDENTITIES:
        path = _REPO_ROOT / relative_path
        if not path.is_file():
            raise WetElectricalSourceGraphError(f"wet/electrical source is missing: {relative_path}")
        actual = _git_blob_sha(path)
        if actual != expected:
            raise WetElectricalSourceGraphError(
                f"wet/electrical source moved at {relative_path}; expected {expected}, got {actual}"
            )
    for relative_path in UNRELEASED_REALIZATION_PATHS:
        if (_REPO_ROOT / relative_path).exists():
            raise WetElectricalSourceGraphError(
                f"previously unmerged realization appeared at {relative_path}; reconstruct and rebind source graph"
            )


def _digest(payload: object) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return sha256(raw).hexdigest()


def _validate_fluid_pair(fluid_domain: str | None, fluid_identity: str | None, *, label: str) -> None:
    if fluid_domain is None:
        if fluid_identity is not None:
            raise WetElectricalSourceGraphError(f"{label} cannot carry fluid identity without a canonical domain")
        return
    if type(fluid_domain) is not str or fluid_domain not in CANONICAL_FLUID_DOMAINS:
        raise WetElectricalSourceGraphError(f"{label} fluid domain is not canonical")
    expected = RELEASED_FLUID_IDENTITY_BY_DOMAIN[fluid_domain]
    if type(fluid_identity) is not str or fluid_identity != expected:
        raise WetElectricalSourceGraphError(
            f"{label} fluid identity does not match canonical domain {fluid_domain}"
        )


@dataclass(frozen=True, slots=True)
class SourceNode:
    node_id: str
    owner_lane: str
    release_state: str
    geometry_state: str
    material_role: str
    fluid_domain: str | None = None
    fluid_identity: str | None = None

    def __post_init__(self) -> None:
        for label, value in (
            ("node_id", self.node_id),
            ("owner_lane", self.owner_lane),
            ("release_state", self.release_state),
            ("geometry_state", self.geometry_state),
            ("material_role", self.material_role),
        ):
            if type(value) is not str or not value or value != value.strip():
                raise WetElectricalSourceGraphError(f"{label} must be exact nonblank text")
        _validate_fluid_pair(self.fluid_domain, self.fluid_identity, label=f"node {self.node_id}")

    def manifest(self) -> dict[str, object]:
        self.__post_init__()
        return {
            "node_id": self.node_id,
            "owner_lane": self.owner_lane,
            "release_state": self.release_state,
            "geometry_state": self.geometry_state,
            "material_role": self.material_role,
            "fluid_domain": self.fluid_domain,
            "fluid_identity": self.fluid_identity,
        }


@dataclass(frozen=True, slots=True)
class SourceEdge:
    edge_id: str
    fluid_domain: str
    fluid_identity: str
    source_node_id: str
    target_node_id: str
    stage: str
    geometry_state: str

    def __post_init__(self) -> None:
        for label, value in (
            ("edge_id", self.edge_id),
            ("source_node_id", self.source_node_id),
            ("target_node_id", self.target_node_id),
            ("stage", self.stage),
            ("geometry_state", self.geometry_state),
        ):
            if type(value) is not str or not value or value != value.strip():
                raise WetElectricalSourceGraphError(f"{label} must be exact nonblank text")
        _validate_fluid_pair(self.fluid_domain, self.fluid_identity, label=f"edge {self.edge_id}")

    def manifest(self) -> dict[str, object]:
        self.__post_init__()
        return {
            "edge_id": self.edge_id,
            "fluid_domain": self.fluid_domain,
            "fluid_identity": self.fluid_identity,
            "source_node_id": self.source_node_id,
            "target_node_id": self.target_node_id,
            "stage": self.stage,
            "geometry_state": self.geometry_state,
        }


@dataclass(frozen=True, slots=True)
class WetElectricalSourceGraph:
    schema: str
    source_main_sha: str
    authority_revision: str
    world_frame_id: str
    nodes: tuple[SourceNode, ...]
    edges: tuple[SourceEdge, ...]
    physical_material_names: tuple[str, ...]
    reference_review_names: tuple[str, ...]
    current_export_selected_names: tuple[str, ...]
    illegal_reference_material_names: tuple[str, ...]
    blockers: tuple[str, ...]
    integration_release_ready: bool
    physical_validation_eligible: bool
    evidence_status: str

    def __post_init__(self) -> None:
        if self.schema != SCHEMA:
            raise WetElectricalSourceGraphError("source-graph schema changed")
        if type(self.source_main_sha) is not str or _SHA40.fullmatch(self.source_main_sha) is None:
            raise WetElectricalSourceGraphError("source_main_sha must be canonical lowercase 40-hex")
        if self.source_main_sha != SOURCE_MAIN_SHA:
            raise WetElectricalSourceGraphError("source graph is stale for released main")
        if self.authority_revision != AUTHORITY_REVISION:
            raise WetElectricalSourceGraphError("authority revision moved")
        if self.world_frame_id != WORLD_FRAME_ID:
            raise WetElectricalSourceGraphError("source graph must remain in MASCK_ONE_AUTHORITY_WORLD_MM")
        if type(self.nodes) is not tuple or any(type(node) is not SourceNode for node in self.nodes):
            raise WetElectricalSourceGraphError("nodes must be an immutable tuple of exact SourceNode records")
        if len({node.node_id for node in self.nodes}) != len(self.nodes):
            raise WetElectricalSourceGraphError("source node IDs must be unique")
        if type(self.edges) is not tuple or any(type(edge) is not SourceEdge for edge in self.edges):
            raise WetElectricalSourceGraphError("edges must be an immutable tuple of exact SourceEdge records")
        if len({edge.edge_id for edge in self.edges}) != len(self.edges):
            raise WetElectricalSourceGraphError("source edge IDs must be unique")

        for node in self.nodes:
            node.__post_init__()
        for edge in self.edges:
            edge.__post_init__()

        node_by_id = {node.node_id: node for node in self.nodes}
        if any(edge.source_node_id not in node_by_id or edge.target_node_id not in node_by_id for edge in self.edges):
            raise WetElectricalSourceGraphError("all fluid edges must terminate on controlled source nodes")
        for edge in self.edges:
            source = node_by_id[edge.source_node_id]
            target = node_by_id[edge.target_node_id]
            if (
                source.fluid_domain != edge.fluid_domain
                or source.fluid_identity != edge.fluid_identity
                or target.fluid_domain != edge.fluid_domain
                or target.fluid_identity != edge.fluid_identity
            ):
                raise WetElectricalSourceGraphError(
                    f"fluid route {edge.edge_id} cannot cross or alias canonical fluid domains"
                )

        for domain, (inlet_id, branch_id) in MANIFOLD_INLET_BRANCH_BINDING_BY_DOMAIN.items():
            expected_identity = RELEASED_FLUID_IDENTITY_BY_DOMAIN[domain]
            inlet = node_by_id.get(inlet_id)
            branch = node_by_id.get(branch_id)
            if inlet is None or branch is None:
                raise WetElectricalSourceGraphError(
                    f"manifold inlet/branch binding is incomplete for {domain}"
                )
            if (
                inlet.fluid_domain != domain
                or inlet.fluid_identity != expected_identity
                or branch.fluid_domain != domain
                or branch.fluid_identity != expected_identity
            ):
                raise WetElectricalSourceGraphError(
                    f"manifold inlet cannot cross or alias branch identity for {domain}"
                )

        actual_route_graph = tuple(
            (
                edge.edge_id,
                edge.fluid_domain,
                edge.fluid_identity,
                edge.source_node_id,
                edge.target_node_id,
                edge.stage,
            )
            for edge in self.edges
        )
        if actual_route_graph != EXPECTED_ROUTE_GRAPH:
            raise WetElectricalSourceGraphError(
                "fluid route graph identity, interfaces, domain, or stage order changed"
            )

        domain_counts = {
            domain: sum(edge.fluid_domain == domain for edge in self.edges)
            for domain in CANONICAL_FLUID_DOMAINS
        }
        if domain_counts != {
            FLUID_DOMAIN_FRESH_WATER: 2,
            FLUID_DOMAIN_CLEANSER: 2,
            FLUID_DOMAIN_MIXED_WASTE: 3,
        }:
            raise WetElectricalSourceGraphError("canonical fluid route counts changed")

        waste_edges = tuple(
            edge for edge in self.edges if edge.fluid_domain == FLUID_DOMAIN_MIXED_WASTE
        )
        if (
            tuple(edge.stage for edge in waste_edges) != WASTE_ROUTE_STAGES
            or waste_edges[0].source_node_id != ROUTE_DESTINATION
            or waste_edges[0].target_node_id != STATION_WASTE
            or waste_edges[1].source_node_id != INTERFACE_PUMP_OUTLET
            or waste_edges[1].target_node_id != BARRIER_WASTE
            or waste_edges[2].source_node_id != INTERFACE_BARRIER_OUTLET
            or waste_edges[2].target_node_id != INTERFACE_CARTRIDGE_INLET_I27
            or any(
                edge.source_node_id == INTERFACE_PUMP_OUTLET
                and edge.target_node_id == INTERFACE_CARTRIDGE_INLET_I27
                for edge in waste_edges
            )
        ):
            raise WetElectricalSourceGraphError(
                "mixed-waste route must retain explicit passive-backflow stage and interfaces"
            )

        if self.physical_material_names != PHYSICAL_MATERIAL_NAMES:
            raise WetElectricalSourceGraphError("physical material boundary changed")
        if self.reference_review_names != REFERENCE_REVIEW_NAMES:
            raise WetElectricalSourceGraphError("reference review boundary changed")
        if set(self.physical_material_names) & set(self.reference_review_names):
            raise WetElectricalSourceGraphError("physical and reference roles must remain disjoint")
        if not self.illegal_reference_material_names:
            raise WetElectricalSourceGraphError(
                "assembly material boundary is no longer the first blocker; reconstruct before promotion"
            )
        if tuple(
            name for name in self.current_export_selected_names if name in self.reference_review_names
        ) != self.illegal_reference_material_names:
            raise WetElectricalSourceGraphError("illegal reference/material mixing accounting changed")
        if self.blockers != BLOCKER_IDS:
            raise WetElectricalSourceGraphError("integration blocker identity or order changed")
        if type(self.integration_release_ready) is not bool or self.integration_release_ready:
            raise WetElectricalSourceGraphError("current wet/electrical integration cannot be marked release ready")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise WetElectricalSourceGraphError("source graph cannot create physical-validation eligibility")
        if self.evidence_status != EVIDENCE_STATUS:
            raise WetElectricalSourceGraphError("source-graph evidence boundary changed")

    @property
    def manifest_sha256(self) -> str:
        return _digest(self.manifest(include_hash=False))

    def manifest(self, *, include_hash: bool = True) -> dict[str, object]:
        self.__post_init__()
        payload: dict[str, object] = {
            "schema": self.schema,
            "source_main_sha": self.source_main_sha,
            "authority_revision": self.authority_revision,
            "world_frame_id": self.world_frame_id,
            "canonical_fluid_domains": list(CANONICAL_FLUID_DOMAINS),
            "released_fluid_identity_by_domain": dict(RELEASED_FLUID_IDENTITY_BY_DOMAIN),
            "manifold_inlet_branch_binding_by_domain": {
                domain: {
                    "inlet_interface_id": inlet_id,
                    "branch_id": branch_id,
                }
                for domain, (inlet_id, branch_id) in MANIFOLD_INLET_BRANCH_BINDING_BY_DOMAIN.items()
            },
            "source_git_blob_identities": [
                {"path": path, "git_blob_sha": blob_sha}
                for path, blob_sha in SOURCE_GIT_BLOB_IDENTITIES
            ],
            "nodes": [node.manifest() for node in self.nodes],
            "edges": [edge.manifest() for edge in self.edges],
            "unreleased_realization_paths": list(UNRELEASED_REALIZATION_PATHS),
            "material_boundary": {
                "physical_material_names": list(self.physical_material_names),
                "reference_review_names": list(self.reference_review_names),
                "current_export_manual_exclusions": list(CURRENT_EXPORT_MANUAL_EXCLUSIONS),
                "current_export_selected_names": list(self.current_export_selected_names),
                "illegal_reference_material_names": list(self.illegal_reference_material_names),
            },
            "blockers": list(self.blockers),
            "first_integration_blocker": self.blockers[0],
            "integration_release_ready": self.integration_release_ready,
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": self.evidence_status,
        }
        if include_hash:
            payload["manifest_sha256"] = _digest(payload)
        return payload


def _released_nodes() -> tuple[SourceNode, ...]:
    topology_only = "RELEASED_TOPOLOGY_OR_REQUIREMENTS_ONLY"
    interface_only = "RELEASED_INTERFACE_TOPOLOGY_ONLY"
    unresolved = "UNRESOLVED_NO_RELEASED_PRODUCER"
    return (
        SourceNode(
            WATER_RESERVOIR_NODE,
            "CELL9_FRESH_WATER",
            "RELEASED",
            "PACKAGE_ENVELOPE_PLUS_TOPOLOGY",
            "PACKAGE_REFERENCE",
            FLUID_DOMAIN_FRESH_WATER,
            FLUID_FRESH_WATER,
        ),
        SourceNode(
            WATER_PORT_PICKUP,
            "CELL9_FRESH_WATER",
            "RELEASED",
            interface_only,
            "INTERFACE_TOPOLOGY_ONLY",
            FLUID_DOMAIN_FRESH_WATER,
            FLUID_FRESH_WATER,
        ),
        SourceNode(
            STATION_WATER,
            "CELL9_FRESH_WATER",
            "RELEASED",
            "PACKAGE_AND_CENTERLINES_UNRESOLVED",
            "TOPOLOGY_ONLY",
            FLUID_DOMAIN_FRESH_WATER,
            FLUID_FRESH_WATER,
        ),
        SourceNode(
            INTERFACE_WATER_PUMP_OUTLET,
            "CELL9_FRESH_WATER",
            "RELEASED",
            interface_only,
            "INTERFACE_TOPOLOGY_ONLY",
            FLUID_DOMAIN_FRESH_WATER,
            FLUID_FRESH_WATER,
        ),
        SourceNode(
            INLET_FRESH_WATER,
            "CELL9_FRESH_WATER",
            "RELEASED",
            interface_only,
            "INTERFACE_TOPOLOGY_ONLY",
            FLUID_DOMAIN_FRESH_WATER,
            FLUID_FRESH_WATER,
        ),
        SourceNode(
            BRANCH_FRESH_WATER,
            "CELL9_FRESH_WATER",
            "RELEASED",
            topology_only,
            "TOPOLOGY_ONLY",
            FLUID_DOMAIN_FRESH_WATER,
            FLUID_FRESH_WATER,
        ),
        SourceNode(
            CLEANSER_STORAGE_NODE,
            "CELL10_CLEANSER",
            "RELEASED",
            topology_only,
            "TOPOLOGY_ONLY",
            FLUID_DOMAIN_CLEANSER,
            FLUID_CLEANSER,
        ),
        SourceNode(
            CLEANSER_PORT_OUTLET,
            "CELL10_CLEANSER",
            "RELEASED",
            interface_only,
            "INTERFACE_TOPOLOGY_ONLY",
            FLUID_DOMAIN_CLEANSER,
            FLUID_CLEANSER,
        ),
        SourceNode(
            STATION_CLEANSER,
            "CELL10_CLEANSER",
            "RELEASED",
            "PACKAGE_AND_CENTERLINES_UNRESOLVED",
            "TOPOLOGY_ONLY",
            FLUID_DOMAIN_CLEANSER,
            FLUID_CLEANSER,
        ),
        SourceNode(
            INTERFACE_CLEANSER_PUMP_OUTLET,
            "CELL10_CLEANSER",
            "RELEASED",
            interface_only,
            "INTERFACE_TOPOLOGY_ONLY",
            FLUID_DOMAIN_CLEANSER,
            FLUID_CLEANSER,
        ),
        SourceNode(
            INLET_CLEANSER,
            "CELL10_CLEANSER",
            "RELEASED",
            interface_only,
            "INTERFACE_TOPOLOGY_ONLY",
            FLUID_DOMAIN_CLEANSER,
            FLUID_CLEANSER,
        ),
        SourceNode(
            BRANCH_CLEANSER,
            "CELL10_CLEANSER",
            "RELEASED",
            topology_only,
            "TOPOLOGY_ONLY",
            FLUID_DOMAIN_CLEANSER,
            FLUID_CLEANSER,
        ),
        SourceNode(
            WASTE_ACQUISITION_NODE,
            "CELL11_WASTE",
            "RELEASED",
            "ACQUISITION_GEOMETRY_UNRESOLVED",
            "TOPOLOGY_ONLY",
            FLUID_DOMAIN_MIXED_WASTE,
            PHASE_MIXED_WASTE,
        ),
        SourceNode(
            ROUTE_DESTINATION,
            "CELL11_WASTE",
            "RELEASED",
            interface_only,
            "INTERFACE_TOPOLOGY_ONLY",
            FLUID_DOMAIN_MIXED_WASTE,
            PHASE_MIXED_WASTE,
        ),
        SourceNode(
            STATION_WASTE,
            "CELL11_WASTE",
            "RELEASED",
            "PACKAGE_UNRESOLVED_CENTERLINE_BACKBONE_RELEASED",
            "TOPOLOGY_ONLY",
            FLUID_DOMAIN_MIXED_WASTE,
            PHASE_MIXED_WASTE,
        ),
        SourceNode(
            INTERFACE_PUMP_OUTLET,
            "CELL11_WASTE",
            "RELEASED",
            "WORLD_CENTERLINE_HANDOFF_INTERFACE_REALIZED",
            "INTERFACE_TOPOLOGY_ONLY",
            FLUID_DOMAIN_MIXED_WASTE,
            PHASE_MIXED_WASTE,
        ),
        SourceNode(
            BARRIER_WASTE,
            "CELL11_WASTE",
            "RELEASED",
            "COMPONENT_UNRESOLVED_CENTERLINE_BACKBONE_RELEASED",
            "TOPOLOGY_ONLY",
            FLUID_DOMAIN_MIXED_WASTE,
            PHASE_MIXED_WASTE,
        ),
        SourceNode(
            INTERFACE_BARRIER_OUTLET,
            "CELL11_WASTE",
            "RELEASED",
            "WORLD_CENTERLINE_HANDOFF_INTERFACE_REALIZED",
            "INTERFACE_TOPOLOGY_ONLY",
            FLUID_DOMAIN_MIXED_WASTE,
            PHASE_MIXED_WASTE,
        ),
        SourceNode(
            INTERFACE_CARTRIDGE_INLET_I27,
            "CELL11_WASTE",
            "RELEASED",
            "WORLD_CENTERLINE_HANDOFF_INTERFACE_REALIZED",
            "INTERFACE_TOPOLOGY_ONLY",
            FLUID_DOMAIN_MIXED_WASTE,
            PHASE_MIXED_WASTE,
        ),
        SourceNode(
            WASTE_CARTRIDGE_NODE,
            "CELL11_WASTE",
            "RELEASED",
            "EXTERNAL_PACKAGE_ENVELOPE_ONLY_DFM_BLOCKED",
            "PACKAGE_REFERENCE",
            FLUID_DOMAIN_MIXED_WASTE,
            PHASE_MIXED_WASTE,
        ),
        SourceNode("BATTERY_REFERENCE", "CELL12_DRY_SIDE", "RELEASED_REFERENCE_ONLY", "PACKAGING_BENCHMARK_ONLY", "PACKAGE_REFERENCE"),
        SourceNode("DRY_SIDE_BAY", "CELL12_DRY_SIDE", "ABSENT", unresolved, "UNRESOLVED"),
        SourceNode("HARNESS_BULKHEAD", "CELL13_HARNESS", "ABSENT", unresolved, "UNRESOLVED"),
        SourceNode("HMI_WARM_THERMAL", "CELL14_HMI_WARM", "ABSENT", unresolved, "UNRESOLVED"),
    )


def _fluid_edges() -> tuple[SourceEdge, ...]:
    fresh_unresolved = (
        "INTERFACE_TOPOLOGY_ONLY_CENTERLINES_TUBING_CONNECTORS_AND_SERVICE_UNRESOLVED"
    )
    waste_realized = "WORLD_CENTERLINE_REALIZED_PACKAGE_COMPONENTS_UNRESOLVED"
    return tuple(
        SourceEdge(
            edge_id,
            fluid_domain,
            fluid_identity,
            source_node_id,
            target_node_id,
            stage,
            waste_realized if fluid_domain == FLUID_DOMAIN_MIXED_WASTE else fresh_unresolved,
        )
        for (
            edge_id,
            fluid_domain,
            fluid_identity,
            source_node_id,
            target_node_id,
            stage,
        ) in EXPECTED_ROUTE_GRAPH
    )


def _validate_authority(authority: Authority) -> None:
    if type(authority) is not Authority:
        raise WetElectricalSourceGraphError("source graph requires exact Authority type")
    canonical = load_authority()
    if authority.data != canonical.data:
        raise WetElectricalSourceGraphError("supplied authority differs from released machine authority")
    if str(authority.get("project", "authority_revision")) != AUTHORITY_REVISION:
        raise WetElectricalSourceGraphError("authority revision moved")


def _model_boundary(model: MasckOneModel) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if type(model) is not MasckOneModel:
        raise WetElectricalSourceGraphError("source graph requires exact MasckOneModel type")
    names = tuple(component.name for component in model.components)
    expected_names = PHYSICAL_MATERIAL_NAMES + REFERENCE_REVIEW_NAMES
    if names != expected_names:
        raise WetElectricalSourceGraphError("released model component identity or order moved")
    current_export_selected = tuple(
        component.name
        for component in model.components
        if component.status != "REFERENCE_ONLY"
        and component.name not in CURRENT_EXPORT_MANUAL_EXCLUSIONS
    )
    illegal = tuple(name for name in current_export_selected if name in REFERENCE_REVIEW_NAMES)
    return current_export_selected, illegal


@lru_cache(maxsize=1)
def _default_model_boundary() -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Build the immutable released model boundary once per process.

    This removes duplicated full-CAD construction from receipt-only tests and smoke
    while source-blob checks still run on every graph reconstruction.
    """
    authority = load_authority()
    _validate_authority(authority)
    return _model_boundary(build_model(authority))


def build_wet_electrical_source_graph(
    authority: Authority | None = None,
    model: MasckOneModel | None = None,
) -> WetElectricalSourceGraph:
    _require_current_sources()
    if (authority is None) != (model is None):
        raise WetElectricalSourceGraphError(
            "authority and model must both be supplied for a nondefault reconstruction"
        )
    if authority is None:
        current_export_selected, illegal = _default_model_boundary()
    else:
        _validate_authority(authority)
        current_export_selected, illegal = _model_boundary(model)
    graph = WetElectricalSourceGraph(
        schema=SCHEMA,
        source_main_sha=SOURCE_MAIN_SHA,
        authority_revision=AUTHORITY_REVISION,
        world_frame_id=WORLD_FRAME_ID,
        nodes=_released_nodes(),
        edges=_fluid_edges(),
        physical_material_names=PHYSICAL_MATERIAL_NAMES,
        reference_review_names=REFERENCE_REVIEW_NAMES,
        current_export_selected_names=current_export_selected,
        illegal_reference_material_names=illegal,
        blockers=BLOCKER_IDS,
        integration_release_ready=False,
        physical_validation_eligible=False,
        evidence_status=EVIDENCE_STATUS,
    )
    graph.__post_init__()
    return graph
