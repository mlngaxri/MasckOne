from __future__ import annotations

"""Cell 1 source-bound integration of the released wet-system package truth.

This module is an integration receipt, not a second Cell 4 authoring lane. It consumes
only geometry and topology already released on ``main``. Unmerged Cell 4 candidates are
not imported. In particular, dry-bay, harness and physical-HMI geometry remain
unresolved because there is no current released producer for them.

The mixed-waste service boxes emitted here are conservative review reservations derived
from the released route bounds and the route-owned provisional service radius. They are
not tubing, channels, service trajectories or physical-clearance evidence.
"""

from dataclasses import asdict, dataclass
from hashlib import sha256
from io import BytesIO
import json
import math
from pathlib import Path
import re

import cadquery as cq

from .cleanser_storage import PORT_IDS as CLEANSER_PORT_IDS, build_cleanser_storage_architecture
from .distribution_manifold import build_distribution_manifold_architecture
from .fresh_pump_packaging import ROUTE_IDS as FRESH_ROUTE_IDS, build_fresh_pump_packaging_architecture
from .model import Component, MasckOneModel, build_model
from .realized_waste_backbone import (
    PHASE_MIXED_WASTE,
    RealizedWasteRoute,
    build_cell4_waste_backbone,
)
from .realized_waste_backbone_release import (
    AUTHORED_AGAINST_MAIN_SHA,
    RELEASE_STATE,
    Cell4WasteBackboneRelease,
    CurrentWasteRoutingSources,
    build_current_waste_routing_sources,
)
from .structural_frame import RESERVATION_HMI_ELECTRONICS
from .water_reservoir import PORT_IDS as WATER_PORT_IDS, build_water_reservoir_architecture
from .waste_cartridge import build_waste_cartridge_architecture
from .waste_pump_architecture import (
    BARRIER_WASTE,
    ROUTE_IDS as WASTE_ROUTE_IDS,
    STATION_WASTE,
)


SCHEMA = "MASCK_ONE_CELL1_WET_SYSTEM_PACKAGE_INGESTION_V1"
SOURCE_MAIN_SHA = "628ec5f5766937433b1bdf8f30edc372924cf41e"
AUTHORITY_REVISION = "2026-08-30-R1"
AUTHORITY_BLOB_SHA = "2608dda483b995539de422290371c219668a1527"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
FROZEN_HYGIENE_CLASSES = (
    "DRY_ALWAYS",
    "WET_DRAINABLE",
    "WET_REMOVABLE",
    "SEALED_NONUSER",
)

SOURCE_BLOBS = (
    ("src/masck_one/model.py", "9e7fa6c71ac28cc45ebb502444bf6c0ea49f7894"),
    ("src/masck_one/structural_frame.py", "bda5ba87d232c0e6a22e200975a80414a10c9a83"),
    ("src/masck_one/water_reservoir.py", "6c14a37d07855550f0bd502e8308ed46682bc19c"),
    ("src/masck_one/cleanser_storage.py", "5e087ca8b05da8352ad4800b2ef8280ea8ddcf29"),
    ("src/masck_one/fresh_pump_packaging.py", "40cb6fb4c3efbfcf25ed0b7d7a75a4269d90a1b4"),
    ("src/masck_one/distribution_manifold.py", "8f2a6c784b51734aba4d1f3809015707fc328405"),
    ("src/masck_one/distribution_geometry.py", "d2dd8b47bb6a2aa1edf57ac0632778228add7997"),
    ("src/masck_one/waste_acquisition.py", "7108fcfbe2baeaa9a343199a6817122ac2aea7ab"),
    ("src/masck_one/waste_pump_architecture.py", "ace02ee529070465b11832f475771125636312cb"),
    ("src/masck_one/waste_pump_packaging.py", "43587520a8c6cdc9ca8cfe362d2aac9589364fdc"),
    ("src/masck_one/waste_cartridge.py", "9dc0fe8a0ed92083c68406da3993e57e767e2483"),
    ("src/masck_one/realized_waste_backbone.py", "6aa79d9a613e278f32da85b4654c0e35cc09b7ca"),
    ("src/masck_one/realized_waste_backbone_release.py", "86f2b12d8721ce0fb233d7b026aed3154de9c964"),
)

CONTROLLED_ENVELOPE = "CONTROLLED_ENVELOPE"
DEVELOPMENT_GEOMETRY_REFERENCE = "DEVELOPMENT_GEOMETRY_REFERENCE"
TOPOLOGY_ONLY = "TOPOLOGY_ONLY"
REALIZED_ROUTE = "REALIZED_ROUTE"
UNRESOLVED = "UNRESOLVED"
MATURITY = frozenset(
    {CONTROLLED_ENVELOPE, DEVELOPMENT_GEOMETRY_REFERENCE, TOPOLOGY_ONLY, REALIZED_ROUTE, UNRESOLVED}
)

