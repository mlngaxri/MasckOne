from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math

import cadquery as cq

from .authority import Authority
from .spatial import Point3


class FreshFluidArchitectureError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ReservoirArchitecture:
    reservoir_id: str
    gross_volume_mL: float
    minimum_usable_mL: float
    development_envelope_mm: tuple[float, float, float]
    development_center_mm: Point3
    fill_interface_status: str
    vent_interface_status: str
    service_status: str
    dead_volume_status: str

    def cad_envelope(self) -> cq.Workplane:
        x, y, z = self.development_envelope_mm
        return cq.Workplane("XY").box(x, y, z, centered=(True, True, True)).translate(self.development_center_mm.as_tuple())


@dataclass(frozen=True, slots=True)
class CleanserArchitecture:
    dose_per_cycle_mL: float
    storage_capacity_mL: float | None
    refill_interface_status: str
    compatibility_status: str
    purge_status: str


@dataclass(frozen=True, slots=True)
class PumpReference:
    reference_id: str
    envelope_mm: tuple[float, float, float]
    mass_g: float
    nominal_flow_range_mL_min: tuple[float, float]
    maximum_pressure_kPa: float
    role_status: str


@dataclass(frozen=True, slots=True)
class PumpStation:
    station_id: str
    fluid_role: str
    reference: PumpReference
    center_mm: Point3
    placement_status: str
    tubing_inner_diameter_mm: float | None
    minimum_bend_radius_mm: float | None
    connector_standard: str | None

    def cad_envelope(self) -> cq.Workplane:
        x, y, z = self.reference.envelope_mm
        return cq.Workplane("XY").box(x, y, z, centered=(True, True, True)).translate(self.center_mm.as_tuple())


@dataclass(frozen=True, slots=True)
class FreshFluidArchitecture:
    reservoir: ReservoirArchitecture
    cleanser: CleanserArchitecture
    pump_stations: tuple[PumpStation, ...]
    route_ids: tuple[str, ...]
    introduced_liquid_mL: float
    maximum_initial_prime_mL: float
    architecture_status: str
    evidence_status: str
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        volume_mm3 = math.prod(self.reservoir.development_envelope_mm)
        if not math.isclose(volume_mm3 / 1000.0, self.reservoir.gross_volume_mL, abs_tol=1e-9):
            raise FreshFluidArchitectureError("Reservoir development envelope must preserve gross-volume baseline")
        if len(self.pump_stations) != 2:
            raise FreshFluidArchitectureError("Iteration 22 reserves separate water and cleanser pump stations")
        if any(
            value is not None
            for station in self.pump_stations
            for value in (station.tubing_inner_diameter_mm, station.minimum_bend_radius_mm, station.connector_standard)
        ):
            raise FreshFluidArchitectureError("Tubing dimensions/connectors remain supplier and metering-rig dependent")
        if self.physical_validation_eligible:
            raise FreshFluidArchitectureError("Fluid packaging architecture is not metering or compatibility evidence")

    @property
    def topology_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        result: dict[str, object] = {
            "reservoir": {
                **asdict(self.reservoir),
                "development_center_mm": list(self.reservoir.development_center_mm.as_tuple()),
            },
            "cleanser": asdict(self.cleanser),
            "pump_stations": [
                {
                    **asdict(station),
                    "center_mm": list(station.center_mm.as_tuple()),
                }
                for station in self.pump_stations
            ],
            "route_ids": list(self.route_ids),
            "introduced_liquid_mL": self.introduced_liquid_mL,
            "maximum_initial_prime_mL": self.maximum_initial_prime_mL,
            "architecture_status": self.architecture_status,
            "evidence_status": self.evidence_status,
            "physical_validation_eligible": self.physical_validation_eligible,
        }
        if include_sha:
            result["topology_sha256"] = self.topology_sha256
        return result


def build_fresh_fluid_architecture(authority: Authority) -> FreshFluidArchitecture:
    gross = authority.number("fluid", "water_reservoir", "gross_mL")
    reservoir = ReservoirArchitecture(
        "WATER_RESERVOIR_ALPHA", gross,
        authority.number("fluid", "water_reservoir", "minimum_usable_mL"),
        (26.0, 25.0, 10.0), Point3(0.0, 76.0, 7.0),
        "FILL_PORT_LOCATION_AND_CLOSURE_UNRESOLVED",
        "VENT_PATH_AND_INGRESS_PROTECTION_UNRESOLVED",
        "REMOVAL_REFILL_AND_CLEANING_TRAJECTORY_UNRESOLVED",
        "USABLE_VOLUME_AND_DEAD_VOLUME_REQUIRE_ORIENTATION_TEST",
    )
    cleanser = CleanserArchitecture(
        authority.number("fluid", "clean_cycle", "cleanser_mL"), None,
        "STORAGE_VOLUME_REFILL_AND_USER_ERROR_PROOFING_UNRESOLVED",
        "FORMULATION_TUBING_SEAL_AND_STORAGE_COMPATIBILITY_EVIDENCE_REQUIRED",
        "PURGE_SEQUENCE_DEFINED_AS_REQUIRED_GEOMETRY_AND_METERING_UNRESOLVED",
    )
    bp7 = PumpReference(
        "BARTELS_BP7", (30.0, 15.0, 3.8), 2.0, (0.0, 9.0), 45.0,
        "PREFERRED_FRESH_FLUID_ALPHA_CANDIDATE_NOT_PRODUCTION_FREEZE",
    )
    stations = (
        PumpStation("PUMP_WATER_ALPHA", "WATER", bp7, Point3(-42.0, 73.0, 10.0),
                    "DEVELOPMENT_PACKAGING_SEED_REQUIRES_ROUTING_AND_COLLISION_CLOSURE", None, None, None),
        PumpStation("PUMP_CLEANSER_ALPHA", "CLEANSER", bp7, Point3(42.0, 73.0, 10.0),
                    "DEVELOPMENT_PACKAGING_SEED_REQUIRES_ROUTING_AND_COLLISION_CLOSURE", None, None, None),
    )
    introduced = authority.number("fluid", "clean_cycle", "nominal_introduced_liquid_mL")
    calculated = sum(authority.number("fluid", "clean_cycle", key) for key in (
        "face_water_mL", "cleanser_mL", "post_flush_water_mL"
    ))
    if not math.isclose(introduced, calculated, abs_tol=1e-9):
        raise FreshFluidArchitectureError("Clean-cycle authority ledger is inconsistent")
    return FreshFluidArchitecture(
        reservoir, cleanser, stations,
        ("ROUTE_WATER_RESERVOIR_TO_PUMP", "ROUTE_WATER_PUMP_TO_MANIFOLD_I23",
         "ROUTE_CLEANSER_STORAGE_TO_PUMP", "ROUTE_CLEANSER_PUMP_TO_MANIFOLD_I23"),
        introduced,
        authority.number("fluid", "clean_cycle", "maximum_initial_prime_mL"),
        "ITERATIONS20_22_RESERVOIR_CLEANSER_AND_DUAL_PUMP_PACKAGING_ARCHITECTURE",
        "NOT_FILL_VENT_PURGE_COMPATIBILITY_METERING_ROUTING_LEAK_OR_SERVICE_VALIDATION",
    )
