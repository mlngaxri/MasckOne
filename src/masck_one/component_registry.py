from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import re
from typing import Iterable

from .actuator_frames import ZONE_IDS
from .boundary_release import build_verified_interface_boundary_topology
from .cleanser_storage import (
    CLEANSER_STORAGE_ID,
    PORT_IDS as CLEANSER_PORT_IDS,
    build_cleanser_storage_architecture,
)
from .distribution_geometry import build_distribution_geometry_architecture
from .distribution_manifold import (
    BRANCH_IDS,
    INLET_CLEANSER,
    INLET_FRESH_WATER,
    build_distribution_manifold_architecture,
)
from .fresh_pump_packaging import (
    INTERFACE_CLEANSER_PUMP_OUTLET,
    INTERFACE_WATER_PUMP_OUTLET,
    ROUTE_IDS as FRESH_ROUTE_IDS,
    STATION_CLEANSER,
    STATION_WATER,
    build_fresh_pump_packaging_architecture,
)
from .interface_attachment import build_interface_attachment_architecture
from .interface_topology import (
    ZONE_GENERAL_FACE,
    ZONE_OPENING_EYE_LEFT,
    ZONE_OPENING_EYE_RIGHT,
    ZONE_OPENING_MOUTH,
    ZONE_OPENING_NOSTRIL_LEFT,
    ZONE_OPENING_NOSTRIL_RIGHT,
    ZONE_T_FOREHEAD,
    ZONE_T_NOSE_PHILTRUM,
)
from .iteration25_source_integrity import canonical_iteration25_sources
from .model import MasckOneModel, build_model
from .structural_frame import (
    DATUM_IDS as FRAME_DATUM_IDS,
    RESERVATION_ACTUATION,
    RESERVATION_FRESH_FLUID,
    RESERVATION_HMI_ELECTRONICS,
    RESERVATION_RETENTION,
    RESERVATION_THERMAL,
    RESERVATION_WASTE,
    build_structural_frame_topology,
)
from .waste_acquisition import (
    REGIONS as WASTE_ACQUISITION_REGIONS,
    ROUTE_DESTINATION as WASTE_ACQUISITION_DESTINATION,
    build_waste_acquisition_architecture,
)
from .waste_cartridge import (
    CARTRIDGE_ID,
    INTERFACE_KEY as CARTRIDGE_INTERFACE_KEY,
    INTERFACE_SEAL as CARTRIDGE_INTERFACE_SEAL,
    INTERFACE_SERVICE as CARTRIDGE_INTERFACE_SERVICE,
    build_waste_cartridge_architecture,
)
from .waste_pump_architecture import (
    BARRIER_WASTE,
    INTERFACE_BARRIER_OUTLET,
    INTERFACE_CARTRIDGE_INLET_I27,
    INTERFACE_PUMP_OUTLET as WASTE_PUMP_OUTLET,
    ROUTE_IDS as WASTE_ROUTE_IDS,
    STATION_WASTE,
    build_waste_pump_architecture,
)
from .water_reservoir import (
    PORT_IDS as WATER_PORT_IDS,
    WATER_RESERVOIR_ID,
    build_water_reservoir_architecture,
)

REGISTRY_SCHEMA = "MASCK_ONE_WHOLE_PRODUCT_COMPONENT_REGISTRY_V1"
SOURCE_MAIN_SHA = "5fce2a43a34d8be49256677a35af60c906dc1653"
AUTHORITY_REVISION = "2026-08-30-R1"
AUTHORITY_BLOB_SHA = "2608dda483b995539de422290371c219668a1527"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"

REALIZED_SOLID = "REALIZED_SOLID"
CONTROLLED_ENVELOPE = "CONTROLLED_ENVELOPE"
TOPOLOGY_ONLY = "TOPOLOGY_ONLY"
UNRESOLVED = "UNRESOLVED"
STATUS_VOCABULARY = (
    REALIZED_SOLID,
    CONTROLLED_ENVELOPE,
    TOPOLOGY_ONLY,
    UNRESOLVED,
)

OWNER_CELL_1 = "CELL_1_INTEGRATION"
OWNER_CELL_2 = "CELL_2_EXTERIOR_INTERFACE"
OWNER_CELL_3 = "CELL_3_MECHANISMS_RETENTION"
OWNER_CELL_4 = "CELL_4_FLUID_POWER_HMI_THERMAL"
OWNER_VOCABULARY = (
    OWNER_CELL_1,
    OWNER_CELL_2,
    OWNER_CELL_3,
    OWNER_CELL_4,
)

SOURCE_GIT_BLOB_BY_MODULE = {
    "config/masck_one_authority.yaml": "2608dda483b995539de422290371c219668a1527",
    "src/masck_one/model.py": "9e7fa6c71ac28cc45ebb502444bf6c0ea49f7894",
    "src/masck_one/interface_topology.py": "38b7c932f71a8675d45d098ac65154f98ff8bbb5",
    "src/masck_one/structural_frame.py": "bda5ba87d232c0e6a22e200975a80414a10c9a83",
    "src/masck_one/actuator_frames.py": "4c2013f994bdc9e084fe227eb5e166f973500ebb",
    "src/masck_one/water_reservoir.py": "6c14a37d07855550f0bd502e8308ed46682bc19c",
    "src/masck_one/cleanser_storage.py": "5e087ca8b05da8352ad4800b2ef8280ea8ddcf29",
    "src/masck_one/fresh_pump_packaging.py": "40cb6fb4c3efbfcf25ed0b7d7a75a4269d90a1b4",
    "src/masck_one/distribution_manifold.py": "8f2a6c784b51734aba4d1f3809015707fc328405",
    "src/masck_one/distribution_geometry.py": "d2dd8b47bb6a2aa1edf57ac0632778228add7997",
    "src/masck_one/waste_acquisition.py": "7108fcfbe2baeaa9a343199a6817122ac2aea7ab",
    "src/masck_one/waste_pump_architecture.py": "ace02ee529070465b11832f475771125636312cb",
    "src/masck_one/waste_cartridge.py": "9dc0fe8a0ed92083c68406da3993e57e767e2483",
}
_GIT_BLOB_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class ComponentRegistryError(ValueError):
    """Raised when component identity or maturity semantics would become ambiguous."""


