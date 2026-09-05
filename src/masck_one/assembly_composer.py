from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
import math
import re

import cadquery as cq

from .model import Component, MasckOneModel, build_model


ASSEMBLY_SCHEMA = "MASCK_ONE_INTEGRATED_ASSEMBLY_SKELETON_V1"
SOURCE_MAIN_SHA = "5fce2a43a34d8be49256677a35af60c906dc1653"
SOURCE_MODEL_GIT_BLOB_SHA = "9e7fa6c71ac28cc45ebb502444bf6c0ea49f7894"
SOURCE_AUTHORITY_GIT_BLOB_SHA = "2608dda483b995539de422290371c219668a1527"
AUTHORITY_REVISION = "2026-08-30-R1"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"

PARTICIPATION_ASSEMBLY_GEOMETRY = "ASSEMBLY_GEOMETRY"
PARTICIPATION_DEVELOPMENT_REFERENCE = "DEVELOPMENT_REFERENCE"
PARTICIPATION_CONTROLLED_ENVELOPE = "CONTROLLED_ENVELOPE"
PARTICIPATION_REFERENCE_KEEPOUT = "REFERENCE_KEEPOUT"
PARTICIPATION_VOCABULARY = (
    PARTICIPATION_ASSEMBLY_GEOMETRY,
    PARTICIPATION_DEVELOPMENT_REFERENCE,
    PARTICIPATION_CONTROLLED_ENVELOPE,
    PARTICIPATION_REFERENCE_KEEPOUT,
)

INSTANCE_ID_BY_SOURCE_NAME = {
    "actuator_envelope_1": "MASCK_ONE-ASM-ACTUATOR-01",
    "actuator_envelope_2": "MASCK_ONE-ASM-ACTUATOR-02",
    "actuator_envelope_3": "MASCK_ONE-ASM-ACTUATOR-03",
    "actuator_envelope_4": "MASCK_ONE-ASM-ACTUATOR-04",
    "battery_reference_envelope": "MASCK_ONE-ASM-BATTERY-REFERENCE",
    "nasal_lobe_membrane_reference": "MASCK_ONE-ASM-NASAL-LOBE-REFERENCE",
    "rigid_shell": "MASCK_ONE-ASM-RIGID-SHELL",
    "visual_eye_left": "MASCK_ONE-ASM-KEEPOUT-EYE-LEFT",
    "visual_eye_right": "MASCK_ONE-ASM-KEEPOUT-EYE-RIGHT",
    "visual_mouth": "MASCK_ONE-ASM-KEEPOUT-MOUTH",
    "visual_nostril_left": "MASCK_ONE-ASM-KEEPOUT-NOSTRIL-LEFT",
    "visual_nostril_right": "MASCK_ONE-ASM-KEEPOUT-NOSTRIL-RIGHT",
    "waste_cartridge_envelope": "MASCK_ONE-ASM-WASTE-CARTRIDGE",
    "water_reservoir_envelope": "MASCK_ONE-ASM-WATER-RESERVOIR",
}
EXPECTED_SOURCE_NAMES = tuple(sorted(INSTANCE_ID_BY_SOURCE_NAME))

_GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_EPS = 1e-12


class AssemblyComposerError(ValueError):
    """Raised when assembly identity, transforms, or source provenance become ambiguous."""


def _canonical_scalar(value: object, *, label: str) -> float:
    if type(value) not in (int, float):
        raise AssemblyComposerError(f"{label} must be an exact finite numeric scalar")
    result = float(value)
    if not math.isfinite(result):
        raise AssemblyComposerError(f"{label} must be finite")
    return 0.0 if result == 0.0 else result


