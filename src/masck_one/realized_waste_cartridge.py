"""Cell 11 source-bound digital realization of the replaceable waste cartridge.

This module converts the released 74 x 36 x 20 mm cartridge package reference into
bounded review geometry without promoting retained-liquid, seal, hygiene, service or
supplier performance.  The released mixed-waste route and interface identity remain
unchanged.  Cartridge body, closure, cavity, inlet bore, a one-sided cartridge key
feature, vent bore and typed reference reservations are explicit B-reps.

The geometry is intentionally not inserted into the development assembly by this
module.  Device-side key/latch counterparts, the inlet coupling/seal, continuous
service motion, frame attachment and physical evidence remain release blockers.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1, sha256
import json
import math
from pathlib import Path

import cadquery as cq

from .model import MasckOneModel, build_model
from .realized_waste_backbone_release import (
    Cell4WasteBackboneRelease,
    build_current_cell4_waste_backbone_release,
)
from .waste_acquisition import PHASE_MIXED_WASTE
from .waste_pump_architecture import (
    INTERFACE_CARTRIDGE_INLET_I27,
    ROUTE_BARRIER_TO_CARTRIDGE,
)


SCHEMA = "MASCK_ONE_CELL11_REALIZED_WASTE_CARTRIDGE_V1"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
AUTHORED_AGAINST_MAIN_SHA = "afe29ff78419b6625dca5594974b6351f6f80e1b"
AUTHORITY_REVISION = "2026-08-30-R1"

SOURCE_GIT_BLOB_IDENTITIES: tuple[tuple[str, str], ...] = (
    ("config/masck_one_authority.yaml", "2608dda483b995539de422290371c219668a1527"),
    ("src/masck_one/model.py", "9e7fa6c71ac28cc45ebb502444bf6c0ea49f7894"),
    ("src/masck_one/waste_acquisition.py", "7108fcfbe2baeaa9a343199a6817122ac2aea7ab"),
    ("src/masck_one/waste_cartridge.py", "9dc0fe8a0ed92083c68406da3993e57e767e2483"),
    ("src/masck_one/waste_pump_architecture.py", "ace02ee529070465b11832f475771125636312cb"),
    ("src/masck_one/realized_waste_backbone.py", "6aa79d9a613e278f32da85b4654c0e35cc09b7ca"),
    ("src/masck_one/realized_waste_backbone_release.py", "86f2b12d8721ce0fb233d7b026aed3154de9c964"),
)

CARTRIDGE_ID = "WASTE-CARTRIDGE-I27-CELL11-REALIZATION-V1"
BODY_ID = "WASTE-CARTRIDGE-I27-CELL11-BODY"
CLOSURE_ID = "WASTE-CARTRIDGE-I27-CELL11-CLOSURE"
CAVITY_ID = "WASTE-CARTRIDGE-I27-CELL11-INSTALLED-FREE-CAVITY-REFERENCE"
INLET_REFERENCE_ID = "WASTE-CARTRIDGE-I27-CELL11-INLET-CONNECTOR-CLEARANCE"
SEAL_LAND_REFERENCE_ID = "WASTE-CARTRIDGE-I27-CELL11-CLOSURE-SEAL-LAND"
VENT_REFERENCE_ID = "WASTE-CARTRIDGE-I27-CELL11-VENT-CLEARANCE"
SERVICE_REFERENCE_ID = "WASTE-CARTRIDGE-I27-CELL11-INFERIOR-SERVICE-RESERVATION"
KEY_FEATURE_ID = "WASTE-CARTRIDGE-I27-CELL11-ASYMMETRIC-KEY-RIB"

PACKAGE_CENTER_WORLD_MM = (0.0, -80.0, 8.0)
PACKAGE_ENVELOPE_XYZ_MM = (74.0, 36.0, 20.0)
PACKAGE_BOUNDS_WORLD_MM = {
    "x": (-37.0, 37.0),
    "y": (-98.0, -62.0),
    "z": (-2.0, 18.0),
}

# Provisional digital construction seeds.  They are intentionally not material,
# process or supplier freezes.  All material/performance claims remain blocked.
BODY_OUTER_XYZ_MM = (74.0, 35.0, 18.0)
BODY_CENTER_WORLD_MM = (0.0, -80.0, 7.0)
BODY_WALL_SEED_MM = 1.2
CLOSURE_PLATE_XYZ_MM = (74.0, 35.0, 2.0)
CLOSURE_PLATE_CENTER_WORLD_MM = (0.0, -80.0, 17.0)
CLOSURE_PLUG_XYZ_MM = (70.0, 31.0, 0.8)
CLOSURE_PLUG_CENTER_WORLD_MM = (0.0, -80.0, 15.6)

KEY_RIB_XYZ_MM = (8.0, 0.5, 5.0)
KEY_RIB_CENTER_WORLD_MM = (24.0, -97.75, 8.0)

ROUTE_HANDOFF_WORLD_MM = (-41.0, -82.0, 14.0)
BODY_INLET_WALL_WORLD_MM = (-37.0, -82.0, 14.0)
INLET_BORE_DIAMETER_MM = 2.4
INLET_REFERENCE_DIAMETER_MM = 4.0
INLET_HANDOFF_GAP_MM = 4.0

VENT_BORE_CENTER_XY_MM = (26.0, -90.0)
VENT_BORE_DIAMETER_MM = 2.0
VENT_CLEARANCE_DIAMETER_MM = 5.0
VENT_CLEARANCE_HEIGHT_MM = 8.0

SEAL_LAND_REFERENCE_THICKNESS_MM = 0.20
SERVICE_TRANSLATION_AXIS_WORLD = (0.0, -1.0, 0.0)
SERVICE_TRANSLATION_SEED_MM = 45.0
SERVICE_REFERENCE_XYZ_MM = (76.0, 80.0, 22.0)
SERVICE_REFERENCE_CENTER_WORLD_MM = (0.0, -102.5, 8.0)

BODY_STATUS = (
    "CELL11_DIGITAL_CARTRIDGE_BODY_AND_OPEN_TRAY_CAVITY_REALIZED_"
    "PROVISIONAL_WALL_NOT_MATERIAL_OR_PROCESS_FREEZE"
)
CLOSURE_STATUS = (
    "CELL11_SEPARATE_CLOSURE_AND_ALIGNMENT_PLUG_REALIZED_"
    "SEAL_MATERIAL_COMPRESSION_AND_LEAKAGE_UNRESOLVED"
)
CAPACITY_STATUS = (
    "GEOMETRIC_INSTALLED_FREE_CAVITY_ONLY_NOT_USABLE_OR_RETAINED_LIQUID_CAPACITY"
)
INLET_STATUS = (
    "RELEASED_ROUTE_HANDOFF_AND_BODY_BORE_REALIZED_CONNECTOR_SEAL_AND_WET_COUPLING_UNRESOLVED"
)
KEY_STATUS = (
    "CARTRIDGE_SIDE_ASYMMETRIC_KEY_FEATURE_REALIZED_DEVICE_COUNTERPART_AND_POSITIVE_RETENTION_UNRESOLVED"
)
VENT_STATUS = (
    "VENT_BORE_AND_EXTERNAL_CLEARANCE_REALIZED_MEDIA_EMISSION_CONTAINMENT_ORIENTATION_AND_LEAKAGE_UNVALIDATED"
)
SERVICE_STATUS = (
    "CONSERVATIVE_INFERIOR_TRANSLATION_RESERVATION_ONLY_CONTINUOUS_SERVICE_MOTION_AND_INTERFACE_DISCONNECT_UNRESOLVED"
)
HYGIENE_CLASSIFICATION = "WET_REMOVABLE"
EVIDENCE_STATUS = (
    "DIGITAL_CARTRIDGE_BODY_CLOSURE_CAVITY_INLET_KEY_VENT_AND_SERVICE_REFERENCE_GEOMETRY_ONLY_NOT_"
    "RETAINED_CAPACITY_SEAL_LEAKAGE_HYGIENE_DURABILITY_WET_HAND_DISPOSAL_OR_PHYSICAL_EVIDENCE"
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TOL = 1e-7


class RealizedWasteCartridgeError(ValueError):
    pass


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def _require_current_sources() -> None:
    for relative_path, expected in SOURCE_GIT_BLOB_IDENTITIES:
        path = _REPO_ROOT / relative_path
        if not path.is_file():
            raise RealizedWasteCartridgeError(f"required cartridge source missing: {relative_path}")
        actual = _git_blob_sha(path)
        if actual != expected:
            raise RealizedWasteCartridgeError(
                f"cartridge source moved at {relative_path}; expected {expected}, got {actual}"
            )


def _box(size: tuple[float, float, float], center: tuple[float, float, float]) -> cq.Workplane:
    return (
        cq.Workplane("XY")
        .box(*size, centered=(True, True, True))
        .translate(center)
    )


def _cylinder(
    start: tuple[float, float, float],
    axis: tuple[float, float, float],
    length_mm: float,
    diameter_mm: float,
) -> cq.Workplane:
    return cq.Workplane(
        obj=cq.Solid.makeCylinder(
            diameter_mm / 2.0,
            length_mm,
            cq.Vector(*start),
            cq.Vector(*axis),
        )
    )


def _one_valid_solid(shape: cq.Workplane, label: str) -> None:
    if shape.solids().size() != 1 or not shape.val().isValid() or shape.val().Volume() <= 0.0:
        raise RealizedWasteCartridgeError(f"{label} must be one valid positive B-rep solid")


def _bounds(shape: cq.Workplane) -> dict[str, tuple[float, float]]:
    box = shape.val().BoundingBox()
    return {
        "x": (float(box.xmin), float(box.xmax)),
        "y": (float(box.ymin), float(box.ymax)),
        "z": (float(box.zmin), float(box.zmax)),
    }


def _outside_volume(shape: cq.Workplane, envelope: cq.Workplane) -> float:
    return float(shape.val().cut(envelope.val()).Volume())


def _intersection_volume(a: cq.Workplane, b: cq.Workplane) -> float:
    return float(a.val().intersect(b.val()).Volume())


def _shape_manifest(shape: cq.Workplane) -> dict[str, object]:
    return {
        "bounds_world_mm": {axis: list(values) for axis, values in _bounds(shape).items()},
        "volume_mm3": float(shape.val().Volume()),
        "valid": bool(shape.val().isValid()),
        "solid_count": int(shape.solids().size()),
    }


def _build_body() -> cq.Workplane:
    outer = _box(BODY_OUTER_XYZ_MM, BODY_CENTER_WORLD_MM)
    inner_x = BODY_OUTER_XYZ_MM[0] - 2.0 * BODY_WALL_SEED_MM
    inner_y = BODY_OUTER_XYZ_MM[1] - 2.0 * BODY_WALL_SEED_MM
    floor_top_z = PACKAGE_BOUNDS_WORLD_MM["z"][0] + BODY_WALL_SEED_MM
    cutter_height = BODY_OUTER_XYZ_MM[2] - BODY_WALL_SEED_MM + 1.0
    cutter = _box(
        (inner_x, inner_y, cutter_height),
        (0.0, -80.0, floor_top_z + cutter_height / 2.0),
    )
    body = outer.cut(cutter)
    body = body.union(_box(KEY_RIB_XYZ_MM, KEY_RIB_CENTER_WORLD_MM))
    inlet_bore = _cylinder(
        (-38.5, BODY_INLET_WALL_WORLD_MM[1], BODY_INLET_WALL_WORLD_MM[2]),
        (1.0, 0.0, 0.0),
        5.0,
        INLET_BORE_DIAMETER_MM,
    )
    return body.cut(inlet_bore)


def _build_closure() -> cq.Workplane:
    closure = _box(CLOSURE_PLATE_XYZ_MM, CLOSURE_PLATE_CENTER_WORLD_MM).union(
        _box(CLOSURE_PLUG_XYZ_MM, CLOSURE_PLUG_CENTER_WORLD_MM)
    )
    vent_bore = _cylinder(
        (VENT_BORE_CENTER_XY_MM[0], VENT_BORE_CENTER_XY_MM[1], 15.0),
        (0.0, 0.0, 1.0),
        4.0,
        VENT_BORE_DIAMETER_MM,
    )
    return closure.cut(vent_bore)


def _build_installed_free_cavity_reference() -> cq.Workplane:
    inner_x = BODY_OUTER_XYZ_MM[0] - 2.0 * BODY_WALL_SEED_MM
    inner_y = BODY_OUTER_XYZ_MM[1] - 2.0 * BODY_WALL_SEED_MM
    floor_top_z = PACKAGE_BOUNDS_WORLD_MM["z"][0] + BODY_WALL_SEED_MM
    cavity_height = 16.0 - floor_top_z
    cavity = _box(
        (inner_x, inner_y, cavity_height),
        (0.0, -80.0, floor_top_z + cavity_height / 2.0),
    )
    return cavity.cut(_box(CLOSURE_PLUG_XYZ_MM, CLOSURE_PLUG_CENTER_WORLD_MM))


def _build_seal_land_reference() -> cq.Workplane:
    outer = _box(
        (BODY_OUTER_XYZ_MM[0], BODY_OUTER_XYZ_MM[1], SEAL_LAND_REFERENCE_THICKNESS_MM),
        (0.0, -80.0, 15.9),
    )
    inner = _box(
        (
            BODY_OUTER_XYZ_MM[0] - 2.0 * BODY_WALL_SEED_MM,
            BODY_OUTER_XYZ_MM[1] - 2.0 * BODY_WALL_SEED_MM,
            SEAL_LAND_REFERENCE_THICKNESS_MM * 2.0,
        ),
        (0.0, -80.0, 15.9),
    )
    return outer.cut(inner)


def _build_inlet_reference() -> cq.Workplane:
    return _cylinder(
        ROUTE_HANDOFF_WORLD_MM,
        (1.0, 0.0, 0.0),
        INLET_HANDOFF_GAP_MM,
        INLET_REFERENCE_DIAMETER_MM,
    )


def _build_vent_clearance_reference() -> cq.Workplane:
    return _cylinder(
        (VENT_BORE_CENTER_XY_MM[0], VENT_BORE_CENTER_XY_MM[1], 18.0),
        (0.0, 0.0, 1.0),
        VENT_CLEARANCE_HEIGHT_MM,
        VENT_CLEARANCE_DIAMETER_MM,
    )


def _build_service_reference() -> cq.Workplane:
    return _box(SERVICE_REFERENCE_XYZ_MM, SERVICE_REFERENCE_CENTER_WORLD_MM)


@dataclass(frozen=True, slots=True)
class RealizedWasteCartridge:
    body_solid: cq.Workplane
    closure_solid: cq.Workplane
    installed_free_cavity_reference: cq.Workplane
    inlet_connector_clearance_reference: cq.Workplane
    seal_land_reference: cq.Workplane
    vent_clearance_reference: cq.Workplane
    service_reservation_reference: cq.Workplane
    source_backbone_manifest_sha256: str
    current_released_shell_interference_mm3: float
    physical_validation_eligible: bool = False

    def validate(self) -> None:
        _require_current_sources()
        for shape, label in (
            (self.body_solid, "cartridge body"),
            (self.closure_solid, "cartridge closure"),
            (self.installed_free_cavity_reference, "installed free cavity reference"),
            (self.inlet_connector_clearance_reference, "inlet connector clearance reference"),
            (self.seal_land_reference, "seal-land reference"),
            (self.vent_clearance_reference, "vent clearance reference"),
            (self.service_reservation_reference, "service reservation reference"),
        ):
            _one_valid_solid(shape, label)

        package = _box(PACKAGE_ENVELOPE_XYZ_MM, PACKAGE_CENTER_WORLD_MM)
        if _outside_volume(self.body_solid, package) > _TOL:
            raise RealizedWasteCartridgeError("cartridge body escapes the controlled package envelope")
        if _outside_volume(self.closure_solid, package) > _TOL:
            raise RealizedWasteCartridgeError("cartridge closure escapes the controlled package envelope")
        if _outside_volume(self.installed_free_cavity_reference, package) > _TOL:
            raise RealizedWasteCartridgeError("cartridge free cavity escapes the controlled package envelope")
        if _intersection_volume(self.body_solid, self.closure_solid) > _TOL:
            raise RealizedWasteCartridgeError("body and closure overlap in the installed assembly state")
        if _intersection_volume(self.body_solid, self.installed_free_cavity_reference) > _TOL:
            raise RealizedWasteCartridgeError("body material intrudes into installed free-cavity reference")
        if _intersection_volume(self.closure_solid, self.installed_free_cavity_reference) > _TOL:
            raise RealizedWasteCartridgeError("closure material intrudes into installed free-cavity reference")

        geometric_free_mL = float(self.installed_free_cavity_reference.val().Volume()) / 1000.0
        if not math.isclose(geometric_free_mL, 37.477888, rel_tol=0.0, abs_tol=1e-6):
            raise RealizedWasteCartridgeError("installed geometric free-cavity accounting changed")
        if geometric_free_mL <= 35.0:
            raise RealizedWasteCartridgeError("geometric free cavity no longer exceeds retained-capacity requirement")
        if not math.isclose(
            float(self.current_released_shell_interference_mm3),
            self.current_released_shell_interference_mm3,
            rel_tol=0.0,
            abs_tol=0.0,
        ) or not math.isfinite(float(self.current_released_shell_interference_mm3)):
            raise RealizedWasteCartridgeError("current shell interference must be finite")
        if self.current_released_shell_interference_mm3 < -_TOL:
            raise RealizedWasteCartridgeError("current shell interference cannot be negative")
        if type(self.source_backbone_manifest_sha256) is not str or len(self.source_backbone_manifest_sha256) != 64:
            raise RealizedWasteCartridgeError("source backbone manifest identity must be SHA-256")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise RealizedWasteCartridgeError("digital cartridge geometry cannot be physical validation evidence")

    @property
    def installed_geometric_free_capacity_mL(self) -> float:
        self.validate()
        return float(self.installed_free_cavity_reference.val().Volume()) / 1000.0

    @property
    def geometric_margin_over_retained_requirement_mL(self) -> float:
        return self.installed_geometric_free_capacity_mL - 35.0

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
        shell_state = (
            "CURRENT_RELEASED_SHELL_INTERFERENCE_PRESENT_CANDIDATE_NOT_ASSEMBLY_MATERIAL"
            if self.current_released_shell_interference_mm3 > _TOL
            else "NO_CURRENT_RELEASED_SHELL_INTERFERENCE_BUT_DOCK_RETENTION_SERVICE_STILL_UNRESOLVED"
        )
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "cartridge_id": CARTRIDGE_ID,
            "authored_against_main_sha": AUTHORED_AGAINST_MAIN_SHA,
            "authority_revision": AUTHORITY_REVISION,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "fluid_identity": PHASE_MIXED_WASTE,
            "route_id": ROUTE_BARRIER_TO_CARTRIDGE,
            "inlet_interface_id": INTERFACE_CARTRIDGE_INLET_I27,
            "released_route_handoff_world_mm": list(ROUTE_HANDOFF_WORLD_MM),
            "body_inlet_wall_world_mm": list(BODY_INLET_WALL_WORLD_MM),
            "inlet_handoff_gap_mm": INLET_HANDOFF_GAP_MM,
            "source_backbone_manifest_sha256": self.source_backbone_manifest_sha256,
            "package_center_world_mm": list(PACKAGE_CENTER_WORLD_MM),
            "package_envelope_xyz_mm": list(PACKAGE_ENVELOPE_XYZ_MM),
            "package_bounds_world_mm": {axis: list(values) for axis, values in PACKAGE_BOUNDS_WORLD_MM.items()},
            "body_id": BODY_ID,
            "body_status": BODY_STATUS,
            "body_wall_seed_mm": BODY_WALL_SEED_MM,
            "body": _shape_manifest(self.body_solid),
            "closure_id": CLOSURE_ID,
            "closure_status": CLOSURE_STATUS,
            "closure": _shape_manifest(self.closure_solid),
            "cavity_id": CAVITY_ID,
            "hygiene_classification": HYGIENE_CLASSIFICATION,
            "installed_geometric_free_capacity_mL": self.installed_geometric_free_capacity_mL,
            "geometric_margin_over_retained_requirement_mL": self.geometric_margin_over_retained_requirement_mL,
            "retained_capacity_requirement_mL": 35.0,
            "capacity_status": CAPACITY_STATUS,
            "cavity_reference": _shape_manifest(self.installed_free_cavity_reference),
            "inlet_reference_id": INLET_REFERENCE_ID,
            "inlet_bore_diameter_mm": INLET_BORE_DIAMETER_MM,
            "inlet_reference_diameter_mm": INLET_REFERENCE_DIAMETER_MM,
            "inlet_status": INLET_STATUS,
            "inlet_connector_clearance_reference": _shape_manifest(self.inlet_connector_clearance_reference),
            "seal_land_reference_id": SEAL_LAND_REFERENCE_ID,
            "seal_status": CLOSURE_STATUS,
            "seal_land_reference": _shape_manifest(self.seal_land_reference),
            "key_feature_id": KEY_FEATURE_ID,
            "key_feature_xyz_mm": list(KEY_RIB_XYZ_MM),
            "key_feature_center_world_mm": list(KEY_RIB_CENTER_WORLD_MM),
            "key_status": KEY_STATUS,
            "device_key_counterpart_realized": False,
            "positive_retention_realized": False,
            "vent_reference_id": VENT_REFERENCE_ID,
            "vent_bore_diameter_mm": VENT_BORE_DIAMETER_MM,
            "vent_status": VENT_STATUS,
            "vent_clearance_reference": _shape_manifest(self.vent_clearance_reference),
            "service_reference_id": SERVICE_REFERENCE_ID,
            "service_translation_axis_world": list(SERVICE_TRANSLATION_AXIS_WORLD),
            "service_translation_seed_mm": SERVICE_TRANSLATION_SEED_MM,
            "service_status": SERVICE_STATUS,
            "continuous_service_motion_realized": False,
            "service_reservation_reference": _shape_manifest(self.service_reservation_reference),
            "current_released_shell_interference_mm3": self.current_released_shell_interference_mm3,
            "current_released_shell_state": shell_state,
            "development_assembly_material_eligible": False,
            "physical_validation_eligible": False,
            "evidence_status": EVIDENCE_STATUS,
        }
        if include_sha:
            payload["manifest_sha256"] = self.manifest_sha256
        return payload


def _validate_released_route(release: Cell4WasteBackboneRelease) -> str:
    if type(release) is not Cell4WasteBackboneRelease:
        raise RealizedWasteCartridgeError("waste backbone release must use exact release type")
    release.validate_invariants()
    matches = tuple(
        route for route in release.realization.routes if route.route_id == ROUTE_BARRIER_TO_CARTRIDGE
    )
    if len(matches) != 1:
        raise RealizedWasteCartridgeError("released cartridge handoff route identity changed")
    route = matches[0]
    route.validate()
    if route.fluid_identity != PHASE_MIXED_WASTE:
        raise RealizedWasteCartridgeError("cartridge route lost exact mixed-waste identity")
    if route.target_interface_id != INTERFACE_CARTRIDGE_INLET_I27:
        raise RealizedWasteCartridgeError("released route no longer terminates at cartridge inlet interface")
    endpoint = tuple(float(value) for value in route.centerline[-1].end.as_tuple())
    if endpoint != ROUTE_HANDOFF_WORLD_MM:
        raise RealizedWasteCartridgeError(
            f"released cartridge handoff moved; expected {ROUTE_HANDOFF_WORLD_MM}, got {endpoint}"
        )
    return release.manifest_sha256


def build_realized_waste_cartridge(
    *,
    model: MasckOneModel | None = None,
    release: Cell4WasteBackboneRelease | None = None,
) -> RealizedWasteCartridge:
    _require_current_sources()
    model = model or build_model()
    release = release or build_current_cell4_waste_backbone_release()
    source_backbone_manifest_sha256 = _validate_released_route(release)

    if str(model.authority.get("project", "authority_revision")) != AUTHORITY_REVISION:
        raise RealizedWasteCartridgeError("authority revision moved")
    envelope = tuple(float(value) for value in model.authority.get("fluid", "cartridge", "external_envelope_mm"))
    if envelope != PACKAGE_ENVELOPE_XYZ_MM:
        raise RealizedWasteCartridgeError("authority cartridge envelope moved")
    retained = float(model.authority.get("fluid", "cartridge", "retained_capacity_min_mL"))
    if retained != 35.0:
        raise RealizedWasteCartridgeError("authority retained-capacity requirement moved")
    hygiene_classes = tuple(model.authority.get("manufacturing", "hygiene_classes"))
    if HYGIENE_CLASSIFICATION not in hygiene_classes:
        raise RealizedWasteCartridgeError("WET_REMOVABLE hygiene class is no longer authority-controlled")

    package_component = model.waste_cartridge_envelope
    if package_component.name != "waste_cartridge_envelope":
        raise RealizedWasteCartridgeError("released cartridge package component identity moved")
    package_bounds = _bounds(package_component.solid)
    for axis in ("x", "y", "z"):
        if any(
            abs(actual - expected) > 1e-6
            for actual, expected in zip(package_bounds[axis], PACKAGE_BOUNDS_WORLD_MM[axis])
        ):
            raise RealizedWasteCartridgeError("released cartridge package placement moved")

    body = _build_body()
    closure = _build_closure()
    cavity = _build_installed_free_cavity_reference()
    inlet_reference = _build_inlet_reference()
    seal_land = _build_seal_land_reference()
    vent_reference = _build_vent_clearance_reference()
    service_reference = _build_service_reference()
    shell_interference = _intersection_volume(body, model.shell.solid) + _intersection_volume(
        closure, model.shell.solid
    )

    result = RealizedWasteCartridge(
        body_solid=body,
        closure_solid=closure,
        installed_free_cavity_reference=cavity,
        inlet_connector_clearance_reference=inlet_reference,
        seal_land_reference=seal_land,
        vent_clearance_reference=vent_reference,
        service_reservation_reference=service_reference,
        source_backbone_manifest_sha256=source_backbone_manifest_sha256,
        current_released_shell_interference_mm3=shell_interference,
        physical_validation_eligible=False,
    )
    result.validate()
    return result
