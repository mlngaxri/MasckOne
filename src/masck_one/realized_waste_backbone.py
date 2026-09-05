"""World-coordinate Cell 4 realization of the controlled mixed-waste backbone.

Coordinates and internal-area values in this module are explicit provisional
engineering baselines. They are not supplier dimensions and do not establish
hydraulic, recovery, leakage, orientation, hygiene, or service performance.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math

from .spatial import Point3
from .waste_acquisition import PHASE_MIXED_WASTE, ROUTE_DESTINATION
from .waste_pump_architecture import (
    BARRIER_WASTE,
    INTERFACE_BARRIER_OUTLET,
    INTERFACE_CARTRIDGE_INLET_I27,
    INTERFACE_PUMP_OUTLET,
    ROUTE_ACQUISITION_TO_PUMP,
    ROUTE_BARRIER_TO_CARTRIDGE,
    ROUTE_PUMP_TO_BARRIER,
    ROUTE_STAGES,
    STATION_WASTE,
)

WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
AUTHORITY_REVISION = "2026-08-30-R1"

(
    STAGE_ACQUISITION_TO_PUMP,
    STAGE_PUMP_TO_PASSIVE_BACKFLOW_BARRIER,
    STAGE_PASSIVE_BACKFLOW_BARRIER_TO_CARTRIDGE_HANDOFF,
) = ROUTE_STAGES

GEOMETRY_PROVENANCE = "CELL4_PROVISIONAL_ENGINEERING_BASELINE_NOT_PHYSICAL_EVIDENCE"
CROSS_SECTION_PROVENANCE = "CELL4_PROVISIONAL_2P4MM_CIRCULAR_ID_SEED_NOT_SUPPLIER_SELECTED"
SERVICE_PROVENANCE = "CELL4_2P0MM_CLEARANCE_RESERVATION_NOT_TRAJECTORY_VALIDATED"
PHYSICAL_STATE = "VALIDATION_GATED"
HYDRAULIC_STATE = "UNVALIDATED_MIXED_PHASE"
BEND_REQUIREMENT_STATE = "BLOCKED_PENDING_SELECTED_TUBE_OR_CHANNEL_REQUIREMENT"
SERVICE_STATE = "RESERVATION_ONLY_COLLISION_AND_DEFORMATION_TRAJECTORY_PENDING"

WASTE_ID_SEED_MM = 2.4
WASTE_INTERNAL_AREA_SEED_MM2 = math.pi * (WASTE_ID_SEED_MM / 2.0) ** 2
SERVICE_CLEARANCE_RESERVATION_MM = 2.0


class RealizedWasteBackboneError(ValueError):
    pass


def _distance(a: Point3, b: Point3) -> float:
    return a.vector_to(b).norm()


def _positive(value: object, label: str) -> float:
    if type(value) not in (int, float) or isinstance(value, bool):
        raise RealizedWasteBackboneError(f"{label} must be an exact numeric scalar")
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise RealizedWasteBackboneError(f"{label} must be finite and positive")
    return result


def _git_sha(value: object, label: str) -> str:
    if type(value) is not str or len(value) != 40 or any(c not in "0123456789abcdef" for c in value):
        raise RealizedWasteBackboneError(f"{label} must be exact lowercase 40-hex")
    return value


def _sha256_digest(value: object, label: str) -> str:
    if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise RealizedWasteBackboneError(f"{label} must be exact lowercase SHA-256")
    return value


def _angle_is_on_sweep(angle_deg: float, start_deg: float, sweep_deg: float) -> bool:
    if sweep_deg > 0.0:
        return (angle_deg - start_deg) % 360.0 <= sweep_deg + 1e-12
    return (start_deg - angle_deg) % 360.0 <= -sweep_deg + 1e-12


@dataclass(frozen=True, slots=True)
class Line3:
    start: Point3
    end: Point3

    def validate(self) -> None:
        if type(self.start) is not Point3 or type(self.end) is not Point3:
            raise RealizedWasteBackboneError("line endpoints must be exact Point3 values")
        if _distance(self.start, self.end) <= 1e-9:
            raise RealizedWasteBackboneError("line cannot have zero length")

    @property
    def length_mm(self) -> float:
        self.validate()
        return _distance(self.start, self.end)

    @property
    def bounds_xyz_mm(self) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
        self.validate()
        return (
            (
                min(self.start.x, self.end.x),
                min(self.start.y, self.end.y),
                min(self.start.z, self.end.z),
            ),
            (
                max(self.start.x, self.end.x),
                max(self.start.y, self.end.y),
                max(self.start.z, self.end.z),
            ),
        )

    def manifest(self) -> dict[str, object]:
        bounds_min, bounds_max = self.bounds_xyz_mm
        return {
            "kind": "LINE",
            "start_xyz_mm": list(self.start.as_tuple()),
            "end_xyz_mm": list(self.end.as_tuple()),
            "length_mm": self.length_mm,
            "bounds_min_xyz_mm": list(bounds_min),
            "bounds_max_xyz_mm": list(bounds_max),
        }


@dataclass(frozen=True, slots=True)
class ArcXY:
    center: Point3
    radius_mm: float
    start_angle_deg: float
    sweep_angle_deg: float

    def validate(self) -> None:
        if type(self.center) is not Point3:
            raise RealizedWasteBackboneError("arc center must be an exact Point3")
        _positive(self.radius_mm, "arc radius")
        for value, label in (
            (self.start_angle_deg, "arc start angle"),
            (self.sweep_angle_deg, "arc sweep angle"),
        ):
            if type(value) not in (int, float) or isinstance(value, bool) or not math.isfinite(float(value)):
                raise RealizedWasteBackboneError(f"{label} must be finite numeric")
        if not 0.0 < abs(float(self.sweep_angle_deg)) <= 180.0:
            raise RealizedWasteBackboneError("arc sweep magnitude must be in (0, 180]")

    def point_at(self, angle_deg: float) -> Point3:
        angle = math.radians(angle_deg)
        return Point3(
            self.center.x + self.radius_mm * math.cos(angle),
            self.center.y + self.radius_mm * math.sin(angle),
            self.center.z,
        )

    @property
    def start(self) -> Point3:
        self.validate()
        return self.point_at(float(self.start_angle_deg))

    @property
    def end(self) -> Point3:
        self.validate()
        return self.point_at(float(self.start_angle_deg) + float(self.sweep_angle_deg))

    @property
    def length_mm(self) -> float:
        self.validate()
        return self.radius_mm * abs(math.radians(float(self.sweep_angle_deg)))

    @property
    def bounds_xyz_mm(self) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
        self.validate()
        start = float(self.start_angle_deg)
        sweep = float(self.sweep_angle_deg)
        candidates = [start, start + sweep]
        for cardinal in (0.0, 90.0, 180.0, 270.0):
            if _angle_is_on_sweep(cardinal, start, sweep):
                candidates.append(cardinal)
        points = tuple(self.point_at(angle) for angle in candidates)
        return (
            (
                min(point.x for point in points),
                min(point.y for point in points),
                self.center.z,
            ),
            (
                max(point.x for point in points),
                max(point.y for point in points),
                self.center.z,
            ),
        )

    def manifest(self) -> dict[str, object]:
        bounds_min, bounds_max = self.bounds_xyz_mm
        return {
            "kind": "ARC_XY",
            "center_xyz_mm": list(self.center.as_tuple()),
            "radius_mm": self.radius_mm,
            "start_angle_deg": float(self.start_angle_deg),
            "sweep_angle_deg": float(self.sweep_angle_deg),
            "start_xyz_mm": list(self.start.as_tuple()),
            "end_xyz_mm": list(self.end.as_tuple()),
            "length_mm": self.length_mm,
            "bounds_min_xyz_mm": list(bounds_min),
            "bounds_max_xyz_mm": list(bounds_max),
        }


Primitive = Line3 | ArcXY


@dataclass(frozen=True, slots=True)
class RealizedWasteRoute:
    route_id: str
    stage: str
    source_interface_id: str
    target_interface_id: str
    centerline: tuple[Primitive, ...]
    fluid_identity: str = PHASE_MIXED_WASTE
    world_frame_id: str = WORLD_FRAME_ID
    internal_area_mm2: float = WASTE_INTERNAL_AREA_SEED_MM2
    cross_section_provenance: str = CROSS_SECTION_PROVENANCE
    service_clearance_reservation_mm: float = SERVICE_CLEARANCE_RESERVATION_MM
    service_clearance_provenance: str = SERVICE_PROVENANCE
    minimum_bend_requirement_mm: None = None
    bend_margin_mm: None = None
    realized_service_clearance_mm: None = None
    service_margin_mm: None = None
    bend_requirement_state: str = BEND_REQUIREMENT_STATE
    service_state: str = SERVICE_STATE
    geometry_provenance: str = GEOMETRY_PROVENANCE
    physical_performance_state: str = PHYSICAL_STATE
    hydraulic_state: str = HYDRAULIC_STATE

    @property
    def segment_id(self) -> str:
        return self.route_id

    def validate(self) -> None:
        if type(self.route_id) is not str or not self.route_id:
            raise RealizedWasteBackboneError("route ID must be exact nonblank text")
        if type(self.stage) is not str or self.stage not in ROUTE_STAGES:
            raise RealizedWasteBackboneError("route stage must use the current controlled waste vocabulary")
        if self.fluid_identity != PHASE_MIXED_WASTE:
            raise RealizedWasteBackboneError("route must retain mixed-waste identity")
        if self.world_frame_id != WORLD_FRAME_ID:
            raise RealizedWasteBackboneError("route must use the frozen authority world frame")
        if type(self.centerline) is not tuple or not self.centerline:
            raise RealizedWasteBackboneError("route must have immutable centerline primitives")
        for primitive in self.centerline:
            if type(primitive) not in (Line3, ArcXY):
                raise RealizedWasteBackboneError("route contains an uncontrolled centerline primitive")
            primitive.validate()
        for left, right in zip(self.centerline, self.centerline[1:]):
            if _distance(left.end, right.start) > 1e-6:
                raise RealizedWasteBackboneError("route centerline is discontinuous")
        _positive(self.internal_area_mm2, "internal area")
        _positive(self.service_clearance_reservation_mm, "service clearance reservation")
        if self.cross_section_provenance != CROSS_SECTION_PROVENANCE or self.geometry_provenance != GEOMETRY_PROVENANCE:
            raise RealizedWasteBackboneError("route geometry provenance is not the controlled provisional baseline")
        if self.service_clearance_provenance != SERVICE_PROVENANCE or self.service_state != SERVICE_STATE:
            raise RealizedWasteBackboneError("service clearance must remain reservation-only")
        if any(
            value is not None
            for value in (
                self.minimum_bend_requirement_mm,
                self.bend_margin_mm,
                self.realized_service_clearance_mm,
                self.service_margin_mm,
            )
        ):
            raise RealizedWasteBackboneError("supplier bend and realized service margins cannot be invented")
        if self.bend_requirement_state != BEND_REQUIREMENT_STATE:
            raise RealizedWasteBackboneError("bend requirement must remain supplier-gated")
        if self.physical_performance_state != PHYSICAL_STATE or self.hydraulic_state != HYDRAULIC_STATE:
            raise RealizedWasteBackboneError("digital geometry cannot promote physical performance")

    @property
    def centerline_length_mm(self) -> float:
        self.validate()
        return math.fsum(item.length_mm for item in self.centerline)

    @property
    def geometric_dead_volume_mL(self) -> float:
        return self.centerline_length_mm * self.internal_area_mm2 / 1000.0

    @property
    def realized_min_bend_radius_mm(self) -> float | None:
        radii = [item.radius_mm for item in self.centerline if type(item) is ArcXY]
        return min(radii) if radii else None

    @property
    def service_envelope_radius_mm(self) -> float:
        return WASTE_ID_SEED_MM / 2.0 + self.service_clearance_reservation_mm

    @property
    def bounds_xyz_mm(self) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
        self.validate()
        bounds = tuple(item.bounds_xyz_mm for item in self.centerline)
        return (
            (
                min(item[0][0] for item in bounds),
                min(item[0][1] for item in bounds),
                min(item[0][2] for item in bounds),
            ),
            (
                max(item[1][0] for item in bounds),
                max(item[1][1] for item in bounds),
                max(item[1][2] for item in bounds),
            ),
        )

    def manifest(self) -> dict[str, object]:
        self.validate()
        bounds_min, bounds_max = self.bounds_xyz_mm
        return {
            "segment_id": self.segment_id,
            "route_id": self.route_id,
            "stage": self.stage,
            "source_interface_id": self.source_interface_id,
            "target_interface_id": self.target_interface_id,
            "fluid_identity": self.fluid_identity,
            "world_frame_id": self.world_frame_id,
            "centerline": [item.manifest() for item in self.centerline],
            "centerline_length_mm": self.centerline_length_mm,
            "bounds_min_xyz_mm": list(bounds_min),
            "bounds_max_xyz_mm": list(bounds_max),
            "internal_area_mm2": self.internal_area_mm2,
            "cross_section_provenance": self.cross_section_provenance,
            "geometric_dead_volume_mL": self.geometric_dead_volume_mL,
            "realized_min_bend_radius_mm": self.realized_min_bend_radius_mm,
            "minimum_bend_requirement_mm": None,
            "bend_margin_mm": None,
            "bend_requirement_state": self.bend_requirement_state,
            "service_envelope_radius_mm": self.service_envelope_radius_mm,
            "service_clearance_reservation_mm": self.service_clearance_reservation_mm,
            "service_clearance_provenance": self.service_clearance_provenance,
            "realized_service_clearance_mm": None,
            "service_margin_mm": None,
            "service_state": self.service_state,
            "geometry_provenance": self.geometry_provenance,
            "physical_performance_state": self.physical_performance_state,
            "hydraulic_state": self.hydraulic_state,
        }


@dataclass(frozen=True, slots=True)
class RealizedWasteBackbone:
    source_git_sha: str
    source_waste_pump_architecture_sha256: str
    routes: tuple[RealizedWasteRoute, ...]
    authority_revision: str = AUTHORITY_REVISION

    def validate(self) -> None:
        _git_sha(self.source_git_sha, "authored-against Git SHA")
        _sha256_digest(
            self.source_waste_pump_architecture_sha256,
            "source waste-pump architecture digest",
        )
        if type(self.authority_revision) is not str or not self.authority_revision:
            raise RealizedWasteBackboneError("authority revision provenance must be exact nonblank text")
        expected = (
            (
                ROUTE_ACQUISITION_TO_PUMP,
                STAGE_ACQUISITION_TO_PUMP,
                PHASE_MIXED_WASTE,
                ROUTE_DESTINATION,
                STATION_WASTE,
            ),
            (
                ROUTE_PUMP_TO_BARRIER,
                STAGE_PUMP_TO_PASSIVE_BACKFLOW_BARRIER,
                PHASE_MIXED_WASTE,
                INTERFACE_PUMP_OUTLET,
                BARRIER_WASTE,
            ),
            (
                ROUTE_BARRIER_TO_CARTRIDGE,
                STAGE_PASSIVE_BACKFLOW_BARRIER_TO_CARTRIDGE_HANDOFF,
                PHASE_MIXED_WASTE,
                INTERFACE_BARRIER_OUTLET,
                INTERFACE_CARTRIDGE_INLET_I27,
            ),
        )
        actual = tuple(
            (
                route.segment_id,
                route.stage,
                route.fluid_identity,
                route.source_interface_id,
                route.target_interface_id,
            )
            for route in self.routes
        )
        if actual != expected:
            raise RealizedWasteBackboneError(
                "realized segment binding must retain the current passive-backflow topology"
            )
        for route in self.routes:
            route.validate()

    @property
    def total_geometric_dead_volume_mL(self) -> float:
        self.validate()
        return math.fsum(route.geometric_dead_volume_mL for route in self.routes)

    @property
    def manifest_sha256(self) -> str:
        self.validate()
        payload = {
            "source_git_sha": self.source_git_sha,
            "source_waste_pump_architecture_sha256": self.source_waste_pump_architecture_sha256,
            "authority_revision": self.authority_revision,
            "routes": [route.manifest() for route in self.routes],
            "total_geometric_dead_volume_mL": self.total_geometric_dead_volume_mL,
        }
        return sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()


def build_cell4_waste_backbone(
    *,
    source_git_sha: str,
    source_waste_pump_architecture_sha256: str,
    authority_revision: str = AUTHORITY_REVISION,
) -> RealizedWasteBackbone:
    """Build a hidden wearer-left inferior route baseline in authority world coordinates."""
    route_a = RealizedWasteRoute(
        ROUTE_ACQUISITION_TO_PUMP,
        STAGE_ACQUISITION_TO_PUMP,
        ROUTE_DESTINATION,
        STATION_WASTE,
        (Line3(Point3(-52.0, -34.0, 12.0), Point3(-48.0, -44.0, 16.0)),),
    )
    route_b = RealizedWasteRoute(
        ROUTE_PUMP_TO_BARRIER,
        STAGE_PUMP_TO_PASSIVE_BACKFLOW_BARRIER,
        INTERFACE_PUMP_OUTLET,
        BARRIER_WASTE,
        (
            Line3(Point3(-48.0, -44.0, 16.0), Point3(-43.0, -44.0, 16.0)),
            ArcXY(Point3(-43.0, -52.0, 16.0), 8.0, 90.0, 90.0),
            Line3(Point3(-51.0, -52.0, 16.0), Point3(-51.0, -58.0, 16.0)),
        ),
    )
    route_c = RealizedWasteRoute(
        ROUTE_BARRIER_TO_CARTRIDGE,
        STAGE_PASSIVE_BACKFLOW_BARRIER_TO_CARTRIDGE_HANDOFF,
        INTERFACE_BARRIER_OUTLET,
        INTERFACE_CARTRIDGE_INLET_I27,
        (
            Line3(Point3(-51.0, -58.0, 16.0), Point3(-51.0, -68.0, 16.0)),
            ArcXY(Point3(-43.0, -68.0, 16.0), 8.0, 180.0, 90.0),
            Line3(Point3(-43.0, -76.0, 16.0), Point3(-41.0, -82.0, 14.0)),
        ),
    )
    result = RealizedWasteBackbone(
        source_git_sha=source_git_sha,
        source_waste_pump_architecture_sha256=source_waste_pump_architecture_sha256,
        authority_revision=authority_revision,
        routes=(route_a, route_b, route_c),
    )
    result.validate()
    return result
