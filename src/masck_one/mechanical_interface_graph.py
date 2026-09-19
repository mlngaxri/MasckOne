from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1, sha256
import json
import math
from pathlib import Path
import re

SCHEMA = "MASCK_ONE_MECHANICAL_INTERFACE_GRAPH_V3"
SOURCE_MAIN_SHA = "42fa11818184cde998c6df25d7c46d4fb0e4c3eb"
AUTHORITY_REVISION = "2026-08-30-R1"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
UNITS = "mm"

CANONICAL_COMPONENT_IDS = frozenset(
    {"frame_structure", "actuator_zone", "retention_halo", "quick_release"}
)
GEOMETRY_ROLES = frozenset(
    {
        "physical_material_candidate",
        "mechanical_reference",
        "service_envelope",
        "keepout",
        "clearance",
        "protected",
        "sweep",
    }
)
INTERFACE_SEMANTICS = frozenset(
    {
        "positive_attachment",
        "clearance",
        "integral_continuity",
        "seal_interface_reservation",
        "route_support",
        "reference_only",
    }
)
SOURCE_STATUSES = frozenset({"RELEASED_MAIN", "CANDIDATE_PR", "HISTORICAL_DONOR"})
INTERFACE_STATUSES = frozenset({"CANDIDATE_REALIZED", "CANDIDATE_OPEN", "UNRESOLVED"})
MOTION_STATUSES = frozenset({"CANDIDATE_CONTINUOUS", "UNRESOLVED"})
LOAD_TRANSFER_SEMANTICS = frozenset({"positive_attachment", "integral_continuity"})
_SHA40 = re.compile(r"^[0-9a-f]{40}$")


class MechanicalInterfaceGraphError(ValueError):
    pass


