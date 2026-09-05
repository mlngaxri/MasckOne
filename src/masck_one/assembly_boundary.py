from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha1, sha256
from functools import lru_cache
from io import BytesIO
import json
from pathlib import Path
import re

import cadquery as cq

from .model import Component, MasckOneModel, build_model


SCHEMA = "MASCK_ONE_CURRENT_MAIN_ASSEMBLY_BOUNDARY_V1"
SOURCE_MAIN_SHA = "afe29ff78419b6625dca5594974b6351f6f80e1b"
SOURCE_MODEL_GIT_BLOB_SHA = "9e7fa6c71ac28cc45ebb502444bf6c0ea49f7894"
SOURCE_AUTHORITY_GIT_BLOB_SHA = "2608dda483b995539de422290371c219668a1527"
AUTHORITY_REVISION = "2026-08-30-R1"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"

# Direct released geometry producers used by build_model(). These source bindings are
# deliberately narrower than the whole repository but broader than model.py alone.
# Per-component B-rep digests below independently guard the realized output geometry.
SOURCE_GEOMETRY_GIT_BLOB_IDENTITIES: tuple[tuple[str, str], ...] = (
    ("config/masck_one_authority.yaml", SOURCE_AUTHORITY_GIT_BLOB_SHA),
    ("src/masck_one/anatomy.py", "872d1e5be1b9ce9baa5b63cb53462eb7b36f40ab"),
    ("src/masck_one/authority.py", "6866e3a428dab8b32b5a1d9e58da78b8f5aa1aa2"),
    ("src/masck_one/coverage.py", "4a8cec4d94db97e63f634a94dd8c90094f3afcb0"),
    ("src/masck_one/facial_surface.py", "764f6f65b83ac7709d959bb0f37f861c90ea2794"),
    ("src/masck_one/interface_topology.py", "38b7c932f71a8675d45d098ac65154f98ff8bbb5"),
    ("src/masck_one/model.py", SOURCE_MODEL_GIT_BLOB_SHA),
    ("src/masck_one/nasal_subsystem.py", "f1f22b828d0465636579fc31eff0bfb6a6bf2507"),
    ("src/masck_one/protected_volumes.py", "ff2b9b288559f9b268e5d08a1d6c78335f745cf1"),
    ("src/masck_one/spatial.py", "8c1106b523fef5111009cc56236a53e3bc5ee10e"),
    ("src/masck_one/worn_pose.py", "9d4ed65246fbc92ac577ce38bceb95cd2253607b"),
)

ROLE_PHYSICAL_MATERIAL = "PHYSICAL_MATERIAL"
ROLE_DEVELOPMENT_REFERENCE = "DEVELOPMENT_REFERENCE"
ROLE_PACKAGE_REFERENCE = "PACKAGE_REFERENCE"
ROLE_PROTECTED_KEEPOUT = "PROTECTED_KEEPOUT"
ROLE_VOCABULARY = (
    ROLE_PHYSICAL_MATERIAL,
    ROLE_DEVELOPMENT_REFERENCE,
    ROLE_PACKAGE_REFERENCE,
    ROLE_PROTECTED_KEEPOUT,
)

