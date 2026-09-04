from __future__ import annotations

"""Manual B power, electronics, HMI and thermal packaging candidate.

This layer is geometry owning for the integrated MVP CAD candidate. It consumes the
current Manual A mechanical realization as a read-only dependency and keeps supplier,
firmware, ingress, thermal, endurance and physical validation claims explicitly open.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math

import cadquery as cq

from .authority import Authority, load_authority
from .mechanical_integration import MechanicalRealization, build_mechanical_realization
from .model import MasckOneModel, build_model

SCHEMA = "MASCK_ONE_MANUAL_B_POWER_ELECTRONICS_HMI_THERMAL_V1"
SOURCE_MAIN_SHA = "b2c2d2d94972e4615e281e86e2feddaaa3c4e0c8"
SOURCE_MANUAL_A_HEAD_SHA = "d49966019e03132edd95d0ad8a390d285a0740c7"
SOURCE_EXTERIOR_HEAD_SHA = "aa250eba05b594c085be4c374f784f20f705750d"
SOURCE_FLUID_HEAD_SHA = "4b08dc4b111b3d7795c282cbf178876050a58bdf"

DIGITAL_ONLY = "DIGITAL_CAD_PACKAGE_NOT_PHYSICAL_VALIDATION"
CAD_PLACEHOLDER = "CAD_PLACEHOLDER_NOT_SELECTED_HARDWARE"
DECISION_GATED = "FORMAL_PRODUCT_DECISION_REQUIRED_BEFORE_CONTROL_MAPPING_FREEZE"

# Design/CAD baselines. These are intentionally not supplier or physical requirements.
BATTERY_FAULT_CLEARANCE_XY_MM = 1.5
BATTERY_FAULT_CLEARANCE_Z_MM = 2.0
BATTERY_CARRIER_WALL_MM = 1.2
PCB_PLACEHOLDER_ENVELOPE_MM = (48.0, 26.0, 1.6)
PCB_EDGE_CLEARANCE_MM = 2.0
DRY_BAY_OUTER_MM = (62.0, 96.0, 16.0)
DRY_BAY_CENTER_MM = (0.0, 0.0, -34.0)
DRY_BAY_WALL_MM = 1.5
DRY_BAY_DOOR_MM = (58.0, 92.0, 1.8)
HARNESS_CLEARANCE_RADIUS_MM = 1.4
CONTROL_TRAVEL_RESERVATION_MM = 1.2
CONTROL_PANEL_DEPTH_MM = 2.4
CHARGING_RESERVATION_MM = (10.0, 8.0, 6.0)
WARM_MODULE_MM = (22.0, 28.0, 2.4)
COOL_RESERVATION_MM = (24.0, 12.0, 4.0)

CONTROL_IDS = ("CLEAN", "POWER", "WARM", "COOL")
LOAD_IDS = (
    "ACTUATORS_X4",
    "FRESH_WATER_PUMP",
    "CLEANSER_PUMP",
    "WASTE_PUMP",
    "CONTROL_ELECTRONICS",
    "PHYSICAL_HMI_STATUS",
    "WARM",
    "COOL_EXPERIMENTAL",
)


class ElectronicsPackageError(ValueError):
    pass


def _text(value: object, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise ElectronicsPackageError(f"{label} must be exact nonblank text")
    return value


def _finite(value: object, label: str, *, positive: bool = False, nonnegative: bool = False) -> float:
    if type(value) not in (int, float):
        raise ElectronicsPackageError(f"{label} must be an exact numeric scalar")
    result = float(value)
    if not math.isfinite(result):
        raise ElectronicsPackageError(f"{label} must be finite")
    if positive and result <= 0.0:
        raise ElectronicsPackageError(f"{label} must be positive")
    if nonnegative and result < 0.0:
        raise ElectronicsPackageError(f"{label} must be non-negative")
    return 0.0 if result == 0.0 else result


def _point(value: object, label: str) -> tuple[float, float, float]:
    if type(value) is not tuple or len(value) != 3:
        raise ElectronicsPackageError(f"{label} must be an exact XYZ tuple")
    return tuple(_finite(v, f"{label}[{i}]") for i, v in enumerate(value))  # type: ignore[return-value]


def _box(size: tuple[float, float, float], center: tuple[float, float, float]) -> cq.Workplane:
    x, y, z = tuple(_finite(v, "box dimension", positive=True) for v in size)
    cx, cy, cz = _point(center, "box center")
    return cq.Workplane("XY").box(x, y, z, centered=(True, True, True)).translate((cx, cy, cz))


def _bbox_manifest(solid: cq.Workplane) -> dict[str, object]:
    shape = solid.val()
    if not shape.isValid() or float(shape.Volume()) <= 0.0:
        raise ElectronicsPackageError("package solid must be valid and positive-volume")
    bb = shape.BoundingBox()
    return {
        "min_mm": [float(bb.xmin), float(bb.ymin), float(bb.zmin)],
        "max_mm": [float(bb.xmax), float(bb.ymax), float(bb.zmax)],
        "spans_mm": [float(bb.xlen), float(bb.ylen), float(bb.zlen)],
        "volume_mm3": float(shape.Volume()),
    }


def _intersection_volume(first: cq.Workplane, second: cq.Workplane) -> float:
    value = float(first.val().intersect(second.val()).Volume())
    if not math.isfinite(value) or value < 0.0:
        raise ElectronicsPackageError("intersection volume must be finite and non-negative")
    return 0.0 if value < 1e-9 else value


def _polyline_clearance_solid(points: tuple[tuple[float, float, float], ...], radius_mm: float) -> cq.Workplane:
    radius = _finite(radius_mm, "clearance radius", positive=True)
    if type(points) is not tuple or len(points) < 2:
        raise ElectronicsPackageError("route requires at least two exact points")
    canonical = tuple(_point(point, f"route point {i}") for i, point in enumerate(points))
    solids: list[cq.Shape] = []
    for a, b in zip(canonical, canonical[1:]):
        dx, dy, dz = (b[i] - a[i] for i in range(3))
        length = math.sqrt(dx * dx + dy * dy + dz * dz)
        if length <= 0.0:
            raise ElectronicsPackageError("route span cannot have zero length")
        direction = cq.Vector(dx / length, dy / length, dz / length)
        solids.append(cq.Solid.makeCylinder(radius, length, cq.Vector(*a), direction))
    for point in canonical:
        solids.append(cq.Solid.makeSphere(radius, cq.Vector(*point)))
    result = cq.Workplane("XY").newObject([solids[0]])
    for solid in solids[1:]:
        result = result.union(cq.Workplane("XY").newObject([solid]))
    return result


@dataclass(frozen=True, slots=True)
class PackagePart:
    part_id: str
    role: str
    solid: cq.Workplane
    wet_dry_class: str
    geometry_status: str
    evidence_status: str = DIGITAL_ONLY

    def __post_init__(self) -> None:
        _text(self.part_id, "part_id")
        _text(self.role, "role")
        _text(self.wet_dry_class, "wet_dry_class")
        _text(self.geometry_status, "geometry_status")
        _text(self.evidence_status, "evidence_status")
        _bbox_manifest(self.solid)

    def manifest(self) -> dict[str, object]:
        return {
            "part_id": self.part_id,
            "role": self.role,
            "wet_dry_class": self.wet_dry_class,
            "geometry_status": self.geometry_status,
            "evidence_status": self.evidence_status,
            "geometry": _bbox_manifest(self.solid),
        }


@dataclass(frozen=True, slots=True)
class HarnessRoute:
    route_id: str
    source_interface_id: str
    target_interface_id: str
    centerline_xyz_mm: tuple[tuple[float, float, float], ...]
    clearance_radius_mm: float
    conductor_spec_status: str
    connector_status: str
    service_loop_status: str
    wet_boundary_status: str

    def __post_init__(self) -> None:
        for label, value in (
            ("route_id", self.route_id),
            ("source_interface_id", self.source_interface_id),
            ("target_interface_id", self.target_interface_id),
            ("conductor_spec_status", self.conductor_spec_status),
            ("connector_status", self.connector_status),
            ("service_loop_status", self.service_loop_status),
            ("wet_boundary_status", self.wet_boundary_status),
        ):
            _text(value, label)
        if self.source_interface_id == self.target_interface_id:
            raise ElectronicsPackageError("harness route cannot alias source and target")
        if type(self.centerline_xyz_mm) is not tuple or len(self.centerline_xyz_mm) < 2:
            raise ElectronicsPackageError("harness centerline must be a non-empty exact tuple")
        for i, point in enumerate(self.centerline_xyz_mm):
            _point(point, f"harness point {i}")
        _finite(self.clearance_radius_mm, "harness clearance radius", positive=True)
        _bbox_manifest(self.clearance_solid)

    @property
    def centerline_length_mm(self) -> float:
        total = 0.0
        for a, b in zip(self.centerline_xyz_mm, self.centerline_xyz_mm[1:]):
            total += math.dist(a, b)
        return total

    @property
    def clearance_solid(self) -> cq.Workplane:
        return _polyline_clearance_solid(self.centerline_xyz_mm, self.clearance_radius_mm)

    def manifest(self) -> dict[str, object]:
        return {
            "route_id": self.route_id,
            "source_interface_id": self.source_interface_id,
            "target_interface_id": self.target_interface_id,
            "centerline_xyz_mm": [list(p) for p in self.centerline_xyz_mm],
            "centerline_length_mm": self.centerline_length_mm,
            "clearance_radius_mm": self.clearance_radius_mm,
            "conductor_spec_status": self.conductor_spec_status,
            "connector_status": self.connector_status,
            "service_loop_status": self.service_loop_status,
            "wet_boundary_status": self.wet_boundary_status,
        }


@dataclass(frozen=True, slots=True)
class InterfaceDatum:
    interface_id: str
    owner_id: str
    role: str
    center_xyz_mm: tuple[float, float, float]
    access_axis_xyz: tuple[float, float, float]
    status: str

    def __post_init__(self) -> None:
        for label, value in (("interface_id", self.interface_id), ("owner_id", self.owner_id), ("role", self.role), ("status", self.status)):
            _text(value, label)
        _point(self.center_xyz_mm, "interface center")
        axis = _point(self.access_axis_xyz, "interface access axis")
        norm = math.sqrt(sum(value * value for value in axis))
        if not math.isclose(norm, 1.0, rel_tol=0.0, abs_tol=1e-12):
            raise ElectronicsPackageError("interface access axis must be unit length")

    def manifest(self) -> dict[str, object]:
        return {
            "interface_id": self.interface_id,
            "owner_id": self.owner_id,
            "role": self.role,
            "center_xyz_mm": list(self.center_xyz_mm),
            "access_axis_xyz": list(self.access_axis_xyz),
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class PhysicalControl:
    control_id: str
    hierarchy: str
    center_xyz_mm: tuple[float, float, float]
    tactile_land_mm: tuple[float, float]
    travel_reservation_mm: float
    accidental_activation_guard_mm: float
    mapping_status: str
    switch_status: str
    sealing_status: str

    def __post_init__(self) -> None:
        if self.control_id not in CONTROL_IDS:
            raise ElectronicsPackageError("control_id must use controlled four-control vocabulary")
        _text(self.hierarchy, "control hierarchy")
        _point(self.center_xyz_mm, "control center")
        if type(self.tactile_land_mm) is not tuple or len(self.tactile_land_mm) != 2:
            raise ElectronicsPackageError("tactile land must be an exact width/height tuple")
        for value in self.tactile_land_mm:
            _finite(value, "tactile land", positive=True)
        _finite(self.travel_reservation_mm, "control travel", positive=True)
        _finite(self.accidental_activation_guard_mm, "control guard", nonnegative=True)
        for label, value in (
            ("mapping_status", self.mapping_status),
            ("switch_status", self.switch_status),
            ("sealing_status", self.sealing_status),
        ):
            _text(value, label)

    @property
    def solid(self) -> cq.Workplane:
        width, height = self.tactile_land_mm
        return _box((width, height, CONTROL_PANEL_DEPTH_MM), self.center_xyz_mm)

    def manifest(self) -> dict[str, object]:
        return {
            "control_id": self.control_id,
            "hierarchy": self.hierarchy,
            "center_xyz_mm": list(self.center_xyz_mm),
            "tactile_land_mm": list(self.tactile_land_mm),
            "travel_reservation_mm": self.travel_reservation_mm,
            "accidental_activation_guard_mm": self.accidental_activation_guard_mm,
            "mapping_status": self.mapping_status,
            "switch_status": self.switch_status,
            "sealing_status": self.sealing_status,
            "geometry": _bbox_manifest(self.solid),
        }


@dataclass(frozen=True, slots=True)
class PowerLoad:
    load_id: str
    quantity: int
    nominal_voltage_V: float | None
    nominal_power_W: float | None
    source_class: str
    source_status: str
    measured: bool

    def __post_init__(self) -> None:
        if self.load_id not in LOAD_IDS:
            raise ElectronicsPackageError("power load ID is not controlled")
        if type(self.quantity) is not int or self.quantity <= 0:
            raise ElectronicsPackageError("power load quantity must be a positive exact integer")
        for label, value in (("nominal_voltage_V", self.nominal_voltage_V), ("nominal_power_W", self.nominal_power_W)):
            if value is not None:
                _finite(value, label, positive=True)
        _text(self.source_class, "source_class")
        _text(self.source_status, "source_status")
        if type(self.measured) is not bool:
            raise ElectronicsPackageError("measured flag must be an exact bool")

    def manifest(self) -> dict[str, object]:
        return {
            "load_id": self.load_id,
            "quantity": self.quantity,
            "nominal_voltage_V": self.nominal_voltage_V,
            "nominal_power_W": self.nominal_power_W,
            "source_class": self.source_class,
            "source_status": self.source_status,
            "measured": self.measured,
        }


@dataclass(frozen=True, slots=True)
class PowerLedger:
    battery_nominal_voltage_V: float
    battery_nameplate_capacity_mAh: float
    battery_source_status: str
    loads: tuple[PowerLoad, ...]
    total_power_W: None
    runtime_estimate_h: None
    runtime_validated: bool
    evidence_status: str

    def __post_init__(self) -> None:
        _finite(self.battery_nominal_voltage_V, "battery nominal voltage", positive=True)
        _finite(self.battery_nameplate_capacity_mAh, "battery nameplate capacity", positive=True)
        _text(self.battery_source_status, "battery source status")
        if tuple(load.load_id for load in self.loads) != LOAD_IDS:
            raise ElectronicsPackageError("power ledger loads must retain controlled order")
        if self.total_power_W is not None or self.runtime_estimate_h is not None:
            raise ElectronicsPackageError("runtime/power total cannot close while load evidence is unresolved")
        if type(self.runtime_validated) is not bool or self.runtime_validated:
            raise ElectronicsPackageError("runtime cannot be marked validated from nameplate arithmetic")
        _text(self.evidence_status, "power evidence status")

    def manifest(self) -> dict[str, object]:
        return {
            "battery_nominal_voltage_V": self.battery_nominal_voltage_V,
            "battery_nameplate_capacity_mAh": self.battery_nameplate_capacity_mAh,
            "battery_source_status": self.battery_source_status,
            "loads": [load.manifest() for load in self.loads],
            "total_power_W": self.total_power_W,
            "runtime_estimate_h": self.runtime_estimate_h,
            "runtime_validated": self.runtime_validated,
            "evidence_status": self.evidence_status,
        }


@dataclass(frozen=True, slots=True)
class InterferenceCheck:
    check_id: str
    first_id: str
    second_id: str
    intersection_volume_mm3: float
    status: str

    @property
    def passes(self) -> bool:
        return self.intersection_volume_mm3 == 0.0

    def manifest(self) -> dict[str, object]:
        return {
            "check_id": self.check_id,
            "first_id": self.first_id,
            "second_id": self.second_id,
            "intersection_volume_mm3": self.intersection_volume_mm3,
            "status": self.status,
            "passes": self.passes,
        }


@dataclass(frozen=True, slots=True)
class ElectronicsPackage:
    authority_revision: str
    source_main_sha: str
    source_manual_a_head_sha: str
    source_exterior_head_sha: str
    source_fluid_head_sha: str
    parts: tuple[PackagePart, ...]
    harness_routes: tuple[HarnessRoute, ...]
    controls: tuple[PhysicalControl, ...]
    interfaces: tuple[InterfaceDatum, ...]
    pcb_mounting_datums_xyz_mm: tuple[tuple[float, float, float], ...]
    power_ledger: PowerLedger
    interference_checks: tuple[InterferenceCheck, ...]
    battery_service_trajectory_xyz_mm: tuple[tuple[float, float, float], ...]
    door_service_trajectory_xyz_mm: tuple[tuple[float, float, float], ...]
    hmi_decision_status: str
    charging_status: str
    warm_status: str
    cool_status: str
    physical_validation_eligible: bool
    evidence_status: str

    def __post_init__(self) -> None:
        for value in (
            self.source_main_sha,
            self.source_manual_a_head_sha,
            self.source_exterior_head_sha,
            self.source_fluid_head_sha,
        ):
            if type(value) is not str or len(value) != 40 or any(ch not in "0123456789abcdef" for ch in value):
                raise ElectronicsPackageError("source commit identity must be exact lowercase Git SHA")
        _text(self.authority_revision, "authority_revision")
        part_ids = tuple(part.part_id for part in self.parts)
        if len(part_ids) != len(set(part_ids)):
            raise ElectronicsPackageError("electronics package part IDs cannot repeat")
        route_ids = tuple(route.route_id for route in self.harness_routes)
        if len(route_ids) != len(set(route_ids)):
            raise ElectronicsPackageError("harness route IDs cannot repeat")
        if tuple(control.control_id for control in self.controls) != CONTROL_IDS:
            raise ElectronicsPackageError("four-control geometry must retain CLEAN-first controlled order")
        interface_ids = tuple(item.interface_id for item in self.interfaces)
        if len(interface_ids) != len(set(interface_ids)):
            raise ElectronicsPackageError("package interface IDs cannot repeat")
        if type(self.pcb_mounting_datums_xyz_mm) is not tuple or len(self.pcb_mounting_datums_xyz_mm) != 4:
            raise ElectronicsPackageError("PCB requires four deterministic mounting datums")
        for point in self.pcb_mounting_datums_xyz_mm:
            _point(point, "PCB mounting datum")
        if any(not check.passes for check in self.interference_checks):
            failures = [check.check_id for check in self.interference_checks if not check.passes]
            raise ElectronicsPackageError(f"required-clear package interference remains: {failures}")
        for point in self.battery_service_trajectory_xyz_mm + self.door_service_trajectory_xyz_mm:
            _point(point, "service trajectory point")
        if self.hmi_decision_status != DECISION_GATED:
            raise ElectronicsPackageError("historical four-control versus current CLEAN-first mapping must remain decision gated")
        for label, value in (
            ("charging_status", self.charging_status),
            ("warm_status", self.warm_status),
            ("cool_status", self.cool_status),
            ("evidence_status", self.evidence_status),
        ):
            _text(value, label)
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise ElectronicsPackageError("digital electronics package is not physical validation evidence")

    @property
    def package_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        return sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "authority_revision": self.authority_revision,
            "sources": {
                "main_sha": self.source_main_sha,
                "manual_a_head_sha": self.source_manual_a_head_sha,
                "exterior_head_sha": self.source_exterior_head_sha,
                "fluid_head_sha": self.source_fluid_head_sha,
                "integration_semantics": "MANUAL_A_STACKED_EXACT_GEOMETRY; EXTERIOR_AND_FLUID_HEADS_READ_ONLY_UNMERGED_REFERENCES",
            },
            "parts": [part.manifest() for part in self.parts],
            "harness_routes": [route.manifest() for route in self.harness_routes],
            "controls": [control.manifest() for control in self.controls],
            "interfaces": [item.manifest() for item in self.interfaces],
            "pcb_mounting_datums_xyz_mm": [list(point) for point in self.pcb_mounting_datums_xyz_mm],
            "power_ledger": self.power_ledger.manifest(),
            "interference_checks": [check.manifest() for check in self.interference_checks],
            "battery_service_trajectory_xyz_mm": [list(p) for p in self.battery_service_trajectory_xyz_mm],
            "door_service_trajectory_xyz_mm": [list(p) for p in self.door_service_trajectory_xyz_mm],
            "hmi_decision_status": self.hmi_decision_status,
            "charging_status": self.charging_status,
            "warm_status": self.warm_status,
            "cool_status": self.cool_status,
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            payload["package_sha256"] = self.package_sha256
        return payload


def _part(parts: tuple[PackagePart, ...], part_id: str) -> PackagePart:
    matches = tuple(part for part in parts if part.part_id == part_id)
    if len(matches) != 1:
        raise ElectronicsPackageError(f"expected exactly one package part {part_id}")
    return matches[0]


def _mechanical_part(realization: MechanicalRealization, part_id: str) -> cq.Workplane:
    matches = tuple(part.solid for part in realization.realized_parts if part.part_id == part_id)
    if len(matches) != 1:
        raise ElectronicsPackageError(f"expected exact Manual A part {part_id}")
    return matches[0]


def _mechanical_sweep(realization: MechanicalRealization, sweep_id: str):
    matches = tuple(sweep for sweep in realization.service_sweeps if sweep.sweep_id == sweep_id)
    if len(matches) != 1:
        raise ElectronicsPackageError(f"expected exact Manual A service sweep {sweep_id}")
    return matches[0]


def _clear(check_id: str, first_id: str, first: cq.Workplane, second_id: str, second: cq.Workplane) -> InterferenceCheck:
    volume = _intersection_volume(first, second)
    return InterferenceCheck(check_id, first_id, second_id, volume, "PASS_DIGITAL_CLEAR" if volume == 0.0 else "FAIL_DIGITAL_INTERFERENCE")


def _build_parts(authority: Authority) -> tuple[PackagePart, ...]:
    bw, bh, bd = tuple(float(v) for v in authority.get("battery_reference", "envelope_mm"))
    battery_center = (0.0, -18.0, -34.0)
    battery = PackagePart(
        "BATTERY_REFERENCE",
        "benchmark pouch cell envelope placed close to head and inside rear halo field",
        _box((bw, bh, bd), battery_center),
        "DRY_ALWAYS",
        str(authority.get("battery_reference", "status")),
    )
    fault = PackagePart(
        "BATTERY_FAULT_CLEARANCE",
        "non-compressive swelling/fault clearance reservation around benchmark cell",
        _box((bw + 2.0 * BATTERY_FAULT_CLEARANCE_XY_MM, bh + 2.0 * BATTERY_FAULT_CLEARANCE_XY_MM, bd + 2.0 * BATTERY_FAULT_CLEARANCE_Z_MM), battery_center),
        "DRY_ALWAYS",
        "MANUAL_B_CAD_CLEARANCE_BASELINE_NOT_CELL_SUPPLIER_SWELLING_REQUIREMENT",
    )
    carrier_outer = _box((bw + 2.0 * (BATTERY_FAULT_CLEARANCE_XY_MM + BATTERY_CARRIER_WALL_MM), bh + 2.0 * (BATTERY_FAULT_CLEARANCE_XY_MM + BATTERY_CARRIER_WALL_MM), bd + 2.0 * (BATTERY_FAULT_CLEARANCE_Z_MM + BATTERY_CARRIER_WALL_MM)), battery_center)
    carrier = PackagePart(
        "BATTERY_CARRIER",
        "open rear-service carrier surrounding fault clearance without compressing the pouch faces",
        carrier_outer.cut(fault.solid),
        "DRY_ALWAYS",
        "MANUAL_B_CAD_CARRIER_BASELINE_FASTENER_MATERIAL_FLAMMABILITY_AND_CELL_RETENTION_PHYSICAL_EVIDENCE_OPEN",
    )
    pcb_center = (0.0, 31.0, -31.0)
    pcb = PackagePart(
        "PCB_CONTROL_PLACEHOLDER",
        "control PCB placeholder with perimeter connector access",
        _box(PCB_PLACEHOLDER_ENVELOPE_MM, pcb_center),
        "DRY_ALWAYS",
        CAD_PLACEHOLDER,
    )
    pcb_support = PackagePart(
        "PCB_SUPPORT_TRAY",
        "four-corner support and datum tray reservation around unselected PCB",
        _box((PCB_PLACEHOLDER_ENVELOPE_MM[0] + 2 * PCB_EDGE_CLEARANCE_MM, PCB_PLACEHOLDER_ENVELOPE_MM[1] + 2 * PCB_EDGE_CLEARANCE_MM, 2.4), (pcb_center[0], pcb_center[1], -33.0)),
        "DRY_ALWAYS",
        "MANUAL_B_CAD_SUPPORT_BASELINE_FASTENER_AND_BOARD_DATUM_PATTERN_NOT_SELECTED",
    )
    outer = _box(DRY_BAY_OUTER_MM, DRY_BAY_CENTER_MM)
    cavity = _box((DRY_BAY_OUTER_MM[0] - 2 * DRY_BAY_WALL_MM, DRY_BAY_OUTER_MM[1] - 2 * DRY_BAY_WALL_MM, DRY_BAY_OUTER_MM[2] - DRY_BAY_WALL_MM), (DRY_BAY_CENTER_MM[0], DRY_BAY_CENTER_MM[1], DRY_BAY_CENTER_MM[2] + DRY_BAY_WALL_MM / 2.0))
    dry_bay_shell = PackagePart(
        "DRY_BAY_SHELL",
        "shallow central rear dry-bay wall and wet-isolation boundary",
        outer.cut(cavity),
        "DRY_ALWAYS",
        "MANUAL_B_CAD_DRY_BAY_BASELINE_NOT_IP_RATING_OR_PRODUCTION_SEAL_EVIDENCE",
    )
    dry_bay_door = PackagePart(
        "DRY_BAY_DOOR",
        "rear service closure kept inside halo visual field",
        _box(DRY_BAY_DOOR_MM, (0.0, 0.0, -42.2)),
        "DRY_ALWAYS",
        "MANUAL_B_CAD_DOOR_BASELINE_SEAL_FASTENER_LATCH_AND_INGRESS_UNSELECTED",
    )
    charge = PackagePart(
        "CHARGING_INTERFACE_RESERVATION",
        "low-highlight left-lower rear charging receptacle and structural backing reservation",
        _box(CHARGING_RESERVATION_MM, (-25.5, -40.0, -33.0)),
        "SEALED_NONUSER",
        "CONNECTOR_TYPE_UNSELECTED_STRUCTURAL_AND_WET_DRY_RESERVATION_ONLY",
    )
    warm_left = PackagePart(
        "WARM_LEFT_RESERVATION",
        "sealed cheek-side heater/spreader/insulation stack reservation",
        _box(WARM_MODULE_MM, (-52.0, -4.0, -4.0)),
        "SEALED_NONUSER",
        "THERMAL_HARDWARE_SENSOR_LIMITS_AND_PHYSICAL_SKIN_SAFETY_EVIDENCE_UNRESOLVED",
    )
    warm_right = PackagePart(
        "WARM_RIGHT_RESERVATION",
        "sealed cheek-side heater/spreader/insulation stack reservation",
        _box(WARM_MODULE_MM, (52.0, -4.0, -4.0)),
        "SEALED_NONUSER",
        "THERMAL_HARDWARE_SENSOR_LIMITS_AND_PHYSICAL_SKIN_SAFETY_EVIDENCE_UNRESOLVED",
    )
    cool = PackagePart(
        "COOL_EXPERIMENTAL_RESERVATION",
        "bounded experimental dry thermal volume inside existing dry-bay depth",
        _box(COOL_RESERVATION_MM, (0.0, 31.0, -38.0)),
        "SEALED_NONUSER",
        "EXPERIMENTAL_RESERVATION_ONLY_NO_COOLING_OR_CONDENSATION_CLOSURE",
    )
    power_protection = PackagePart(
        "PCB_POWER_PROTECTION_ZONE",
        "board-level fuse/protection/charging-power reservation on the dry side",
        _box((12.0, 8.0, 1.0), (-14.0, 31.0, -29.5)),
        "DRY_ALWAYS",
        "BOARD_ZONE_RESERVATION_ONLY_FUSE_PROTECTION_IC_AND_CHARGER_COMPONENTS_UNSELECTED",
    )
    status_window = PackagePart(
        "STATUS_WINDOW_RESERVATION",
        "flush optical window reservation adjacent to CLEAN-first side controls",
        _box((10.0, 3.0, 1.2), (69.0, 39.0, 9.0)),
        "SEALED_NONUSER",
        "OPTICAL_STACK_LED_COUNT_COLOR_INTENSITY_AND_SEAL_UNSELECTED",
    )
    return (battery, fault, carrier, pcb, pcb_support, dry_bay_shell, dry_bay_door, charge, warm_left, warm_right, cool, power_protection, status_window)


def _build_controls() -> tuple[PhysicalControl, ...]:
    return (
        PhysicalControl("CLEAN", "PRIMARY_DOMINANT", (69.0, 25.0, 9.0), (11.0, 11.0), CONTROL_TRAVEL_RESERVATION_MM, 1.0, DECISION_GATED, "SWITCH_STACK_UNSELECTED", "FLUSH_SEALED_ACTUATOR_GEOMETRY_REQUIRED"),
        PhysicalControl("POWER", "SECONDARY", (69.0, 11.0, 9.0), (8.0, 8.0), CONTROL_TRAVEL_RESERVATION_MM, 1.2, DECISION_GATED, "SWITCH_STACK_UNSELECTED", "FLUSH_SEALED_ACTUATOR_GEOMETRY_REQUIRED"),
        PhysicalControl("WARM", "SECONDARY", (69.0, -2.0, 9.0), (8.0, 8.0), CONTROL_TRAVEL_RESERVATION_MM, 1.2, DECISION_GATED, "SWITCH_STACK_UNSELECTED", "FLUSH_SEALED_ACTUATOR_GEOMETRY_REQUIRED"),
        PhysicalControl("COOL", "SECONDARY_EXPERIMENTAL", (69.0, -15.0, 9.0), (8.0, 8.0), CONTROL_TRAVEL_RESERVATION_MM, 1.5, DECISION_GATED, "SWITCH_STACK_UNSELECTED", "FLUSH_SEALED_ACTUATOR_GEOMETRY_REQUIRED"),
    )


def _build_harness_routes() -> tuple[HarnessRoute, ...]:
    common = {
        "clearance_radius_mm": HARNESS_CLEARANCE_RADIUS_MM,
        "conductor_spec_status": "WIRE_GAUGE_INSULATION_TEMPERATURE_RATING_AND_BUNDLE_BUILD_UNSELECTED",
        "connector_status": "CONNECTOR_FAMILY_KEYING_RETENTION_AND_CURRENT_RATING_UNSELECTED",
        "wet_boundary_status": "DRY_SIDE_ROUTE_WITH_SEALED_BULKHEAD_RESERVATION_AT_WET_PACKAGE_HANDOFF",
    }
    def route(route_id: str, source: str, target: str, pts: tuple[tuple[float,float,float],...], loop: str="NO_EXTRA_SERVICE_LOOP_REQUIRED") -> HarnessRoute:
        return HarnessRoute(route_id, source, target, pts, service_loop_status=loop, **common)
    return (
        route("HARNESS-BATTERY-PCB", "BATTERY-CONNECTOR-ACCESS", "PCB-POWER-EDGE", ((0.0, 8.5, -34.0), (0.0, 14.0, -34.0), (0.0, 18.0, -31.0)), "SHORT_DISCONNECT_SLACK_RESERVED_INSIDE_DRY_BAY"),
        route("HARNESS-PCB-ACTUATOR-A", "PCB-ACT-A", "ACTUATOR-A-ELECTRICAL", ((-18.0, 31.0, -31.0), (-28.0, 45.0, -24.0), (-48.0, 58.0, -14.0), (-60.0, 66.0, -8.0))),
        route("HARNESS-PCB-ACTUATOR-B", "PCB-ACT-B", "ACTUATOR-B-ELECTRICAL", ((18.0, 31.0, -31.0), (28.0, 45.0, -24.0), (48.0, 58.0, -14.0), (60.0, 66.0, -8.0))),
        route("HARNESS-PCB-ACTUATOR-C", "PCB-ACT-C", "ACTUATOR-C-ELECTRICAL", ((-18.0, 23.0, -31.0), (-28.0, -12.0, -26.0), (-46.0, -45.0, -14.0), (-58.0, -60.0, -8.0))),
        route("HARNESS-PCB-ACTUATOR-D", "PCB-ACT-D", "ACTUATOR-D-ELECTRICAL", ((18.0, 23.0, -31.0), (28.0, -12.0, -26.0), (46.0, -45.0, -14.0), (58.0, -60.0, -8.0))),
        route("HARNESS-PCB-FRESH-WATER-PUMP", "PCB-PUMP-WATER", "WATER-PUMP-DRY-BULKHEAD", ((-14.0, 40.0, -31.0), (-20.0, 56.0, -24.0), (-28.0, 66.0, -14.0))),
        route("HARNESS-PCB-CLEANSER-PUMP", "PCB-PUMP-CLEANSER", "CLEANSER-PUMP-DRY-BULKHEAD", ((14.0, 40.0, -31.0), (20.0, 56.0, -24.0), (28.0, 66.0, -14.0))),
        route("HARNESS-PCB-WASTE-PUMP", "PCB-PUMP-WASTE", "WASTE-PUMP-DRY-BULKHEAD", ((0.0, 18.0, -31.0), (0.0, -20.0, -28.0), (0.0, -48.0, -20.0), (0.0, -58.0, -14.0))),
        route("HARNESS-PCB-HMI", "PCB-HMI-EDGE", "HMI-SIDE-PANEL", ((20.0, 36.0, -31.0), (40.0, 34.0, -24.0), (58.0, 30.0, -12.0), (65.0, 24.0, 5.0)), "LOCAL_FLEX_LOOP_RESERVED_BEHIND_SIDE_CONTROL_PANEL"),
        route("HARNESS-PCB-WARM-LEFT", "PCB-WARM-L", "WARM-LEFT-SEALED-FEED", ((-20.0, 20.0, -31.0), (-34.0, 10.0, -24.0), (-48.0, -2.0, -10.0))),
        route("HARNESS-PCB-WARM-RIGHT", "PCB-WARM-R", "WARM-RIGHT-SEALED-FEED", ((20.0, 20.0, -31.0), (34.0, 10.0, -24.0), (48.0, -2.0, -10.0))),
        route("HARNESS-PCB-COOL-RESERVATION", "PCB-THERMAL-EXP", "COOL-RESERVATION", ((0.0, 38.0, -31.0), (0.0, 34.0, -34.0), (0.0, 31.0, -36.0))),
        route("HARNESS-PCB-CHARGING", "PCB-CHARGE-EDGE", "CHARGING-DRY-SIDE", ((-18.0, 18.0, -31.0), (-23.0, -8.0, -31.0), (-23.0, -35.0, -33.0)), "CONNECTOR_SERVICE_SLACK_RESERVED_INSIDE_DRY_BAY"),
    )


def _build_interfaces(harness: tuple[HarnessRoute, ...]) -> tuple[InterfaceDatum, ...]:
    records: list[InterfaceDatum] = []
    seen: set[str] = set()
    for route in harness:
        for interface_id, point, axis, owner in (
            (route.source_interface_id, route.centerline_xyz_mm[0], (0.0, 0.0, -1.0), "PCB_OR_BATTERY_DRY_SIDE"),
            (route.target_interface_id, route.centerline_xyz_mm[-1], (0.0, 0.0, 1.0), "DOWNSTREAM_PACKAGE_HANDOFF"),
        ):
            if interface_id in seen:
                continue
            seen.add(interface_id)
            records.append(InterfaceDatum(interface_id, owner, "electrical harness interface datum", point, axis, "CAD_INTERFACE_DATUM_CONNECTOR_HARDWARE_UNSELECTED"))
    records.append(InterfaceDatum("CHARGING-USER-ACCESS", "CHARGING_INTERFACE_RESERVATION", "external charging access reservation", (-30.5, -40.0, -33.0), (-1.0, 0.0, 0.0), "USER_ACCESS_GEOMETRY_RESERVED_CONNECTOR_AND_INGRESS_UNSELECTED"))
    records.append(InterfaceDatum("STATUS-OPTICAL-WINDOW", "STATUS_WINDOW_RESERVATION", "status light/window optical interface", (69.0, 39.0, 9.0), (0.0, 0.0, 1.0), "OPTICAL_WINDOW_RESERVED_LED_AND_LIGHTPIPE_UNSELECTED"))
    return tuple(records)


def _build_power_ledger(authority: Authority) -> PowerLedger:
    unresolved = "BLOCKED_PENDING_SELECTED_HARDWARE_OR_CONTROLLED_SUPPLIER_POWER_EVIDENCE"
    loads = tuple(
        PowerLoad(load_id, quantity, None, None, "UNRESOLVED", unresolved, False)
        for load_id, quantity in (
            ("ACTUATORS_X4", 4),
            ("FRESH_WATER_PUMP", 1),
            ("CLEANSER_PUMP", 1),
            ("WASTE_PUMP", 1),
            ("CONTROL_ELECTRONICS", 1),
            ("PHYSICAL_HMI_STATUS", 1),
            ("WARM", 2),
            ("COOL_EXPERIMENTAL", 1),
        )
    )
    return PowerLedger(
        float(authority.get("battery_reference", "nominal_voltage_V")),
        float(authority.get("battery_reference", "capacity_mAh")),
        str(authority.get("battery_reference", "status")),
        loads,
        None,
        None,
        False,
        "NAMEPLATE_BATTERY_REFERENCE_AND_UNRESOLVED_LOAD_LEDGER_NOT_RUNTIME_EVIDENCE",
    )


def _service_sweep(solid: cq.Workplane, points: tuple[tuple[float,float,float],...]) -> tuple[cq.Workplane, ...]:
    if type(points) is not tuple or len(points) < 2:
        raise ElectronicsPackageError("service sweep needs at least two points")
    origin = points[0]
    return tuple(solid.translate(tuple(point[i] - origin[i] for i in range(3))) for point in points)


def build_electronics_package(authority: Authority | None = None) -> ElectronicsPackage:
    authority = authority or load_authority()
    if type(authority) is not Authority:
        raise TypeError("authority must be exact Authority")
    model: MasckOneModel = build_model(authority)
    mechanical = build_mechanical_realization(authority)
    parts = _build_parts(authority)
    controls = _build_controls()
    harness = _build_harness_routes()

    allowed_hygiene = set(authority.get("manufacturing", "hygiene_classes"))
    if any(part.wet_dry_class not in allowed_hygiene for part in parts):
        raise ElectronicsPackageError("electronics package uses wet/dry class outside frozen authority vocabulary")

    battery = _part(parts, "BATTERY_REFERENCE")
    fault = _part(parts, "BATTERY_FAULT_CLEARANCE")
    carrier = _part(parts, "BATTERY_CARRIER")
    pcb = _part(parts, "PCB_CONTROL_PLACEHOLDER")
    dry_bay = _part(parts, "DRY_BAY_SHELL")
    door = _part(parts, "DRY_BAY_DOOR")
    charge = _part(parts, "CHARGING_INTERFACE_RESERVATION")
    warm_left = _part(parts, "WARM_LEFT_RESERVATION")
    warm_right = _part(parts, "WARM_RIGHT_RESERVATION")
    cool = _part(parts, "COOL_EXPERIMENTAL_RESERVATION")
    power_protection = _part(parts, "PCB_POWER_PROTECTION_ZONE")
    status_window = _part(parts, "STATUS_WINDOW_RESERVATION")
    clearance_parts = (battery, fault, carrier, pcb, _part(parts, "PCB_SUPPORT_TRAY"), dry_bay, door, charge, warm_left, warm_right, cool, power_protection, status_window)

    # Internal nesting is intentional and checked separately from required-clear pairs.
    if _intersection_volume(battery.solid, fault.solid) <= 0.0:
        raise ElectronicsPackageError("battery must be contained by its fault-clearance reservation")
    if _intersection_volume(carrier.solid, battery.solid) > 0.0:
        raise ElectronicsPackageError("battery carrier must not compress the benchmark cell envelope")
    if _intersection_volume(carrier.solid, fault.solid) > 0.0:
        raise ElectronicsPackageError("battery carrier must remain outside fault-clearance reservation")

    checks: list[InterferenceCheck] = []
    # Exact Manual A owned geometry from the stacked branch.
    mechanical_obstacles = (
        "FRAME-PERIMETER-REACTION",
        "RETENTION-HALO-OCCIPITAL-CROWN",
        "RETENTION-YOKE-LEFT",
        "RETENTION-YOKE-RIGHT-FIXED",
        "QUICK-RELEASE-LATCH-MOVING",
    )
    for package_part in clearance_parts:
        for obstacle_id in mechanical_obstacles:
            checks.append(_clear(f"CLEAR-{package_part.part_id}-{obstacle_id}", package_part.part_id, package_part.solid, obstacle_id, _mechanical_part(mechanical, obstacle_id)))

    # Dry electronics must remain behind currently released wet package envelopes.
    for package_part in clearance_parts:
        for wet_id, wet_solid in (
            ("WATER_RESERVOIR_ENVELOPE", model.water_reservoir_envelope.solid),
            ("WASTE_CARTRIDGE_ENVELOPE", model.waste_cartridge_envelope.solid),
        ):
            checks.append(_clear(f"CLEAR-{package_part.part_id}-{wet_id}", package_part.part_id, package_part.solid, wet_id, wet_solid))

    # Harness clearance envelopes cannot cross released wet package or the exact release latch.
    release_latch = _mechanical_part(mechanical, "QUICK-RELEASE-LATCH-MOVING")
    for route in harness:
        for obstacle_id, obstacle in (
            ("WATER_RESERVOIR_ENVELOPE", model.water_reservoir_envelope.solid),
            ("WASTE_CARTRIDGE_ENVELOPE", model.waste_cartridge_envelope.solid),
            ("QUICK-RELEASE-LATCH-MOVING", release_latch),
        ):
            checks.append(_clear(f"CLEAR-{route.route_id}-{obstacle_id}", route.route_id, route.clearance_solid, obstacle_id, obstacle))

    # HMI controls must stay clear of the moving latch and released fluid packages.
    for control in controls:
        for obstacle_id, obstacle in (
            ("QUICK-RELEASE-LATCH-MOVING", release_latch),
            ("WATER_RESERVOIR_ENVELOPE", model.water_reservoir_envelope.solid),
            ("WASTE_CARTRIDGE_ENVELOPE", model.waste_cartridge_envelope.solid),
        ):
            checks.append(_clear(f"CLEAR-HMI-{control.control_id}-{obstacle_id}", f"HMI-{control.control_id}", control.solid, obstacle_id, obstacle))

    # Consume Manual A service motion, not only final-state parts. Electronics and harness
    # must remain clear through the complete sampled quick-release and cartridge sweeps.
    release_sweep = _mechanical_sweep(mechanical, "QUICK-RELEASE-OUTBOARD-WITHDRAWAL")
    cartridge_sweep = _mechanical_sweep(mechanical, "CARTRIDGE-DOWNWARD-REMOVAL")
    for sweep_id, sweep in ((release_sweep.sweep_id, release_sweep), (cartridge_sweep.sweep_id, cartridge_sweep)):
        samples = sweep.sampled_solids()
        for sample_index, obstacle in enumerate(samples):
            for package_part in clearance_parts:
                checks.append(_clear(f"CLEAR-{package_part.part_id}-{sweep_id}-S{sample_index}", package_part.part_id, package_part.solid, sweep_id, obstacle))
            for route in harness:
                checks.append(_clear(f"CLEAR-{route.route_id}-{sweep_id}-S{sample_index}", route.route_id, route.clearance_solid, sweep_id, obstacle))
            for control in controls:
                checks.append(_clear(f"CLEAR-HMI-{control.control_id}-{sweep_id}-S{sample_index}", f"HMI-{control.control_id}", control.solid, sweep_id, obstacle))

    battery_center = battery.solid.val().Center()
    battery_service = (
        (float(battery_center.x), float(battery_center.y), float(battery_center.z)),
        (float(battery_center.x), float(battery_center.y), -45.0),
        (float(battery_center.x), float(battery_center.y), -58.0),
        (float(battery_center.x), float(battery_center.y), -70.0),
    )
    door_center = door.solid.val().Center()
    door_service = (
        (float(door_center.x), float(door_center.y), float(door_center.z)),
        (float(door_center.x), float(door_center.y), -50.0),
        (float(door_center.x), float(door_center.y), -60.0),
    )
    service_obstacles = tuple(_mechanical_part(mechanical, identifier) for identifier in mechanical_obstacles)
    for sweep_id, moving, points in (
        ("BATTERY-REARWARD-SERVICE", battery.solid, battery_service),
        ("DRY-BAY-DOOR-REARWARD-SERVICE", door.solid, door_service),
    ):
        for sample_index, sample in enumerate(_service_sweep(moving, points)):
            for obstacle_id, obstacle in zip(mechanical_obstacles, service_obstacles, strict=True):
                checks.append(_clear(f"CLEAR-{sweep_id}-S{sample_index}-{obstacle_id}", sweep_id, sample, obstacle_id, obstacle))

    package = ElectronicsPackage(
        authority_revision=str(authority.get("project", "authority_revision")),
        source_main_sha=SOURCE_MAIN_SHA,
        source_manual_a_head_sha=SOURCE_MANUAL_A_HEAD_SHA,
        source_exterior_head_sha=SOURCE_EXTERIOR_HEAD_SHA,
        source_fluid_head_sha=SOURCE_FLUID_HEAD_SHA,
        parts=parts,
        harness_routes=harness,
        controls=controls,
        interfaces=_build_interfaces(harness),
        pcb_mounting_datums_xyz_mm=((-21.0, 21.0, -33.8), (21.0, 21.0, -33.8), (-21.0, 41.0, -33.8), (21.0, 41.0, -33.8)),
        power_ledger=_build_power_ledger(authority),
        interference_checks=tuple(checks),
        battery_service_trajectory_xyz_mm=battery_service,
        door_service_trajectory_xyz_mm=door_service,
        hmi_decision_status=DECISION_GATED,
        charging_status="PHYSICAL_RESERVATION_REALIZED_CONNECTOR_SUPPORT_SEAL_IP_RATING_CERTIFICATION_AND_CHARGING_WHILE_WET_NOT_AUTHORIZED",
        warm_status="DUAL_SEALED_WARM_PACKAGE_RESERVATIONS_REALIZED_HEATER_SENSOR_SPREADER_INSULATION_SELECTION_AND_SKIN_SAFETY_PHYSICAL_GATE_OPEN",
        cool_status="BOUNDED_EXPERIMENTAL_DRY_BAY_RESERVATION_ONLY_NO_MVP_DEPENDENCY_NO_CONDENSATION_OR_COOLING_CLAIM",
        physical_validation_eligible=False,
        evidence_status=DIGITAL_ONLY,
    )
    return package
