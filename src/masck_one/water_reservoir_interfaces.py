from __future__ import annotations

"""Realized fill, vent and pickup interface geometry for the fresh-water module.

This module is a bounded Cell 4 digital-geometry increment stacked on the realized
fresh-water reservoir. All bore sizes, closure/service reservations and internal
vent/pickup endpoint placements are provisional engineering baselines. They are not
supplier dimensions and do not establish sealing, leakage, venting, priming, spill,
orientation, hygiene, drying, durability or physical service performance.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math

import cadquery as cq

from .authority import Authority
from .realized_water_reservoir import (
    FLUID_IDENTITY,
    INTERNAL_DEPTH_Z_MM,
    INTERNAL_HEIGHT_Y_MM,
    INTERNAL_WIDTH_X_MM,
    INTERNAL_Z_MAX_MM,
    INTERNAL_Z_MIN_MM,
    LID_Z_MAX_MM,
    OUTER_HEIGHT_Y_MM,
    RESERVOIR_CENTER,
    RealizedWaterReservoir,
    build_realized_water_reservoir,
)
from .spatial import Point3, Vector3
from .water_reservoir import (
    ORIENTATION_CASE_IDS,
    PORT_FILL,
    PORT_PICKUP,
    PORT_VENT,
    WaterReservoirError,
)

WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
GEOMETRY_STATUS = "CELL4_PROVISIONAL_WATER_SERVICE_INTERFACE_GEOMETRY_NOT_PHYSICAL_EVIDENCE"
CROSS_SECTION_PROVENANCE = "CELL4_PROVISIONAL_INTERFACE_SEEDS_NO_SUPPLIER_SELECTION"
ORIENTATION_EVIDENCE_STATUS = (
    "DIGITAL_ENDPOINT_TO_AXIS_ALIGNED_CAVITY_BOUNDARY_REASONING_ONLY_"
    "NOT_SPILL_PRIMING_DRAWABILITY_OR_ORIENTATION_PERFORMANCE_EVIDENCE"
)
PHYSICAL_EVIDENCE_STATUS = (
    "DIGITAL_FILL_VENT_PICKUP_GEOMETRY_ONLY_NOT_SEALING_LEAKAGE_INGRESS_PRIMING_"
    "SPILL_ORIENTATION_HYGIENE_DRYING_DURABILITY_OR_SERVICE_VALIDATION"
)

# Explicit provisional Cell 4 CAD baselines. These reserve geometry without selecting
# production closures, membranes, tubing, fittings, materials or manufacturing process.
FILL_BORE_DIAMETER_MM = 6.0
FILL_CLOSURE_RESERVATION_DIAMETER_MM = 9.0
FILL_CLOSURE_RESERVATION_HEIGHT_MM = 3.0
VENT_LUMEN_DIAMETER_MM = 1.2
VENT_EXTERNAL_BARRIER_RESERVATION_DIAMETER_MM = 4.0
VENT_EXTERNAL_BARRIER_RESERVATION_HEIGHT_MM = 2.0
PICKUP_PASSAGE_DIAMETER_MM = 2.0
PICKUP_CONNECTOR_RESERVATION_DIAMETER_MM = 5.0
PICKUP_CONNECTOR_RESERVATION_LENGTH_MM = 4.0
PORT_CUT_OVERTRAVEL_MM = 0.2
VENT_INTERNAL_HIGH_SIDE_OFFSET_Y_MM = 1.0
VENT_INTERNAL_TOP_OFFSET_Z_MM = 0.5
PICKUP_INTERNAL_CAVITY_OVERTRAVEL_MM = 1.0

INTERNAL_X_MIN_MM = RESERVOIR_CENTER.x - INTERNAL_WIDTH_X_MM / 2.0
INTERNAL_X_MAX_MM = RESERVOIR_CENTER.x + INTERNAL_WIDTH_X_MM / 2.0
INTERNAL_Y_MIN_MM = RESERVOIR_CENTER.y - INTERNAL_HEIGHT_Y_MM / 2.0
INTERNAL_Y_MAX_MM = RESERVOIR_CENTER.y + INTERNAL_HEIGHT_Y_MM / 2.0

VENT_INTERNAL_TERMINUS = Point3(
    6.0,
    INTERNAL_Y_MAX_MM - VENT_INTERNAL_HIGH_SIDE_OFFSET_Y_MM,
    INTERNAL_Z_MAX_MM - VENT_INTERNAL_TOP_OFFSET_Z_MM,
)
PICKUP_INTERNAL_MOUTH = Point3(
    0.0,
    INTERNAL_Y_MIN_MM,
    INTERNAL_Z_MIN_MM + 1.0,
)


def _canonical_sha256(value: object, *, label: str) -> str:
    if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise WaterReservoirError(f"{label} must be canonical lowercase SHA-256")
    return value


def _cylinder(radius_mm: float, length_mm: float, start: Point3, direction: Vector3) -> cq.Workplane:
    if radius_mm <= 0.0 or length_mm <= 0.0:
        raise WaterReservoirError("Interface cylinders require positive radius and length")
    axis = direction.normalized()
    solid = cq.Solid.makeCylinder(
        radius_mm,
        length_mm,
        cq.Vector(*start.as_tuple()),
        cq.Vector(*axis.as_tuple()),
    )
    return cq.Workplane(obj=solid)


def _distance(a: Point3, b: Point3) -> float:
    return math.sqrt((b.x - a.x) ** 2 + (b.y - a.y) ** 2 + (b.z - a.z) ** 2)


def _projection(point: Point3, direction: Vector3) -> float:
    return point.x * direction.x + point.y * direction.y + point.z * direction.z


def _cavity_corners() -> tuple[Point3, ...]:
    return tuple(
        Point3(x, y, z)
        for x in (INTERNAL_X_MIN_MM, INTERNAL_X_MAX_MM)
        for y in (INTERNAL_Y_MIN_MM, INTERNAL_Y_MAX_MM)
        for z in (INTERNAL_Z_MIN_MM, INTERNAL_Z_MAX_MM)
    )


@dataclass(frozen=True, slots=True)
class OrientationGeometryCase:
    case_id: str
    gravity_down_world: Vector3 | None
    pickup_distance_to_gravity_low_boundary_mm: float | None
    vent_distance_to_gravity_high_boundary_mm: float | None
    numeric_screen_status: str
    evidence_status: str = ORIENTATION_EVIDENCE_STATUS
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        if self.case_id not in ORIENTATION_CASE_IDS:
            raise WaterReservoirError(f"Unknown reservoir orientation case {self.case_id!r}")
        if self.gravity_down_world is None:
            if self.pickup_distance_to_gravity_low_boundary_mm is not None:
                raise WaterReservoirError("Angle-unresolved orientation cannot carry numeric pickup distance")
            if self.vent_distance_to_gravity_high_boundary_mm is not None:
                raise WaterReservoirError("Angle-unresolved orientation cannot carry numeric vent distance")
            if self.numeric_screen_status != "ANGLE_UNRESOLVED_NO_NUMERIC_AXIS_SCREEN":
                raise WaterReservoirError("Angle-unresolved orientation must fail closed")
        else:
            if not math.isclose(self.gravity_down_world.norm(), 1.0, rel_tol=0.0, abs_tol=1e-12):
                raise WaterReservoirError("Orientation gravity vector must be unit length")
            for label, value in (
                ("pickup boundary distance", self.pickup_distance_to_gravity_low_boundary_mm),
                ("vent boundary distance", self.vent_distance_to_gravity_high_boundary_mm),
            ):
                if type(value) not in (int, float) or isinstance(value, bool) or not math.isfinite(float(value)) or float(value) < -1e-9:
                    raise WaterReservoirError(f"{label} must be a non-negative finite digital distance")
            if self.numeric_screen_status != "AXIS_ALIGNED_ENDPOINT_DISTANCE_AVAILABLE_NO_PERFORMANCE_INFERENCE":
                raise WaterReservoirError("Numeric orientation case must retain digital-only status")
        if self.evidence_status != ORIENTATION_EVIDENCE_STATUS:
            raise WaterReservoirError("Orientation reasoning cannot be promoted beyond digital geometry")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise WaterReservoirError("Orientation geometry cannot become physical validation evidence")

    def manifest(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "gravity_down_world_xyz": None if self.gravity_down_world is None else list(self.gravity_down_world.as_tuple()),
            "pickup_distance_to_gravity_low_boundary_mm": self.pickup_distance_to_gravity_low_boundary_mm,
            "vent_distance_to_gravity_high_boundary_mm": self.vent_distance_to_gravity_high_boundary_mm,
            "numeric_screen_status": self.numeric_screen_status,
            "evidence_status": self.evidence_status,
            "physical_validation_eligible": self.physical_validation_eligible,
        }


@dataclass(frozen=True, slots=True)
class WaterReservoirInterfaceGeometry:
    source_authority_revision: str
    source_realized_reservoir_sha256: str
    lid_with_fill_vent_ports_solid: cq.Workplane
    body_with_pickup_port_solid: cq.Workplane
    fill_bore_solid: cq.Workplane
    fill_closure_reservation_solid: cq.Workplane
    vent_path_solid: cq.Workplane
    vent_external_barrier_reservation_solid: cq.Workplane
    pickup_passage_solid: cq.Workplane
    pickup_connector_reservation_solid: cq.Workplane
    fill_centerline: tuple[Point3, ...]
    vent_centerline: tuple[Point3, ...]
    pickup_centerline: tuple[Point3, ...]
    orientation_cases: tuple[OrientationGeometryCase, ...]
    fluid_identity: str = FLUID_IDENTITY
    geometry_status: str = GEOMETRY_STATUS
    cross_section_provenance: str = CROSS_SECTION_PROVENANCE
    physical_validation_eligible: bool = False
    evidence_status: str = PHYSICAL_EVIDENCE_STATUS

    def __post_init__(self) -> None:
        self.validate_invariants()

    @property
    def fill_centerline_length_mm(self) -> float:
        return math.fsum(_distance(a, b) for a, b in zip(self.fill_centerline, self.fill_centerline[1:]))

    @property
    def vent_centerline_length_mm(self) -> float:
        return math.fsum(_distance(a, b) for a, b in zip(self.vent_centerline, self.vent_centerline[1:]))

    @property
    def pickup_centerline_length_mm(self) -> float:
        return math.fsum(_distance(a, b) for a, b in zip(self.pickup_centerline, self.pickup_centerline[1:]))

    @property
    def vent_internal_area_mm2(self) -> float:
        return math.pi * (VENT_LUMEN_DIAMETER_MM / 2.0) ** 2

    @property
    def vent_centerline_geometric_volume_mL(self) -> float:
        return self.vent_centerline_length_mm * self.vent_internal_area_mm2 / 1000.0

    @property
    def pickup_internal_area_mm2(self) -> float:
        return math.pi * (PICKUP_PASSAGE_DIAMETER_MM / 2.0) ** 2

    @property
    def pickup_centerline_geometric_volume_mL(self) -> float:
        return self.pickup_centerline_length_mm * self.pickup_internal_area_mm2 / 1000.0

    def validate_invariants(self) -> None:
        _canonical_sha256(self.source_realized_reservoir_sha256, label="realized-water source manifest")
        if type(self.source_authority_revision) is not str or not self.source_authority_revision:
            raise WaterReservoirError("Interface geometry requires exact authority revision")
        if self.fluid_identity != "FRESH_WATER":
            raise WaterReservoirError("Reservoir service interfaces cannot change FRESH_WATER identity")
        if self.geometry_status != GEOMETRY_STATUS or self.cross_section_provenance != CROSS_SECTION_PROVENANCE:
            raise WaterReservoirError("Reservoir service geometry must remain explicitly provisional")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise WaterReservoirError("Reservoir service geometry cannot become physical validation evidence")
        if self.evidence_status != PHYSICAL_EVIDENCE_STATUS:
            raise WaterReservoirError("Reservoir service evidence firewall must remain exact")
        if tuple(case.case_id for case in self.orientation_cases) != ORIENTATION_CASE_IDS:
            raise WaterReservoirError("Interface geometry must preserve the complete controlled orientation case set")

        for name, solid in (
            ("ported lid", self.lid_with_fill_vent_ports_solid),
            ("ported body", self.body_with_pickup_port_solid),
            ("fill bore", self.fill_bore_solid),
            ("fill closure reservation", self.fill_closure_reservation_solid),
            ("vent path", self.vent_path_solid),
            ("vent barrier reservation", self.vent_external_barrier_reservation_solid),
            ("pickup passage", self.pickup_passage_solid),
            ("pickup connector reservation", self.pickup_connector_reservation_solid),
        ):
            shape = solid.val()
            if not shape.isValid() or solid.solids().size() != 1:
                raise WaterReservoirError(f"Water reservoir {name} must be one valid deterministic solid")

        if len(self.fill_centerline) != 2 or len(self.pickup_centerline) != 2 or len(self.vent_centerline) != 3:
            raise WaterReservoirError("Water service centerline topology is not controlled")
        if self.fill_centerline[0].z != INTERNAL_Z_MAX_MM or self.fill_centerline[-1].z != LID_Z_MAX_MM:
            raise WaterReservoirError("Fill centerline must traverse exactly from cavity to external lid datum")
        if self.vent_centerline[-1] != VENT_INTERNAL_TERMINUS:
            raise WaterReservoirError("Vent path must terminate at the controlled internal high-side point")
        if self.pickup_centerline[-1] != PICKUP_INTERNAL_MOUTH:
            raise WaterReservoirError("Pickup path must terminate at the controlled internal pickup mouth")

    def validate_current_sources(self, authority: Authority) -> RealizedWaterReservoir:
        current = build_realized_water_reservoir(authority)
        current.validate_current_sources(authority)
        if self.source_authority_revision != str(authority.get("project", "authority_revision")):
            raise WaterReservoirError("Water service interface geometry is stale for current authority")
        if self.source_realized_reservoir_sha256 != current.manifest_sha256:
            raise WaterReservoirError("Water service interface geometry is stale for current realized reservoir")
        return current

    def manifest(self) -> dict[str, object]:
        return {
            "schema": "MASCK_ONE_CELL4_WATER_SERVICE_INTERFACES_V1",
            "source_authority_revision": self.source_authority_revision,
            "source_realized_reservoir_sha256": self.source_realized_reservoir_sha256,
            "world_frame_id": WORLD_FRAME_ID,
            "fluid_identity": self.fluid_identity,
            "fill": {
                "port_id": PORT_FILL,
                "bore_diameter_mm": FILL_BORE_DIAMETER_MM,
                "closure_reservation_diameter_mm": FILL_CLOSURE_RESERVATION_DIAMETER_MM,
                "closure_reservation_height_mm": FILL_CLOSURE_RESERVATION_HEIGHT_MM,
                "centerline_xyz_mm": [list(point.as_tuple()) for point in self.fill_centerline],
                "centerline_length_mm": self.fill_centerline_length_mm,
                "status": "PROVISIONAL_FILL_THROAT_AND_CLOSURE_KEEP_OUT_NO_SEAL_SELECTION",
            },
            "vent": {
                "port_id": PORT_VENT,
                "lumen_diameter_mm": VENT_LUMEN_DIAMETER_MM,
                "internal_area_mm2": self.vent_internal_area_mm2,
                "centerline_xyz_mm": [list(point.as_tuple()) for point in self.vent_centerline],
                "centerline_length_mm": self.vent_centerline_length_mm,
                "centerline_geometric_volume_mL": self.vent_centerline_geometric_volume_mL,
                "external_barrier_reservation_diameter_mm": VENT_EXTERNAL_BARRIER_RESERVATION_DIAMETER_MM,
                "external_barrier_reservation_height_mm": VENT_EXTERNAL_BARRIER_RESERVATION_HEIGHT_MM,
                "status": "PROVISIONAL_CONTINUOUS_VENT_LUMEN_AND_LIQUID_BARRIER_KEEP_OUT_INGRESS_UNVALIDATED",
            },
            "pickup": {
                "port_id": PORT_PICKUP,
                "passage_diameter_mm": PICKUP_PASSAGE_DIAMETER_MM,
                "internal_area_mm2": self.pickup_internal_area_mm2,
                "centerline_xyz_mm": [list(point.as_tuple()) for point in self.pickup_centerline],
                "centerline_length_mm": self.pickup_centerline_length_mm,
                "centerline_geometric_volume_mL": self.pickup_centerline_geometric_volume_mL,
                "connector_reservation_diameter_mm": PICKUP_CONNECTOR_RESERVATION_DIAMETER_MM,
                "connector_reservation_length_mm": PICKUP_CONNECTOR_RESERVATION_LENGTH_MM,
                "status": "PROVISIONAL_LOW_SIDE_PICKUP_PASSAGE_AND_CONNECTOR_KEEP_OUT_NO_TUBE_OR_FITTING_SELECTION",
            },
            "orientation_reasoning": [case.manifest() for case in self.orientation_cases],
            "orientation_reasoning_status": ORIENTATION_EVIDENCE_STATUS,
            "cross_section_provenance": self.cross_section_provenance,
            "geometry_status": self.geometry_status,
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": self.evidence_status,
        }

    @property
    def manifest_sha256(self) -> str:
        return sha256(
            json.dumps(self.manifest(), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()


def _axis_aligned_orientation_case(
    case_id: str,
    gravity: Vector3,
) -> OrientationGeometryCase:
    gravity = gravity.normalized()
    projections = tuple(_projection(point, gravity) for point in _cavity_corners())
    low_projection = max(projections)
    high_projection = min(projections)
    pickup_projection = _projection(PICKUP_INTERNAL_MOUTH, gravity)
    vent_projection = _projection(VENT_INTERNAL_TERMINUS, gravity)
    return OrientationGeometryCase(
        case_id=case_id,
        gravity_down_world=gravity,
        pickup_distance_to_gravity_low_boundary_mm=max(0.0, low_projection - pickup_projection),
        vent_distance_to_gravity_high_boundary_mm=max(0.0, vent_projection - high_projection),
        numeric_screen_status="AXIS_ALIGNED_ENDPOINT_DISTANCE_AVAILABLE_NO_PERFORMANCE_INFERENCE",
    )


def _orientation_cases() -> tuple[OrientationGeometryCase, ...]:
    numeric = {
        "ORIENTATION_NEUTRAL": Vector3(0.0, -1.0, 0.0),
        "ORIENTATION_FACE_UP": Vector3(0.0, 0.0, -1.0),
        "ORIENTATION_FACE_DOWN": Vector3(0.0, 0.0, 1.0),
    }
    cases: list[OrientationGeometryCase] = []
    for case_id in ORIENTATION_CASE_IDS:
        gravity = numeric.get(case_id)
        if gravity is None:
            cases.append(
                OrientationGeometryCase(
                    case_id=case_id,
                    gravity_down_world=None,
                    pickup_distance_to_gravity_low_boundary_mm=None,
                    vent_distance_to_gravity_high_boundary_mm=None,
                    numeric_screen_status="ANGLE_UNRESOLVED_NO_NUMERIC_AXIS_SCREEN",
                )
            )
        else:
            cases.append(_axis_aligned_orientation_case(case_id, gravity))
    return tuple(cases)


def build_water_reservoir_interface_geometry(
    authority: Authority,
    realized: RealizedWaterReservoir | None = None,
) -> WaterReservoirInterfaceGeometry:
    realized = realized or build_realized_water_reservoir(authority)
    realized.validate_current_sources(authority)
    datums = {datum.datum_id: datum for datum in realized.datums}
    fill_datum = datums[PORT_FILL]
    vent_datum = datums[PORT_VENT]
    pickup_datum = datums[PORT_PICKUP]

    fill_internal = Point3(fill_datum.point.x, fill_datum.point.y, INTERNAL_Z_MAX_MM)
    fill_cut_start = Point3(
        fill_datum.point.x,
        fill_datum.point.y,
        INTERNAL_Z_MAX_MM - PORT_CUT_OVERTRAVEL_MM,
    )
    fill_cut_length = LID_Z_MAX_MM - INTERNAL_Z_MAX_MM + 2.0 * PORT_CUT_OVERTRAVEL_MM
    fill_bore = _cylinder(
        FILL_BORE_DIAMETER_MM / 2.0,
        fill_cut_length,
        fill_cut_start,
        Vector3(0.0, 0.0, 1.0),
    )
    fill_closure_reservation = _cylinder(
        FILL_CLOSURE_RESERVATION_DIAMETER_MM / 2.0,
        FILL_CLOSURE_RESERVATION_HEIGHT_MM,
        fill_datum.point,
        Vector3(0.0, 0.0, 1.0),
    )

    vent_turn = Point3(
        vent_datum.point.x,
        vent_datum.point.y,
        VENT_INTERNAL_TERMINUS.z,
    )
    vent_vertical_start = Point3(
        vent_datum.point.x,
        vent_datum.point.y,
        VENT_INTERNAL_TERMINUS.z,
    )
    vent_vertical_length = vent_datum.point.z - VENT_INTERNAL_TERMINUS.z + PORT_CUT_OVERTRAVEL_MM
    vent_vertical = _cylinder(
        VENT_LUMEN_DIAMETER_MM / 2.0,
        vent_vertical_length,
        vent_vertical_start,
        Vector3(0.0, 0.0, 1.0),
    )
    vent_horizontal = _cylinder(
        VENT_LUMEN_DIAMETER_MM / 2.0,
        VENT_INTERNAL_TERMINUS.y - vent_turn.y,
        vent_turn,
        Vector3(0.0, 1.0, 0.0),
    )
    vent_path = vent_vertical.union(vent_horizontal)
    vent_barrier_reservation = _cylinder(
        VENT_EXTERNAL_BARRIER_RESERVATION_DIAMETER_MM / 2.0,
        VENT_EXTERNAL_BARRIER_RESERVATION_HEIGHT_MM,
        vent_datum.point,
        Vector3(0.0, 0.0, 1.0),
    )

    pickup_internal_overtravel = Point3(
        PICKUP_INTERNAL_MOUTH.x,
        PICKUP_INTERNAL_MOUTH.y + PICKUP_INTERNAL_CAVITY_OVERTRAVEL_MM,
        PICKUP_INTERNAL_MOUTH.z,
    )
    pickup_cut_start = Point3(
        pickup_datum.point.x,
        pickup_datum.point.y - PORT_CUT_OVERTRAVEL_MM,
        pickup_datum.point.z,
    )
    pickup_cut_length = pickup_internal_overtravel.y - pickup_cut_start.y
    pickup_passage = _cylinder(
        PICKUP_PASSAGE_DIAMETER_MM / 2.0,
        pickup_cut_length,
        pickup_cut_start,
        Vector3(0.0, 1.0, 0.0),
    )
    pickup_connector_reservation = _cylinder(
        PICKUP_CONNECTOR_RESERVATION_DIAMETER_MM / 2.0,
        PICKUP_CONNECTOR_RESERVATION_LENGTH_MM,
        pickup_datum.point,
        Vector3(0.0, -1.0, 0.0),
    )

    lid_with_ports = realized.lid_solid.cut(fill_bore).cut(vent_vertical)
    body_with_pickup = realized.body_solid.cut(pickup_passage)

    result = WaterReservoirInterfaceGeometry(
        source_authority_revision=str(authority.get("project", "authority_revision")),
        source_realized_reservoir_sha256=realized.manifest_sha256,
        lid_with_fill_vent_ports_solid=lid_with_ports,
        body_with_pickup_port_solid=body_with_pickup,
        fill_bore_solid=fill_bore,
        fill_closure_reservation_solid=fill_closure_reservation,
        vent_path_solid=vent_path,
        vent_external_barrier_reservation_solid=vent_barrier_reservation,
        pickup_passage_solid=pickup_passage,
        pickup_connector_reservation_solid=pickup_connector_reservation,
        fill_centerline=(fill_internal, fill_datum.point),
        vent_centerline=(vent_datum.point, vent_turn, VENT_INTERNAL_TERMINUS),
        pickup_centerline=(pickup_datum.point, PICKUP_INTERNAL_MOUTH),
        orientation_cases=_orientation_cases(),
    )
    result.validate_current_sources(authority)
    return result