INSTANCE_ID_BY_SOURCE_NAME = {
    "rigid_shell": "MASCK_ONE-ASM-RIGID-SHELL",
    "nasal_lobe_membrane_reference": "MASCK_ONE-ASM-NASAL-LOBE-REFERENCE",
    "actuator_envelope_1": "MASCK_ONE-ASM-ACTUATOR-REFERENCE-01",
    "actuator_envelope_2": "MASCK_ONE-ASM-ACTUATOR-REFERENCE-02",
    "actuator_envelope_3": "MASCK_ONE-ASM-ACTUATOR-REFERENCE-03",
    "actuator_envelope_4": "MASCK_ONE-ASM-ACTUATOR-REFERENCE-04",
    "water_reservoir_envelope": "MASCK_ONE-ASM-WATER-REFERENCE",
    "waste_cartridge_envelope": "MASCK_ONE-ASM-WASTE-CARTRIDGE-REFERENCE",
    "battery_reference_envelope": "MASCK_ONE-ASM-BATTERY-REFERENCE",
    "visual_eye_left": "MASCK_ONE-ASM-KEEPOUT-EYE-LEFT",
    "visual_eye_right": "MASCK_ONE-ASM-KEEPOUT-EYE-RIGHT",
    "visual_mouth": "MASCK_ONE-ASM-KEEPOUT-MOUTH",
    "visual_nostril_left": "MASCK_ONE-ASM-KEEPOUT-NOSTRIL-LEFT",
    "visual_nostril_right": "MASCK_ONE-ASM-KEEPOUT-NOSTRIL-RIGHT",
}
EXPECTED_SOURCE_NAMES = tuple(sorted(INSTANCE_ID_BY_SOURCE_NAME))
PHYSICAL_MATERIAL_NAMES = ("rigid_shell",)
DEVELOPMENT_REFERENCE_NAMES = ("nasal_lobe_membrane_reference",)
PACKAGE_REFERENCE_NAMES = (
    "actuator_envelope_1",
    "actuator_envelope_2",
    "actuator_envelope_3",
    "actuator_envelope_4",
    "battery_reference_envelope",
    "waste_cartridge_envelope",
    "water_reservoir_envelope",
)
PROTECTED_KEEPOUT_NAMES = (
    "visual_eye_left",
    "visual_eye_right",
    "visual_mouth",
    "visual_nostril_left",
    "visual_nostril_right",
)

_GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_REPO_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_STATUS = (
    "DIGITAL_ASSEMBLY_MATERIAL_REFERENCE_SEPARATION_ONLY_NOT_FIT_CLEARANCE_SERVICE_LOAD_"
    "RETENTION_HYDRAULIC_ELECTRICAL_THERMAL_HYGIENE_OR_PHYSICAL_VALIDATION"
)


class AssemblyBoundaryError(ValueError):
    pass


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def _brep_sha256(solid: cq.Workplane) -> str:
    if type(solid) is not cq.Workplane:
        raise AssemblyBoundaryError("assembly B-rep digest requires exact CadQuery Workplane geometry")
    shape = solid.val()
    if not shape.isValid() or not shape.Solids():
        raise AssemblyBoundaryError("assembly B-rep digest requires valid solid geometry")
    buffer = BytesIO()
    shape.exportBrep(buffer)
    payload = buffer.getvalue()
    if not payload:
        raise AssemblyBoundaryError("assembly B-rep export produced no bytes")
    return sha256(payload).hexdigest()


def _expected_source_sha(relative_path: str, configured_sha: str) -> str:
    # Retain the original named model/authority constants as public fail-closed
    # bindings while also publishing the complete direct producer set.
    if relative_path == "src/masck_one/model.py":
        return SOURCE_MODEL_GIT_BLOB_SHA
    if relative_path == "config/masck_one_authority.yaml":
        return SOURCE_AUTHORITY_GIT_BLOB_SHA
    return configured_sha


def _require_source_files_current() -> None:
    seen: set[str] = set()
    for relative_path, configured_sha in SOURCE_GEOMETRY_GIT_BLOB_IDENTITIES:
        if (
            type(relative_path) is not str
            or not relative_path
            or relative_path in seen
            or _GIT_SHA_RE.fullmatch(configured_sha) is None
        ):
            raise AssemblyBoundaryError("assembly source-graph identity set is malformed")
        seen.add(relative_path)
        expected_sha = _expected_source_sha(relative_path, configured_sha)
        if _GIT_SHA_RE.fullmatch(expected_sha) is None:
            raise AssemblyBoundaryError(f"assembly source binding is malformed for {relative_path}")
        path = _REPO_ROOT / relative_path
        if not path.is_file():
            raise AssemblyBoundaryError(f"assembly source file is missing: {relative_path}")
        actual_sha = _git_blob_sha(path)
        if actual_sha != expected_sha:
            raise AssemblyBoundaryError(
                f"assembly source moved at {relative_path}; expected {expected_sha}, got {actual_sha}"
            )


def _expected_role(name: str) -> str:
    if name in PHYSICAL_MATERIAL_NAMES:
        return ROLE_PHYSICAL_MATERIAL
    if name in DEVELOPMENT_REFERENCE_NAMES:
        return ROLE_DEVELOPMENT_REFERENCE
    if name in PACKAGE_REFERENCE_NAMES:
        return ROLE_PACKAGE_REFERENCE
    if name in PROTECTED_KEEPOUT_NAMES:
        return ROLE_PROTECTED_KEEPOUT
    raise AssemblyBoundaryError(f"unclassified released component {name!r}")


