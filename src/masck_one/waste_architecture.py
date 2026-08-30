from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math

import cadquery as cq

from .authority import Authority
from .coverage import FacialCoverageMesh
from .protected_volumes import ProtectedVolumeSet
from .spatial import Point2, Point3


class WasteArchitectureError(ValueError):
    pass


REQUIRED_FAULT_STATES = (
    "PUMP_OFF_OR_POWER_LOSS",
    "GAS_INGESTION_OR_INTERMITTENT_LIQUID_SLUGGING",
    "FOAM_INGESTION",
    "ROUTE_OCCLUSION",
    "BACKFLOW",
    "CARTRIDGE_MISSING_OR_INCORRECTLY_INSTALLED",
    "CARTRIDGE_FULL_OR_REDUCED_RETENTION",
    "LOCAL_POOLING_NEAR_PROTECTED_OPENINGS",
)

REQUIRED_ORIENTATION_CASES = (
    "UPRIGHT",
    "RECLINED",
    "LEFT_SIDE_TILT",
    "RIGHT_SIDE_TILT",
    "FACE_UP",
    "FACE_DOWN",
    "ORIENTATION_TRANSITION",
)


@dataclass(frozen=True, slots=True)
class WasteAcquisitionPath:
    path_id: str
    source_triangle_index: int
    centerline_mm: tuple[Point3, ...]
    gutter_width_mm: float | None
    gutter_depth_mm: float | None
    capillary_geometry_status: str
    gravity_role: str

    def __post_init__(self) -> None:
        if self.source_triangle_index < 0:
            raise WasteArchitectureError("Acquisition source triangle cannot be negative")
        if len(self.centerline_mm) < 2:
            raise WasteArchitectureError("Acquisition path requires at least two centerline points")
        if any(left == right for left, right in zip(self.centerline_mm, self.centerline_mm[1:])):
            raise WasteArchitectureError("Acquisition centerline cannot contain a zero-length segment")
        if self.gutter_width_mm is not None or self.gutter_depth_mm is not None:
            raise WasteArchitectureError("Waste gutter dimensions require registered surfaces and recovery testing")

    def cad_centerline(self) -> cq.Wire:
        points = [cq.Vector(*point.as_tuple()) for point in self.centerline_mm]
        return cq.Wire.makePolygon(points, close=False)


@dataclass(frozen=True, slots=True)
class TransientBuffer:
    buffer_id: str
    upstream_path_id: str
    location_mm: Point3
    usable_capacity_mL: float | None
    geometry_status: str

    def __post_init__(self) -> None:
        if self.usable_capacity_mL is not None:
            raise WasteArchitectureError("Transient-buffer capacity requires mixed-phase recovery evidence")


@dataclass(frozen=True, slots=True)
class WastePumpStation:
    station_id: str
    reference_id: str
    development_envelope_mm: tuple[float, float, float]
    center_mm: Point3
    mixed_phase_status: str
    fault_state_ids: tuple[str, ...]
    inlet_interface_status: str
    outlet_interface_status: str

    def cad_envelope(self) -> cq.Workplane:
        x, y, z = self.development_envelope_mm
        return cq.Workplane("XY").box(x, y, z, centered=(True, True, True)).translate(
            self.center_mm.as_tuple()
        )


@dataclass(frozen=True, slots=True)
class WasteCartridgeArchitecture:
    cartridge_id: str
    external_envelope_mm: tuple[float, float, float]
    center_mm: Point3
    retained_capacity_target_mL: float
    service_cycles_baseline: int
    internal_usable_capacity_mL: float | None
    insertion_key_status: str
    seal_status: str
    missing_detection_status: str
    service_trajectory_status: str
    retained_capacity_status: str
    internal_geometry_status: str
    media_status: str
    vent_air_management_status: str

    def __post_init__(self) -> None:
        if any(value <= 0.0 for value in self.external_envelope_mm):
            raise WasteArchitectureError("Cartridge external envelope dimensions must be positive")
        if self.retained_capacity_target_mL <= 0.0:
            raise WasteArchitectureError("Cartridge retained-capacity target must be positive")
        if self.service_cycles_baseline <= 0:
            raise WasteArchitectureError("Cartridge service-cycle baseline must be positive")
        if self.internal_usable_capacity_mL is not None:
            raise WasteArchitectureError(
                "Internal usable cartridge capacity cannot be asserted before wall, seal, vent, media and retained-volume evidence are controlled"
            )

    @property
    def external_bounding_volume_mL(self) -> float:
        """Bounding-box volume only. Never treat this as fillable or retained capacity."""
        return math.prod(self.external_envelope_mm) / 1000.0

    def cad_external_envelope(self) -> cq.Workplane:
        x, y, z = self.external_envelope_mm
        return cq.Workplane("XY").box(x, y, z, centered=(True, True, True)).translate(
            self.center_mm.as_tuple()
        )

    def cad_capacity_reservation(self) -> cq.Workplane:
        raise WasteArchitectureError(
            "No capacity solid is valid until cartridge wall, seal, keying, vent/air handling, contaminated-interface and media geometry are controlled"
        )