def _canonical_triple(value: object, *, label: str) -> tuple[float, float, float]:
    if type(value) is not tuple or len(value) != 3:
        raise AssemblyComposerError(f"{label} must be an exact three-value tuple")
    return tuple(_canonical_scalar(item, label=f"{label}[{index}]") for index, item in enumerate(value))  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class CanonicalTransform:
    """Source-to-authority-world transform for one assembly instance.

    Released ``model.py`` geometry is already authored in the authority world frame, so
    V1 intentionally accepts identity transforms only. This prevents a composer from
    silently re-positioning subsystem geometry while still making the transform explicit.
    """

    translation_xyz_mm: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation_axis_xyz: tuple[float, float, float] = (0.0, 0.0, 1.0)
    rotation_deg: float = 0.0
    source_frame_id: str = WORLD_FRAME_ID
    target_frame_id: str = WORLD_FRAME_ID
    semantics: str = "SOURCE_GEOMETRY_ALREADY_IN_AUTHORITY_WORLD_FRAME"

    def __post_init__(self) -> None:
        translation = _canonical_triple(self.translation_xyz_mm, label="assembly translation")
        axis = _canonical_triple(self.rotation_axis_xyz, label="assembly rotation axis")
        angle = _canonical_scalar(self.rotation_deg, label="assembly rotation angle")
        if translation != (0.0, 0.0, 0.0) or axis != (0.0, 0.0, 1.0) or abs(angle) > _EPS:
            raise AssemblyComposerError(
                "V1 assembly composer cannot transform released world-frame geometry"
            )
        if self.source_frame_id != WORLD_FRAME_ID or self.target_frame_id != WORLD_FRAME_ID:
            raise AssemblyComposerError("assembly transforms must remain in the canonical authority world frame")
        if self.semantics != "SOURCE_GEOMETRY_ALREADY_IN_AUTHORITY_WORLD_FRAME":
            raise AssemblyComposerError("assembly transform semantics must remain explicit and controlled")
        object.__setattr__(self, "translation_xyz_mm", translation)
        object.__setattr__(self, "rotation_axis_xyz", axis)
        object.__setattr__(self, "rotation_deg", angle)

    @property
    def is_identity(self) -> bool:
        return True

    def manifest(self) -> dict[str, object]:
        return {
            "translation_xyz_mm": list(self.translation_xyz_mm),
            "rotation_axis_xyz": list(self.rotation_axis_xyz),
            "rotation_deg": self.rotation_deg,
            "source_frame_id": self.source_frame_id,
            "target_frame_id": self.target_frame_id,
            "semantics": self.semantics,
        }


@dataclass(frozen=True, slots=True)
class AssemblyInstance:
    instance_id: str
    source_component_name: str
    source_component_status: str
    participation: str
    include_in_development_compound: bool
    source_module: str
    source_git_blob_sha: str
    transform: CanonicalTransform
    evidence_status: str
    source_component: Component = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        for label, value in (
            ("instance_id", self.instance_id),
            ("source_component_name", self.source_component_name),
            ("source_component_status", self.source_component_status),
            ("source_module", self.source_module),
            ("evidence_status", self.evidence_status),
        ):
            if type(value) is not str or not value or value != value.strip():
                raise AssemblyComposerError(f"{label} must be exact nonblank text")
        if self.participation not in PARTICIPATION_VOCABULARY:
            raise AssemblyComposerError(f"uncontrolled assembly participation {self.participation!r}")
        if type(self.include_in_development_compound) is not bool:
            raise AssemblyComposerError("assembly inclusion flag must be a literal bool")
        if self.source_module != "src/masck_one/model.py":
            raise AssemblyComposerError("V1 assembly instances must consume released model.py geometry")
        if self.source_git_blob_sha != SOURCE_MODEL_GIT_BLOB_SHA or _GIT_SHA_RE.fullmatch(self.source_git_blob_sha) is None:
            raise AssemblyComposerError("assembly instance model source binding is stale")
        if type(self.transform) is not CanonicalTransform or not self.transform.is_identity:
            raise AssemblyComposerError("assembly instance must carry the controlled identity world transform")
        if type(self.source_component) is not Component:
            raise AssemblyComposerError("assembly instance must retain the exact source Component object")
        if self.source_component.name != self.source_component_name:
            raise AssemblyComposerError("assembly instance source name does not match the consumed source object")
        if self.source_component.status != self.source_component_status:
            raise AssemblyComposerError("assembly instance source status is stale")
        if self.source_component_status == "REFERENCE_ONLY":
            if self.participation != PARTICIPATION_REFERENCE_KEEPOUT or self.include_in_development_compound:
                raise AssemblyComposerError("reference-only geometry cannot enter the development compound")
        elif not self.include_in_development_compound:
            raise AssemblyComposerError("released non-reference geometry cannot disappear from the development compound")

    def manifest(self) -> dict[str, object]:
        return {
            "instance_id": self.instance_id,
            "source_component_name": self.source_component_name,
            "source_component_status": self.source_component_status,
            "participation": self.participation,
            "include_in_development_compound": self.include_in_development_compound,
            "source_module": self.source_module,
            "source_git_blob_sha": self.source_git_blob_sha,
            "transform": self.transform.manifest(),
            "evidence_status": self.evidence_status,
        }


