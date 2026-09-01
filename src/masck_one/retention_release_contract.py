"""Pre-roadmap retention and quick-release architecture contract.

This module deliberately does not implement Iteration 29 or 30 geometry. It binds the
released structural-frame retention reservation and frozen quick-release safety
requirements into a deterministic topology/evidence contract so later retention work
cannot silently invent load paths, couple emergency release to fit adjustment, or claim
physical release performance from digital state.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import re

from .authority import Authority
from .structural_frame import (
    RESERVATION_IDS,
    RESERVATION_RETENTION,
    StructuralFrameTopology,
)

CONTRACT_ID = "MASCK_ONE_RETENTION_RELEASE_PREWORK_V1"
SELECTION_STATUS = "PREFERRED_EVALUATION_LANE_ONLY_NOT_ITERATION29_OR30_RELEASE"
DIGITAL_GEOMETRY_STATUS = "BLOCKED_PENDING_CONTROLLED_ITERATION29_RETENTION_GEOMETRY"
PHYSICAL_VALIDATION_STATUS = "BLOCKED_PENDING_RETENTION_HEADFORM_AND_HUMAN_FACTORS_EVIDENCE"
PREFERRED_EVALUATION_LANE = "DEDICATED_SINGLE_ACTION_LOOP_BREAK_SEPARATE_FROM_PRELOAD_ADJUSTMENT"

_ID = re.compile(r"^[A-Z][A-Z0-9_]{0,95}$")
_SHA = re.compile(r"^[0-9a-f]{64}$")


class RetentionReleaseContractError(ValueError):
    """Raised when the pre-roadmap retention/release contract is violated."""


def _identity(name: str, value: object) -> str:
    if type(value) is not str or _ID.fullmatch(value) is None:
        raise RetentionReleaseContractError(
            f"{name} must be exact built-in canonical ASCII uppercase identity"
        )
    return value


def _text(name: str, value: object) -> str:
    if type(value) is not str or not value.strip():
        raise RetentionReleaseContractError(f"{name} must be explicit non-empty text")
    return value


def _sha256(name: str, value: object) -> str:
    if type(value) is not str or _SHA.fullmatch(value) is None:
        raise RetentionReleaseContractError(
            f"{name} must be exact built-in canonical lowercase SHA-256"
        )
    return value


def _positive_number(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RetentionReleaseContractError(f"{name} must be numeric and not bool")
    value = float(value)
    if not math.isfinite(value) or value <= 0.0:
        raise RetentionReleaseContractError(f"{name} must be finite and positive")
    return value


def _exact_bool(name: str, value: object) -> bool:
    if type(value) is not bool:
        raise RetentionReleaseContractError(f"{name} must be exact bool")
    return value


@dataclass(frozen=True, slots=True)
class QuickReleaseRequirements:
    """Authority-bound release requirements, not measured release performance."""

    time_max_s: float
    time_status: str
    force_target_N: tuple[float, float]
    force_status: str
    one_hand_wet_unpowered: bool
    one_hand_wet_unpowered_status: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "time_max_s", _positive_number("time_max_s", self.time_max_s))
        if type(self.force_target_N) is not tuple or len(self.force_target_N) != 2:
            raise RetentionReleaseContractError("force_target_N must be exact 2-item tuple")
        lo = _positive_number("force_target_N[0]", self.force_target_N[0])
        hi = _positive_number("force_target_N[1]", self.force_target_N[1])
        if lo > hi:
            raise RetentionReleaseContractError("force target must be ordered minimum to maximum")
        object.__setattr__(self, "force_target_N", (lo, hi))
        object.__setattr__(
            self,
            "one_hand_wet_unpowered",
            _exact_bool("one_hand_wet_unpowered", self.one_hand_wet_unpowered),
        )
        if not self.one_hand_wet_unpowered:
            raise RetentionReleaseContractError("one-hand wet unpowered release is a frozen requirement")
        if _text("time_status", self.time_status) != "FROZEN_SAFETY_REQUIREMENT":
            raise RetentionReleaseContractError("release-time classification drift")
        if _text("force_status", self.force_status) != "VALIDATION_GATED":
            raise RetentionReleaseContractError("release-force classification drift")
        if (
            _text("one_hand_wet_unpowered_status", self.one_hand_wet_unpowered_status)
            != "FROZEN_SAFETY_REQUIREMENT"
        ):
            raise RetentionReleaseContractError("wet/unpowered release classification drift")

    def validate_invariants(self) -> None:
        self.__post_init__()

    def manifest(self) -> dict[str, object]:
        self.validate_invariants()
        return {
            "time_max_s": self.time_max_s,
            "time_status": self.time_status,
            "force_target_N": list(self.force_target_N),
            "force_status": self.force_status,
            "one_hand_wet_unpowered": self.one_hand_wet_unpowered,
            "one_hand_wet_unpowered_status": self.one_hand_wet_unpowered_status,
            "performance_evidence": "REQUIREMENT_ONLY_NOT_MEASURED_PERFORMANCE",
        }


@dataclass(frozen=True, slots=True)
class RetentionEdge:
    """One abstract load-path/topology edge, with no physical dimensions."""

    edge_id: str
    node_a: str
    node_b: str
    role: str
    release_interrupt: bool = False
    preload_adjustment: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "edge_id", _identity("edge_id", self.edge_id))
        object.__setattr__(self, "node_a", _identity("node_a", self.node_a))
        object.__setattr__(self, "node_b", _identity("node_b", self.node_b))
        if self.node_a == self.node_b:
            raise RetentionReleaseContractError("retention edge endpoints must differ")
        object.__setattr__(self, "role", _text("edge role", self.role))
        object.__setattr__(
            self, "release_interrupt", _exact_bool("release_interrupt", self.release_interrupt)
        )
        object.__setattr__(
            self, "preload_adjustment", _exact_bool("preload_adjustment", self.preload_adjustment)
        )
        if self.release_interrupt and self.preload_adjustment:
            raise RetentionReleaseContractError(
                "emergency release edge may not also be the preload-adjustment edge"
            )

    @property
    def undirected_key(self) -> tuple[str, str]:
        return tuple(sorted((self.node_a, self.node_b)))  # type: ignore[return-value]

    def manifest(self) -> dict[str, object]:
        self.__post_init__()
        return {
            "edge_id": self.edge_id,
            "node_a": self.node_a,
            "node_b": self.node_b,
            "role": self.role,
            "release_interrupt": self.release_interrupt,
            "preload_adjustment": self.preload_adjustment,
        }


@dataclass(frozen=True, slots=True)
class RetentionLoadPathTopology:
    """Abstract single-loop retention load topology with crown load sharing.

    The topology expresses only connectivity. There are intentionally no coordinates,
    strap widths, preload values, contact pressures, latch dimensions or trajectories.
    """

    topology_id: str
    nodes: tuple[str, ...]
    edges: tuple[RetentionEdge, ...]
    crown_node_id: str
    occipital_node_id: str
    release_control_id: str
    preload_adjuster_id: str
    geometry_status: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "topology_id", _identity("topology_id", self.topology_id))
        if type(self.nodes) is not tuple or not self.nodes:
            raise RetentionReleaseContractError("nodes must be a non-empty exact tuple")
        checked_nodes = tuple(_identity("node_id", node) for node in self.nodes)
        if len(set(checked_nodes)) != len(checked_nodes):
            raise RetentionReleaseContractError("retention topology node IDs must be unique")
        object.__setattr__(self, "nodes", checked_nodes)
        if type(self.edges) is not tuple or not self.edges:
            raise RetentionReleaseContractError("edges must be a non-empty exact tuple")
        for edge in self.edges:
            if type(edge) is not RetentionEdge:
                raise RetentionReleaseContractError("edges must contain exact RetentionEdge values")
            edge.__post_init__()
            if edge.node_a not in checked_nodes or edge.node_b not in checked_nodes:
                raise RetentionReleaseContractError("retention edge references unknown node")
        if len({edge.edge_id for edge in self.edges}) != len(self.edges):
            raise RetentionReleaseContractError("retention edge IDs must be unique")
        if len({edge.undirected_key for edge in self.edges}) != len(self.edges):
            raise RetentionReleaseContractError("duplicate undirected retention edge")
        for field_name in (
            "crown_node_id",
            "occipital_node_id",
            "release_control_id",
            "preload_adjuster_id",
        ):
            value = _identity(field_name, getattr(self, field_name))
            if field_name.endswith("node_id") and value not in checked_nodes:
                raise RetentionReleaseContractError(f"{field_name} must reference a topology node")
            object.__setattr__(self, field_name, value)
        if self.release_control_id == self.preload_adjuster_id:
            raise RetentionReleaseContractError(
                "emergency release control must remain distinct from preload adjustment"
            )
        object.__setattr__(self, "geometry_status", _text("geometry_status", self.geometry_status))
        if self.geometry_status != DIGITAL_GEOMETRY_STATUS:
            raise RetentionReleaseContractError("prework topology cannot claim controlled retention geometry")
        self._validate_graph()

    def _adjacency(self, *, release_open: bool) -> dict[str, set[str]]:
        adjacency = {node: set() for node in self.nodes}
        for edge in self.edges:
            if release_open and edge.release_interrupt:
                continue
            adjacency[edge.node_a].add(edge.node_b)
            adjacency[edge.node_b].add(edge.node_a)
        return adjacency

    def _component_count(self, *, release_open: bool) -> int:
        adjacency = self._adjacency(release_open=release_open)
        unseen = set(self.nodes)
        components = 0
        while unseen:
            components += 1
            stack = [next(iter(unseen))]
            while stack:
                node = stack.pop()
                if node not in unseen:
                    continue
                unseen.remove(node)
                stack.extend(adjacency[node] & unseen)
        return components

    def cycle_rank(self, *, release_open: bool) -> int:
        self._validate_member_types_only()
        edge_count = sum(
            1 for edge in self.edges if not (release_open and edge.release_interrupt)
        )
        return edge_count - len(self.nodes) + self._component_count(release_open=release_open)

    def _validate_member_types_only(self) -> None:
        if type(self.nodes) is not tuple or type(self.edges) is not tuple:
            raise RetentionReleaseContractError("retention topology containers were corrupted")
        for node in self.nodes:
            _identity("node_id", node)
        for edge in self.edges:
            if type(edge) is not RetentionEdge:
                raise RetentionReleaseContractError("retention topology edge type was corrupted")
            edge.__post_init__()

    def _validate_graph(self) -> None:
        release_edges = tuple(edge for edge in self.edges if edge.release_interrupt)
        adjustment_edges = tuple(edge for edge in self.edges if edge.preload_adjustment)
        if len(release_edges) != 1:
            raise RetentionReleaseContractError(
                "prework retention topology requires exactly one primary loop-break edge"
            )
        if len(adjustment_edges) != 1:
            raise RetentionReleaseContractError(
                "prework retention topology requires exactly one abstract preload-adjustment edge"
            )
        if self._component_count(release_open=False) != 1:
            raise RetentionReleaseContractError("closed retention topology must be connected")
        if self.cycle_rank(release_open=False) != 1:
            raise RetentionReleaseContractError(
                "closed retention topology must contain exactly one independent retention loop"
            )
        if self.cycle_rank(release_open=True) != 0:
            raise RetentionReleaseContractError(
                "opening the emergency release must break every closed retention cycle"
            )
        closed_adjacency = self._adjacency(release_open=False)
        if len(closed_adjacency[self.crown_node_id]) != 1:
            raise RetentionReleaseContractError(
                "crown support must be a load-sharing branch, not a secondary closed retention loop"
            )
        if self.occipital_node_id not in closed_adjacency[self.crown_node_id]:
            raise RetentionReleaseContractError(
                "crown load-sharing branch must terminate deliberately at occipital support"
            )

    def validate_invariants(self) -> None:
        self.__post_init__()

    def manifest(self) -> dict[str, object]:
        self.validate_invariants()
        return {
            "topology_id": self.topology_id,
            "nodes": list(self.nodes),
            "edges": [edge.manifest() for edge in self.edges],
            "crown_node_id": self.crown_node_id,
            "occipital_node_id": self.occipital_node_id,
            "release_control_id": self.release_control_id,
            "preload_adjuster_id": self.preload_adjuster_id,
            "closed_cycle_rank": self.cycle_rank(release_open=False),
            "release_open_cycle_rank": self.cycle_rank(release_open=True),
            "geometry_status": self.geometry_status,
            "load_path_evidence": "TOPOLOGY_ONLY_NOT_FORCE_PRELOAD_PRESSURE_SLIP_OR_STRENGTH_EVIDENCE",
        }


@dataclass(frozen=True, slots=True)
class ReleaseArchitectureOption:
    option_id: str
    concept: str
    strengths: tuple[str, ...]
    material_risks: tuple[str, ...]
    disposition: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "option_id", _identity("option_id", self.option_id))
        object.__setattr__(self, "concept", _text("concept", self.concept))
        for field_name in ("strengths", "material_risks"):
            value = getattr(self, field_name)
            if type(value) is not tuple or not value:
                raise RetentionReleaseContractError(f"{field_name} must be non-empty exact tuple")
            checked = tuple(_text(field_name, item) for item in value)
            if len(set(checked)) != len(checked):
                raise RetentionReleaseContractError(f"{field_name} entries must be unique")
            object.__setattr__(self, field_name, checked)
        object.__setattr__(self, "disposition", _text("disposition", self.disposition))

    def validate_invariants(self) -> None:
        self.__post_init__()

    def manifest(self) -> dict[str, object]:
        self.validate_invariants()
        return {
            "option_id": self.option_id,
            "concept": self.concept,
            "strengths": list(self.strengths),
            "material_risks": list(self.material_risks),
            "disposition": self.disposition,
        }


@dataclass(frozen=True, slots=True)
class RetentionReleasePreworkContract:
    source_structural_frame_sha256: str
    source_retention_reservation_status: str
    requirements: QuickReleaseRequirements
    load_path_topology: RetentionLoadPathTopology
    architecture_options: tuple[ReleaseArchitectureOption, ...]
    preferred_evaluation_lane: str
    selection_status: str
    required_digital_artifacts: tuple[str, ...]
    required_physical_evidence: tuple[str, ...]
    customer_friction_hypotheses: tuple[str, ...]
    digital_geometry_status: str
    physical_validation_status: str
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "source_structural_frame_sha256",
            _sha256("source_structural_frame_sha256", self.source_structural_frame_sha256),
        )
        object.__setattr__(
            self,
            "source_retention_reservation_status",
            _text("source_retention_reservation_status", self.source_retention_reservation_status),
        )
        if type(self.requirements) is not QuickReleaseRequirements:
            raise RetentionReleaseContractError("requirements must be exact QuickReleaseRequirements")
        self.requirements.validate_invariants()
        if type(self.load_path_topology) is not RetentionLoadPathTopology:
            raise RetentionReleaseContractError(
                "load_path_topology must be exact RetentionLoadPathTopology"
            )
        self.load_path_topology.validate_invariants()
        if type(self.architecture_options) is not tuple or not self.architecture_options:
            raise RetentionReleaseContractError("architecture_options must be non-empty exact tuple")
        for option in self.architecture_options:
            if type(option) is not ReleaseArchitectureOption:
                raise RetentionReleaseContractError(
                    "architecture_options must contain exact ReleaseArchitectureOption"
                )
            option.validate_invariants()
        ids = tuple(option.option_id for option in self.architecture_options)
        if len(set(ids)) != len(ids):
            raise RetentionReleaseContractError("architecture option IDs must be unique")
        if ids != (
            "DEDICATED_SINGLE_ACTION_LOOP_BREAK",
            "REAR_CENTER_LOOP_BREAK",
            "FRONT_FRAME_LOOP_BREAK",
            "PRELOAD_ADJUSTER_UNWIND_AS_RELEASE",
        ):
            raise RetentionReleaseContractError("architecture option order/coverage drift")
        object.__setattr__(
            self,
            "preferred_evaluation_lane",
            _identity("preferred_evaluation_lane", self.preferred_evaluation_lane),
        )
        if self.preferred_evaluation_lane != PREFERRED_EVALUATION_LANE:
            raise RetentionReleaseContractError("preferred evaluation lane drift")
        if _text("selection_status", self.selection_status) != SELECTION_STATUS:
            raise RetentionReleaseContractError("pre-roadmap selection status drift")
        for field_name in (
            "required_digital_artifacts",
            "required_physical_evidence",
            "customer_friction_hypotheses",
        ):
            value = getattr(self, field_name)
            if type(value) is not tuple or not value:
                raise RetentionReleaseContractError(f"{field_name} must be non-empty exact tuple")
            checked = tuple(_text(field_name, item) for item in value)
            if len(set(checked)) != len(checked):
                raise RetentionReleaseContractError(f"{field_name} entries must be unique")
            object.__setattr__(self, field_name, checked)
        if _text("digital_geometry_status", self.digital_geometry_status) != DIGITAL_GEOMETRY_STATUS:
            raise RetentionReleaseContractError("digital retention geometry cannot be promoted in prework")
        if (
            _text("physical_validation_status", self.physical_validation_status)
            != PHYSICAL_VALIDATION_STATUS
        ):
            raise RetentionReleaseContractError("physical validation status drift")
        object.__setattr__(
            self,
            "physical_validation_eligible",
            _exact_bool("physical_validation_eligible", self.physical_validation_eligible),
        )
        if self.physical_validation_eligible:
            raise RetentionReleaseContractError(
                "pre-roadmap retention/release contract cannot be physical-validation eligible"
            )

    def validate_invariants(self) -> None:
        self.__post_init__()

    @property
    def provenance_sha256(self) -> str:
        payload = self.manifest(include_sha=False)
        raw = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("ascii")
        return hashlib.sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        if type(include_sha) is not bool:
            raise RetentionReleaseContractError("include_sha must be exact bool")
        self.validate_invariants()
        payload: dict[str, object] = {
            "contract": CONTRACT_ID,
            "source_structural_frame_sha256": self.source_structural_frame_sha256,
            "source_retention_reservation_status": self.source_retention_reservation_status,
            "requirements": self.requirements.manifest(),
            "load_path_topology": self.load_path_topology.manifest(),
            "architecture_options": [option.manifest() for option in self.architecture_options],
            "preferred_evaluation_lane": self.preferred_evaluation_lane,
            "selection_status": self.selection_status,
            "required_digital_artifacts": list(self.required_digital_artifacts),
            "required_physical_evidence": list(self.required_physical_evidence),
            "customer_friction_hypotheses": list(self.customer_friction_hypotheses),
            "digital_geometry_status": self.digital_geometry_status,
            "physical_validation_status": self.physical_validation_status,
            "physical_validation_eligible": self.physical_validation_eligible,
            "iteration29_complete": False,
            "iteration30_complete": False,
        }
        if include_sha:
            payload["provenance_sha256"] = self.provenance_sha256
        return payload


def _validate_source_frame(authority: Authority, frame: StructuralFrameTopology) -> str:
    if type(authority) is not Authority:
        raise RetentionReleaseContractError("authority must be exact Authority")
    if type(frame) is not StructuralFrameTopology:
        raise RetentionReleaseContractError("frame must be exact StructuralFrameTopology")
    if frame.physical_validation_eligible:
        raise RetentionReleaseContractError("source structural frame cannot be physical evidence")
    if frame.cross_section_dimensions_mm is not None or frame.material_selection is not None:
        raise RetentionReleaseContractError(
            "pre-roadmap retention work requires the released unresolved structural-frame evidence boundary"
        )
    expected_frame = authority.pair("geometry", "functional_frame_xy_mm")
    if tuple(frame.functional_frame_xy_mm) != tuple(expected_frame):
        raise RetentionReleaseContractError("structural-frame authority dimensions are stale or mutated")
    if type(frame.reservations) is not tuple:
        raise RetentionReleaseContractError("structural-frame reservation container was corrupted")
    if tuple(item.reservation_id for item in frame.reservations) != RESERVATION_IDS:
        raise RetentionReleaseContractError("structural-frame reservation identity/order drift")
    retention = next(item for item in frame.reservations if item.reservation_id == RESERVATION_RETENTION)
    if retention.functional_role != (
        "reserve structural load-transfer interface to halo/occipital/crown retention system"
    ):
        raise RetentionReleaseContractError("retention reservation role drift")
    if retention.interface_count is not None:
        raise RetentionReleaseContractError("Iteration 15 may not predeclare retention interface count")
    if retention.placement_status != "RETENTION_GEOMETRY_DEFERRED_TO_ITERATION29":
        raise RetentionReleaseContractError("retention geometry was promoted outside Iteration 29")
    if retention.envelope_status != "UNRESOLVED":
        raise RetentionReleaseContractError("retention envelope must remain unresolved before Iteration 29")
    expected_evidence = "RESERVATION_ONLY_NOT_PRELOAD_QUICK_RELEASE_OR_FIT_EVIDENCE"
    if retention.evidence_status != expected_evidence:
        raise RetentionReleaseContractError("retention reservation evidence boundary drift")
    return retention.placement_status


def _requirements_from_authority(authority: Authority) -> QuickReleaseRequirements:
    force = authority.pair("safety", "quick_release", "force_target_N")
    return QuickReleaseRequirements(
        time_max_s=authority.number("safety", "quick_release", "time_max_s"),
        time_status=str(authority.get("safety", "quick_release", "time_status")),
        force_target_N=(float(force[0]), float(force[1])),
        force_status=str(authority.get("safety", "quick_release", "force_status")),
        one_hand_wet_unpowered=authority.get(
            "safety", "quick_release", "one_hand_wet_unpowered"
        ),
        one_hand_wet_unpowered_status=str(
            authority.get("safety", "quick_release", "one_hand_wet_unpowered_status")
        ),
    )


def _prework_topology() -> RetentionLoadPathTopology:
    nodes = (
        "RET_FRAME_LEFT_INTERFACE",
        "RET_LEFT_LOAD_TRANSFER",
        "RET_OCCIPITAL_SUPPORT",
        "RET_PRELOAD_ADJUSTER",
        "RET_RIGHT_LOAD_TRANSFER",
        "RET_QUICK_RELEASE_COUPLER",
        "RET_FRAME_RIGHT_INTERFACE",
        "RET_CROWN_LOAD_SHARE",
    )
    edges = (
        RetentionEdge(
            "RET_EDGE_FRAME_LEFT_TO_TRANSFER",
            "RET_FRAME_LEFT_INTERFACE",
            "RET_LEFT_LOAD_TRANSFER",
            "left structural-frame reaction transfer",
        ),
        RetentionEdge(
            "RET_EDGE_LEFT_TO_OCCIPITAL",
            "RET_LEFT_LOAD_TRANSFER",
            "RET_OCCIPITAL_SUPPORT",
            "left circumferential retention load path",
        ),
        RetentionEdge(
            "RET_EDGE_OCCIPITAL_TO_ADJUSTER",
            "RET_OCCIPITAL_SUPPORT",
            "RET_PRELOAD_ADJUSTER",
            "abstract preload-adjustment segment; exact location and mechanism unresolved",
            preload_adjustment=True,
        ),
        RetentionEdge(
            "RET_EDGE_ADJUSTER_TO_RIGHT",
            "RET_PRELOAD_ADJUSTER",
            "RET_RIGHT_LOAD_TRANSFER",
            "right circumferential retention load path downstream of abstract adjustment",
        ),
        RetentionEdge(
            "RET_EDGE_RIGHT_TO_RELEASE",
            "RET_RIGHT_LOAD_TRANSFER",
            "RET_QUICK_RELEASE_COUPLER",
            "load path into dedicated emergency release function",
        ),
        RetentionEdge(
            "RET_EDGE_RELEASE_TO_FRAME_RIGHT",
            "RET_QUICK_RELEASE_COUPLER",
            "RET_FRAME_RIGHT_INTERFACE",
            "single-action emergency loop-break segment; exact location/geometry unresolved",
            release_interrupt=True,
        ),
        RetentionEdge(
            "RET_EDGE_FRAME_REACTION_BRIDGE",
            "RET_FRAME_RIGHT_INTERFACE",
            "RET_FRAME_LEFT_INTERFACE",
            "existing structural-frame reaction closure represented topologically only",
        ),
        RetentionEdge(
            "RET_EDGE_OCCIPITAL_TO_CROWN",
            "RET_OCCIPITAL_SUPPORT",
            "RET_CROWN_LOAD_SHARE",
            "crown load-sharing branch that must not create a secondary retention loop",
        ),
    )
    return RetentionLoadPathTopology(
        topology_id="RETENTION_PREWORK_SINGLE_LOOP_CROWN_BRANCH",
        nodes=nodes,
        edges=edges,
        crown_node_id="RET_CROWN_LOAD_SHARE",
        occipital_node_id="RET_OCCIPITAL_SUPPORT",
        release_control_id="RET_QUICK_RELEASE_COUPLER",
        preload_adjuster_id="RET_PRELOAD_ADJUSTER",
        geometry_status=DIGITAL_GEOMETRY_STATUS,
    )


def _architecture_options() -> tuple[ReleaseArchitectureOption, ...]:
    return (
        ReleaseArchitectureOption(
            option_id="DEDICATED_SINGLE_ACTION_LOOP_BREAK",
            concept=(
                "A dedicated mechanical release interrupts the primary retention loop in one action, "
                "while fit/preload adjustment remains a separate function. Exact side, locus, latch "
                "geometry and actuation direction are deliberately unresolved."
            ),
            strengths=(
                "directly separates emergency release from fit tuning",
                "compatible with unpowered and firmware-independent release semantics",
                "permits topology-level proof that crown load sharing cannot trap a second closed loop",
            ),
            material_risks=(
                "exact control location may create asymmetric doff trajectory or accidental contact risk",
                "wet grip, glove-free dexterity, hair/pinch clearance and latch contamination remain unproven",
                "lateral versus rear placement must be reconciled with harness, battery and service packaging",
            ),
            disposition="PREFERRED_EVALUATION_LANE_NOT_GEOMETRY_FREEZE",
        ),
        ReleaseArchitectureOption(
            option_id="REAR_CENTER_LOOP_BREAK",
            concept=(
                "A dedicated loop-break control is concentrated near the occipital/rear retention region."
            ),
            strengths=(
                "can unload the circumferential retention path away from protected facial regions",
                "offers potentially symmetric opening of the head-contact loop",
            ),
            material_risks=(
                "blind one-hand wet reach may be slower or less certain than a more accessible control",
                "hair entanglement and pinch exposure are material rear-head risks",
                "preferred halo battery packaging creates a future Iteration 31 coexistence conflict to resolve",
            ),
            disposition="CREDIBLE_ALTERNATIVE_REQUIRES_REACH_HAIR_AND_PACKAGING_PROOF",
        ),
        ReleaseArchitectureOption(
            option_id="FRONT_FRAME_LOOP_BREAK",
            concept="A release control breaks retention close to the front structural frame.",
            strengths=(
                "high visual/tactile accessibility during normal handling",
                "potentially short direct load path to the structural frame",
            ),
            material_risks=(
                "control and release motion occur near facial protected regions and skin-contact interfaces",
                "accidental activation risk is elevated where the user handles the device front during don/doff",
                "opening trajectory could drag or rotate the facial interface across the face if poorly constrained",
            ),
            disposition="DEPRIORITIZED_PENDING_STRONGER_PROTECTED_REGION_AND_TRAJECTORY_CASE",
        ),
        ReleaseArchitectureOption(
            option_id="PRELOAD_ADJUSTER_UNWIND_AS_RELEASE",
            concept=(
                "Normal preload adjustment is also used as the only emergency release path by unwinding tension."
            ),
            strengths=(
                "lowest apparent part-count and interaction-count concept",
                "reuses an existing fit-control function",
            ),
            material_risks=(
                "couples emergency escape to the fit-adjustment mechanism and its failure modes",
                "multi-step or multi-turn unloading can conflict with the two-second frozen release requirement",
                "contamination, ratchet/dial damage or high preload could make emergency release less deterministic",
            ),
            disposition="REJECTED_AS_PRIMARY_EMERGENCY_RELEASE_PATH",
        ),
    )


def build_retention_release_prework(
    authority: Authority,
    frame: StructuralFrameTopology,
) -> RetentionReleasePreworkContract:
    """Build deterministic retention/release prework without implementing Iteration 29/30.

    This function is intentionally blocked from accepting caller-supplied geometry,
    release-force measurements, trajectory hashes or user-test outcomes. Those belong to
    later controlled iterations/evidence channels.
    """

    reservation_status = _validate_source_frame(authority, frame)
    contract = RetentionReleasePreworkContract(
        source_structural_frame_sha256=_sha256(
            "source_structural_frame_sha256", frame.topology_sha256
        ),
        source_retention_reservation_status=reservation_status,
        requirements=_requirements_from_authority(authority),
        load_path_topology=_prework_topology(),
        architecture_options=_architecture_options(),
        preferred_evaluation_lane=PREFERRED_EVALUATION_LANE,
        selection_status=SELECTION_STATUS,
        required_digital_artifacts=(
            "released Iteration 29 retention geometry with exact frame-anchor provenance",
            "local retention force/preload axes and deliberate reaction paths",
            "normal don/doff trajectories and complete swept-volume provenance",
            "quick-release start/end transforms and continuous collision-checked trajectory",
            "wet grip-access geometry and finger approach envelope",
            "hair and pinch keep-out geometry through the complete release trajectory",
            "accidental-activation protection geometry and actuation-direction rationale",
            "harness, service and future halo-battery clearance relationships",
            "tolerance/DOE stack tied to exact release and retention geometry",
            "travel/storage state envelope with no snag-prone unsupported release state",
        ),
        required_physical_evidence=(
            "one-hand wet unpowered release time distribution against the frozen two-second requirement",
            "release actuation-force distribution against the validation-gated target range",
            "accidental-release resistance under representative handling and head motion",
            "retention slip and stability across controlled headform/fit matrix",
            "regional pressure/hotspot behavior including nose bridge upper lip chin forehead and crown",
            "hair capture and pinch hazard evaluation across relevant hair/hand conditions",
            "release/don/doff usability without app instructions or firmware availability",
            "retention and release durability/service-cycle evidence",
        ),
        customer_friction_hypotheses=(
            "H-FIT-01",
            "H-FIT-02",
            "H-FIT-03",
            "H-RET-01",
            "H-RET-02",
            "H-QR-01",
            "H-TRAVEL-01",
            "H-STATE-02",
            "H-STATE-06",
            "H-STATE-07",
        ),
        digital_geometry_status=DIGITAL_GEOMETRY_STATUS,
        physical_validation_status=PHYSICAL_VALIDATION_STATUS,
        physical_validation_eligible=False,
    )
    contract.validate_invariants()
    return contract
