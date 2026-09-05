"""Source-bound realized CAD for the dedicated cleanser pump package.

The released dual-pump architecture controls a distinct CLEANSER station but deliberately
does not select a pump, package, tubing, connector, or hydraulic capability. This layer
therefore realizes only a conservative dimensional screening envelope, local interface
reservations, an open drainable cradle, and a stationary service-clearance reservation.
Supplier body references are package-screening evidence only and are not evidence of
cleanser compatibility, viscosity range, metering, pressure-flow performance, or selection.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import re

import cadquery as cq

from .authority import Authority
from .boundary_release import build_verified_interface_boundary_topology
from .cleanser_storage import CleanserStorageArchitecture, PORT_OUTLET, build_cleanser_storage_architecture
from .fresh_pump_packaging import (
    FLUID_CLEANSER,
    INTERFACE_CLEANSER_PUMP_OUTLET,
    ROUTE_CLEANSER_MANIFOLD,
    ROUTE_CLEANSER_SOURCE,
    STATION_CLEANSER,
    FreshPumpPackagingArchitecture,
    FreshPumpPackagingError,
    build_fresh_pump_packaging_architecture,
)
from .interface_attachment import build_interface_attachment_architecture
from .model import MasckOneModel, build_model
from .structural_frame import StructuralFrameTopology, build_structural_frame_topology
from .water_reservoir import WaterReservoirArchitecture, build_water_reservoir_architecture

WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
AUTHORED_AGAINST_MAIN_SHA = "21cf8c4fb8ca0d20ddb58f90bcee6275bc98ca30"
SOURCE_FRESH_PUMP_ARCHITECTURE_BLOB_SHA = "40cb6fb4c3efbfcf25ed0b7d7a75a4269d90a1b4"
SCHEMA = "MASCK_ONE_CELL4_REALIZED_CLEANSER_PUMP_V1"

# Official body dimensions observed on current supplier product pages on 2026-09-05.
# These references are intentionally reused only to bound hidden package space. They do
# not establish chemical compatibility, viscosity capability, flow, pressure, driver,
# accuracy, orientation behavior, life, or a supplier down-select for CLEANSER.
SUPPLIER_DIMENSIONAL_SCREENING_REFERENCES: tuple[dict[str, object], ...] = (
    {
        "reference_id": "BARTELS_BP7_BODY_DIMENSION_SCREEN_2026-09-05",
        "manufacturer": "Bartels Mikrotechnik",
        "model_family": "The Bartels Pump | BP7",
        "body_envelope_xyz_mm": [30.0, 15.0, 3.8],
        "source_type": "OFFICIAL_PRODUCT_PAGE",
        "source_url": "https://bartels-mikrotechnik.de/product/the-bartels-pump-bp7-piezo-pump/",
        "selection_status": "DIMENSIONAL_SCREEN_ONLY_NOT_CLEANSER_SUITABILITY_OR_SELECTION",
    },
    {
        "reference_id": "TAKASAGO_SDMP302_306_BODY_DIMENSION_SCREEN_2026-09-05",
        "manufacturer": "Takasago Fluidic Systems",
        "model_family": "SDMP302 / SDMP306 standard series",
        "body_envelope_xyz_mm": [25.0, 25.0, 4.8],
        "source_type": "OFFICIAL_PRODUCT_PAGE",
        "source_url": "https://www.takasago-fluidics.com/products/sdmp-s",
        "selection_status": "DIMENSIONAL_SCREEN_ONLY_NOT_CLEANSER_SUITABILITY_OR_SELECTION",
    },
    {
        "reference_id": "TAKASAGO_SDMP302D_306D_BODY_DIMENSION_SCREEN_2026-09-05",
        "manufacturer": "Takasago Fluidic Systems",
        "model_family": "SDMP302D / SDMP306D built-in driver series",
        "body_envelope_xyz_mm": [25.0, 25.0, 8.2],
        "source_type": "OFFICIAL_PRODUCT_PAGE",
        "source_url": "https://www.takasago-fluidics.com/products/sdmp-d",
        "selection_status": "DIMENSIONAL_SCREEN_ONLY_NOT_CLEANSER_SUITABILITY_OR_SELECTION",
    },
)


def _screening_sha256() -> str:
    raw = json.dumps(
        SUPPLIER_DIMENSIONAL_SCREENING_REFERENCES,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(raw).hexdigest()


SUPPLIER_DIMENSIONAL_SCREENING_SHA256 = _screening_sha256()
SUPPLIER_SCREENING_EVIDENCE_STATUS = (
    "OFFICIAL_BODY_DIMENSIONS_FOR_DIGITAL_PACKAGE_SCREENING_ONLY_"
    "NOT_CLEANSER_COMPATIBILITY_VISCOSITY_PERFORMANCE_OR_SELECTION"
)

REFERENCE_PACKAGE_ID = "PUMP-STATION-CLEANSER-CELL4-DIMENSIONAL-SCREENING-ENVELOPE"
INLET_DATUM_ID = "PUMP-STATION-CLEANSER-INLET-DATUM-CELL4"
OUTLET_DATUM_ID = INTERFACE_CLEANSER_PUMP_OUTLET
PORT_DATUM_IDS = (INLET_DATUM_ID, OUTLET_DATUM_ID)

# Wearer-right counterpart to the water station's wearer-left packaging band. Placement
# is a provisional Cell 4 world-frame baseline, not an authority-level supplier package.
PACKAGE_CENTER_WORLD_MM = (46.0, -10.0, 7.0)
PACKAGE_ENVELOPE_XYZ_MM = (30.0, 25.0, 8.2)
PACKAGE_LONG_AXIS_WORLD = "+X"
PACKAGE_CLEARANCE_RESERVATION_MM = 2.0

# Local port reservation geometry is deliberately not a tubing selection. Released
# architecture has no tubing ID, bend radius, or connector standard.
PORT_LUMEN_DIAMETER_SEED_MM = 2.0
PORT_RESERVATION_DIAMETER_MM = 4.0
PORT_RESERVATION_PROJECTION_MM = 2.0
INLET_CENTER_WORLD_MM = (31.0, -7.0, 7.0)
OUTLET_CENTER_WORLD_MM = (31.0, -13.0, 7.0)
PORT_AXIS_WORLD = (-1.0, 0.0, 0.0)

# Open-ended local cradle. Both Y ends remain open so this does not create an enclosed
# wet pocket. Frame join and retention are deliberately unresolved.
SUPPORT_BASE_XYZ_MM = (32.8, 27.0, 1.5)
SUPPORT_BASE_CENTER_WORLD_MM = (46.0, -10.0, 1.65)
SUPPORT_RAIL_XYZ_MM = (1.0, 27.0, 8.2)
SUPPORT_RAIL_CENTER_X_MM = (30.1, 61.9)
SUPPORT_RAIL_CENTER_Y_MM = -10.0
SUPPORT_RAIL_CENTER_Z_MM = 6.5
SUPPORT_PACKAGE_SIDE_GAP_SEED_MM = 0.4
SUPPORT_PACKAGE_BASE_GAP_SEED_MM = 0.5
SUPPORT_CAVITY_CLASSIFICATION = "WET_DRAINABLE"

SERVICE_CLEARANCE_CENTER_WORLD_MM = PACKAGE_CENTER_WORLD_MM
SERVICE_CLEARANCE_XYZ_MM = (34.0, 29.0, 12.2)
SERVICE_CLEARANCE_BOUNDS_WORLD_MM = {
    "x": (29.0, 63.0),
    "y": (-24.5, 4.5),
    "z": (0.9, 13.1),
}

REFERENCE_PACKAGE_STATUS = (
    "DIMENSIONAL_SCREENING_ENVELOPE_NOT_SELECTED_CLEANSER_PUMP_PACKAGE"
)
PORT_STATUS = "PROVISIONAL_LOCAL_INTERFACE_RESERVATION_NOT_TUBING_CONNECTOR_OR_FLOW_SIZING"
SUPPORT_STATUS = "PROVISIONAL_DRAINABLE_LOCAL_CRADLE_FRAME_JOIN_AND_RETENTION_UNRESOLVED"
SERVICE_STATUS = "LOCAL_DIGITAL_CLEARANCE_RESERVED_REPLACEMENT_TRAJECTORY_UNRESOLVED"
ROUTING_STATUS = (
    "PUMP_LOCAL_PORT_DATUMS_REALIZED_SOURCE_AND_MANIFOLD_CENTERLINES_REMAIN_UNRESOLVED"
)
PHYSICAL_EVIDENCE_STATUS = (
    "DIGITAL_CLEANSER_PUMP_PACKAGE_PORT_SUPPORT_AND_CLEARANCE_GEOMETRY_ONLY_NOT_"
    "SUPPLIER_SELECTION_CHEMICAL_COMPATIBILITY_VISCOSITY_FLOW_PRESSURE_METERING_"
    "PRIMING_LEAK_ORIENTATION_SERVICE_DURABILITY_RUNTIME_OR_PHYSICAL_EVIDENCE"
)

_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
_GIT_SHA_RE = re.compile(r"[0-9a-f]{40}\Z")


class RealizedCleanserPumpError(ValueError):
    pass


def _box(dx: float, dy: float, dz: float, center: tuple[float, float, float]) -> cq.Workplane:
    return cq.Workplane("XY").box(dx, dy, dz, centered=(True, True, True)).translate(center)


def _x_cylinder_between(
    *,
    y_mm: float,
    z_mm: float,
    x0_mm: float,
    x1_mm: float,
    diameter_mm: float,
) -> cq.Workplane:
    xmin = min(x0_mm, x1_mm)
    length = abs(x1_mm - x0_mm)
    return (
        cq.Workplane("YZ")
        .workplane(offset=xmin)
        .center(y_mm, z_mm)
        .circle(diameter_mm / 2.0)
        .extrude(length)
    )


def _one_valid_solid(shape: cq.Workplane, label: str) -> None:
    if shape.solids().size() != 1 or not shape.val().isValid() or shape.val().Volume() <= 0.0:
        raise RealizedCleanserPumpError(f"{label} must be one valid positive deterministic solid")


def _intersection_volume(a: cq.Workplane, b: cq.Workplane) -> float:
    return float(a.val().intersect(b.val()).Volume())


def _outside_volume(shape: cq.Workplane, envelope: cq.Workplane) -> float:
    return float(shape.val().cut(envelope.val()).Volume())


@dataclass(frozen=True, slots=True)
class CurrentCleanserPumpSources:
    model: MasckOneModel
    authority: Authority
    water: WaterReservoirArchitecture
    cleanser: CleanserStorageArchitecture
    frame: StructuralFrameTopology
    architecture: FreshPumpPackagingArchitecture

    def validate(self) -> None:
        if type(self.model) is not MasckOneModel:
            raise RealizedCleanserPumpError("current model must use exact MasckOneModel type")
        if type(self.authority) is not Authority:
            raise RealizedCleanserPumpError("current authority must use exact Authority type")
        if type(self.water) is not WaterReservoirArchitecture:
            raise RealizedCleanserPumpError("current water source must use exact WaterReservoirArchitecture")
        if type(self.cleanser) is not CleanserStorageArchitecture:
            raise RealizedCleanserPumpError("current cleanser source must use exact CleanserStorageArchitecture")
        if type(self.frame) is not StructuralFrameTopology:
            raise RealizedCleanserPumpError("current frame must use exact StructuralFrameTopology")
        if type(self.architecture) is not FreshPumpPackagingArchitecture:
            raise RealizedCleanserPumpError("current pump source must use exact FreshPumpPackagingArchitecture")
        try:
            self.architecture.validate_current_sources(
                authority=self.authority,
                water=self.water,
                cleanser=self.cleanser,
                frame=self.frame,
            )
        except FreshPumpPackagingError as exc:
            raise RealizedCleanserPumpError("current cleanser-pump source graph is stale or corrupted") from exc


def build_current_cleanser_pump_sources() -> CurrentCleanserPumpSources:
    """Reconstruct the current repository-rooted cleanser-pump source graph once."""
    model = build_model()
    boundaries = build_verified_interface_boundary_topology(
        model.authority,
        model.facial_surface,
        model.coverage_mesh,
        model.compliant_interface_topology,
    )
    attachment = build_interface_attachment_architecture(model.authority, boundaries)
    frame = build_structural_frame_topology(model.authority, attachment)
    water = build_water_reservoir_architecture(model.authority)
    cleanser = build_cleanser_storage_architecture(model.authority)
    architecture = build_fresh_pump_packaging_architecture(
        model.authority,
        water,
        cleanser,
        frame,
    )
    sources = CurrentCleanserPumpSources(
        model=model,
        authority=model.authority,
        water=water,
        cleanser=cleanser,
        frame=frame,
        architecture=architecture,
    )
    sources.validate()
    return sources


@dataclass(frozen=True, slots=True)
class RealizedCleanserPumpPortDatum:
    datum_id: str
    route_id: str
    role: str
    source_interface_id: str
    target_interface_id: str
    center_world_mm: tuple[float, float, float]
    axis_world: tuple[float, float, float]
    fluid_identity: str = FLUID_CLEANSER
    lumen_diameter_seed_mm: float = PORT_LUMEN_DIAMETER_SEED_MM
    reservation_diameter_mm: float = PORT_RESERVATION_DIAMETER_MM
    reservation_projection_mm: float = PORT_RESERVATION_PROJECTION_MM
    status: str = PORT_STATUS

    def __post_init__(self) -> None:
        if self.datum_id not in PORT_DATUM_IDS:
            raise RealizedCleanserPumpError(f"unknown cleanser-pump port datum {self.datum_id!r}")
        if self.route_id not in (ROUTE_CLEANSER_SOURCE, ROUTE_CLEANSER_MANIFOLD):
            raise RealizedCleanserPumpError("cleanser-pump datum route ID is not controlled")
        if self.fluid_identity != FLUID_CLEANSER:
            raise RealizedCleanserPumpError("cleanser-pump datum must retain exact CLEANSER identity")
        if tuple(float(v) for v in self.axis_world) != PORT_AXIS_WORLD:
            raise RealizedCleanserPumpError("cleanser-pump provisional local port axes must retain -X world direction")
        if not all(type(v) in (int, float) and math.isfinite(float(v)) for v in self.center_world_mm):
            raise RealizedCleanserPumpError("cleanser-pump datum center must contain finite numeric scalars")
        if self.lumen_diameter_seed_mm != PORT_LUMEN_DIAMETER_SEED_MM:
            raise RealizedCleanserPumpError("cleanser-pump local lumen seed changed")
        if self.reservation_diameter_mm != PORT_RESERVATION_DIAMETER_MM:
            raise RealizedCleanserPumpError("cleanser-pump reservation diameter changed")
        if self.reservation_projection_mm != PORT_RESERVATION_PROJECTION_MM:
            raise RealizedCleanserPumpError("cleanser-pump reservation projection changed")
        if self.status != PORT_STATUS:
            raise RealizedCleanserPumpError("cleanser-pump port evidence boundary changed")

    @property
    def lumen_area_seed_mm2(self) -> float:
        return math.pi * (self.lumen_diameter_seed_mm / 2.0) ** 2

    def manifest(self) -> dict[str, object]:
        return {
            "datum_id": self.datum_id,
            "route_id": self.route_id,
            "fluid_identity": self.fluid_identity,
            "role": self.role,
            "source_interface_id": self.source_interface_id,
            "target_interface_id": self.target_interface_id,
            "center_world_mm": list(self.center_world_mm),
            "axis_world": list(self.axis_world),
            "lumen_diameter_seed_mm": self.lumen_diameter_seed_mm,
            "lumen_area_seed_mm2": self.lumen_area_seed_mm2,
            "reservation_diameter_mm": self.reservation_diameter_mm,
            "reservation_projection_mm": self.reservation_projection_mm,
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class RealizedCleanserPump:
    source_authority_revision: str
    source_fresh_pump_architecture_sha256: str
    source_cleanser_architecture_sha256: str
    authored_against_git_sha: str
    source_architecture_blob_sha: str
    package_reference_solid: cq.Workplane
    support_cradle_solid: cq.Workplane
    inlet_port_reservation_solid: cq.Workplane
    outlet_port_reservation_solid: cq.Workplane
    service_clearance_solid: cq.Workplane
    port_datums: tuple[RealizedCleanserPumpPortDatum, RealizedCleanserPumpPortDatum]
    station_id: str = STATION_CLEANSER
    reference_package_id: str = REFERENCE_PACKAGE_ID
    fluid_identity: str = FLUID_CLEANSER
    supplier_package_candidate_id: str | None = None
    supplier_package_evidence_sha256: str | None = None
    supplier_dimensional_screening_sha256: str = SUPPLIER_DIMENSIONAL_SCREENING_SHA256
    support_cavity_classification: str = SUPPORT_CAVITY_CLASSIFICATION
    reference_package_status: str = REFERENCE_PACKAGE_STATUS
    support_status: str = SUPPORT_STATUS
    service_status: str = SERVICE_STATUS
    routing_status: str = ROUTING_STATUS
    physical_validation_eligible: bool = False
    evidence_status: str = PHYSICAL_EVIDENCE_STATUS

    def __post_init__(self) -> None:
        self.validate_invariants()

    @property
    def reference_envelope_volume_mm3(self) -> float:
        return float(self.package_reference_solid.val().Volume())

    @property
    def manifest_sha256(self) -> str:
        raw = json.dumps(
            self.manifest(include_sha=False),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return sha256(raw).hexdigest()

    def validate_invariants(self) -> None:
        if type(self.source_authority_revision) is not str or not self.source_authority_revision:
            raise RealizedCleanserPumpError("realized cleanser pump requires exact authority revision")
        for value, label in (
            (self.source_fresh_pump_architecture_sha256, "fresh-pump architecture source"),
            (self.source_cleanser_architecture_sha256, "cleanser architecture source"),
            (self.supplier_dimensional_screening_sha256, "supplier dimensional screening record"),
        ):
            if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
                raise RealizedCleanserPumpError(f"{label} must be canonical lowercase SHA-256")
        for value, label in (
            (self.authored_against_git_sha, "authored-against Git provenance"),
            (self.source_architecture_blob_sha, "fresh-pump source blob"),
        ):
            if type(value) is not str or _GIT_SHA_RE.fullmatch(value) is None:
                raise RealizedCleanserPumpError(f"{label} must be exact lowercase 40-hex")
        if self.station_id != STATION_CLEANSER or self.fluid_identity != FLUID_CLEANSER:
            raise RealizedCleanserPumpError("realized package must remain the controlled CLEANSER pump station")
        if self.reference_package_id != REFERENCE_PACKAGE_ID:
            raise RealizedCleanserPumpError("realized cleanser-pump reference package ID changed")
        if self.supplier_package_candidate_id is not None or self.supplier_package_evidence_sha256 is not None:
            raise RealizedCleanserPumpError("dimensional screen cannot imply a selected cleanser pump")
        if self.supplier_dimensional_screening_sha256 != SUPPLIER_DIMENSIONAL_SCREENING_SHA256:
            raise RealizedCleanserPumpError("supplier dimensional screening record changed")
        if self.support_cavity_classification != SUPPORT_CAVITY_CLASSIFICATION:
            raise RealizedCleanserPumpError("cleanser-pump support cavity must remain WET_DRAINABLE")
        if (
            self.reference_package_status != REFERENCE_PACKAGE_STATUS
            or self.support_status != SUPPORT_STATUS
            or self.service_status != SERVICE_STATUS
            or self.routing_status != ROUTING_STATUS
        ):
            raise RealizedCleanserPumpError("cleanser-pump package/support/service/routing evidence boundary changed")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise RealizedCleanserPumpError("digital cleanser-pump package cannot become physical validation evidence")
        if self.evidence_status != PHYSICAL_EVIDENCE_STATUS:
            raise RealizedCleanserPumpError("cleanser-pump physical-evidence firewall changed")
        if tuple(item.datum_id for item in self.port_datums) != PORT_DATUM_IDS:
            raise RealizedCleanserPumpError("cleanser-pump port datum identity/order changed")
        if tuple(item.center_world_mm for item in self.port_datums) != (
            INLET_CENTER_WORLD_MM,
            OUTLET_CENTER_WORLD_MM,
        ):
            raise RealizedCleanserPumpError("cleanser-pump port datum placement changed")
        for label, shape in (
            ("reference package", self.package_reference_solid),
            ("support cradle", self.support_cradle_solid),
            ("inlet reservation", self.inlet_port_reservation_solid),
            ("outlet reservation", self.outlet_port_reservation_solid),
            ("service clearance", self.service_clearance_solid),
        ):
            _one_valid_solid(shape, f"cleanser pump {label}")
        if not math.isclose(
            self.reference_envelope_volume_mm3,
            math.prod(PACKAGE_ENVELOPE_XYZ_MM),
            abs_tol=1e-8,
        ):
            raise RealizedCleanserPumpError("cleanser-pump dimensional screening envelope changed")
        if _intersection_volume(self.package_reference_solid, self.support_cradle_solid) > 1e-7:
            raise RealizedCleanserPumpError("cleanser-pump screening envelope overlaps support material")
        for shape in (
            self.package_reference_solid,
            self.support_cradle_solid,
            self.inlet_port_reservation_solid,
            self.outlet_port_reservation_solid,
        ):
            if _outside_volume(shape, self.service_clearance_solid) > 1e-7:
                raise RealizedCleanserPumpError(
                    "cleanser-pump local geometry escapes controlled service-clearance reservation"
                )

    def validate_current_sources(
        self,
        sources: CurrentCleanserPumpSources,
    ) -> FreshPumpPackagingArchitecture:
        if type(sources) is not CurrentCleanserPumpSources:
            raise RealizedCleanserPumpError("sources must use exact CurrentCleanserPumpSources type")
        sources.validate()
        architecture = sources.architecture
        if self.source_authority_revision != str(sources.authority.get("project", "authority_revision")):
            raise RealizedCleanserPumpError("realized cleanser-pump package is stale for current authority")
        if self.source_fresh_pump_architecture_sha256 != architecture.architecture_sha256:
            raise RealizedCleanserPumpError("realized cleanser-pump package is stale for current pump architecture")
        if self.source_cleanser_architecture_sha256 != sources.cleanser.architecture_sha256:
            raise RealizedCleanserPumpError("realized cleanser-pump package is stale for current cleanser architecture")
        station = next(
            (item for item in architecture.stations if item.station_id == STATION_CLEANSER),
            None,
        )
        if station is None or station.fluid_identity != FLUID_CLEANSER:
            raise RealizedCleanserPumpError("current cleanser-pump station identity changed")
        unresolved = (
            station.package_candidate_id,
            station.package_evidence_sha256,
            station.envelope_mm,
            station.placement_xyz_mm,
            station.orientation_axis_xyz,
            station.tubing_inner_diameter_mm,
            station.minimum_bend_radius_mm,
            station.connector_standard,
        )
        if any(value is not None for value in unresolved):
            raise RealizedCleanserPumpError(
                "current source now carries supplier/package/routing selection; retire Cell 4 cleanser screening envelope"
            )
        return architecture

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "source_authority_revision": self.source_authority_revision,
            "source_fresh_pump_architecture_sha256": self.source_fresh_pump_architecture_sha256,
            "source_cleanser_architecture_sha256": self.source_cleanser_architecture_sha256,
            "authored_against_git_sha": self.authored_against_git_sha,
            "authored_against_git_sha_role": "HISTORICAL_PROVENANCE_ONLY_NOT_RELEASE_FRESHNESS_PROOF",
            "source_architecture_blob_sha": self.source_architecture_blob_sha,
            "world_frame_id": WORLD_FRAME_ID,
            "station_id": self.station_id,
            "fluid_identity": self.fluid_identity,
            "reference_package_id": self.reference_package_id,
            "supplier_package_candidate_id": self.supplier_package_candidate_id,
            "supplier_package_evidence_sha256": self.supplier_package_evidence_sha256,
            "supplier_dimensional_screening": {
                "record_sha256": self.supplier_dimensional_screening_sha256,
                "evidence_status": SUPPLIER_SCREENING_EVIDENCE_STATUS,
                "references": [dict(item) for item in SUPPLIER_DIMENSIONAL_SCREENING_REFERENCES],
                "selection_status": "NO_CLEANSER_PUMP_SELECTED",
            },
            "reference_package": {
                "center_world_mm": list(PACKAGE_CENTER_WORLD_MM),
                "envelope_xyz_mm": list(PACKAGE_ENVELOPE_XYZ_MM),
                "long_axis_world": PACKAGE_LONG_AXIS_WORLD,
                "geometric_envelope_volume_mm3": self.reference_envelope_volume_mm3,
                "status": self.reference_package_status,
                "evidence_role": (
                    "FIT_AND_COLLISION_DIMENSIONAL_SCREEN_ONLY_NOT_SELECTED_CLEANSER_PUMP_OR_MASS"
                ),
            },
            "ports": [item.manifest() for item in self.port_datums],
            "support": {
                "architecture": "OPEN_Y_END_U_CRADLE",
                "base_xyz_mm": list(SUPPORT_BASE_XYZ_MM),
                "base_center_world_mm": list(SUPPORT_BASE_CENTER_WORLD_MM),
                "rail_xyz_mm": list(SUPPORT_RAIL_XYZ_MM),
                "rail_center_x_mm": list(SUPPORT_RAIL_CENTER_X_MM),
                "rail_center_y_mm": SUPPORT_RAIL_CENTER_Y_MM,
                "rail_center_z_mm": SUPPORT_RAIL_CENTER_Z_MM,
                "package_side_gap_seed_mm": SUPPORT_PACKAGE_SIDE_GAP_SEED_MM,
                "package_base_gap_seed_mm": SUPPORT_PACKAGE_BASE_GAP_SEED_MM,
                "cavity_classification": self.support_cavity_classification,
                "drain_dry_path": "OPEN_AT_BOTH_Y_ENDS_NO_ENCLOSED_SUPPORT_CAVITY",
                "frame_join_geometry": None,
                "retention_geometry": None,
                "status": self.support_status,
            },
            "service_clearance": {
                "reservation_mm": PACKAGE_CLEARANCE_RESERVATION_MM,
                "center_world_mm": list(SERVICE_CLEARANCE_CENTER_WORLD_MM),
                "xyz_mm": list(SERVICE_CLEARANCE_XYZ_MM),
                "bounds_world_mm": {
                    key: list(value) for key, value in SERVICE_CLEARANCE_BOUNDS_WORLD_MM.items()
                },
                "replacement_trajectory_world_mm": None,
                "precondition": (
                    "MASK_UNPOWERED_LOCAL_SERVICE_ACCESS_SHELL_OR_SERVICE_OPENING_NOT_YET_REALIZED"
                ),
                "status": self.service_status,
            },
            "routing": {
                "source_route_id": ROUTE_CLEANSER_SOURCE,
                "source_interface_id": PORT_OUTLET,
                "pump_station_id": STATION_CLEANSER,
                "pump_outlet_interface_id": INTERFACE_CLEANSER_PUMP_OUTLET,
                "downstream_route_id": ROUTE_CLEANSER_MANIFOLD,
                "downstream_interface_id": "MANIFOLD-INLET-CLEANSER-I23",
                "source_to_pump_centerline": None,
                "pump_to_manifold_centerline": None,
                "tubing_inner_diameter_mm": None,
                "minimum_bend_radius_mm": None,
                "connector_standard": None,
                "status": self.routing_status,
            },
            "performance_claims": {
                "cleanser_compatibility": None,
                "viscosity_limit_mPa_s": None,
                "flow_curve": None,
                "pressure_capability": None,
                "metering_accuracy": None,
                "priming_behavior": None,
                "orientation_independence": None,
                "acoustic_performance": None,
                "runtime": None,
            },
            "fresh_water_identity_unchanged": True,
            "mixed_waste_architecture_unchanged": (
                "ACQUISITION_TO_WASTE_PUMP_TO_PASSIVE_BACKFLOW_PROTECTION_TO_CARTRIDGE"
            ),
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            payload["manifest_sha256"] = self.manifest_sha256
        return payload


def build_realized_cleanser_pump(
    sources: CurrentCleanserPumpSources,
) -> RealizedCleanserPump:
    if type(sources) is not CurrentCleanserPumpSources:
        raise RealizedCleanserPumpError("sources must use exact CurrentCleanserPumpSources type")
    sources.validate()

    package = _box(*PACKAGE_ENVELOPE_XYZ_MM, PACKAGE_CENTER_WORLD_MM)
    base = _box(*SUPPORT_BASE_XYZ_MM, SUPPORT_BASE_CENTER_WORLD_MM)
    left_rail = _box(
        *SUPPORT_RAIL_XYZ_MM,
        (SUPPORT_RAIL_CENTER_X_MM[0], SUPPORT_RAIL_CENTER_Y_MM, SUPPORT_RAIL_CENTER_Z_MM),
    )
    right_rail = _box(
        *SUPPORT_RAIL_XYZ_MM,
        (SUPPORT_RAIL_CENTER_X_MM[1], SUPPORT_RAIL_CENTER_Y_MM, SUPPORT_RAIL_CENTER_Z_MM),
    )
    support = base.union(left_rail).union(right_rail)

    package_inner_face_x = PACKAGE_CENTER_WORLD_MM[0] - PACKAGE_ENVELOPE_XYZ_MM[0] / 2.0
    port_tip_x = package_inner_face_x - PORT_RESERVATION_PROJECTION_MM
    inlet_reservation = _x_cylinder_between(
        y_mm=INLET_CENTER_WORLD_MM[1],
        z_mm=INLET_CENTER_WORLD_MM[2],
        x0_mm=package_inner_face_x,
        x1_mm=port_tip_x,
        diameter_mm=PORT_RESERVATION_DIAMETER_MM,
    )
    outlet_reservation = _x_cylinder_between(
        y_mm=OUTLET_CENTER_WORLD_MM[1],
        z_mm=OUTLET_CENTER_WORLD_MM[2],
        x0_mm=package_inner_face_x,
        x1_mm=port_tip_x,
        diameter_mm=PORT_RESERVATION_DIAMETER_MM,
    )
    service_clearance = _box(
        *SERVICE_CLEARANCE_XYZ_MM,
        SERVICE_CLEARANCE_CENTER_WORLD_MM,
    )

    ports = (
        RealizedCleanserPumpPortDatum(
            datum_id=INLET_DATUM_ID,
            route_id=ROUTE_CLEANSER_SOURCE,
            role="CLEANSER_SOURCE_TO_PUMP_PROVISIONAL_LOCAL_INTERFACE_DATUM",
            source_interface_id=PORT_OUTLET,
            target_interface_id=STATION_CLEANSER,
            center_world_mm=INLET_CENTER_WORLD_MM,
            axis_world=PORT_AXIS_WORLD,
        ),
        RealizedCleanserPumpPortDatum(
            datum_id=OUTLET_DATUM_ID,
            route_id=ROUTE_CLEANSER_MANIFOLD,
            role="CLEANSER_PUMP_TO_MANIFOLD_PROVISIONAL_LOCAL_INTERFACE_DATUM",
            source_interface_id=INTERFACE_CLEANSER_PUMP_OUTLET,
            target_interface_id="MANIFOLD-INLET-CLEANSER-I23",
            center_world_mm=OUTLET_CENTER_WORLD_MM,
            axis_world=PORT_AXIS_WORLD,
        ),
    )

    realized = RealizedCleanserPump(
        source_authority_revision=str(sources.authority.get("project", "authority_revision")),
        source_fresh_pump_architecture_sha256=sources.architecture.architecture_sha256,
        source_cleanser_architecture_sha256=sources.cleanser.architecture_sha256,
        authored_against_git_sha=AUTHORED_AGAINST_MAIN_SHA,
        source_architecture_blob_sha=SOURCE_FRESH_PUMP_ARCHITECTURE_BLOB_SHA,
        package_reference_solid=package,
        support_cradle_solid=support,
        inlet_port_reservation_solid=inlet_reservation,
        outlet_port_reservation_solid=outlet_reservation,
        service_clearance_solid=service_clearance,
        port_datums=ports,
    )
    realized.validate_current_sources(sources)
    return realized


def build_current_realized_cleanser_pump() -> RealizedCleanserPump:
    """Trusted path that always reconstructs the current repository source graph."""
    return build_realized_cleanser_pump(build_current_cleanser_pump_sources())
