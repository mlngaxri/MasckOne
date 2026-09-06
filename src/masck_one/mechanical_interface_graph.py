from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import re

SCHEMA = "MASCK_ONE_MECHANICAL_INTERFACE_GRAPH_V2"
SOURCE_MAIN_SHA = "5a3a07fe4425d55520ed4468c6c71f5bc0a2f45e"
SOURCE_MAIN_TREE_SHA = "9402021a9335bb64c360548649d2cc6a7a1b0fad"
AUTHORITY_REVISION = "2026-08-30-R1"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
UNITS = "mm"
SUPERSEDED_RETENTION_PRS = (83, 87, 89)

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
SOURCE_STATUSES = frozenset({"RELEASED_MAIN", "CANDIDATE_PR", "UNRESOLVED"})
INTERFACE_STATUSES = frozenset({"CANDIDATE_REALIZED", "CANDIDATE_OPEN", "UNRESOLVED"})
MOTION_STATUSES = frozenset({"CANDIDATE_CONTINUOUS", "UNRESOLVED"})
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

    def __post_init__(self) -> None:
        _nonblank(self.source_id, "source id")
        _nonblank(self.path, "source path")
        _nonblank(self.symbol, "source symbol")
        _nonblank(self.note, "source note")
        _sha40(self.blob_sha, "source blob SHA")
        _sha40(self.head_sha, "source head SHA")
        if self.status not in SOURCE_STATUSES:
            raise MechanicalInterfaceGraphError(f"unknown source status {self.status}")
        if self.status == "CANDIDATE_PR":
            if (
                isinstance(self.pr_number, bool)
                or not isinstance(self.pr_number, int)
                or self.pr_number <= 0
            ):
                raise MechanicalInterfaceGraphError(
                    "candidate source requires a positive PR number"
                )
        elif self.pr_number is not None:
            raise MechanicalInterfaceGraphError(
                "only candidate PR sources may carry a PR number"
            )

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
            raise MechanicalInterfaceGraphError(
                f"unknown interface status {self.status}"
            )
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

    def manifest(self) -> dict[str, object]:
        return {
            "interface_id": self.interface_id,
            "from_node": self.from_node,
            "to_node": self.to_node,
            "semantics": self.semantics,
            "status": self.status,
            "source_id": self.source_id,
            "positive_attachment": self.positive_attachment,
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
                    "candidate continuous reference motion cannot claim unresolved blockers"
                )
        else:
            if self.source_id is not None or self.travel_mm is not None or self.sample_count is not None:
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


