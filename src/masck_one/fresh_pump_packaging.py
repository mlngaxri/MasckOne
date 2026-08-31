"""Dual fresh-fluid pump packaging and tubing-interface architecture.

Iteration 22 establishes stable water and cleanser station identities and route
boundaries. Supplier selection, package dimensions, placements, tube dimensions,
connectors, pressure-flow behavior, dosing accuracy, and physical performance remain
unresolved until controlled evidence and generated geometry exist.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import re

from .cleanser_storage import CleanserStorageArchitecture, PORT_OUTLET
from .structural_frame import (
    RESERVATION_FRESH_FLUID,
    StructuralFrameTopology,
)
from .water_reservoir import PORT_PICKUP, WaterReservoirArchitecture


class FreshPumpPackagingError(ValueError):
    """Raised when the Iteration-22 source, identity, or evidence boundary is invalid."""


STATION_WATER = "PUMP-STATION-WATER"
STATION_CLEANSER = "PUMP-STATION-CLEANSER"
STATION_IDS = (STATION_WATER, STATION_CLEANSER)

INTERFACE_WATER_PUMP_OUTLET = "PUMP-OUTLET-WATER"
INTERFACE_CLEANSER_PUMP_OUTLET = "PUMP-OUTLET-CLEANSER"

ROUTE_WATER_SOURCE = "ROUTE-WATER-RESERVOIR-TO-PUMP"
ROUTE_WATER_MANIFOLD = "ROUTE-WATER-PUMP-TO-MANIFOLD-I23"
ROUTE_CLEANSER_SOURCE = "ROUTE-CLEANSER-STORAGE-TO-PUMP"
ROUTE_CLEANSER_MANIFOLD = "ROUTE-CLEANSER-PUMP-TO-MANIFOLD-I23"
ROUTE_IDS = (
    ROUTE_WATER_SOURCE,
    ROUTE_WATER_MANIFOLD,
    ROUTE_CLEANSER_SOURCE,
    ROUTE_CLEANSER_MANIFOLD,
)

FLUID_IDENTITIES = frozenset({"WATER", "CLEANSER"})
ROUTE_STAGES = frozenset({"SOURCE_TO_PUMP", "PUMP_TO_MANIFOLD"})
PUMP_PACKAGE_STATUS = "UNRESOLVED_PENDING_CONTROLLED_SUPPLIER_PACKAGE_EVIDENCE"
PUMP_METERING_STATUS = "VALIDATION_GATED_PENDING_PRESSURE_FLOW_AND_METERING_RIG_EVIDENCE"
ROUTE_GEOMETRY_STATUS = "UNRESOLVED_PENDING_CONTROLLED_CENTERLINES_TUBING_AND_CONNECTORS"
ROUTE_HYDRAULIC_STATUS = "VALIDATION_GATED_PENDING_CONTROLLED_GEOMETRY_FLUID_PROPERTIES_AND_PUMP_CURVES"
ARCHITECTURE_EVIDENCE_STATUS = (
    "DUAL_PUMP_AND_TUBING_INTERFACE_ARCHITECTURE_ONLY_NOT_PACKAGE_SELECTION_"
    "METERING_HYDRAULIC_LEAK_SERVICE_OR_PHYSICAL_EVIDENCE"
)

_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


def _text(value: object, *, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise FreshPumpPackagingError(f"{label} must be exact built-in nonblank text")
    return value


def _sha(value: object, *, label: str) -> str:
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
        raise FreshPumpPackagingError(f"{label} must be a canonical lowercase SHA-256")
    return value


@dataclass(frozen=True, slots=True)
class PumpStationReservation:
    station_id: str
    fluid_identity: str
    source_architecture_sha256: str
    source_port_id: str
    pump_outlet_interface_id: str
    frame_reservation_id: str
    package_candidate_id: str | None
    package_evidence_sha256: str | None
    envelope_mm: tuple[float, float, float] | None
    placement_xyz_mm: tuple[float, float, float] | None
    orientation_axis_xyz: tuple[float, float, float] | None
    tubing_inner_diameter_mm: float | None
    minimum_bend_radius_mm: float | None
    connector_standard: str | None
    package_status: str
    routing_status: str
    service_status: str
    metering_performance_status: str

    def __post_init__(self) -> None:
        if type(self.station_id) is not str or self.station_id not in STATION_IDS:
            raise FreshPumpPackagingError(f"unknown pump station {self.station_id!r}")
        if type(self.fluid_identity) is not str or self.fluid_identity not in FLUID_IDENTITIES:
            raise FreshPumpPackagingError("pump station fluid identity must be exact WATER or CLEANSER")
        _sha(self.source_architecture_sha256, label="pump station source architecture")
        _text(self.source_port_id, label="pump station source port ID")
        _text(self.pump_outlet_interface_id, label="pump outlet interface ID")
        if type(self.frame_reservation_id) is not str or self.frame_reservation_id != RESERVATION_FRESH_FLUID:
            raise FreshPumpPackagingError("pump station must consume the fresh-fluid frame reservation")

        unresolved = (
            self.package_candidate_id,
            self.package_evidence_sha256,
            self.envelope_mm,
            self.placement_xyz_mm,
            self.orientation_axis_xyz,
            self.tubing_inner_diameter_mm,
            self.minimum_bend_radius_mm,
            self.connector_standard,
        )
        if any(value is not None for value in unresolved):
            raise FreshPumpPackagingError(
                "Iteration 22 cannot invent pump selection, package geometry, placement, tubing dimensions, or connectors"
            )
        for label, value in (
            ("pump package status", self.package_status),
            ("pump routing status", self.routing_status),
            ("pump service status", self.service_status),
            ("pump metering status", self.metering_performance_status),
        ):
            _text(value, label=label)
        if type(self.package_status) is not str or self.package_status != PUMP_PACKAGE_STATUS:
            raise FreshPumpPackagingError("pump package selection must remain unresolved")
        if type(self.metering_performance_status) is not str or self.metering_performance_status != PUMP_METERING_STATUS:
            raise FreshPumpPackagingError("pump metering performance must remain validation gated")

    def manifest(self) -> dict[str, object]:
        return {
            "station_id": self.station_id,
            "fluid_identity": self.fluid_identity,
            "source_architecture_sha256": self.source_architecture_sha256,
            "source_port_id": self.source_port_id,
            "pump_outlet_interface_id": self.pump_outlet_interface_id,
            "frame_reservation_id": self.frame_reservation_id,
            "package_candidate_id": self.package_candidate_id,
            "package_evidence_sha256": self.package_evidence_sha256,
            "envelope_mm": self.envelope_mm,
            "placement_xyz_mm": self.placement_xyz_mm,
            "orientation_axis_xyz": self.orientation_axis_xyz,
            "tubing_inner_diameter_mm": self.tubing_inner_diameter_mm,
            "minimum_bend_radius_mm": self.minimum_bend_radius_mm,
            "connector_standard": self.connector_standard,
            "package_status": self.package_status,
            "routing_status": self.routing_status,
            "service_status": self.service_status,
            "metering_performance_status": self.metering_performance_status,
        }


@dataclass(frozen=True, slots=True)
class FreshFluidRouteInterface:
    route_id: str
    fluid_identity: str
    stage: str
    source_interface_id: str
    target_interface_id: str
    geometry_status: str
    hydraulic_status: str
    service_status: str

    def __post_init__(self) -> None:
        if type(self.route_id) is not str or self.route_id not in ROUTE_IDS:
            raise FreshPumpPackagingError(f"unknown fresh-fluid route {self.route_id!r}")
        if type(self.fluid_identity) is not str or self.fluid_identity not in FLUID_IDENTITIES:
            raise FreshPumpPackagingError("route fluid identity must be exact WATER or CLEANSER")
        if type(self.stage) is not str or self.stage not in ROUTE_STAGES:
            raise FreshPumpPackagingError("route stage must use the controlled vocabulary")
        for label, value in (
            ("route source interface", self.source_interface_id),
            ("route target interface", self.target_interface_id),
            ("route geometry status", self.geometry_status),
            ("route hydraulic status", self.hydraulic_status),
            ("route service status", self.service_status),
        ):
            _text(value, label=label)
        if type(self.geometry_status) is not str or self.geometry_status != ROUTE_GEOMETRY_STATUS:
            raise FreshPumpPackagingError("Iteration-22 route geometry must remain unresolved")
        if type(self.hydraulic_status) is not str or self.hydraulic_status != ROUTE_HYDRAULIC_STATUS:
            raise FreshPumpPackagingError("fresh-route hydraulics must remain validation gated")

    def manifest(self) -> dict[str, object]:
        return {
            "route_id": self.route_id,
            "fluid_identity": self.fluid_identity,
            "stage": self.stage,
            "source_interface_id": self.source_interface_id,
            "target_interface_id": self.target_interface_id,
            "geometry_status": self.geometry_status,
            "hydraulic_status": self.hydraulic_status,
            "service_status": self.service_status,
        }


@dataclass(frozen=True, slots=True)
class FreshPumpPackagingArchitecture:
    source_water_architecture_sha256: str
    source_cleanser_architecture_sha256: str
    source_structural_frame_sha256: str
    stations: tuple[PumpStationReservation, ...]
    routes: tuple[FreshFluidRouteInterface, ...]
    physical_validation_eligible: bool
    evidence_status: str

    def __post_init__(self) -> None:
        _sha(self.source_water_architecture_sha256, label="source water architecture")
        _sha(self.source_cleanser_architecture_sha256, label="source cleanser architecture")
        _sha(self.source_structural_frame_sha256, label="source structural frame")
        if type(self.stations) is not tuple or tuple(type(item) for item in self.stations) != (
            PumpStationReservation,
            PumpStationReservation,
        ):
            raise FreshPumpPackagingError("pump stations must be an exact immutable two-station tuple")
        if tuple(item.station_id for item in self.stations) != STATION_IDS:
            raise FreshPumpPackagingError("pump stations must retain controlled water/cleanser order")
        if tuple(item.fluid_identity for item in self.stations) != ("WATER", "CLEANSER"):
            raise FreshPumpPackagingError("pump stations cannot swap or combine fluid identities")
        expected_stations = (
            (
                "WATER",
                self.source_water_architecture_sha256,
                PORT_PICKUP,
                INTERFACE_WATER_PUMP_OUTLET,
            ),
            (
                "CLEANSER",
                self.source_cleanser_architecture_sha256,
                PORT_OUTLET,
                INTERFACE_CLEANSER_PUMP_OUTLET,
            ),
        )
        actual_stations = tuple(
            (
                station.fluid_identity,
                station.source_architecture_sha256,
                station.source_port_id,
                station.pump_outlet_interface_id,
            )
            for station in self.stations
        )
        if actual_stations != expected_stations:
            raise FreshPumpPackagingError("pump station source and outlet bindings cannot cross or alias fluid paths")
        if type(self.routes) is not tuple or any(type(item) is not FreshFluidRouteInterface for item in self.routes):
            raise FreshPumpPackagingError("fresh routes must be an immutable tuple of exact route records")
        if tuple(item.route_id for item in self.routes) != ROUTE_IDS:
            raise FreshPumpPackagingError("fresh routes must follow the complete controlled route order")
        expected = (
            ("WATER", "SOURCE_TO_PUMP", PORT_PICKUP, STATION_WATER),
            ("WATER", "PUMP_TO_MANIFOLD", INTERFACE_WATER_PUMP_OUTLET, "MANIFOLD-INLET-WATER-I23"),
            ("CLEANSER", "SOURCE_TO_PUMP", PORT_OUTLET, STATION_CLEANSER),
            ("CLEANSER", "PUMP_TO_MANIFOLD", INTERFACE_CLEANSER_PUMP_OUTLET, "MANIFOLD-INLET-CLEANSER-I23"),
        )
        actual = tuple(
            (route.fluid_identity, route.stage, route.source_interface_id, route.target_interface_id)
            for route in self.routes
        )
        if actual != expected:
            raise FreshPumpPackagingError("fresh-route interfaces cannot cross, bypass, or alias fluid paths")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise FreshPumpPackagingError("digital pump packaging cannot be physical validation evidence")
        if type(self.evidence_status) is not str or self.evidence_status != ARCHITECTURE_EVIDENCE_STATUS:
            raise FreshPumpPackagingError("pump packaging evidence status must use the controlled architecture evidence state")

    def validate_current_sources(
        self,
        *,
        water: WaterReservoirArchitecture,
        cleanser: CleanserStorageArchitecture,
        frame: StructuralFrameTopology,
    ) -> None:
        if type(water) is not WaterReservoirArchitecture:
            raise FreshPumpPackagingError("water must be an exact WaterReservoirArchitecture")
        if type(cleanser) is not CleanserStorageArchitecture:
            raise FreshPumpPackagingError("cleanser must be an exact CleanserStorageArchitecture")
        if type(frame) is not StructuralFrameTopology:
            raise FreshPumpPackagingError("frame must be an exact StructuralFrameTopology")
        if self.source_water_architecture_sha256 != water.architecture_sha256:
            raise FreshPumpPackagingError("pump packaging is stale for current water architecture")
        if self.source_cleanser_architecture_sha256 != cleanser.architecture_sha256:
            raise FreshPumpPackagingError("pump packaging is stale for current cleanser architecture")
        if self.source_structural_frame_sha256 != frame.topology_sha256:
            raise FreshPumpPackagingError("pump packaging is stale for current structural frame")
        reservations = tuple(
            item for item in frame.reservations if item.reservation_id == RESERVATION_FRESH_FLUID
        )
        if len(reservations) != 1:
            raise FreshPumpPackagingError("structural frame must expose exactly one fresh-fluid reservation")

    @property
    def architecture_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "source_water_architecture_sha256": self.source_water_architecture_sha256,
            "source_cleanser_architecture_sha256": self.source_cleanser_architecture_sha256,
            "source_structural_frame_sha256": self.source_structural_frame_sha256,
            "stations": [item.manifest() for item in self.stations],
            "routes": [item.manifest() for item in self.routes],
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            payload["architecture_sha256"] = self.architecture_sha256
        return payload


def build_fresh_pump_packaging_architecture(
    water: WaterReservoirArchitecture,
    cleanser: CleanserStorageArchitecture,
    frame: StructuralFrameTopology,
) -> FreshPumpPackagingArchitecture:
    if type(water) is not WaterReservoirArchitecture:
        raise FreshPumpPackagingError("water must be an exact WaterReservoirArchitecture")
    if type(cleanser) is not CleanserStorageArchitecture:
        raise FreshPumpPackagingError("cleanser must be an exact CleanserStorageArchitecture")
    if type(frame) is not StructuralFrameTopology:
        raise FreshPumpPackagingError("frame must be an exact StructuralFrameTopology")
    common_station = {
        "frame_reservation_id": RESERVATION_FRESH_FLUID,
        "package_candidate_id": None,
        "package_evidence_sha256": None,
        "envelope_mm": None,
        "placement_xyz_mm": None,
        "orientation_axis_xyz": None,
        "tubing_inner_diameter_mm": None,
        "minimum_bend_radius_mm": None,
        "connector_standard": None,
        "package_status": PUMP_PACKAGE_STATUS,
        "routing_status": "INTERFACE_TOPOLOGY_ONLY_CENTERLINES_AND_SERVICE_CLEARANCE_UNRESOLVED",
        "service_status": "REPLACEABILITY_PURGE_AND_ACCESS_TRAJECTORY_REQUIRE_ASSEMBLY_GEOMETRY",
        "metering_performance_status": PUMP_METERING_STATUS,
    }
    stations = (
        PumpStationReservation(
            station_id=STATION_WATER,
            fluid_identity="WATER",
            source_architecture_sha256=water.architecture_sha256,
            source_port_id=PORT_PICKUP,
            pump_outlet_interface_id=INTERFACE_WATER_PUMP_OUTLET,
            **common_station,
        ),
        PumpStationReservation(
            station_id=STATION_CLEANSER,
            fluid_identity="CLEANSER",
            source_architecture_sha256=cleanser.architecture_sha256,
            source_port_id=PORT_OUTLET,
            pump_outlet_interface_id=INTERFACE_CLEANSER_PUMP_OUTLET,
            **common_station,
        ),
    )
    common_route = {
        "geometry_status": ROUTE_GEOMETRY_STATUS,
        "hydraulic_status": ROUTE_HYDRAULIC_STATUS,
        "service_status": "ROUTE_ACCESS_PURGE_REPLACEMENT_AND_STRAIN_RELIEF_UNRESOLVED",
    }
    routes = (
        FreshFluidRouteInterface(ROUTE_WATER_SOURCE, "WATER", "SOURCE_TO_PUMP", PORT_PICKUP, STATION_WATER, **common_route),
        FreshFluidRouteInterface(ROUTE_WATER_MANIFOLD, "WATER", "PUMP_TO_MANIFOLD", INTERFACE_WATER_PUMP_OUTLET, "MANIFOLD-INLET-WATER-I23", **common_route),
        FreshFluidRouteInterface(ROUTE_CLEANSER_SOURCE, "CLEANSER", "SOURCE_TO_PUMP", PORT_OUTLET, STATION_CLEANSER, **common_route),
        FreshFluidRouteInterface(ROUTE_CLEANSER_MANIFOLD, "CLEANSER", "PUMP_TO_MANIFOLD", INTERFACE_CLEANSER_PUMP_OUTLET, "MANIFOLD-INLET-CLEANSER-I23", **common_route),
    )
    architecture = FreshPumpPackagingArchitecture(
        source_water_architecture_sha256=water.architecture_sha256,
        source_cleanser_architecture_sha256=cleanser.architecture_sha256,
        source_structural_frame_sha256=frame.topology_sha256,
        stations=stations,
        routes=routes,
        physical_validation_eligible=False,
        evidence_status=ARCHITECTURE_EVIDENCE_STATUS,
    )
    architecture.validate_current_sources(water=water, cleanser=cleanser, frame=frame)
    return architecture