@dataclass(frozen=True, slots=True)
class IntegratedAssemblySkeleton:
    schema: str
    source_main_sha: str
    source_model_git_blob_sha: str
    source_authority_git_blob_sha: str
    authority_revision: str
    coordinate_frame_id: str
    instances: tuple[AssemblyInstance, ...]
    physical_validation_eligible: bool
    evidence_status: str

    def __post_init__(self) -> None:
        if self.schema != ASSEMBLY_SCHEMA:
            raise AssemblyComposerError("unexpected assembly-skeleton schema")
        if self.source_main_sha != SOURCE_MAIN_SHA or _GIT_SHA_RE.fullmatch(self.source_main_sha) is None:
            raise AssemblyComposerError("assembly skeleton is not bound to reconstructed released main")
        if self.source_model_git_blob_sha != SOURCE_MODEL_GIT_BLOB_SHA:
            raise AssemblyComposerError("assembly model source blob is stale")
        if self.source_authority_git_blob_sha != SOURCE_AUTHORITY_GIT_BLOB_SHA:
            raise AssemblyComposerError("assembly authority source blob is stale")
        if self.authority_revision != AUTHORITY_REVISION:
            raise AssemblyComposerError("assembly authority revision is stale")
        if self.coordinate_frame_id != WORLD_FRAME_ID:
            raise AssemblyComposerError("assembly skeleton must use the canonical authority world frame")
        if type(self.instances) is not tuple or not self.instances:
            raise AssemblyComposerError("assembly skeleton requires immutable source instances")
        instance_ids = tuple(item.instance_id for item in self.instances)
        source_names = tuple(item.source_component_name for item in self.instances)
        if len(instance_ids) != len(set(instance_ids)) or len(source_names) != len(set(source_names)):
            raise AssemblyComposerError("assembly instance and source-component IDs must be globally unique")
        if instance_ids != tuple(sorted(instance_ids)):
            raise AssemblyComposerError("assembly instances must be deterministic by stable instance ID")
        if tuple(sorted(source_names)) != EXPECTED_SOURCE_NAMES:
            raise AssemblyComposerError("assembly skeleton does not consume the complete released model component set")
        for item in self.instances:
            item.__post_init__()
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise AssemblyComposerError("digital assembly composition cannot be physical validation evidence")
        if self.evidence_status != (
            "DIGITAL_RELEASED_MAIN_ASSEMBLY_COMPOSITION_ONLY_NOT_FIT_CLEARANCE_SERVICE_LOAD_"
            "RETENTION_HYDRAULIC_ELECTRICAL_THERMAL_HYGIENE_OR_PHYSICAL_EVIDENCE"
        ):
            raise AssemblyComposerError("assembly evidence boundary must remain explicit")

    @property
    def assembly_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        return sha256(raw).hexdigest()

    @property
    def development_instances(self) -> tuple[AssemblyInstance, ...]:
        return tuple(item for item in self.instances if item.include_in_development_compound)

    @property
    def reference_keepout_instances(self) -> tuple[AssemblyInstance, ...]:
        return tuple(item for item in self.instances if not item.include_in_development_compound)

    def development_compound(self) -> cq.Compound:
        shapes = [item.source_component.solid.val() for item in self.development_instances]
        if not shapes:
            raise AssemblyComposerError("development assembly cannot be empty")
        return cq.Compound.makeCompound(shapes)

    def reference_keepout_compound(self) -> cq.Compound:
        shapes = [item.source_component.solid.val() for item in self.reference_keepout_instances]
        if not shapes:
            raise AssemblyComposerError("reference keepout assembly cannot be empty")
        return cq.Compound.makeCompound(shapes)

    def geometry_summary(self) -> dict[str, object]:
        development = self.development_compound()
        keepouts = self.reference_keepout_compound()
        development_box = development.BoundingBox()
        keepout_box = keepouts.BoundingBox()
        return {
            "development_instance_count": len(self.development_instances),
            "reference_keepout_instance_count": len(self.reference_keepout_instances),
            "development_bounds_xyz_mm": [
                round(float(development_box.xlen), 6),
                round(float(development_box.ylen), 6),
                round(float(development_box.zlen), 6),
            ],
            "reference_keepout_bounds_xyz_mm": [
                round(float(keepout_box.xlen), 6),
                round(float(keepout_box.ylen), 6),
                round(float(keepout_box.zlen), 6),
            ],
            "geometry_semantics": "SOURCE_SOLIDS_COMPOSED_WITH_IDENTITY_WORLD_TRANSFORMS_NO_REDEFINITION",
        }

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": self.schema,
            "source_main_sha": self.source_main_sha,
            "source_model_git_blob_sha": self.source_model_git_blob_sha,
            "source_authority_git_blob_sha": self.source_authority_git_blob_sha,
            "authority_revision": self.authority_revision,
            "coordinate_frame_id": self.coordinate_frame_id,
            "instances": [item.manifest() for item in self.instances],
            "geometry_summary": self.geometry_summary(),
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
            payload["assembly_sha256"] = sha256(raw).hexdigest()
        return payload


