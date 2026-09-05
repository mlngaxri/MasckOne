from __future__ import annotations

"""Source-bound realized geometry for the removable fresh-water reservoir.

The geometry in this module is a deterministic Cell 4 engineering baseline. The
1.0 mm wall, pickup height, datum placement and service sweep are provisional CAD
choices, not supplier dimensions or physical leakage, orientation, hygiene, drying,
serviceability or durability evidence.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math

import cadquery as cq

from .authority import Authority
from .spatial import Point3, Vector3
from .water_reservoir import (
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
GEOMETRY_STATUS = "CELL4_PROVISIONAL_DIGITAL_RESERVOIR_GEOMETRY_NOT_PHYSICAL_EVIDENCE"
CROSS_SECTION_PROVENANCE = "CELL4_PROVISIONAL_1P0MM_WALL_NOT_MATERIAL_OR_PROCESS_SELECTED"
SERVICE_STATUS = "STRAIGHT_POSTERIOR_REMOVAL_SWEEP_DIGITAL_RESERVATION_ONLY"
VOLUME_EVIDENCE_KIND = "DIGITAL_GEOMETRIC_VOLUME_ONLY"
PHYSICAL_EVIDENCE_STATUS = (
    "DIGITAL_FRESH_WATER_RESERVOIR_GEOMETRY_ONLY_NOT_LEAKAGE_ORIENTATION_HYGIENE_"
    "DRYING_SERVICEABILITY_DURABILITY_OR_PHYSICAL_SAFETY_EVIDENCE"
)

# Numerical-kernel comparison allowance only. This is not a liquid-metering,
# manufacturing, tolerance-stack or physical-volume requirement.
CAD_VOLUME_TOLERANCE_ML = 1e-9

# The prior model carried a 26 x 25 x 10 mm solid and labelled its 6500 mm3
# material volume as water capacity. This realization keeps that exact 6.5 mL
# quantity as the *internal cavity* and adds explicit walls around it.
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
BODY_Z_MAX_MM = INTERNAL_Z_MAX_MM
LID_Z_MIN_MM = BODY_Z_MAX_MM
LID_Z_MAX_MM = OUTER_Z_MAX_MM

PICKUP_CENTER_ABOVE_INTERNAL_FLOOR_MM = 1.0
SERVICE_WITHDRAWAL_TRAVEL_MM = 14.0
PACKAGE_CLEARANCE_RESERVATION_MM = 2.0
CAVITY_CUT_OVERTRAVEL_MM = 0.2

DATUM_MOUNT_LEFT = "WATER-RESERVOIR-MOUNT-WEARER-LEFT"
DATUM_MOUNT_RIGHT = "WATER-RESERVOIR-MOUNT-WEARER-RIGHT"
DATUM_MOUNT_REAR_STOP = "WATER-RESERVOIR-MOUNT-POSTERIOR-STOP"
DATUM_SERVICE_WITHDRAWAL = "WATER-RESERVOIR-SERVICE-WITHDRAWAL"
DATUM_IDS = (
    DATUM_MOUNT_LEFT,
    DATUM_MOUNT_RIGHT,
    DATUM_MOUNT_REAR_STOP,
    DATUM_SERVICE_WITHDRAWAL,
    PORT_FILL,
    PORT_VENT,
    PORT_PICKUP,
)


def _canonical_sha256(value: object, *, label: str) -> str:
    if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise WaterReservoirError(f"{label} must be canonical lowercase SHA-256")
    return value


def _positive(value: object, *, label: str) -> float:
    if type(value) not in (int, float) or isinstance(value, bool):
        raise WaterReservoirError(f"{label} must be an exact numeric scalar")
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise WaterReservoirError(f"{label} must be finite and positive")
    return result


def _box(width_x: float, height_y: float, depth_z: float, center: Point3) -> cq.Workplane:
    return (
        cq.Workplane("XY")
        .box(width_x, height_y, depth_z, centered=(True, True, True))
        .translate(center.as_tuple())
    )


@dataclass(frozen=True, slots=True)
class ReservoirDatum:
    datum_id: str
    point: Point3
    axis: Vector3
    role: str
    fluid_identity: str | None
    geometry_status: str = GEOMETRY_STATUS

    def __post_init__(self) -> None:
        if self.datum_id not in DATUM_IDS:
            raise WaterReservoirError(f"Unknown realized reservoir datum {self.datum_id!r}")
        if type(self.role) is not str or not self.role or self.role != self.role.strip():
            raise WaterReservoirError("Reservoir datum role must be exact nonblank text")
        if not math.isclose(self.axis.norm(), 1.0, rel_tol=0.0, abs_tol=1e-12):
            raise WaterReservoirError("Reservoir datum axis must be a unit vector")
        if self.fluid_identity not in (None, FLUID_IDENTITY):
            raise WaterReservoirError("Reservoir fluid datums cannot change fresh-water identity")
        if self.geometry_status != GEOMETRY_STATUS:
            raise WaterReservoirError("Reservoir datum cannot promote physical geometry evidence")

    def manifest(self) -> dict[str, object]:
        return {
            "datum_id": self.datum_id,
            "point_xyz_mm": list(self.point.as_tuple()),
            "axis_xyz": list(self.axis.as_tuple()),
            "role": self.role,
            "fluid_identity": self.fluid_identity,
            "geometry_status": self.geometry_status,
        }


@dataclass(frozen=True, slots=True)
class RealizedWaterReservoir:
    reservoir_id: str
    source_authority_revision: str
    source_architecture_sha256: str
    gross_target_mL: float
    minimum_usable_mL: float
    body_solid: cq.Workplane
    lid_solid: cq.Workplane
    cavity_solid: cq.Workplane
    dead_volume_solid: cq.Workplane
    outer_envelope_solid: cq.Workplane
    service_sweep_solid: cq.Workplane
    datums: tuple[ReservoirDatum, ...]
    cavity_classification: str = "WET_REMOVABLE"
    fluid_identity: str = FLUID_IDENTITY
    wall_thickness_mm: float = WALL_THICKNESS_MM
    pickup_center_above_internal_floor_mm: float = PICKUP_CENTER_ABOVE_INTERNAL_FLOOR_MM
    service_withdrawal_travel_mm: float = SERVICE_WITHDRAWAL_TRAVEL_MM
    package_clearance_reservation_mm: float = PACKAGE_CLEARANCE_RESERVATION_MM
    geometry_status: str = GEOMETRY_STATUS
    cross_section_provenance: str = CROSS_SECTION_PROVENANCE
    service_status: str = SERVICE_STATUS
    volume_evidence_kind: str = VOLUME_EVIDENCE_KIND
    physical_validation_eligible: bool = False
    evidence_status: str = PHYSICAL_EVIDENCE_STATUS

    def __post_init__(self) -> None:
        self.validate_invariants()

    @property
    def gross_geometric_volume_mL(self) -> float:
        return float(self.cavity_solid.val().Volume()) / 1000.0

    @property
    def neutral_geometric_dead_volume_mL(self) -> float:
        return float(self.dead_volume_solid.val().Volume()) / 1000.0

    @property
    def neutral_geometric_usable_volume_mL(self) -> float:
        return self.gross_geometric_volume_mL - self.neutral_geometric_dead_volume_mL

    @property
    def gross_target_met(self) -> bool:
        return self.gross_geometric_volume_mL >= self.gross_target_mL - CAD_VOLUME_TOLERANCE_ML

    @property
    def minimum_usable_met(self) -> bool:
        return self.neutral_geometric_usable_volume_mL >= self.minimum_usable_mL - CAD_VOLUME_TOLERANCE_ML

    @property
    def outer_bounds_xyz_mm(self) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
        """Return exact authored package bounds, not OCCT tolerance-inflated bounds."""
        half_x = OUTER_WIDTH_X_MM / 2.0
        half_y = OUTER_HEIGHT_Y_MM / 2.0
        half_z = OUTER_DEPTH_Z_MM / 2.0
        return (
            (
                RESERVOIR_CENTER.x - half_x,
                RESERVOIR_CENTER.y - half_y,
                RESERVOIR_CENTER.z - half_z,
            ),
            (
                RESERVOIR_CENTER.x + half_x,
                RESERVOIR_CENTER.y + half_y,
                RESERVOIR_CENTER.z + half_z,
            ),
        )

    def validate_invariants(self) -> None:
        if self.reservoir_id != WATER_RESERVOIR_ID:
            raise WaterReservoirError("Realized reservoir must retain the stable water-reservoir ID")
        if type(self.source_authority_revision) is not str or not self.source_authority_revision:
            raise WaterReservoirError("Realized reservoir authority revision must be exact nonblank text")
        _canonical_sha256(self.source_architecture_sha256, label="water-reservoir source architecture")
        gross_target = _positive(self.gross_target_mL, label="gross water target")
        minimum_usable = _positive(self.minimum_usable_mL, label="minimum usable water target")
        if minimum_usable > gross_target:
            raise WaterReservoirError("Minimum usable target cannot exceed gross water target")
        if self.fluid_identity != FLUID_IDENTITY:
            raise WaterReservoirError("Realized reservoir cannot change FRESH_WATER identity")
        if self.cavity_classification != "WET_REMOVABLE":
            raise WaterReservoirError("Realized reservoir must remain WET_REMOVABLE")
        if tuple(datum.datum_id for datum in self.datums) != DATUM_IDS:
            raise WaterReservoirError("Realized reservoir datum set/order is not controlled")
        if self.wall_thickness_mm != WALL_THICKNESS_MM:
            raise WaterReservoirError("Reservoir wall must retain the controlled provisional baseline")
        if self.pickup_center_above_internal_floor_mm != PICKUP_CENTER_ABOVE_INTERNAL_FLOOR_MM:
            raise WaterReservoirError("Pickup-height baseline must remain controlled")
        if self.service_withdrawal_travel_mm != SERVICE_WITHDRAWAL_TRAVEL_MM:
            raise WaterReservoirError("Reservoir service sweep must retain controlled travel")
        if self.package_clearance_reservation_mm != PACKAGE_CLEARANCE_RESERVATION_MM:
            raise WaterReservoirError("Reservoir package-clearance reservation must remain controlled")
        if self.geometry_status != GEOMETRY_STATUS or self.cross_section_provenance != CROSS_SECTION_PROVENANCE:
            raise WaterReservoirError("Reservoir geometry cannot promote provisional CAD to physical evidence")
        if self.service_status != SERVICE_STATUS or self.volume_evidence_kind != VOLUME_EVIDENCE_KIND:
            raise WaterReservoirError("Reservoir service/volume evidence status must remain digital-only")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise WaterReservoirError("Realized reservoir cannot be physical validation evidence")
        if self.evidence_status != PHYSICAL_EVIDENCE_STATUS:
            raise WaterReservoirError("Realized reservoir evidence firewall must remain exact")

        for label, solid, expected_solids in (
            ("body", self.body_solid, 1),
            ("lid", self.lid_solid, 1),
            ("cavity", self.cavity_solid, 1),
            ("dead volume", self.dead_volume_solid, 1),
            ("outer envelope", self.outer_envelope_solid, 1),
            ("service sweep", self.service_sweep_solid, 1),
        ):
            shape = solid.val()
            if not shape.isValid() or solid.solids().size() != expected_solids:
                raise WaterReservoirError(f"Realized reservoir {label} must be one valid deterministic solid")

        gross = self.gross_geometric_volume_mL
        dead = self.neutral_geometric_dead_volume_mL
        usable = self.neutral_geometric_usable_volume_mL
        if dead <= 0.0 or dead >= gross:
            raise WaterReservoirError("Neutral geometric dead volume must be positive and below gross cavity volume")
        if not math.isclose(gross, gross_target, rel_tol=0.0, abs_tol=CAD_VOLUME_TOLERANCE_ML):
            raise WaterReservoirError("Realized cavity must close the exact authority gross-volume baseline")
        if usable < minimum_usable - CAD_VOLUME_TOLERANCE_ML:
            raise WaterReservoirError("Realized neutral geometric usable volume must satisfy the authority minimum")

        body_bb = self.body_solid.val().BoundingBox()
        lid_bb = self.lid_solid.val().BoundingBox()
        if not math.isclose(float(body_bb.zmax), LID_Z_MIN_MM, rel_tol=0.0, abs_tol=2e-6):
            raise WaterReservoirError("Reservoir body must terminate at the controlled lid interface plane")
        if not math.isclose(float(lid_bb.zmin), LID_Z_MIN_MM, rel_tol=0.0, abs_tol=2e-6):
            raise WaterReservoirError("Reservoir lid must begin at the controlled body interface plane")

    def validate_current_sources(self, authority: Authority) -> WaterReservoirArchitecture:
        current = build_water_reservoir_architecture(authority)
        current.validate_current_authority(authority)
        if self.source_authority_revision != str(authority.get("project", "authority_revision")):
            raise WaterReservoirError("Realized reservoir is stale for current authority revision")
        if self.source_architecture_sha256 != current.architecture_sha256:
            raise WaterReservoirError("Realized reservoir is stale for current water-reservoir architecture")
        if self.gross_target_mL != current.gross_target_mL:
            raise WaterReservoirError("Realized reservoir gross target is stale")
        if self.minimum_usable_mL != current.minimum_usable_mL:
            raise WaterReservoirError("Realized reservoir usable target is stale")
        return current

    def manifest(self) -> dict[str, object]:
        bounds_min, bounds_max = self.outer_bounds_xyz_mm
        return {
            "reservoir_id": self.reservoir_id,
            "source_authority_revision": self.source_authority_revision,
            "source_architecture_sha256": self.source_architecture_sha256,
            "world_frame_id": WORLD_FRAME_ID,
            "fluid_identity": self.fluid_identity,
            "cavity_classification": self.cavity_classification,
            "internal_dimensions_xyz_mm": [
                INTERNAL_WIDTH_X_MM,
                INTERNAL_HEIGHT_Y_MM,
                INTERNAL_DEPTH_Z_MM,
            ],
            "outer_dimensions_xyz_mm": [
                OUTER_WIDTH_X_MM,
                OUTER_HEIGHT_Y_MM,
                OUTER_DEPTH_Z_MM,
            ],
            "outer_center_xyz_mm": list(RESERVOIR_CENTER.as_tuple()),
            "outer_bounds_min_xyz_mm": list(bounds_min),
            "outer_bounds_max_xyz_mm": list(bounds_max),
            "wall_thickness_mm": self.wall_thickness_mm,
            "wall_provenance": self.cross_section_provenance,
            "gross_target_mL": self.gross_target_mL,
            "minimum_usable_mL": self.minimum_usable_mL,
            "gross_geometric_volume_mL": self.gross_geometric_volume_mL,
            "neutral_geometric_dead_volume_mL": self.neutral_geometric_dead_volume_mL,
            "neutral_geometric_usable_volume_mL": self.neutral_geometric_usable_volume_mL,
            "gross_target_met": self.gross_target_met,
            "minimum_usable_met": self.minimum_usable_met,
            "pickup_center_above_internal_floor_mm": self.pickup_center_above_internal_floor_mm,
            "service_withdrawal_travel_mm": self.service_withdrawal_travel_mm,
            "package_clearance_reservation_mm": self.package_clearance_reservation_mm,
            "datums": [datum.manifest() for datum in self.datums],
            "geometry_status": self.geometry_status,
            "service_status": self.service_status,
            "volume_evidence_kind": self.volume_evidence_kind,
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": self.evidence_status,
        }

    @property
    def manifest_sha256(self) -> str:
        return sha256(
            json.dumps(self.manifest(), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()


def _build_datums() -> tuple[ReservoirDatum, ...]:
    half_x = OUTER_WIDTH_X_MM / 2.0
    half_y = OUTER_HEIGHT_Y_MM / 2.0
    mount_z = (OUTER_Z_MIN_MM + LID_Z_MIN_MM) / 2.0
    pickup_z = INTERNAL_Z_MIN_MM + PICKUP_CENTER_ABOVE_INTERNAL_FLOOR_MM
    return (
        ReservoirDatum(
            DATUM_MOUNT_LEFT,
            Point3(-half_x, RESERVOIR_CENTER.y, mount_z),
            Vector3(-1.0, 0.0, 0.0),
            "reservoir-side left mounting reference; mating frame feature unresolved",
            None,
        ),
        ReservoirDatum(
            DATUM_MOUNT_RIGHT,
            Point3(half_x, RESERVOIR_CENTER.y, mount_z),
            Vector3(1.0, 0.0, 0.0),
            "reservoir-side right mounting reference; mating frame feature unresolved",
            None,
        ),
        ReservoirDatum(
            DATUM_MOUNT_REAR_STOP,
            Point3(0.0, RESERVOIR_CENTER.y, OUTER_Z_MIN_MM),
            Vector3(0.0, 0.0, -1.0),
            "reservoir posterior seating-stop reference; frame stop geometry unresolved",
            None,
        ),
        ReservoirDatum(
            DATUM_SERVICE_WITHDRAWAL,
            Point3(0.0, RESERVOIR_CENTER.y, OUTER_Z_MIN_MM),
            Vector3(0.0, 0.0, -1.0),
            "straight posterior off-face reservoir removal axis",
            None,
        ),
        ReservoirDatum(
            PORT_FILL,
            Point3(-6.0, RESERVOIR_CENTER.y, LID_Z_MAX_MM),
            Vector3(0.0, 0.0, 1.0),
            "fresh-water fill interface datum on removable lid; connector/seal unresolved",
            FLUID_IDENTITY,
        ),
        ReservoirDatum(
            PORT_VENT,
            Point3(6.0, RESERVOIR_CENTER.y, LID_Z_MAX_MM),
            Vector3(0.0, 0.0, 1.0),
            "fresh-water vent interface datum on removable lid; liquid barrier unresolved",
            FLUID_IDENTITY,
        ),
        ReservoirDatum(
            PORT_PICKUP,
            Point3(0.0, RESERVOIR_CENTER.y - half_y, pickup_z),
            Vector3(0.0, -1.0, 0.0),
            "fresh-water pickup handoff datum; connector and tube geometry unresolved",
            FLUID_IDENTITY,
        ),
    )


def build_realized_water_reservoir(authority: Authority) -> RealizedWaterReservoir:
    architecture = build_water_reservoir_architecture(authority)

    body_depth = WALL_THICKNESS_MM + INTERNAL_DEPTH_Z_MM
    body_center = Point3(
        RESERVOIR_CENTER.x,
        RESERVOIR_CENTER.y,
        OUTER_Z_MIN_MM + body_depth / 2.0,
    )
    body_outer = _box(OUTER_WIDTH_X_MM, OUTER_HEIGHT_Y_MM, body_depth, body_center)

    cavity_cut_depth = INTERNAL_DEPTH_Z_MM + CAVITY_CUT_OVERTRAVEL_MM
    cavity_cut_center = Point3(
        RESERVOIR_CENTER.x,
        RESERVOIR_CENTER.y,
        INTERNAL_Z_MIN_MM + cavity_cut_depth / 2.0,
    )
    cavity_cut = _box(
        INTERNAL_WIDTH_X_MM,
        INTERNAL_HEIGHT_Y_MM,
        cavity_cut_depth,
        cavity_cut_center,
    )
    body = body_outer.cut(cavity_cut)

    lid = _box(
        OUTER_WIDTH_X_MM,
        OUTER_HEIGHT_Y_MM,
        WALL_THICKNESS_MM,
        Point3(RESERVOIR_CENTER.x, RESERVOIR_CENTER.y, (LID_Z_MIN_MM + LID_Z_MAX_MM) / 2.0),
    )

    cavity = _box(
        INTERNAL_WIDTH_X_MM,
        INTERNAL_HEIGHT_Y_MM,
        INTERNAL_DEPTH_Z_MM,
        Point3(
            RESERVOIR_CENTER.x,
            RESERVOIR_CENTER.y,
            (INTERNAL_Z_MIN_MM + INTERNAL_Z_MAX_MM) / 2.0,
        ),
    )

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

    outer_envelope = _box(
        OUTER_WIDTH_X_MM,
        OUTER_HEIGHT_Y_MM,
        OUTER_DEPTH_Z_MM,
        RESERVOIR_CENTER,
    )

    sweep_depth = OUTER_DEPTH_Z_MM + SERVICE_WITHDRAWAL_TRAVEL_MM
    service_sweep = _box(
        OUTER_WIDTH_X_MM,
        OUTER_HEIGHT_Y_MM,
        sweep_depth,
        Point3(
            RESERVOIR_CENTER.x,
            RESERVOIR_CENTER.y,
            RESERVOIR_CENTER.z - SERVICE_WITHDRAWAL_TRAVEL_MM / 2.0,
        ),
    )

    result = RealizedWaterReservoir(
        reservoir_id=WATER_RESERVOIR_ID,
        source_authority_revision=str(authority.get("project", "authority_revision")),
        source_architecture_sha256=architecture.architecture_sha256,
        gross_target_mL=architecture.gross_target_mL,
        minimum_usable_mL=architecture.minimum_usable_mL,
        body_solid=body,
        lid_solid=lid,
        cavity_solid=cavity,
        dead_volume_solid=dead_volume,
        outer_envelope_solid=outer_envelope,
        service_sweep_solid=service_sweep,
        datums=_build_datums(),
    )
    result.validate_current_sources(authority)
    return result