DIGITAL_ONLY = (
    "DIGITAL_WET_SYSTEM_INTEGRATION_ONLY_NOT_FLOW_LEAKAGE_RECOVERY_CAPACITY_SEAL_"
    "HYGIENE_DRYING_CLEANSER_COMPATIBILITY_INGRESS_HMI_ELECTRICAL_OR_PHYSICAL_EVIDENCE"
)
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
_GIT_SHA_RE = re.compile(r"[0-9a-f]{40}\Z")


class WetSystemPackageIngestionError(ValueError):
    pass


def _git_sha(value: object, label: str) -> str:
    if type(value) is not str or _GIT_SHA_RE.fullmatch(value) is None:
        raise WetSystemPackageIngestionError(f"{label} must be exact lowercase 40-hex")
    return value


def _sha256(value: object, label: str) -> str:
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
        raise WetSystemPackageIngestionError(f"{label} must be canonical lowercase SHA-256")
    return value


def _brep_sha256(solid: cq.Workplane) -> str:
    shape = solid.val()
    if not shape.isValid() or not shape.Solids() or float(shape.Volume()) <= 0.0:
        raise WetSystemPackageIngestionError("B-rep digest requires valid positive-volume geometry")
    buffer = BytesIO()
    shape.exportBrep(buffer)
    payload = buffer.getvalue()
    if not payload:
        raise WetSystemPackageIngestionError("B-rep export produced no bytes")
    return sha256(payload).hexdigest()


def _bounds(solid: cq.Workplane) -> tuple[float, float, float, float, float, float]:
    bb = solid.val().BoundingBox()
    return tuple(float(value) for value in (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax))


def _service_aabb(route: RealizedWasteRoute) -> cq.Workplane:
    route.validate()
    lower, upper = route.bounds_xyz_mm
    radius = float(route.service_envelope_radius_mm)
    mins = tuple(float(value) - radius for value in lower)
    maxs = tuple(float(value) + radius for value in upper)
    size = tuple(maxs[index] - mins[index] for index in range(3))
    center = tuple((mins[index] + maxs[index]) / 2.0 for index in range(3))
    if any(not math.isfinite(value) or value <= 0.0 for value in size):
        raise WetSystemPackageIngestionError("route service AABB dimensions must be finite and positive")
    return cq.Workplane("XY").box(*size, centered=(True, True, True)).translate(center)


def _compound(parts: tuple[cq.Workplane, ...]) -> cq.Workplane:
    if not parts:
        raise WetSystemPackageIngestionError("wet package review compound requires geometry")
    shapes = [part.val() for part in parts]
    if any(not shape.isValid() or not shape.Solids() for shape in shapes):
        raise WetSystemPackageIngestionError("wet package review compound contains invalid geometry")
    return cq.Workplane(obj=cq.Compound.makeCompound(shapes))


@dataclass(frozen=True, slots=True)
class WetSourceBinding:
    source_main_sha: str
    authority_revision: str
    authority_blob_sha: str
    world_frame_id: str
    source_blobs: tuple[tuple[str, str], ...]

    def validate(self) -> None:
        _git_sha(self.source_main_sha, "source main")
        _git_sha(self.authority_blob_sha, "authority blob")
        if self.source_main_sha != SOURCE_MAIN_SHA:
            raise WetSystemPackageIngestionError("wet integration is stale for current released main")
        if self.authority_revision != AUTHORITY_REVISION or self.authority_blob_sha != AUTHORITY_BLOB_SHA:
            raise WetSystemPackageIngestionError("wet integration authority provenance changed")
        if self.world_frame_id != WORLD_FRAME_ID:
            raise WetSystemPackageIngestionError("wet integration must use the canonical authority world frame")
        if self.source_blobs != SOURCE_BLOBS:
            raise WetSystemPackageIngestionError("wet integration source blob set changed")
        for path, digest in self.source_blobs:
            if type(path) is not str or not path.startswith("src/masck_one/"):
                raise WetSystemPackageIngestionError("wet source path escaped engineering source root")
            _git_sha(digest, f"source blob {path}")

    def manifest(self) -> dict[str, object]:
        return {
            "source_main_sha": self.source_main_sha,
            "authority_revision": self.authority_revision,
            "authority_blob_sha": self.authority_blob_sha,
            "world_frame_id": self.world_frame_id,
            "source_blobs": [list(item) for item in self.source_blobs],
        }


