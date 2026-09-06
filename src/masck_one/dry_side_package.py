from __future__ import annotations

"""Source-bound Cell 12 battery, dry-bay, PCB and charging package.

Digital CAD packaging evidence only. This module does not select a production cell,
PCB, connector, charger, protection circuit, seal, fastener or material, and it does
not claim runtime, ingress, electrical safety or physical service performance.
"""

from dataclasses import dataclass
from hashlib import sha1, sha256
import json
import math
from pathlib import Path

import cadquery as cq

from .authority import Authority, load_authority
from .model import MasckOneModel, build_model

SCHEMA = "MASCK_ONE_CELL12_COMPACT_DRY_SIDE_PACKAGE_V1"
SOURCE_MAIN_SHA = "afe29ff78419b6625dca5594974b6351f6f80e1b"
AUTHORITY_REVISION = "2026-08-30-R1"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
LEGACY_DONOR_PR = 64
LEGACY_DONOR_HEAD_SHA = "49a32d0c61bd1057ee707ee2ef20b8ff4e6ede01"
LEGACY_DONOR_BLOB_SHA = "59e69a781e4ffcbb581a9f2835c9cb581b3939f2"
EVIDENCE_STATUS = "DIGITAL_DRY_SIDE_PACKAGING_ONLY_NOT_PHYSICAL_OR_ELECTRICAL_VALIDATION"

SOURCE_GIT_BLOB_IDENTITIES = (
    ("config/masck_one_authority.yaml", "2608dda483b995539de422290371c219668a1527"),
    ("src/masck_one/model.py", "9e7fa6c71ac28cc45ebb502444bf6c0ea49f7894"),
    ("src/masck_one/structural_frame.py", "bda5ba87d232c0e6a22e200975a80414a10c9a83"),
)

# PR #64 donor values retained only as labelled CAD reservation seeds. They are not
# supplier swelling limits or abuse-test evidence.
BATTERY_FAULT_CLEARANCE_XY_MM = 1.5
BATTERY_FAULT_CLEARANCE_Z_MM = 2.0

# Compact reflow replacing the stale PR #64 62 x 96 x 16 mm bay. These are Cell 12
# digital package baselines, not a released exterior or production drawing.
DRY_BAY_OUTER_MM = (48.0, 66.0, 22.0)
DRY_BAY_CENTER_MM = (0.0, 0.0, -36.0)
DRY_BAY_WALL_MM = 1.8
BATTERY_GUIDE_WALL_MM = 1.5
SUPPORT_RIB_THICKNESS_MM = 1.0
BATTERY_CENTER_MM = (0.0, -2.0, -39.0)
PCB_REFERENCE_MM = (38.0, 22.0, 1.6)
PCB_CENTER_MM = (0.0, 19.0, -29.4)
PCB_SUPPORT_MM = (40.0, 24.0, 1.2)
PCB_SUPPORT_CENTER_MM = (0.0, 19.0, -30.9)
POWER_ZONE_MM = (12.0, 8.0, 1.0)
POWER_ZONE_CENTER_MM = (-10.0, 19.0, -28.4)
DOOR_MM = (46.0, 64.0, 1.8)
DOOR_CENTER_MM = (0.0, 0.0, -47.9)
DOOR_CORNER_RADIUS_MM = 8.0
CHARGE_RESERVATION_MM = (10.0, 8.0, 4.0)
CHARGE_CENTER_MM = (-23.0, -26.0, -28.5)
BATTERY_SERVICE_END_Z_MM = -70.0
DOOR_SERVICE_END_Z_MM = -60.0

LOAD_IDS = (
    "ACTUATORS_X4",
    "FRESH_WATER_PUMP",
    "CLEANSER_PUMP",
    "WASTE_PUMP",
    "CONTROL_ELECTRONICS",
    "HMI_AND_THERMAL_AUXILIARIES",
)
_REPO_ROOT = Path(__file__).resolve().parents[2]


class DrySidePackageError(ValueError):
    pass