def _nonblank(value: object, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise MechanicalInterfaceGraphError(f"{label} must be exact nonblank text")
    return value


def _sha40(value: object, label: str) -> str:
    if type(value) is not str or _SHA40.fullmatch(value) is None:
        raise MechanicalInterfaceGraphError(
            f"{label} must be a lowercase 40-character Git SHA"
        )
    return value


def _finite_positive(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MechanicalInterfaceGraphError(f"{label} must be a real number")
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise MechanicalInterfaceGraphError(f"{label} must be finite and positive")
    return result


def _finite_nonnegative(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MechanicalInterfaceGraphError(f"{label} must be a real number")
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise MechanicalInterfaceGraphError(f"{label} must be finite and nonnegative")
    return result


def _git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(f"blob {len(raw)}\0".encode("ascii") + raw).hexdigest()


@dataclass(frozen=True, slots=True)
class SourceBinding:
    source_id: str
    status: str
    path: str
    symbol: str
    blob_sha: str
    head_sha: str
    pr_number: int | None
    note: str
    local_file_binding: bool = False

    def __post_init__(self) -> None:
        _nonblank(self.source_id, "source id")
        _nonblank(self.path, "source path")
        _nonblank(self.symbol, "source symbol")
        _nonblank(self.note, "source note")
        _sha40(self.blob_sha, "source blob SHA")
        _sha40(self.head_sha, "source head SHA")
        if self.status not in SOURCE_STATUSES:
            raise MechanicalInterfaceGraphError(f"unknown source status {self.status}")
        if self.status in {"CANDIDATE_PR", "HISTORICAL_DONOR"}:
            if (
                isinstance(self.pr_number, bool)
                or not isinstance(self.pr_number, int)
                or self.pr_number <= 0
            ):
                raise MechanicalInterfaceGraphError(
                    "candidate/donor source requires a positive PR number"
                )
        elif self.pr_number is not None:
            raise MechanicalInterfaceGraphError(
                "released-main source cannot carry a PR number"
            )
        if type(self.local_file_binding) is not bool:
            raise MechanicalInterfaceGraphError("local_file_binding must be an exact bool")

    def manifest(self) -> dict[str, object]:
        return {
            "source_id": self.source_id,
            "status": self.status,
            "path": self.path,
            "symbol": self.symbol,
            "blob_sha": self.blob_sha,
            "head_sha": self.head_sha,
            "pr_number": self.pr_number,
            "note": self.note,
            "local_file_binding": self.local_file_binding,
        }


@dataclass(frozen=True, slots=True)
class MechanicalNode:
    node_id: str
    canonical_component_id: str
    instance_index: int | None
    source_id: str
    source_native_id: str
    geometry_role: str
    frame_id: str = WORLD_FRAME_ID
    units: str = UNITS

    def __post_init__(self) -> None:
        _nonblank(self.node_id, "node id")
        _nonblank(self.source_id, "node source id")
        _nonblank(self.source_native_id, "source-native id")
        if self.canonical_component_id not in CANONICAL_COMPONENT_IDS:
            raise MechanicalInterfaceGraphError(
                f"unknown canonical component id {self.canonical_component_id}"
            )
        if self.geometry_role not in GEOMETRY_ROLES:
            raise MechanicalInterfaceGraphError(
                f"unknown node geometry role {self.geometry_role}"
            )
        if self.frame_id != WORLD_FRAME_ID or self.units != UNITS:
            raise MechanicalInterfaceGraphError(
                "mechanical nodes must use canonical world-mm identity"
            )
        if self.canonical_component_id == "actuator_zone":
            if self.instance_index not in (0, 1, 2, 3):
                raise MechanicalInterfaceGraphError(
                    "actuator nodes require instance index 0..3"
                )
        elif self.instance_index is not None:
            raise MechanicalInterfaceGraphError(
                "only actuator_zone may carry an instance index"
            )

    def manifest(self) -> dict[str, object]:
        return {
            "node_id": self.node_id,
            "canonical_component_id": self.canonical_component_id,
            "instance_index": self.instance_index,
            "source_id": self.source_id,
            "source_native_id": self.source_native_id,
            "geometry_role": self.geometry_role,
            "frame_id": self.frame_id,
            "units": self.units,
        }


@dataclass(frozen=True, slots=True)
class MechanicalInterface:
    interface_id: str
    from_node: str
    to_node: str
    semantics: str
    status: str
    source_id: str
    positive_attachment: bool
    note: str

    def __post_init__(self) -> None:
        _nonblank(self.interface_id, "interface id")
        _nonblank(self.from_node, "interface from-node")
        _nonblank(self.to_node, "interface to-node")
        _nonblank(self.source_id, "interface source id")
        _nonblank(self.note, "interface note")
        if self.semantics not in INTERFACE_SEMANTICS:
            raise MechanicalInterfaceGraphError(
                f"unknown interface semantics {self.semantics}"
            )
        if self.status not in INTERFACE_STATUSES:
            raise MechanicalInterfaceGraphError(f"unknown interface status {self.status}")
        if type(self.positive_attachment) is not bool:
            raise MechanicalInterfaceGraphError(
                "positive_attachment must be an exact bool"
            )
        if self.positive_attachment != (self.semantics == "positive_attachment"):
            raise MechanicalInterfaceGraphError(
                "positive attachment bool must agree exactly with interface semantics"
            )
        if self.positive_attachment and self.status != "CANDIDATE_REALIZED":
            raise MechanicalInterfaceGraphError(
                "open/unresolved interface cannot be positive attachment"
            )
        if self.status != "CANDIDATE_REALIZED" and self.semantics not in {
            "reference_only",
            "clearance",
        }:
            raise MechanicalInterfaceGraphError(
                "open/unresolved interface may only expose reference or clearance semantics"
            )

    @property
    def transfers_load_digitally(self) -> bool:
        return (
            self.status == "CANDIDATE_REALIZED"
            and self.semantics in LOAD_TRANSFER_SEMANTICS
        )

    def manifest(self) -> dict[str, object]:
        return {
            "interface_id": self.interface_id,
            "from_node": self.from_node,
            "to_node": self.to_node,
            "semantics": self.semantics,
            "status": self.status,
            "source_id": self.source_id,
            "positive_attachment": self.positive_attachment,
            "transfers_load_digitally": self.transfers_load_digitally,
            "note": self.note,
        }


@dataclass(frozen=True, slots=True)
class ServiceMotion:
    motion_id: str
    moving_node: str
    status: str
    source_id: str | None
    continuous: bool
    travel_mm: float | None
    sample_count: int | None
    whole_product_motion: bool
    note: str
    blocking_source_ids: tuple[str, ...] = ()
    interference_mm3: float | None = None

    def __post_init__(self) -> None:
        _nonblank(self.motion_id, "motion id")
        _nonblank(self.moving_node, "moving node")
        _nonblank(self.note, "motion note")
        if self.status not in MOTION_STATUSES:
            raise MechanicalInterfaceGraphError(f"unknown motion status {self.status}")
        if type(self.continuous) is not bool or type(self.whole_product_motion) is not bool:
            raise MechanicalInterfaceGraphError("motion bool fields must be exact bools")
        if self.interference_mm3 is not None:
            _finite_nonnegative(self.interference_mm3, "motion interference")
        if any(type(item) is not str or not item for item in self.blocking_source_ids):
            raise MechanicalInterfaceGraphError(
                "motion blocking source ids must be nonblank strings"
            )
        if len(self.blocking_source_ids) != len(set(self.blocking_source_ids)):
            raise MechanicalInterfaceGraphError(
                "motion blocking source ids must be unique"
            )
        if self.status == "CANDIDATE_CONTINUOUS":
            _nonblank(self.source_id, "candidate motion source id")
            _finite_positive(self.travel_mm, "candidate motion travel")
            if (
                isinstance(self.sample_count, bool)
                or not isinstance(self.sample_count, int)
                or self.sample_count < 2
            ):
                raise MechanicalInterfaceGraphError(
                    "candidate continuous motion requires >=2 samples"
                )
            if not self.continuous:
                raise MechanicalInterfaceGraphError(
                    "candidate continuous motion must be continuous"
                )
            if self.blocking_source_ids:
                raise MechanicalInterfaceGraphError(
                    "candidate continuous motion cannot claim unresolved blockers"
                )
        else:
            if (
                self.source_id is not None
                or self.travel_mm is not None
                or self.sample_count is not None
            ):
                raise MechanicalInterfaceGraphError(
                    "unresolved motion cannot fabricate source, travel, or sampled evidence"
                )
            if self.continuous:
                raise MechanicalInterfaceGraphError(
                    "unresolved motion cannot claim continuity"
                )

    def manifest(self) -> dict[str, object]:
        return {
            "motion_id": self.motion_id,
            "moving_node": self.moving_node,
            "status": self.status,
            "source_id": self.source_id,
            "continuous": self.continuous,
            "travel_mm": self.travel_mm,
            "sample_count": self.sample_count,
            "whole_product_motion": self.whole_product_motion,
            "blocking_source_ids": list(self.blocking_source_ids),
            "interference_mm3": self.interference_mm3,
            "note": self.note,
        }


def _connected_nodes(start: str, interfaces: tuple[MechanicalInterface, ...]) -> set[str]:
    adjacency: dict[str, set[str]] = {}
    for edge in interfaces:
        adjacency.setdefault(edge.from_node, set()).add(edge.to_node)
        adjacency.setdefault(edge.to_node, set()).add(edge.from_node)
    seen = {start}
    stack = [start]
    while stack:
        current = stack.pop()
        for neighbor in adjacency.get(current, ()):
            if neighbor not in seen:
                seen.add(neighbor)
                stack.append(neighbor)
    return seen


@dataclass(frozen=True, slots=True)
class MechanicalInterfaceGraph:
    sources: tuple[SourceBinding, ...]
    nodes: tuple[MechanicalNode, ...]
    interfaces: tuple[MechanicalInterface, ...]
    service_motions: tuple[ServiceMotion, ...]
    whole_mechanical_package_closed: bool = False

    def __post_init__(self) -> None:
        if (
            type(self.whole_mechanical_package_closed) is not bool
            or self.whole_mechanical_package_closed
        ):
            raise MechanicalInterfaceGraphError(
                "whole mechanical package must remain open while cross-boundary joins/service are unresolved"
            )

        source_ids = tuple(item.source_id for item in self.sources)
        node_ids = tuple(item.node_id for item in self.nodes)
        interface_ids = tuple(item.interface_id for item in self.interfaces)
        motion_ids = tuple(item.motion_id for item in self.service_motions)
        for values, label in (
            (source_ids, "source"),
            (node_ids, "node"),
            (interface_ids, "interface"),
            (motion_ids, "motion"),
        ):
            if len(values) != len(set(values)):
                raise MechanicalInterfaceGraphError(f"duplicate {label} id")

        source_set = set(source_ids)
        node_set = set(node_ids)
        if any(node.source_id not in source_set for node in self.nodes):
            raise MechanicalInterfaceGraphError("node references an unknown source")
        for interface in self.interfaces:
            if interface.source_id not in source_set:
                raise MechanicalInterfaceGraphError(
                    "interface references an unknown source"
                )
            if interface.from_node not in node_set or interface.to_node not in node_set:
                raise MechanicalInterfaceGraphError(
                    "interface endpoint is not a graph node"
                )
        for motion in self.service_motions:
            if motion.moving_node not in node_set:
                raise MechanicalInterfaceGraphError(
                    "motion moving node is not a graph node"
                )
            if motion.source_id is not None and motion.source_id not in source_set:
                raise MechanicalInterfaceGraphError("motion references an unknown source")
            if any(item not in source_set for item in motion.blocking_source_ids):
                raise MechanicalInterfaceGraphError(
                    "motion blocker references an unknown source"
                )

        actuator_indices = sorted(
            node.instance_index
            for node in self.nodes
            if node.canonical_component_id == "actuator_zone"
            and node.source_native_id == "ACTUATOR-CARRIER-TEMPLATE"
        )
        if actuator_indices != [0, 1, 2, 3]:
            raise MechanicalInterfaceGraphError(
                "graph must preserve exactly four actuator carrier zones"
            )

        realized_edges = tuple(edge for edge in self.interfaces if edge.transfers_load_digitally)
        for node in self.nodes:
            if node.geometry_role != "physical_material_candidate":
                continue
            if not any(
                edge.from_node == node.node_id or edge.to_node == node.node_id
                for edge in realized_edges
            ):
                raise MechanicalInterfaceGraphError(
                    f"floating material candidate is prohibited: {node.node_id}"
                )

        required_retention_nodes = {
            "FRAME_REACTION_LOOP",
            "RETENTION_ROOT_LEFT",
            "RETENTION_ROOT_RIGHT",
            "OCCIPITAL_YOKE_LEFT",
            "OCCIPITAL_YOKE_RIGHT",
            "RETENTION_ADJUSTMENT_LEFT",
            "RETENTION_ADJUSTMENT_RIGHT",
            "RETENTION_CARRIER_LEFT",
            "RETENTION_CARRIER_RIGHT",
            "CROWN_SUPPORT",
        }
        if not required_retention_nodes.issubset(node_set):
            raise MechanicalInterfaceGraphError(
                "selected bilateral retention load path is incomplete"
            )
        required_retention_interface_ids = {
            "FRAME_TO_RETENTION_ROOT_LEFT",
            "FRAME_TO_RETENTION_ROOT_RIGHT",
            "RETENTION_ROOT_TO_YOKE_LEFT",
            "RETENTION_ROOT_TO_YOKE_RIGHT",
            "YOKE_TO_ADJUSTMENT_LEFT",
            "YOKE_TO_ADJUSTMENT_RIGHT",
            "ADJUSTMENT_TO_CARRIER_LEFT",
            "ADJUSTMENT_TO_CARRIER_RIGHT",
            "CARRIER_TO_CROWN_LEFT",
            "CARRIER_TO_CROWN_RIGHT",
        }
        edge_by_id = {edge.interface_id: edge for edge in self.interfaces}
        if not required_retention_interface_ids.issubset(edge_by_id):
            raise MechanicalInterfaceGraphError(
                "selected retention load path is missing an exact required counterpart"
            )
        if any(
            not edge_by_id[interface_id].transfers_load_digitally
            for interface_id in required_retention_interface_ids
        ):
            raise MechanicalInterfaceGraphError(
                "selected retention load path counterpart lost positive/integral load transfer"
            )
        connected = _connected_nodes("FRAME_REACTION_LOOP", realized_edges)
        if not required_retention_nodes.issubset(connected):
            raise MechanicalInterfaceGraphError(
                "selected bilateral retention load path lacks positive/integral counterparts"
            )

        donor = next(
            (item for item in self.sources if item.source_id == "QUICK_RELEASE_V1"),
            None,
        )
        quick_node = next(
            (item for item in self.nodes if item.node_id == "QUICK_RELEASE_RIGHT"),
            None,
        )
        if (
            donor is None
            or donor.status != "HISTORICAL_DONOR"
            or quick_node is None
            or quick_node.geometry_role != "mechanical_reference"
        ):
            raise MechanicalInterfaceGraphError(
                "closed quick-release lineage must remain a historical reference donor"
            )

        whole_removal = [
            item
            for item in self.service_motions
            if item.motion_id == "WHOLE_HEAD_REMOVAL"
        ]
        if len(whole_removal) != 1 or whole_removal[0].status != "UNRESOLVED":
            raise MechanicalInterfaceGraphError(
                "whole-head removal must remain unresolved"
            )

        for side in ("LEFT", "RIGHT"):
            factory = next(
                (
                    item
                    for item in self.service_motions
                    if item.motion_id == f"{side}_RETENTION_GUARD_OUTBOARD_FACTORY_INSTALL"
                ),
                None,
            )
            if (
                factory is None
                or factory.status != "CANDIDATE_CONTINUOUS"
                or factory.interference_mm3 != 0.0
            ):
                raise MechanicalInterfaceGraphError(
                    "latest Cell 8 outboard guard factory sweep must remain exact and collision-free"
                )

    @property
    def selected_retention_load_path_closed(self) -> bool:
        return True

    @property
    def graph_sha256(self) -> str:
        raw = json.dumps(
            self.manifest(include_sha=False),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        return sha256(raw.encode("utf-8")).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        result: dict[str, object] = {
            "schema": SCHEMA,
            "source_main_sha": SOURCE_MAIN_SHA,
            "authority_revision": AUTHORITY_REVISION,
            "frame_id": WORLD_FRAME_ID,
            "units": UNITS,
            "canonical_registry_status": "RELEASED_MAIN_SOURCE_BOUND",
            "sources": [item.manifest() for item in self.sources],
            "nodes": [item.manifest() for item in self.nodes],
            "interfaces": [item.manifest() for item in self.interfaces],
            "service_motions": [item.manifest() for item in self.service_motions],
            "selected_retention_load_path_closed": self.selected_retention_load_path_closed,
            "whole_mechanical_package_closed": self.whole_mechanical_package_closed,
            "superseded_evidence": [
                {
                    "source": "PR_124_MECHANICAL_INTERFACE_GRAPH_V2",
                    "reason": "stale producer receipts and pre-Cell6 retention counterpart assumptions",
                },
                {
                    "source": "PR_109_PRE_OUTBOARD_GUARD_SWEEPS",
                    "reason": "39.840676 mm3 yoke-intersecting pure-X guard installation path superseded by exact outboard entry sweeps at PR 109 head 82087afce9db01d041ca745dc3d464912fb12123",
                },
                {
                    "source": "PR_71_PROMOTION_EVIDENCE",
                    "reason": "closed unmerged quick-release branch retained only as exact geometry donor",
                },
            ],
            "evidence_status": (
                "DIGITAL_SOURCE_BOUND_INTERFACE_AND_MOTION_CLASSIFICATION_ONLY_NOT_PHYSICAL_"
                "FIT_FORCE_SAFETY_STRENGTH_DURABILITY_OR_SERVICE_VALIDATION"
            ),
        }
        if include_sha:
            result["graph_sha256"] = self.graph_sha256
        return result


def _sources() -> tuple[SourceBinding, ...]:
    return (
        SourceBinding(
            "REGISTRY_V3",
            "RELEASED_MAIN",
            "src/masck_one/component_registry.py",
            "CanonicalComponentRegistry",
            "00b729ca0b113c98bba0ecf899e86783873158d0",
            SOURCE_MAIN_SHA,
            None,
            "Released canonical registry on exact current main.",
            True,
        ),
        SourceBinding(
            "FRAME_V2",
            "CANDIDATE_PR",
            "src/masck_one/structural_frame_realization.py",
            "StructuralFrameRealization",
            "5e626e73cc130dc6cc6570e40183380562cf5b5e",
            "2d5ace19e2f87a8bd92f4620d8e6b225ba3826be",
            117,
            "Current-main Cell 6 structural reaction-loop owner. Exact-head CI 34319974921 failed in full unit/integration; no green promotion evidence is inherited.",
            True,
        ),
        SourceBinding(
            "FRAME_RETENTION_ROOTS_V1",
            "CANDIDATE_PR",
            "src/masck_one/structural_frame_retention_roots.py",
            "StructuralFrameRetentionRootArchitecture",
            "982c9722792a1190075a6a52a9ca756ebd5d502b",
            "2d5ace19e2f87a8bd92f4620d8e6b225ba3826be",
            117,
            "Bilateral frame-integral clevises with transverse capture pins and split retainers at the exact yoke root datums. Binding is refreshed to PR 123 blob 6d35c96bc65bb1e0e877deadc65481bf44954b4e.",
            True,
        ),
        SourceBinding(
            "FRAME_CROWN_SUPPORT_V1",
            "CANDIDATE_PR",
            "src/masck_one/structural_frame_crown_support.py",
            "StructuralFrameCrownSupportArchitecture",
            "aff317669d115bcd65f21421828a557b00deba5e",
            "2d5ace19e2f87a8bd92f4620d8e6b225ba3826be",
            117,
            "One-piece bilateral crown support with positive X-axis pin capture; seated pin/crown collision repair is retained.",
            True,
        ),
        SourceBinding(
            "CARRIER_V1",
            "CANDIDATE_PR",
            "src/masck_one/actuator_carriers.py",
            "ActuatorCarrierPackage",
            "9c613f40ed1b8cb43c3a40bb945d53084a71d121",
            "37e03df4b6abbd222422c8bfd4e70b03a4e5ae07",
            118,
            "Unrelated Cell 7 actuator-carrier candidate is preserved without changing its open world-mount status.",
        ),
        SourceBinding(
            "OCCIPITAL_YOKES_V1",
            "CANDIDATE_PR",
            "src/masck_one/occipital_stabilizer.py",
            "OccipitalStabilizer",
            "6d35c96bc65bb1e0e877deadc65481bf44954b4e",
            "25686766238b66ecf900009042d721c08e042592",
            123,
            "Exact Cell 8 bilateral yokes are selected. Their older frame-counterpart-unresolved statement is superseded by current Cell 6 positive clevis/pin counterparts.",
        ),
        SourceBinding(
            "RETENTION_ADJUSTMENT_V1",
            "CANDIDATE_PR",
            "src/masck_one/retention_fit_adjustment.py",
            "RetentionFitAdjustment",
            "4d4583d3df7c86151fd7761fbc05e6f93328d338",
            "88a88bed01fd3b3acfb38ff5f6f3ae3d5bbf54fe",
            92,
            "Indexed bounded adjustment geometry retained as the current Cell 3 owner; anthropometric fit remains unvalidated.",
        ),
        SourceBinding(
            "RETENTION_V2",
            "CANDIDATE_PR",
            "src/masck_one/retention_load_path.py",
            "RetentionLoadPathPackage",
            "9647405b36642105c929a3fdd0617d03bfe68c98",
            "88a88bed01fd3b3acfb38ff5f6f3ae3d5bbf54fe",
            92,
            "Cell 3 carrier and crown/facial handoff geometry retained. Old missing-crown-counterpart assumption is superseded only where Cell 6 now supplies exact positive crown capture.",
        ),
        SourceBinding(
            "QUICK_RELEASE_V1",
            "HISTORICAL_DONOR",
            "src/masck_one/right_quick_release_latch.py",
            "QuickReleaseLatchResult",
            "11d90a75eb108c53f5a1621abdace7271bf5cac5",
            "0b5a619c6cea344038b0e8b8cc10a50e3d193390",
            71,
            "Closed unmerged 7.3 mm captive right-latch lineage is geometry donor evidence only, not an integrated attachment or promotion receipt.",
        ),
        SourceBinding(
            "RETENTION_GUARDS_V2",
            "CANDIDATE_PR",
            "src/masck_one/retention_hazard_guards.py",
            "RetentionHazardGuardPackage",
            "7620ce296d37f7c109aeb7ff26925c75898ce24f",
            "82087afce9db01d041ca745dc3d464912fb12123",
            109,
            "Latest Cell 8 guard owner with exact outboard 22 mm installation sweeps. Prior yoke-intersecting inboard path is superseded.",
        ),
        SourceBinding(
            "SERVICE_INVENTORY_V1",
            "CANDIDATE_PR",
            "src/masck_one/assembly_service_inventory.py",
            "AssemblyServiceInventory",
            "e44c8ca12d7b163a5a3fb54fbce7ca2c16d0fc5c",
            "630cc19497661ae834032eb8ea06e28dfd6100b7",
            114,
            "Stale service inventory is retained only as blocker evidence; it cannot close whole-head removal.",
        ),
    )


def build_mechanical_interface_graph() -> MechanicalInterfaceGraph:
    nodes: list[MechanicalNode] = [
        MechanicalNode(
            "FRAME_REACTION_LOOP",
            "frame_structure",
            None,
            "FRAME_V2",
            "MASCK_ONE-FRAME-MEMBER-PERIMETER-REACTION-LOOP-V1",
            "physical_material_candidate",
        ),
        MechanicalNode(
            "RETENTION_ROOT_LEFT",
            "frame_structure",
            None,
            "FRAME_RETENTION_ROOTS_V1",
            "RETENTION_ROOT_WEARER_LEFT",
            "physical_material_candidate",
        ),
        MechanicalNode(
            "RETENTION_ROOT_RIGHT",
            "frame_structure",
            None,
            "FRAME_RETENTION_ROOTS_V1",
            "RETENTION_ROOT_WEARER_RIGHT",
            "physical_material_candidate",
        ),
        MechanicalNode(
            "OCCIPITAL_YOKE_LEFT",
            "retention_halo",
            None,
            "OCCIPITAL_YOKES_V1",
            "OCCIPITAL_STABILIZER_LEFT_YOKE",
            "physical_material_candidate",
        ),
        MechanicalNode(
            "OCCIPITAL_YOKE_RIGHT",
            "retention_halo",
            None,
            "OCCIPITAL_YOKES_V1",
            "OCCIPITAL_STABILIZER_RIGHT_YOKE",
            "physical_material_candidate",
        ),
        MechanicalNode(
            "RETENTION_ADJUSTMENT_LEFT",
            "retention_halo",
            None,
            "RETENTION_ADJUSTMENT_V1",
            "RETENTION_ADJUSTMENT_LEFT",
            "physical_material_candidate",
        ),
        MechanicalNode(
            "RETENTION_ADJUSTMENT_RIGHT",
            "retention_halo",
            None,
            "RETENTION_ADJUSTMENT_V1",
            "RETENTION_ADJUSTMENT_RIGHT",
            "physical_material_candidate",
        ),
        MechanicalNode(
            "RETENTION_CARRIER_LEFT",
            "retention_halo",
            None,
            "RETENTION_V2",
            "RETENTION_LOAD_PATH_LEFT",
            "physical_material_candidate",
        ),
        MechanicalNode(
            "RETENTION_CARRIER_RIGHT",
            "retention_halo",
            None,
            "RETENTION_V2",
            "RETENTION_LOAD_PATH_RIGHT",
            "physical_material_candidate",
        ),
        MechanicalNode(
            "CROWN_SUPPORT",
            "retention_halo",
            None,
            "FRAME_CROWN_SUPPORT_V1",
            "ONE_PIECE_BILATERAL_CROWN_SUPPORT",
            "physical_material_candidate",
        ),
        MechanicalNode(
            "QUICK_RELEASE_RIGHT",
            "quick_release",
            None,
            "QUICK_RELEASE_V1",
            "QR_BODY_RIGHT+QR_SLIDER_RIGHT",
            "mechanical_reference",
        ),
        MechanicalNode(
            "QUICK_RELEASE_GUARD_RIGHT",
            "quick_release",
            None,
            "RETENTION_GUARDS_V2",
            "RETENTION_QUICK_RELEASE_GUARD_RIGHT",
            "mechanical_reference",
        ),
        MechanicalNode(
            "RETENTION_GUARD_LEFT",
            "retention_halo",
            None,
            "RETENTION_GUARDS_V2",
            "RETENTION_OCCIPITAL_GUARD_LEFT",
            "mechanical_reference",
        ),
        MechanicalNode(
            "RETENTION_GUARD_RIGHT",
            "retention_halo",
            None,
            "RETENTION_GUARDS_V2",
            "RETENTION_OCCIPITAL_GUARD_RIGHT",
            "mechanical_reference",
        ),
    ]
    for index in range(4):
        nodes.append(
            MechanicalNode(
                f"ACTUATOR_CARRIER_ZONE_{index}",
                "actuator_zone",
                index,
                "CARRIER_V1",
                "ACTUATOR-CARRIER-TEMPLATE",
                "physical_material_candidate",
            )
        )

    interfaces: list[MechanicalInterface] = []
    for index in range(4):
        carrier = f"ACTUATOR_CARRIER_ZONE_{index}"
        interfaces.extend(
            (
                MechanicalInterface(
                    f"CARRIER_LOCAL_CLOSURE_ZONE_{index}",
                    carrier,
                    carrier,
                    "positive_attachment",
                    "CANDIDATE_REALIZED",
                    "CARRIER_V1",
                    True,
                    "Existing two-pin local carrier closure is preserved unchanged.",
                ),
                MechanicalInterface(
                    f"FRAME_TO_CARRIER_ZONE_{index}",
                    "FRAME_REACTION_LOOP",
                    carrier,
                    "reference_only",
                    "CANDIDATE_OPEN",
                    "CARRIER_V1",
                    False,
                    "Unrelated actuator world mount remains open because current package transforms conflict with protected envelopes.",
                ),
            )
        )

    interfaces.extend(
        (
            MechanicalInterface(
                "FRAME_TO_RETENTION_ROOT_LEFT",
                "FRAME_REACTION_LOOP",
                "RETENTION_ROOT_LEFT",
                "integral_continuity",
                "CANDIDATE_REALIZED",
                "FRAME_RETENTION_ROOTS_V1",
                False,
                "Cell 6 frame stem/bridge/clevis is integral with the structural reaction loop.",
            ),
            MechanicalInterface(
                "FRAME_TO_RETENTION_ROOT_RIGHT",
                "FRAME_REACTION_LOOP",
                "RETENTION_ROOT_RIGHT",
                "integral_continuity",
                "CANDIDATE_REALIZED",
                "FRAME_RETENTION_ROOTS_V1",
                False,
                "Cell 6 frame stem/bridge/clevis is integral with the structural reaction loop.",
            ),
            MechanicalInterface(
                "RETENTION_ROOT_TO_YOKE_LEFT",
                "RETENTION_ROOT_LEFT",
                "OCCIPITAL_YOKE_LEFT",
                "positive_attachment",
                "CANDIDATE_REALIZED",
                "FRAME_RETENTION_ROOTS_V1",
                True,
                "Exact +/-72,10,-31 mm yoke bore is captured by the Cell 6 transverse pin and split retainer with positive radial clearance.",
            ),
            MechanicalInterface(
                "RETENTION_ROOT_TO_YOKE_RIGHT",
                "RETENTION_ROOT_RIGHT",
                "OCCIPITAL_YOKE_RIGHT",
                "positive_attachment",
                "CANDIDATE_REALIZED",
                "FRAME_RETENTION_ROOTS_V1",
                True,
                "Exact +/-72,10,-31 mm yoke bore is captured by the Cell 6 transverse pin and split retainer with positive radial clearance.",
            ),
            MechanicalInterface(
                "YOKE_TO_ADJUSTMENT_LEFT",
                "OCCIPITAL_YOKE_LEFT",
                "RETENTION_ADJUSTMENT_LEFT",
                "positive_attachment",
                "CANDIDATE_REALIZED",
                "RETENTION_ADJUSTMENT_V1",
                True,
                "Cell 3 successor yoke tongue, indexed guide and permanent stop hardware form the bounded positive adjustment mechanism.",
            ),
            MechanicalInterface(
                "YOKE_TO_ADJUSTMENT_RIGHT",
                "OCCIPITAL_YOKE_RIGHT",
                "RETENTION_ADJUSTMENT_RIGHT",
                "positive_attachment",
                "CANDIDATE_REALIZED",
                "RETENTION_ADJUSTMENT_V1",
                True,
                "Cell 3 successor yoke tongue, indexed guide and permanent stop hardware form the bounded positive adjustment mechanism.",
            ),
            MechanicalInterface(
                "ADJUSTMENT_TO_CARRIER_LEFT",
                "RETENTION_ADJUSTMENT_LEFT",
                "RETENTION_CARRIER_LEFT",
                "positive_attachment",
                "CANDIDATE_REALIZED",
                "RETENTION_V2",
                True,
                "Cell 3 carrier positively captures the fixed adjustment housing using the retained dual-pin clevis architecture.",
            ),
            MechanicalInterface(
                "ADJUSTMENT_TO_CARRIER_RIGHT",
                "RETENTION_ADJUSTMENT_RIGHT",
                "RETENTION_CARRIER_RIGHT",
                "positive_attachment",
                "CANDIDATE_REALIZED",
                "RETENTION_V2",
                True,
                "Cell 3 carrier positively captures the fixed adjustment housing using the retained dual-pin clevis architecture.",
            ),
            MechanicalInterface(
                "CARRIER_TO_CROWN_LEFT",
                "RETENTION_CARRIER_LEFT",
                "CROWN_SUPPORT",
                "positive_attachment",
                "CANDIDATE_REALIZED",
                "FRAME_CROWN_SUPPORT_V1",
                True,
                "Cell 6 crown eyelet is positively pinned through the exact Cell 3 left crown-lug X-axis bore.",
            ),
            MechanicalInterface(
                "CARRIER_TO_CROWN_RIGHT",
                "RETENTION_CARRIER_RIGHT",
                "CROWN_SUPPORT",
                "positive_attachment",
                "CANDIDATE_REALIZED",
                "FRAME_CROWN_SUPPORT_V1",
                True,
                "Cell 6 crown eyelet is positively pinned through the exact Cell 3 right crown-lug X-axis bore.",
            ),
            MechanicalInterface(
                "FRAME_TO_RETENTION_FACIAL_REACTION_LEFT",
                "FRAME_REACTION_LOOP",
                "RETENTION_CARRIER_LEFT",
                "reference_only",
                "CANDIDATE_OPEN",
                "RETENTION_V2",
                False,
                "Cell 3 facial-reaction handoff feature has no current exact frame-side positive mating counterpart.",
            ),
            MechanicalInterface(
                "FRAME_TO_RETENTION_FACIAL_REACTION_RIGHT",
                "FRAME_REACTION_LOOP",
                "RETENTION_CARRIER_RIGHT",
                "reference_only",
                "CANDIDATE_OPEN",
                "RETENTION_V2",
                False,
                "Cell 3 facial-reaction handoff feature has no current exact frame-side positive mating counterpart.",
            ),
            MechanicalInterface(
                "RETENTION_TO_QUICK_RELEASE",
                "RETENTION_CARRIER_RIGHT",
                "QUICK_RELEASE_RIGHT",
                "reference_only",
                "CANDIDATE_OPEN",
                "QUICK_RELEASE_V1",
                False,
                "Closed PR 71 remains a stale-base donor. No integrated retention counterpart is promoted from overlap or reference geometry.",
            ),
            MechanicalInterface(
                "QUICK_RELEASE_TO_GUARD",
                "QUICK_RELEASE_RIGHT",
                "QUICK_RELEASE_GUARD_RIGHT",
                "clearance",
                "CANDIDATE_OPEN",
                "RETENTION_GUARDS_V2",
                False,
                "Guard preserves the emergency pull corridor but has no positive frame counterpart.",
            ),
            MechanicalInterface(
                "RETENTION_TO_LEFT_GUARD",
                "OCCIPITAL_YOKE_LEFT",
                "RETENTION_GUARD_LEFT",
                "clearance",
                "CANDIDATE_OPEN",
                "RETENTION_GUARDS_V2",
                False,
                "Latest final guard pose retains approximately 2.46221445 mm yoke clearance; guard attachment remains open.",
            ),
            MechanicalInterface(
                "RETENTION_TO_RIGHT_GUARD",
                "OCCIPITAL_YOKE_RIGHT",
                "RETENTION_GUARD_RIGHT",
                "clearance",
                "CANDIDATE_OPEN",
                "RETENTION_GUARDS_V2",
                False,
                "Latest final guard pose retains approximately 2.46221445 mm yoke clearance; guard attachment remains open.",
            ),
        )
    )

    motions = (
        ServiceMotion(
            "RIGHT_QUICK_RELEASE_PULL",
            "QUICK_RELEASE_RIGHT",
            "CANDIDATE_CONTINUOUS",
            "QUICK_RELEASE_V1",
            True,
            7.3,
            39,
            False,
            "Exact donor latch withdrawal reference only; it cannot establish whole-head removal or physical release force/time.",
        ),
        ServiceMotion(
            "RIGHT_QUICK_RELEASE_GUARD_FACTORY_INSTALL",
            "QUICK_RELEASE_GUARD_RIGHT",
            "CANDIDATE_CONTINUOUS",
            "RETENTION_GUARDS_V2",
            True,
            35.0,
            2,
            False,
            "Exact guard factory sweep remains clear of the yoke and emergency pull corridor on latest Cell 8 head.",
            interference_mm3=0.0,
        ),
        ServiceMotion(
            "LEFT_RETENTION_GUARD_OUTBOARD_FACTORY_INSTALL",
            "RETENTION_GUARD_LEFT",
            "CANDIDATE_CONTINUOUS",
            "RETENTION_GUARDS_V2",
            True,
            22.0,
            2,
            False,
            "Exact outboard-to-final X sweep supersedes the old inboard path that intersected yoke and protected reservations.",
            interference_mm3=0.0,
        ),
        ServiceMotion(
            "RIGHT_RETENTION_GUARD_OUTBOARD_FACTORY_INSTALL",
            "RETENTION_GUARD_RIGHT",
            "CANDIDATE_CONTINUOUS",
            "RETENTION_GUARDS_V2",
            True,
            22.0,
            2,
            False,
            "Exact outboard-to-final X sweep supersedes the old inboard path that intersected yoke and protected reservations.",
            interference_mm3=0.0,
        ),
        ServiceMotion(
            "RETENTION_CARRIER_SEPARATION_REASSEMBLY",
            "RETENTION_CARRIER_RIGHT",
            "UNRESOLVED",
            None,
            False,
            None,
            None,
            False,
            "Nonteleporting integrated retention separation/reassembly remains open beyond the local pin-removal sequences.",
            blocking_source_ids=("RETENTION_V2", "SERVICE_INVENTORY_V1"),
        ),
        ServiceMotion(
            "WHOLE_HEAD_REMOVAL",
            "CROWN_SUPPORT",
            "UNRESOLVED",
            None,
            False,
            None,
            None,
            True,
            "No integrated post-release continuous whole-head removal sweep exists. One-hand wet removal, <=2 s release and 5-12 N release force remain physical gates.",
            blocking_source_ids=(
                "RETENTION_V2",
                "QUICK_RELEASE_V1",
                "SERVICE_INVENTORY_V1",
            ),
        ),
    )
    return MechanicalInterfaceGraph(_sources(), tuple(nodes), tuple(interfaces), motions)


def manifest_json(graph: MechanicalInterfaceGraph | None = None) -> str:
    graph = build_mechanical_interface_graph() if graph is None else graph
    return json.dumps(graph.manifest(), sort_keys=True, indent=2, allow_nan=False) + "\n"


def source_binding_map(
    graph: MechanicalInterfaceGraph | None = None,
) -> dict[str, SourceBinding]:
    graph = build_mechanical_interface_graph() if graph is None else graph
    return {item.source_id: item for item in graph.sources}


def unresolved_interface_ids(
    graph: MechanicalInterfaceGraph | None = None,
) -> tuple[str, ...]:
    graph = build_mechanical_interface_graph() if graph is None else graph
    return tuple(
        item.interface_id
        for item in graph.interfaces
        if item.status != "CANDIDATE_REALIZED"
    )


def candidate_source_heads(
    graph: MechanicalInterfaceGraph | None = None,
) -> tuple[tuple[int, str], ...]:
    graph = build_mechanical_interface_graph() if graph is None else graph
    return tuple(
        (item.pr_number, item.head_sha)
        for item in graph.sources
        if item.status == "CANDIDATE_PR" and item.pr_number is not None
    )


def assert_local_source_bindings(
    repo_root: str | Path,
    graph: MechanicalInterfaceGraph | None = None,
) -> None:
    graph = build_mechanical_interface_graph() if graph is None else graph
    root = Path(repo_root)
    for source in graph.sources:
        if not source.local_file_binding:
            continue
        path = root / source.path
        if not path.is_file():
            raise MechanicalInterfaceGraphError(
                f"bound local source is missing: {source.path}"
            )
        observed = _git_blob_sha(path)
        if observed != source.blob_sha:
            raise MechanicalInterfaceGraphError(
                f"bound local source moved at {source.path}; expected {source.blob_sha}, got {observed}"
            )