@dataclass(frozen=True, slots=True)
class InterfaceDatum:
    datum_id: str
    datum_type: str
    status: str
    xyz_mm: tuple[float, float, float] | None = None
    direction_xyz: tuple[float, float, float] | None = None

    def __post_init__(self) -> None:
        for label, value in (
            ("datum_id", self.datum_id),
            ("datum_type", self.datum_type),
            ("status", self.status),
        ):
            if type(value) is not str or not value or value != value.strip():
                raise ComponentRegistryError(f"{label} must be exact nonblank text")
        if self.xyz_mm is not None and (
            type(self.xyz_mm) is not tuple
            or len(self.xyz_mm) != 3
            or any(type(value) not in (int, float) for value in self.xyz_mm)
        ):
            raise ComponentRegistryError("datum xyz must be an exact three-value tuple when defined")
        if self.direction_xyz is not None and (
            type(self.direction_xyz) is not tuple
            or len(self.direction_xyz) != 3
            or any(type(value) not in (int, float) for value in self.direction_xyz)
        ):
            raise ComponentRegistryError("datum direction must be an exact three-value tuple when defined")

    def manifest(self) -> dict[str, object]:
        return {
            "datum_id": self.datum_id,
            "datum_type": self.datum_type,
            "status": self.status,
            "xyz_mm": None if self.xyz_mm is None else list(self.xyz_mm),
            "direction_xyz": None if self.direction_xyz is None else list(self.direction_xyz),
        }


@dataclass(frozen=True, slots=True)
class ComponentRecord:
    component_id: str
    display_name: str
    owner: str
    source_module: str
    source_git_blob_sha: str
    source_object_id: str
    status: str
    interface_datums: tuple[InterfaceDatum, ...]
    source_digest_sha256: str | None
    evidence_status: str

    def __post_init__(self) -> None:
        for label, value in (
            ("component_id", self.component_id),
            ("display_name", self.display_name),
            ("source_module", self.source_module),
            ("source_object_id", self.source_object_id),
            ("evidence_status", self.evidence_status),
        ):
            if type(value) is not str or not value or value != value.strip():
                raise ComponentRegistryError(f"{label} must be exact nonblank text")
        if self.owner not in OWNER_VOCABULARY:
            raise ComponentRegistryError(f"uncontrolled owner {self.owner!r}")
        if self.status not in STATUS_VOCABULARY:
            raise ComponentRegistryError(f"uncontrolled component status {self.status!r}")
        if self.source_module not in SOURCE_GIT_BLOB_BY_MODULE:
            raise ComponentRegistryError(f"source module {self.source_module!r} is not provenance-bound")
        if self.source_git_blob_sha != SOURCE_GIT_BLOB_BY_MODULE[self.source_module]:
            raise ComponentRegistryError(
                f"{self.component_id} source blob does not match controlled module identity"
            )
        if _GIT_BLOB_RE.fullmatch(self.source_git_blob_sha) is None:
            raise ComponentRegistryError("component source blob must be a canonical git blob SHA")
        if self.source_digest_sha256 is not None and _SHA256_RE.fullmatch(self.source_digest_sha256) is None:
            raise ComponentRegistryError("component source digest must be canonical SHA-256")
        if type(self.interface_datums) is not tuple or not self.interface_datums:
            raise ComponentRegistryError(f"{self.component_id} must expose at least one interface datum")
        datum_ids = tuple(item.datum_id for item in self.interface_datums)
        if len(datum_ids) != len(set(datum_ids)):
            raise ComponentRegistryError(f"{self.component_id} interface datum IDs cannot repeat")
        if self.status == UNRESOLVED and self.source_digest_sha256 is not None:
            raise ComponentRegistryError(
                f"{self.component_id} unresolved hardware cannot imply a realized geometry digest"
            )

    def manifest(self) -> dict[str, object]:
        return {
            "component_id": self.component_id,
            "display_name": self.display_name,
            "owner": self.owner,
            "source_module": self.source_module,
            "source_git_blob_sha": self.source_git_blob_sha,
            "source_object_id": self.source_object_id,
            "status": self.status,
            "interface_datums": [item.manifest() for item in self.interface_datums],
            "source_digest_sha256": self.source_digest_sha256,
            "evidence_status": self.evidence_status,
        }


