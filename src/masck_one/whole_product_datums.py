"""Cell 17 whole-product datum hierarchy bound to released geometry.

The hierarchy makes coordinate-frame identity and transforms explicit without
promoting reference/package geometry into manufacturing datums or claiming
process/metrology capability.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1, sha256
import json
import math
from pathlib import Path
import re

from .actuator_frames import ZONE_IDS
from .authority import Authority, load_authority
from .model import MasckOneModel, build_model
from .spatial import Matrix3, RigidTransform, Vector3, CanonicalDatums
from .structural_frame import (
    DATUM_CENTER,
    DATUM_INFERIOR,
    DATUM_LEFT,
    DATUM_RIGHT,
    DATUM_SUPERIOR,
)

SCHEMA = "MASCK_ONE_CELL17_WHOLE_PRODUCT_DATUM_HIERARCHY_V1"
SOURCE_MAIN_SHA = "afe29ff78419b6625dca5594974b6351f6f80e1b"
AUTHORITY_REVISION = "2026-08-30-R1"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
LEGACY_GLOBAL_FRAME_ID = "MASCK_ONE_GLOBAL"

SHELL_PRIMARY_FRAME_ID = "MASCK_ONE_LOCAL_SHELL_PRIMARY"
STRUCTURAL_FRAME_REFERENCE_ID = "MASCK_ONE_LOCAL_STRUCTURAL_FRAME_REFERENCE"
STRUCTURAL_FRAME_DATUM_IDS = (
    DATUM_CENTER,
    DATUM_SUPERIOR,
    DATUM_INFERIOR,
    DATUM_LEFT,
    DATUM_RIGHT,
)
WATER_RESERVOIR_PACKAGE_FRAME_ID = "MASCK_ONE_LOCAL_WATER_RESERVOIR_PACKAGE"
WATER_RESERVOIR_ROOT_FRAME_ID = "MASCK_ONE_LOCAL_WATER_RESERVOIR_ROOT"
WASTE_CARTRIDGE_PACKAGE_FRAME_ID = "MASCK_ONE_LOCAL_WASTE_CARTRIDGE_PACKAGE"
WASTE_CARTRIDGE_ROOT_FRAME_ID = "MASCK_ONE_LOCAL_WASTE_CARTRIDGE_ROOT"
BATTERY_PACKAGE_FRAME_ID = "MASCK_ONE_LOCAL_BATTERY_REFERENCE_PACKAGE"
RETENTION_ROOT_FRAME_ID = "MASCK_ONE_LOCAL_RETENTION_ROOT"
DRY_SIDE_ROOT_FRAME_ID = "MASCK_ONE_LOCAL_DRY_SIDE_ROOT"
HMI_ROOT_FRAME_ID = "MASCK_ONE_LOCAL_HMI_ROOT"
THERMAL_ROOT_FRAME_ID = "MASCK_ONE_LOCAL_THERMAL_ROOT"
CLEANSER_ROOT_FRAME_ID = "MASCK_ONE_LOCAL_CLEANSER_ROOT"

ACTUATOR_FRAME_IDS = tuple(f"MASCK_ONE_LOCAL_{zone_id}" for zone_id in ZONE_IDS)

EVIDENCE_STATUS = (
    "DIGITAL_DATUM_HIERARCHY_ONLY_NOT_MANUFACTURING_PROCESS_CAPABILITY_"
    "METROLOGY_CAPABILITY_FIT_ASSEMBLY_PERFORMANCE_OR_PHYSICAL_VALIDATION"
)

SOURCE_GIT_BLOB_IDENTITIES: tuple[tuple[str, str], ...] = (
    ("config/masck_one_authority.yaml", "2608dda483b995539de422290371c219668a1527"),
    ("src/masck_one/authority.py", "6866e3a428dab8b32b5a1d9e58da78b8f5aa1aa2"),
    ("src/masck_one/spatial.py", "8c1106b523fef5111009cc56236a53e3bc5ee10e"),
    ("src/masck_one/structural_frame.py", "bda5ba87d232c0e6a22e200975a80414a10c9a83"),
    ("src/masck_one/actuator_frames.py", "4c2013f994bdc9e084fe227eb5e166f973500ebb"),
    ("src/masck_one/model.py", "9e7fa6c71ac28cc45ebb502444bf6c0ea49f7894"),
    ("src/masck_one/water_reservoir.py", "6c14a37d07855550f0bd502e8308ed46682bc19c"),
    ("src/masck_one/cleanser_storage.py", "5e087ca8b05da8352ad4800b2ef8280ea8ddcf29"),
    ("src/masck_one/waste_cartridge.py", "9dc0fe8a0ed92083c68406da3993e57e767e2483"),
)
_SOURCE_BLOB_BY_PATH = dict(SOURCE_GIT_BLOB_IDENTITIES)

DATUM_CLASS_VALUES = (
    "AUTHORITY_WORLD",
    "LEGACY_IDENTITY_ALIAS",
    "PRIMARY_PART_REFERENCE",
    "STRUCTURAL_REFERENCE",
    "PACKAGE_REFERENCE",
    "SUBSYSTEM_LOCAL",
)
TRANSFORM_STATUS_VALUES = ("ROOT", "RESOLVED_IDENTITY", "RESOLVED_RIGID", "UNRESOLVED")
MANUFACTURING_STATUS_VALUES = (
    "CANONICAL_SYSTEM_REFERENCE_NOT_PART_DATUM",
    "DIGITAL_PRIMARY_REFERENCE_NOT_QUALIFIED_MANUFACTURING_DATUM",
    "REFERENCE_ONLY_NOT_MANUFACTURING_DATUM",
    "UNRESOLVED_NOT_QUALIFIED_MANUFACTURING_DATUM",
)
GEOMETRY_ROLE_VALUES = (
    "COORDINATE_SYSTEM_REFERENCE",
    "PHYSICAL_MATERIAL_COORDINATE_REFERENCE",
    "STRUCTURAL_REFERENCE_WITH_UNRESOLVED_3D_DATUM_QUALIFICATION",
    "PACKAGE_REFERENCE_ONLY",
    "NO_RELEASED_PLACEMENT_GEOMETRY",
)

_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_ID = re.compile(r"^[A-Z][A-Z0-9_-]{2,127}$")
_REPO_ROOT = Path(__file__).resolve().parents[2]


class DatumHierarchyError(ValueError):
    pass


def _exact_text(value: object, *, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise DatumHierarchyError(f"{label} must be exact nonblank text")
    return value


def _datum_id(value: object, *, label: str) -> str:
    text = _exact_text(value, label=label)
    if _ID.fullmatch(text) is None:
        raise DatumHierarchyError(f"{label} must be canonical uppercase identity text")
    return text


def _sha40(value: object, *, label: str) -> str:
    text = _exact_text(value, label=label)
    if _SHA40.fullmatch(text) is None:
        raise DatumHierarchyError(f"{label} must be a lowercase 40-character Git SHA")
    return text


def _finite(value: object, *, label: str) -> float:
    if type(value) not in (int, float):
        raise DatumHierarchyError(f"{label} must be an exact numeric scalar")
    result = float(value)
    if not math.isfinite(result):
        raise DatumHierarchyError(f"{label} must be finite")
    return 0.0 if result == 0.0 else result


def _partial_translation(
    value: object,
    *,
    label: str,
) -> tuple[float | None, float | None, float | None]:
    if type(value) is not tuple or len(value) != 3:
        raise DatumHierarchyError(f"{label} must be an exact XYZ tuple")
    result = tuple(
        None if item is None else _finite(item, label=f"{label} coordinate")
        for item in value
    )
    if all(item is None for item in result) or all(item is not None for item in result):
        raise DatumHierarchyError(f"{label} requires both known and unresolved coordinates")
    return result[0], result[1], result[2]


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def _require_source_files_current() -> None:
    for relative_path, expected in SOURCE_GIT_BLOB_IDENTITIES:
        path = _REPO_ROOT / relative_path
        if not path.is_file():
            raise DatumHierarchyError(f"datum-hierarchy source file is missing: {relative_path}")
        actual = _git_blob_sha(path)
        if actual != expected:
            raise DatumHierarchyError(
                f"datum-hierarchy source moved at {relative_path}; expected {expected}, got {actual}"
            )


def _transform_is_identity(transform: RigidTransform) -> bool:
    identity = Matrix3.identity()
    return transform.rotation.rows == identity.rows and transform.translation == Vector3(0.0, 0.0, 0.0)


def _transform_manifest(transform: RigidTransform) -> dict[str, object]:
    if type(transform) is not RigidTransform:
        raise DatumHierarchyError("transform must be exact RigidTransform")
    return {
        "rotation_rows": [list(row) for row in transform.rotation.rows],
        "translation_mm": list(transform.translation.as_tuple()),
        "length_unit": "mm",
    }


@dataclass(frozen=True, slots=True)
class DatumNode:
    datum_id: str
    parent_id: str | None
    datum_class: str
    producer_path: str | None
    producer_blob_sha: str | None
    source_locator: str
    transform_status: str
    local_to_parent: RigidTransform | None
    manufacturing_status: str
    geometry_role: str
    blocker: str | None = None
    partial_translation_mm: tuple[float | None, float | None, float | None] | None = None

    def __post_init__(self) -> None:
        _datum_id(self.datum_id, label="datum ID")
        if self.parent_id is not None:
            _datum_id(self.parent_id, label="datum parent ID")
            if self.parent_id == self.datum_id:
                raise DatumHierarchyError("datum cannot parent itself")
        if self.datum_class not in DATUM_CLASS_VALUES:
            raise DatumHierarchyError("unsupported datum class")
        if (self.producer_path is None) != (self.producer_blob_sha is None):
            raise DatumHierarchyError("producer path and blob SHA must be present or absent together")
        if self.producer_path is not None:
            _exact_text(self.producer_path, label="producer path")
            expected = _SOURCE_BLOB_BY_PATH.get(self.producer_path)
            if expected is None:
                raise DatumHierarchyError("producer path is not in the released source binding set")
            if _sha40(self.producer_blob_sha, label="producer blob SHA") != expected:
                raise DatumHierarchyError("producer blob SHA does not match released source binding")
        _exact_text(self.source_locator, label="source locator")
        if self.transform_status not in TRANSFORM_STATUS_VALUES:
            raise DatumHierarchyError("unsupported transform status")
        if self.manufacturing_status not in MANUFACTURING_STATUS_VALUES:
            raise DatumHierarchyError("unsupported manufacturing status")
        if self.geometry_role not in GEOMETRY_ROLE_VALUES:
            raise DatumHierarchyError("unsupported geometry role")
        partial = None
        if self.partial_translation_mm is not None:
            partial = _partial_translation(self.partial_translation_mm, label="partial datum translation")
            object.__setattr__(self, "partial_translation_mm", partial)
            if self.transform_status != "UNRESOLVED":
                raise DatumHierarchyError("partial datum translation is only valid for unresolved transforms")

        if self.transform_status == "ROOT":
            if self.parent_id is not None or self.local_to_parent is not None:
                raise DatumHierarchyError("root datum cannot have parent transform")
            if partial is not None:
                raise DatumHierarchyError("root datum cannot carry a partial translation")
        elif self.transform_status == "UNRESOLVED":
            if self.parent_id is None or self.local_to_parent is not None:
                raise DatumHierarchyError("unresolved datum requires parent and no numeric transform")
            _exact_text(self.blocker, label="unresolved datum blocker")
            if self.manufacturing_status != "UNRESOLVED_NOT_QUALIFIED_MANUFACTURING_DATUM":
                raise DatumHierarchyError("unresolved datum cannot imply manufacturing qualification")
        else:
            if self.parent_id is None or type(self.local_to_parent) is not RigidTransform:
                raise DatumHierarchyError("resolved datum requires parent and exact rigid transform")
            if self.blocker is not None:
                raise DatumHierarchyError("resolved datum cannot carry unresolved blocker")
            if partial is not None:
                raise DatumHierarchyError("resolved datum cannot carry a partial translation")
            if self.transform_status == "RESOLVED_IDENTITY" and not _transform_is_identity(self.local_to_parent):
                raise DatumHierarchyError("identity binding must carry exact identity transform")
            if self.transform_status == "RESOLVED_RIGID" and _transform_is_identity(self.local_to_parent):
                raise DatumHierarchyError("non-identity rigid binding cannot carry identity transform")

        if self.datum_class == "PACKAGE_REFERENCE":
            if self.manufacturing_status != "REFERENCE_ONLY_NOT_MANUFACTURING_DATUM":
                raise DatumHierarchyError("package reference cannot be promoted to a manufacturing datum")
            if self.geometry_role != "PACKAGE_REFERENCE_ONLY":
                raise DatumHierarchyError("package reference cannot be physical material")
        if self.geometry_role == "NO_RELEASED_PLACEMENT_GEOMETRY" and self.transform_status != "UNRESOLVED":
            raise DatumHierarchyError("datum without released geometry must remain unresolved")
        if self.geometry_role == "PHYSICAL_MATERIAL_COORDINATE_REFERENCE":
            if self.manufacturing_status != "DIGITAL_PRIMARY_REFERENCE_NOT_QUALIFIED_MANUFACTURING_DATUM":
                raise DatumHierarchyError("physical material coordinate reference is not a qualified manufacturing datum")

    def manifest(self) -> dict[str, object]:
        self.__post_init__()
        return {
            "datum_id": self.datum_id,
            "parent_id": self.parent_id,
            "datum_class": self.datum_class,
            "producer_path": self.producer_path,
            "producer_blob_sha": self.producer_blob_sha,
            "source_locator": self.source_locator,
            "transform_status": self.transform_status,
            "local_to_parent": None if self.local_to_parent is None else _transform_manifest(self.local_to_parent),
            "partial_translation_mm": None if self.partial_translation_mm is None else list(self.partial_translation_mm),
            "manufacturing_status": self.manufacturing_status,
            "geometry_role": self.geometry_role,
            "blocker": self.blocker,
        }


@dataclass(frozen=True, slots=True)
class WholeProductDatumHierarchy:
    source_main_sha: str
    authority_revision: str
    world_origin_xyz_mm: tuple[float, float, float]
    axis_positive: tuple[str, str, str]
    nodes: tuple[DatumNode, ...]
    physical_validation_eligible: bool = False
    evidence_status: str = EVIDENCE_STATUS

    def __post_init__(self) -> None:
        _sha40(self.source_main_sha, label="source main SHA")
        if self.source_main_sha != SOURCE_MAIN_SHA:
            raise DatumHierarchyError("datum hierarchy is not bound to the released source main")
        if _exact_text(self.authority_revision, label="authority revision") != AUTHORITY_REVISION:
            raise DatumHierarchyError("datum hierarchy authority revision is stale")
        if type(self.world_origin_xyz_mm) is not tuple or len(self.world_origin_xyz_mm) != 3:
            raise DatumHierarchyError("world origin must be an exact XYZ tuple")
        origin = tuple(_finite(value, label="world origin coordinate") for value in self.world_origin_xyz_mm)
        if origin != (0.0, 0.0, 0.0):
            raise DatumHierarchyError("authority world origin must remain exact zero")
        if self.axis_positive != ("wearer_right", "superior", "anterior"):
            raise DatumHierarchyError("authority world axis/sign convention drifted")
        if type(self.nodes) is not tuple or not self.nodes:
            raise DatumHierarchyError("datum hierarchy requires a non-empty exact node tuple")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise DatumHierarchyError("digital datum hierarchy cannot be physical-validation evidence")
        if self.evidence_status != EVIDENCE_STATUS:
            raise DatumHierarchyError("datum hierarchy evidence boundary drifted")

        ids = tuple(node.datum_id for node in self.nodes)
        if len(set(ids)) != len(ids):
            raise DatumHierarchyError("datum IDs must be unique")
        if ids[0] != WORLD_FRAME_ID:
            raise DatumHierarchyError("authority world must be the first/root datum")
        node_by_id = {node.datum_id: node for node in self.nodes}
        world = node_by_id[WORLD_FRAME_ID]
        if world.datum_class != "AUTHORITY_WORLD" or world.transform_status != "ROOT":
            raise DatumHierarchyError("authority world datum semantics drifted")
        for node in self.nodes[1:]:
            if node.parent_id not in node_by_id:
                raise DatumHierarchyError(f"datum {node.datum_id} has unknown parent")
        for node in self.nodes:
            seen: set[str] = set()
            current = node
            while current.parent_id is not None:
                if current.datum_id in seen:
                    raise DatumHierarchyError("datum hierarchy contains a cycle")
                seen.add(current.datum_id)
                current = node_by_id[current.parent_id]
            if current.datum_id != WORLD_FRAME_ID:
                raise DatumHierarchyError("every datum chain must terminate at authority world")

        legacy = node_by_id.get(LEGACY_GLOBAL_FRAME_ID)
        if legacy is None or legacy.parent_id != WORLD_FRAME_ID or legacy.transform_status != "RESOLVED_IDENTITY":
            raise DatumHierarchyError("legacy MASCK_ONE_GLOBAL alias must be explicit identity to authority world")

        shell = node_by_id.get(SHELL_PRIMARY_FRAME_ID)
        if shell is None or shell.parent_id != WORLD_FRAME_ID or shell.transform_status != "RESOLVED_IDENTITY":
            raise DatumHierarchyError("shell primary reference must be explicit identity to authority world")

        structural = node_by_id.get(STRUCTURAL_FRAME_REFERENCE_ID)
        if (
            structural is None
            or structural.parent_id != WORLD_FRAME_ID
            or structural.transform_status != "RESOLVED_IDENTITY"
            or structural.manufacturing_status != "UNRESOLVED_NOT_QUALIFIED_MANUFACTURING_DATUM"
        ):
            raise DatumHierarchyError("structural reference frame cannot imply resolved 3D manufacturing datum")
        structural_children = tuple(node_by_id.get(datum_id) for datum_id in STRUCTURAL_FRAME_DATUM_IDS)
        if any(node is None for node in structural_children):
            raise DatumHierarchyError("released structural XY datum set is incomplete")
        if any(
            node.parent_id != STRUCTURAL_FRAME_REFERENCE_ID
            or node.transform_status != "UNRESOLVED"
            or node.partial_translation_mm is None
            for node in structural_children
            if node is not None
        ):
            raise DatumHierarchyError("released structural XY datums must remain partial children of structural reference")

    @property
    def node_by_id(self) -> dict[str, DatumNode]:
        return {node.datum_id: node for node in self.nodes}

    def local_to_world_transform(self, datum_id: str) -> RigidTransform | None:
        current = self.node_by_id.get(_datum_id(datum_id, label="datum lookup ID"))
        if current is None:
            raise DatumHierarchyError(f"unknown datum ID {datum_id!r}")
        transform = RigidTransform.identity()
        while current.parent_id is not None:
            if current.local_to_parent is None:
                return None
            transform = transform.followed_by(current.local_to_parent)
            current = self.node_by_id[current.parent_id]
        return transform

    @property
    def hierarchy_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        self.__post_init__()
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "source_main_sha": self.source_main_sha,
            "authority_revision": self.authority_revision,
            "authority_world_frame_id": WORLD_FRAME_ID,
            "length_unit": "mm",
            "world_origin_xyz_mm": list(self.world_origin_xyz_mm),
            "axis_positive": list(self.axis_positive),
            "source_git_blobs": [
                {"path": path, "git_blob_sha": digest}
                for path, digest in SOURCE_GIT_BLOB_IDENTITIES
            ],
            "nodes": [node.manifest() for node in self.nodes],
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            payload["hierarchy_sha256"] = self.hierarchy_sha256
        return payload


def _component_center_mm(component: object) -> Vector3:
    try:
        center = component.solid.val().Center()
    except AttributeError as exc:
        raise DatumHierarchyError("package datum source must expose released B-rep center") from exc
    return Vector3(
        _finite(float(center.x), label="package center X"),
        _finite(float(center.y), label="package center Y"),
        _finite(float(center.z), label="package center Z"),
    )


def _translation_binding(vector: Vector3) -> tuple[str, RigidTransform]:
    transform = RigidTransform.from_translation(vector)
    return ("RESOLVED_IDENTITY", transform) if _transform_is_identity(transform) else ("RESOLVED_RIGID", transform)


def _released_node(
    *,
    datum_id: str,
    parent_id: str,
    datum_class: str,
    producer_path: str,
    source_locator: str,
    transform_status: str,
    local_to_parent: RigidTransform,
    manufacturing_status: str,
    geometry_role: str,
) -> DatumNode:
    return DatumNode(
        datum_id=datum_id,
        parent_id=parent_id,
        datum_class=datum_class,
        producer_path=producer_path,
        producer_blob_sha=_SOURCE_BLOB_BY_PATH[producer_path],
        source_locator=source_locator,
        transform_status=transform_status,
        local_to_parent=local_to_parent,
        manufacturing_status=manufacturing_status,
        geometry_role=geometry_role,
    )


def _unresolved_node(
    datum_id: str,
    parent_id: str,
    *,
    source_locator: str,
    blocker: str,
    producer_path: str | None = None,
    partial_translation_mm: tuple[float | None, float | None, float | None] | None = None,
    datum_class: str = "SUBSYSTEM_LOCAL",
    geometry_role: str = "NO_RELEASED_PLACEMENT_GEOMETRY",
) -> DatumNode:
    return DatumNode(
        datum_id=datum_id,
        parent_id=parent_id,
        datum_class=datum_class,
        producer_path=producer_path,
        producer_blob_sha=None if producer_path is None else _SOURCE_BLOB_BY_PATH[producer_path],
        source_locator=source_locator,
        transform_status="UNRESOLVED",
        local_to_parent=None,
        manufacturing_status="UNRESOLVED_NOT_QUALIFIED_MANUFACTURING_DATUM",
        geometry_role=geometry_role,
        blocker=blocker,
        partial_translation_mm=partial_translation_mm,
    )


def build_whole_product_datum_hierarchy(
    *,
    authority: Authority | None = None,
    model: MasckOneModel | None = None,
) -> WholeProductDatumHierarchy:
    _require_source_files_current()
    authority = authority or (model.authority if model is not None else load_authority())
    if type(authority) is not Authority:
        raise DatumHierarchyError("datum hierarchy requires exact Authority type")
    canonical = load_authority()
    if authority.data != canonical.data:
        raise DatumHierarchyError("supplied authority differs from released machine authority")
    if str(authority.get("project", "authority_revision")) != AUTHORITY_REVISION:
        raise DatumHierarchyError("authority revision moved")
    if authority.get("project", "units", "length") != "mm":
        raise DatumHierarchyError("datum hierarchy requires exact authority millimetre length unit")

    datums = CanonicalDatums.from_authority(authority)
    if datums.global_frame.name != LEGACY_GLOBAL_FRAME_ID:
        raise DatumHierarchyError("released CanonicalDatums legacy frame name moved")
    if datums.global_frame.local_to_global_transform != RigidTransform.identity():
        raise DatumHierarchyError("released CanonicalDatums no longer maps identically to authority world")

    model = model or build_model(authority)
    if model.authority.data != authority.data:
        raise DatumHierarchyError("model authority differs from hierarchy authority")
    if model.datums.global_frame.name != LEGACY_GLOBAL_FRAME_ID:
        raise DatumHierarchyError("model datum frame identity drifted")

    identity = RigidTransform.identity()
    nodes: list[DatumNode] = [
        DatumNode(
            datum_id=WORLD_FRAME_ID,
            parent_id=None,
            datum_class="AUTHORITY_WORLD",
            producer_path="config/masck_one_authority.yaml",
            producer_blob_sha=_SOURCE_BLOB_BY_PATH["config/masck_one_authority.yaml"],
            source_locator="coordinate_system origin and positive-axis semantics",
            transform_status="ROOT",
            local_to_parent=None,
            manufacturing_status="CANONICAL_SYSTEM_REFERENCE_NOT_PART_DATUM",
            geometry_role="COORDINATE_SYSTEM_REFERENCE",
        ),
        _released_node(
            datum_id=LEGACY_GLOBAL_FRAME_ID,
            parent_id=WORLD_FRAME_ID,
            datum_class="LEGACY_IDENTITY_ALIAS",
            producer_path="src/masck_one/spatial.py",
            source_locator="CanonicalDatums.from_authority global_frame",
            transform_status="RESOLVED_IDENTITY",
            local_to_parent=identity,
            manufacturing_status="CANONICAL_SYSTEM_REFERENCE_NOT_PART_DATUM",
            geometry_role="COORDINATE_SYSTEM_REFERENCE",
        ),
        _released_node(
            datum_id=SHELL_PRIMARY_FRAME_ID,
            parent_id=WORLD_FRAME_ID,
            datum_class="PRIMARY_PART_REFERENCE",
            producer_path="src/masck_one/model.py",
            source_locator="_build_shell authored directly in authority-world coordinates",
            transform_status="RESOLVED_IDENTITY",
            local_to_parent=identity,
            manufacturing_status="DIGITAL_PRIMARY_REFERENCE_NOT_QUALIFIED_MANUFACTURING_DATUM",
            geometry_role="PHYSICAL_MATERIAL_COORDINATE_REFERENCE",
        ),
        _released_node(
            datum_id=STRUCTURAL_FRAME_REFERENCE_ID,
            parent_id=WORLD_FRAME_ID,
            datum_class="STRUCTURAL_REFERENCE",
            producer_path="src/masck_one/structural_frame.py",
            source_locator="authority-derived XY frame datums; Z qualification remains unresolved",
            transform_status="RESOLVED_IDENTITY",
            local_to_parent=identity,
            manufacturing_status="UNRESOLVED_NOT_QUALIFIED_MANUFACTURING_DATUM",
            geometry_role="STRUCTURAL_REFERENCE_WITH_UNRESOLVED_3D_DATUM_QUALIFICATION",
        ),
    ]

    frame_width_mm, frame_height_mm = authority.pair("geometry", "functional_frame_xy_mm")
    structural_xy = (
        (DATUM_CENTER, 0.0, 0.0, "canonical sagittal/transverse datum intersection"),
        (DATUM_SUPERIOR, 0.0, frame_height_mm / 2.0, "functional-frame authority height / 2"),
        (DATUM_INFERIOR, 0.0, -frame_height_mm / 2.0, "-functional-frame authority height / 2"),
        (DATUM_LEFT, -frame_width_mm / 2.0, 0.0, "-functional-frame authority width / 2"),
        (DATUM_RIGHT, frame_width_mm / 2.0, 0.0, "functional-frame authority width / 2"),
    )
    structural_z_blocker = (
        "released structural FrameDatum z_status=UNRESOLVED_UNTIL_STRUCTURAL_3D_SURFACE_AND_PACKAGING_CLOSURE; "
        "known authority-derived XY cannot be promoted to a complete 3D transform"
    )
    for datum_id, x_mm, y_mm, derivation in structural_xy:
        nodes.append(
            _unresolved_node(
                datum_id,
                STRUCTURAL_FRAME_REFERENCE_ID,
                source_locator=f"structural_frame.FrameDatum derivation={derivation}",
                blocker=structural_z_blocker,
                producer_path="src/masck_one/structural_frame.py",
                partial_translation_mm=(x_mm, y_mm, None),
                datum_class="STRUCTURAL_REFERENCE",
                geometry_role="STRUCTURAL_REFERENCE_WITH_UNRESOLVED_3D_DATUM_QUALIFICATION",
            )
        )

    package_specs = (
        (
            WATER_RESERVOIR_PACKAGE_FRAME_ID,
            model.water_reservoir_envelope,
            "water_reservoir_envelope B-rep centroid",
        ),
        (
            WASTE_CARTRIDGE_PACKAGE_FRAME_ID,
            model.waste_cartridge_envelope,
            "waste_cartridge_envelope B-rep centroid",
        ),
        (
            BATTERY_PACKAGE_FRAME_ID,
            model.battery_reference_envelope,
            "battery_reference_envelope B-rep centroid",
        ),
    )
    for datum_id, component, locator in package_specs:
        status, transform = _translation_binding(_component_center_mm(component))
        nodes.append(
            _released_node(
                datum_id=datum_id,
                parent_id=WORLD_FRAME_ID,
                datum_class="PACKAGE_REFERENCE",
                producer_path="src/masck_one/model.py",
                source_locator=locator,
                transform_status=status,
                local_to_parent=transform,
                manufacturing_status="REFERENCE_ONLY_NOT_MANUFACTURING_DATUM",
                geometry_role="PACKAGE_REFERENCE_ONLY",
            )
        )

    for frame_id, zone_id in zip(ACTUATOR_FRAME_IDS, ZONE_IDS, strict=True):
        nodes.append(
            DatumNode(
                datum_id=frame_id,
                parent_id=STRUCTURAL_FRAME_REFERENCE_ID,
                datum_class="SUBSYSTEM_LOCAL",
                producer_path="src/masck_one/actuator_frames.py",
                producer_blob_sha=_SOURCE_BLOB_BY_PATH["src/masck_one/actuator_frames.py"],
                source_locator=f"ActuatorLocalFrame zone_id={zone_id}",
                transform_status="UNRESOLVED",
                local_to_parent=None,
                manufacturing_status="UNRESOLVED_NOT_QUALIFIED_MANUFACTURING_DATUM",
                geometry_role="NO_RELEASED_PLACEMENT_GEOMETRY",
                blocker=(
                    "released actuator frame has no origin_xyz_mm, axis_azimuth_deg, structural_mount_datum_id "
                    "or production envelope; model.py actuator cylinders are package/development proxies only"
                ),
            )
        )

    unresolved_roots = (
        (
            WATER_RESERVOIR_ROOT_FRAME_ID,
            WORLD_FRAME_ID,
            "released primary water-reservoir subsystem root",
            (
                "water_reservoir.py explicitly leaves pickup/port locations and structural mount geometry unresolved; "
                "the model.py water box remains a separate package reference only"
            ),
            "src/masck_one/water_reservoir.py",
        ),
        (
            WASTE_CARTRIDGE_ROOT_FRAME_ID,
            WORLD_FRAME_ID,
            "released waste-cartridge subsystem root",
            (
                "waste_cartridge.py leaves insertion axis, key/seal geometry and service trajectory unresolved; "
                "the model.py cartridge box remains a separate package reference only"
            ),
            "src/masck_one/waste_cartridge.py",
        ),
        (
            CLEANSER_ROOT_FRAME_ID,
            WORLD_FRAME_ID,
            "released cleanser-storage subsystem root",
            (
                "cleanser_storage.py explicitly leaves refill/outlet/purge port locations and controlled storage "
                "geometry unresolved"
            ),
            "src/masck_one/cleanser_storage.py",
        ),
        (
            RETENTION_ROOT_FRAME_ID,
            WORLD_FRAME_ID,
            "retention subsystem root",
            "no retention/halo/quick-release producer is released on source main",
            None,
        ),
        (
            DRY_SIDE_ROOT_FRAME_ID,
            WORLD_FRAME_ID,
            "dry-side electronics/battery/PCB root",
            "no integrated dry-bay/PCB/charging/harness producer is released on source main",
            None,
        ),
        (
            HMI_ROOT_FRAME_ID,
            DRY_SIDE_ROOT_FRAME_ID,
            "physical HMI root",
            "no physical HMI control geometry is released on source main",
            None,
        ),
        (
            THERMAL_ROOT_FRAME_ID,
            DRY_SIDE_ROOT_FRAME_ID,
            "thermal/WARM root",
            "no current thermal/WARM package geometry is released on source main",
            None,
        ),
    )
    for datum_id, parent_id, locator, blocker, producer_path in unresolved_roots:
        nodes.append(
            _unresolved_node(
                datum_id,
                parent_id,
                source_locator=locator,
                blocker=blocker,
                producer_path=producer_path,
            )
        )

    hierarchy = WholeProductDatumHierarchy(
        source_main_sha=SOURCE_MAIN_SHA,
        authority_revision=AUTHORITY_REVISION,
        world_origin_xyz_mm=tuple(float(v) for v in authority.get("coordinate_system", "origin")),
        axis_positive=(
            str(authority.get("coordinate_system", "x_positive")),
            str(authority.get("coordinate_system", "y_positive")),
            str(authority.get("coordinate_system", "z_positive")),
        ),
        nodes=tuple(nodes),
    )

    # Resolve each numeric chain now so malformed transform composition fails before export.
    for node in hierarchy.nodes:
        transform = hierarchy.local_to_world_transform(node.datum_id)
        if node.transform_status == "UNRESOLVED":
            if transform is not None:
                raise DatumHierarchyError("unresolved datum unexpectedly resolved to world")
        elif transform is None:
            raise DatumHierarchyError("resolved datum failed to compose to world")
    return hierarchy