def _text(value: object, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise DrySidePackageError(f"{label} must be exact nonblank text")
    return value


def _finite(value: object, label: str, *, positive: bool = False) -> float:
    if type(value) not in (int, float):
        raise DrySidePackageError(f"{label} must be an exact numeric scalar")
    result = float(value)
    if not math.isfinite(result):
        raise DrySidePackageError(f"{label} must be finite")
    if positive and result <= 0.0:
        raise DrySidePackageError(f"{label} must be positive")
    return 0.0 if result == 0.0 else result


def _point(value: object, label: str) -> tuple[float, float, float]:
    if type(value) is not tuple or len(value) != 3:
        raise DrySidePackageError(f"{label} must be an exact XYZ tuple")
    return tuple(_finite(item, f"{label}[{index}]") for index, item in enumerate(value))  # type: ignore[return-value]


def _box(size: tuple[float, float, float], center: tuple[float, float, float]) -> cq.Workplane:
    sx, sy, sz = tuple(_finite(item, "box dimension", positive=True) for item in size)
    cx, cy, cz = _point(center, "box center")
    return cq.Workplane("XY").box(sx, sy, sz, centered=(True, True, True)).translate((cx, cy, cz))


def _geometry(solid: cq.Workplane) -> dict[str, object]:
    shape = solid.val()
    if not shape.isValid() or len(shape.Solids()) != 1 or float(shape.Volume()) <= 0.0:
        raise DrySidePackageError("dry-side geometry must be one valid positive-volume solid")
    bb = shape.BoundingBox()
    return {
        "min_mm": [float(bb.xmin), float(bb.ymin), float(bb.zmin)],
        "max_mm": [float(bb.xmax), float(bb.ymax), float(bb.zmax)],
        "spans_mm": [float(bb.xlen), float(bb.ylen), float(bb.zlen)],
        "volume_mm3": float(shape.Volume()),
    }


def _intersection(first: cq.Workplane, second: cq.Workplane) -> float:
    value = float(first.val().intersect(second.val()).Volume())
    if not math.isfinite(value) or value < 0.0:
        raise DrySidePackageError("intersection volume must be finite and non-negative")
    return 0.0 if value < 1e-8 else value


def _distance(first: cq.Workplane, second: cq.Workplane) -> float:
    value = float(first.val().distance(second.val()))
    if not math.isfinite(value) or value < 0.0:
        raise DrySidePackageError("B-rep distance must be finite and non-negative")
    return 0.0 if value < 1e-8 else value


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def _require_sources() -> None:
    for relative_path, expected in SOURCE_GIT_BLOB_IDENTITIES:
        path = _REPO_ROOT / relative_path
        if not path.is_file():
            raise DrySidePackageError(f"dry-side source file missing: {relative_path}")
        actual = _git_blob_sha(path)
        if actual != expected:
            raise DrySidePackageError(
                f"dry-side source moved at {relative_path}; expected {expected}, got {actual}"
            )


def _require_authority(authority: Authority) -> None:
    if type(authority) is not Authority:
        raise DrySidePackageError("dry-side package requires exact Authority type")
    canonical = load_authority()
    if authority.data != canonical.data:
        raise DrySidePackageError("supplied authority differs from released machine authority")
    if str(authority.get("project", "authority_revision")) != AUTHORITY_REVISION:
        raise DrySidePackageError("dry-side authority revision moved")
    expected = ("wearer_right", "superior", "anterior")
    actual = (
        authority.get("coordinate_system", "x_positive"),
        authority.get("coordinate_system", "y_positive"),
        authority.get("coordinate_system", "z_positive"),
    )
    if tuple(authority.get("coordinate_system", "origin")) != (0.0, 0.0, 0.0) or actual != expected:
        raise DrySidePackageError("dry-side package requires canonical world origin and axis signs")


@dataclass(frozen=True, slots=True)
class PackageGeometry:
    geometry_id: str
    role: str
    solid: cq.Workplane
    material_class: str
    hygiene_class: str
    geometry_status: str

    def __post_init__(self) -> None:
        for label, value in (
            ("geometry_id", self.geometry_id), ("role", self.role),
            ("material_class", self.material_class), ("hygiene_class", self.hygiene_class),
            ("geometry_status", self.geometry_status),
        ):
            _text(value, label)
        allowed = {"PHYSICAL_MATERIAL_CANDIDATE", "REFERENCE_ONLY", "SERVICE_SWEEP_REFERENCE", "SEAL_INTERFACE_RESERVATION"}
        if self.material_class not in allowed:
            raise DrySidePackageError("uncontrolled dry-side material class")
        _geometry(self.solid)

    def manifest(self) -> dict[str, object]:
        return {
            "geometry_id": self.geometry_id,
            "role": self.role,
            "material_class": self.material_class,
            "hygiene_class": self.hygiene_class,
            "geometry_status": self.geometry_status,
            "geometry": _geometry(self.solid),
        }


@dataclass(frozen=True, slots=True)
class CollisionCheck:
    check_id: str
    first_id: str
    second_id: str
    intersection_volume_mm3: float
    minimum_distance_mm: float

    def __post_init__(self) -> None:
        for label, value in (("check_id", self.check_id), ("first_id", self.first_id), ("second_id", self.second_id)):
            _text(value, label)
        _finite(self.intersection_volume_mm3, "intersection volume")
        _finite(self.minimum_distance_mm, "minimum distance")
        if self.intersection_volume_mm3 != 0.0:
            raise DrySidePackageError(f"required-clear dry-side collision: {self.check_id}")

    def manifest(self) -> dict[str, object]:
        return {
            "check_id": self.check_id,
            "first_id": self.first_id,
            "second_id": self.second_id,
            "intersection_volume_mm3": self.intersection_volume_mm3,
            "minimum_distance_mm": self.minimum_distance_mm,
            "passes": True,
        }


@dataclass(frozen=True, slots=True)
class DrySidePackage:
    authority_revision: str
    physical_geometry: tuple[PackageGeometry, ...]
    reference_geometry: tuple[PackageGeometry, ...]
    service_geometry: tuple[PackageGeometry, ...]
    collision_checks: tuple[CollisionCheck, ...]
    pcb_mounting_datums_xyz_mm: tuple[tuple[float, float, float], ...]
    battery_nominal_voltage_V: float
    battery_capacity_mAh: float
    battery_mass_g: float
    rib_ratio: float

    def __post_init__(self) -> None:
        if self.authority_revision != AUTHORITY_REVISION:
            raise DrySidePackageError("authority revision mismatch")
        ids = [item.geometry_id for item in (*self.physical_geometry, *self.reference_geometry, *self.service_geometry)]
        if len(ids) != len(set(ids)):
            raise DrySidePackageError("dry-side geometry IDs cannot repeat")
        if any(item.material_class != "PHYSICAL_MATERIAL_CANDIDATE" for item in self.physical_geometry):
            raise DrySidePackageError("physical set contains non-material geometry")
        if any(item.material_class == "PHYSICAL_MATERIAL_CANDIDATE" for item in (*self.reference_geometry, *self.service_geometry)):
            raise DrySidePackageError("reference/service geometry cannot silently enter material")
        if len(self.pcb_mounting_datums_xyz_mm) != 4:
            raise DrySidePackageError("PCB zone requires four deterministic mounting datums")
        for point in self.pcb_mounting_datums_xyz_mm:
            _point(point, "PCB mounting datum")
        for value, label in (
            (self.battery_nominal_voltage_V, "battery nominal voltage"),
            (self.battery_capacity_mAh, "battery capacity"),
            (self.battery_mass_g, "battery mass"),
            (self.rib_ratio, "rib ratio"),
        ):
            _finite(value, label, positive=True)

    @property
    def package_sha256(self) -> str:
        raw = json.dumps(self.manifest(False), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        return sha256(raw).hexdigest()

    def manifest(self, include_sha: bool = True) -> dict[str, object]:
        unresolved = "BLOCKED_PENDING_SELECTED_HARDWARE_OR_CONTROLLED_SUPPLIER_OR_MEASUREMENT_EVIDENCE"
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "authority_revision": self.authority_revision,
            "world_frame_id": WORLD_FRAME_ID,
            "sources": {
                "main_sha": SOURCE_MAIN_SHA,
                "source_git_blobs": {path: digest for path, digest in SOURCE_GIT_BLOB_IDENTITIES},
                "legacy_donor_pr": LEGACY_DONOR_PR,
                "legacy_donor_head_sha": LEGACY_DONOR_HEAD_SHA,
                "legacy_donor_electronics_blob_sha": LEGACY_DONOR_BLOB_SHA,
                "donor_semantics": "CONCEPT_AND_LABELLED_CAD_RESERVATION_SEEDS_ONLY_NOT_AUTHORITY",
            },
            "physical_geometry": [item.manifest() for item in self.physical_geometry],
            "reference_geometry": [item.manifest() for item in self.reference_geometry],
            "service_geometry": [item.manifest() for item in self.service_geometry],
            "pcb_mounting_datums_xyz_mm": [list(point) for point in self.pcb_mounting_datums_xyz_mm],
            "power_ledger": {
                "battery_nominal_voltage_V": self.battery_nominal_voltage_V,
                "battery_capacity_mAh": self.battery_capacity_mAh,
                "battery_mass_g": self.battery_mass_g,
                "loads": [{"load_id": load_id, "quantity": quantity, "nominal_power_W": None, "status": unresolved}
                          for load_id, quantity in zip(LOAD_IDS, (4, 1, 1, 1, 1, 1), strict=True)],
                "total_dry_side_mass_g": None,
                "total_power_W": None,
                "runtime_estimate_h": None,
                "runtime_validated": False,
            },
            "collision_checks": [item.manifest() for item in self.collision_checks],
            "interfaces": {
                "frame_attachment": {
                    "datum_xyz_mm": [0.0, 0.0, -25.0],
                    "relationship": "POSITIVE_ATTACHMENT_REQUIRED_COUNTERPART_UNRELEASED",
                    "status": "BLOCKED_RELEASED_FRAME_HAS_TOPOLOGY_ONLY_NO_3D_DRY_BAY_COUNTERPART",
                },
                "rear_service_door": {
                    "datum_xyz_mm": [0.0, 0.0, -47.0],
                    "relationship": "SEAL_INTERFACE_RESERVATION_POSITIVE_CLOSURE_REQUIRED",
                    "status": "BLOCKED_LATCH_FASTENER_SEAL_STACK_AND_EXTERIOR_MATCH_UNSELECTED",
                },
                "charging": {
                    "datum_xyz_mm": list(CHARGE_CENTER_MM),
                    "axis_xyz": [-1.0, 0.0, 0.0],
                    "relationship": "SEAL_INTERFACE_RESERVATION",
                    "status": "CONNECTOR_TYPE_RETENTION_INGRESS_CERTIFICATION_AND_ACTIVE_WET_CHARGING_UNSELECTED",
                },
            },
            "dfm": {
                "dry_bay_wall_mm": DRY_BAY_WALL_MM,
                "battery_guide_wall_mm": BATTERY_GUIDE_WALL_MM,
                "support_rib_thickness_mm": SUPPORT_RIB_THICKNESS_MM,
                "support_rib_to_wall_ratio": self.rib_ratio,
                "draft_geometry_realized": False,
                "draft_status": "BLOCKED_DRAFT_AND_PARTING_ARCHITECTURE_NOT_YET_REALIZED",
                "material_status": "UNSELECTED",
                "tolerance_stack_status": "PROVISIONAL_DIGITAL_CLEARANCES_ONLY",
            },
            "integration": {
                "frame_positive_attachment_realized": False,
                "door_positive_attachment_realized": False,
                "charging_connector_selected": False,
                "ingress_validated": False,
                "electrical_safety_validated": False,
                "development_assembly_status": "REVIEW_ONLY_NOT_INSERTED_INTO_RELEASED_PHYSICAL_ASSEMBLY",
            },
            "evidence_status": EVIDENCE_STATUS,
        }
        if include_sha:
            payload["package_sha256"] = self.package_sha256
        return payload


def _z_sweep(size: tuple[float, float, float], start: tuple[float, float, float], end_z: float) -> cq.Workplane:
    sx, sy, sz = size
    if end_z >= start[2]:
        raise DrySidePackageError("rear service sweep must travel along -Z")
    return _box((sx, sy, sz + start[2] - end_z), (start[0], start[1], (start[2] + end_z) / 2.0))


def _build_geometry(authority: Authority) -> tuple[tuple[PackageGeometry, ...], tuple[PackageGeometry, ...], tuple[PackageGeometry, ...]]:
    bw, bh, bd = tuple(float(item) for item in authority.get("battery_reference", "envelope_mm"))
    fault_size = (bw + 3.0, bh + 3.0, bd + 4.0)
    guide_size = tuple(fault_size[index] + 2.0 * BATTERY_GUIDE_WALL_MM for index in range(3))

    bay_outer = _box(DRY_BAY_OUTER_MM, DRY_BAY_CENTER_MM)
    cavity_size = (DRY_BAY_OUTER_MM[0] - 3.6, DRY_BAY_OUTER_MM[1] - 3.6, DRY_BAY_OUTER_MM[2] - 1.8)
    bay_cavity = _box(cavity_size, (0.0, 0.0, DRY_BAY_CENTER_MM[2] - 0.9))
    bay_shell = bay_outer.cut(bay_cavity)

    fault = _box(fault_size, BATTERY_CENTER_MM)
    guide_outer = _box(guide_size, BATTERY_CENTER_MM)
    guide_void = _box((fault_size[0], fault_size[1], guide_size[2] + 2.0), BATTERY_CENTER_MM)
    guide = guide_outer.cut(guide_void)
    guide_top_z = float(guide.val().BoundingBox().zmax)
    pylon_end_z = -26.5
    pylon_depth = pylon_end_z - guide_top_z
    structure = bay_shell.union(guide)
    for x in (-19.5, 19.5):
        for y in (-30.25, 26.25):
            structure = structure.union(_box((1.0, 1.0, pylon_depth), (x, y, (guide_top_z + pylon_end_z) / 2.0)))
    structure = structure.union(_box(PCB_SUPPORT_MM, PCB_SUPPORT_CENTER_MM))

    door = _box(DOOR_MM, DOOR_CENTER_MM).edges("|Z").fillet(DOOR_CORNER_RADIUS_MM)
    battery = _box((bw, bh, bd), BATTERY_CENTER_MM)
    pcb = _box(PCB_REFERENCE_MM, PCB_CENTER_MM)
    power_zone = _box(POWER_ZONE_MM, POWER_ZONE_CENTER_MM)
    charge = _box(CHARGE_RESERVATION_MM, CHARGE_CENTER_MM)

    physical = (
        PackageGeometry("DRY_BAY_CARRIER_STRUCTURE", "integral compact bay, noncompressive battery edge guide and PCB support shelf", structure, "PHYSICAL_MATERIAL_CANDIDATE", "DRY_ALWAYS", "CELL12_CAD_BASELINE_FRAME_ATTACHMENT_UNRELEASED"),
        PackageGeometry("REAR_SERVICE_DOOR_CANDIDATE", "rounded low-highlight rear service closure candidate", door, "PHYSICAL_MATERIAL_CANDIDATE", "DRY_ALWAYS", "CELL12_CAD_CANDIDATE_LATCH_SEAL_AND_EXTERIOR_MATCH_UNRESOLVED"),
    )
    reference = (
        PackageGeometry("BATTERY_PACKAGING_BENCHMARK", "authority EEMB benchmark at Cell 12 rear-package placement", battery, "REFERENCE_ONLY", "DRY_ALWAYS", str(authority.get("battery_reference", "status"))),
        PackageGeometry("BATTERY_FAULT_CLEARANCE_RESERVATION", "noncompressive donor-derived digital fault/swelling clearance", fault, "REFERENCE_ONLY", "DRY_ALWAYS", "PR64_CAD_SEED_NOT_SUPPLIER_SWELLING_REQUIREMENT"),
        PackageGeometry("PCB_BARE_BOARD_REFERENCE", "unselected PCB fit reference", pcb, "REFERENCE_ONLY", "DRY_ALWAYS", "REFLOWED_FIT_ZONE_NOT_ROUTED_OR_SELECTED_PCB"),
        PackageGeometry("PCB_POWER_PROTECTION_CHARGING_ZONE", "fuse/protection/charging board-zone reservation", power_zone, "REFERENCE_ONLY", "DRY_ALWAYS", "PR64_ZONE_CONCEPT_COMPONENTS_CREEPAGE_CLEARANCE_UNRESOLVED"),
        PackageGeometry("CHARGING_INTERFACE_RESERVATION", "left-lower wall-crossing charging and seal-interface reservation", charge, "SEAL_INTERFACE_RESERVATION", "SEALED_NONUSER", "CONNECTOR_RETENTION_SEAL_IP_CERTIFICATION_UNSELECTED"),
    )
    service = (
        PackageGeometry("BATTERY_REARWARD_SERVICE_SWEEP", "continuous -Z swept fault-envelope clearance after door removal", _z_sweep(fault_size, BATTERY_CENTER_MM, BATTERY_SERVICE_END_Z_MM), "SERVICE_SWEEP_REFERENCE", "DRY_ALWAYS", "MASK_REMOVED_UNPOWERED_DIGITAL_MOTION_PHYSICAL_SERVICE_OPEN"),
        PackageGeometry("REAR_SERVICE_DOOR_WITHDRAWAL_SWEEP", "continuous -Z door withdrawal clearance", _z_sweep(DOOR_MM, DOOR_CENTER_MM, DOOR_SERVICE_END_Z_MM), "SERVICE_SWEEP_REFERENCE", "DRY_ALWAYS", "MASK_REMOVED_UNPOWERED_DIGITAL_MOTION_LATCH_SEQUENCE_OPEN"),
    )
    return physical, reference, service


def _clear(check_id: str, first_id: str, first: cq.Workplane, second_id: str, second: cq.Workplane) -> CollisionCheck:
    return CollisionCheck(check_id, first_id, second_id, _intersection(first, second), _distance(first, second))


def build_dry_side_package(authority: Authority | None = None, model: MasckOneModel | None = None) -> DrySidePackage:
    _require_sources()
    authority = authority or load_authority()
    _require_authority(authority)
    model = model or build_model(authority)
    if type(model) is not MasckOneModel or model.authority.data != authority.data:
        raise DrySidePackageError("dry-side package requires a current exact-authority MasckOneModel")

    physical, reference, service = _build_geometry(authority)
    allowed_hygiene = set(authority.get("manufacturing", "hygiene_classes"))
    if any(item.hygiene_class not in allowed_hygiene for item in (*physical, *reference, *service)):
        raise DrySidePackageError("dry-side hygiene class outside frozen authority vocabulary")

    structure, door = (item.solid for item in physical)
    battery, fault, pcb, power_zone, _charge = (item.solid for item in reference)
    if _intersection(battery, fault) <= 0.0:
        raise DrySidePackageError("battery must be contained by its fault reservation")
    if _intersection(structure, battery) or _intersection(structure, fault):
        raise DrySidePackageError("carrier material intrudes into battery/fault reservation")
    if _intersection(structure, pcb):
        raise DrySidePackageError("PCB fit reference intersects dry-bay material")
    if _intersection(pcb, power_zone) <= 0.0:
        raise DrySidePackageError("power/protection zone must remain on PCB fit reference")

    checks = [
        _clear("CLEAR-BATTERY-SWEEP-STRUCTURE", service[0].geometry_id, service[0].solid, physical[0].geometry_id, structure),
        _clear("CLEAR-BATTERY-SWEEP-PCB", service[0].geometry_id, service[0].solid, reference[2].geometry_id, pcb),
        _clear("CLEAR-DOOR-SWEEP-STRUCTURE", service[1].geometry_id, service[1].solid, physical[0].geometry_id, structure),
    ]
    obstacles = (
        (model.shell.name, model.shell.solid),
        *((item.name, item.solid) for item in model.actuator_envelopes),
        (model.water_reservoir_envelope.name, model.water_reservoir_envelope.solid),
        (model.waste_cartridge_envelope.name, model.waste_cartridge_envelope.solid),
        (model.battery_reference_envelope.name, model.battery_reference_envelope.solid),
        *((item.name, item.solid) for item in model.visual_keepouts),
    )
    for moving_or_material in (*physical, *service):
        for obstacle_id, obstacle in obstacles:
            checks.append(_clear(f"CLEAR-{moving_or_material.geometry_id}-{obstacle_id}", moving_or_material.geometry_id, moving_or_material.solid, obstacle_id, obstacle))

    rib_ratio = SUPPORT_RIB_THICKNESS_MM / DRY_BAY_WALL_MM
    low, high = tuple(float(item) for item in authority.get("manufacturing", "rib_thickness_ratio_range"))
    if not low <= rib_ratio <= high:
        raise DrySidePackageError("support rib ratio violates authority manufacturing baseline")
    if DRY_BAY_WALL_MM < float(authority.get("geometry", "shell_absolute_development_min_mm")):
        raise DrySidePackageError("dry-bay wall is below controlled development minimum")

    return DrySidePackage(
        AUTHORITY_REVISION,
        physical,
        reference,
        service,
        tuple(checks),
        ((-15.0, 11.0, -30.25), (15.0, 11.0, -30.25), (-15.0, 27.0, -30.25), (15.0, 27.0, -30.25)),
        float(authority.get("battery_reference", "nominal_voltage_V")),
        float(authority.get("battery_reference", "capacity_mAh")),
        float(authority.get("battery_reference", "mass_g")),
        rib_ratio,
    )


if __name__ == "__main__":
    print(json.dumps(build_dry_side_package().manifest(), indent=2))