@dataclass(frozen=True, slots=True)
class WholeProductComponentRegistry:
    schema: str
    source_main_sha: str
    authority_revision: str
    authority_blob_sha: str
    coordinate_frame_id: str
    components: tuple[ComponentRecord, ...]
    physical_validation_eligible: bool
    evidence_status: str

    def __post_init__(self) -> None:
        if self.schema != REGISTRY_SCHEMA:
            raise ComponentRegistryError("unexpected component-registry schema")
        if self.source_main_sha != SOURCE_MAIN_SHA:
            raise ComponentRegistryError("component registry is not bound to reconstructed main")
        if self.authority_revision != AUTHORITY_REVISION or self.authority_blob_sha != AUTHORITY_BLOB_SHA:
            raise ComponentRegistryError("component registry authority identity is stale")
        if self.coordinate_frame_id != WORLD_FRAME_ID:
            raise ComponentRegistryError("component registry must use the canonical authority world frame")
        if type(self.components) is not tuple or not self.components:
            raise ComponentRegistryError("component registry requires an immutable nonempty component tuple")
        ids = tuple(item.component_id for item in self.components)
        if len(ids) != len(set(ids)):
            raise ComponentRegistryError("component IDs must be globally unique")
        if tuple(sorted(ids)) != ids:
            raise ComponentRegistryError("component registry order must be deterministic by component ID")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise ComponentRegistryError("digital component registry cannot be physical validation evidence")
        if type(self.evidence_status) is not str or not self.evidence_status:
            raise ComponentRegistryError("registry evidence status must be explicit")
        self._validate_maturity_semantics()

    def _validate_maturity_semantics(self) -> None:
        by_id = {item.component_id: item for item in self.components}
        required = {
            "MASCK_ONE-COMP-ACTUATOR-01",
            "MASCK_ONE-COMP-ACTUATOR-02",
            "MASCK_ONE-COMP-ACTUATOR-03",
            "MASCK_ONE-COMP-ACTUATOR-04",
            "MASCK_ONE-COMP-BATTERY",
            "MASCK_ONE-COMP-CLEANSER-RESERVOIR",
            "MASCK_ONE-COMP-FACIAL-INTERFACE",
            "MASCK_ONE-COMP-FRESH-MANIFOLD",
            "MASCK_ONE-COMP-PCB",
            "MASCK_ONE-COMP-RETENTION-HALO",
            "MASCK_ONE-COMP-RIGID-SHELL",
            "MASCK_ONE-COMP-WASTE-CARTRIDGE",
            "MASCK_ONE-COMP-WASTE-PUMP",
            "MASCK_ONE-COMP-WATER-PUMP",
            "MASCK_ONE-COMP-WATER-RESERVOIR",
        }
        missing = sorted(required - set(by_id))
        if missing:
            raise ComponentRegistryError(f"registry is missing core MVP components: {missing}")
        if by_id["MASCK_ONE-COMP-RIGID-SHELL"].status != REALIZED_SOLID:
            raise ComponentRegistryError("released main rigid shell must remain represented as a realized solid")
        for actuator_id in (
            "MASCK_ONE-COMP-ACTUATOR-01",
            "MASCK_ONE-COMP-ACTUATOR-02",
            "MASCK_ONE-COMP-ACTUATOR-03",
            "MASCK_ONE-COMP-ACTUATOR-04",
        ):
            if by_id[actuator_id].status != CONTROLLED_ENVELOPE:
                raise ComponentRegistryError("development actuator packages must remain controlled envelopes")
        if by_id["MASCK_ONE-COMP-FACIAL-INTERFACE"].status != TOPOLOGY_ONLY:
            raise ComponentRegistryError("facial interface cannot be promoted beyond topology on released main")
        for unresolved_id in (
            "MASCK_ONE-COMP-PCB",
            "MASCK_ONE-COMP-RETENTION-HALO",
            "MASCK_ONE-COMP-WASTE-PUMP",
            "MASCK_ONE-COMP-WATER-PUMP",
        ):
            if by_id[unresolved_id].status != UNRESOLVED:
                raise ComponentRegistryError(f"{unresolved_id} cannot be promoted without controlled package geometry")

    @property
    def registry_sha256(self) -> str:
        raw = json.dumps(
            self.manifest(include_sha=False),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": self.schema,
            "source_main_sha": self.source_main_sha,
            "authority_revision": self.authority_revision,
            "authority_blob_sha": self.authority_blob_sha,
            "coordinate_frame_id": self.coordinate_frame_id,
            "status_vocabulary": list(STATUS_VOCABULARY),
            "owner_vocabulary": list(OWNER_VOCABULARY),
            "source_git_blobs": dict(sorted(SOURCE_GIT_BLOB_BY_MODULE.items())),
            "components": [item.manifest() for item in self.components],
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            payload["registry_sha256"] = self.registry_sha256
        return payload


def _datum(
    datum_id: str,
    datum_type: str,
    status: str,
    xyz_mm: tuple[float, float, float] | None = None,
    direction_xyz: tuple[float, float, float] | None = None,
) -> InterfaceDatum:
    return InterfaceDatum(datum_id, datum_type, status, xyz_mm, direction_xyz)


def _record(
    component_id: str,
    display_name: str,
    owner: str,
    source_module: str,
    source_object_id: str,
    status: str,
    datums: Iterable[InterfaceDatum],
    *,
    digest: str | None = None,
    evidence: str,
) -> ComponentRecord:
    return ComponentRecord(
        component_id=component_id,
        display_name=display_name,
        owner=owner,
        source_module=source_module,
        source_git_blob_sha=SOURCE_GIT_BLOB_BY_MODULE[source_module],
        source_object_id=source_object_id,
        status=status,
        interface_datums=tuple(datums),
        source_digest_sha256=digest,
        evidence_status=evidence,
    )


def _frame_datums() -> tuple[InterfaceDatum, ...]:
    return tuple(
        _datum(item, "FRAME_DATUM", "AUTHORITY_DERIVED_XY_Z_UNRESOLVED")
        for item in FRAME_DATUM_IDS
    )


def _reservation_datum(reservation_id: str) -> InterfaceDatum:
    return _datum(reservation_id, "FRAME_RESERVATION", "TOPOLOGY_ONLY")


def _unresolved_datum(component_id: str, role: str) -> InterfaceDatum:
    return _datum(
        f"{component_id}-DATUM-{role}",
        "UNRESOLVED_INTERFACE_DATUM",
        "IDENTITY_RESERVED_GEOMETRY_UNRESOLVED",
    )


def build_whole_product_component_registry(
    model: MasckOneModel | None = None,
) -> WholeProductComponentRegistry:
    """Build the authoritative released-main component registry.

    The registry intentionally describes released ``main`` only. Unmerged specialist
    branches are not consumed as source truth. Their future merge must update this
    registry in the same bounded change if component maturity or interface identity changes.
    """
    model = model or build_model()
    authority = model.authority
    revision = str(authority.get("project", "authority_revision"))
    if revision != AUTHORITY_REVISION:
        raise ComponentRegistryError("repository authority revision changed; registry requires rebind")

    boundary = build_verified_interface_boundary_topology(
        authority,
        model.facial_surface,
        model.coverage_mesh,
        model.compliant_interface_topology,
    )
    attachment = build_interface_attachment_architecture(authority, boundary)
    frame = build_structural_frame_topology(authority, attachment)
    canonical = canonical_iteration25_sources(authority)
    water = build_water_reservoir_architecture(authority)
    cleanser = build_cleanser_storage_architecture(authority)
    fresh_pumps = build_fresh_pump_packaging_architecture(authority, water, cleanser, frame)
    manifold = build_distribution_manifold_architecture(
        authority, fresh_pumps, water, cleanser, frame
    )
    distribution = build_distribution_geometry_architecture(
        authority,
        manifold,
        fresh_pumps,
        water,
        cleanser,
        frame,
        model.coverage_mesh,
        model.protected_volumes,
    )
    if (
        canonical.water.architecture_sha256 != water.architecture_sha256
        or canonical.cleanser.architecture_sha256 != cleanser.architecture_sha256
        or canonical.frame.topology_sha256 != frame.topology_sha256
        or canonical.pump.architecture_sha256 != fresh_pumps.architecture_sha256
        or canonical.manifold.architecture_sha256 != manifold.architecture_sha256
        or canonical.distribution.architecture_sha256 != distribution.architecture_sha256
    ):
        raise ComponentRegistryError("registry source graph differs from canonical released source graph")

    acquisition = build_waste_acquisition_architecture(
        authority,
        distribution,
        manifold=manifold,
        pump=fresh_pumps,
        water=water,
        cleanser=cleanser,
        frame=frame,
        coverage=model.coverage_mesh,
        protected=model.protected_volumes,
    )
    waste_pump = build_waste_pump_architecture(
        authority, acquisition, distribution, frame
    )
    cartridge = build_waste_cartridge_architecture(
        authority, waste_pump, acquisition, distribution, frame
    )

    shell_apertures = (
        _datum(ZONE_OPENING_EYE_LEFT, "PROTECTED_APERTURE", "AUTHORITY_BACKED"),
        _datum(ZONE_OPENING_EYE_RIGHT, "PROTECTED_APERTURE", "AUTHORITY_BACKED"),
        _datum(ZONE_OPENING_MOUTH, "PROTECTED_APERTURE", "AUTHORITY_BACKED"),
        _datum(ZONE_OPENING_NOSTRIL_LEFT, "PROTECTED_APERTURE", "AUTHORITY_BACKED"),
        _datum(ZONE_OPENING_NOSTRIL_RIGHT, "PROTECTED_APERTURE", "AUTHORITY_BACKED"),
    )

    records: list[ComponentRecord] = [
        _record(
            "MASCK_ONE-COMP-RIGID-SHELL",
            "Rigid exterior shell",
            OWNER_CELL_2,
            "src/masck_one/model.py",
            model.shell.name,
            REALIZED_SOLID,
            shell_apertures + (_datum(FRAME_DATUM_IDS[0], "ASSEMBLY_DATUM", "AUTHORITY_DERIVED_XY_Z_UNRESOLVED"),),
            evidence="DETERMINISTIC_CURRENT_MAIN_BREP_NOT_CLASS_A_OR_PHYSICAL_VALIDATION",
        ),
        _record(
            "MASCK_ONE-COMP-FACIAL-INTERFACE",
            "Compliant facial interface",
            OWNER_CELL_2,
            "src/masck_one/interface_topology.py",
            "COMPLIANT_INTERFACE_TOPOLOGY",
            TOPOLOGY_ONLY,
            tuple(
                _datum(zone, "INTERFACE_PARAMETER_ZONE", "TOPOLOGY_DEFINED_GEOMETRY_MATERIAL_UNRESOLVED")
                for zone in (
                    ZONE_GENERAL_FACE,
                    ZONE_T_FOREHEAD,
                    ZONE_T_NOSE_PHILTRUM,
                    ZONE_OPENING_EYE_LEFT,
                    ZONE_OPENING_EYE_RIGHT,
                    ZONE_OPENING_MOUTH,
                    ZONE_OPENING_NOSTRIL_LEFT,
                    ZONE_OPENING_NOSTRIL_RIGHT,
                )
            ),
            digest=model.compliant_interface_topology.topology_sha256,
            evidence="CONTACT_TOPOLOGY_ONLY_NOT_FIT_PRESSURE_COMFORT_OR_MATERIAL_EVIDENCE",
        ),
        _record(
            "MASCK_ONE-COMP-NASAL-LOBE-REFERENCE",
            "Nasal lobe local-thickness development reference",
            OWNER_CELL_2,
            "src/masck_one/model.py",
            model.nasal_interface.name,
            REALIZED_SOLID,
            (
                _datum(ZONE_OPENING_NOSTRIL_LEFT, "PROTECTED_APERTURE", "AUTHORITY_BACKED"),
                _datum(ZONE_OPENING_NOSTRIL_RIGHT, "PROTECTED_APERTURE", "AUTHORITY_BACKED"),
            ),
            evidence="DEVELOPMENT_REFERENCE_SOLID_ONLY_NOT_FINAL_ANATOMICAL_INTERFACE",
        ),
        _record(
            "MASCK_ONE-COMP-STRUCTURAL-FRAME",
            "Structural reaction frame",
            OWNER_CELL_3,
            "src/masck_one/structural_frame.py",
            "MASCK_ONE-FRAME-LOADPATH-PERIMETER-REACTION-LOOP",
            TOPOLOGY_ONLY,
            _frame_datums(),
            digest=frame.topology_sha256,
            evidence="FRAME_TOPOLOGY_ONLY_3D_MEMBER_CROSS_SECTION_MATERIAL_AND_LOAD_EVIDENCE_UNRESOLVED",
        ),
    ]

    actuator_centers = (
        (-48.0, 52.0, 2.0),
        (48.0, 52.0, 2.0),
        (-50.0, -38.0, 2.0),
        (50.0, -38.0, 2.0),
    )
    for index, (zone_id, center) in enumerate(zip(ZONE_IDS, actuator_centers, strict=True), start=1):
        records.append(
            _record(
                f"MASCK_ONE-COMP-ACTUATOR-{index:02d}",
                f"Actuator development package zone {index}",
                OWNER_CELL_3,
                "src/masck_one/model.py",
                model.actuator_envelopes[index - 1].name,
                CONTROLLED_ENVELOPE,
                (
                    _datum(zone_id, "ACTUATION_ZONE", "FROZEN_FOUR_ZONE_ARCHITECTURE", center),
                    _reservation_datum(RESERVATION_ACTUATION),
                ),
                evidence="SUPPLIER_REFERENCE_PACKAGE_ENVELOPE_ONLY_PRODUCTION_SELECTION_MOUNT_AND_PERFORMANCE_UNRESOLVED",
            )
        )

    records.extend(
        [
            _record(
                "MASCK_ONE-COMP-RETENTION-HALO",
                "Retention halo",
                OWNER_CELL_3,
                "src/masck_one/structural_frame.py",
                RESERVATION_RETENTION,
                UNRESOLVED,
                (_reservation_datum(RESERVATION_RETENTION),),
                evidence="RETENTION_IDENTITY_AND_FRAME_RESERVATION_ONLY_NO_RELEASED_MAIN_GEOMETRY",
            ),
            _record(
                "MASCK_ONE-COMP-QUICK-RELEASE-RIGHT",
                "Right unpowered emergency quick release",
                OWNER_CELL_3,
                "src/masck_one/structural_frame.py",
                RESERVATION_RETENTION,
                UNRESOLVED,
                (
                    _reservation_datum(RESERVATION_RETENTION),
                    _unresolved_datum("MASCK_ONE-COMP-QUICK-RELEASE-RIGHT", "RELEASE_AXIS"),
                ),
                evidence="FROZEN_SAFETY_REQUIREMENT_NO_RELEASED_MAIN_MECHANISM_GEOMETRY_OR_PHYSICAL_RELEASE_EVIDENCE",
            ),
            _record(
                "MASCK_ONE-COMP-RETENTION-LEFT-INTERFACE",
                "Left retention interface",
                OWNER_CELL_3,
                "src/masck_one/structural_frame.py",
                RESERVATION_RETENTION,
                UNRESOLVED,
                (
                    _reservation_datum(RESERVATION_RETENTION),
                    _unresolved_datum("MASCK_ONE-COMP-RETENTION-LEFT-INTERFACE", "ATTACHMENT"),
                ),
                evidence="RETENTION_INTERFACE_IDENTITY_RESERVED_GEOMETRY_UNRESOLVED",
            ),
            _record(
                "MASCK_ONE-COMP-WATER-RESERVOIR",
                "Fresh-water reservoir",
                OWNER_CELL_4,
                "src/masck_one/water_reservoir.py",
                WATER_RESERVOIR_ID,
                CONTROLLED_ENVELOPE,
                tuple(_datum(port, "FLUID_PORT", "PORT_ID_CONTROLLED_GEOMETRY_UNRESOLVED") for port in WATER_PORT_IDS),
                digest=water.architecture_sha256,
                evidence="MODEL_PACKAGE_ENVELOPE_PLUS_STORAGE_TOPOLOGY_NOT_USABLE_VOLUME_LEAK_OR_ORIENTATION_EVIDENCE",
            ),
            _record(
                "MASCK_ONE-COMP-CLEANSER-RESERVOIR",
                "Dedicated cleanser reservoir",
                OWNER_CELL_4,
                "src/masck_one/cleanser_storage.py",
                CLEANSER_STORAGE_ID,
                TOPOLOGY_ONLY,
                tuple(_datum(port, "FLUID_PORT", "PORT_ID_CONTROLLED_GEOMETRY_UNRESOLVED") for port in CLEANSER_PORT_IDS),
                digest=cleanser.architecture_sha256,
                evidence="STORAGE_REFILL_PURGE_TOPOLOGY_ONLY_CAPACITY_GEOMETRY_COMPATIBILITY_AND_HYGIENE_UNRESOLVED",
            ),
            _record(
                "MASCK_ONE-COMP-WATER-PUMP",
                "Fresh-water metering pump",
                OWNER_CELL_4,
                "src/masck_one/fresh_pump_packaging.py",
                STATION_WATER,
                UNRESOLVED,
                (
                    _datum(WATER_PORT_IDS[-1], "FLUID_SOURCE_PORT", "CONTROLLED_ID_GEOMETRY_UNRESOLVED"),
                    _datum(INTERFACE_WATER_PUMP_OUTLET, "FLUID_OUTLET", "CONTROLLED_ID_GEOMETRY_UNRESOLVED"),
                    _reservation_datum(RESERVATION_FRESH_FLUID),
                ),
                evidence="PUMP_STATION_IDENTITY_ONLY_PACKAGE_SELECTION_PLACEMENT_METERING_AND_SERVICE_UNRESOLVED",
            ),
            _record(
                "MASCK_ONE-COMP-CLEANSER-PUMP",
                "Cleanser metering pump",
                OWNER_CELL_4,
                "src/masck_one/fresh_pump_packaging.py",
                STATION_CLEANSER,
                UNRESOLVED,
                (
                    _datum(CLEANSER_PORT_IDS[1], "FLUID_SOURCE_PORT", "CONTROLLED_ID_GEOMETRY_UNRESOLVED"),
                    _datum(INTERFACE_CLEANSER_PUMP_OUTLET, "FLUID_OUTLET", "CONTROLLED_ID_GEOMETRY_UNRESOLVED"),
                    _reservation_datum(RESERVATION_FRESH_FLUID),
                ),
                evidence="PUMP_STATION_IDENTITY_ONLY_PACKAGE_SELECTION_PLACEMENT_METERING_AND_SERVICE_UNRESOLVED",
            ),
            _record(
                "MASCK_ONE-COMP-FRESH-MANIFOLD",
                "Fresh water and cleanser distribution manifold",
                OWNER_CELL_4,
                "src/masck_one/distribution_manifold.py",
                "DISTRIBUTION_MANIFOLD_I23",
                TOPOLOGY_ONLY,
                (
                    _datum(INLET_FRESH_WATER, "MANIFOLD_INLET", "CONTROLLED_ID_GEOMETRY_UNRESOLVED"),
                    _datum(INLET_CLEANSER, "MANIFOLD_INLET", "CONTROLLED_ID_GEOMETRY_UNRESOLVED"),
                    *tuple(
                        _datum(item.outlet_id, "MANIFOLD_OUTLET", "PLACEMENT_RESERVED_BY_DISTRIBUTION_GEOMETRY")
                        for item in manifold.outlets
                    ),
                ),
                digest=manifold.architecture_sha256,
                evidence="BRANCH_AND_OUTLET_TOPOLOGY_ONLY_BORE_RESTRICTION_FLOW_BALANCE_AND_PHYSICAL_DISTRIBUTION_UNRESOLVED",
            ),
            _record(
                "MASCK_ONE-COMP-FRESH-DISTRIBUTION",
                "Skin-facing fresh-fluid distribution network",
                OWNER_CELL_4,
                "src/masck_one/distribution_geometry.py",
                "DISTRIBUTION_GEOMETRY_I24",
                TOPOLOGY_ONLY,
                tuple(
                    _datum(
                        item.outlet_id,
                        "OUTLET_DEVELOPMENT_DATUM",
                        "DEVELOPMENT_TARGET_NOT_REGISTERED_ANATOMICAL_POSITION",
                        item.center_xyz_mm,
                        item.lateral_direction_xyz,
                    )
                    for item in distribution.placements
                ),
                digest=distribution.architecture_sha256,
                evidence="DEVELOPMENT_OUTLET_DATUMS_AND_GROOVE_INTENT_ONLY_GROOVE_SECTION_FLOW_AND_PHYSICAL_DISTRIBUTION_UNRESOLVED",
            ),
            _record(
                "MASCK_ONE-COMP-WASTE-ACQUISITION",
                "Facial mixed-waste acquisition network",
                OWNER_CELL_4,
                "src/masck_one/waste_acquisition.py",
                "WASTE_ACQUISITION_I25",
                TOPOLOGY_ONLY,
                tuple(
                    _datum(region, "WASTE_ACQUISITION_REGION", "TOPOLOGY_ONLY_GUTTER_GEOMETRY_UNRESOLVED")
                    for region in WASTE_ACQUISITION_REGIONS
                )
                + (_datum(WASTE_ACQUISITION_DESTINATION, "WASTE_HANDOFF", "CONTROLLED_INTERFACE_ID"),),
                digest=acquisition.architecture_sha256,
                evidence="WASTE_ACQUISITION_TOPOLOGY_ONLY_NOT_RECOVERY_RESIDUAL_LEAKAGE_OR_HYGIENE_EVIDENCE",
            ),
            _record(
                "MASCK_ONE-COMP-WASTE-PUMP",
                "Mixed-phase waste pump",
                OWNER_CELL_4,
                "src/masck_one/waste_pump_architecture.py",
                STATION_WASTE,
                UNRESOLVED,
                (
                    _datum(WASTE_ACQUISITION_DESTINATION, "WASTE_INLET", "CONTROLLED_INTERFACE_ID"),
                    _datum(WASTE_PUMP_OUTLET, "WASTE_OUTLET", "CONTROLLED_INTERFACE_ID"),
                    _reservation_datum(RESERVATION_WASTE),
                ),
                evidence="WASTE_PUMP_IDENTITY_ONLY_PACKAGE_PLACEMENT_TUBING_HYDRAULICS_AND_SERVICE_UNRESOLVED",
            ),
            _record(
                "MASCK_ONE-COMP-WASTE-BACKFLOW-BARRIER",
                "Passive mixed-waste backflow barrier",
                OWNER_CELL_4,
                "src/masck_one/waste_pump_architecture.py",
                BARRIER_WASTE,
                UNRESOLVED,
                (
                    _datum(WASTE_PUMP_OUTLET, "WASTE_INLET", "CONTROLLED_INTERFACE_ID"),
                    _datum(INTERFACE_BARRIER_OUTLET, "WASTE_OUTLET", "CONTROLLED_INTERFACE_ID"),
                ),
                evidence="PASSIVE_BARRIER_TOPOLOGY_REQUIRED_COMPONENT_SELECTION_GEOMETRY_AND_REVERSE_FLOW_PERFORMANCE_UNRESOLVED",
            ),
            _record(
                "MASCK_ONE-COMP-MIXED-WASTE-ROUTES",
                "Mixed-waste route network",
                OWNER_CELL_4,
                "src/masck_one/waste_pump_architecture.py",
                "WASTE_ROUTE_NETWORK_I26",
                TOPOLOGY_ONLY,
                tuple(
                    _datum(route_id, "WASTE_ROUTE", "TOPOLOGY_ONLY_CENTERLINE_UNRESOLVED")
                    for route_id in WASTE_ROUTE_IDS
                ),
                digest=waste_pump.architecture_sha256,
                evidence="ROUTE_ID_STAGE_PHASE_AND_INTERFACE_TOPOLOGY_ONLY_NO_RELEASED_MAIN_CENTERLINES",
            ),
            _record(
                "MASCK_ONE-COMP-WASTE-CARTRIDGE",
                "Removable waste cartridge",
                OWNER_CELL_4,
                "src/masck_one/waste_cartridge.py",
                CARTRIDGE_ID,
                CONTROLLED_ENVELOPE,
                (
                    _datum(INTERFACE_CARTRIDGE_INLET_I27, "WASTE_INLET", "CONTROLLED_INTERFACE_ID"),
                    _datum(CARTRIDGE_INTERFACE_KEY, "SERVICE_KEY", "TOPOLOGY_ONLY_GEOMETRY_UNRESOLVED"),
                    _datum(CARTRIDGE_INTERFACE_SEAL, "WET_SEAL", "TOPOLOGY_ONLY_GEOMETRY_UNRESOLVED"),
                    _datum(CARTRIDGE_INTERFACE_SERVICE, "SERVICE_TRAJECTORY", "TOPOLOGY_ONLY_TRAJECTORY_UNRESOLVED"),
                ),
                digest=cartridge.architecture_sha256,
                evidence="AUTHORITY_EXTERNAL_ENVELOPE_PLUS_SERVICE_TOPOLOGY_NOT_USABLE_CAPACITY_SEAL_LEAKAGE_OR_SERVICE_EVIDENCE",
            ),
            _record(
                "MASCK_ONE-COMP-BATTERY",
                "Battery packaging benchmark",
                OWNER_CELL_4,
                "config/masck_one_authority.yaml",
                "battery_reference",
                CONTROLLED_ENVELOPE,
                (
                    _reservation_datum(RESERVATION_HMI_ELECTRONICS),
                    _unresolved_datum("MASCK_ONE-COMP-BATTERY", "ELECTRICAL_CONNECTOR"),
                ),
                evidence="AUTHORITY_PACKAGING_BENCHMARK_ONLY_NOT_PRODUCTION_CELL_PACK_SWELLING_RUNTIME_OR_SAFETY_EVIDENCE",
            ),
            _record(
                "MASCK_ONE-COMP-PCB",
                "Control and power PCB",
                OWNER_CELL_4,
                "src/masck_one/structural_frame.py",
                RESERVATION_HMI_ELECTRONICS,
                UNRESOLVED,
                (
                    _reservation_datum(RESERVATION_HMI_ELECTRONICS),
                    _unresolved_datum("MASCK_ONE-COMP-PCB", "MOUNT"),
                ),
                evidence="DRY_BAY_RESERVATION_ONLY_NO_RELEASED_MAIN_PCB_PACKAGE_OR_CONNECTOR_GEOMETRY",
            ),
            _record(
                "MASCK_ONE-COMP-HARNESS",
                "Electrical harness",
                OWNER_CELL_4,
                "src/masck_one/structural_frame.py",
                RESERVATION_HMI_ELECTRONICS,
                UNRESOLVED,
                (
                    _reservation_datum(RESERVATION_HMI_ELECTRONICS),
                    _unresolved_datum("MASCK_ONE-COMP-HARNESS", "ROUTING"),
                ),
                evidence="HARNESS_FUNCTION_REQUIRED_NO_RELEASED_MAIN_ROUTE_CONNECTOR_OR_STRAIN_RELIEF_GEOMETRY",
            ),
            _record(
                "MASCK_ONE-COMP-CHARGING-INTERFACE",
                "Charging interface",
                OWNER_CELL_4,
                "src/masck_one/structural_frame.py",
                RESERVATION_HMI_ELECTRONICS,
                UNRESOLVED,
                (
                    _reservation_datum(RESERVATION_HMI_ELECTRONICS),
                    _unresolved_datum("MASCK_ONE-COMP-CHARGING-INTERFACE", "USER_ACCESS"),
                ),
                evidence="CHARGING_FUNCTION_REQUIRED_NO_RELEASED_MAIN_CONNECTOR_SEAL_OR_ACCESS_GEOMETRY",
            ),
            _record(
                "MASCK_ONE-COMP-DRY-BAY",
                "Electronics dry bay",
                OWNER_CELL_4,
                "src/masck_one/structural_frame.py",
                RESERVATION_HMI_ELECTRONICS,
                UNRESOLVED,
                (
                    _reservation_datum(RESERVATION_HMI_ELECTRONICS),
                    _unresolved_datum("MASCK_ONE-COMP-DRY-BAY", "WET_DRY_BOUNDARY"),
                ),
                evidence="DRY_BAY_IDENTITY_RESERVED_NO_RELEASED_MAIN_ENCLOSURE_SEAL_DRAIN_OR_SERVICE_GEOMETRY",
            ),
        ]
    )

    for role in ("CLEAN", "POWER", "WARM", "COOL"):
        records.append(
            _record(
                f"MASCK_ONE-COMP-HMI-{role}",
                f"{role} physical HMI control",
                OWNER_CELL_4,
                "src/masck_one/structural_frame.py",
                RESERVATION_HMI_ELECTRONICS,
                UNRESOLVED,
                (
                    _reservation_datum(RESERVATION_HMI_ELECTRONICS),
                    _unresolved_datum(f"MASCK_ONE-COMP-HMI-{role}", "USER_CONTROL"),
                ),
                evidence="PHYSICAL_HMI_FUNCTION_RESERVED_NO_RELEASED_MAIN_CONTROL_LAND_SEAL_OR_WET_FINGER_GEOMETRY",
            )
        )

    for side in ("LEFT", "RIGHT"):
        records.append(
            _record(
                f"MASCK_ONE-COMP-WARM-{side}",
                f"WARM thermal reservation {side.lower()}",
                OWNER_CELL_4,
                "src/masck_one/structural_frame.py",
                RESERVATION_THERMAL,
                UNRESOLVED,
                (
                    _reservation_datum(RESERVATION_THERMAL),
                    _unresolved_datum(f"MASCK_ONE-COMP-WARM-{side}", "THERMAL_INTERFACE"),
                ),
                evidence="WARM_FUNCTION_RESERVED_NO_RELEASED_MAIN_HEATER_SENSOR_SPREADER_INSULATION_OR_SAFETY_GEOMETRY",
            )
        )

    records.extend(
        [
            _record(
                "MASCK_ONE-COMP-COOL-RESERVATION",
                "Bounded experimental COOL reservation",
                OWNER_CELL_4,
                "src/masck_one/structural_frame.py",
                RESERVATION_THERMAL,
                UNRESOLVED,
                (
                    _reservation_datum(RESERVATION_THERMAL),
                    _unresolved_datum("MASCK_ONE-COMP-COOL-RESERVATION", "THERMAL_INTERFACE"),
                ),
                evidence="EXPERIMENTAL_RESERVATION_ONLY_NOT_MVP_DEPENDENCY_NO_RELEASED_MAIN_HARDWARE_OR_THERMAL_EVIDENCE",
            ),
            _record(
                "MASCK_ONE-COMP-WET-DRY-BULKHEAD",
                "Wet to dry interface bulkhead",
                OWNER_CELL_4,
                "src/masck_one/structural_frame.py",
                RESERVATION_HMI_ELECTRONICS,
                UNRESOLVED,
                (
                    _reservation_datum(RESERVATION_HMI_ELECTRONICS),
                    _reservation_datum(RESERVATION_FRESH_FLUID),
                    _reservation_datum(RESERVATION_WASTE),
                ),
                evidence="WET_DRY_INTERFACE_REQUIRED_NO_RELEASED_MAIN_BULKHEAD_SEAL_CONNECTOR_OR_INGRESS_GEOMETRY",
            ),
            _record(
                "MASCK_ONE-COMP-DRAIN-DRY-PATH",
                "Drain and dry service path",
                OWNER_CELL_4,
                "src/masck_one/structural_frame.py",
                RESERVATION_WASTE,
                UNRESOLVED,
                (
                    _reservation_datum(RESERVATION_WASTE),
                    _unresolved_datum("MASCK_ONE-COMP-DRAIN-DRY-PATH", "LOW_POINT"),
                ),
                evidence="DRAIN_DRY_REQUIREMENT_ONLY_LOW_POINTS_RETAINED_POCKETS_AND_PHYSICAL_HYGIENE_UNRESOLVED",
            ),
        ]
    )

    records.sort(key=lambda item: item.component_id)
    registry = WholeProductComponentRegistry(
        schema=REGISTRY_SCHEMA,
        source_main_sha=SOURCE_MAIN_SHA,
        authority_revision=revision,
        authority_blob_sha=AUTHORITY_BLOB_SHA,
        coordinate_frame_id=WORLD_FRAME_ID,
        components=tuple(records),
        physical_validation_eligible=False,
        evidence_status=(
            "AUTHORITATIVE_RELEASED_MAIN_COMPONENT_ID_OWNERSHIP_SOURCE_MATURITY_AND_INTERFACE_REGISTRY_ONLY_"
            "NOT_FIT_COMFORT_HYDRAULIC_ELECTRICAL_THERMAL_HYGIENE_RUNTIME_OR_OTHER_PHYSICAL_VALIDATION"
        ),
    )
    return registry
