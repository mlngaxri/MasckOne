"""Source-bound Cell 11 supported-liner waste cartridge candidate.

The selected digital architecture is the supported formed liner with a shallow
reinforced closure. The historical thick-wall tray/deep-plug topology is retained
only as superseded evidence. Geometric free cavity is never promoted to retained
liquid capacity or physical performance.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from functools import lru_cache
from hashlib import sha1, sha256
from pathlib import Path
import math

import cadquery as cq

from .model import _loft_ellipses, build_model
from .realized_waste_backbone_release import build_current_cell4_waste_backbone_release
from .waste_acquisition import PHASE_MIXED_WASTE
from .waste_pump_architecture import (
    INTERFACE_CARTRIDGE_INLET_I27,
    ROUTE_BARRIER_TO_CARTRIDGE,
)

AUTHORED_AGAINST_MAIN_SHA = "42fa11818184cde998c6df25d7c46d4fb0e4c3eb"
OWNER_PREDECESSOR_PR = 115
OWNER_PREDECESSOR_HEAD_SHA = "96397f9e1142224979bfc43717ccf325d07fc21f"
BLIND_SERVICE_CHECKPOINT_SHA = "e8541d0c99fe3106802df644a795fc07db7e7864"
AUTHORITY_REVISION = "2026-08-30-R1"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
CARTRIDGE_LOCAL_FRAME_ID = "MASCK_ONE_WASTE_CARTRIDGE_LOCAL_MM"
SCHEMA = "MASCK_ONE_CELL11_SUPPORTED_LINER_V3"

SELECTED_ARCHITECTURE = "SUPPORTED_FORMED_LINER_SHALLOW_REINFORCED_CLOSURE"
SUPERSEDED_ARCHITECTURE = "HISTORICAL_1P2MM_THICK_TRAY_DEEP_PLUG"
SUPERSEDED_GEOMETRIC_CAPACITY_ML = 27.4016290784

RETAINED_CAPACITY_REQUIREMENT_ML = 35.0
PACKAGE_ENVELOPE_XYZ_MM = (74.0, 36.0, 20.0)
PACKAGE_CENTER_WORLD_MM = (0.0, -80.0, 8.0)
ROUTE_HANDOFF_WORLD_MM = (-41.0, -82.0, 14.0)
BODY_INLET_WALL_WORLD_MM = (-37.0, -82.0, 14.0)
SEAL_PLANE_POINT_WORLD_MM = (0.0, -80.0, 17.8)
BLIND_KEY_DATUM_WORLD_MM = (-36.0, -80.5, 17.2)
LEFT_RETENTION_DATUM_WORLD_MM = (-37.0, -82.0, 17.0)
RIGHT_RETENTION_DATUM_WORLD_MM = (37.0, -82.0, 17.0)
TOL_MM3 = 1e-7

ROOT = Path(__file__).resolve().parents[2]
SOURCE_GIT_BLOB_IDENTITIES = (
    ("config/masck_one_authority.yaml", "2608dda483b995539de422290371c219668a1527"),
    ("schemas/masck_one_authority.schema.json", "58accbe48619058cb99ab51a0387cf01874c3717"),
    ("src/masck_one/model.py", "9e7fa6c71ac28cc45ebb502444bf6c0ea49f7894"),
    ("src/masck_one/protected_volumes.py", "ff2b9b288559f9b268e5d08a1d6c78335f745cf1"),
    ("src/masck_one/waste_acquisition.py", "7108fcfbe2baeaa9a343199a6817122ac2aea7ab"),
    ("src/masck_one/waste_cartridge.py", "9dc0fe8a0ed92083c68406da3993e57e767e2483"),
    ("src/masck_one/waste_pump_architecture.py", "ace02ee529070465b11832f475771125636312cb"),
    ("src/masck_one/realized_waste_backbone.py", "6aa79d9a613e278f32da85b4654c0e35cc09b7ca"),
    ("src/masck_one/realized_waste_backbone_release.py", "86f2b12d8721ce0fb233d7b026aed3154de9c964"),
)


class RealizedWasteCartridgeError(ValueError):
    """The candidate no longer satisfies its source-bound digital contract."""


def require_sources() -> None:
    for name, expected in SOURCE_GIT_BLOB_IDENTITIES:
        data = (ROOT / name).read_bytes()
        actual = sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
        if actual != expected:
            raise RealizedWasteCartridgeError(f"cartridge source moved: {name}")


def volume(shape) -> float:
    value = shape.val() if isinstance(shape, cq.Workplane) else shape
    return math.fsum(solid.Volume(1e-12) for solid in value.Solids())


def box(size, center):
    return cq.Workplane("XY").box(*size).translate(center)


def cylinder(start, axis, length, diameter):
    return cq.Workplane(
        obj=cq.Solid.makeCylinder(
            diameter / 2.0,
            length,
            cq.Vector(*start),
            cq.Vector(*axis),
        )
    )


def bounds(shape) -> list[float]:
    bb = shape.val().BoundingBox()
    return [float(getattr(bb, key)) for key in ("xmin", "xmax", "ymin", "ymax", "zmin", "zmax")]


def protected_prism(zone):
    prism = (
        cq.Workplane("XY", origin=(zone.center.x, zone.center.y, -100))
        .ellipse(zone.envelope_width_mm / 2.0, zone.envelope_height_mm / 2.0)
        .extrude(200)
    )
    return prism.rotate(
        (zone.center.x, zone.center.y, 0),
        (zone.center.x, zone.center.y, 1),
        zone.angle_deg,
    )


def _mouth(a, b, z0, z1, extra):
    return (
        cq.Workplane("XY", origin=(0, -50, z0))
        .ellipse(a + extra, b + extra)
        .workplane(offset=z1 - z0)
        .ellipse(a, b)
        .loft(ruled=True)
    )


def _matrix_local_to_world() -> list[list[float]]:
    x, y, z = PACKAGE_CENTER_WORLD_MM
    return [
        [1.0, 0.0, 0.0, x],
        [0.0, 1.0, 0.0, y],
        [0.0, 0.0, 1.0, z],
        [0.0, 0.0, 0.0, 1.0],
    ]


def _matrix_world_to_local() -> list[list[float]]:
    x, y, z = PACKAGE_CENTER_WORLD_MM
    return [
        [1.0, 0.0, 0.0, -x],
        [0.0, 1.0, 0.0, -y],
        [0.0, 0.0, 1.0, -z],
        [0.0, 0.0, 0.0, 1.0],
    ]


def service_datums() -> dict[str, dict[str, object]]:
    """Datums only. They do not establish tolerance, seal or service evidence."""
    return {
        "cartridge_center": {
            "point_world_mm": list(PACKAGE_CENTER_WORLD_MM),
            "role": "LOCAL_FRAME_ORIGIN",
        },
        "waste_route_handoff": {
            "point_world_mm": list(ROUTE_HANDOFF_WORLD_MM),
            "role": "DEVICE_SIDE_ROUTE_REFERENCE",
        },
        "body_inlet_wall": {
            "point_world_mm": list(BODY_INLET_WALL_WORLD_MM),
            "role": "CARTRIDGE_BODY_PORT_DATUM",
        },
        "seal_plane": {
            "point_world_mm": list(SEAL_PLANE_POINT_WORLD_MM),
            "normal_world": [0.0, 0.0, 1.0],
            "role": "CLOSURE_BOND_LAND_REFERENCE",
        },
        "blind_key": {
            "point_world_mm": list(BLIND_KEY_DATUM_WORLD_MM),
            "role": "ASYMMETRIC_BLIND_INSERTION_KEY_DATUM",
        },
        "left_retention": {
            "point_world_mm": list(LEFT_RETENTION_DATUM_WORLD_MM),
            "axis_world": [-1.0, 0.0, 0.0],
            "role": "LEFT_PRISMATIC_RETENTION_DATUM",
        },
        "right_retention": {
            "point_world_mm": list(RIGHT_RETENTION_DATUM_WORLD_MM),
            "axis_world": [1.0, 0.0, 0.0],
            "role": "RIGHT_PRISMATIC_RETENTION_DATUM",
        },
    }


@dataclass(frozen=True)
class LinerSeed:
    wall_mm: float = 0.15
    floor_mm: float = 0.15
    lid_mm: float = 0.15
    shell_reserve_mm: float = 0.10
    draft_deg: float = 1.0
    collar_width_mm: float = 0.80
    collar_depth_mm: float = 0.60

    def __post_init__(self):
        for key, value in asdict(self).items():
            if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                raise RealizedWasteCartridgeError(f"nonfinite/nonpositive seed: {key}")
        if not (
            0.10 <= self.wall_mm <= 1.2
            and 0.10 <= self.floor_mm <= 1.2
            and 0.10 <= self.lid_mm <= 2.0
            and 1.0 <= self.draft_deg <= 3.0
            and 0.05 <= self.shell_reserve_mm <= 0.5
            and 0.6 <= self.collar_width_mm <= 1.5
            and 0.4 <= self.collar_depth_mm <= 1.5
        ):
            raise RealizedWasteCartridgeError("seed outside bounded geometry DOE")


def _core(seed: LinerSeed, *, inner: bool):
    """Nested drafted profiles without offset-shell healing."""
    t = seed.wall_mm if inner else 0.0
    z0 = -2.0 + seed.floor_mm if inner else -2.0
    z1 = 18.0 - seed.lid_mm if inner else 18.0
    slope = math.tan(math.radians(seed.draft_deg))
    low = t + slope * (18.0 - z0)
    high = t + slope * (18.0 - z1)
    rectangular = (
        cq.Workplane("XY", origin=(0, -80, z0))
        .rect(74 - 2 * low, 36 - 2 * low)
        .workplane(offset=z1 - z0)
        .rect(74 - 2 * high, 36 - 2 * high)
        .loft(ruled=True)
    )
    reserve = t + seed.shell_reserve_mm
    inside = _loft_ellipses(
        [
            (-2, 151.4 - 2 * reserve, 198.4 - 2 * reserve),
            (-1, 151.4 - 2 * reserve, 198.4 - 2 * reserve),
            (10, 164.4 - 2 * reserve, 203.4 - 2 * reserve),
            (22, 168.4 - 2 * reserve, 206.4 - 2 * reserve),
        ]
    )
    mouth = _mouth(
        38.5 + reserve + high - t,
        25.5 + reserve + high - t,
        z0,
        z1,
        slope * (z1 - z0),
    )
    return rectangular.intersect(inside).cut(mouth)


def _valid(shape, name: str) -> None:
    if (
        len(shape.val().Solids()) != 1
        or not shape.val().isValid()
        or not math.isfinite(volume(shape))
        or volume(shape) <= 0
    ):
        raise RealizedWasteCartridgeError(f"{name} must be one valid connected solid")


@dataclass
class RealizedWasteCartridge:
    seed: LinerSeed
    body_solid: cq.Workplane
    closure_solid: cq.Workplane
    installed_free_cavity_reference: cq.Workplane
    inlet_connector_clearance_reference: cq.Workplane
    seal_land_reference: cq.Workplane
    vent_clearance_reference: cq.Workplane
    key_reference: cq.Workplane
    retention_pockets_reference: cq.Workplane
    dry_retention_reference: cq.Workplane
    device_parts: dict[str, cq.Workplane]
    outer_reference: cq.Workplane
    inner_reference: cq.Workplane
    model: object
    source_backbone_manifest_sha256: str
    fluid_identity: str = PHASE_MIXED_WASTE
    route_id: str = ROUTE_BARRIER_TO_CARTRIDGE
    physical_validation_eligible: bool = False

    @property
    def installed_geometric_free_capacity_mL(self) -> float:
        return volume(self.installed_free_cavity_reference) / 1000.0

    @property
    def geometric_capacity_delta_to_retained_requirement_mL(self) -> float:
        return self.installed_geometric_free_capacity_mL - RETAINED_CAPACITY_REQUIREMENT_ML

    def manufacturing_components(self) -> dict[str, cq.Workplane]:
        return {
            "body": self.body_solid,
            "closure": self.closure_solid,
            **self.device_parts,
        }

    def reference_geometry(self) -> dict[str, cq.Workplane]:
        return {
            "cavity": self.installed_free_cavity_reference,
            "seal_land": self.seal_land_reference,
            "vent_reservation": self.vent_clearance_reference,
            "key_channel": self.key_reference,
            "retention_pockets": self.retention_pockets_reference,
            "dry_retention_reservation": self.dry_retention_reference,
            "inlet_reference": self.inlet_connector_clearance_reference,
        }

    def review_shapes(self) -> dict[str, cq.Workplane]:
        return {**self.manufacturing_components(), **self.reference_geometry()}

    def validate(self, *, require_capacity: bool = True) -> None:
        require_sources()
        self.seed.__post_init__()
        if self.fluid_identity != PHASE_MIXED_WASTE or self.route_id != ROUTE_BARRIER_TO_CARTRIDGE:
            raise RealizedWasteCartridgeError("wrong fluid or passive-backflow route identity")
        if self.physical_validation_eligible is not False:
            raise RealizedWasteCartridgeError("physical validation cannot be promoted")
        if self.source_backbone_manifest_sha256 != current_route_digest():
            raise RealizedWasteCartridgeError("stale or unverified route source")

        for name in (
            "body_solid",
            "closure_solid",
            "installed_free_cavity_reference",
            "inlet_connector_clearance_reference",
            "seal_land_reference",
            "vent_clearance_reference",
            "key_reference",
        ):
            _valid(getattr(self, name), name)
        for name, shape in self.device_parts.items():
            _valid(shape, name)

        expected_device_parts = {
            "left_bolt",
            "right_bolt",
            "left_bolt_guide",
            "right_bolt_guide",
            "key_tongue",
        }
        if set(self.device_parts) != expected_device_parts:
            raise RealizedWasteCartridgeError("device material identities changed")
        if (
            len(self.retention_pockets_reference.val().Solids()) != 2
            or volume(self.retention_pockets_reference) <= 0
        ):
            raise RealizedWasteCartridgeError("bilateral retention reservations lost")

        package = self.model.waste_cartridge_envelope.solid
        moving = (
            self.body_solid,
            self.closure_solid,
            self.installed_free_cavity_reference,
        )
        for shape in moving:
            if volume(shape.cut(package)) > TOL_MM3:
                raise RealizedWasteCartridgeError("package containment lost")
            if volume(shape.intersect(self.model.shell.solid)) > TOL_MM3:
                raise RealizedWasteCartridgeError("released shell intersection")
            for protected in self.model.protected_volumes.all:
                if volume(shape.intersect(protected_prism(protected.zone))) > TOL_MM3:
                    raise RealizedWasteCartridgeError("protected-mouth/face exclusion lost")

        for first, second in (
            (moving[0], moving[1]),
            (moving[0], moving[2]),
            (moving[1], moving[2]),
        ):
            if volume(first.intersect(second)) > TOL_MM3:
                raise RealizedWasteCartridgeError("material counted as cavity or parts overlap")

        expected_cavity = (
            self.inner_reference.cut(self.body_solid)
            .cut(self.closure_solid)
            .cut(self.vent_clearance_reference)
            .cut(self.dry_retention_reference)
        )
        for first, second in (
            (expected_cavity, moving[2]),
            (moving[2], expected_cavity),
        ):
            if volume(first.cut(second)) > TOL_MM3:
                raise RealizedWasteCartridgeError("free cavity accounting changed")

        if require_capacity and self.installed_geometric_free_capacity_mL < RETAINED_CAPACITY_REQUIREMENT_ML:
            raise RealizedWasteCartridgeError("geometric free cavity below 35 mL")

        if volume(self.closure_solid.intersect(self.retention_pockets_reference)) > TOL_MM3:
            raise RealizedWasteCartridgeError("retention pocket filled")
        if volume(self.closure_solid.intersect(self.key_reference)) > TOL_MM3:
            raise RealizedWasteCartridgeError("key channel filled")

        for land in (
            box((1.8, 1.0, 0.3), (-35.8, -80.5, 16.6)),
            box((1.8, 1.0, 0.2), (-35.8, -80.5, 17.85)),
        ):
            if volume(land.cut(self.closure_solid)) > TOL_MM3:
                raise RealizedWasteCartridgeError("blind key floor/roof material lost")
        if volume(self.seal_land_reference.cut(self.closure_solid)) > TOL_MM3:
            raise RealizedWasteCartridgeError("seal land is not actual closure material")

        if self.body_solid.val().distance(self.inlet_connector_clearance_reference.val()) > 1e-5:
            raise RealizedWasteCartridgeError("inlet handoff no longer meets body")
        inlet = cylinder((-41, -82, 14), (1, 0, 0), 9, 2.4)
        vent = cylinder((26, -89, 16), (0, 0, 1), 4, 2)
        if (
            volume(self.body_solid.intersect(inlet)) > TOL_MM3
            or self.installed_free_cavity_reference.val().distance(inlet.val()) > 1e-6
        ):
            raise RealizedWasteCartridgeError("inlet lumen blocked or disconnected")
        if volume(self.closure_solid.intersect(vent)) > TOL_MM3:
            raise RealizedWasteCartridgeError("vent bore blocked")

    def manifest(self) -> dict[str, object]:
        self.validate()
        shapes = self.review_shapes()
        materials = set(self.manufacturing_components())
        return {
            "schema": SCHEMA,
            "selected_architecture": SELECTED_ARCHITECTURE,
            "superseded_selected_candidate": {
                "architecture": SUPERSEDED_ARCHITECTURE,
                "geometric_capacity_mL": SUPERSEDED_GEOMETRIC_CAPACITY_ML,
                "status": "SUPERSEDED_NOT_SELECTED_HISTORICAL_EVIDENCE_ONLY",
            },
            "authored_against_main_sha": AUTHORED_AGAINST_MAIN_SHA,
            "owner_lineage": {
                "predecessor_pr": OWNER_PREDECESSOR_PR,
                "predecessor_head_sha": OWNER_PREDECESSOR_HEAD_SHA,
                "blind_service_checkpoint_sha": BLIND_SERVICE_CHECKPOINT_SHA,
            },
            "source_git_blobs": dict(SOURCE_GIT_BLOB_IDENTITIES),
            "producer_content_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
            "source_backbone_manifest_sha256": self.source_backbone_manifest_sha256,
            "authority_revision": AUTHORITY_REVISION,
            "world_frame_id": WORLD_FRAME_ID,
            "local_frame": {
                "frame_id": CARTRIDGE_LOCAL_FRAME_ID,
                "origin_world_mm": list(PACKAGE_CENTER_WORLD_MM),
                "axes_world": {
                    "x": [1.0, 0.0, 0.0],
                    "y": [0.0, 1.0, 0.0],
                    "z": [0.0, 0.0, 1.0],
                },
                "local_to_world_4x4": _matrix_local_to_world(),
                "world_to_local_4x4": _matrix_world_to_local(),
            },
            "service_datums": service_datums(),
            "fluid_identity": self.fluid_identity,
            "route_id": self.route_id,
            "inlet_interface_id": INTERFACE_CARTRIDGE_INLET_I27,
            "released_route_handoff_world_mm": list(ROUTE_HANDOFF_WORLD_MM),
            "body_inlet_wall_world_mm": list(BODY_INLET_WALL_WORLD_MM),
            "package_envelope_xyz_mm": list(PACKAGE_ENVELOPE_XYZ_MM),
            "seed": asdict(self.seed),
            "seed_status": "DOE_ONLY_PROCESS_CAPABILITY_UNKNOWN",
            "installed_geometric_free_capacity_mL": self.installed_geometric_free_capacity_mL,
            "geometric_capacity_delta_to_retained_requirement_mL": self.geometric_capacity_delta_to_retained_requirement_mL,
            "geometric_capacity_requirement_met": self.installed_geometric_free_capacity_mL >= RETAINED_CAPACITY_REQUIREMENT_ML,
            "retained_capacity_requirement_mL": RETAINED_CAPACITY_REQUIREMENT_ML,
            "retained_capacity_mL": None,
            "retained_capacity_status": "PHYSICAL_VALIDATION_REQUIRED_GEOMETRIC_CAVITY_IS_NOT_RETAINED_CAPACITY",
            "parts": {
                name: {
                    "id": "WASTE-CARTRIDGE-I27-CELL11-" + name.upper().replace("_", "-"),
                    "role": "CANDIDATE_MATERIAL" if name in materials else "REFERENCE_ONLY",
                    "valid": shape.val().isValid(),
                    "solid_count": len(shape.val().Solids()),
                    "volume_mm3": volume(shape),
                    "bounds_world_mm": bounds(shape),
                }
                for name, shape in shapes.items()
            },
            "current_released_shell_interference_mm3": sum(
                volume(shape.intersect(self.model.shell.solid))
                for shape in (self.body_solid, self.closure_solid)
            ),
            "protected_zone_intersections_mm3": {
                protected.zone.zone_id: sum(
                    volume(shape.intersect(protected_prism(protected.zone)))
                    for shape in (self.body_solid, self.closure_solid)
                )
                for protected in self.model.protected_volumes.all
            },
            "positive_retention_status": "LOCAL_SLIDING_BOLT_GEOMETRY_ONLY_DEVICE_MOUNT_LOAD_AND_CAPTURE_UNRESOLVED",
            "seal_status": "LOCAL_BOND_LAND_AND_INLET_SOCKET_GEOMETRY_PROCESS_AND_LEAKAGE_UNRESOLVED",
            "service_condition": "MASK_REMOVED_UNPOWERED",
            "continuous_installed_device_path_proven": False,
            "development_assembly_material_eligible": False,
            "physical_validation_eligible": False,
            "blockers": [
                "CURRENT_MAIN_RELEASED_FRAME_HAS_NO_BREP_FOR_INSTALLED_SERVICE_COLLISION_PROOF",
                "KEY_AND_BOLT_CAPTURE_ACCESS",
                "WET_DISCONNECT_AND_PASSIVE_BACKFLOW_SEQUENCE",
                "DEVICE_DOCK_FRAME_ATTACHMENT",
                "FILM_FORMING_AND_BOND_PROCESS",
                "MIN_MAX_SEAL_AND_RETENTION_FITS",
                "REMOVED_STATE_PORT_CLOSURE",
                "PHYSICAL_RETAINED_CAPACITY_AND_WET_SYSTEM_VALIDATION",
            ],
        }


@lru_cache(maxsize=2)
def _route_digest(source_identity):
    release = build_current_cell4_waste_backbone_release()
    matches = [
        route
        for route in release.realization.routes
        if route.route_id == ROUTE_BARRIER_TO_CARTRIDGE
    ]
    if (
        len(matches) != 1
        or matches[0].fluid_identity != PHASE_MIXED_WASTE
        or matches[0].target_interface_id != INTERFACE_CARTRIDGE_INLET_I27
    ):
        raise RealizedWasteCartridgeError("passive-backflow cartridge route changed")
    if tuple(matches[0].centerline[-1].end.as_tuple()) != ROUTE_HANDOFF_WORLD_MM:
        raise RealizedWasteCartridgeError("route handoff moved")
    return release.manifest_sha256


def current_route_digest():
    identity = tuple(
        (
            path.relative_to(ROOT).as_posix(),
            sha256(path.read_bytes()).hexdigest(),
        )
        for path in sorted((ROOT / "src/masck_one").glob("*.py"))
    )
    return _route_digest(identity)


def build_realized_waste_cartridge(*, model=None, seed=None, verify_route=True):
    require_sources()
    seed = seed or LinerSeed()
    seed.__post_init__()
    model = model or build_model()

    if tuple(model.authority.get("fluid", "cartridge", "external_envelope_mm")) != PACKAGE_ENVELOPE_XYZ_MM:
        raise RealizedWasteCartridgeError("authority package moved")
    if model.authority.number("fluid", "cartridge", "retained_capacity_min_mL") != RETAINED_CAPACITY_REQUIREMENT_ML:
        raise RealizedWasteCartridgeError("authority capacity moved")

    route_digest = "UNVERIFIED_EXPLORATION"
    if verify_route:
        route_digest = current_route_digest()

    outer = _core(seed, inner=False)
    inner = _core(seed, inner=True)

    split = 18 - seed.lid_mm - seed.collar_depth_mm
    body = outer.cut(inner).intersect(box((200, 200, split + 2), (0, -80, (split - 2) / 2)))
    collar_band = outer.intersect(
        box((200, 200, seed.collar_depth_mm), (0, -80, split + seed.collar_depth_mm / 2))
    )
    opening = _core(replace(seed, wall_mm=seed.collar_width_mm), inner=True)
    collar = collar_band.cut(opening)
    lid = outer.intersect(box((200, 200, seed.lid_mm), (0, -80, 18 - seed.lid_mm / 2)))
    closure = collar.union(lid)

    boss = cylinder((-37, -82, 14), (1, 0, 0), 2.5, 5)
    bore = cylinder((-41, -82, 14), (1, 0, 0), 9, 2.4)
    body = body.union(boss).cut(bore)

    islands = []
    for x in (-35.4, 35.4):
        island = box((3.2, 6, 1.6), (x, -82, 17.2)).intersect(outer)
        islands.append(island)
        closure = closure.union(island)

    pockets = [
        cylinder((-37, -82, 17), (1, 0, 0), 1.2, 1.4),
        cylinder((37, -82, 17), (-1, 0, 0), 1.2, 1.4),
    ]
    key = box((2.4, 1.2, 0.9), (-36.0, -80.5, 17.2))
    closure = closure.cut(key)
    for pocket in pockets:
        closure = closure.cut(pocket)

    vent = cylinder((26, -89, 16.4), (0, 0, 1), 1.6, 5)
    vent_bore = cylinder((26, -89, 16), (0, 0, 1), 4, 2)
    closure = closure.cut(vent_bore)

    dry = cq.Workplane(obj=cq.Compound.makeCompound([shape.val() for shape in islands]))
    body = body.cut(closure).cut(key)
    cavity = inner.cut(body).cut(closure).cut(vent).cut(dry)
    seal = collar_band.cut(opening).intersect(box((200, 200, 0.1), (0, -80, 17.8)))

    device = {}
    for label, sign in (("left", -1), ("right", 1)):
        pin = cylinder((sign * 35.9, -82, 17), (sign, 0, 0), 4.0, 1.2)
        guide = box((2.4, 4, 2.8), (sign * 39.5, -82, 17)).cut(
            cylinder((sign * 37.5, -82, 17), (sign, 0, 0), 4.0, 1.4)
        )
        device[label + "_bolt"] = pin
        device[label + "_bolt_guide"] = guide
    device["key_tongue"] = box((1.6, 1.0, 0.7), (-35.7, -80.5, 17.2))

    result = RealizedWasteCartridge(
        seed,
        body,
        closure,
        cavity,
        cylinder(ROUTE_HANDOFF_WORLD_MM, (1, 0, 0), 4, 4),
        seal,
        vent,
        key,
        cq.Workplane(obj=cq.Compound.makeCompound([pocket.val() for pocket in pockets])),
        dry,
        device,
        outer,
        inner,
        model,
        route_digest,
    )
    result.validate()
    return result
