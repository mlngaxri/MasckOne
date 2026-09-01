"""Evidence-bounded fresh-fluid manifold branching and metering topology.

Iteration 23 reserves the authority-defined outlet count behind two isolated fluid
branches. Outlet placement/direction belongs to Iteration 24. Branch bores,
restrictions, pressure drop, flow balance, and physical performance remain blocked.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import re

from .authority import Authority
from .cleanser_storage import CleanserStorageArchitecture
from .fresh_pump_packaging import (
    FLUID_CLEANSER,
    FLUID_FRESH_WATER,
    ROUTE_CLEANSER_MANIFOLD,
    ROUTE_WATER_MANIFOLD,
    FreshPumpPackagingArchitecture,
    FreshPumpPackagingError,
)
from .structural_frame import StructuralFrameTopology
from .water_reservoir import WaterReservoirArchitecture


class DistributionManifoldError(ValueError):
    """Raised when Iteration 23 provenance or evidence boundaries are violated."""


BRANCH_FRESH_WATER = "MANIFOLD-BRANCH-FRESH-WATER"
BRANCH_CLEANSER = "MANIFOLD-BRANCH-CLEANSER"
BRANCH_IDS = (BRANCH_FRESH_WATER, BRANCH_CLEANSER)

INLET_FRESH_WATER = "MANIFOLD-INLET-WATER-I23"
INLET_CLEANSER = "MANIFOLD-INLET-CLEANSER-I23"

OUTLET_COUNT_STATUS = "VALIDATION_GATED_DESIGN_BASELINE"
AUTHORITY_GEOMETRY_STATUS = "ENGINEERING_BASELINE"
OUTLET_REALIZATION_STATUS = "RESERVATION_ONLY_POSITION_AND_DIRECTION_DEFERRED_TO_ITERATION24"
BRANCH_GEOMETRY_STATUS = "TOPOLOGY_ONLY_BORE_RESTRICTION_AND_CENTERLINES_UNRESOLVED"
PRESSURE_DROP_STATUS = "BLOCKED_PENDING_CONTROLLED_BORE_RESTRICTION_FLUID_PROPERTIES_AND_PUMP_CURVES"
FLOW_BALANCE_STATUS = "BLOCKED_PENDING_CONTROLLED_GEOMETRY_AND_METERING_RIG_EVIDENCE"
ARCHITECTURE_EVIDENCE_STATUS = (
    "DIGITAL_MANIFOLD_BRANCH_AND_OUTLET_RESERVATION_ONLY_NOT_METERING_PRESSURE_DROP_"
    "FLOW_BALANCE_DISTRIBUTION_LEAKAGE_SERVICE_OR_PHYSICAL_EVIDENCE"
)

_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


def _exact_text(value: object, *, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise DistributionManifoldError(f"{label} must be exact built-in nonblank text")
    return value


def _sha(value: object, *, label: str) -> str:
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
        raise DistributionManifoldError(f"{label} must be a canonical lowercase SHA-256")
    return value


def _real(value: object, *, label: str, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DistributionManifoldError(f"{label} must be a finite real number")
    result = float(value)
    if not math.isfinite(result):
        raise DistributionManifoldError(f"{label} must be finite")
    if positive and result <= 0.0:
        raise DistributionManifoldError(f"{label} must be positive")
    if not positive and result < 0.0:
        raise DistributionManifoldError(f"{label} must be non-negative")
    return result


def _positive_int(value: object, *, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise DistributionManifoldError(f"{label} must be an exact positive integer")
    return value


def _outlet_id(fluid_identity: str, sequence_index: int) -> str:
    return f"MANIFOLD-OUTLET-{fluid_identity}-{sequence_index:02d}"


@dataclass(frozen=True, slots=True)
class ManifoldOutletReservation:
    outlet_id: str
    branch_id: str
    fluid_identity: str
    sequence_index: int
    diameter_seed_mm: float
    position_sensitivity_mm: float
    direction_sensitivity_deg: float
    position_xyz_mm: tuple[float, float, float] | None
    direction_xyz: tuple[float, float, float] | None
    realization_status: str

    def __post_init__(self) -> None:
        _exact_text(self.outlet_id, label="manifold outlet ID")
        if type(self.branch_id) is not str or self.branch_id not in BRANCH_IDS:
            raise DistributionManifoldError("manifold outlet branch ID is not controlled")
        expected_branch = {
            FLUID_FRESH_WATER: BRANCH_FRESH_WATER,
            FLUID_CLEANSER: BRANCH_CLEANSER,
        }
        if type(self.fluid_identity) is not str or self.fluid_identity not in expected_branch:
            raise DistributionManifoldError("manifold outlet fluid identity is not controlled")
        if self.branch_id != expected_branch[self.fluid_identity]:
            raise DistributionManifoldError("manifold outlet cannot cross fluid branches")
        sequence = _positive_int(self.sequence_index, label="manifold outlet sequence")
        if self.outlet_id != _outlet_id(self.fluid_identity, sequence):
            raise DistributionManifoldError("manifold outlet ID must derive from fluid identity and sequence")
        diameter = _real(self.diameter_seed_mm, label="outlet diameter seed", positive=True)
        position_sensitivity = _real(
            self.position_sensitivity_mm,
            label="outlet position sensitivity",
        )
        direction_sensitivity = _real(
            self.direction_sensitivity_deg,
            label="outlet direction sensitivity",
        )
        if self.position_xyz_mm is not None or self.direction_xyz is not None:
            raise DistributionManifoldError(
                "Iteration 23 cannot assign outlet positions or directions before Iteration 24"
            )
        if type(self.realization_status) is not str or self.realization_status != OUTLET_REALIZATION_STATUS:
            raise DistributionManifoldError("outlet realization status must use the controlled deferred state")
        object.__setattr__(self, "diameter_seed_mm", diameter)
        object.__setattr__(self, "position_sensitivity_mm", position_sensitivity)
        object.__setattr__(self, "direction_sensitivity_deg", direction_sensitivity)

    def manifest(self) -> dict[str, object]:
        return {
            "outlet_id": self.outlet_id,
            "branch_id": self.branch_id,
            "fluid_identity": self.fluid_identity,
            "sequence_index": self.sequence_index,
            "diameter_seed_mm": self.diameter_seed_mm,
            "position_sensitivity_mm": self.position_sensitivity_mm,
            "direction_sensitivity_deg": self.direction_sensitivity_deg,
            "position_xyz_mm": self.position_xyz_mm,
            "direction_xyz": self.direction_xyz,
            "realization_status": self.realization_status,
        }


@dataclass(frozen=True, slots=True)
class ManifoldBranch:
    branch_id: str
    fluid_identity: str
    upstream_route_id: str
    inlet_interface_id: str
    outlet_ids: tuple[str, ...]
    nominal_inner_diameter_mm: float | None
    metering_restriction_geometry_mm: tuple[float, ...] | None
    centerline_xyz_mm: tuple[tuple[float, float, float], ...] | None
    geometry_status: str
    pressure_drop_status: str
    flow_balance_status: str

    def __post_init__(self) -> None:
        expected = {
            BRANCH_FRESH_WATER: (FLUID_FRESH_WATER, ROUTE_WATER_MANIFOLD, INLET_FRESH_WATER),
            BRANCH_CLEANSER: (FLUID_CLEANSER, ROUTE_CLEANSER_MANIFOLD, INLET_CLEANSER),
        }
        if type(self.branch_id) is not str or self.branch_id not in expected:
            raise DistributionManifoldError("manifold branch ID is not controlled")
        actual = (self.fluid_identity, self.upstream_route_id, self.inlet_interface_id)
        if any(type(value) is not str for value in actual) or actual != expected[self.branch_id]:
            raise DistributionManifoldError("manifold branch cannot cross or alias its fluid inlet")
        if type(self.outlet_ids) is not tuple or not self.outlet_ids:
            raise DistributionManifoldError("manifold branch requires an immutable nonempty outlet tuple")
        if any(type(value) is not str for value in self.outlet_ids):
            raise DistributionManifoldError("manifold branch outlet IDs must be exact built-in strings")
        if len(self.outlet_ids) != len(set(self.outlet_ids)):
            raise DistributionManifoldError("manifold branch outlet IDs cannot repeat")
        if any(
            value is not None
            for value in (
                self.nominal_inner_diameter_mm,
                self.metering_restriction_geometry_mm,
                self.centerline_xyz_mm,
            )
        ):
            raise DistributionManifoldError(
                "Iteration 23 cannot invent branch bore, restriction, or centerline geometry"
            )
        controlled = (
            (self.geometry_status, BRANCH_GEOMETRY_STATUS, "branch geometry status"),
            (self.pressure_drop_status, PRESSURE_DROP_STATUS, "branch pressure-drop status"),
            (self.flow_balance_status, FLOW_BALANCE_STATUS, "branch flow-balance status"),
        )
        for value, expected_value, label in controlled:
            if type(value) is not str or value != expected_value:
                raise DistributionManifoldError(f"{label} must use its controlled evidence state")

    def manifest(self) -> dict[str, object]:
        return {
            "branch_id": self.branch_id,
            "fluid_identity": self.fluid_identity,
            "upstream_route_id": self.upstream_route_id,
            "inlet_interface_id": self.inlet_interface_id,
            "outlet_ids": list(self.outlet_ids),
            "nominal_inner_diameter_mm": self.nominal_inner_diameter_mm,
            "metering_restriction_geometry_mm": self.metering_restriction_geometry_mm,
            "centerline_xyz_mm": self.centerline_xyz_mm,
            "geometry_status": self.geometry_status,
            "pressure_drop_status": self.pressure_drop_status,
            "flow_balance_status": self.flow_balance_status,
        }


@dataclass(frozen=True, slots=True)
class DistributionManifoldArchitecture:
    source_authority_revision: str
    source_pump_architecture_sha256: str
    water_outlet_count: int
    cleanser_outlet_count: int
    outlet_diameter_seed_mm: float
    outlet_position_sensitivity_mm: float
    outlet_direction_sensitivity_deg: float
    outlet_count_status: str
    authority_geometry_status: str
    branches: tuple[ManifoldBranch, ...]
    outlets: tuple[ManifoldOutletReservation, ...]
    physical_validation_eligible: bool
    evidence_status: str

    def __post_init__(self) -> None:
        _exact_text(self.source_authority_revision, label="source authority revision")
        _sha(self.source_pump_architecture_sha256, label="source pump architecture")
        water_count = _positive_int(self.water_outlet_count, label="water outlet count")
        cleanser_count = _positive_int(self.cleanser_outlet_count, label="cleanser outlet count")
        diameter = _real(self.outlet_diameter_seed_mm, label="outlet diameter seed", positive=True)
        position_sensitivity = _real(
            self.outlet_position_sensitivity_mm,
            label="outlet position sensitivity",
        )
        direction_sensitivity = _real(
            self.outlet_direction_sensitivity_deg,
            label="outlet direction sensitivity",
        )
        if type(self.outlet_count_status) is not str or self.outlet_count_status != OUTLET_COUNT_STATUS:
            raise DistributionManifoldError("outlet count status must use the controlled authority state")
        if type(self.authority_geometry_status) is not str or self.authority_geometry_status != AUTHORITY_GEOMETRY_STATUS:
            raise DistributionManifoldError("authority geometry status must use the controlled authority state")
        if type(self.branches) is not tuple or tuple(type(item) for item in self.branches) != (
            ManifoldBranch,
            ManifoldBranch,
        ):
            raise DistributionManifoldError("manifold branches must be an exact immutable two-branch tuple")
        if tuple(item.branch_id for item in self.branches) != BRANCH_IDS:
            raise DistributionManifoldError("manifold branches must retain controlled fluid order")
        if type(self.outlets) is not tuple or any(
            type(item) is not ManifoldOutletReservation for item in self.outlets
        ):
            raise DistributionManifoldError("manifold outlets must be an immutable tuple of exact reservations")
        expected_outlets = tuple(
            _outlet_id(fluid, index)
            for fluid, count in (
                (FLUID_FRESH_WATER, water_count),
                (FLUID_CLEANSER, cleanser_count),
            )
            for index in range(1, count + 1)
        )
        if tuple(item.outlet_id for item in self.outlets) != expected_outlets:
            raise DistributionManifoldError("manifold outlets must retain complete controlled identity and order")
        expected_branch_outlets = (
            expected_outlets[:water_count],
            expected_outlets[water_count:],
        )
        if tuple(item.outlet_ids for item in self.branches) != expected_branch_outlets:
            raise DistributionManifoldError("manifold branch outlet ownership cannot cross, omit, or alias")
        expected_numeric = (diameter, position_sensitivity, direction_sensitivity)
        if any(
            (
                item.diameter_seed_mm,
                item.position_sensitivity_mm,
                item.direction_sensitivity_deg,
            )
            != expected_numeric
            for item in self.outlets
        ):
            raise DistributionManifoldError("outlet reservations must retain architecture sensitivity values")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise DistributionManifoldError("digital manifold topology cannot be physical validation evidence")
        if type(self.evidence_status) is not str or self.evidence_status != ARCHITECTURE_EVIDENCE_STATUS:
            raise DistributionManifoldError("manifold evidence status must use the controlled architecture state")
        object.__setattr__(self, "outlet_diameter_seed_mm", diameter)
        object.__setattr__(self, "outlet_position_sensitivity_mm", position_sensitivity)
        object.__setattr__(self, "outlet_direction_sensitivity_deg", direction_sensitivity)

    def validate_current_sources(
        self,
        *,
        authority: Authority,
        pump: FreshPumpPackagingArchitecture,
        water: WaterReservoirArchitecture,
        cleanser: CleanserStorageArchitecture,
        frame: StructuralFrameTopology,
    ) -> None:
        if type(authority) is not Authority:
            raise DistributionManifoldError("authority must be an exact Authority contract")
        if type(pump) is not FreshPumpPackagingArchitecture:
            raise DistributionManifoldError("pump must be an exact FreshPumpPackagingArchitecture")
        try:
            pump.validate_current_sources(
                authority=authority,
                water=water,
                cleanser=cleanser,
                frame=frame,
            )
        except FreshPumpPackagingError as exc:
            raise DistributionManifoldError("pump architecture is stale for current sources") from exc
        if self.source_pump_architecture_sha256 != pump.architecture_sha256:
            raise DistributionManifoldError("manifold is stale for current pump architecture")
        expected = (
            str(authority.get("project", "authority_revision")),
            int(authority.get("fluid", "outlets", "water_count_first_manifold")),
            int(authority.get("fluid", "outlets", "cleanser_count_first_manifold")),
            authority.number("fluid", "outlets", "manifold_outlet_diameter_seed_mm"),
            authority.number("fluid", "outlets", "outlet_position_sensitivity_mm"),
            authority.number("fluid", "outlets", "outlet_direction_sensitivity_deg"),
            str(authority.get("fluid", "outlets", "count_status")),
            str(authority.get("fluid", "outlets", "geometry_status")),
        )
        actual = (
            self.source_authority_revision,
            self.water_outlet_count,
            self.cleanser_outlet_count,
            self.outlet_diameter_seed_mm,
            self.outlet_position_sensitivity_mm,
            self.outlet_direction_sensitivity_deg,
            self.outlet_count_status,
            self.authority_geometry_status,
        )
        if actual != expected:
            raise DistributionManifoldError("manifold authority inputs are stale")

    @property
    def architecture_sha256(self) -> str:
        raw = json.dumps(
            self.manifest(include_sha=False),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "source_authority_revision": self.source_authority_revision,
            "source_pump_architecture_sha256": self.source_pump_architecture_sha256,
            "water_outlet_count": self.water_outlet_count,
            "cleanser_outlet_count": self.cleanser_outlet_count,
            "outlet_diameter_seed_mm": self.outlet_diameter_seed_mm,
            "outlet_position_sensitivity_mm": self.outlet_position_sensitivity_mm,
            "outlet_direction_sensitivity_deg": self.outlet_direction_sensitivity_deg,
            "outlet_count_status": self.outlet_count_status,
            "authority_geometry_status": self.authority_geometry_status,
            "branches": [item.manifest() for item in self.branches],
            "outlets": [item.manifest() for item in self.outlets],
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            payload["architecture_sha256"] = self.architecture_sha256
        return payload


def build_distribution_manifold_architecture(
    authority: Authority,
    pump: FreshPumpPackagingArchitecture,
    water: WaterReservoirArchitecture,
    cleanser: CleanserStorageArchitecture,
    frame: StructuralFrameTopology,
) -> DistributionManifoldArchitecture:
    if type(authority) is not Authority:
        raise DistributionManifoldError("authority must be an exact Authority contract")
    if type(pump) is not FreshPumpPackagingArchitecture:
        raise DistributionManifoldError("pump must be an exact FreshPumpPackagingArchitecture")
    water_count = int(authority.get("fluid", "outlets", "water_count_first_manifold"))
    cleanser_count = int(authority.get("fluid", "outlets", "cleanser_count_first_manifold"))
    diameter = authority.number("fluid", "outlets", "manifold_outlet_diameter_seed_mm")
    position_sensitivity = authority.number("fluid", "outlets", "outlet_position_sensitivity_mm")
    direction_sensitivity = authority.number("fluid", "outlets", "outlet_direction_sensitivity_deg")

    outlets = tuple(
        ManifoldOutletReservation(
            outlet_id=_outlet_id(fluid_identity, index),
            branch_id=branch_id,
            fluid_identity=fluid_identity,
            sequence_index=index,
            diameter_seed_mm=diameter,
            position_sensitivity_mm=position_sensitivity,
            direction_sensitivity_deg=direction_sensitivity,
            position_xyz_mm=None,
            direction_xyz=None,
            realization_status=OUTLET_REALIZATION_STATUS,
        )
        for fluid_identity, branch_id, count in (
            (FLUID_FRESH_WATER, BRANCH_FRESH_WATER, water_count),
            (FLUID_CLEANSER, BRANCH_CLEANSER, cleanser_count),
        )
        for index in range(1, count + 1)
    )
    common_branch = {
        "nominal_inner_diameter_mm": None,
        "metering_restriction_geometry_mm": None,
        "centerline_xyz_mm": None,
        "geometry_status": BRANCH_GEOMETRY_STATUS,
        "pressure_drop_status": PRESSURE_DROP_STATUS,
        "flow_balance_status": FLOW_BALANCE_STATUS,
    }
    branches = (
        ManifoldBranch(
            branch_id=BRANCH_FRESH_WATER,
            fluid_identity=FLUID_FRESH_WATER,
            upstream_route_id=ROUTE_WATER_MANIFOLD,
            inlet_interface_id=INLET_FRESH_WATER,
            outlet_ids=tuple(item.outlet_id for item in outlets if item.fluid_identity == FLUID_FRESH_WATER),
            **common_branch,
        ),
        ManifoldBranch(
            branch_id=BRANCH_CLEANSER,
            fluid_identity=FLUID_CLEANSER,
            upstream_route_id=ROUTE_CLEANSER_MANIFOLD,
            inlet_interface_id=INLET_CLEANSER,
            outlet_ids=tuple(item.outlet_id for item in outlets if item.fluid_identity == FLUID_CLEANSER),
            **common_branch,
        ),
    )
    architecture = DistributionManifoldArchitecture(
        source_authority_revision=str(authority.get("project", "authority_revision")),
        source_pump_architecture_sha256=pump.architecture_sha256,
        water_outlet_count=water_count,
        cleanser_outlet_count=cleanser_count,
        outlet_diameter_seed_mm=diameter,
        outlet_position_sensitivity_mm=position_sensitivity,
        outlet_direction_sensitivity_deg=direction_sensitivity,
        outlet_count_status=str(authority.get("fluid", "outlets", "count_status")),
        authority_geometry_status=str(authority.get("fluid", "outlets", "geometry_status")),
        branches=branches,
        outlets=outlets,
        physical_validation_eligible=False,
        evidence_status=ARCHITECTURE_EVIDENCE_STATUS,
    )
    architecture.validate_current_sources(
        authority=authority,
        pump=pump,
        water=water,
        cleanser=cleanser,
        frame=frame,
    )
    return architecture