@dataclass(frozen=True, slots=True)
class WetComponentRecord:
    component_id: str
    owner: str
    semantic_source: str
    semantic_source_sha256: str | None
    maturity: str
    fluid_identity: str | None
    cavity_classification: str | None
    interface_ids: tuple[str, ...]
    evidence_status: str
    geometry: cq.Workplane | None = None
    geometry_source: str | None = None

    def __post_init__(self) -> None:
        if type(self.component_id) is not str or not self.component_id:
            raise WetSystemPackageIngestionError("wet component ID must be exact nonblank text")
        if self.owner not in {"CELL_4", "CELL_1_INTEGRATION"}:
            raise WetSystemPackageIngestionError("wet component owner is uncontrolled")
        if self.maturity not in MATURITY:
            raise WetSystemPackageIngestionError("wet component maturity is uncontrolled")
        if self.semantic_source_sha256 is not None:
            _sha256(self.semantic_source_sha256, f"{self.component_id} semantic source")
        if self.cavity_classification is not None and self.cavity_classification not in FROZEN_HYGIENE_CLASSES:
            raise WetSystemPackageIngestionError("component cavity classification left the authority vocabulary")
        if type(self.interface_ids) is not tuple or any(type(item) is not str or not item for item in self.interface_ids):
            raise WetSystemPackageIngestionError("component interface IDs must be immutable exact text")
        if not self.evidence_status:
            raise WetSystemPackageIngestionError("component evidence status must be explicit")
        if self.geometry is None:
            if self.geometry_source is not None:
                raise WetSystemPackageIngestionError("geometry source cannot be claimed without geometry")
            if self.maturity == CONTROLLED_ENVELOPE:
                raise WetSystemPackageIngestionError("controlled-envelope component requires geometry")
        else:
            shape = self.geometry.val()
            if not shape.isValid() or not shape.Solids() or float(shape.Volume()) <= 0.0:
                raise WetSystemPackageIngestionError("integrated wet geometry must be valid positive-volume B-rep")
            if self.geometry_source is None:
                raise WetSystemPackageIngestionError("integrated geometry requires exact source identity")
            if self.maturity not in {CONTROLLED_ENVELOPE, DEVELOPMENT_GEOMETRY_REFERENCE}:
                raise WetSystemPackageIngestionError("topology/unresolved components cannot carry product geometry")

    def manifest(self) -> dict[str, object]:
        return {
            "component_id": self.component_id,
            "owner": self.owner,
            "semantic_source": self.semantic_source,
            "semantic_source_sha256": self.semantic_source_sha256,
            "maturity": self.maturity,
            "fluid_identity": self.fluid_identity,
            "cavity_classification": self.cavity_classification,
            "interface_ids": list(self.interface_ids),
            "evidence_status": self.evidence_status,
            "geometry_source": self.geometry_source,
            "brep_sha256": None if self.geometry is None else _brep_sha256(self.geometry),
            "bounds_mm": None if self.geometry is None else list(_bounds(self.geometry)),
            "physical_validation_eligible": False,
        }


@dataclass(frozen=True, slots=True)
class WetRouteRecord:
    route_id: str
    fluid_identity: str
    stage: str
    source_interface_id: str
    target_interface_id: str
    maturity: str
    source_architecture_sha256: str
    geometry_status: str
    centerline_length_mm: float | None
    geometric_dead_volume_mL: float | None
    service_envelope_radius_mm: float | None
    service_aabb: cq.Workplane | None

    def __post_init__(self) -> None:
        if self.maturity not in {TOPOLOGY_ONLY, REALIZED_ROUTE}:
            raise WetSystemPackageIngestionError("route maturity must be topology-only or realized")
        _sha256(self.source_architecture_sha256, f"{self.route_id} source architecture")
        if self.maturity == TOPOLOGY_ONLY:
            if any(value is not None for value in (
                self.centerline_length_mm,
                self.geometric_dead_volume_mL,
                self.service_envelope_radius_mm,
                self.service_aabb,
            )):
                raise WetSystemPackageIngestionError("topology-only fresh route cannot invent geometry")
        else:
            if self.fluid_identity != PHASE_MIXED_WASTE:
                raise WetSystemPackageIngestionError("realized route must retain mixed-waste identity")
            if any(value is None for value in (
                self.centerline_length_mm,
                self.geometric_dead_volume_mL,
                self.service_envelope_radius_mm,
                self.service_aabb,
            )):
                raise WetSystemPackageIngestionError("realized mixed-waste route requires released geometry")
            shape = self.service_aabb.val()  # type: ignore[union-attr]
            if not shape.isValid() or len(shape.Solids()) != 1 or float(shape.Volume()) <= 0.0:
                raise WetSystemPackageIngestionError("route service AABB must be one valid positive solid")

    def manifest(self) -> dict[str, object]:
        return {
            "route_id": self.route_id,
            "fluid_identity": self.fluid_identity,
            "stage": self.stage,
            "source_interface_id": self.source_interface_id,
            "target_interface_id": self.target_interface_id,
            "maturity": self.maturity,
            "source_architecture_sha256": self.source_architecture_sha256,
            "geometry_status": self.geometry_status,
            "centerline_length_mm": self.centerline_length_mm,
            "geometric_dead_volume_mL": self.geometric_dead_volume_mL,
            "service_envelope_radius_mm": self.service_envelope_radius_mm,
            "service_aabb_brep_sha256": None if self.service_aabb is None else _brep_sha256(self.service_aabb),
            "service_aabb_bounds_mm": None if self.service_aabb is None else list(_bounds(self.service_aabb)),
            "service_aabb_semantics": None if self.service_aabb is None else (
                "CONSERVATIVE_ROUTE_SERVICE_AABB_REFERENCE_NOT_TUBING_CHANNEL_OR_PHYSICAL_CLEARANCE_EVIDENCE"
            ),
        }