@dataclass(frozen=True, slots=True)
class MechanicalInterfaceGraph:
    sources: tuple[SourceBinding, ...]
    nodes: tuple[MechanicalNode, ...]
    interfaces: tuple[MechanicalInterface, ...]
    service_motions: tuple[ServiceMotion, ...]
    whole_mechanical_package_closed: bool = False

    def __post_init__(self) -> None:
        if type(self.whole_mechanical_package_closed) is not bool or self.whole_mechanical_package_closed:
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
        required_sources = {
            "FRAME_V1",
            "CARRIER_V1",
            "ACTUATOR_DONOR_AUDIT_V1",
            "RETENTION_V2",
            "OCCIPITAL_YOKES_V1",
            "QUICK_RELEASE_V1",
            "RETENTION_GUARDS_V1",
        }
        if not required_sources.issubset(source_set):
            raise MechanicalInterfaceGraphError("current Cells 6-8 and quick-release source set is incomplete")
        if any(node.source_id not in source_set for node in self.nodes):
            raise MechanicalInterfaceGraphError("node references an unknown source")
        for interface in self.interfaces:
            if interface.source_id not in source_set:
                raise MechanicalInterfaceGraphError("interface references an unknown source")
            if interface.from_node not in node_set or interface.to_node not in node_set:
                raise MechanicalInterfaceGraphError("interface endpoint is not a graph node")
        for motion in self.service_motions:
            if motion.moving_node not in node_set:
                raise MechanicalInterfaceGraphError("motion moving node is not a graph node")
            if motion.source_id is not None and motion.source_id not in source_set:
                raise MechanicalInterfaceGraphError("motion references an unknown source")
            if any(item not in source_set for item in motion.blocking_source_ids):
                raise MechanicalInterfaceGraphError("motion blocker references an unknown source")

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

        cross_boundary_prefixes = (
            "FRAME_TO_CARRIER_",
            "FRAME_TO_RETENTION_",
            "RETENTION_TO_QUICK_RELEASE",
        )
        if any(
            edge.positive_attachment
            for edge in self.interfaces
            if edge.interface_id.startswith(cross_boundary_prefixes)
        ):
            raise MechanicalInterfaceGraphError(
                "unresolved cross-boundary joins cannot become positive attachments"
            )

        whole_removal = [
            item for item in self.service_motions if item.motion_id == "WHOLE_HEAD_REMOVAL"
        ]
        if len(whole_removal) != 1 or whole_removal[0].status != "UNRESOLVED":
            raise MechanicalInterfaceGraphError("whole-head removal must remain unresolved")

        for side in ("LEFT", "RIGHT"):
            factory = [
                item
                for item in self.service_motions
                if item.motion_id == f"{side}_RETENTION_GUARD_FACTORY_INSTALL"
            ]
            if len(factory) != 1 or factory[0].status != "UNRESOLVED":
                raise MechanicalInterfaceGraphError(
                    "bilateral retention-guard factory install must remain unresolved"
                )
            if set(factory[0].blocking_source_ids) != {
                "RETENTION_GUARDS_V1",
                "OCCIPITAL_YOKES_V1",
            }:
                raise MechanicalInterfaceGraphError(
                    "retention-guard factory blocker must bind guard and current yoke sources"
                )
            if factory[0].interference_mm3 is None or factory[0].interference_mm3 <= 0.0:
                raise MechanicalInterfaceGraphError(
                    "retention-guard factory blocker must preserve measured sweep interference"
                )

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
            "source_main_tree_sha": SOURCE_MAIN_TREE_SHA,
            "authority_revision": AUTHORITY_REVISION,
            "frame_id": WORLD_FRAME_ID,
            "units": UNITS,
            "superseded_retention_prs": list(SUPERSEDED_RETENTION_PRS),
            "canonical_registry_status": "CANDIDATE_PR_BINDING_NOT_RELEASE_AUTHORITY",
            "sources": [item.manifest() for item in self.sources],
            "nodes": [item.manifest() for item in self.nodes],
            "interfaces": [item.manifest() for item in self.interfaces],
            "service_motions": [item.manifest() for item in self.service_motions],
            "whole_mechanical_package_closed": self.whole_mechanical_package_closed,
            "evidence_status": (
                "DIGITAL_SOURCE_BOUND_INTERFACE_KINEMATIC_AND_SWEPT_VOLUME_CLASSIFICATION_ONLY_"
                "NOT_PHYSICAL_FIT_FORCE_SAFETY_STRENGTH_DURABILITY_OR_SERVICE_VALIDATION"
            ),
        }
        if include_sha:
            result["graph_sha256"] = self.graph_sha256
        return result


