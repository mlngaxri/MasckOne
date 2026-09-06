from __future__ import annotations

from dataclasses import dataclass
import math

from .mechanical_interface_graph import WORLD_FRAME_ID, build_mechanical_interface_graph

SCHEMA = "MASCK_ONE_MECHANICAL_INTERFACE_TRANSFORMS_V1"
LOCAL_ACTUATOR_FRAME_ID = "MASCK_ONE_ACTUATOR_PACKAGE_LOCAL_MM"
IDENTITY_TRANSFORM = (
    1.0,
    0.0,
    0.0,
    0.0,
    0.0,
    1.0,
    0.0,
    0.0,
    0.0,
    0.0,
    1.0,
    0.0,
    0.0,
    0.0,
    0.0,
    1.0,
)
RESOLVED = "IDENTITY_WORLD_TRANSFORM_RESOLVED"
UNRESOLVED = "UNRESOLVED_WORLD_MOUNT_TRANSFORM"


class MechanicalTransformError(ValueError):
    pass


def _nonblank(value: object, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise MechanicalTransformError(f"{label} must be exact nonblank text")
    return value


def _matrix(values: object) -> tuple[float, ...]:
    if not isinstance(values, tuple) or len(values) != 16:
        raise MechanicalTransformError("resolved transform must be a 4x4 row-major tuple")
    result: list[float] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise MechanicalTransformError("transform entries must be real numerics")
        number = float(value)
        if not math.isfinite(number):
            raise MechanicalTransformError("transform entries must be finite")
        result.append(number)
    return tuple(result)


@dataclass(frozen=True, slots=True)
class NodeTransformBinding:
    node_id: str
    source_schema_or_component_id: str
    source_frame_id: str
    target_frame_id: str
    status: str
    transform_row_major: tuple[float, ...] | None
    note: str

    def __post_init__(self) -> None:
        _nonblank(self.node_id, "node id")
        _nonblank(self.source_schema_or_component_id, "source schema/component id")
        _nonblank(self.source_frame_id, "source frame id")
        _nonblank(self.target_frame_id, "target frame id")
        _nonblank(self.note, "transform note")
        if self.target_frame_id != WORLD_FRAME_ID:
            raise MechanicalTransformError("mechanical graph target frame must remain canonical world")
        if self.status == RESOLVED:
            matrix = _matrix(self.transform_row_major)
            if self.source_frame_id != WORLD_FRAME_ID or matrix != IDENTITY_TRANSFORM:
                raise MechanicalTransformError(
                    "resolved world-authored mechanical nodes must use exact identity transform"
                )
        elif self.status == UNRESOLVED:
            if self.transform_row_major is not None:
                raise MechanicalTransformError(
                    "unresolved world mount cannot carry a fabricated transform matrix"
                )
            if self.source_frame_id == WORLD_FRAME_ID:
                raise MechanicalTransformError(
                    "world-authored node cannot be marked unresolved without a different native frame"
                )
        else:
            raise MechanicalTransformError(f"unknown transform status {self.status}")

    def manifest(self) -> dict[str, object]:
        return {
            "node_id": self.node_id,
            "source_schema_or_component_id": self.source_schema_or_component_id,
            "source_frame_id": self.source_frame_id,
            "target_frame_id": self.target_frame_id,
            "status": self.status,
            "transform_row_major": (
                list(self.transform_row_major) if self.transform_row_major is not None else None
            ),
            "note": self.note,
        }


def build_mechanical_transform_bindings() -> tuple[NodeTransformBinding, ...]:
    graph = build_mechanical_interface_graph()
    bindings: list[NodeTransformBinding] = []
    for node in graph.nodes:
        if node.node_id.startswith("ACTUATOR_CARRIER_ZONE_"):
            bindings.append(
                NodeTransformBinding(
                    node.node_id,
                    "MASCK_ONE_CELL7_ACTUATOR_CARRIER_TEMPLATE_V1",
                    LOCAL_ACTUATOR_FRAME_ID,
                    WORLD_FRAME_ID,
                    UNRESOLVED,
                    None,
                    "Cell 7 local carrier B-rep has no protected-clear accepted world mount; source reference placements are collision-review references only.",
                )
            )
            continue
        source_identity = {
            "FRAME_REACTION_LOOP": "MASCK_ONE-FRAME-MEMBER-PERIMETER-REACTION-LOOP-V1",
            "RETENTION_LOAD_PATH": "MASCK_ONE_CELL3_RETENTION_LOAD_PATH_V1",
            "QUICK_RELEASE_RIGHT": "MASCK_ONE_CELL3_RIGHT_QUICK_RELEASE_LATCH_V3",
            "QUICK_RELEASE_GUARD_RIGHT": "RETENTION_QUICK_RELEASE_GUARD_RIGHT",
            "RETENTION_GUARD_LEFT": "RETENTION_OCCIPITAL_GUARD_LEFT",
            "RETENTION_GUARD_RIGHT": "RETENTION_OCCIPITAL_GUARD_RIGHT",
        }.get(node.node_id)
        if source_identity is None:
            raise MechanicalTransformError(
                f"mechanical graph node {node.node_id} lacks an explicit native-frame binding"
            )
        bindings.append(
            NodeTransformBinding(
                node.node_id,
                source_identity,
                WORLD_FRAME_ID,
                WORLD_FRAME_ID,
                RESOLVED,
                IDENTITY_TRANSFORM,
                "Producer geometry is authored directly in MASCK_ONE_AUTHORITY_WORLD_MM; no implicit axis, sign, unit or origin transform is permitted.",
            )
        )

    graph_ids = tuple(node.node_id for node in graph.nodes)
    binding_ids = tuple(binding.node_id for binding in bindings)
    if binding_ids != graph_ids or len(binding_ids) != len(set(binding_ids)):
        raise MechanicalTransformError(
            "mechanical transform ledger must cover every graph node exactly once in graph order"
        )
    return tuple(bindings)


def transform_manifest() -> dict[str, object]:
    bindings = build_mechanical_transform_bindings()
    return {
        "schema": SCHEMA,
        "target_frame_id": WORLD_FRAME_ID,
        "bindings": [binding.manifest() for binding in bindings],
        "unresolved_world_mount_nodes": [
            binding.node_id for binding in bindings if binding.status == UNRESOLVED
        ],
    }
