from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1, sha256
import json
import math
from pathlib import Path
import re

from .cleanser_storage import CLEANSER_STORAGE_ID
from .fresh_pump_packaging import STATION_CLEANSER, STATION_WATER
from .model import MasckOneModel, build_model
from .realized_waste_backbone_release import Cell4WasteBackboneRelease, build_current_cell4_waste_backbone_release
from .structural_frame import (
    RESERVATION_FRESH_FLUID,
    RESERVATION_HMI_ELECTRONICS,
    RESERVATION_RETENTION,
    RESERVATION_THERMAL,
    RESERVATION_WASTE,
)
from .waste_cartridge import CARTRIDGE_ID
from .waste_pump_architecture import BARRIER_WASTE, STATION_WASTE
from .water_reservoir import WATER_RESERVOIR_ID


SCHEMA = "MASCK_ONE_CANONICAL_COMPONENT_REGISTRY_V2"
SOURCE_MAIN_SHA = "afe29ff78419b6625dca5594974b6351f6f80e1b"
AUTHORITY_REVISION = "2026-08-30-R1"
AUTHORITY_BLOB_SHA = "2608dda483b995539de422290371c219668a1527"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
LENGTH_UNIT = "mm"

ROLE_PHYSICAL_MATERIAL = "PHYSICAL_MATERIAL"
ROLE_DEVELOPMENT_REFERENCE = "DEVELOPMENT_REFERENCE"
ROLE_PACKAGE_REFERENCE = "PACKAGE_REFERENCE"
ROLE_PROTECTED_REFERENCE = "PROTECTED_KEEPOUT_REFERENCE"
ROLE_REALIZED_CENTERLINE = "REALIZED_CENTERLINE_REFERENCE"
ROLE_TOPOLOGY = "TOPOLOGY_ONLY"
ROLE_UNRESOLVED = "UNRESOLVED_REQUIRED"
GEOMETRY_ROLES = (
    ROLE_PHYSICAL_MATERIAL,
    ROLE_DEVELOPMENT_REFERENCE,
    ROLE_PACKAGE_REFERENCE,
    ROLE_PROTECTED_REFERENCE,
    ROLE_REALIZED_CENTERLINE,
    ROLE_TOPOLOGY,
    ROLE_UNRESOLVED,
)

OWNER_CELL_1 = "CELL_1_INTEGRATION"
OWNER_CELL_2 = "CELL_2_EXTERIOR_INTERFACE"
OWNER_CELL_3 = "CELL_3_MECHANISMS_RETENTION"
OWNER_CELL_4 = "CELL_4_FLUID_POWER_HMI_THERMAL"

IDENTITY_WORLD_TRANSFORM = (
    1.0, 0.0, 0.0, 0.0,
    0.0, 1.0, 0.0, 0.0,
    0.0, 0.0, 1.0, 0.0,
    0.0, 0.0, 0.0, 1.0,
)

SOURCE_GIT_BLOBS = {
    "config/masck_one_authority.yaml": "2608dda483b995539de422290371c219668a1527",
    "src/masck_one/model.py": "9e7fa6c71ac28cc45ebb502444bf6c0ea49f7894",
    "src/masck_one/interface_topology.py": "38b7c932f71a8675d45d098ac65154f98ff8bbb5",
    "src/masck_one/structural_frame.py": "bda5ba87d232c0e6a22e200975a80414a10c9a83",
    "src/masck_one/water_reservoir.py": "6c14a37d07855550f0bd502e8308ed46682bc19c",
    "src/masck_one/cleanser_storage.py": "5e087ca8b05da8352ad4800b2ef8280ea8ddcf29",
    "src/masck_one/fresh_pump_packaging.py": "40cb6fb4c3efbfcf25ed0b7d7a75a4269d90a1b4",
    "src/masck_one/distribution_manifold.py": "8f2a6c784b51734aba4d1f3809015707fc328405",
    "src/masck_one/distribution_geometry.py": "d2dd8b47bb6a2aa1edf57ac0632778228add7997",
    "src/masck_one/waste_acquisition.py": "7108fcfbe2baeaa9a343199a6817122ac2aea7ab",
    "src/masck_one/waste_pump_architecture.py": "ace02ee529070465b11832f475771125636312cb",
    "src/masck_one/waste_cartridge.py": "9dc0fe8a0ed92083c68406da3993e57e767e2483",
    "src/masck_one/realized_waste_backbone.py": "6aa79d9a613e278f32da85b4654c0e35cc09b7ca",
}
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_SHA64 = re.compile(r"^[0-9a-f]{64}$")