def _participation(component: Component) -> str:
    if component.status == "REFERENCE_ONLY":
        return PARTICIPATION_REFERENCE_KEEPOUT
    if component.name == "nasal_lobe_membrane_reference":
        return PARTICIPATION_DEVELOPMENT_REFERENCE
    if component.name.startswith("actuator_envelope_") or component.name.endswith("_envelope"):
        return PARTICIPATION_CONTROLLED_ENVELOPE
    return PARTICIPATION_ASSEMBLY_GEOMETRY


def build_integrated_assembly_skeleton(model: MasckOneModel | None = None) -> IntegratedAssemblySkeleton:
    model = model or build_model()
    if type(model) is not MasckOneModel:
        raise AssemblyComposerError("assembly composer requires the exact MasckOneModel type")
    revision = str(model.authority.get("project", "authority_revision"))
    if revision != AUTHORITY_REVISION:
        raise AssemblyComposerError("model authority revision differs from the reconstructed release binding")
    components = {component.name: component for component in model.components}
    if tuple(sorted(components)) != EXPECTED_SOURCE_NAMES:
        raise AssemblyComposerError("released model component set changed and requires explicit assembly rebind")

    instances = tuple(
        sorted(
            (
                AssemblyInstance(
                    instance_id=INSTANCE_ID_BY_SOURCE_NAME[name],
                    source_component_name=name,
                    source_component_status=component.status,
                    participation=_participation(component),
                    include_in_development_compound=component.status != "REFERENCE_ONLY",
                    source_module="src/masck_one/model.py",
                    source_git_blob_sha=SOURCE_MODEL_GIT_BLOB_SHA,
                    transform=CanonicalTransform(),
                    evidence_status=(
                        "SOURCE_GEOMETRY_CONSUMED_UNCHANGED_FROM_RELEASED_MAIN_"
                        "NOT_A_PHYSICAL_VALIDATION_OR_PRODUCTION_FREEZE"
                    ),
                    source_component=component,
                )
                for name, component in components.items()
            ),
            key=lambda item: item.instance_id,
        )
    )
    return IntegratedAssemblySkeleton(
        schema=ASSEMBLY_SCHEMA,
        source_main_sha=SOURCE_MAIN_SHA,
        source_model_git_blob_sha=SOURCE_MODEL_GIT_BLOB_SHA,
        source_authority_git_blob_sha=SOURCE_AUTHORITY_GIT_BLOB_SHA,
        authority_revision=AUTHORITY_REVISION,
        coordinate_frame_id=WORLD_FRAME_ID,
        instances=instances,
        physical_validation_eligible=False,
        evidence_status=(
            "DIGITAL_RELEASED_MAIN_ASSEMBLY_COMPOSITION_ONLY_NOT_FIT_CLEARANCE_SERVICE_LOAD_"
            "RETENTION_HYDRAULIC_ELECTRICAL_THERMAL_HYGIENE_OR_PHYSICAL_EVIDENCE"
        ),
    )