def _component_map(model: MasckOneModel) -> dict[str, Component]:
    components = {component.name: component for component in model.components}
    if len(components) != len(model.components) or tuple(sorted(components)) != EXPECTED_SOURCE_NAMES:
        raise AssemblyBoundaryError("released model component set changed and requires explicit assembly rebind")
    return components


def _canonical_brep_digests(model: MasckOneModel) -> dict[str, str]:
    return {name: _brep_sha256(component.solid) for name, component in _component_map(model).items()}


@lru_cache(maxsize=1)
def _released_canonical_brep_digests() -> tuple[tuple[str, str], ...]:
    canonical = build_model()
    return tuple(sorted(_canonical_brep_digests(canonical).items()))


@dataclass(frozen=True, slots=True)
class AssemblyInstance:
    instance_id: str
    source_component_name: str
    source_component_status: str
    role: str
    include_in_physical_material: bool
    source_module: str
    source_git_blob_sha: str
    source_component_brep_sha256: str
    coordinate_frame_id: str
    transform_semantics: str
    evidence_status: str
    source_component: Component = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        for label, value in (
            ("instance_id", self.instance_id),
            ("source_component_name", self.source_component_name),
            ("source_component_status", self.source_component_status),
            ("source_module", self.source_module),
            ("coordinate_frame_id", self.coordinate_frame_id),
            ("transform_semantics", self.transform_semantics),
            ("evidence_status", self.evidence_status),
        ):
            if type(value) is not str or not value or value != value.strip():
                raise AssemblyBoundaryError(f"{label} must be exact nonblank text")
        if self.role not in ROLE_VOCABULARY:
            raise AssemblyBoundaryError(f"uncontrolled assembly role {self.role!r}")
        if type(self.include_in_physical_material) is not bool:
            raise AssemblyBoundaryError("physical-material inclusion must be an exact bool")
        if type(self.source_component) is not Component:
            raise AssemblyBoundaryError("assembly instance must retain the exact source Component object")
        if self.source_component.name != self.source_component_name:
            raise AssemblyBoundaryError("assembly source-component identity moved")
        if self.source_component.status != self.source_component_status:
            raise AssemblyBoundaryError("assembly source-component status moved")
        if self.source_module != "src/masck_one/model.py":
            raise AssemblyBoundaryError("current assembly instances must consume released model.py geometry")
        if self.source_git_blob_sha != SOURCE_MODEL_GIT_BLOB_SHA or _GIT_SHA_RE.fullmatch(self.source_git_blob_sha) is None:
            raise AssemblyBoundaryError("assembly model source binding is stale")
        if _SHA256_RE.fullmatch(self.source_component_brep_sha256) is None:
            raise AssemblyBoundaryError("assembly source-component B-rep digest is malformed")
        if _brep_sha256(self.source_component.solid) != self.source_component_brep_sha256:
            raise AssemblyBoundaryError(
                f"assembly source-component B-rep moved for {self.source_component_name}"
            )
        if self.coordinate_frame_id != WORLD_FRAME_ID:
            raise AssemblyBoundaryError("assembly instance is not in the canonical authority world frame")
        if self.transform_semantics != "IDENTITY_SOURCE_ALREADY_IN_AUTHORITY_WORLD_MM":
            raise AssemblyBoundaryError("assembly transform semantics changed")
        expected_role = _expected_role(self.source_component_name)
        if self.role != expected_role:
            raise AssemblyBoundaryError(
                f"assembly role mismatch for {self.source_component_name}: expected {expected_role}, got {self.role}"
            )
        expected_material = expected_role == ROLE_PHYSICAL_MATERIAL
        if self.include_in_physical_material is not expected_material:
            raise AssemblyBoundaryError(
                f"material/reference mixing for {self.source_component_name}: role {expected_role}"
            )
        if self.evidence_status != "SOURCE_GEOMETRY_CONSUMED_UNCHANGED_DIGITAL_ONLY":
            raise AssemblyBoundaryError("assembly instance evidence status changed")

    def manifest(self) -> dict[str, object]:
        self.__post_init__()
        return {
            "instance_id": self.instance_id,
            "source_component_name": self.source_component_name,
            "source_component_status": self.source_component_status,
            "role": self.role,
            "include_in_physical_material": self.include_in_physical_material,
            "source_module": self.source_module,
            "source_git_blob_sha": self.source_git_blob_sha,
            "source_component_brep_sha256": self.source_component_brep_sha256,
            "coordinate_frame_id": self.coordinate_frame_id,
            "transform_semantics": self.transform_semantics,
            "evidence_status": self.evidence_status,
        }