class ComponentRegistryError(ValueError):
    pass


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def _require_current_sources() -> None:
    for relative_path, expected in SOURCE_GIT_BLOBS.items():
        path = _REPO_ROOT / relative_path
        if not path.is_file():
            raise ComponentRegistryError(f"component-registry source missing: {relative_path}")
        actual = _git_blob_sha(path)
        if actual != expected:
            raise ComponentRegistryError(
                f"component-registry source moved at {relative_path}; expected {expected}, got {actual}"
            )


def _exact_text(value: object, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise ComponentRegistryError(f"{label} must be exact nonblank text")
    return value


def _digest(payload: object) -> str:
    return sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class ComponentRecord:
    component_id: str
    display_name: str
    owner: str
    geometry_role: str
    source_path: str
    source_blob_sha: str
    source_object_id: str
    source_digest_sha256: str | None
    coordinate_frame_id: str
    length_unit: str
    world_from_source_transform: tuple[float, ...]
    physical_material_eligible: bool
    service_state: str
    evidence_status: str
    supersedes_geometry_role: str | None = None

    def __post_init__(self) -> None:
        for label, value in (
            ("component_id", self.component_id),
            ("display_name", self.display_name),
            ("owner", self.owner),
            ("source_path", self.source_path),
            ("source_object_id", self.source_object_id),
            ("service_state", self.service_state),
            ("evidence_status", self.evidence_status),
        ):
            _exact_text(value, label)
        if not self.component_id.startswith("MASCK_ONE-COMP-"):
            raise ComponentRegistryError("component ID must use the stable MASCK_ONE-COMP namespace")
        if self.geometry_role not in GEOMETRY_ROLES:
            raise ComponentRegistryError(f"uncontrolled geometry role {self.geometry_role!r}")
        expected_blob = SOURCE_GIT_BLOBS.get(self.source_path)
        if expected_blob is None or self.source_blob_sha != expected_blob:
            raise ComponentRegistryError("component source path/blob pair is not current-main bound")
        if _SHA40.fullmatch(self.source_blob_sha) is None:
            raise ComponentRegistryError("source blob must be canonical lowercase 40-hex")
        if self.source_digest_sha256 is not None and _SHA64.fullmatch(self.source_digest_sha256) is None:
            raise ComponentRegistryError("source digest must be canonical lowercase SHA-256")
        if self.coordinate_frame_id != WORLD_FRAME_ID or self.length_unit != LENGTH_UNIT:
            raise ComponentRegistryError("component geometry must use canonical authority world millimetres")
        if type(self.world_from_source_transform) is not tuple or len(self.world_from_source_transform) != 16:
            raise ComponentRegistryError("component transform must be an exact 4x4 tuple")
        if any(type(v) not in (int, float) or not math.isfinite(float(v)) for v in self.world_from_source_transform):
            raise ComponentRegistryError("component transform must contain finite numeric values")
        if tuple(float(v) for v in self.world_from_source_transform) != IDENTITY_WORLD_TRANSFORM:
            raise ComponentRegistryError("current released producers must be consumed in canonical world without hidden transform")
        if type(self.physical_material_eligible) is not bool:
            raise ComponentRegistryError("physical material eligibility must be exact bool")
        if self.physical_material_eligible != (self.geometry_role == ROLE_PHYSICAL_MATERIAL):
            raise ComponentRegistryError("only PHYSICAL_MATERIAL records may enter the physical assembly")
        if self.geometry_role == ROLE_UNRESOLVED and self.source_digest_sha256 is not None:
            raise ComponentRegistryError("unresolved entries cannot imply realized geometry digests")
        if self.supersedes_geometry_role is not None:
            if self.supersedes_geometry_role not in GEOMETRY_ROLES:
                raise ComponentRegistryError("superseded geometry role must be controlled")
            if self.supersedes_geometry_role == self.geometry_role:
                raise ComponentRegistryError("superseded geometry role must actually differ")

    def manifest(self) -> dict[str, object]:
        self.__post_init__()
        return {
            "component_id": self.component_id,
            "display_name": self.display_name,
            "owner": self.owner,
            "geometry_role": self.geometry_role,
            "source_path": self.source_path,
            "source_blob_sha": self.source_blob_sha,
            "source_object_id": self.source_object_id,
            "source_digest_sha256": self.source_digest_sha256,
            "coordinate_frame_id": self.coordinate_frame_id,
            "length_unit": self.length_unit,
            "world_from_source_transform": list(self.world_from_source_transform),
            "physical_material_eligible": self.physical_material_eligible,
            "service_state": self.service_state,
            "evidence_status": self.evidence_status,
            "supersedes_geometry_role": self.supersedes_geometry_role,
        }


@dataclass(frozen=True, slots=True)
class CanonicalComponentRegistry:
    schema: str
    source_main_sha: str
    authority_revision: str
    authority_blob_sha: str
    coordinate_frame_id: str
    length_unit: str
    components: tuple[ComponentRecord, ...]
    physical_validation_eligible: bool
    evidence_status: str

    def __post_init__(self) -> None:
        if self.schema != SCHEMA or self.source_main_sha != SOURCE_MAIN_SHA:
            raise ComponentRegistryError("component registry is stale for released main")
        if self.authority_revision != AUTHORITY_REVISION or self.authority_blob_sha != AUTHORITY_BLOB_SHA:
            raise ComponentRegistryError("component registry authority identity is stale")
        if self.coordinate_frame_id != WORLD_FRAME_ID or self.length_unit != LENGTH_UNIT:
            raise ComponentRegistryError("registry frame/unit identity changed")
        if type(self.components) is not tuple or not self.components:
            raise ComponentRegistryError("registry requires immutable nonempty components")
        ids = tuple(item.component_id for item in self.components)
        if ids != tuple(sorted(ids)) or len(ids) != len(set(ids)):
            raise ComponentRegistryError("registry component IDs must be unique and deterministically sorted")
        for item in self.components:
            item.__post_init__()
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise ComponentRegistryError("digital registry cannot be physical validation")
        _exact_text(self.evidence_status, "registry evidence status")
        if self.physical_material_model_component_names != ("rigid_shell",):
            raise ComponentRegistryError(
                "released current-main physical material must be exactly rigid_shell; references/proxies cannot enter"
            )
        by_id = {item.component_id: item for item in self.components}
        required_unresolved = (
            "MASCK_ONE-COMP-CHARGING-INTERFACE",
            "MASCK_ONE-COMP-DRY-BAY",
            "MASCK_ONE-COMP-HARNESS",
            "MASCK_ONE-COMP-PCB",
            "MASCK_ONE-COMP-QUICK-RELEASE-RIGHT",
            "MASCK_ONE-COMP-RETENTION-HALO",
            "MASCK_ONE-COMP-WASTE-CARTRIDGE-BODY",
            "MASCK_ONE-COMP-WASTE-PUMP",
            "MASCK_ONE-COMP-WATER-PUMP",
        )
        for component_id in required_unresolved:
            if by_id.get(component_id) is None or by_id[component_id].geometry_role != ROLE_UNRESOLVED:
                raise ComponentRegistryError(f"{component_id} must remain fail-closed until released geometry exists")
        if by_id["MASCK_ONE-COMP-MIXED-WASTE-ROUTES"].geometry_role != ROLE_REALIZED_CENTERLINE:
            raise ComponentRegistryError("released mixed-waste routes must consume realized centerlines, not stale topology")
        if by_id["MASCK_ONE-COMP-WASTE-CARTRIDGE-PACKAGE"].geometry_role != ROLE_PACKAGE_REFERENCE:
            raise ComponentRegistryError("waste cartridge package must remain non-material reference geometry")

    @property
    def physical_material_model_component_names(self) -> tuple[str, ...]:
        return tuple(
            item.source_object_id
            for item in self.components
            if item.physical_material_eligible and item.source_path == "src/masck_one/model.py"
        )

    @property
    def unresolved_component_ids(self) -> tuple[str, ...]:
        return tuple(item.component_id for item in self.components if item.geometry_role == ROLE_UNRESOLVED)

    @property
    def registry_sha256(self) -> str:
        return _digest(self.manifest(include_sha=False))

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": self.schema,
            "source_main_sha": self.source_main_sha,
            "authority_revision": self.authority_revision,
            "authority_blob_sha": self.authority_blob_sha,
            "coordinate_frame_id": self.coordinate_frame_id,
            "length_unit": self.length_unit,
            "geometry_roles": list(GEOMETRY_ROLES),
            "source_git_blobs": dict(sorted(SOURCE_GIT_BLOBS.items())),
            "components": [item.manifest() for item in self.components],
            "physical_material_model_component_names": list(self.physical_material_model_component_names),
            "unresolved_component_ids": list(self.unresolved_component_ids),
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            payload["registry_sha256"] = _digest(payload)
        return payload


def _record(
    component_id: str,
    display_name: str,
    owner: str,
    role: str,
    source_path: str,
    source_object_id: str,
    *,
    digest: str | None = None,
    service_state: str,
    evidence_status: str,
    supersedes_geometry_role: str | None = None,
) -> ComponentRecord:
    return ComponentRecord(
        component_id=component_id,
        display_name=display_name,
        owner=owner,
        geometry_role=role,
        source_path=source_path,
        source_blob_sha=SOURCE_GIT_BLOBS[source_path],
        source_object_id=source_object_id,
        source_digest_sha256=digest,
        coordinate_frame_id=WORLD_FRAME_ID,
        length_unit=LENGTH_UNIT,
        world_from_source_transform=IDENTITY_WORLD_TRANSFORM,
        physical_material_eligible=role == ROLE_PHYSICAL_MATERIAL,
        service_state=service_state,
        evidence_status=evidence_status,
        supersedes_geometry_role=supersedes_geometry_role,
    )


def build_current_component_registry(
    model: MasckOneModel | None = None,
    waste_release: Cell4WasteBackboneRelease | None = None,
) -> CanonicalComponentRegistry:
    _require_current_sources()
    model = model or build_model()
    revision = str(model.authority.get("project", "authority_revision"))
    if revision != AUTHORITY_REVISION:
        raise ComponentRegistryError("authority revision moved; component registry requires rebind")

    model_components = {item.name: item for item in model.components}
    expected_model_components = {
        "rigid_shell",
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
    }
    if set(model_components) != expected_model_components:
        raise ComponentRegistryError(
            "released model component identity changed; registry must be reconciled before use"
        )
    if model_components["rigid_shell"].status != "CAD_BASELINE":
        raise ComponentRegistryError("rigid shell maturity changed")
    if model_components["nasal_lobe_membrane_reference"].status != "DEVELOPMENT_LOCAL_THICKNESS_REFERENCE":
        raise ComponentRegistryError("nasal development-reference maturity changed")
    for name in ("actuator_envelope_1", "actuator_envelope_2", "actuator_envelope_3", "actuator_envelope_4"):
        if model_components[name].status != "ALPHA_PHYSICS_REFERENCE":
            raise ComponentRegistryError("actuator package-reference maturity changed")
    if model_components["water_reservoir_envelope"].status != "ENGINEERING_BASELINE_ENVELOPE":
        raise ComponentRegistryError("water package-reference maturity changed")
    if model_components["waste_cartridge_envelope"].status != "ENGINEERING_BASELINE_ENVELOPE":
        raise ComponentRegistryError("waste cartridge package-reference maturity changed")
    if model_components["battery_reference_envelope"].status != "PACKAGING_BENCHMARK_NOT_PRODUCTION_FREEZE":
        raise ComponentRegistryError("battery package-reference maturity changed")
    for name in ("visual_eye_left", "visual_eye_right", "visual_mouth", "visual_nostril_left", "visual_nostril_right"):
        if model_components[name].status != "REFERENCE_ONLY":
            raise ComponentRegistryError("protected review geometry maturity changed")

    waste_release = waste_release or build_current_cell4_waste_backbone_release()
    waste_manifest = waste_release.manifest()
    waste_digest = str(waste_manifest["realization_manifest_sha256"])
    if _SHA64.fullmatch(waste_digest) is None:
        raise ComponentRegistryError("released mixed-waste realization digest is malformed")

    records: list[ComponentRecord] = [
        _record(
            "MASCK_ONE-COMP-RIGID-SHELL",
            "Rigid exterior shell",
            OWNER_CELL_2,
            ROLE_PHYSICAL_MATERIAL,
            "src/masck_one/model.py",
            "rigid_shell",
            service_state="ASSEMBLY_MATERIAL_RELEASED_SERVICE_SPLITS_NOT_YET_CLOSED",
            evidence_status="CURRENT_MAIN_BREP_DIGITAL_ONLY_NOT_TOOLING_OR_PHYSICAL_VALIDATION",
        ),
        _record(
            "MASCK_ONE-COMP-FACIAL-INTERFACE",
            "Compliant facial interface",
            OWNER_CELL_2,
            ROLE_TOPOLOGY,
            "src/masck_one/interface_topology.py",
            "COMPLIANT_INTERFACE_TOPOLOGY",
            digest=model.compliant_interface_topology.topology_sha256,
            service_state="TOPOLOGY_ONLY_FINAL_MATERIAL_JOIN_AND_SERVICE_UNRESOLVED",
            evidence_status="CONTACT_TOPOLOGY_ONLY_NOT_FIT_PRESSURE_COMFORT_OR_MATERIAL_EVIDENCE",
        ),
        _record(
            "MASCK_ONE-COMP-NASAL-LOBE-REFERENCE",
            "Nasal lobe local-thickness reference",
            OWNER_CELL_2,
            ROLE_DEVELOPMENT_REFERENCE,
            "src/masck_one/model.py",
            "nasal_lobe_membrane_reference",
            service_state="REFERENCE_ONLY_NOT_SERVICE_PART",
            evidence_status="LOCAL_THICKNESS_DEVELOPMENT_REFERENCE_NOT_FINAL_ANATOMICAL_MEMBRANE",
        ),
        _record(
            "MASCK_ONE-COMP-STRUCTURAL-FRAME",
            "Structural reaction frame",
            OWNER_CELL_3,
            ROLE_TOPOLOGY,
            "src/masck_one/structural_frame.py",
            "MASCK_ONE-FRAME-LOADPATH-PERIMETER-REACTION-LOOP",
            service_state="TOPOLOGY_ONLY_3D_MEMBER_JOIN_AND_TOOL_ACCESS_UNRESOLVED",
            evidence_status="STRUCTURAL_TOPOLOGY_ONLY_NOT_MEMBER_BREP_LOAD_MODAL_OR_FATIGUE_EVIDENCE",
        ),
        _record(
            "MASCK_ONE-COMP-WATER-RESERVOIR-PACKAGE",
            "Fresh-water package envelope",
            OWNER_CELL_4,
            ROLE_PACKAGE_REFERENCE,
            "src/masck_one/model.py",
            "water_reservoir_envelope",
            service_state="PACKAGE_REFERENCE_REFILL_PORT_BODY_WALL_AND_LID_SERVICE_UNRESOLVED",
            evidence_status="PACKAGE_ENVELOPE_NOT_RESERVOIR_MATERIAL_OR_USABLE_VOLUME_EVIDENCE",
        ),
        _record(
            "MASCK_ONE-COMP-WATER-RESERVOIR",
            "Fresh-water reservoir architecture",
            OWNER_CELL_4,
            ROLE_TOPOLOGY,
            "src/masck_one/water_reservoir.py",
            WATER_RESERVOIR_ID,
            service_state="ARCHITECTURE_ONLY_BODY_PORT_JOIN_AND_SERVICE_GEOMETRY_UNRESOLVED",
            evidence_status="STORAGE_ARCHITECTURE_ONLY_NOT_LEAK_OR_USABLE_VOLUME_EVIDENCE",
        ),
        _record(
            "MASCK_ONE-COMP-CLEANSER-RESERVOIR",
            "Cleanser reservoir architecture",
            OWNER_CELL_4,
            ROLE_TOPOLOGY,
            "src/masck_one/cleanser_storage.py",
            CLEANSER_STORAGE_ID,
            service_state="ARCHITECTURE_ONLY_BODY_REFILL_PURGE_AND_SERVICE_GEOMETRY_UNRESOLVED",
            evidence_status="STORAGE_ARCHITECTURE_ONLY_NOT_COMPATIBILITY_HYGIENE_OR_PHYSICAL_EVIDENCE",
        ),
        _record(
            "MASCK_ONE-COMP-WATER-PUMP",
            "Fresh-water metering pump",
            OWNER_CELL_4,
            ROLE_UNRESOLVED,
            "src/masck_one/fresh_pump_packaging.py",
            STATION_WATER,
            service_state="PACKAGE_SELECTION_PLACEMENT_CONNECTORS_AND_SERVICE_UNRESOLVED",
            evidence_status="STATION_IDENTITY_ONLY_NO_RELEASED_PACKAGE_BREP_OR_PERFORMANCE_EVIDENCE",
        ),
        _record(
            "MASCK_ONE-COMP-CLEANSER-PUMP",
            "Cleanser metering pump",
            OWNER_CELL_4,
            ROLE_UNRESOLVED,
            "src/masck_one/fresh_pump_packaging.py",
            STATION_CLEANSER,
            service_state="PACKAGE_SELECTION_PLACEMENT_CONNECTORS_AND_SERVICE_UNRESOLVED",
            evidence_status="STATION_IDENTITY_ONLY_NO_RELEASED_PACKAGE_BREP_OR_PERFORMANCE_EVIDENCE",
        ),
        _record(
            "MASCK_ONE-COMP-FRESH-MANIFOLD",
            "Fresh-fluid distribution manifold",
            OWNER_CELL_4,
            ROLE_TOPOLOGY,
            "src/masck_one/distribution_manifold.py",
            "DISTRIBUTION_MANIFOLD_I23",
            service_state="TOPOLOGY_ONLY_BODY_COVER_JOIN_AND_TOOL_ACCESS_UNRESOLVED",
            evidence_status="MANIFOLD_TOPOLOGY_ONLY_NOT_FLOW_BALANCE_OR_PHYSICAL_DISTRIBUTION_EVIDENCE",
        ),
        _record(
            "MASCK_ONE-COMP-FRESH-DISTRIBUTION",
            "Fresh-fluid distribution routes",
            OWNER_CELL_4,
            ROLE_TOPOLOGY,
            "src/masck_one/distribution_geometry.py",
            "DISTRIBUTION_GEOMETRY_I24",
            service_state="OUTLET_DATUMS_ONLY_ROUTE_SECTION_SUPPORT_AND_SERVICE_UNRESOLVED",
            evidence_status="DEVELOPMENT_ROUTE_TOPOLOGY_NOT_SELECTED_TUBE_CHANNEL_OR_FLOW_EVIDENCE",
        ),
        _record(
            "MASCK_ONE-COMP-WASTE-ACQUISITION",
            "Mixed-waste acquisition architecture",
            OWNER_CELL_4,
            ROLE_TOPOLOGY,
            "src/masck_one/waste_acquisition.py",
            "WASTE_ACQUISITION_I25",
            service_state="TOPOLOGY_ONLY_GUTTER_GEOMETRY_DRAIN_DRY_AND_SERVICE_UNRESOLVED",
            evidence_status="ACQUISITION_TOPOLOGY_ONLY_NOT_RECOVERY_RESIDUAL_OR_HYGIENE_EVIDENCE",
        ),
        _record(
            "MASCK_ONE-COMP-WASTE-PUMP",
            "Mixed-phase waste pump",
            OWNER_CELL_4,
            ROLE_UNRESOLVED,
            "src/masck_one/waste_pump_architecture.py",
            STATION_WASTE,
            service_state="PACKAGE_SELECTION_PLACEMENT_CONNECTORS_AND_SERVICE_UNRESOLVED",
            evidence_status="STATION_IDENTITY_ONLY_NO_RELEASED_PUMP_BREP_OR_HYDRAULIC_EVIDENCE",
        ),
        _record(
            "MASCK_ONE-COMP-WASTE-BACKFLOW-BARRIER",
            "Passive waste backflow barrier",
            OWNER_CELL_4,
            ROLE_TOPOLOGY,
            "src/masck_one/waste_pump_architecture.py",
            BARRIER_WASTE,
            service_state="ROUTE_STAGE_ONLY_COMPONENT_SELECTION_PLACEMENT_AND_SERVICE_UNRESOLVED",
            evidence_status="PASSIVE_BARRIER_TOPOLOGY_ONLY_NOT_SELECTED_COMPONENT_OR_REVERSE_FLOW_EVIDENCE",
        ),
        _record(
            "MASCK_ONE-COMP-MIXED-WASTE-ROUTES",
            "Mixed-waste backbone centerlines",
            OWNER_CELL_4,
            ROLE_REALIZED_CENTERLINE,
            "src/masck_one/realized_waste_backbone.py",
            "CELL4_MIXED_WASTE_BACKBONE",
            digest=waste_digest,
            service_state="CENTERLINES_REALIZED_SELECTED_ROUTE_MATERIAL_SUPPORTS_BEND_AND_SERVICE_STILL_UNRESOLVED",
            evidence_status="WORLD_COORDINATE_CENTERLINE_GEOMETRY_ONLY_NOT_SELECTED_TUBING_HYDRAULIC_OR_SERVICE_EVIDENCE",
            supersedes_geometry_role=ROLE_TOPOLOGY,
        ),
        _record(
            "MASCK_ONE-COMP-WASTE-CARTRIDGE-PACKAGE",
            "Waste cartridge external package envelope",
            OWNER_CELL_4,
            ROLE_PACKAGE_REFERENCE,
            "src/masck_one/model.py",
            "waste_cartridge_envelope",
            service_state="PACKAGE_REFERENCE_ONLY_BODY_CAVITY_SEAL_KEY_RETENTION_AND_SERVICE_UNRESOLVED",
            evidence_status="AUTHORITY_EXTERNAL_ENVELOPE_ONLY_EXCLUDED_FROM_PHYSICAL_ASSEMBLY",
        ),
        _record(
            "MASCK_ONE-COMP-WASTE-CARTRIDGE-ARCHITECTURE",
            "Waste cartridge architecture",
            OWNER_CELL_4,
            ROLE_TOPOLOGY,
            "src/masck_one/waste_cartridge.py",
            CARTRIDGE_ID,
            service_state="SERVICE_INTERFACE_TOPOLOGY_ONLY_TRAJECTORY_AND_RETENTION_UNRESOLVED",
            evidence_status="CARTRIDGE_TOPOLOGY_ONLY_NOT_BODY_CAPACITY_SEAL_HYGIENE_OR_WET_HAND_SERVICE_EVIDENCE",
        ),
        _record(
            "MASCK_ONE-COMP-WASTE-CARTRIDGE-BODY",
            "Waste cartridge physical body",
            OWNER_CELL_4,
            ROLE_UNRESOLVED,
            "src/masck_one/waste_cartridge.py",
            CARTRIDGE_ID,
            service_state="BODY_CAVITY_SEAL_KEY_RETENTION_AND_NONTELEPORTING_SERVICE_GEOMETRY_UNRESOLVED",
            evidence_status="NO_RELEASED_PHYSICAL_BODY_BREP_PACKAGE_BOX_MUST_NOT_SUBSTITUTE",
        ),
        _record(
            "MASCK_ONE-COMP-BATTERY-PACKAGE",
            "Battery packaging benchmark",
            OWNER_CELL_4,
            ROLE_PACKAGE_REFERENCE,
            "src/masck_one/model.py",
            "battery_reference_envelope",
            service_state="PACKAGE_BENCHMARK_ONLY_CARRIER_CONNECTOR_SWELL_AND_SERVICE_UNRESOLVED",
            evidence_status="AUTHORITY_PACKAGING_BENCHMARK_NOT_PRODUCTION_CELL_OR_SAFETY_EVIDENCE",
        ),
        _record(
            "MASCK_ONE-COMP-RETENTION-HALO",
            "Retention halo",
            OWNER_CELL_3,
            ROLE_UNRESOLVED,
            "src/masck_one/structural_frame.py",
            RESERVATION_RETENTION,
            service_state="RELEASED_FRAME_RESERVATION_ONLY_HALO_BREP_ATTACHMENT_AND_FIT_ADJUSTMENT_UNRESOLVED",
            evidence_status="NO_RELEASED_MAIN_RETENTION_MATERIAL_GEOMETRY_OR_PHYSICAL_FORCE_EVIDENCE",
        ),
        _record(
            "MASCK_ONE-COMP-QUICK-RELEASE-RIGHT",
            "Right unpowered emergency quick release",
            OWNER_CELL_3,
            ROLE_UNRESOLVED,
            "src/masck_one/structural_frame.py",
            RESERVATION_RETENTION,
            service_state="MECHANISM_BREP_LOAD_PATH_WET_ONE_HAND_TRAJECTORY_AND_TOOL_ACCESS_UNRESOLVED",
            evidence_status="FROZEN_SAFETY_REQUIREMENT_NO_RELEASED_MAIN_MECHANISM_OR_PHYSICAL_TIME_FORCE_EVIDENCE",
        ),
        _record(
            "MASCK_ONE-COMP-PCB",
            "Control and power PCB",
            OWNER_CELL_4,
            ROLE_UNRESOLVED,
            "src/masck_one/structural_frame.py",
            RESERVATION_HMI_ELECTRONICS,
            service_state="PCB_OUTLINE_MOUNT_CONNECTORS_AND_SERVICE_UNRESOLVED",
            evidence_status="DRY_SIDE_RESERVATION_ONLY_NO_RELEASED_PCB_PACKAGE",
        ),
        _record(
            "MASCK_ONE-COMP-HARNESS",
            "Electrical harness",
            OWNER_CELL_4,
            ROLE_UNRESOLVED,
            "src/masck_one/structural_frame.py",
            RESERVATION_HMI_ELECTRONICS,
            service_state="ENDPOINTS_ROUTE_CONNECTORS_STRAIN_RELIEF_AND_SERVICE_UNRESOLVED",
            evidence_status="HARNESS_FUNCTION_REQUIRED_NO_RELEASED_ROUTE_OR_CONNECTOR_GEOMETRY",
        ),
        _record(
            "MASCK_ONE-COMP-CHARGING-INTERFACE",
            "Charging interface",
            OWNER_CELL_4,
            ROLE_UNRESOLVED,
            "src/masck_one/structural_frame.py",
            RESERVATION_HMI_ELECTRONICS,
            service_state="CONNECTOR_SEAL_ACCESS_AND_SERVICE_UNRESOLVED",
            evidence_status="CHARGING_FUNCTION_REQUIRED_NO_RELEASED_MAIN_INTERFACE_GEOMETRY",
        ),
        _record(
            "MASCK_ONE-COMP-DRY-BAY",
            "Electronics dry bay",
            OWNER_CELL_4,
            ROLE_UNRESOLVED,
            "src/masck_one/structural_frame.py",
            RESERVATION_HMI_ELECTRONICS,
            service_state="ENCLOSURE_JOIN_SEAL_DRAIN_AND_SERVICE_UNRESOLVED",
            evidence_status="DRY_BAY_RESERVATION_ONLY_NO_RELEASED_ENCLOSURE_MATERIAL_GEOMETRY",
        ),
        _record(
            "MASCK_ONE-COMP-WET-DRY-BULKHEAD",
            "Wet-dry bulkhead",
            OWNER_CELL_4,
            ROLE_UNRESOLVED,
            "src/masck_one/structural_frame.py",
            RESERVATION_HMI_ELECTRONICS,
            service_state="BULKHEAD_SEALS_PENETRATIONS_CONNECTORS_AND_SERVICE_UNRESOLVED",
            evidence_status="WET_DRY_INTERFACE_REQUIRED_NO_RELEASED_BULKHEAD_BREP",
        ),
        _record(
            "MASCK_ONE-COMP-HMI",
            "Physical HMI package",
            OWNER_CELL_4,
            ROLE_UNRESOLVED,
            "src/masck_one/structural_frame.py",
            RESERVATION_HMI_ELECTRONICS,
            service_state="CONTROL_LAND_MEMBRANE_CAP_WINDOW_SEAL_AND_WET_FINGER_ACCESS_UNRESOLVED",
            evidence_status="HMI_FUNCTION_RESERVED_NO_RELEASED_PHYSICAL_HMI_GEOMETRY",
        ),
        _record(
            "MASCK_ONE-COMP-WARM",
            "WARM thermal package",
            OWNER_CELL_4,
            ROLE_UNRESOLVED,
            "src/masck_one/structural_frame.py",
            RESERVATION_THERMAL,
            service_state="HEATER_SENSOR_SPREADER_INSULATION_MOUNT_AND_SERVICE_UNRESOLVED",
            evidence_status="THERMAL_RESERVATION_ONLY_NO_RELEASED_WARM_PACKAGE_OR_SAFETY_EVIDENCE",
        ),
        _record(
            "MASCK_ONE-COMP-DRAIN-DRY-PATH",
            "Drain and dry path",
            OWNER_CELL_4,
            ROLE_UNRESOLVED,
            "src/masck_one/structural_frame.py",
            RESERVATION_WASTE,
            service_state="LOW_POINTS_CHANNELS_EXIT_AND_NONTELEPORTING_DRYING_ACCESS_UNRESOLVED",
            evidence_status="DRAIN_DRY_REQUIREMENT_ONLY_NO_RELEASED_ROUTE_GEOMETRY_OR_HYGIENE_EVIDENCE",
        ),
    ]

    for index in range(1, 5):
        records.append(
            _record(
                f"MASCK_ONE-COMP-ACTUATOR-{index:02d}-PACKAGE",
                f"Actuator zone {index} package reference",
                OWNER_CELL_3,
                ROLE_PACKAGE_REFERENCE,
                "src/masck_one/model.py",
                f"actuator_envelope_{index}",
                service_state="PACKAGE_REFERENCE_ONLY_MOUNT_COUPLING_STOPS_AND_SERVICE_UNRESOLVED",
                evidence_status="SUPPLIER_SIZE_REFERENCE_NOT_SELECTED_ACTUATOR_MATERIAL_OR_PERFORMANCE_EVIDENCE",
            )
        )

    protected_ids = (
        ("EYE-LEFT", "visual_eye_left"),
        ("EYE-RIGHT", "visual_eye_right"),
        ("MOUTH", "visual_mouth"),
        ("NOSTRIL-LEFT", "visual_nostril_left"),
        ("NOSTRIL-RIGHT", "visual_nostril_right"),
    )
    for suffix, source_object in protected_ids:
        records.append(
            _record(
                f"MASCK_ONE-COMP-PROTECTED-{suffix}",
                f"Protected {suffix.lower()} review keepout",
                OWNER_CELL_1,
                ROLE_PROTECTED_REFERENCE,
                "src/masck_one/model.py",
                source_object,
                service_state="REFERENCE_ONLY_NEVER_ASSEMBLY_MATERIAL",
                evidence_status="AUTHORITY_DERIVED_PROTECTED_REVIEW_GEOMETRY_NOT_ANATOMICAL_OR_PHYSICAL_EVIDENCE",
            )
        )

    records.sort(key=lambda item: item.component_id)
    return CanonicalComponentRegistry(
        schema=SCHEMA,
        source_main_sha=SOURCE_MAIN_SHA,
        authority_revision=revision,
        authority_blob_sha=AUTHORITY_BLOB_SHA,
        coordinate_frame_id=WORLD_FRAME_ID,
        length_unit=LENGTH_UNIT,
        components=tuple(records),
        physical_validation_eligible=False,
        evidence_status=(
            "CURRENT_RELEASED_COMPONENT_ID_GEOMETRY_ROLE_SOURCE_AND_MATERIAL_BOUNDARY_ONLY_"
            "NOT_FIT_COMFORT_HYDRAULIC_ELECTRICAL_THERMAL_HYGIENE_DURABILITY_OR_PHYSICAL_VALIDATION"
        ),
    )
