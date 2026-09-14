from __future__ import annotations

"""Cell 9 fresh-water source-to-pump geometry and pump package.

This module realizes source-bound digital package/interface geometry plus the bounded
reservoir-pickup to pump-inlet route. It does not select a supplier pump, tubing,
connector, driver, flow curve, pressure capability, prime behavior, orientation
performance, leakage performance, service performance, or any other physical result.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math

import cadquery as cq

from .authority import Authority
from .realized_fresh_water_source import build_realized_fresh_water_source
from .spatial import Point3, Vector3
from .water_reservoir import PORT_PICKUP, WaterReservoirError

WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
FLUID_IDENTITY = "FRESH_WATER"
PUMP_STATION_ID = "PUMP-STATION-WATER"
PUMP_OUTLET_ID = "PUMP-OUTLET-WATER"
MANIFOLD_INLET_ID = "MANIFOLD-INLET-WATER-I23"
SOURCE_ROUTE_ID = "ROUTE-WATER-RESERVOIR-TO-PUMP"
DOWNSTREAM_ROUTE_ID = "ROUTE-WATER-PUMP-TO-MANIFOLD-I23"
CAVITY_CLASSIFICATION = "WET_DRAINABLE"

AUTHORED_MAIN_SHA = "d02bce5b5cb43e33febd6e1a40fdc98f3893efca"
DONOR_PR85_HEAD = "668727ad2676a7d41f095878ff5d9110c8f7a44a"
DONOR_STATUS = "HISTORICAL_UNMERGED_GEOMETRY_DONOR_ONLY"

PUMP_CENTER = Point3(-46.0, -10.0, 7.0)
PUMP_SIZE_XYZ_MM = (30.0, 25.0, 8.2)
PUMP_LONG_AXIS = Vector3(1.0, 0.0, 0.0)
INLET_POINT = Point3(-31.0, -7.0, 7.0)
OUTLET_POINT = Point3(-31.0, -13.0, 7.0)
PORT_AXIS = Vector3(1.0, 0.0, 0.0)
PORT_RESERVATION_DIAMETER_MM = 4.0
PORT_RESERVATION_PROJECTION_MM = 2.0
PROVISIONAL_LUMEN_SEED_MM = 2.0

# The source route is intentionally bounded to the already-realized pickup and pump
# inlet datums. The intermediate vertices keep the run medial until inferior to the eye
# apertures, then move laterally to the pump side. These are current digital routing
# geometry, not selected flexible-tube bend geometry or a physical fit claim.
SOURCE_ROUTE_CENTERLINE_XYZ_MM = (
    (0.0, 62.5, 3.0),
    (0.0, 18.0, 3.0),
    (-33.0, 18.0, 7.0),
    (-33.0, -7.0, 7.0),
    (-31.0, -7.0, 7.0),
)
SOURCE_ROUTE_GEOMETRY_STATUS = (
    "REALIZED_WORLD_CENTERLINE_WITH_PROVISIONAL_LUMEN_SEED_NOT_SELECTED_TUBE_OR_BEND_GEOMETRY"
)
SOURCE_ROUTE_SUPPORT_STATUS = (
    "CENTERLINE_REALIZED_SUPPORT_ATTACHMENT_BLOCKED_PENDING_CURRENT_3D_FRAME_MEMBER_GEOMETRY"
)
DOWNSTREAM_ROUTE_STATUS = "BLOCKED_PENDING_WORLD_COORDINATE_MANIFOLD_INLET_DATUM"

CRADLE_BASE_SIZE_XYZ_MM = (32.8, 27.0, 1.5)
CRADLE_RAIL_SIZE_XYZ_MM = (1.0, 27.0, 8.7)
PACKAGE_SIDE_GAP_MM = 0.4
PACKAGE_BASE_GAP_MM = 0.5
SERVICE_SIZE_XYZ_MM = (34.0, 29.0, 12.2)

GEOMETRY_STATUS = "CELL9_CURRENT_MAIN_PUMP_SUPPLIER_FAMILY_SCREENING_GEOMETRY"
ROUTING_STATUS = "SOURCE_TO_PUMP_CENTERLINE_REALIZED_PUMP_TO_MANIFOLD_BLOCKED"
EVIDENCE_STATUS = (
    "DIGITAL_PACKAGE_INTERFACE_AND_SOURCE_ROUTE_GEOMETRY_ONLY_NOT_SUPPLIER_SELECTION_"
    "FLOW_PRESSURE_PRIME_ORIENTATION_LEAKAGE_ELECTRICAL_HYGIENE_DURABILITY_OR_PHYSICAL_SERVICE_EVIDENCE"
)


def _box(size_xyz: tuple[float, float, float], center: Point3) -> cq.Workplane:
    return (
        cq.Workplane("XY")
        .box(*size_xyz, centered=(True, True, True))
        .translate(center.as_tuple())
    )


def _cylinder(start: Point3, axis: Vector3, length_mm: float, diameter_mm: float) -> cq.Workplane:
    if length_mm <= 0.0 or diameter_mm <= 0.0:
        raise WaterReservoirError("pump interface dimensions must be positive")
    direction = axis.normalized()
    solid = cq.Solid.makeCylinder(
        diameter_mm / 2.0,
        length_mm,
        cq.Vector(*start.as_tuple()),
        cq.Vector(*direction.as_tuple()),
    )
    return cq.Workplane("XY").newObject([solid])


def _route_length_mm(points: tuple[tuple[float, float, float], ...]) -> float:
    if len(points) < 2:
        raise WaterReservoirError("fresh-water route requires at least two points")
    return sum(
        math.dist(a, b)
        for a, b in zip(points, points[1:])
    )


def _route_reference(points: tuple[tuple[float, float, float], ...], diameter_mm: float) -> cq.Workplane:
    if diameter_mm <= 0.0:
        raise WaterReservoirError("fresh-water route reference diameter must be positive")
    radius = diameter_mm / 2.0
    result: cq.Workplane | None = None
    for a, b in zip(points, points[1:]):
        length = math.dist(a, b)
        if length <= 0.0:
            raise WaterReservoirError("fresh-water route cannot contain zero-length segments")
        axis = Vector3(b[0] - a[0], b[1] - a[1], b[2] - a[2])
        segment = _cylinder(Point3(*a), axis, length, diameter_mm)
        result = segment if result is None else result.union(segment)
    for point in points[1:-1]:
        sphere = cq.Workplane("XY").newObject(
            [cq.Solid.makeSphere(radius, cq.Vector(*point))]
        )
        result = sphere if result is None else result.union(sphere)
    if result is None:
        raise WaterReservoirError("fresh-water route reference was not created")
    return result


@dataclass(frozen=True, slots=True)
class FreshWaterPumpDatum:
    datum_id: str
    point: Point3
    axis: Vector3
    role: str

    def manifest(self) -> dict[str, object]:
        return {
            "datum_id": self.datum_id,
            "point_xyz_mm": list(self.point.as_tuple()),
            "axis_xyz": list(self.axis.as_tuple()),
            "role": self.role,
            "fluid_identity": FLUID_IDENTITY,
        }


@dataclass(frozen=True, slots=True)
class RealizedFreshWaterPump:
    source_manifest_sha256: str
    package_solid: cq.Workplane
    support_cradle_solid: cq.Workplane
    inlet_reservation_solid: cq.Workplane
    outlet_reservation_solid: cq.Workplane
    service_reservation_solid: cq.Workplane
    source_route_reference_solid: cq.Workplane
    inlet_datum: FreshWaterPumpDatum
    outlet_datum: FreshWaterPumpDatum

    def validate_invariants(self) -> None:
        if len(self.source_manifest_sha256) != 64:
            raise WaterReservoirError("fresh-water pump source manifest hash must be SHA-256")
        for label, solid in (
            ("pump package", self.package_solid),
            ("pump cradle", self.support_cradle_solid),
            ("pump inlet reservation", self.inlet_reservation_solid),
            ("pump outlet reservation", self.outlet_reservation_solid),
            ("pump service reservation", self.service_reservation_solid),
            ("source route reference", self.source_route_reference_solid),
        ):
            if solid.solids().size() != 1 or not solid.val().isValid() or solid.val().Volume() <= 0.0:
                raise WaterReservoirError(f"{label} must be one valid positive B-rep")
        expected_volume = math.prod(PUMP_SIZE_XYZ_MM)
        if not math.isclose(self.package_solid.val().Volume(), expected_volume, rel_tol=0.0, abs_tol=1e-7):
            raise WaterReservoirError("pump screening envelope volume moved")
        if self.package_solid.val().intersect(self.support_cradle_solid.val()).Volume() > 1e-7:
            raise WaterReservoirError("pump package must preserve cradle installation gap")
        if self.inlet_datum.datum_id != "PUMP-STATION-WATER-INLET-DATUM-CELL9":
            raise WaterReservoirError("fresh-water pump inlet datum ID moved")
        if self.outlet_datum.datum_id != PUMP_OUTLET_ID:
            raise WaterReservoirError("fresh-water pump outlet datum ID moved")
        if SOURCE_ROUTE_CENTERLINE_XYZ_MM[0] != (0.0, 62.5, 3.0):
            raise WaterReservoirError("fresh-water source route no longer starts at released pickup datum")
        if SOURCE_ROUTE_CENTERLINE_XYZ_MM[-1] != self.inlet_datum.point.as_tuple():
            raise WaterReservoirError("fresh-water source route no longer terminates at pump inlet datum")

    def manifest(self) -> dict[str, object]:
        self.validate_invariants()
        route_length_mm = _route_length_mm(SOURCE_ROUTE_CENTERLINE_XYZ_MM)
        lumen_volume_ml = (
            math.pi * (PROVISIONAL_LUMEN_SEED_MM / 2.0) ** 2 * route_length_mm / 1000.0
        )
        return {
            "world_frame_id": WORLD_FRAME_ID,
            "fluid_identity": FLUID_IDENTITY,
            "pump_station_id": PUMP_STATION_ID,
            "source_route_id": SOURCE_ROUTE_ID,
            "source_interface_id": PORT_PICKUP,
            "downstream_route_id": DOWNSTREAM_ROUTE_ID,
            "downstream_interface_id": MANIFOLD_INLET_ID,
            "source_manifest_sha256": self.source_manifest_sha256,
            "authored_main_sha": AUTHORED_MAIN_SHA,
            "historical_donor": {"pr85_head": DONOR_PR85_HEAD, "status": DONOR_STATUS},
            "package": {
                "center_xyz_mm": list(PUMP_CENTER.as_tuple()),
                "size_xyz_mm": list(PUMP_SIZE_XYZ_MM),
                "long_axis_xyz": list(PUMP_LONG_AXIS.as_tuple()),
                "supplier_package_candidate_id": None,
                "supplier_package_evidence_sha256": None,
            },
            "interfaces": {
                "inlet": self.inlet_datum.manifest(),
                "outlet": self.outlet_datum.manifest(),
                "provisional_lumen_seed_mm": PROVISIONAL_LUMEN_SEED_MM,
                "reservation_diameter_mm": PORT_RESERVATION_DIAMETER_MM,
                "reservation_projection_mm": PORT_RESERVATION_PROJECTION_MM,
            },
            "source_route": {
                "route_id": SOURCE_ROUTE_ID,
                "centerline_xyz_mm": [list(point) for point in SOURCE_ROUTE_CENTERLINE_XYZ_MM],
                "centerline_length_mm": route_length_mm,
                "provisional_lumen_seed_mm": PROVISIONAL_LUMEN_SEED_MM,
                "neutral_geometric_lumen_volume_ml": lumen_volume_ml,
                "geometry_status": SOURCE_ROUTE_GEOMETRY_STATUS,
                "support_status": SOURCE_ROUTE_SUPPORT_STATUS,
                "selected_tubing": None,
                "selected_connector_standard": None,
                "selected_minimum_bend_radius_mm": None,
            },
            "downstream_route_status": DOWNSTREAM_ROUTE_STATUS,
            "support": {
                "cavity_classification": CAVITY_CLASSIFICATION,
                "base_size_xyz_mm": list(CRADLE_BASE_SIZE_XYZ_MM),
                "rail_size_xyz_mm": list(CRADLE_RAIL_SIZE_XYZ_MM),
                "package_side_gap_mm": PACKAGE_SIDE_GAP_MM,
                "package_base_gap_mm": PACKAGE_BASE_GAP_MM,
                "both_y_ends_open": True,
            },
            "service_reservation_size_xyz_mm": list(SERVICE_SIZE_XYZ_MM),
            "geometry_status": GEOMETRY_STATUS,
            "routing_status": ROUTING_STATUS,
            "selected_tubing_id_mm": None,
            "selected_minimum_bend_radius_mm": None,
            "selected_connector_standard": None,
            "physical_validation_eligible": False,
            "evidence_status": EVIDENCE_STATUS,
        }

    @property
    def manifest_sha256(self) -> str:
        return sha256(json.dumps(self.manifest(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def build_realized_fresh_water_pump(authority: Authority) -> RealizedFreshWaterPump:
    source = build_realized_fresh_water_source(authority)
    source.validate_current_sources(authority)
    pickup = next(item for item in source.datums if item.datum_id == PORT_PICKUP)
    if pickup.point.as_tuple() != SOURCE_ROUTE_CENTERLINE_XYZ_MM[0]:
        raise WaterReservoirError("fresh-water pickup moved; source route requires reconstruction")

    package = _box(PUMP_SIZE_XYZ_MM, PUMP_CENTER)

    package_z_min = PUMP_CENTER.z - PUMP_SIZE_XYZ_MM[2] / 2.0
    base_center = Point3(
        PUMP_CENTER.x,
        PUMP_CENTER.y,
        package_z_min - PACKAGE_BASE_GAP_MM - CRADLE_BASE_SIZE_XYZ_MM[2] / 2.0,
    )
    base = _box(CRADLE_BASE_SIZE_XYZ_MM, base_center)
    half_x = PUMP_SIZE_XYZ_MM[0] / 2.0
    rail_offset = half_x + PACKAGE_SIDE_GAP_MM + CRADLE_RAIL_SIZE_XYZ_MM[0] / 2.0
    base_top_z = base_center.z + CRADLE_BASE_SIZE_XYZ_MM[2] / 2.0
    rail_center_z = base_top_z + CRADLE_RAIL_SIZE_XYZ_MM[2] / 2.0
    left_rail = _box(
        CRADLE_RAIL_SIZE_XYZ_MM,
        Point3(PUMP_CENTER.x - rail_offset, PUMP_CENTER.y, rail_center_z),
    )
    right_rail = _box(
        CRADLE_RAIL_SIZE_XYZ_MM,
        Point3(PUMP_CENTER.x + rail_offset, PUMP_CENTER.y, rail_center_z),
    )
    cradle = base.union(left_rail).union(right_rail)

    inlet = FreshWaterPumpDatum(
        "PUMP-STATION-WATER-INLET-DATUM-CELL9",
        INLET_POINT,
        PORT_AXIS,
        "source-bound pump inlet package datum consumed by realized source route",
    )
    outlet = FreshWaterPumpDatum(
        PUMP_OUTLET_ID,
        OUTLET_POINT,
        PORT_AXIS,
        "pump outlet package datum; manifold-feed route and final manifold datum unresolved",
    )
    inlet_ref = _cylinder(
        INLET_POINT,
        PORT_AXIS,
        PORT_RESERVATION_PROJECTION_MM,
        PORT_RESERVATION_DIAMETER_MM,
    )
    outlet_ref = _cylinder(
        OUTLET_POINT,
        PORT_AXIS,
        PORT_RESERVATION_PROJECTION_MM,
        PORT_RESERVATION_DIAMETER_MM,
    )
    service = _box(SERVICE_SIZE_XYZ_MM, PUMP_CENTER)
    source_route = _route_reference(
        SOURCE_ROUTE_CENTERLINE_XYZ_MM,
        PROVISIONAL_LUMEN_SEED_MM,
    )

    realized = RealizedFreshWaterPump(
        source_manifest_sha256=source.manifest_sha256,
        package_solid=package,
        support_cradle_solid=cradle,
        inlet_reservation_solid=inlet_ref,
        outlet_reservation_solid=outlet_ref,
        service_reservation_solid=service,
        source_route_reference_solid=source_route,
        inlet_datum=inlet,
        outlet_datum=outlet,
    )
    realized.validate_invariants()
    return realized