@dataclass(frozen=True, slots=True)
class FluidRouteContract:
    route_id: str
    fluid_role: str
    source_interface_id: str
    sink_interface_id: str
    inner_diameter_mm: float | None
    minimum_bend_radius_mm: float | None
    dead_volume_mL: float | None
    service_clearance_mm: float | None
    validation_status: str

    def __post_init__(self) -> None:
        if not self.route_id or not self.source_interface_id or not self.sink_interface_id:
            raise WasteArchitectureError("Route and interface IDs cannot be empty")
        if any(
            value is not None
            for value in (
                self.inner_diameter_mm,
                self.minimum_bend_radius_mm,
                self.dead_volume_mL,
                self.service_clearance_mm,
            )
        ):
            raise WasteArchitectureError("Route dimensions require selected tubing, connectors and service evidence")


@dataclass(frozen=True, slots=True)
class WasteArchitecture:
    source_coverage_sha256: str
    acquisition_paths: tuple[WasteAcquisitionPath, ...]
    transient_buffers: tuple[TransientBuffer, ...]
    pump_station: WastePumpStation
    cartridge: WasteCartridgeArchitecture
    route_contracts: tuple[FluidRouteContract, ...]
    orientation_case_ids: tuple[str, ...]
    orientation_validation_status: str
    minimum_recovery_ratio: float
    maximum_residual_free_liquid_uL: float
    architecture_status: str
    evidence_status: str
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        if len(self.source_coverage_sha256) != 64:
            raise WasteArchitectureError("Waste architecture must bind to an exact coverage revision")
        path_ids = {path.path_id for path in self.acquisition_paths}
        if len(path_ids) != 4 or len(self.acquisition_paths) != 4:
            raise WasteArchitectureError("Development baseline requires four unique regional acquisition paths")
        buffer_ids = {buffer.buffer_id for buffer in self.transient_buffers}
        if len(self.transient_buffers) != 4 or len(buffer_ids) != 4:
            raise WasteArchitectureError("Development baseline requires four unique transient buffers")
        if {buffer.upstream_path_id for buffer in self.transient_buffers} != path_ids:
            raise WasteArchitectureError("Each acquisition path requires one transient-buffer handoff")
        if (
            len(self.pump_station.fault_state_ids) != len(REQUIRED_FAULT_STATES)
            or set(self.pump_station.fault_state_ids) != set(REQUIRED_FAULT_STATES)
        ):
            raise WasteArchitectureError("Waste pump architecture must enumerate every brief-required fault state")
        if (
            len(self.orientation_case_ids) != len(REQUIRED_ORIENTATION_CASES)
            or set(self.orientation_case_ids) != set(REQUIRED_ORIENTATION_CASES)
        ):
            raise WasteArchitectureError("Waste architecture must enumerate every controlled orientation case")
        if len({route.route_id for route in self.route_contracts}) != len(self.route_contracts):
            raise WasteArchitectureError("Fluid route IDs must be unique")
        if self.cartridge.external_bounding_volume_mL + 1e-9 < self.cartridge.retained_capacity_target_mL:
            raise WasteArchitectureError(
                "Cartridge external bounding volume cannot be smaller than the retained-capacity target"
            )
        if self.cartridge.internal_usable_capacity_mL is not None:
            raise WasteArchitectureError(
                "Retained capacity is validation-gated and cannot be promoted from bounding-box arithmetic"
            )
        if not 0.0 < self.minimum_recovery_ratio <= 1.0:
            raise WasteArchitectureError("Recovery-ratio requirement must be in (0, 1]")
        if self.maximum_residual_free_liquid_uL < 0.0:
            raise WasteArchitectureError("Residual free-liquid requirement cannot be negative")
        if self.physical_validation_eligible:
            raise WasteArchitectureError("Digital waste architecture is not recovery, leakage or capacity evidence")

    def cad_acquisition_centerlines(self) -> cq.Workplane:
        wires = [path.cad_centerline() for path in self.acquisition_paths]
        return cq.Workplane("XY").newObject([cq.Compound.makeCompound(wires)])

    @property
    def topology_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        result: dict[str, object] = {
            "source_coverage_sha256": self.source_coverage_sha256,
            "acquisition_paths": [
                {
                    **asdict(path),
                    "centerline_mm": [list(point.as_tuple()) for point in path.centerline_mm],
                }
                for path in self.acquisition_paths
            ],
            "transient_buffers": [
                {**asdict(buffer), "location_mm": list(buffer.location_mm.as_tuple())}
                for buffer in self.transient_buffers
            ],
            "pump_station": {
                **asdict(self.pump_station),
                "center_mm": list(self.pump_station.center_mm.as_tuple()),
            },
            "cartridge": {
                **asdict(self.cartridge),
                "center_mm": list(self.cartridge.center_mm.as_tuple()),
                "external_bounding_volume_mL": self.cartridge.external_bounding_volume_mL,
            },
            "route_contracts": [asdict(route) for route in self.route_contracts],
            "orientation_case_ids": list(self.orientation_case_ids),
            "orientation_validation_status": self.orientation_validation_status,
            "minimum_recovery_ratio": self.minimum_recovery_ratio,
            "maximum_residual_free_liquid_uL": self.maximum_residual_free_liquid_uL,
            "architecture_status": self.architecture_status,
            "evidence_status": self.evidence_status,
            "physical_validation_eligible": self.physical_validation_eligible,
        }
        if include_sha:
            result["topology_sha256"] = self.topology_sha256
        return result