@dataclass(frozen=True, slots=True)
class CavityClassRecord:
    cavity_id: str
    source_id: str
    classification: str | None
    classification_status: str

    def __post_init__(self) -> None:
        if self.classification is not None and self.classification not in FROZEN_HYGIENE_CLASSES:
            raise WetSystemPackageIngestionError("cavity class left the frozen authority vocabulary")
        if type(self.classification_status) is not str or not self.classification_status:
            raise WetSystemPackageIngestionError("cavity classification status must be explicit")

    def manifest(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class WetSystemPackageIntegration:
    binding: WetSourceBinding
    water_architecture_sha256: str
    cleanser_architecture_sha256: str
    fresh_pump_architecture_sha256: str
    manifold_architecture_sha256: str
    distribution_architecture_sha256: str
    waste_acquisition_architecture_sha256: str
    waste_pump_architecture_sha256: str
    waste_cartridge_architecture_sha256: str
    realized_waste_manifest_sha256: str
    realized_waste_release_state: str
    components: tuple[WetComponentRecord, ...]
    routes: tuple[WetRouteRecord, ...]
    cavities: tuple[CavityClassRecord, ...]
    unresolved_integration: tuple[str, ...]
    evidence_status: str = DIGITAL_ONLY
    physical_validation_eligible: bool = False

    def validate(self) -> None:
        self.binding.validate()
        for value, label in (
            (self.water_architecture_sha256, "water architecture"),
            (self.cleanser_architecture_sha256, "cleanser architecture"),
            (self.fresh_pump_architecture_sha256, "fresh pump architecture"),
            (self.manifold_architecture_sha256, "manifold architecture"),
            (self.distribution_architecture_sha256, "distribution architecture"),
            (self.waste_acquisition_architecture_sha256, "waste acquisition architecture"),
            (self.waste_pump_architecture_sha256, "waste pump architecture"),
            (self.waste_cartridge_architecture_sha256, "waste cartridge architecture"),
            (self.realized_waste_manifest_sha256, "realized waste manifest"),
        ):
            _sha256(value, label)
        if self.realized_waste_release_state != RELEASE_STATE:
            raise WetSystemPackageIngestionError("mixed-waste release state was promoted or changed")
        component_ids = tuple(record.component_id for record in self.components)
        expected_components = (
            "DRY-BATTERY-PACKAGING-BENCHMARK",
            "DRY-BAY",
            "HARNESS",
            "HMI",
            "WET-CLEANSER-PUMP",
            "WET-CLEANSER-RESERVOIR",
            "WET-FRESH-DISTRIBUTION",
            "WET-FRESH-MANIFOLD",
            "WET-FRESH-WATER-PUMP",
            "WET-WASTE-ACQUISITION",
            "WET-WASTE-BACKFLOW-BARRIER",
            "WET-WASTE-CARTRIDGE-PACKAGE-REFERENCE",
            "WET-WASTE-PUMP",
            "WET-WATER-RESERVOIR-PACKAGE-REFERENCE",
        )
        if component_ids != expected_components:
            raise WetSystemPackageIngestionError("wet component registry drifted from controlled order")
        if tuple(route.route_id for route in self.routes) != FRESH_ROUTE_IDS + WASTE_ROUTE_IDS:
            raise WetSystemPackageIngestionError("wet route registry must retain fresh then mixed-waste controlled order")
        unresolved_ids = {"DRY-BAY", "HARNESS", "HMI"}
        for component in self.components:
            if component.component_id in unresolved_ids:
                if component.maturity != UNRESOLVED or component.geometry is not None:
                    raise WetSystemPackageIngestionError("unreleased electrical/HMI work cannot gain geometry")
                if RESERVATION_HMI_ELECTRONICS not in component.interface_ids:
                    raise WetSystemPackageIngestionError("unresolved electrical/HMI work must remain bound to frame reservation")
        for cavity in self.cavities:
            if cavity.classification is not None and cavity.classification not in FROZEN_HYGIENE_CLASSES:
                raise WetSystemPackageIngestionError("cavity ledger left frozen authority vocabulary")
        if type(self.unresolved_integration) is not tuple or not self.unresolved_integration:
            raise WetSystemPackageIngestionError("wet integration must preserve explicit downstream blockers")
        if self.evidence_status != DIGITAL_ONLY or self.physical_validation_eligible:
            raise WetSystemPackageIngestionError("wet integration cannot become physical validation evidence")

    @property
    def package_reference_compound(self) -> cq.Workplane:
        parts = tuple(
            record.geometry
            for record in self.components
            if record.geometry is not None and record.maturity == CONTROLLED_ENVELOPE
        )
        return _compound(parts)  # type: ignore[arg-type]

    @property
    def integration_sha256(self) -> str:
        raw = json.dumps(
            self.manifest(include_sha=False),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "binding": self.binding.manifest(),
            "source_architecture_sha256": {
                "water": self.water_architecture_sha256,
                "cleanser": self.cleanser_architecture_sha256,
                "fresh_pumps": self.fresh_pump_architecture_sha256,
                "manifold": self.manifold_architecture_sha256,
                "distribution": self.distribution_architecture_sha256,
                "waste_acquisition": self.waste_acquisition_architecture_sha256,
                "waste_pump_and_passive_backflow": self.waste_pump_architecture_sha256,
                "waste_cartridge": self.waste_cartridge_architecture_sha256,
                "realized_waste_manifest": self.realized_waste_manifest_sha256,
            },
            "realized_waste_release_state": self.realized_waste_release_state,
            "components": [record.manifest() for record in self.components],
            "routes": [record.manifest() for record in self.routes],
            "cavities": [record.manifest() for record in self.cavities],
            "package_reference_compound_brep_sha256": _brep_sha256(self.package_reference_compound),
            "unresolved_integration": list(self.unresolved_integration),
            "evidence_status": self.evidence_status,
            "physical_validation_eligible": False,
        }
        if include_sha:
            payload["integration_sha256"] = self.integration_sha256
        return payload


def _component(
    component_id: str,
    semantic_source: str,
    semantic_sha: str | None,
    maturity: str,
    *,
    fluid: str | None = None,
    cavity: str | None = None,
    interfaces: tuple[str, ...] = (),
    evidence: str,
    geometry: cq.Workplane | None = None,
    geometry_source: str | None = None,
    owner: str = "CELL_4",
) -> WetComponentRecord:
    return WetComponentRecord(
        component_id=component_id,
        owner=owner,
        semantic_source=semantic_source,
        semantic_source_sha256=semantic_sha,
        maturity=maturity,
        fluid_identity=fluid,
        cavity_classification=cavity,
        interface_ids=interfaces,
        evidence_status=evidence,
        geometry=geometry,
        geometry_source=geometry_source,
    )


def build_wet_system_package_integration(
    *,
    model: MasckOneModel | None = None,
) -> WetSystemPackageIntegration:
    model = model or build_model()
    authority = model.authority
    if str(authority.get("project", "authority_revision")) != AUTHORITY_REVISION:
        raise WetSystemPackageIngestionError("current authority revision changed")
    if tuple(authority.get("manufacturing", "hygiene_classes")) != FROZEN_HYGIENE_CLASSES:
        raise WetSystemPackageIngestionError("frozen hygiene vocabulary changed; rebind integration")

    # Use the released live-source waste wrapper once as the canonical downstream graph.
    current = build_current_waste_routing_sources()
    if current.authority.data != authority.data:
        raise WetSystemPackageIngestionError("model authority differs from current released wet source graph")

    water = build_water_reservoir_architecture(current.authority)
    cleanser = build_cleanser_storage_architecture(current.authority)
    fresh = build_fresh_pump_packaging_architecture(
        current.authority, water, cleanser, current.frame
    )
    manifold = build_distribution_manifold_architecture(
        current.authority, fresh, water, cleanser, current.frame
    )
    if current.distribution.source_manifold_architecture_sha256 != manifold.architecture_sha256:
        raise WetSystemPackageIngestionError("released distribution is stale for reconstructed fresh manifold")

    cartridge = build_waste_cartridge_architecture(
        current.authority,
        current.architecture,
        current.acquisition,
        current.distribution,
        current.frame,
    )

    realization = build_cell4_waste_backbone(
        source_git_sha=AUTHORED_AGAINST_MAIN_SHA,
        source_waste_pump_architecture_sha256=current.architecture.architecture_sha256,
        authority_revision=current.architecture.source_authority_revision,
    )
    release = Cell4WasteBackboneRelease(
        authored_against_git_sha=AUTHORED_AGAINST_MAIN_SHA,
        source_waste_pump_architecture_sha256=current.architecture.architecture_sha256,
        realization=realization,
    )
    release.validate_current_sources(current)

    components = tuple(sorted((
        _component(
            "WET-WATER-RESERVOIR-PACKAGE-REFERENCE",
            "water_reservoir.py:WaterReservoirArchitecture",
            water.architecture_sha256,
            CONTROLLED_ENVELOPE,
            fluid="FRESH_WATER",
            cavity=water.cavity_classification,
            interfaces=tuple(port.port_id for port in water.ports),
            evidence="CONTROLLED_MODEL_PACKAGE_REFERENCE_PLUS_RELEASED_STORAGE_ARCHITECTURE_NOT_REALIZED_RESERVOIR_BODY_OR_PHYSICAL_VOLUME_EVIDENCE",
            geometry=model.water_reservoir_envelope.solid,
            geometry_source="model.py:water_reservoir_envelope",
        ),
        _component(
            "WET-CLEANSER-RESERVOIR",
            "cleanser_storage.py:CleanserStorageArchitecture",
            cleanser.architecture_sha256,
            TOPOLOGY_ONLY,
            fluid="CLEANSER",
            cavity=cleanser.cavity_classification,
            interfaces=tuple(port.port_id for port in cleanser.ports),
            evidence="RELEASED_CLEANSER_STORAGE_SERVICE_TOPOLOGY_ONLY_CURRENT_REALIZED_CLEANSER_MODULE_PR_NOT_CONSUMED",
        ),
        _component(
            "WET-FRESH-WATER-PUMP",
            "fresh_pump_packaging.py:PUMP-STATION-WATER",
            fresh.architecture_sha256,
            TOPOLOGY_ONLY,
            fluid="FRESH_WATER",
            interfaces=(fresh.stations[0].source_port_id, fresh.stations[0].pump_outlet_interface_id),
            evidence="RELEASED_PUMP_STATION_TOPOLOGY_WITH_PACKAGE_SELECTION_AND_GEOMETRY_UNRESOLVED",
        ),
        _component(
            "WET-CLEANSER-PUMP",
            "fresh_pump_packaging.py:PUMP-STATION-CLEANSER",
            fresh.architecture_sha256,
            TOPOLOGY_ONLY,
            fluid="CLEANSER",
            interfaces=(fresh.stations[1].source_port_id, fresh.stations[1].pump_outlet_interface_id),
            evidence="RELEASED_PUMP_STATION_TOPOLOGY_WITH_PACKAGE_SELECTION_AND_GEOMETRY_UNRESOLVED",
        ),
        _component(
            "WET-FRESH-MANIFOLD",
            "distribution_manifold.py:DistributionManifoldArchitecture",
            manifold.architecture_sha256,
            TOPOLOGY_ONLY,
            interfaces=tuple(branch.inlet_interface_id for branch in manifold.branches),
            evidence="RELEASED_MANIFOLD_BRANCH_AND_OUTLET_TOPOLOGY_ONLY_NOT_TUBING_OR_HYDRAULIC_EVIDENCE",
        ),
        _component(
            "WET-FRESH-DISTRIBUTION",
            "distribution_geometry.py:DistributionGeometryArchitecture",
            current.distribution.architecture_sha256,
            DEVELOPMENT_GEOMETRY_REFERENCE,
            interfaces=tuple(item.outlet_id for item in current.distribution.placements),
            evidence="RELEASED_DEVELOPMENT_OUTLET_PLACEMENTS_AND_GROOVE_INTENTS_WITHOUT_PRODUCT_ROUTE_BREP_OR_PHYSICAL_FLOW_EVIDENCE",
        ),
        _component(
            "WET-WASTE-ACQUISITION",
            "waste_acquisition.py:WasteAcquisitionArchitecture",
            current.acquisition.architecture_sha256,
            TOPOLOGY_ONLY,
            fluid=PHASE_MIXED_WASTE,
            cavity="WET_DRAINABLE",
            interfaces=tuple(region.region_id for region in current.acquisition.regions),
            evidence="RELEASED_REGIONAL_ACQUISITION_TOPOLOGY_WITH_GUTTER_CAPILLARY_AND_BUFFER_GEOMETRY_UNRESOLVED",
        ),
        _component(
            "WET-WASTE-PUMP",
            "waste_pump_architecture.py:WastePumpArchitecture.station",
            current.architecture.architecture_sha256,
            TOPOLOGY_ONLY,
            fluid=PHASE_MIXED_WASTE,
            interfaces=(current.architecture.station.pump_inlet_interface_id, current.architecture.station.pump_outlet_interface_id),
            evidence="RELEASED_MIXED_WASTE_PUMP_STATION_TOPOLOGY_ONLY_NOT_SELECTED_PUMP_OR_PHYSICAL_PERFORMANCE_EVIDENCE",
        ),
        _component(
            "WET-WASTE-BACKFLOW-BARRIER",
            "waste_pump_architecture.py:PassiveBackflowBarrierReservation",
            current.architecture.architecture_sha256,
            TOPOLOGY_ONLY,
            fluid=PHASE_MIXED_WASTE,
            interfaces=(current.architecture.barrier.source_interface_id, current.architecture.barrier.target_interface_id),
            evidence="RELEASED_FIRST_CLASS_PASSIVE_BACKFLOW_STAGE_TOPOLOGY_ONLY_PHYSICAL_BACKFLOW_PERFORMANCE_UNVALIDATED",
        ),
        _component(
            "WET-WASTE-CARTRIDGE-PACKAGE-REFERENCE",
            "waste_cartridge.py:WasteCartridgeArchitecture",
            cartridge.architecture_sha256,
            CONTROLLED_ENVELOPE,
            fluid=PHASE_MIXED_WASTE,
            interfaces=(
                cartridge.interfaces.inlet_interface_id,
                cartridge.interfaces.key_interface_id,
                cartridge.interfaces.seal_interface_id,
                cartridge.interfaces.service_interface_id,
            ),
            evidence="AUTHORITY_CONTROLLED_EXTERNAL_PACKAGE_REFERENCE_ONLY_KEY_SEAL_SERVICE_TRAJECTORY_AND_USABLE_CAPACITY_UNRESOLVED",
            geometry=model.waste_cartridge_envelope.solid,
            geometry_source="model.py:waste_cartridge_envelope",
        ),
        _component(
            "DRY-BATTERY-PACKAGING-BENCHMARK",
            "authority.yaml:battery_reference",
            None,
            CONTROLLED_ENVELOPE,
            interfaces=(),
            evidence="AUTHORITY_PACKAGING_BENCHMARK_NOT_PRODUCTION_BATTERY_OR_DRY_BAY_REALIZATION",
            geometry=model.battery_reference_envelope.solid,
            geometry_source="model.py:battery_reference_envelope",
            owner="CELL_1_INTEGRATION",
        ),
        _component(
            "DRY-BAY",
            "structural_frame.py:FRAME_RESERVATION_HMI_ELECTRONICS",
            current.frame.topology_sha256,
            UNRESOLVED,
            interfaces=(RESERVATION_HMI_ELECTRONICS,),
            evidence="NO_CURRENT_RELEASED_DRY_BAY_PRODUCER_LEGACY_MANUAL_B_NOT_CONSUMED",
            owner="CELL_1_INTEGRATION",
        ),
        _component(
            "HARNESS",
            "structural_frame.py:FRAME_RESERVATION_HMI_ELECTRONICS",
            current.frame.topology_sha256,
            UNRESOLVED,
            interfaces=(RESERVATION_HMI_ELECTRONICS,),
            evidence="NO_CURRENT_RELEASED_HARNESS_PRODUCER_LEGACY_MANUAL_B_ROUTES_NOT_CONSUMED",
            owner="CELL_1_INTEGRATION",
        ),
        _component(
            "HMI",
            "structural_frame.py:FRAME_RESERVATION_HMI_ELECTRONICS",
            current.frame.topology_sha256,
            UNRESOLVED,
            interfaces=(RESERVATION_HMI_ELECTRONICS,),
            evidence="NO_CURRENT_RELEASED_PHYSICAL_HMI_PRODUCER_CLEAN_FIRST_INTENT_NOT_GEOMETRY_AUTHORITY",
            owner="CELL_1_INTEGRATION",
        ),
    ), key=lambda item: item.component_id))

    fresh_routes = tuple(
        WetRouteRecord(
            route_id=route.route_id,
            fluid_identity=route.fluid_identity,
            stage=route.stage,
            source_interface_id=route.source_interface_id,
            target_interface_id=route.target_interface_id,
            maturity=TOPOLOGY_ONLY,
            source_architecture_sha256=fresh.architecture_sha256,
            geometry_status=route.geometry_status,
            centerline_length_mm=None,
            geometric_dead_volume_mL=None,
            service_envelope_radius_mm=None,
            service_aabb=None,
        )
        for route in fresh.routes
    )
    waste_routes = tuple(
        WetRouteRecord(
            route_id=route.route_id,
            fluid_identity=route.fluid_identity,
            stage=route.stage,
            source_interface_id=route.source_interface_id,
            target_interface_id=route.target_interface_id,
            maturity=REALIZED_ROUTE,
            source_architecture_sha256=current.architecture.architecture_sha256,
            geometry_status=route.geometry_provenance,
            centerline_length_mm=route.centerline_length_mm,
            geometric_dead_volume_mL=route.geometric_dead_volume_mL,
            service_envelope_radius_mm=route.service_envelope_radius_mm,
            service_aabb=_service_aabb(route),
        )
        for route in release.realization.routes
    )

    cavities = tuple(
        [
            CavityClassRecord(
                "CAVITY-WATER-RESERVOIR",
                water.reservoir_id,
                water.cavity_classification,
                "PRODUCER_OWNED_RELEASED_CLASSIFICATION",
            ),
            CavityClassRecord(
                "CAVITY-CLEANSER-RESERVOIR",
                cleanser.reservoir_id,
                cleanser.cavity_classification,
                "PRODUCER_OWNED_RELEASED_CLASSIFICATION",
            ),
        ]
        + [
            CavityClassRecord(
                f"CAVITY-WASTE-ACQUISITION-{region.region_id}",
                region.region_id,
                region.hygiene_class,
                "PRODUCER_OWNED_RELEASED_CLASSIFICATION",
            )
            for region in current.acquisition.regions
        ]
        + [
            CavityClassRecord(
                "CAVITY-WASTE-CARTRIDGE",
                cartridge.cartridge_id,
                None,
                "UNRESOLVED_NO_RELEASED_CARTRIDGE_CAVITY_CLASSIFICATION_FIELD",
            ),
            CavityClassRecord(
                "CAVITY-FRESH-WATER-PUMP",
                fresh.stations[0].station_id,
                None,
                "UNRESOLVED_RELEASED_PUMP_ARCHITECTURE_HAS_NO_CAVITY_CLASSIFICATION",
            ),
            CavityClassRecord(
                "CAVITY-CLEANSER-PUMP",
                fresh.stations[1].station_id,
                None,
                "UNRESOLVED_RELEASED_PUMP_ARCHITECTURE_HAS_NO_CAVITY_CLASSIFICATION",
            ),
            CavityClassRecord(
                "CAVITY-DRY-BAY",
                RESERVATION_HMI_ELECTRONICS,
                None,
                "UNRESOLVED_NO_CURRENT_RELEASED_DRY_BAY_PRODUCER",
            ),
        ]
    )

    integration = WetSystemPackageIntegration(
        binding=WetSourceBinding(
            source_main_sha=SOURCE_MAIN_SHA,
            authority_revision=AUTHORITY_REVISION,
            authority_blob_sha=AUTHORITY_BLOB_SHA,
            world_frame_id=WORLD_FRAME_ID,
            source_blobs=SOURCE_BLOBS,
        ),
        water_architecture_sha256=water.architecture_sha256,
        cleanser_architecture_sha256=cleanser.architecture_sha256,
        fresh_pump_architecture_sha256=fresh.architecture_sha256,
        manifold_architecture_sha256=manifold.architecture_sha256,
        distribution_architecture_sha256=current.distribution.architecture_sha256,
        waste_acquisition_architecture_sha256=current.acquisition.architecture_sha256,
        waste_pump_architecture_sha256=current.architecture.architecture_sha256,
        waste_cartridge_architecture_sha256=cartridge.architecture_sha256,
        realized_waste_manifest_sha256=release.realization.manifest_sha256,
        realized_waste_release_state=release.release_state,
        components=components,
        routes=fresh_routes + waste_routes,
        cavities=cavities,
        unresolved_integration=(
            "FRESH_WATER_RESERVOIR_REALIZED_BODY_LID_AND_SERVICE_TRAJECTORY_NOT_RELEASED_MAIN",
            "CLEANSER_REALIZED_CASSETTE_CLOSURE_VENT_PICKUP_AND_SERVICE_ENVELOPE_NOT_RELEASED_MAIN",
            "FRESH_WATER_AND_CLEANSER_PUMP_PACKAGE_SELECTION_AND_REALIZED_CENTERLINES_NOT_RELEASED_MAIN",
            "WASTE_PUMP_AND_PASSIVE_BACKFLOW_HARDWARE_SELECTION_AND_PACKAGE_GEOMETRY_UNRESOLVED",
            "WASTE_CARTRIDGE_KEY_SEAL_INSERTION_REMOVAL_AND_SERVICE_TRAJECTORY_UNRESOLVED",
            "DRY_BAY_PCB_HARNESS_CHARGING_AND_PHYSICAL_HMI_HAVE_NO_CURRENT_RELEASED_PRODUCER",
            "WET_DRY_BULKHEAD_DRAIN_DRY_AND_WHOLE_PRODUCT_HYGIENE_CLOSURE_UNRESOLVED",
            "FLOW_LEAKAGE_RECOVERY_ORIENTATION_DRAINING_DRYING_AND_CLEANSER_COMPATIBILITY_PHYSICAL_GATES_OPEN",
            "INGRESS_ELECTRICAL_HMI_THERMAL_AND_RUNTIME_PHYSICAL_GATES_OPEN",
        ),
        evidence_status=DIGITAL_ONLY,
        physical_validation_eligible=False,
    )
    integration.validate()
    return integration


def export_wet_system_package_review(
    output_dir: str | Path,
    integration: WetSystemPackageIntegration | None = None,
) -> tuple[Path, ...]:
    integration = integration or build_wet_system_package_integration()
    integration.validate()
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    outputs: list[Path] = []
    compound_path = root / "cell1_wet_package_reference_compound.step"
    cq.exporters.export(integration.package_reference_compound, str(compound_path))
    outputs.append(compound_path)

    for route in integration.routes:
        if route.service_aabb is None:
            continue
        stem = route.route_id.lower().replace("-", "_")
        path = root / f"cell1_{stem}_service_aabb_reference.step"
        cq.exporters.export(route.service_aabb, str(path))
        outputs.append(path)

    manifest_path = root / "cell1_wet_system_package_ingestion_manifest.json"
    manifest_path.write_text(
        json.dumps(integration.manifest(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    outputs.append(manifest_path)
    return tuple(outputs)