def _sources() -> tuple[SourceBinding, ...]:
    return (
        SourceBinding(
            "REGISTRY_V2",
            "CANDIDATE_PR",
            "src/masck_one/component_registry.py",
            "CanonicalComponentRegistry",
            "d68a109c93532bfa424a574fdbd899230ae20d0b",
            "90d20231710a24bbf02ba0c9ae52ef8b37f0ce73",
            120,
            "Cell 1 canonical registry remains pre-PR121 candidate evidence and is not release authority.",
        ),
        SourceBinding(
            "FRAME_V1",
            "CANDIDATE_PR",
            "src/masck_one/structural_frame_realization.py",
            "StructuralFrameRealization",
            "0ea2ada736825fe1a0e06491d16690ae98cfccde",
            "34273de3bd86294080e51873c212e988b4a966f4",
            117,
            "Cell 6 reaction-loop B-rep is current specialist geometry; frame-shell, actuator and retention positive counterparts remain open.",
        ),
        SourceBinding(
            "CARRIER_V1",
            "CANDIDATE_PR",
            "src/masck_one/actuator_carriers.py",
            "ActuatorCarrierPackage",
            "9c613f40ed1b8cb43c3a40bb945d53084a71d121",
            "37e03df4b6abbd222422c8bfd4e70b03a4e5ae07",
            118,
            "Cell 7 local split carrier capture is positive locally, but world_mount_eligible is false and reaction/coupling/final stops are absent.",
        ),
        SourceBinding(
            "ACTUATOR_DONOR_AUDIT_V1",
            "CANDIDATE_PR",
            "src/masck_one/legacy_actuator_donor_audit.py",
            "build_legacy_actuator_donor_audit",
            "d23b574ed0048aba76f64e63471a3327fde2fd5b",
            "dfdd8468731ae7e58e0aa3f7910662fbbef1ba60",
            127,
            "Post-PR121 Cell 7 audit rejects legacy collar/shoe/frame overlap as attachment and rejects donor world placements; it contributes semantics only, not current mount geometry.",
        ),
        SourceBinding(
            "RETENTION_V2",
            "CANDIDATE_PR",
            "src/masck_one/retention_load_path.py",
            "RetentionLoadPathPackage",
            "9647405b36642105c929a3fdd0617d03bfe68c98",
            "1137401b7f25320c4955a8d35cc0f128b6558ab3",
            92,
            "Cell 3 retention lineage has been reconstructed with current post-PR121 main ancestry; retained load-path B-rep blob is unchanged and crown/front-frame counterparts remain open.",
        ),
        SourceBinding(
            "OCCIPITAL_YOKES_V1",
            "CANDIDATE_PR",
            "src/masck_one/occipital_stabilizer.py",
            "OccipitalStabilizer",
            "6d35c96bc65bb1e0e877deadc65481bf44954b4e",
            "25686766238b66ecf900009042d721c08e042592",
            123,
            "Cell 8 current yoke candidate preserves the positive yoke geometry and supplies the measured bilateral guard-sweep interference; frame-side counterpart remains unrealized.",
        ),
        SourceBinding(
            "QUICK_RELEASE_V1",
            "CANDIDATE_PR",
            "src/masck_one/right_quick_release_latch.py",
            "QuickReleaseLatchResult",
            "11d90a75eb108c53f5a1621abdace7271bf5cac5",
            "0b5a619c6cea344038b0e8b8cc10a50e3d193390",
            71,
            "Strong stale-base donor lineage for the exact 7.3 mm continuous pull and split guide only; no stale promotion claim is inherited.",
        ),
        SourceBinding(
            "RETENTION_GUARDS_V1",
            "CANDIDATE_PR",
            "src/masck_one/retention_hazard_guards.py",
            "RetentionHazardGuardPackage",
            "b497e9154067cef9ee24da4d421ea6c7861c348e",
            "fb586cc1ea1cde92526417593f9e5aa990d2ae4f",
            109,
            "Final guard B-reps clear the yokes, but each published bilateral pure-X factory sweep intersects its current yoke by about 39.840676 mm3.",
        ),
        SourceBinding(
            "SERVICE_INVENTORY_V1",
            "CANDIDATE_PR",
            "src/masck_one/assembly_service_inventory.py",
            "AssemblyServiceInventory",
            "e44c8ca12d7b163a5a3fb54fbce7ca2c16d0fc5c",
            "630cc19497661ae834032eb8ea06e28dfd6100b7",
            114,
            "Service inventory is stale candidate evidence only; no released nonteleporting whole-head removal producer exists.",
        ),
    )