@dataclass(frozen=True, slots=True)
class CurrentMainAssemblyBoundary:
    schema: str
    source_main_sha: str
    source_model_git_blob_sha: str
    source_authority_git_blob_sha: str
    source_geometry_git_blob_identities: tuple[tuple[str, str], ...]
    authority_revision: str
    coordinate_frame_id: str
    instances: tuple[AssemblyInstance, ...]
    physical_validation_eligible: bool
    evidence_status: str

    def __post_init__(self) -> None:
        if self.schema != SCHEMA:
            raise AssemblyBoundaryError("unexpected assembly-boundary schema")
        if self.source_main_sha != SOURCE_MAIN_SHA or _GIT_SHA_RE.fullmatch(self.source_main_sha) is None:
            raise AssemblyBoundaryError("assembly boundary is not bound to reconstructed released main")
        if self.source_model_git_blob_sha != SOURCE_MODEL_GIT_BLOB_SHA:
            raise AssemblyBoundaryError("assembly model source blob is stale")
        if self.source_authority_git_blob_sha != SOURCE_AUTHORITY_GIT_BLOB_SHA:
            raise AssemblyBoundaryError("assembly authority source blob is stale")
        if self.source_geometry_git_blob_identities != SOURCE_GEOMETRY_GIT_BLOB_IDENTITIES:
            raise AssemblyBoundaryError("assembly direct geometry source graph changed")
        if len(self.source_geometry_git_blob_identities) != len(
            {path for path, _ in self.source_geometry_git_blob_identities}
        ):
            raise AssemblyBoundaryError("assembly direct geometry source graph contains duplicate paths")
        for path, digest in self.source_geometry_git_blob_identities:
            if type(path) is not str or not path or _GIT_SHA_RE.fullmatch(digest) is None:
                raise AssemblyBoundaryError("assembly direct geometry source graph is malformed")
        if self.authority_revision != AUTHORITY_REVISION:
            raise AssemblyBoundaryError("assembly authority revision moved")
        if self.coordinate_frame_id != WORLD_FRAME_ID:
            raise AssemblyBoundaryError("assembly boundary must use the canonical authority world frame")
        if type(self.instances) is not tuple or not self.instances:
            raise AssemblyBoundaryError("assembly boundary requires immutable source instances")
        instance_ids = tuple(item.instance_id for item in self.instances)
        source_names = tuple(item.source_component_name for item in self.instances)
        if instance_ids != tuple(sorted(instance_ids)):
            raise AssemblyBoundaryError("assembly instances must be deterministic by stable instance ID")
        if len(instance_ids) != len(set(instance_ids)) or len(source_names) != len(set(source_names)):
            raise AssemblyBoundaryError("assembly instance identities must be unique")
        if tuple(sorted(source_names)) != EXPECTED_SOURCE_NAMES:
            raise AssemblyBoundaryError("released model component set changed and requires explicit assembly rebind")
        for item in self.instances:
            item.__post_init__()
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise AssemblyBoundaryError("digital assembly composition cannot be physical validation evidence")
        if self.evidence_status != EVIDENCE_STATUS:
            raise AssemblyBoundaryError("assembly evidence boundary changed")

    @property
    def physical_material_instances(self) -> tuple[AssemblyInstance, ...]:
        return tuple(item for item in self.instances if item.include_in_physical_material)

    @property
    def reference_instances(self) -> tuple[AssemblyInstance, ...]:
        return tuple(item for item in self.instances if not item.include_in_physical_material)

    @property
    def development_assembly_exclusions(self) -> tuple[str, ...]:
        return tuple(sorted(item.source_component_name for item in self.reference_instances))

    def physical_material_compound(self) -> cq.Compound:
        shapes = [item.source_component.solid.val() for item in self.physical_material_instances]
        if not shapes:
            raise AssemblyBoundaryError("physical development assembly cannot be empty")
        return cq.Compound.makeCompound(shapes)

    def reference_review_compound(self) -> cq.Compound:
        shapes = [item.source_component.solid.val() for item in self.reference_instances]
        if not shapes:
            raise AssemblyBoundaryError("reference review compound cannot be empty")
        return cq.Compound.makeCompound(shapes)

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        self.__post_init__()
        payload: dict[str, object] = {
            "schema": self.schema,
            "source_main_sha": self.source_main_sha,
            "source_model_git_blob_sha": self.source_model_git_blob_sha,
            "source_authority_git_blob_sha": self.source_authority_git_blob_sha,
            "source_geometry_git_blob_identities": [list(item) for item in self.source_geometry_git_blob_identities],
            "authority_revision": self.authority_revision,
            "coordinate_frame_id": self.coordinate_frame_id,
            "instances": [item.manifest() for item in self.instances],
            "physical_material_names": [item.source_component_name for item in self.physical_material_instances],
            "reference_review_names": [item.source_component_name for item in self.reference_instances],
            "development_assembly_exclusions": list(self.development_assembly_exclusions),
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
            payload["manifest_sha256"] = sha256(raw).hexdigest()
        return payload


def build_current_main_assembly_boundary(model: MasckOneModel | None = None) -> CurrentMainAssemblyBoundary:
    _require_source_files_current()
    if model is None:
        model = build_model()
        canonical_digests = _canonical_brep_digests(model)
    else:
        if type(model) is not MasckOneModel:
            raise AssemblyBoundaryError("assembly boundary requires the exact MasckOneModel type")
        canonical_digests = dict(_released_canonical_brep_digests())
    if type(model) is not MasckOneModel:
        raise AssemblyBoundaryError("assembly boundary requires the exact MasckOneModel type")
    revision = str(model.authority.get("project", "authority_revision"))
    if revision != AUTHORITY_REVISION:
        raise AssemblyBoundaryError("model authority revision differs from the released binding")

    components = _component_map(model)
    actual_digests = _canonical_brep_digests(model)
    if actual_digests != canonical_digests:
        moved = sorted(name for name in EXPECTED_SOURCE_NAMES if actual_digests[name] != canonical_digests[name])
        raise AssemblyBoundaryError(
            "supplied model B-rep differs from released canonical build for: " + ", ".join(moved)
        )

    instances = tuple(
        sorted(
            (
                AssemblyInstance(
                    instance_id=INSTANCE_ID_BY_SOURCE_NAME[name],
                    source_component_name=name,
                    source_component_status=component.status,
                    role=_expected_role(name),
                    include_in_physical_material=_expected_role(name) == ROLE_PHYSICAL_MATERIAL,
                    source_module="src/masck_one/model.py",
                    source_git_blob_sha=SOURCE_MODEL_GIT_BLOB_SHA,
                    source_component_brep_sha256=canonical_digests[name],
                    coordinate_frame_id=WORLD_FRAME_ID,
                    transform_semantics="IDENTITY_SOURCE_ALREADY_IN_AUTHORITY_WORLD_MM",
                    evidence_status="SOURCE_GEOMETRY_CONSUMED_UNCHANGED_DIGITAL_ONLY",
                    source_component=component,
                )
                for name, component in components.items()
            ),
            key=lambda item: item.instance_id,
        )
    )
    return CurrentMainAssemblyBoundary(
        schema=SCHEMA,
        source_main_sha=SOURCE_MAIN_SHA,
        source_model_git_blob_sha=SOURCE_MODEL_GIT_BLOB_SHA,
        source_authority_git_blob_sha=SOURCE_AUTHORITY_GIT_BLOB_SHA,
        source_geometry_git_blob_identities=SOURCE_GEOMETRY_GIT_BLOB_IDENTITIES,
        authority_revision=AUTHORITY_REVISION,
        coordinate_frame_id=WORLD_FRAME_ID,
        instances=instances,
        physical_validation_eligible=False,
        evidence_status=EVIDENCE_STATUS,
    )
