"""Source-bound honest package/interface realization for the passive mixed-waste backflow stage.

Released waste routing already requires acquisition -> waste pump -> passive backflow
protection -> cartridge, but the passive device remains unselected. This module therefore
adds only a world-coordinate dimensional screening envelope, co-located route-graph
interface datums, an open WET_DRAINABLE local support cradle, an explicit low-point
drain/dry free-space corridor, and a stationary service reservation.

Nothing here selects a valve or proves reverse-flow blocking, cracking pressure, leakage,
mixed-phase/foam handling, orientation behavior, hygiene, drying, durability, or service
performance.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1, sha256
import json
import math
from pathlib import Path

import cadquery as cq

from .realized_waste_backbone import WASTE_ID_SEED_MM
from .realized_waste_backbone_release import (
    Cell4WasteBackboneRelease,
    build_current_cell4_waste_backbone_release,
)
from .waste_acquisition import PHASE_MIXED_WASTE
from .waste_pump_architecture import (
    BARRIER_PERFORMANCE_STATUS,
    BARRIER_SELECTION_STATUS,
    BARRIER_WASTE,
    INTERFACE_BARRIER_OUTLET,
    INTERFACE_CARTRIDGE_INLET_I27,
    INTERFACE_PUMP_OUTLET,
    ROUTE_BARRIER_TO_CARTRIDGE,
    ROUTE_PUMP_TO_BARRIER,
)

WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
AUTHORED_AGAINST_MAIN_SHA = "21cf8c4fb8ca0d20ddb58f90bcee6275bc98ca30"
SOURCE_WASTE_PUMP_ARCHITECTURE_BLOB_SHA = "ace02ee529070465b11832f475771125636312cb"
SOURCE_REALIZED_WASTE_BACKBONE_BLOB_SHA = "6aa79d9a613e278f32da85b4654c0e35cc09b7ca"
SOURCE_REALIZED_WASTE_RELEASE_BLOB_SHA = "86f2b12d8721ce0fb233d7b026aed3154de9c964"
SCHEMA = "MASCK_ONE_CELL4_REALIZED_PASSIVE_BACKFLOW_PACKAGE_V1"

MIXED_PHASE_CONSTITUENTS = ("AIR", "LIQUID", "CLEANSER", "FOAM", "CONTAMINANT")
PACKAGE_ID = "PASSIVE-BACKFLOW-BARRIER-WASTE-I26-CELL4-PROVISIONAL-PACKAGE"
PACKAGE_CENTER_WORLD_MM = (-49.0, -62.0, 13.0)
PACKAGE_ENVELOPE_XYZ_MM = (6.0, 8.0, 6.0)
PACKAGE_BOUNDS_WORLD_MM = {
    "x": (-52.0, -46.0),
    "y": (-66.0, -58.0),
    "z": (10.0, 16.0),
}
ROUTE_GRAPH_ANCHOR_WORLD_MM = (-51.0, -58.0, 16.0)
ROUTE_AXIS_WORLD = (0.0, -1.0, 0.0)

# The route graph collapses the passive stage to one station point. These short solids are
# therefore route-anchor occupancy references only; they do not invent selected device
# port spacing or connector geometry.
ROUTE_INTERFACE_RESERVATION_DIAMETER_MM = 3.2
ROUTE_INTERFACE_PROJECTION_MM = 2.0
ROUTE_LUMEN_DIAMETER_SEED_MM = WASTE_ID_SEED_MM
UPSTREAM_REFERENCE_START_WORLD_MM = (-51.0, -56.0, 16.0)
DOWNSTREAM_REFERENCE_START_WORLD_MM = ROUTE_GRAPH_ANCHOR_WORLD_MM

# One connected open-U saddle under the screening envelope. The package is intentionally
# separated from the saddle by a provisional 0.5 mm base gap; frame join and retention are
# unresolved. The support has no enclosed local wet pocket.
SUPPORT_RAIL_XYZ_MM = (1.0, 9.0, 1.0)
SUPPORT_RAIL_CENTER_X_MM = (-50.5, -47.5)
SUPPORT_RAIL_CENTER_Y_MM = -62.0
SUPPORT_RAIL_CENTER_Z_MM = 9.0
SUPPORT_CROSSBAR_XYZ_MM = (4.0, 1.0, 1.0)
SUPPORT_CROSSBAR_CENTER_WORLD_MM = (-49.0, -66.0, 9.0)
SUPPORT_PACKAGE_BASE_GAP_SEED_MM = 0.5
SUPPORT_CAVITY_CLASSIFICATION = "WET_DRAINABLE"

# Free-space corridor between the two support rails, open toward +Y. It is a geometric
# drainage/drying path reservation, not evidence of drying time or hygiene performance.
DRAIN_DRY_CLEARANCE_CENTER_WORLD_MM = (-49.0, -61.5, 9.75)
DRAIN_DRY_CLEARANCE_XYZ_MM = (2.0, 8.0, 0.4)

# Stationary local free-space reservation only. No replacement trajectory is claimed.
SERVICE_CLEARANCE_CENTER_WORLD_MM = (-49.0, -61.0, 13.0)
SERVICE_CLEARANCE_XYZ_MM = (8.0, 12.0, 10.0)
SERVICE_CLEARANCE_BOUNDS_WORLD_MM = {
    "x": (-53.0, -45.0),
    "y": (-67.0, -55.0),
    "z": (8.0, 18.0),
}
LOCAL_STATIONARY_CLEARANCE_SEED_MM = 1.0

PACKAGE_STATUS = (
    "CELL4_PROVISIONAL_PASSIVE_BACKFLOW_DIMENSIONAL_SCREENING_ENVELOPE_NOT_COMPONENT_SELECTED"
)
INTERFACE_STATUS = (
    "COLOCATED_RELEASED_ROUTE_GRAPH_DATUMS_SELECTED_DEVICE_PORT_SEPARATION_CONNECTOR_AND_WET_PATH_UNRESOLVED"
)
SUPPORT_STATUS = (
    "OPEN_WET_DRAINABLE_LOCAL_SADDLE_FRAME_JOIN_RETENTION_AND_MATERIAL_UNRESOLVED"
)
DRAIN_DRY_STATUS = (
    "LOW_POINT_OPEN_CLEARANCE_CORRIDOR_ONLY_DRYING_TIME_HYGIENE_AND_PURGE_PERFORMANCE_UNVALIDATED"
)
SERVICE_STATUS = (
    "STATIONARY_LOCAL_CLEARANCE_ONLY_REPLACEMENT_TRAJECTORY_STRAIN_RELIEF_AND_ACCESS_UNRESOLVED"
)
PHYSICAL_EVIDENCE_STATUS = (
    "DIGITAL_PASSIVE_BACKFLOW_PACKAGE_INTERFACE_SUPPORT_DRAIN_DRY_AND_SERVICE_GEOMETRY_ONLY_NOT_"
    "COMPONENT_SELECTION_REVERSE_FLOW_CRACKING_PRESSURE_LEAKAGE_MIXED_PHASE_FOAM_ORIENTATION_"
    "CONTAINMENT_HYGIENE_DRYING_SERVICE_DURABILITY_OR_PHYSICAL_EVIDENCE"
)


class RealizedPassiveBackflowError(ValueError):
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
        raise RealizedPassiveBackflowError(
            f"{label} must be one valid positive deterministic solid"
        )


def _outside_volume(shape: cq.Workplane, envelope: cq.Workplane) -> float:
    return float(shape.val().cut(envelope.val()).Volume())


def _intersection_volume(a: cq.Workplane, b: cq.Workplane) -> float:
    return float(a.val().intersect(b.val()).Volume())


def _git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    header = f"blob {len(raw)}\0".encode("ascii")
    return sha1(header + raw).hexdigest()


def _assert_source_blobs() -> None:
    expected = {
        "waste_pump_architecture.py": SOURCE_WASTE_PUMP_ARCHITECTURE_BLOB_SHA,
        "realized_waste_backbone.py": SOURCE_REALIZED_WASTE_BACKBONE_BLOB_SHA,
        "realized_waste_backbone_release.py": SOURCE_REALIZED_WASTE_RELEASE_BLOB_SHA,
    }
    for filename, expected_sha in expected.items():
        observed = _git_blob_sha(Path(__file__).with_name(filename))
        if observed != expected_sha:
            raise RealizedPassiveBackflowError(
                f"{filename} changed; passive-backflow package requires explicit source rebind"
            )


def _point_tuple(point: object) -> tuple[float, float, float]:
    try:
        return (float(point.x), float(point.y), float(point.z))
    except (AttributeError, TypeError, ValueError) as exc:
        raise RealizedPassiveBackflowError("route endpoint must expose finite xyz coordinates") from exc


@dataclass(frozen=True, slots=True)
class PassiveBackflowInterfaceDatum:
    datum_id: str
    route_id: str
    role: str
    source_interface_id: str
    target_interface_id: str
    center_world_mm: tuple[float, float, float]
    axis_world: tuple[float, float, float]
    fluid_identity: str = PHASE_MIXED_WASTE
    lumen_diameter_seed_mm: float = ROUTE_LUMEN_DIAMETER_SEED_MM
    reservation_diameter_mm: float = ROUTE_INTERFACE_RESERVATION_DIAMETER_MM
    selected_port_separation_mm: None = None
    connector_standard: None = None
    status: str = INTERFACE_STATUS

    def validate(self) -> None:
        if self.fluid_identity != PHASE_MIXED_WASTE:
            raise RealizedPassiveBackflowError("passive-backflow interface lost mixed-waste identity")
        if tuple(float(v) for v in self.center_world_mm) != ROUTE_GRAPH_ANCHOR_WORLD_MM:
            raise RealizedPassiveBackflowError("passive-backflow interface moved off released route anchor")
        if tuple(float(v) for v in self.axis_world) != ROUTE_AXIS_WORLD:
            raise RealizedPassiveBackflowError("passive-backflow interface axis changed")
        if self.lumen_diameter_seed_mm != ROUTE_LUMEN_DIAMETER_SEED_MM:
            raise RealizedPassiveBackflowError("passive-backflow interface changed route lumen seed")
        if self.reservation_diameter_mm != ROUTE_INTERFACE_RESERVATION_DIAMETER_MM:
            raise RealizedPassiveBackflowError("passive-backflow interface reservation changed")
        if self.selected_port_separation_mm is not None or self.connector_standard is not None:
            raise RealizedPassiveBackflowError("selected device port spacing/connectors cannot be invented")
        if self.status != INTERFACE_STATUS:
            raise RealizedPassiveBackflowError("passive-backflow interface evidence state changed")

        expected = {
            "PASSIVE-BACKFLOW-UPSTREAM-ROUTE-ANCHOR-CELL4": (
                ROUTE_PUMP_TO_BARRIER,
                INTERFACE_PUMP_OUTLET,
                BARRIER_WASTE,
            ),
            "PASSIVE-BACKFLOW-DOWNSTREAM-ROUTE-ANCHOR-CELL4": (
                ROUTE_BARRIER_TO_CARTRIDGE,
                INTERFACE_BARRIER_OUTLET,
                INTERFACE_CARTRIDGE_INLET_I27,
            ),
        }
        if self.datum_id not in expected:
            raise RealizedPassiveBackflowError("unknown passive-backflow interface datum")
        if (
            self.route_id,
            self.source_interface_id,
            self.target_interface_id,
        ) != expected[self.datum_id]:
            raise RealizedPassiveBackflowError(
                "passive-backflow interface route/source/target binding changed"
            )

    def manifest(self) -> dict[str, object]:
        self.validate()
        return {
            "datum_id": self.datum_id,
            "route_id": self.route_id,
            "role": self.role,
            "source_interface_id": self.source_interface_id,
            "target_interface_id": self.target_interface_id,
            "center_world_mm": list(self.center_world_mm),
            "axis_world": list(self.axis_world),
            "fluid_identity": self.fluid_identity,
            "lumen_diameter_seed_mm": self.lumen_diameter_seed_mm,
            "lumen_area_seed_mm2": math.pi * (self.lumen_diameter_seed_mm / 2.0) ** 2,
            "reservation_diameter_mm": self.reservation_diameter_mm,
            "selected_port_separation_mm": None,
            "connector_standard": None,
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class RealizedPassiveBackflowPackage:
    source_authority_revision: str
    source_waste_pump_architecture_sha256: str
    source_backbone_realization_sha256: str
    authored_against_git_sha: str
    package_screening_solid: cq.Workplane
    support_cradle_solid: cq.Workplane
    upstream_route_anchor_solid: cq.Workplane
    downstream_route_anchor_solid: cq.Workplane
    drain_dry_clearance_solid: cq.Workplane
    service_clearance_solid: cq.Workplane
    interface_datums: tuple[PassiveBackflowInterfaceDatum, ...]
    fluid_identity: str = PHASE_MIXED_WASTE
    world_frame_id: str = WORLD_FRAME_ID
    barrier_id: str = BARRIER_WASTE
    package_id: str = PACKAGE_ID
    selected_component_id: None = None
    selected_component_evidence_sha256: None = None
    selected_component_geometry: None = None
    cracking_pressure_kPa: None = None
    reverse_leakage_mL_min: None = None
    support_cavity_classification: str = SUPPORT_CAVITY_CLASSIFICATION
    physical_validation_eligible: bool = False
    package_status: str = PACKAGE_STATUS
    selection_status: str = BARRIER_SELECTION_STATUS
    performance_status: str = BARRIER_PERFORMANCE_STATUS
    support_status: str = SUPPORT_STATUS
    drain_dry_status: str = DRAIN_DRY_STATUS
    service_status: str = SERVICE_STATUS
    evidence_status: str = PHYSICAL_EVIDENCE_STATUS

    def validate_invariants(self) -> None:
        _assert_source_blobs()
        if self.fluid_identity != PHASE_MIXED_WASTE:
            raise RealizedPassiveBackflowError("passive-backflow package must retain mixed-waste identity")
        if self.world_frame_id != WORLD_FRAME_ID:
            raise RealizedPassiveBackflowError("passive-backflow package must use authority world frame")
        if self.barrier_id != BARRIER_WASTE or self.package_id != PACKAGE_ID:
            raise RealizedPassiveBackflowError("passive-backflow package identity changed")
        if self.authored_against_git_sha != AUTHORED_AGAINST_MAIN_SHA:
            raise RealizedPassiveBackflowError("passive-backflow authored-against main provenance changed")
        if len(self.source_waste_pump_architecture_sha256) != 64:
            raise RealizedPassiveBackflowError("waste-pump architecture digest must be SHA-256")
        if len(self.source_backbone_realization_sha256) != 64:
            raise RealizedPassiveBackflowError("backbone realization digest must be SHA-256")
        if not self.source_authority_revision:
            raise RealizedPassiveBackflowError("authority revision provenance is required")

        if any(
            value is not None
            for value in (
                self.selected_component_id,
                self.selected_component_evidence_sha256,
                self.selected_component_geometry,
                self.cracking_pressure_kPa,
                self.reverse_leakage_mL_min,
            )
        ):
            raise RealizedPassiveBackflowError(
                "passive-backflow realization cannot invent component selection or performance"
            )
        if self.selection_status != BARRIER_SELECTION_STATUS:
            raise RealizedPassiveBackflowError("passive-backflow selection must remain unresolved")
        if self.performance_status != BARRIER_PERFORMANCE_STATUS:
            raise RealizedPassiveBackflowError("passive-backflow performance must remain validation gated")
        if self.support_cavity_classification != SUPPORT_CAVITY_CLASSIFICATION:
            raise RealizedPassiveBackflowError("local support hygiene class changed")
        if self.physical_validation_eligible:
            raise RealizedPassiveBackflowError("digital passive-backflow package is not physical evidence")
        if (
            self.package_status != PACKAGE_STATUS
            or self.support_status != SUPPORT_STATUS
            or self.drain_dry_status != DRAIN_DRY_STATUS
            or self.service_status != SERVICE_STATUS
            or self.evidence_status != PHYSICAL_EVIDENCE_STATUS
        ):
            raise RealizedPassiveBackflowError("passive-backflow evidence firewall changed")

        if type(self.interface_datums) is not tuple or len(self.interface_datums) != 2:
            raise RealizedPassiveBackflowError("passive-backflow package requires two route-graph datums")
        for datum in self.interface_datums:
            if type(datum) is not PassiveBackflowInterfaceDatum:
                raise RealizedPassiveBackflowError("passive-backflow datum type changed")
            datum.validate()

        for label, shape in (
            ("package screening envelope", self.package_screening_solid),
            ("support cradle", self.support_cradle_solid),
            ("upstream route anchor", self.upstream_route_anchor_solid),
            ("downstream route anchor", self.downstream_route_anchor_solid),
            ("drain/dry clearance", self.drain_dry_clearance_solid),
            ("service clearance", self.service_clearance_solid),
        ):
            _one_valid_solid(shape, label)

        if _intersection_volume(self.package_screening_solid, self.support_cradle_solid) > 1e-7:
            raise RealizedPassiveBackflowError("package screening envelope intersects support cradle")
        if _intersection_volume(self.drain_dry_clearance_solid, self.package_screening_solid) > 1e-7:
            raise RealizedPassiveBackflowError("drain/dry corridor intersects package screening envelope")
        if _intersection_volume(self.drain_dry_clearance_solid, self.support_cradle_solid) > 1e-7:
            raise RealizedPassiveBackflowError("drain/dry corridor intersects support material")

        for label, shape in (
            ("package", self.package_screening_solid),
            ("support", self.support_cradle_solid),
            ("upstream route anchor", self.upstream_route_anchor_solid),
            ("downstream route anchor", self.downstream_route_anchor_solid),
            ("drain/dry corridor", self.drain_dry_clearance_solid),
        ):
            if _outside_volume(shape, self.service_clearance_solid) > 1e-7:
                raise RealizedPassiveBackflowError(
                    f"{label} escapes stationary passive-backflow service reservation"
                )

    def validate_source_release(self, release: Cell4WasteBackboneRelease) -> None:
        self.validate_invariants()
        if type(release) is not Cell4WasteBackboneRelease:
            raise RealizedPassiveBackflowError("source must use exact Cell4WasteBackboneRelease type")
        release.validate_invariants()
        if self.source_waste_pump_architecture_sha256 != release.source_waste_pump_architecture_sha256:
            raise RealizedPassiveBackflowError(
                "passive-backflow package is stale for released waste-pump architecture"
            )
        if self.source_backbone_realization_sha256 != release.realization.manifest_sha256:
            raise RealizedPassiveBackflowError(
                "passive-backflow package is stale for released world-coordinate backbone"
            )
        if self.source_authority_revision != release.realization.authority_revision:
            raise RealizedPassiveBackflowError(
                "passive-backflow package is stale for released authority revision"
            )

        by_id = {route.route_id: route for route in release.realization.routes}
        if set(by_id) != {
            "ROUTE-WASTE-ACQUISITION-TO-PUMP-I26",
            ROUTE_PUMP_TO_BARRIER,
            ROUTE_BARRIER_TO_CARTRIDGE,
        }:
            raise RealizedPassiveBackflowError("released waste route set changed")
        upstream = by_id[ROUTE_PUMP_TO_BARRIER]
        downstream = by_id[ROUTE_BARRIER_TO_CARTRIDGE]
        if upstream.fluid_identity != PHASE_MIXED_WASTE or downstream.fluid_identity != PHASE_MIXED_WASTE:
            raise RealizedPassiveBackflowError("released barrier-adjacent routes lost mixed-waste identity")
        if upstream.target_interface_id != BARRIER_WASTE:
            raise RealizedPassiveBackflowError("released pump-to-barrier route no longer terminates at barrier")
        if downstream.source_interface_id != INTERFACE_BARRIER_OUTLET:
            raise RealizedPassiveBackflowError("released barrier-to-cartridge route no longer begins at barrier outlet")

        upstream_end = _point_tuple(upstream.centerline[-1].end)
        downstream_start = _point_tuple(downstream.centerline[0].start)
        if upstream_end != ROUTE_GRAPH_ANCHOR_WORLD_MM or downstream_start != ROUTE_GRAPH_ANCHOR_WORLD_MM:
            raise RealizedPassiveBackflowError(
                "released passive-backflow route graph anchor moved; package requires explicit re-placement"
            )

    @property
    def package_envelope_volume_mm3(self) -> float:
        return math.prod(PACKAGE_ENVELOPE_XYZ_MM)

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        self.validate_invariants()
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "source_authority_revision": self.source_authority_revision,
            "source_waste_pump_architecture_sha256": self.source_waste_pump_architecture_sha256,
            "source_backbone_realization_sha256": self.source_backbone_realization_sha256,
            "authored_against_git_sha": self.authored_against_git_sha,
            "authored_against_git_sha_role": "HISTORICAL_PROVENANCE_NOT_RELEASE_FRESHNESS_PROOF",
            "source_blob_bindings": {
                "waste_pump_architecture.py": SOURCE_WASTE_PUMP_ARCHITECTURE_BLOB_SHA,
                "realized_waste_backbone.py": SOURCE_REALIZED_WASTE_BACKBONE_BLOB_SHA,
                "realized_waste_backbone_release.py": SOURCE_REALIZED_WASTE_RELEASE_BLOB_SHA,
            },
            "world_frame_id": self.world_frame_id,
            "barrier_id": self.barrier_id,
            "fluid_identity": self.fluid_identity,
            "mixed_phase_constituents": list(MIXED_PHASE_CONSTITUENTS),
            "topology_order": [
                "ACQUISITION",
                "WASTE_PUMP",
                "PASSIVE_BACKFLOW_PROTECTION",
                "CARTRIDGE",
            ],
            "package": {
                "package_id": self.package_id,
                "center_world_mm": list(PACKAGE_CENTER_WORLD_MM),
                "envelope_xyz_mm": list(PACKAGE_ENVELOPE_XYZ_MM),
                "bounds_world_mm": {key: list(value) for key, value in PACKAGE_BOUNDS_WORLD_MM.items()},
                "geometric_screening_volume_mm3": self.package_envelope_volume_mm3,
                "selected_component_id": None,
                "selected_component_evidence_sha256": None,
                "selected_component_geometry": None,
                "status": self.package_status,
            },
            "route_graph_anchor": {
                "center_world_mm": list(ROUTE_GRAPH_ANCHOR_WORLD_MM),
                "axis_world": list(ROUTE_AXIS_WORLD),
                "route_lumen_diameter_seed_mm": ROUTE_LUMEN_DIAMETER_SEED_MM,
                "route_lumen_area_seed_mm2": math.pi * (ROUTE_LUMEN_DIAMETER_SEED_MM / 2.0) ** 2,
                "interface_reservation_diameter_mm": ROUTE_INTERFACE_RESERVATION_DIAMETER_MM,
                "interface_projection_mm": ROUTE_INTERFACE_PROJECTION_MM,
                "selected_device_port_separation_mm": None,
                "connector_standard": None,
                "co_located_graph_interfaces": True,
                "co_location_reason": (
                    "RELEASED_BACKBONE_COLLAPSES_PASSIVE_DEVICE_TO_ONE_LOGICAL_ROUTE_STATION; "
                    "SELECTED_DEVICE_MUST_RESEGMENT_PORT_DATUMS"
                ),
            },
            "interface_datums": [datum.manifest() for datum in self.interface_datums],
            "support": {
                "architecture": "OPEN_U_SADDLE_ONE_CONNECTED_SOLID",
                "rail_xyz_mm": list(SUPPORT_RAIL_XYZ_MM),
                "rail_center_x_mm": list(SUPPORT_RAIL_CENTER_X_MM),
                "rail_center_y_mm": SUPPORT_RAIL_CENTER_Y_MM,
                "rail_center_z_mm": SUPPORT_RAIL_CENTER_Z_MM,
                "crossbar_xyz_mm": list(SUPPORT_CROSSBAR_XYZ_MM),
                "crossbar_center_world_mm": list(SUPPORT_CROSSBAR_CENTER_WORLD_MM),
                "package_base_gap_seed_mm": SUPPORT_PACKAGE_BASE_GAP_SEED_MM,
                "cavity_classification": self.support_cavity_classification,
                "selected_device_internal_cavity_geometry": None,
                "frame_join_geometry": None,
                "retention_geometry": None,
                "status": self.support_status,
            },
            "drain_dry": {
                "center_world_mm": list(DRAIN_DRY_CLEARANCE_CENTER_WORLD_MM),
                "xyz_mm": list(DRAIN_DRY_CLEARANCE_XYZ_MM),
                "path": "OPEN_TOWARD_POSITIVE_Y_BETWEEN_SUPPORT_RAILS",
                "status": self.drain_dry_status,
            },
            "service_clearance": {
                "local_stationary_clearance_seed_mm": LOCAL_STATIONARY_CLEARANCE_SEED_MM,
                "center_world_mm": list(SERVICE_CLEARANCE_CENTER_WORLD_MM),
                "xyz_mm": list(SERVICE_CLEARANCE_XYZ_MM),
                "bounds_world_mm": {
                    key: list(value) for key, value in SERVICE_CLEARANCE_BOUNDS_WORLD_MM.items()
                },
                "replacement_trajectory_world_mm": None,
                "status": self.service_status,
            },
            "selection_status": self.selection_status,
            "performance_status": self.performance_status,
            "performance_claims": {
                "reverse_flow_blocking_validated": False,
                "cracking_pressure_kPa": None,
                "reverse_leakage_mL_min": None,
                "mixed_phase_foam_behavior": None,
                "orientation_independence": None,
                "recovery": None,
                "containment": None,
                "hygiene": None,
                "drying_time": None,
                "durability": None,
            },
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            payload["manifest_sha256"] = self.manifest_sha256
        return payload

    @property
    def manifest_sha256(self) -> str:
        payload = self.manifest(include_sha=False)
        return sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()


def build_realized_passive_backflow_package(
    release: Cell4WasteBackboneRelease,
) -> RealizedPassiveBackflowPackage:
    if type(release) is not Cell4WasteBackboneRelease:
        raise RealizedPassiveBackflowError("release must use exact Cell4WasteBackboneRelease type")
    release.validate_invariants()

    package = _box(*PACKAGE_ENVELOPE_XYZ_MM, PACKAGE_CENTER_WORLD_MM)
    rail_left = _box(
        *SUPPORT_RAIL_XYZ_MM,
        (
            SUPPORT_RAIL_CENTER_X_MM[0],
            SUPPORT_RAIL_CENTER_Y_MM,
            SUPPORT_RAIL_CENTER_Z_MM,
        ),
    )
    rail_right = _box(
        *SUPPORT_RAIL_XYZ_MM,
        (
            SUPPORT_RAIL_CENTER_X_MM[1],
            SUPPORT_RAIL_CENTER_Y_MM,
            SUPPORT_RAIL_CENTER_Z_MM,
        ),
    )
    crossbar = _box(*SUPPORT_CROSSBAR_XYZ_MM, SUPPORT_CROSSBAR_CENTER_WORLD_MM)
    support = rail_left.union(rail_right).union(crossbar)

    upstream_reference = _cylinder_from(
        UPSTREAM_REFERENCE_START_WORLD_MM,
        ROUTE_AXIS_WORLD,
        ROUTE_INTERFACE_PROJECTION_MM,
        ROUTE_INTERFACE_RESERVATION_DIAMETER_MM,
    )
    downstream_reference = _cylinder_from(
        DOWNSTREAM_REFERENCE_START_WORLD_MM,
        ROUTE_AXIS_WORLD,
        ROUTE_INTERFACE_PROJECTION_MM,
        ROUTE_INTERFACE_RESERVATION_DIAMETER_MM,
    )
    drain_dry = _box(
        *DRAIN_DRY_CLEARANCE_XYZ_MM,
        DRAIN_DRY_CLEARANCE_CENTER_WORLD_MM,
    )
    service = _box(
        *SERVICE_CLEARANCE_XYZ_MM,
        SERVICE_CLEARANCE_CENTER_WORLD_MM,
    )

    datums = (
        PassiveBackflowInterfaceDatum(
            datum_id="PASSIVE-BACKFLOW-UPSTREAM-ROUTE-ANCHOR-CELL4",
            route_id=ROUTE_PUMP_TO_BARRIER,
            role="PUMP_TO_PASSIVE_BACKFLOW_PROTECTION_ROUTE_GRAPH_HANDOFF",
            source_interface_id=INTERFACE_PUMP_OUTLET,
            target_interface_id=BARRIER_WASTE,
            center_world_mm=ROUTE_GRAPH_ANCHOR_WORLD_MM,
            axis_world=ROUTE_AXIS_WORLD,
        ),
        PassiveBackflowInterfaceDatum(
            datum_id="PASSIVE-BACKFLOW-DOWNSTREAM-ROUTE-ANCHOR-CELL4",
            route_id=ROUTE_BARRIER_TO_CARTRIDGE,
            role="PASSIVE_BACKFLOW_PROTECTION_TO_CARTRIDGE_ROUTE_GRAPH_HANDOFF",
            source_interface_id=INTERFACE_BARRIER_OUTLET,
            target_interface_id=INTERFACE_CARTRIDGE_INLET_I27,
            center_world_mm=ROUTE_GRAPH_ANCHOR_WORLD_MM,
            axis_world=ROUTE_AXIS_WORLD,
        ),
    )

    result = RealizedPassiveBackflowPackage(
        source_authority_revision=release.realization.authority_revision,
        source_waste_pump_architecture_sha256=release.source_waste_pump_architecture_sha256,
        source_backbone_realization_sha256=release.realization.manifest_sha256,
        authored_against_git_sha=AUTHORED_AGAINST_MAIN_SHA,
        package_screening_solid=package,
        support_cradle_solid=support,
        upstream_route_anchor_solid=upstream_reference,
        downstream_route_anchor_solid=downstream_reference,
        drain_dry_clearance_solid=drain_dry,
        service_clearance_solid=service,
        interface_datums=datums,
    )
    result.validate_source_release(release)
    return result


def build_current_realized_passive_backflow_package() -> RealizedPassiveBackflowPackage:
    """Trusted path rooted in current released waste-routing source truth."""
    return build_realized_passive_backflow_package(
        build_current_cell4_waste_backbone_release()
    )