def _regional_source(coverage: FacialCoverageMesh, protected: ProtectedVolumeSet, x: float, y: float):
    candidates = [
        triangle
        for triangle in coverage.target_triangles
        if not protected.excluded_xy(Point2(triangle.centroid.x, triangle.centroid.y))
        and triangle.centroid.x * x > 0.0
        and triangle.centroid.y * y > 0.0
    ]
    if not candidates:
        raise WasteArchitectureError("No target-only triangle is available for a regional waste path")
    return min(
        candidates,
        key=lambda triangle: (
            math.dist((triangle.centroid.x, triangle.centroid.y), (x, y)),
            triangle.triangle_index,
        ),
    )


def build_waste_architecture(
    authority: Authority,
    coverage: FacialCoverageMesh,
    protected: ProtectedVolumeSet,
    cartridge_center_mm: Point3,
    fresh_route_ids: tuple[str, ...],
) -> WasteArchitecture:
    frame_x, frame_y = authority.pair("geometry", "functional_frame_xy_mm")
    anchors = (
        ("UPPER_LEFT", -frame_x / 4.0, frame_y / 4.0),
        ("UPPER_RIGHT", frame_x / 4.0, frame_y / 4.0),
        ("LOWER_LEFT", -frame_x / 4.0, -frame_y / 4.0),
        ("LOWER_RIGHT", frame_x / 4.0, -frame_y / 4.0),
    )
    paths = []
    buffers = []
    for region_id, x, y in anchors:
        triangle = _regional_source(coverage, protected, x, y)
        sign = -1.0 if triangle.centroid.x < 0.0 else 1.0
        handoff = Point3(sign * frame_x / 2.0, triangle.centroid.y, triangle.centroid.z)
        path_id = f"WASTE_PATH_{region_id}"
        paths.append(
            WasteAcquisitionPath(
                path_id,
                triangle.triangle_index,
                (triangle.centroid, handoff),
                None,
                None,
                "CENTERLINE_INTENT_ONLY_REQUIRES_REGISTERED_SKIN_SURFACE_AND_MIXED_PHASE_RIG",
                "SECONDARY_NOT_PRIMARY_TRANSPORT_MECHANISM",
            )
        )
        buffers.append(
            TransientBuffer(
                f"BUFFER_{region_id}",
                path_id,
                handoff,
                None,
                "LOCATION_HANDOFF_ONLY_CAPACITY_AND_GEOMETRY_UNRESOLVED",
            )
        )

    external = tuple(float(value) for value in authority.get("fluid", "cartridge", "external_envelope_mm"))
    retained = authority.number("fluid", "cartridge", "retained_capacity_min_mL")
    cartridge = WasteCartridgeArchitecture(
        "WASTE_CARTRIDGE_ALPHA",
        external,
        cartridge_center_mm,
        retained,
        int(authority.number("fluid", "cartridge", "service_cycles_baseline")),
        None,
        "KEY_AND_INCORRECT_INSERTION_REJECTION_GEOMETRY_UNRESOLVED",
        "SEAL_STACK_COMPRESSION_MATERIAL_AND_LEAKAGE_EVIDENCE_UNRESOLVED",
        "MISSING_OR_MISINSTALLED_STATE_REQUIRES_SENSOR_AND_STATE_MACHINE_HANDOFF",
        "INSERTION_REMOVAL_GRIP_AND_CONTAMINATION_BOUNDARY_UNRESOLVED",
        str(authority.get("fluid", "cartridge", "retained_capacity_status")),
        "WALL_SEAL_KEYING_VENT_MEDIA_AND_CONTAMINATED_INTERFACE_GEOMETRY_UNRESOLVED",
        "NO_ABSORBENT_OR_RETENTION_MEDIA_VOLUME_CREDIT_WITHOUT_PHYSICAL_EVIDENCE",
        "VENTING_AIR_SEPARATION_AND_ORIENTATION_BEHAVIOR_UNRESOLVED",
    )
    pump = WastePumpStation(
        "PUMP_WASTE_ALPHA",
        "TAKASAGO_SDMP_DEVELOPMENT_REFERENCE",
        (25.0, 25.0, 8.2),
        Point3(0.0, -45.0, 8.0),
        "MIXED_GAS_LIQUID_FOAM_OPERATION_REQUIRES_ITERATION45_RIG_NO_DATASHEET_ASSUMPTION",
        REQUIRED_FAULT_STATES,
        "INLET_INTERFACE_AND_SLUG_BUFFERING_UNRESOLVED",
        "OUTLET_CHECK_VALVE_BACKFLOW_AND_CARTRIDGE_INTERFACE_UNRESOLVED",
    )
    waste_routes = (
        FluidRouteContract(
            "ROUTE_WASTE_BUFFERS_TO_PUMP_I26",
            "WASTE_MIXED_PHASE",
            "REGIONAL_TRANSIENT_BUFFERS",
            pump.station_id,
            None,
            None,
            None,
            None,
            "ROUTE_TOPOLOGY_ONLY_MIXED_PHASE_OCCLUSION_AND_SERVICE_EVIDENCE_REQUIRED",
        ),
        FluidRouteContract(
            "ROUTE_WASTE_PUMP_TO_CARTRIDGE_I27",
            "WASTE_MIXED_PHASE",
            pump.station_id,
            cartridge.cartridge_id,
            None,
            None,
            None,
            None,
            "ROUTE_TOPOLOGY_ONLY_BACKFLOW_LEAKAGE_AND_SERVICE_EVIDENCE_REQUIRED",
        ),
    )
    fresh_route_contracts = tuple(
        FluidRouteContract(
            route_id,
            "FRESH_FLUID",
            "SOURCE_DEFINED_BY_FRESH_FLUID_ARCHITECTURE",
            "SINK_DEFINED_BY_FRESH_FLUID_ARCHITECTURE",
            None,
            None,
            None,
            None,
            "ITERATION28_INTEGRATION_CONTRACT_DIMENSIONS_AND_DEAD_VOLUME_UNRESOLVED",
        )
        for route_id in fresh_route_ids
    )
    return WasteArchitecture(
        coverage.segmentation_sha256,
        tuple(paths),
        tuple(buffers),
        pump,
        cartridge,
        (*fresh_route_contracts, *waste_routes),
        REQUIRED_ORIENTATION_CASES,
        "ORIENTATION_CASES_REGISTERED_FOR_RIG_OR_SIMULATION_HANDOFF_NO_PASS_STATUS_ASSIGNED",
        authority.number("fluid", "waste", "recovery_ratio_min"),
        authority.number("fluid", "waste", "residual_free_liquid_max_uL"),
        "ITERATIONS25_28_WASTE_ACQUISITION_PUMP_CARTRIDGE_AND_ROUTING_ARCHITECTURE",
        "NOT_RECOVERY_RESIDUAL_POOLING_MIXED_PHASE_CAPACITY_LEAKAGE_BACKFLOW_OR_SERVICE_VALIDATION",
    )
