"""Source-bound provisional CAD realization for the mixed-waste pump station.

The released waste architecture and realized backbone already control the station identity,
mixed-waste phase, route order, and passive-backflow stage. This module adds only a
world-coordinate dimensional screening envelope, route-anchor port reservations, an open
WET_DRAINABLE support cradle, a low-point drain/dry clearance corridor, and a stationary
service reservation. It does not select a pump or establish mixed-phase/foam handling,
pressure-flow behavior, recovery, leakage, orientation, hygiene, durability, or service
performance.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import re

import cadquery as cq

from .realized_waste_backbone import WASTE_ID_SEED_MM
from .realized_waste_backbone_release import (
    Cell4WasteBackboneRelease,
    build_current_cell4_waste_backbone_release,
)
from .waste_acquisition import PHASE_MIXED_WASTE, ROUTE_DESTINATION
from .waste_pump_architecture import (
    BARRIER_WASTE,
    INTERFACE_PUMP_OUTLET,
    ROUTE_ACQUISITION_TO_PUMP,
    ROUTE_PUMP_TO_BARRIER,
    STATION_WASTE,
)

WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
AUTHORED_AGAINST_MAIN_SHA = "21cf8c4fb8ca0d20ddb58f90bcee6275bc98ca30"
SOURCE_WASTE_PUMP_ARCHITECTURE_BLOB_SHA = "ace02ee529070465b11832f475771125636312cb"
SOURCE_REALIZED_WASTE_BACKBONE_BLOB_SHA = "6aa79d9a613e278f32da85b4654c0e35cc09b7ca"
SCHEMA = "MASCK_ONE_CELL4_REALIZED_MIXED_WASTE_PUMP_V1"

MIXED_PHASE_CONSTITUENTS = ("AIR", "LIQUID", "CLEANSER", "FOAM", "CONTAMINANT")
PACKAGE_ID = "PUMP-STATION-WASTE-I26-CELL4-PROVISIONAL-PACKAGE"
PACKAGE_CENTER_WORLD_MM = (-54.0, -48.0, 12.0)
PACKAGE_ENVELOPE_XYZ_MM = (12.0, 8.0, 8.0)
PACKAGE_BOUNDS_WORLD_MM = {
    "x": (-60.0, -48.0),
    "y": (-52.0, -44.0),
    "z": (8.0, 16.0),
}
STATION_ROUTE_ANCHOR_WORLD_MM = (-48.0, -44.0, 16.0)

# The released acquisition route reaches the station with vector (4,-10,4), and the
# released pump-to-barrier route departs +X. These are route-anchor interface directions,
# not selected pump port orientations.
_SQRT_33 = math.sqrt(33.0)
INLET_ROUTE_AXIS_WORLD = (2.0 / _SQRT_33, -5.0 / _SQRT_33, 2.0 / _SQRT_33)
OUTLET_ROUTE_AXIS_WORLD = (1.0, 0.0, 0.0)
PORT_RESERVATION_DIAMETER_MM = 4.0
PORT_RESERVATION_PROJECTION_MM = 3.0
PORT_LUMEN_DIAMETER_SEED_MM = WASTE_ID_SEED_MM

# Open one-piece U cradle. The center remains open beneath the package, so there is no
# enclosed local wet pocket. The free-space drain/dry reference passes through that
# opening and is not assembly material.
SUPPORT_RAIL_XYZ_MM = (13.0, 1.0, 1.0)
SUPPORT_RAIL_CENTER_X_MM = -54.0
SUPPORT_RAIL_CENTER_Y_MM = (-51.5, -44.5)
SUPPORT_RAIL_CENTER_Z_MM = 7.0
SUPPORT_CROSSBAR_XYZ_MM = (1.0, 8.0, 1.0)
SUPPORT_CROSSBAR_CENTER_WORLD_MM = (-60.0, -48.0, 7.0)
SUPPORT_PACKAGE_BASE_GAP_SEED_MM = 0.5
SUPPORT_CAVITY_CLASSIFICATION = "WET_DRAINABLE"

DRAIN_DRY_CLEARANCE_CENTER_WORLD_MM = (-53.5, -48.0, 6.75)
DRAIN_DRY_CLEARANCE_XYZ_MM = (11.0, 5.0, 1.5)

# This is stationary local free space only, not a validated replacement trajectory.
SERVICE_CLEARANCE_CENTER_WORLD_MM = (-54.0, -48.0, 11.5)
SERVICE_CLEARANCE_XYZ_MM = (14.0, 10.0, 11.0)
SERVICE_CLEARANCE_BOUNDS_WORLD_MM = {
    "x": (-61.0, -47.0),
    "y": (-53.0, -43.0),
    "z": (6.0, 17.0),
}
LOCAL_STATIONARY_CLEARANCE_SEED_MM = 1.0

PACKAGE_STATUS = (
    "CELL4_PROVISIONAL_MIXED_WASTE_PUMP_DIMENSIONAL_SCREENING_ENVELOPE_NOT_SUPPLIER_SELECTED"
)
PORT_STATUS = (
    "ROUTE_ANCHOR_PORT_RESERVATION_ONLY_SELECTED_PUMP_PORT_SEPARATION_CONNECTOR_AND_WET_PATH_UNRESOLVED"
)
SUPPORT_STATUS = (
    "OPEN_WET_DRAINABLE_LOCAL_CRADLE_GEOMETRY_FRAME_JOIN_RETENTION_AND_MATERIAL_UNRESOLVED"
)
DRAIN_DRY_STATUS = (
    "LOW_POINT_OPEN_CLEARANCE_CORRIDOR_ONLY_DRYING_TIME_HYGIENE_AND_PURGE_PERFORMANCE_UNVALIDATED"
)
SERVICE_STATUS = (
    "STATIONARY_LOCAL_CLEARANCE_ONLY_REPLACEMENT_TRAJECTORY_STRAIN_RELIEF_AND_ACCESS_UNRESOLVED"
)
HYDRAULIC_STATUS = (
    "VALIDATION_GATED_MIXED_PHASE_AIR_LIQUID_CLEANSER_FOAM_CONTAMINANT_PUMP_BEHAVIOR_UNRESOLVED"
)
PHYSICAL_EVIDENCE_STATUS = (
    "DIGITAL_MIXED_WASTE_PUMP_PACKAGE_PORT_SUPPORT_DRAIN_DRY_AND_SERVICE_GEOMETRY_ONLY_NOT_"
    "SUPPLIER_SELECTION_MIXED_PHASE_FOAM_PRESSURE_FLOW_RECOVERY_LEAKAGE_ORIENTATION_"
    "CONTAINMENT_HYGIENE_DRYING_SERVICE_DURABILITY_ACOUSTICS_RUNTIME_OR_PHYSICAL_EVIDENCE"
)

_GIT_SHA_RE = re.compile(r"[0-9a-f]{40}\Z")
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


class RealizedWastePumpError(ValueError):
    pass


def _box(
    dx: float,
    dy: float,
    dz: float,
    center: tuple[float, float, float],
) -> cq.Workplane:
    return (
        cq.Workplane("XY")
        .box(dx, dy, dz, centered=(True, True, True))
        .translate(center)
    )


def _cylinder_from(
    start: tuple[float, float, float],
    direction: tuple[float, float, float],
    length_mm: float,
    diameter_mm: float,
) -> cq.Workplane:
    solid = cq.Solid.makeCylinder(
        diameter_mm / 2.0,
        length_mm,
        cq.Vector(*start),
        cq.Vector(*direction),
    )
    return cq.Workplane(obj=solid)


def _one_valid_solid(shape: cq.Workplane, label: str) -> None:
    if shape.solids().size() != 1 or not shape.val().isValid() or shape.val().Volume() <= 0.0:
        raise RealizedWastePumpError(
            f"{label} must be one valid positive deterministic solid"
        )


def _outside_volume(shape: cq.Workplane, envelope: cq.Workplane) -> float:
    return float(shape.val().cut(envelope.val()).Volume())


def _intersection_volume(a: cq.Workplane, b: cq.Workplane) -> float:
    return float(a.val().intersect(b.val()).Volume())


def _tuple3(value: tuple[float, float, float]) -> tuple[float, float, float]:
    return tuple(float(v) for v in value)


@dataclass(frozen=True, slots=True)
class WastePumpPortDatum:
    datum_id: str
    route_id: str
    role: str
    source_interface_id: str
    target_interface_id: str
    center_world_mm: tuple[float, float, float]
    axis_world: tuple[float, float, float]
    fluid_identity: str = PHASE_MIXED_WASTE
    lumen_diameter_seed_mm: float = PORT_LUMEN_DIAMETER_SEED_MM
    reservation_diameter_mm: float = PORT_RESERVATION_DIAMETER_MM
    reservation_projection_mm: float = PORT_RESERVATION_PROJECTION_MM
    status: str = PORT_STATUS

    def validate(self) -> None:
        expected = {
            "PUMP-STATION-WASTE-I26-INLET-ROUTE-ANCHOR": (
                ROUTE_ACQUISITION_TO_PUMP,
                "INLET",
                ROUTE_DESTINATION,
                STATION_WASTE,
                INLET_ROUTE_AXIS_WORLD,
            ),
            "WASTE_PUMP_OUTLET_ITERATION_26_INTERFACE": (
                ROUTE_PUMP_TO_BARRIER,
                "OUTLET",
                INTERFACE_PUMP_OUTLET,
                BARRIER_WASTE,
                OUTLET_ROUTE_AXIS_WORLD,
            ),
        }
        if self.datum_id not in expected:
            raise RealizedWastePumpError("unknown mixed-waste pump port datum")
        route_id, role, source, target, axis = expected[self.datum_id]
        if (
            self.route_id,
            self.role,
            self.source_interface_id,
            self.target_interface_id,
        ) != (route_id, role, source, target):
            raise RealizedWastePumpError(
                "mixed-waste pump port binding changed or bypasses controlled topology"
            )
        if self.fluid_identity != PHASE_MIXED_WASTE:
            raise RealizedWastePumpError("pump port must retain exact mixed-waste identity")
        if _tuple3(self.center_world_mm) != STATION_ROUTE_ANCHOR_WORLD_MM:
            raise RealizedWastePumpError(
                "pump port must remain on the released route station anchor"
            )
        if any(
            abs(float(a) - float(b)) > 1e-12
            for a, b in zip(self.axis_world, axis)
        ):
            raise RealizedWastePumpError("pump port route-anchor axis changed")
        if self.lumen_diameter_seed_mm != WASTE_ID_SEED_MM:
            raise RealizedWastePumpError(
                "pump port lumen seed must inherit released waste-route geometry"
            )
        if self.reservation_diameter_mm != PORT_RESERVATION_DIAMETER_MM:
            raise RealizedWastePumpError("pump port reservation diameter changed")
        if self.reservation_projection_mm != PORT_RESERVATION_PROJECTION_MM:
            raise RealizedWastePumpError("pump port reservation projection changed")
        if self.status != PORT_STATUS:
            raise RealizedWastePumpError("pump port evidence boundary changed")

    @property
    def lumen_area_seed_mm2(self) -> float:
        return math.pi * (self.lumen_diameter_seed_mm / 2.0) ** 2

    def manifest(self) -> dict[str, object]:
        self.validate()
        return {
            "datum_id": self.datum_id,
            "route_id": self.route_id,
            "role": self.role,
            "source_interface_id": self.source_interface_id,
            "target_interface_id": self.target_interface_id,
            "fluid_identity": self.fluid_identity,
            "center_world_mm": list(self.center_world_mm),
            "axis_world": list(self.axis_world),
            "lumen_diameter_seed_mm": self.lumen_diameter_seed_mm,
            "lumen_area_seed_mm2": self.lumen_area_seed_mm2,
            "reservation_diameter_mm": self.reservation_diameter_mm,
            "reservation_projection_mm": self.reservation_projection_mm,
            "selected_port_center_separation_mm": None,
            "selected_connector_standard": None,
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class RealizedWastePumpPackage:
    authored_against_git_sha: str
    source_backbone_authored_git_sha: str
    source_waste_pump_architecture_sha256: str
    source_backbone_realization_sha256: str
    source_authority_revision: str
    package_screening_solid: cq.Workplane
    support_cradle_solid: cq.Workplane
    inlet_port_reservation_solid: cq.Workplane
    outlet_port_reservation_solid: cq.Workplane
    drain_dry_clearance_solid: cq.Workplane
    service_clearance_solid: cq.Workplane
    port_datums: tuple[WastePumpPortDatum, ...]
    physical_validation_eligible: bool = False

    def validate(self) -> None:
        if _GIT_SHA_RE.fullmatch(self.authored_against_git_sha) is None:
            raise RealizedWastePumpError("authored Git SHA must be exact lowercase 40-hex")
        if self.authored_against_git_sha != AUTHORED_AGAINST_MAIN_SHA:
            raise RealizedWastePumpError("waste-pump package is stale for its authored main")
        if _GIT_SHA_RE.fullmatch(self.source_backbone_authored_git_sha) is None:
            raise RealizedWastePumpError("backbone Git SHA must be exact lowercase 40-hex")
        for value, label in (
            (self.source_waste_pump_architecture_sha256, "waste architecture"),
            (self.source_backbone_realization_sha256, "waste backbone"),
        ):
            if _SHA256_RE.fullmatch(value) is None:
                raise RealizedWastePumpError(f"{label} digest must be exact lowercase SHA-256")
        if self.source_authority_revision != "2026-08-30-R1":
            raise RealizedWastePumpError("waste-pump authority revision changed")
        if self.physical_validation_eligible:
            raise RealizedWastePumpError("digital pump geometry cannot be physical evidence")

        for shape, label in (
            (self.package_screening_solid, "package screening envelope"),
            (self.support_cradle_solid, "support cradle"),
            (self.inlet_port_reservation_solid, "inlet port reservation"),
            (self.outlet_port_reservation_solid, "outlet port reservation"),
            (self.drain_dry_clearance_solid, "drain/dry clearance"),
            (self.service_clearance_solid, "service clearance"),
        ):
            _one_valid_solid(shape, label)

        if type(self.port_datums) is not tuple or len(self.port_datums) != 2:
            raise RealizedWastePumpError("mixed-waste pump must expose exactly two route port datums")
        for datum in self.port_datums:
            if type(datum) is not WastePumpPortDatum:
                raise RealizedWastePumpError("port datums must use exact WastePumpPortDatum")
            datum.validate()

        if _outside_volume(self.package_screening_solid, self.service_clearance_solid) > 1e-7:
            raise RealizedWastePumpError("package screening envelope escapes local service reservation")
        if _outside_volume(self.support_cradle_solid, self.service_clearance_solid) > 1e-7:
            raise RealizedWastePumpError("support cradle escapes local service reservation")
        if _outside_volume(self.drain_dry_clearance_solid, self.service_clearance_solid) > 1e-7:
            raise RealizedWastePumpError("drain/dry corridor escapes local service reservation")
        if _intersection_volume(self.drain_dry_clearance_solid, self.support_cradle_solid) > 1e-7:
            raise RealizedWastePumpError("low-point drain/dry corridor is blocked by cradle material")
        if _intersection_volume(self.drain_dry_clearance_solid, self.package_screening_solid) > 1e-7:
            raise RealizedWastePumpError("low-point drain/dry corridor is blocked by package envelope")

    def validate_current_backbone(self, release: Cell4WasteBackboneRelease) -> None:
        self.validate()
        if type(release) is not Cell4WasteBackboneRelease:
            raise RealizedWastePumpError("source release must use exact Cell4WasteBackboneRelease")
        release.validate_invariants()
        realization = release.realization
        if self.source_backbone_authored_git_sha != release.authored_against_git_sha:
            raise RealizedWastePumpError("waste-pump package is stale for backbone Git provenance")
        if (
            self.source_waste_pump_architecture_sha256
            != release.source_waste_pump_architecture_sha256
        ):
            raise RealizedWastePumpError("waste-pump package is stale for waste architecture")
        if self.source_backbone_realization_sha256 != realization.manifest_sha256:
            raise RealizedWastePumpError("waste-pump package is stale for realized waste backbone")
        if self.source_authority_revision != realization.authority_revision:
            raise RealizedWastePumpError("waste-pump package is stale for authority revision")

        route_a, route_b, route_c = realization.routes
        inlet_anchor = route_a.centerline[-1].end.as_tuple()
        outlet_anchor = route_b.centerline[0].start.as_tuple()
        if _tuple3(inlet_anchor) != STATION_ROUTE_ANCHOR_WORLD_MM:
            raise RealizedWastePumpError("released acquisition route moved from package station")
        if _tuple3(outlet_anchor) != STATION_ROUTE_ANCHOR_WORLD_MM:
            raise RealizedWastePumpError("released pump outlet route moved from package station")
        if route_c.source_interface_id != "WASTE_BACKFLOW_BARRIER_OUTLET_ITERATION_26_INTERFACE":
            raise RealizedWastePumpError("passive-backflow downstream handoff changed")
        if any(route.fluid_identity != PHASE_MIXED_WASTE for route in realization.routes):
            raise RealizedWastePumpError("released waste routes lost exact mixed-waste identity")

    @property
    def manifest_sha256(self) -> str:
        raw = json.dumps(
            self.manifest(include_sha=False),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        self.validate()
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "world_frame_id": WORLD_FRAME_ID,
            "authored_against_git_sha": self.authored_against_git_sha,
            "source_backbone_authored_git_sha": self.source_backbone_authored_git_sha,
            "source_waste_pump_architecture_blob_sha": SOURCE_WASTE_PUMP_ARCHITECTURE_BLOB_SHA,
            "source_realized_waste_backbone_blob_sha": SOURCE_REALIZED_WASTE_BACKBONE_BLOB_SHA,
            "source_waste_pump_architecture_sha256": self.source_waste_pump_architecture_sha256,
            "source_backbone_realization_sha256": self.source_backbone_realization_sha256,
            "source_authority_revision": self.source_authority_revision,
            "station_id": STATION_WASTE,
            "fluid_identity": PHASE_MIXED_WASTE,
            "mixed_phase_constituents_for_physical_reasoning": list(MIXED_PHASE_CONSTITUENTS),
            "package": {
                "package_id": PACKAGE_ID,
                "center_world_mm": list(PACKAGE_CENTER_WORLD_MM),
                "envelope_xyz_mm": list(PACKAGE_ENVELOPE_XYZ_MM),
                "bounds_world_mm": {
                    axis: list(bounds) for axis, bounds in PACKAGE_BOUNDS_WORLD_MM.items()
                },
                "supplier_candidate": None,
                "selected_internal_wet_path_geometry": None,
                "status": PACKAGE_STATUS,
            },
            "route_station_anchor_world_mm": list(STATION_ROUTE_ANCHOR_WORLD_MM),
            "ports": [datum.manifest() for datum in self.port_datums],
            "support": {
                "cavity_classification": SUPPORT_CAVITY_CLASSIFICATION,
                "package_base_gap_seed_mm": SUPPORT_PACKAGE_BASE_GAP_SEED_MM,
                "status": SUPPORT_STATUS,
            },
            "drain_dry": {
                "center_world_mm": list(DRAIN_DRY_CLEARANCE_CENTER_WORLD_MM),
                "clearance_xyz_mm": list(DRAIN_DRY_CLEARANCE_XYZ_MM),
                "status": DRAIN_DRY_STATUS,
            },
            "service": {
                "center_world_mm": list(SERVICE_CLEARANCE_CENTER_WORLD_MM),
                "clearance_xyz_mm": list(SERVICE_CLEARANCE_XYZ_MM),
                "bounds_world_mm": {
                    axis: list(bounds)
                    for axis, bounds in SERVICE_CLEARANCE_BOUNDS_WORLD_MM.items()
                },
                "local_stationary_clearance_seed_mm": LOCAL_STATIONARY_CLEARANCE_SEED_MM,
                "replacement_trajectory": None,
                "status": SERVICE_STATUS,
            },
            "topology_guard": {
                "ordered_stages": [
                    "ACQUISITION_TO_PUMP",
                    "PUMP_TO_PASSIVE_BACKFLOW_BARRIER",
                    "PASSIVE_BACKFLOW_BARRIER_TO_CARTRIDGE_HANDOFF",
                ],
                "passive_backflow_component_geometry": None,
                "passive_backflow_performance": "VALIDATION_GATED",
            },
            "hydraulic_status": HYDRAULIC_STATUS,
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": PHYSICAL_EVIDENCE_STATUS,
        }
        if include_sha:
            payload["manifest_sha256"] = self.manifest_sha256
        return payload


def _build_support_cradle() -> cq.Workplane:
    rails = [
        _box(
            *SUPPORT_RAIL_XYZ_MM,
            (
                SUPPORT_RAIL_CENTER_X_MM,
                center_y,
                SUPPORT_RAIL_CENTER_Z_MM,
            ),
        )
        for center_y in SUPPORT_RAIL_CENTER_Y_MM
    ]
    crossbar = _box(
        *SUPPORT_CROSSBAR_XYZ_MM,
        SUPPORT_CROSSBAR_CENTER_WORLD_MM,
    )
    return rails[0].union(rails[1]).union(crossbar)


def build_realized_waste_pump_package(
    release: Cell4WasteBackboneRelease | None = None,
) -> RealizedWastePumpPackage:
    release = release or build_current_cell4_waste_backbone_release()
    release.validate_invariants()

    inlet_axis_back_to_route = tuple(-v for v in INLET_ROUTE_AXIS_WORLD)
    result = RealizedWastePumpPackage(
        authored_against_git_sha=AUTHORED_AGAINST_MAIN_SHA,
        source_backbone_authored_git_sha=release.authored_against_git_sha,
        source_waste_pump_architecture_sha256=release.source_waste_pump_architecture_sha256,
        source_backbone_realization_sha256=release.realization.manifest_sha256,
        source_authority_revision=release.realization.authority_revision,
        package_screening_solid=_box(
            *PACKAGE_ENVELOPE_XYZ_MM,
            PACKAGE_CENTER_WORLD_MM,
        ),
        support_cradle_solid=_build_support_cradle(),
        inlet_port_reservation_solid=_cylinder_from(
            STATION_ROUTE_ANCHOR_WORLD_MM,
            inlet_axis_back_to_route,
            PORT_RESERVATION_PROJECTION_MM,
            PORT_RESERVATION_DIAMETER_MM,
        ),
        outlet_port_reservation_solid=_cylinder_from(
            STATION_ROUTE_ANCHOR_WORLD_MM,
            OUTLET_ROUTE_AXIS_WORLD,
            PORT_RESERVATION_PROJECTION_MM,
            PORT_RESERVATION_DIAMETER_MM,
        ),
        drain_dry_clearance_solid=_box(
            *DRAIN_DRY_CLEARANCE_XYZ_MM,
            DRAIN_DRY_CLEARANCE_CENTER_WORLD_MM,
        ),
        service_clearance_solid=_box(
            *SERVICE_CLEARANCE_XYZ_MM,
            SERVICE_CLEARANCE_CENTER_WORLD_MM,
        ),
        port_datums=(
            WastePumpPortDatum(
                datum_id="PUMP-STATION-WASTE-I26-INLET-ROUTE-ANCHOR",
                route_id=ROUTE_ACQUISITION_TO_PUMP,
                role="INLET",
                source_interface_id=ROUTE_DESTINATION,
                target_interface_id=STATION_WASTE,
                center_world_mm=STATION_ROUTE_ANCHOR_WORLD_MM,
                axis_world=INLET_ROUTE_AXIS_WORLD,
            ),
            WastePumpPortDatum(
                datum_id=INTERFACE_PUMP_OUTLET,
                route_id=ROUTE_PUMP_TO_BARRIER,
                role="OUTLET",
                source_interface_id=INTERFACE_PUMP_OUTLET,
                target_interface_id=BARRIER_WASTE,
                center_world_mm=STATION_ROUTE_ANCHOR_WORLD_MM,
                axis_world=OUTLET_ROUTE_AXIS_WORLD,
            ),
        ),
    )
    result.validate_current_backbone(release)
    return result
