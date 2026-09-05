"""Source-bound fresh-water pump packaging realization.

The controlled Iteration-22 architecture intentionally does not select a production
pump. This layer therefore realizes a conservative digital screening envelope that
bounds three current official supplier-body references, plus provisional local port,
support and service geometry. Supplier references remain screening evidence only and
cannot promote a package selection, hydraulic performance, electrical performance or
physical service validation.
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
from .cleanser_storage import CleanserStorageArchitecture, build_cleanser_storage_architecture
from .fresh_pump_packaging import (
    FLUID_FRESH_WATER,
    INTERFACE_WATER_PUMP_OUTLET,
    ROUTE_WATER_MANIFOLD,
    ROUTE_WATER_SOURCE,
    STATION_WATER,
    FreshPumpPackagingArchitecture,
    FreshPumpPackagingError,
    build_fresh_pump_packaging_architecture,
)
from .interface_attachment import build_interface_attachment_architecture
from .model import MasckOneModel, build_model
from .structural_frame import StructuralFrameTopology, build_structural_frame_topology
from .water_reservoir import (
    PORT_PICKUP,
    WaterReservoirArchitecture,
    build_water_reservoir_architecture,
)

WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
AUTHORED_AGAINST_MAIN_SHA = "628ec5f5766937433b1bdf8f30edc372924cf41e"
SOURCE_FRESH_PUMP_ARCHITECTURE_BLOB_SHA = "40cb6fb4c3efbfcf25ed0b7d7a75a4269d90a1b4"
SCHEMA = "MASCK_ONE_CELL4_REALIZED_FRESH_WATER_PUMP_V2"

# Official supplier pages observed 2026-09-05. These records capture only published
# body dimensions needed for package screening. They are not a supplier down-select,
# purchase specification, performance acceptance, connector definition or qualification.
SUPPLIER_SCREENING_REFERENCES: tuple[dict[str, object], ...] = (
    {
        "reference_id": "BARTELS_BP7_BODY_SCREEN_2026-09-05",
        "manufacturer": "Bartels Mikrotechnik",
        "model_family": "The Bartels Pump | BP7",
        "body_envelope_xyz_mm": [30.0, 15.0, 3.8],
        "source_type": "OFFICIAL_PRODUCT_PAGE",
        "source_url": "https://bartels-mikrotechnik.de/product/the-bartels-pump-bp7-piezo-pump/",
        "observed_date": "2026-09-05",
        "selection_status": "SCREENING_REFERENCE_ONLY_NOT_SELECTED",
    },
    {
        "reference_id": "TAKASAGO_SDMP302_306_BODY_SCREEN_2026-09-05",
        "manufacturer": "Takasago Fluidic Systems",
        "model_family": "SDMP302 / SDMP306 standard series",
        "body_envelope_xyz_mm": [25.0, 25.0, 4.8],
        "source_type": "OFFICIAL_PRODUCT_PAGE",
        "source_url": "https://www.takasago-fluidics.com/products/sdmp-s",
        "observed_date": "2026-09-05",
        "selection_status": "SCREENING_REFERENCE_ONLY_NOT_SELECTED",
    },
    {
        "reference_id": "TAKASAGO_SDMP302D_306D_BODY_SCREEN_2026-09-05",
        "manufacturer": "Takasago Fluidic Systems",
        "model_family": "SDMP302D / SDMP306D built-in driver series",
        "body_envelope_xyz_mm": [25.0, 25.0, 8.2],
        "source_type": "OFFICIAL_PRODUCT_PAGE",
        "source_url": "https://www.takasago-fluidics.com/products/sdmp-d",
        "observed_date": "2026-09-05",
        "selection_status": "SCREENING_REFERENCE_ONLY_NOT_SELECTED",
    },
)


def _supplier_screening_record_sha256() -> str:
    raw = json.dumps(
        SUPPLIER_SCREENING_REFERENCES,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(raw).hexdigest()


SUPPLIER_SCREENING_RECORD_SHA256 = _supplier_screening_record_sha256()
SUPPLIER_SCREENING_RECORD_HASH_ROLE = (
    "HASH_OF_NORMALIZED_CELL4_DIMENSIONAL_SCREENING_RECORD_NOT_VENDOR_DOCUMENT_HASH"
)
SUPPLIER_SCREENING_EVIDENCE_STATUS = (
    "VERIFIED_OFFICIAL_BODY_DIMENSIONS_FOR_DIGITAL_SCREENING_ONLY_NOT_SUPPLIER_SELECTION"
)

REFERENCE_PACKAGE_ID = "PUMP-STATION-WATER-CELL4-SUPPLIER-FAMILY-SCREENING-ENVELOPE"
INLET_DATUM_ID = "PUMP-STATION-WATER-INLET-DATUM-CELL4"
OUTLET_DATUM_ID = INTERFACE_WATER_PUMP_OUTLET
PORT_DATUM_IDS = (INLET_DATUM_ID, OUTLET_DATUM_ID)

# Componentwise bounding envelope for the three verified body references above.
# This is deliberately larger than any single listed body in one or more axes and is
# not presented as the dimensions of an actual pump.
PACKAGE_CENTER_WORLD_MM = (-46.0, -10.0, 7.0)
PACKAGE_ENVELOPE_XYZ_MM = (30.0, 25.0, 8.2)
PACKAGE_LONG_AXIS_WORLD = "+X"
PACKAGE_CLEARANCE_RESERVATION_MM = 2.0

# Port coordinates remain provisional Cell 4 interface datums. The supplier pages do
# not establish one common connector geometry across all screening references.
PORT_LUMEN_DIAMETER_SEED_MM = 2.0
PORT_RESERVATION_DIAMETER_MM = 4.0
PORT_RESERVATION_PROJECTION_MM = 2.0
INLET_CENTER_WORLD_MM = (-31.0, -7.0, 7.0)
OUTLET_CENTER_WORLD_MM = (-31.0, -13.0, 7.0)
PORT_AXIS_WORLD = (1.0, 0.0, 0.0)

# Open-ended local cradle around the screening envelope. The base remains below the
# package by a provisional 0.5 mm gap, and the side rails preserve 0.4 mm lateral gap.
SUPPORT_BASE_XYZ_MM = (32.8, 27.0, 1.5)
SUPPORT_BASE_CENTER_WORLD_MM = (-46.0, -10.0, 1.65)
SUPPORT_RAIL_XYZ_MM = (1.0, 27.0, 8.2)
SUPPORT_RAIL_CENTER_X_MM = (-61.9, -30.1)
SUPPORT_RAIL_CENTER_Y_MM = -10.0
SUPPORT_RAIL_CENTER_Z_MM = 6.5
SUPPORT_PACKAGE_SIDE_GAP_SEED_MM = 0.4
SUPPORT_PACKAGE_BASE_GAP_SEED_MM = 0.5
SUPPORT_CAVITY_CLASSIFICATION = "WET_DRAINABLE"

# Two-millimetre local package reservation around the complete supplier-family body
# bounding envelope. This is a stationary assembly/service keepout, not a demonstrated
# extraction trajectory.
SERVICE_CLEARANCE_CENTER_WORLD_MM = PACKAGE_CENTER_WORLD_MM
SERVICE_CLEARANCE_XYZ_MM = (34.0, 29.0, 12.2)
SERVICE_CLEARANCE_BOUNDS_WORLD_MM = {
    "x": (-63.0, -29.0),
    "y": (-24.5, 4.5),
    "z": (0.9, 13.1),
}

REFERENCE_PACKAGE_STATUS = (
    "VERIFIED_SUPPLIER_FAMILY_BODY_BOUNDING_ENVELOPE_NOT_SELECTED_PRODUCTION_PACKAGE"
)
PORT_STATUS = "PROVISIONAL_DATUM_AND_INTERFACE_RESERVATION_NOT_CONNECTOR_OR_TUBING_SELECTION"
SUPPORT_STATUS = "PROVISIONAL_DRAINABLE_LOCAL_CRADLE_FRAME_JOIN_AND_RETENTION_UNRESOLVED"
SERVICE_STATUS = "LOCAL_DIGITAL_CLEARANCE_RESERVED_REPLACEMENT_TRAJECTORY_UNRESOLVED"
ROUTING_STATUS = "PUMP_LOCAL_PORT_DATUMS_REALIZED_SOURCE_AND_MANIFOLD_CENTERLINES_REMAIN_UNRESOLVED"
PHYSICAL_EVIDENCE_STATUS = (
    "DIGITAL_REFERENCE_PACKAGE_SUPPORT_PORT_AND_CLEARANCE_GEOMETRY_ONLY_NOT_SUPPLIER_"
    "SELECTION_FLOW_PRESSURE_METERING_PRIMING_LEAK_SERVICE_DURABILITY_OR_PHYSICAL_EVIDENCE"
)

_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
_GIT_SHA_RE = re.compile(r"[0-9a-f]{40}\Z")


class RealizedFreshWaterPumpError(ValueError):
    pass


def _box(dx: float, dy: float, dz: float, center: tuple[float, float, float]) -> cq.Workplane:
    return cq.Workplane("XY").box(dx, dy, dz, centered=(True, True, True)).translate(center)


def _x_cylinder(
    center_y_mm: float,
    center_z_mm: float,
    x0_mm: float,
    diameter_mm: float,
    length_mm: float,
) -> cq.Workplane:
    return (
        cq.Workplane("YZ")
        .workplane(offset=x0_mm)
        .center(center_y_mm, center_z_mm)
        .circle(diameter_mm / 2.0)
        .extrude(length_mm)
    )


def _one_valid_solid(shape: cq.Workplane, label: str) -> None:
    if shape.solids().size() != 1 or not shape.val().isValid() or shape.val().Volume() <= 0.0:
        raise RealizedFreshWaterPumpError(f"{label} must be one valid positive deterministic solid")


def _intersection_volume(a: cq.Workplane, b: cq.Workplane) -> float:
    return float(a.val().intersect(b.val()).Volume())


def _outside_volume(shape: cq.Workplane, envelope: cq.Workplane) -> float:
    return float(shape.val().cut(envelope.val()).Volume())


@dataclass(frozen=True, slots=True)
class CurrentFreshPumpSources:
    model: MasckOneModel
    authority: Authority
    water: WaterReservoirArchitecture
    cleanser: CleanserStorageArchitecture
    frame: StructuralFrameTopology
    architecture: FreshPumpPackagingArchitecture

    def validate(self) -> None:
        if type(self.model) is not MasckOneModel:
            raise RealizedFreshWaterPumpError("current model must use the exact MasckOneModel type")
        if type(self.authority) is not Authority:
            raise RealizedFreshWaterPumpError("current authority must use the exact Authority type")
        if type(self.water) is not WaterReservoirArchitecture:
            raise RealizedFreshWaterPumpError("current water source must use exact WaterReservoirArchitecture")
        if type(self.cleanser) is not CleanserStorageArchitecture:
            raise RealizedFreshWaterPumpError("current cleanser source must use exact CleanserStorageArchitecture")
        if type(self.frame) is not StructuralFrameTopology:
            raise RealizedFreshWaterPumpError("current frame must use exact StructuralFrameTopology")
        if type(self.architecture) is not FreshPumpPackagingArchitecture:
            raise RealizedFreshWaterPumpError("current pump source must use exact FreshPumpPackagingArchitecture")
        try:
            self.architecture.validate_current_sources(
                authority=self.authority,
                water=self.water,
                cleanser=self.cleanser,
                frame=self.frame,
            )
        except FreshPumpPackagingError as exc:
            raise RealizedFreshWaterPumpError("current fresh-pump source graph is stale or corrupted") from exc


def build_current_fresh_pump_sources() -> CurrentFreshPumpSources:
    """Reconstruct the current repository-rooted fresh-pump source graph."""
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
    sources = CurrentFreshPumpSources(
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
class RealizedPumpPortDatum:
    datum_id: str
    route_id: str
    fluid_identity: str
    role: str
    source_interface_id: str
    target_interface_id: str
    center_world_mm: tuple[float, float, float]
    axis_world: tuple[float, float, float]
    lumen_diameter_seed_mm: float
    reservation_diameter_mm: float
    reservation_projection_mm: float
    status: str = PORT_STATUS

    def __post_init__(self) -> None:
        if self.datum_id not in PORT_DATUM_IDS:
            raise RealizedFreshWaterPumpError(f"unknown water-pump port datum {self.datum_id!r}")
        if self.route_id not in (ROUTE_WATER_SOURCE, ROUTE_WATER_MANIFOLD):
            raise RealizedFreshWaterPumpError("water-pump port datum route ID is not controlled")
        if self.fluid_identity != FLUID_FRESH_WATER:
            raise RealizedFreshWaterPumpError("water-pump port datum must retain exact FRESH_WATER identity")
        if type(self.role) is not str or not self.role:
            raise RealizedFreshWaterPumpError("water-pump port datum role must be exact nonblank text")
        if type(self.source_interface_id) is not str or not self.source_interface_id:
            raise RealizedFreshWaterPumpError("water-pump port source interface must be exact nonblank text")
        if type(self.target_interface_id) is not str or not self.target_interface_id:
            raise RealizedFreshWaterPumpError("water-pump port target interface must be exact nonblank text")
        if type(self.center_world_mm) is not tuple or len(self.center_world_mm) != 3:
            raise RealizedFreshWaterPumpError("water-pump port center must be an exact 3-vector tuple")
        if type(self.axis_world) is not tuple or len(self.axis_world) != 3:
            raise RealizedFreshWaterPumpError("water-pump port axis must be an exact 3-vector tuple")
        if not all(type(v) in (int, float) and math.isfinite(float(v)) for v in self.center_world_mm):
            raise RealizedFreshWaterPumpError("water-pump port center must contain finite numeric scalars")
        if tuple(float(v) for v in self.axis_world) != PORT_AXIS_WORLD:
            raise RealizedFreshWaterPumpError("water-pump provisional port axes must retain +X world direction")
        if not math.isclose(self.lumen_diameter_seed_mm, PORT_LUMEN_DIAMETER_SEED_MM, abs_tol=1e-12):
            raise RealizedFreshWaterPumpError("water-pump port lumen seed changed")
        if not math.isclose(self.reservation_diameter_mm, PORT_RESERVATION_DIAMETER_MM, abs_tol=1e-12):
            raise RealizedFreshWaterPumpError("water-pump port reservation diameter changed")
        if not math.isclose(self.reservation_projection_mm, PORT_RESERVATION_PROJECTION_MM, abs_tol=1e-12):
            raise RealizedFreshWaterPumpError("water-pump port reservation projection changed")
        if self.status != PORT_STATUS:
            raise RealizedFreshWaterPumpError("water-pump port evidence boundary changed")

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
class RealizedFreshWaterPump:
    source_authority_revision: str
    source_fresh_pump_architecture_sha256: str
    source_water_architecture_sha256: str
    authored_against_git_sha: str
    source_architecture_blob_sha: str
    package_reference_solid: cq.Workplane
    support_cradle_solid: cq.Workplane
    inlet_port_reservation_solid: cq.Workplane
    outlet_port_reservation_solid: cq.Workplane
    service_clearance_solid: cq.Workplane
    port_datums: tuple[RealizedPumpPortDatum, RealizedPumpPortDatum]
    station_id: str = STATION_WATER
    reference_package_id: str = REFERENCE_PACKAGE_ID
    fluid_identity: str = FLUID_FRESH_WATER
    supplier_package_candidate_id: str | None = None
    supplier_package_evidence_sha256: str | None = None
    supplier_screening_record_sha256: str = SUPPLIER_SCREENING_RECORD_SHA256
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
            raise RealizedFreshWaterPumpError("realized water pump requires exact authority revision")
        for value, label in (
            (self.source_fresh_pump_architecture_sha256, "fresh-pump architecture source"),
            (self.source_water_architecture_sha256, "water architecture source"),
            (self.supplier_screening_record_sha256, "supplier screening record"),
        ):
            if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
                raise RealizedFreshWaterPumpError(f"{label} must be canonical lowercase SHA-256")
        for value, label in (
            (self.authored_against_git_sha, "authored-against Git provenance"),
            (self.source_architecture_blob_sha, "fresh-pump source blob"),
        ):
            if type(value) is not str or _GIT_SHA_RE.fullmatch(value) is None:
                raise RealizedFreshWaterPumpError(f"{label} must be exact lowercase 40-hex")
        if self.supplier_screening_record_sha256 != SUPPLIER_SCREENING_RECORD_SHA256:
            raise RealizedFreshWaterPumpError("supplier screening dimensional record changed")
        if self.station_id != STATION_WATER or self.fluid_identity != FLUID_FRESH_WATER:
            raise RealizedFreshWaterPumpError("realized package must remain the controlled FRESH_WATER pump station")
        if self.reference_package_id != REFERENCE_PACKAGE_ID:
            raise RealizedFreshWaterPumpError("realized water-pump reference package ID changed")
        if self.supplier_package_candidate_id is not None or self.supplier_package_evidence_sha256 is not None:
            raise RealizedFreshWaterPumpError("screening reference cannot imply a selected supplier package")
        if self.support_cavity_classification != SUPPORT_CAVITY_CLASSIFICATION:
            raise RealizedFreshWaterPumpError("water-pump support cavity must remain WET_DRAINABLE")
        if self.reference_package_status != REFERENCE_PACKAGE_STATUS:
            raise RealizedFreshWaterPumpError("water-pump reference package status changed")
        if self.support_status != SUPPORT_STATUS or self.service_status != SERVICE_STATUS or self.routing_status != ROUTING_STATUS:
            raise RealizedFreshWaterPumpError("water-pump support/service/routing evidence boundary changed")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise RealizedFreshWaterPumpError("digital water-pump reference cannot become physical validation evidence")
        if self.evidence_status != PHYSICAL_EVIDENCE_STATUS:
            raise RealizedFreshWaterPumpError("water-pump physical-evidence firewall changed")
        if type(self.port_datums) is not tuple or len(self.port_datums) != 2:
            raise RealizedFreshWaterPumpError("water-pump realization requires exact inlet/outlet datum tuple")
        if tuple(item.datum_id for item in self.port_datums) != PORT_DATUM_IDS:
            raise RealizedFreshWaterPumpError("water-pump port datum order changed")
        if tuple(item.center_world_mm for item in self.port_datums) != (INLET_CENTER_WORLD_MM, OUTLET_CENTER_WORLD_MM):
            raise RealizedFreshWaterPumpError("water-pump port datum placement changed")
        for label, shape in (
            ("reference package", self.package_reference_solid),
            ("support cradle", self.support_cradle_solid),
            ("inlet port reservation", self.inlet_port_reservation_solid),
            ("outlet port reservation", self.outlet_port_reservation_solid),
            ("service clearance", self.service_clearance_solid),
        ):
            _one_valid_solid(shape, f"water pump {label}")
        expected_volume = math.prod(PACKAGE_ENVELOPE_XYZ_MM)
        if not math.isclose(self.reference_envelope_volume_mm3, expected_volume, abs_tol=1e-8):
            raise RealizedFreshWaterPumpError("supplier-family water-pump screening envelope changed")
        if _intersection_volume(self.package_reference_solid, self.support_cradle_solid) > 1e-7:
            raise RealizedFreshWaterPumpError("water-pump reference envelope overlaps support material")
        for shape in (
            self.package_reference_solid,
            self.support_cradle_solid,
            self.inlet_port_reservation_solid,
            self.outlet_port_reservation_solid,
        ):
            if _outside_volume(shape, self.service_clearance_solid) > 1e-7:
                raise RealizedFreshWaterPumpError("water-pump local geometry escapes controlled service-clearance reservation")

    def validate_current_sources(self, sources: CurrentFreshPumpSources) -> FreshPumpPackagingArchitecture:
        if type(sources) is not CurrentFreshPumpSources:
            raise RealizedFreshWaterPumpError("sources must use exact CurrentFreshPumpSources type")
        sources.validate()
        architecture = sources.architecture
        if self.source_authority_revision != str(sources.authority.get("project", "authority_revision")):
            raise RealizedFreshWaterPumpError("realized water-pump package is stale for current authority")
        if self.source_fresh_pump_architecture_sha256 != architecture.architecture_sha256:
            raise RealizedFreshWaterPumpError("realized water-pump package is stale for current fresh-pump architecture")
        if self.source_water_architecture_sha256 != sources.water.architecture_sha256:
            raise RealizedFreshWaterPumpError("realized water-pump package is stale for current water architecture")
        station = next((item for item in architecture.stations if item.station_id == STATION_WATER), None)
        if station is None or station.fluid_identity != FLUID_FRESH_WATER:
            raise RealizedFreshWaterPumpError("current water-pump station identity changed")
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
            raise RealizedFreshWaterPumpError(
                "current source now carries supplier/package/routing selection; retire Cell 4 screening envelope"
            )
        return architecture

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "source_authority_revision": self.source_authority_revision,
            "source_fresh_pump_architecture_sha256": self.source_fresh_pump_architecture_sha256,
            "source_water_architecture_sha256": self.source_water_architecture_sha256,
            "authored_against_git_sha": self.authored_against_git_sha,
            "authored_against_git_sha_role": "HISTORICAL_PROVENANCE_ONLY_NOT_RELEASE_FRESHNESS_PROOF",
            "source_architecture_blob_sha": self.source_architecture_blob_sha,
            "world_frame_id": WORLD_FRAME_ID,
            "station_id": self.station_id,
            "fluid_identity": self.fluid_identity,
            "reference_package_id": self.reference_package_id,
            "supplier_package_candidate_id": self.supplier_package_candidate_id,
            "supplier_package_evidence_sha256": self.supplier_package_evidence_sha256,
            "supplier_screening": {
                "record_sha256": self.supplier_screening_record_sha256,
                "record_hash_role": SUPPLIER_SCREENING_RECORD_HASH_ROLE,
                "evidence_status": SUPPLIER_SCREENING_EVIDENCE_STATUS,
                "references": [dict(item) for item in SUPPLIER_SCREENING_REFERENCES],
                "selection_status": "NO_SUPPLIER_PACKAGE_SELECTED",
            },
            "reference_package": {
                "center_world_mm": list(PACKAGE_CENTER_WORLD_MM),
                "envelope_xyz_mm": list(PACKAGE_ENVELOPE_XYZ_MM),
                "long_axis_world": PACKAGE_LONG_AXIS_WORLD,
                "geometric_envelope_volume_mm3": self.reference_envelope_volume_mm3,
                "status": self.reference_package_status,
                "evidence_role": "FIT_AND_COLLISION_REFERENCE_ONLY_NOT_SELECTED_PUMP_DIMENSIONS_OR_MASS",
                "construction_role": (
                    "COMPONENTWISE_BOUND_OF_VERIFIED_REFERENCE_BODIES_NOT_DIMENSIONS_OF_ONE_ACTUAL_PUMP"
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
                "precondition": "MASK_UNPOWERED_LOCAL_SERVICE_ACCESS_SHELL_OR_SERVICE_OPENING_NOT_YET_REALIZED",
                "status": self.service_status,
            },
            "routing": {
                "source_route_id": ROUTE_WATER_SOURCE,
                "source_interface_id": PORT_PICKUP,
                "pump_station_id": STATION_WATER,
                "pump_outlet_interface_id": INTERFACE_WATER_PUMP_OUTLET,
                "downstream_route_id": ROUTE_WATER_MANIFOLD,
                "downstream_interface_id": "MANIFOLD-INLET-WATER-I23",
                "source_to_pump_centerline": None,
                "pump_to_manifold_centerline": None,
                "tubing_inner_diameter_mm": None,
                "minimum_bend_radius_mm": None,
                "connector_standard": None,
                "status": self.routing_status,
            },
            "performance_claims": {
                "flow_curve": None,
                "pressure_capability": None,
                "metering_accuracy": None,
                "priming_behavior": None,
                "orientation_independence": None,
                "acoustic_performance": None,
                "runtime": None,
            },
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            payload["manifest_sha256"] = self.manifest_sha256
        return payload


def build_realized_fresh_water_pump(sources: CurrentFreshPumpSources) -> RealizedFreshWaterPump:
    if type(sources) is not CurrentFreshPumpSources:
        raise RealizedFreshWaterPumpError("sources must use exact CurrentFreshPumpSources type")
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

    port_face_x = PACKAGE_CENTER_WORLD_MM[0] + PACKAGE_ENVELOPE_XYZ_MM[0] / 2.0
    inlet_reservation = _x_cylinder(
        INLET_CENTER_WORLD_MM[1],
        INLET_CENTER_WORLD_MM[2],
        port_face_x,
        PORT_RESERVATION_DIAMETER_MM,
        PORT_RESERVATION_PROJECTION_MM,
    )
    outlet_reservation = _x_cylinder(
        OUTLET_CENTER_WORLD_MM[1],
        OUTLET_CENTER_WORLD_MM[2],
        port_face_x,
        PORT_RESERVATION_DIAMETER_MM,
        PORT_RESERVATION_PROJECTION_MM,
    )
    service_clearance = _box(*SERVICE_CLEARANCE_XYZ_MM, SERVICE_CLEARANCE_CENTER_WORLD_MM)

    ports = (
        RealizedPumpPortDatum(
            datum_id=INLET_DATUM_ID,
            route_id=ROUTE_WATER_SOURCE,
            fluid_identity=FLUID_FRESH_WATER,
            role="SOURCE_TO_PUMP_PROVISIONAL_INTERFACE_DATUM",
            source_interface_id=PORT_PICKUP,
            target_interface_id=STATION_WATER,
            center_world_mm=INLET_CENTER_WORLD_MM,
            axis_world=PORT_AXIS_WORLD,
            lumen_diameter_seed_mm=PORT_LUMEN_DIAMETER_SEED_MM,
            reservation_diameter_mm=PORT_RESERVATION_DIAMETER_MM,
            reservation_projection_mm=PORT_RESERVATION_PROJECTION_MM,
        ),
        RealizedPumpPortDatum(
            datum_id=OUTLET_DATUM_ID,
            route_id=ROUTE_WATER_MANIFOLD,
            fluid_identity=FLUID_FRESH_WATER,
            role="PUMP_TO_MANIFOLD_PROVISIONAL_INTERFACE_DATUM",
            source_interface_id=INTERFACE_WATER_PUMP_OUTLET,
            target_interface_id="MANIFOLD-INLET-WATER-I23",
            center_world_mm=OUTLET_CENTER_WORLD_MM,
            axis_world=PORT_AXIS_WORLD,
            lumen_diameter_seed_mm=PORT_LUMEN_DIAMETER_SEED_MM,
            reservation_diameter_mm=PORT_RESERVATION_DIAMETER_MM,
            reservation_projection_mm=PORT_RESERVATION_PROJECTION_MM,
        ),
    )

    realized = RealizedFreshWaterPump(
        source_authority_revision=str(sources.authority.get("project", "authority_revision")),
        source_fresh_pump_architecture_sha256=sources.architecture.architecture_sha256,
        source_water_architecture_sha256=sources.water.architecture_sha256,
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


def build_current_realized_fresh_water_pump() -> RealizedFreshWaterPump:
    """Trusted path that always reconstructs the current repository source graph."""
    return build_realized_fresh_water_pump(build_current_fresh_pump_sources())
