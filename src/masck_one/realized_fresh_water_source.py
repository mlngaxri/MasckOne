from __future__ import annotations

"""Current-main source geometry for the Masck One fresh-water reservoir.

This module reconstructs the useful geometric intent from abandoned Cell 4 water
reservoir candidates onto released source contracts. All dimensions introduced here
remain provisional digital CAD baselines. Nothing in this module establishes sealing,
leakage, venting, priming, drawdown, orientation robustness, hygiene performance,
serviceability, durability, supplier selection, or physical safety.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math

import cadquery as cq

from .authority import Authority
from .spatial import Point3, Vector3
from .water_reservoir import (
    ORIENTATION_CASE_IDS,
    PORT_FILL,
    PORT_PICKUP,
    PORT_VENT,
    WATER_RESERVOIR_ID,
    WaterReservoirArchitecture,
    WaterReservoirError,
    build_water_reservoir_architecture,
)

WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
FLUID_IDENTITY = "FRESH_WATER"
CAVITY_CLASSIFICATION = "WET_REMOVABLE"

# Exact historical donor provenance. These heads are source material only, not
# authority or release dependencies.
DONOR_PR75_HEAD = "08b5769753858cb457f0117bf25498875072d812"
DONOR_PR78_HEAD = "d309573ece2ccc2bd3302f0ccda779f2f4324eb5"
DONOR_REALIZED_WATER_BLOB = "96c311beb58ff5ddb1af4fbd28a46ffe9adeda37"
DONOR_STATUS = "HISTORICAL_UNMERGED_SOURCE_MATERIAL_ONLY"

# Current-main source identity at this bounded reconstruction. Runtime authority and
# architecture checks below remain the trusted semantic binding.
AUTHORED_MAIN_SHA = "afe29ff78419b6625dca5594974b6351f6f80e1b"
AUTHORITY_BLOB_SHA = "2608dda483b995539de422290371c219668a1527"
WATER_ARCHITECTURE_BLOB_SHA = "6c14a37d07855550f0bd502e8308ed46682bc19c"

INTERNAL_WIDTH_X_MM = 26.0
INTERNAL_HEIGHT_Y_MM = 25.0
INTERNAL_DEPTH_Z_MM = 10.0
WALL_THICKNESS_MM = 1.0
OUTER_WIDTH_X_MM = INTERNAL_WIDTH_X_MM + 2.0 * WALL_THICKNESS_MM
OUTER_HEIGHT_Y_MM = INTERNAL_HEIGHT_Y_MM + 2.0 * WALL_THICKNESS_MM
OUTER_DEPTH_Z_MM = INTERNAL_DEPTH_Z_MM + 2.0 * WALL_THICKNESS_MM
RESERVOIR_CENTER = Point3(0.0, 76.0, 7.0)

OUTER_Z_MIN_MM = RESERVOIR_CENTER.z - OUTER_DEPTH_Z_MM / 2.0
OUTER_Z_MAX_MM = RESERVOIR_CENTER.z + OUTER_DEPTH_Z_MM / 2.0
INTERNAL_Z_MIN_MM = OUTER_Z_MIN_MM + WALL_THICKNESS_MM
INTERNAL_Z_MAX_MM = OUTER_Z_MAX_MM - WALL_THICKNESS_MM
LID_INTERFACE_Z_MM = INTERNAL_Z_MAX_MM

PICKUP_CENTER_ABOVE_INTERNAL_FLOOR_MM = 1.0
FILL_BORE_DIAMETER_MM = 6.0
FILL_CLOSURE_RESERVATION_DIAMETER_MM = 9.0
FILL_CLOSURE_RESERVATION_HEIGHT_MM = 3.0
VENT_LUMEN_DIAMETER_MM = 1.2
VENT_EXTERNAL_BARRIER_RESERVATION_DIAMETER_MM = 4.0
VENT_EXTERNAL_BARRIER_RESERVATION_HEIGHT_MM = 2.0
PICKUP_PASSAGE_DIAMETER_MM = 2.0
PICKUP_CONNECTOR_RESERVATION_DIAMETER_MM = 5.0
PICKUP_CONNECTOR_RESERVATION_LENGTH_MM = 4.0
SERVICE_WITHDRAWAL_TRAVEL_MM = 14.0
PACKAGE_CLEARANCE_RESERVATION_MM = 2.0
PORT_CUT_OVERTRAVEL_MM = 0.2

GEOMETRY_STATUS = "CELL9_PROVISIONAL_DIGITAL_FRESH_WATER_SOURCE_GEOMETRY"
SERVICE_STATUS = "STRAIGHT_POSTERIOR_RESERVATION_ONLY_NONTELEPORTING_PRODUCT_SERVICE_UNRESOLVED"
EVIDENCE_STATUS = (
    "DIGITAL_FRESH_WATER_SOURCE_GEOMETRY_ONLY_NOT_SEAL_LEAK_VENT_PRIME_ORIENTATION_"
    "HYGIENE_SERVICE_DURABILITY_SUPPLIER_OR_PHYSICAL_PERFORMANCE_EVIDENCE"
)


def _sha40(value: object, *, label: str) -> str:
    if type(value) is not str or len(value) != 40 or any(c not in "0123456789abcdef" for c in value):
        raise WaterReservoirError(f"{label} must be exact lowercase 40-hex")
    return value


def _sha256(value: object, *, label: str) -> str:
    if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise WaterReservoirError(f"{label} must be canonical lowercase SHA-256")
    return value


def _box(width_x: float, height_y: float, depth_z: float, center: Point3) -> cq.Workplane:
    return (
        cq.Workplane("XY")
        .box(width_x, height_y, depth_z, centered=(True, True, True))
        .translate(center.as_tuple())
    )


def _cylinder_between(start: Point3, end: Point3, diameter_mm: float) -> cq.Workplane:
    if type(diameter_mm) not in (int, float) or isinstance(diameter_mm, bool):
        raise WaterReservoirError("cylinder diameter must be an exact numeric scalar")
    diameter = float(diameter_mm)
    if not math.isfinite(diameter) or diameter <= 0.0:
        raise WaterReservoirError("cylinder diameter must be finite and positive")
    vector = start.vector_to(end)
    length = vector.norm()
    if length <= 1e-12:
        raise WaterReservoirError("cylinder endpoints must be distinct")
    direction = vector.normalized()
    solid = cq.Solid.makeCylinder(
        diameter / 2.0,
        length,
        cq.Vector(*start.as_tuple()),
        cq.Vector(*direction.as_tuple()),
    )
    return cq.Workplane("XY").newObject([solid])


@dataclass(frozen=True, slots=True)
class FreshWaterDatum:
    datum_id: str
    point: Point3
    axis: Vector3
    role: str
    fluid_identity: str = FLUID_IDENTITY

    def __post_init__(self) -> None:
        if self.datum_id not in (PORT_FILL, PORT_VENT, PORT_PICKUP):
            raise WaterReservoirError("fresh-water datum ID is not controlled")
        if type(self.role) is not str or not self.role or self.role != self.role.strip():
            raise WaterReservoirError("fresh-water datum role must be exact nonblank text")
        if self.fluid_identity != FLUID_IDENTITY:
            raise WaterReservoirError("fresh-water source datums cannot change fluid identity")
        if not math.isclose(self.axis.norm(), 1.0, rel_tol=0.0, abs_tol=1e-12):
            raise WaterReservoirError("fresh-water datum axis must be unit length")

    def manifest(self) -> dict[str, object]:
        return {
            "datum_id": self.datum_id,
            "point_xyz_mm": list(self.point.as_tuple()),
            "axis_xyz": list(self.axis.as_tuple()),
            "role": self.role,
            "fluid_identity": self.fluid_identity,
        }


@dataclass(frozen=True, slots=True)
class RealizedFreshWaterSource:
    source_authority_revision: str
    source_architecture_sha256: str
    body_solid: cq.Workplane
    lid_solid: cq.Workplane
    cavity_solid: cq.Workplane
    dead_volume_reference_solid: cq.Workplane
    fill_bore_reference_solid: cq.Workplane
    vent_lumen_reference_solid: cq.Workplane
    pickup_passage_reference_solid: cq.Workplane
    fill_closure_reservation_solid: cq.Workplane
    vent_barrier_reservation_solid: cq.Workplane
    pickup_connector_reservation_solid: cq.Workplane
    service_sweep_reservation_solid: cq.Workplane
    datums: tuple[FreshWaterDatum, ...]
    orientation_case_ids: tuple[str, ...] = ORIENTATION_CASE_IDS
    reservoir_id: str = WATER_RESERVOIR_ID
    fluid_identity: str = FLUID_IDENTITY
    cavity_classification: str = CAVITY_CLASSIFICATION
    geometry_status: str = GEOMETRY_STATUS
    service_status: str = SERVICE_STATUS
    physical_validation_eligible: bool = False
    evidence_status: str = EVIDENCE_STATUS

    def __post_init__(self) -> None:
        self.validate_invariants()

    @property
    def gross_geometric_volume_mL(self) -> float:
        return float(self.cavity_solid.val().Volume()) / 1000.0

    @property
    def neutral_geometric_dead_volume_mL(self) -> float:
        return float(self.dead_volume_reference_solid.val().Volume()) / 1000.0

    @property
    def neutral_geometric_usable_volume_mL(self) -> float:
        return self.gross_geometric_volume_mL - self.neutral_geometric_dead_volume_mL

    @property
    def physical_material_solids(self) -> tuple[cq.Workplane, cq.Workplane]:
        return self.body_solid, self.lid_solid

    @property
    def reference_only_solids(self) -> tuple[cq.Workplane, ...]:
        return (
            self.cavity_solid,
            self.dead_volume_reference_solid,
            self.fill_bore_reference_solid,
            self.vent_lumen_reference_solid,
            self.pickup_passage_reference_solid,
            self.fill_closure_reservation_solid,
            self.vent_barrier_reservation_solid,
            self.pickup_connector_reservation_solid,
            self.service_sweep_reservation_solid,
        )

    def validate_invariants(self) -> None:
        if self.reservoir_id != WATER_RESERVOIR_ID:
            raise WaterReservoirError("realized source must retain water reservoir ID")
        if self.fluid_identity != FLUID_IDENTITY:
            raise WaterReservoirError("realized source cannot change FRESH_WATER identity")
        if self.cavity_classification != CAVITY_CLASSIFICATION:
            raise WaterReservoirError("realized source cavity must remain WET_REMOVABLE")
        if self.orientation_case_ids != ORIENTATION_CASE_IDS:
            raise WaterReservoirError("realized source must retain the complete controlled orientation case set")
        _sha256(self.source_architecture_sha256, label="source water architecture")
        if type(self.source_authority_revision) is not str or not self.source_authority_revision:
            raise WaterReservoirError("source authority revision must be exact nonblank text")
        if tuple(datum.datum_id for datum in self.datums) != (PORT_FILL, PORT_VENT, PORT_PICKUP):
            raise WaterReservoirError("realized source must expose fill, vent and pickup datums in controlled order")
        if self.geometry_status != GEOMETRY_STATUS or self.service_status != SERVICE_STATUS:
            raise WaterReservoirError("realized source cannot promote digital geometry/service evidence")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise WaterReservoirError("realized source cannot become physical validation evidence")
        if self.evidence_status != EVIDENCE_STATUS:
            raise WaterReservoirError("realized source evidence firewall must remain exact")

        for label, solid in (
            ("body", self.body_solid),
            ("lid", self.lid_solid),
            ("cavity", self.cavity_solid),
            ("dead-volume reference", self.dead_volume_reference_solid),
            ("fill bore", self.fill_bore_reference_solid),
            ("vent lumen", self.vent_lumen_reference_solid),
            ("pickup passage", self.pickup_passage_reference_solid),
            ("fill closure reservation", self.fill_closure_reservation_solid),
            ("vent barrier reservation", self.vent_barrier_reservation_solid),
            ("pickup connector reservation", self.pickup_connector_reservation_solid),
            ("service sweep reservation", self.service_sweep_reservation_solid),
        ):
            if solid.solids().size() != 1 or not solid.val().isValid() or float(solid.val().Volume()) <= 0.0:
                raise WaterReservoirError(f"{label} must be one valid positive deterministic solid")

        if not math.isclose(self.gross_geometric_volume_mL, 6.5, rel_tol=0.0, abs_tol=1e-9):
            raise WaterReservoirError("fresh-water cavity must preserve the 6.5 mL gross geometric baseline")
        if not math.isclose(self.neutral_geometric_dead_volume_mL, 0.65, rel_tol=0.0, abs_tol=1e-9):
            raise WaterReservoirError("fresh-water neutral dead-volume reference must remain 0.65 mL")
        if self.neutral_geometric_usable_volume_mL < 5.5 - 1e-9:
            raise WaterReservoirError("fresh-water neutral geometric usable volume must meet authority minimum")
        if self.body_solid.val().intersect(self.lid_solid.val()).Volume() > 1e-7:
            raise WaterReservoirError("reservoir body and lid cannot overlap as attachment")

    def validate_current_sources(self, authority: Authority) -> WaterReservoirArchitecture:
        if type(authority) is not Authority:
            raise WaterReservoirError("authority must be an exact Authority contract")
        current = build_water_reservoir_architecture(authority)
        current.validate_current_authority(authority)
        if self.source_authority_revision != str(authority.get("project", "authority_revision")):
            raise WaterReservoirError("fresh-water source geometry is stale for current authority")
        if self.source_architecture_sha256 != current.architecture_sha256:
            raise WaterReservoirError("fresh-water source geometry is stale for current water architecture")
        if current.gross_target_mL != 6.5 or current.minimum_usable_mL != 5.5:
            raise WaterReservoirError("fresh-water source geometry requires explicit rework after authority volume movement")
        return current

    def manifest(self) -> dict[str, object]:
        self.validate_invariants()
        return {
            "reservoir_id": self.reservoir_id,
            "world_frame_id": WORLD_FRAME_ID,
            "fluid_identity": self.fluid_identity,
            "cavity_classification": self.cavity_classification,
            "source_authority_revision": self.source_authority_revision,
            "source_architecture_sha256": self.source_architecture_sha256,
            "authored_main_sha": AUTHORED_MAIN_SHA,
            "source_git_blobs": {
                "authority": AUTHORITY_BLOB_SHA,
                "water_reservoir_architecture": WATER_ARCHITECTURE_BLOB_SHA,
            },
            "historical_donor_provenance": {
                "status": DONOR_STATUS,
                "pr75_head": DONOR_PR75_HEAD,
                "pr78_head": DONOR_PR78_HEAD,
                "realized_water_blob": DONOR_REALIZED_WATER_BLOB,
            },
            "internal_dimensions_xyz_mm": [INTERNAL_WIDTH_X_MM, INTERNAL_HEIGHT_Y_MM, INTERNAL_DEPTH_Z_MM],
            "outer_dimensions_xyz_mm": [OUTER_WIDTH_X_MM, OUTER_HEIGHT_Y_MM, OUTER_DEPTH_Z_MM],
            "outer_center_xyz_mm": list(RESERVOIR_CENTER.as_tuple()),
            "wall_thickness_mm": WALL_THICKNESS_MM,
            "gross_geometric_volume_mL": self.gross_geometric_volume_mL,
            "neutral_geometric_dead_volume_mL": self.neutral_geometric_dead_volume_mL,
            "neutral_geometric_usable_volume_mL": self.neutral_geometric_usable_volume_mL,
            "port_geometry": {
                "fill_bore_diameter_mm": FILL_BORE_DIAMETER_MM,
                "fill_closure_reservation_diameter_mm": FILL_CLOSURE_RESERVATION_DIAMETER_MM,
                "fill_closure_reservation_height_mm": FILL_CLOSURE_RESERVATION_HEIGHT_MM,
                "vent_lumen_diameter_mm": VENT_LUMEN_DIAMETER_MM,
                "vent_barrier_reservation_diameter_mm": VENT_EXTERNAL_BARRIER_RESERVATION_DIAMETER_MM,
                "vent_barrier_reservation_height_mm": VENT_EXTERNAL_BARRIER_RESERVATION_HEIGHT_MM,
                "pickup_passage_diameter_mm": PICKUP_PASSAGE_DIAMETER_MM,
                "pickup_connector_reservation_diameter_mm": PICKUP_CONNECTOR_RESERVATION_DIAMETER_MM,
                "pickup_connector_reservation_length_mm": PICKUP_CONNECTOR_RESERVATION_LENGTH_MM,
            },
            "datums": [datum.manifest() for datum in self.datums],
            "orientation_case_ids": list(self.orientation_case_ids),
            "service_withdrawal_travel_mm": SERVICE_WITHDRAWAL_TRAVEL_MM,
            "package_clearance_reservation_mm": PACKAGE_CLEARANCE_RESERVATION_MM,
            "material_semantics": {
                "physical_material": ["reservoir_body", "reservoir_lid"],
                "reference_only": [
                    "internal_cavity",
                    "neutral_dead_volume",
                    "fill_bore",
                    "vent_lumen",
                    "pickup_passage",
                    "fill_closure_reservation",
                    "vent_barrier_reservation",
                    "pickup_connector_reservation",
                    "service_sweep_reservation",
                ],
            },
            "geometry_status": self.geometry_status,
            "service_status": self.service_status,
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": self.evidence_status,
        }

    @property
    def manifest_sha256(self) -> str:
        raw = json.dumps(self.manifest(), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return sha256(raw).hexdigest()


def build_realized_fresh_water_source(authority: Authority) -> RealizedFreshWaterSource:
    architecture = build_water_reservoir_architecture(authority)
    architecture.validate_current_authority(authority)

    outer = _box(OUTER_WIDTH_X_MM, OUTER_HEIGHT_Y_MM, OUTER_DEPTH_Z_MM, RESERVOIR_CENTER)
    cavity = _box(INTERNAL_WIDTH_X_MM, INTERNAL_HEIGHT_Y_MM, INTERNAL_DEPTH_Z_MM, RESERVOIR_CENTER)

    body_selector = _box(
        OUTER_WIDTH_X_MM + 2.0,
        OUTER_HEIGHT_Y_MM + 2.0,
        LID_INTERFACE_Z_MM - OUTER_Z_MIN_MM,
        Point3(RESERVOIR_CENTER.x, RESERVOIR_CENTER.y, (OUTER_Z_MIN_MM + LID_INTERFACE_Z_MM) / 2.0),
    )
    lid_selector = _box(
        OUTER_WIDTH_X_MM + 2.0,
        OUTER_HEIGHT_Y_MM + 2.0,
        OUTER_Z_MAX_MM - LID_INTERFACE_Z_MM,
        Point3(RESERVOIR_CENTER.x, RESERVOIR_CENTER.y, (LID_INTERFACE_Z_MM + OUTER_Z_MAX_MM) / 2.0),
    )
    body_unported = outer.intersect(body_selector).cut(cavity)
    lid_unported = outer.intersect(lid_selector)

    fill_datum = FreshWaterDatum(
        PORT_FILL,
        Point3(-6.0, RESERVOIR_CENTER.y, OUTER_Z_MAX_MM),
        Vector3(0.0, 0.0, 1.0),
        "fresh-water fill interface on removable lid; closure and seal hardware unresolved",
    )
    vent_datum = FreshWaterDatum(
        PORT_VENT,
        Point3(6.0, RESERVOIR_CENTER.y, OUTER_Z_MAX_MM),
        Vector3(0.0, 0.0, 1.0),
        "fresh-water vent interface on removable lid; liquid barrier hardware unresolved",
    )
    pickup_z = INTERNAL_Z_MIN_MM + PICKUP_CENTER_ABOVE_INTERNAL_FLOOR_MM
    pickup_datum = FreshWaterDatum(
        PORT_PICKUP,
        Point3(0.0, RESERVOIR_CENTER.y - OUTER_HEIGHT_Y_MM / 2.0, pickup_z),
        Vector3(0.0, -1.0, 0.0),
        "fresh-water pickup handoff; downstream connector, tubing and pump routing unresolved",
    )

    fill_bore = _cylinder_between(
        Point3(fill_datum.point.x, fill_datum.point.y, INTERNAL_Z_MAX_MM - PORT_CUT_OVERTRAVEL_MM),
        Point3(fill_datum.point.x, fill_datum.point.y, OUTER_Z_MAX_MM + PORT_CUT_OVERTRAVEL_MM),
        FILL_BORE_DIAMETER_MM,
    )
    fill_closure_reservation = _cylinder_between(
        fill_datum.point,
        fill_datum.point.translated(Vector3(0.0, 0.0, FILL_CLOSURE_RESERVATION_HEIGHT_MM)),
        FILL_CLOSURE_RESERVATION_DIAMETER_MM,
    )

    vent_internal_terminus = Point3(6.0, 87.5, 11.5)
    vent_lumen = _cylinder_between(vent_internal_terminus, vent_datum.point, VENT_LUMEN_DIAMETER_MM)
    vent_barrier_reservation = _cylinder_between(
        vent_datum.point,
        vent_datum.point.translated(Vector3(0.0, 0.0, VENT_EXTERNAL_BARRIER_RESERVATION_HEIGHT_MM)),
        VENT_EXTERNAL_BARRIER_RESERVATION_DIAMETER_MM,
    )

    pickup_internal = Point3(
        pickup_datum.point.x,
        RESERVOIR_CENTER.y - INTERNAL_HEIGHT_Y_MM / 2.0 + PORT_CUT_OVERTRAVEL_MM,
        pickup_datum.point.z,
    )
    pickup_external = Point3(
        pickup_datum.point.x,
        pickup_datum.point.y - PORT_CUT_OVERTRAVEL_MM,
        pickup_datum.point.z,
    )
    pickup_passage = _cylinder_between(pickup_external, pickup_internal, PICKUP_PASSAGE_DIAMETER_MM)
    pickup_connector_reservation = _cylinder_between(
        pickup_datum.point,
        pickup_datum.point.translated(Vector3(0.0, -PICKUP_CONNECTOR_RESERVATION_LENGTH_MM, 0.0)),
        PICKUP_CONNECTOR_RESERVATION_DIAMETER_MM,
    )

    body = body_unported.cut(pickup_passage)
    lid = lid_unported.cut(fill_bore).cut(vent_lumen)

    dead_volume = _box(
        INTERNAL_WIDTH_X_MM,
        INTERNAL_HEIGHT_Y_MM,
        PICKUP_CENTER_ABOVE_INTERNAL_FLOOR_MM,
        Point3(
            RESERVOIR_CENTER.x,
            RESERVOIR_CENTER.y,
            INTERNAL_Z_MIN_MM + PICKUP_CENTER_ABOVE_INTERNAL_FLOOR_MM / 2.0,
        ),
    )

    service_sweep = _box(
        OUTER_WIDTH_X_MM,
        OUTER_HEIGHT_Y_MM,
        OUTER_DEPTH_Z_MM + SERVICE_WITHDRAWAL_TRAVEL_MM,
        Point3(RESERVOIR_CENTER.x, RESERVOIR_CENTER.y, RESERVOIR_CENTER.z - SERVICE_WITHDRAWAL_TRAVEL_MM / 2.0),
    )

    result = RealizedFreshWaterSource(
        source_authority_revision=str(authority.get("project", "authority_revision")),
        source_architecture_sha256=architecture.architecture_sha256,
        body_solid=body,
        lid_solid=lid,
        cavity_solid=cavity,
        dead_volume_reference_solid=dead_volume,
        fill_bore_reference_solid=fill_bore,
        vent_lumen_reference_solid=vent_lumen,
        pickup_passage_reference_solid=pickup_passage,
        fill_closure_reservation_solid=fill_closure_reservation,
        vent_barrier_reservation_solid=vent_barrier_reservation,
        pickup_connector_reservation_solid=pickup_connector_reservation,
        service_sweep_reservation_solid=service_sweep,
        datums=(fill_datum, vent_datum, pickup_datum),
    )
    result.validate_current_sources(authority)
    _sha40(AUTHORED_MAIN_SHA, label="authored main SHA")
    _sha40(AUTHORITY_BLOB_SHA, label="authority Git blob")
    _sha40(WATER_ARCHITECTURE_BLOB_SHA, label="water architecture Git blob")
    _sha40(DONOR_PR75_HEAD, label="donor PR75 head")
    _sha40(DONOR_PR78_HEAD, label="donor PR78 head")
    _sha40(DONOR_REALIZED_WATER_BLOB, label="donor realized-water Git blob")
    return result