def build_mechanical_interface_graph() -> MechanicalInterfaceGraph:
    nodes: list[MechanicalNode] = [
        MechanicalNode(
            "FRAME_REACTION_LOOP",
            "frame_structure",
            None,
            "FRAME_V1",
            "MASCK_ONE-FRAME-MEMBER-PERIMETER-REACTION-LOOP-V1",
            "physical_material_candidate",
        ),
        MechanicalNode(
            "RETENTION_LOAD_PATH",
            "retention_halo",
            None,
            "RETENTION_V2",
            "RETENTION_LOAD_PATH_V2",
            "physical_material_candidate",
        ),
        MechanicalNode(
            "QUICK_RELEASE_RIGHT",
            "quick_release",
            None,
            "QUICK_RELEASE_V1",
            "QR_BODY_RIGHT+QR_SLIDER_RIGHT",
            "physical_material_candidate",
        ),
        MechanicalNode(
            "QUICK_RELEASE_GUARD_RIGHT",
            "quick_release",
            None,
            "RETENTION_GUARDS_V1",
            "RETENTION_QUICK_RELEASE_GUARD_RIGHT",
            "physical_material_candidate",
        ),
        MechanicalNode(
            "RETENTION_GUARD_LEFT",
            "retention_halo",
            None,
            "RETENTION_GUARDS_V1",
            "RETENTION_OCCIPITAL_GUARD_LEFT",
            "physical_material_candidate",
        ),
        MechanicalNode(
            "RETENTION_GUARD_RIGHT",
            "retention_halo",
            None,
            "RETENTION_GUARDS_V1",
            "RETENTION_OCCIPITAL_GUARD_RIGHT",
            "physical_material_candidate",
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
        interfaces.append(
            MechanicalInterface(
                f"CARRIER_LOCAL_CLOSURE_ZONE_{index}",
                carrier,
                carrier,
                "positive_attachment",
                "CANDIDATE_REALIZED",
                "CARRIER_V1",
                True,
                "Two headed pins and retained clips positively close the local split carrier template.",
            )
        )
        interfaces.append(
            MechanicalInterface(
                f"FRAME_TO_CARRIER_ZONE_{index}",
                "FRAME_REACTION_LOOP",
                carrier,
                "reference_only",
                "CANDIDATE_OPEN",
                "CARRIER_V1",
                False,
                "World mount is protected-envelope conflicted and structural_frame_attachment_realized is false; Cell 7 donor audit forbids filling this gap with legacy overlap geometry.",
            )
        )

    interfaces.extend(
        (
            MechanicalInterface(
                "FRAME_TO_RETENTION_CROWN",
                "FRAME_REACTION_LOOP",
                "RETENTION_LOAD_PATH",
                "reference_only",
                "CANDIDATE_OPEN",
                "RETENTION_V2",
                False,
                "Crown handoff lug exists but the Cell 6 frame mating counterpart is absent.",
            ),
            MechanicalInterface(
                "FRAME_TO_RETENTION_FACIAL_REACTION",
                "FRAME_REACTION_LOOP",
                "RETENTION_LOAD_PATH",
                "reference_only",
                "CANDIDATE_OPEN",
                "RETENTION_V2",
                False,
                "Facial-reaction handoff exists but the front-frame mating counterpart is absent.",
            ),
            MechanicalInterface(
                "RETENTION_TO_QUICK_RELEASE",
                "RETENTION_LOAD_PATH",
                "QUICK_RELEASE_RIGHT",
                "reference_only",
                "CANDIDATE_OPEN",
                "QUICK_RELEASE_V1",
                False,
                "Exact quick-release donor motion is preserved, but an integrated positive retention counterpart is not current-source realized.",
            ),
            MechanicalInterface(
                "QUICK_RELEASE_TO_GUARD",
                "QUICK_RELEASE_RIGHT",
                "QUICK_RELEASE_GUARD_RIGHT",
                "clearance",
                "CANDIDATE_OPEN",
                "RETENTION_GUARDS_V1",
                False,
                "Guard preserves the emergency pull corridor but has no realized positive attachment counterpart.",
            ),
            MechanicalInterface(
                "RETENTION_TO_LEFT_GUARD",
                "RETENTION_LOAD_PATH",
                "RETENTION_GUARD_LEFT",
                "clearance",
                "CANDIDATE_OPEN",
                "OCCIPITAL_YOKES_V1",
                False,
                "Final-position yoke-to-guard clearance is about 2.46221445 mm; attachment and factory trajectory remain open.",
            ),
            MechanicalInterface(
                "RETENTION_TO_RIGHT_GUARD",
                "RETENTION_LOAD_PATH",
                "RETENTION_GUARD_RIGHT",
                "clearance",
                "CANDIDATE_OPEN",
                "OCCIPITAL_YOKES_V1",
                False,
                "Final-position yoke-to-guard clearance is about 2.46221445 mm; attachment and factory trajectory remain open.",
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
            "Exact candidate latch withdrawal motion only; it does not establish whole-head removal or physical release force/time.",
        ),
        ServiceMotion(
            "RIGHT_QUICK_RELEASE_GUARD_FACTORY_INSTALL",
            "QUICK_RELEASE_GUARD_RIGHT",
            "CANDIDATE_CONTINUOUS",
            "RETENTION_GUARDS_V1",
            True,
            35.0,
            2,
            False,
            "Published right quick-release-guard pure-X reference sweep remains about 3.0 mm clear of the current yoke reconstruction.",
            interference_mm3=0.0,
        ),
        ServiceMotion(
            "LEFT_RETENTION_GUARD_PURE_X_SWEEP_REFERENCE",
            "RETENTION_GUARD_LEFT",
            "CANDIDATE_CONTINUOUS",
            "RETENTION_GUARDS_V1",
            True,
            22.0,
            2,
            False,
            "Published exact pure-X sweep geometry only; it is not a collision-free integrated factory path.",
            interference_mm3=39.840676,
        ),
        ServiceMotion(
            "RIGHT_RETENTION_GUARD_PURE_X_SWEEP_REFERENCE",
            "RETENTION_GUARD_RIGHT",
            "CANDIDATE_CONTINUOUS",
            "RETENTION_GUARDS_V1",
            True,
            22.0,
            2,
            False,
            "Published exact pure-X sweep geometry only; it is not a collision-free integrated factory path.",
            interference_mm3=39.840676,
        ),
        ServiceMotion(
            "LEFT_RETENTION_GUARD_FACTORY_INSTALL",
            "RETENTION_GUARD_LEFT",
            "UNRESOLVED",
            None,
            False,
            None,
            None,
            False,
            "Factory order or an alternate nonteleporting trajectory is unresolved because the published pure-X sweep intersects the current left yoke.",
            blocking_source_ids=("RETENTION_GUARDS_V1", "OCCIPITAL_YOKES_V1"),
            interference_mm3=39.840676,
        ),
        ServiceMotion(
            "RIGHT_RETENTION_GUARD_FACTORY_INSTALL",
            "RETENTION_GUARD_RIGHT",
            "UNRESOLVED",
            None,
            False,
            None,
            None,
            False,
            "Factory order or an alternate nonteleporting trajectory is unresolved because the published pure-X sweep intersects the current right yoke.",
            blocking_source_ids=("RETENTION_GUARDS_V1", "OCCIPITAL_YOKES_V1"),
            interference_mm3=39.840676,
        ),
        ServiceMotion(
            "RETENTION_CARRIER_SEPARATION_REASSEMBLY",
            "RETENTION_LOAD_PATH",
            "UNRESOLVED",
            None,
            False,
            None,
            None,
            False,
            "Nonteleporting separation/reassembly after pin withdrawal remains an explicit Cell 3 service blocker.",
            blocking_source_ids=("RETENTION_V2", "SERVICE_INVENTORY_V1"),
        ),
        ServiceMotion(
            "WHOLE_HEAD_REMOVAL",
            "RETENTION_LOAD_PATH",
            "UNRESOLVED",
            None,
            False,
            None,
            None,
            True,
            "No released integrated post-release whole-head removal sweep exists; physical one-hand wet removal remains gated.",
            blocking_source_ids=("RETENTION_V2", "SERVICE_INVENTORY_V1"),
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
        item.interface_id for item in graph.interfaces if item.status != "CANDIDATE_REALIZED"
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
