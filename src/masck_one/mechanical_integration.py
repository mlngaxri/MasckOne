from __future__ import annotations

"""Evidence-bounded whole-product mechanical packaging for Masck One.

Manual A realizes only the geometry it owns, reuses released package envelopes, and
keeps missing other-lane geometry as explicit blockers. Digital CAD checks are not
physical validation evidence.
"""

from dataclasses import dataclass
import hashlib
import json
import math

import cadquery as cq

from .anatomy import build_facial_reference
from .authority import Authority, load_authority
from .exterior_surface import build_refined_exterior_shell
from .model import Component, MasckOneModel, build_model
from .spatial import CanonicalDatums, Point3


SCHEMA = "MASCK_ONE_MECHANICAL_INTEGRATION_V1"
STATUS_CANDIDATE = "MANUAL_A_DIGITAL_CAD_CANDIDATE_NOT_AUTHORITY_OR_PHYSICAL_EVIDENCE"
STATUS_RELEASED_ENVELOPE = "RELEASED_OR_AUTHORITY_BACKED_PACKAGE_ENVELOPE_NOT_PRODUCTION_FREEZE"
STATUS_BLOCKED = "BLOCKED_PENDING_OWNING_LANE_REALIZED_GEOMETRY"
STANDARD_GRAVITY_M_S2 = 9.80665

# Manual-A design-candidate dimensions. These are deliberately not written into machine
# authority and must not be presented as frozen product requirements.
FRAME_MEMBER_RADIAL_MM = 6.0
FRAME_DEPTH_MM = 2.4
FRAME_Z_REAR_MM = -4.0
REACTION_MEMBER_Y_MM = 8.0
REACTION_MEMBER_Z_MM = 2.4
HALO_OUTER_XY_MM = (162.0, 194.0)
HALO_MEMBER_RADIAL_MM = 4.0
HALO_DEPTH_MM = 4.0
HALO_Z_REAR_MM = -46.0
YOKE_X_MM = 78.0
YOKE_WIDTH_X_MM = 4.0
YOKE_HEIGHT_Y_MM = 12.0
RELEASE_TRAVEL_MM = 18.0
LOWER_SERVICE_CUT_XYZ_MM = (82.0, 45.0, 28.0)
LOWER_SERVICE_CUT_CENTER = (0.0, -102.0, 7.0)
ACTUATOR_PACKAGE_DIAMETER_MM = 10.2
ACTUATOR_PACKAGE_LENGTH_MM = 18.7
ACTUATOR_PLACEMENTS = (
    ("ACTUATOR-ZONE-A", Point3(-60.0, 66.0, -1.5), -1.0),
    ("ACTUATOR-ZONE-B", Point3(60.0, 66.0, -1.5), 1.0),
    ("ACTUATOR-ZONE-C", Point3(-58.0, -60.0, -1.5), -1.0),
    ("ACTUATOR-ZONE-D", Point3(58.0, -60.0, -1.5), 1.0),
)


class MechanicalIntegrationError(ValueError):
    pass


def _real(value: object, *, label: str, positive: bool = False) -> float:
    if type(value) not in (int, float):
        raise MechanicalIntegrationError(f"{label} must be an exact numeric scalar")
    result = float(value)
    if not math.isfinite(result) or (positive and result <= 0.0):
        raise MechanicalIntegrationError(f"{label} must be finite" + (" and positive" if positive else ""))
    return 0.0 if result == 0.0 else result


def _text(value: object, *, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise MechanicalIntegrationError(f"{label} must be exact nonblank text")
    return value


def _box(x: float, y: float, z: float, center: Point3) -> cq.Workplane:
    for label, value in (("x", x), ("y", y), ("z", z)):
        _real(value, label=f"box {label}", positive=True)
    return cq.Workplane("XY").box(x, y, z, centered=(True, True, True)).translate(center.as_tuple())


def _ring(outer_x: float, outer_y: float, radial: float, depth: float, z_rear: float) -> cq.Workplane:
    for label, value in (("outer_x", outer_x), ("outer_y", outer_y), ("radial", radial), ("depth", depth)):
        _real(value, label=label, positive=True)
    inner_x = outer_x - 2.0 * radial
    inner_y = outer_y - 2.0 * radial
    if inner_x <= 0.0 or inner_y <= 0.0:
        raise MechanicalIntegrationError("ring member consumes ring aperture")
    outer = cq.Workplane("XY").workplane(offset=z_rear).ellipse(outer_x / 2.0, outer_y / 2.0).extrude(depth)
    inner = cq.Workplane("XY").workplane(offset=z_rear - 0.5).ellipse(inner_x / 2.0, inner_y / 2.0).extrude(depth + 1.0)
    return outer.cut(inner)


def intersection_volume_mm3(a: cq.Workplane, b: cq.Workplane) -> float:
    value = float(a.val().intersect(b.val()).Volume())
    if not math.isfinite(value) or value < 0.0:
        raise MechanicalIntegrationError("intersection volume must be finite and nonnegative")
    return 0.0 if value < 1e-9 else value


def _protected_ellipse(width: float, height: float, center: tuple[float, float], clearance: float) -> cq.Workplane:
    return (
        cq.Workplane("XY").workplane(offset=-20.0).center(*center)
        .ellipse((width + 2.0 * clearance) / 2.0, (height + 2.0 * clearance) / 2.0)
        .extrude(70.0)
    )


def _protected_circle(diameter: float, center: tuple[float, float], clearance: float) -> cq.Workplane:
    return (
        cq.Workplane("XY").workplane(offset=-20.0).center(*center)
        .circle((diameter + 2.0 * clearance) / 2.0).extrude(70.0)
    )


@dataclass(frozen=True, slots=True)
class PackagePart:
    part_id: str
    solid: cq.Workplane
    owner: str
    geometry_status: str
    evidence_status: str

    def __post_init__(self) -> None:
        for label, value in (("part_id", self.part_id), ("owner", self.owner), ("geometry_status", self.geometry_status), ("evidence_status", self.evidence_status)):
            _text(value, label=label)
        shape = self.solid.val()
        if not shape.isValid() or float(shape.Volume()) <= 0.0:
            raise MechanicalIntegrationError(f"{self.part_id} is not a valid positive-volume solid")

    @property
    def volume_mm3(self) -> float:
        return float(self.solid.val().Volume())

    @property
    def centroid_xyz_mm(self) -> tuple[float, float, float]:
        c = self.solid.val().Center()
        return float(c.x), float(c.y), float(c.z)

    def manifest(self) -> dict[str, object]:
        return {
            "part_id": self.part_id,
            "owner": self.owner,
            "geometry_status": self.geometry_status,
            "evidence_status": self.evidence_status,
            "volume_mm3": self.volume_mm3,
            "centroid_xyz_mm": list(self.centroid_xyz_mm),
        }


@dataclass(frozen=True, slots=True)
class UnresolvedReservation:
    reservation_id: str
    owner: str
    reason: str
    required_for: tuple[str, ...]

    def __post_init__(self) -> None:
        for label, value in (("reservation_id", self.reservation_id), ("owner", self.owner), ("reason", self.reason)):
            _text(value, label=label)
        if type(self.required_for) is not tuple or not self.required_for:
            raise MechanicalIntegrationError("unresolved reservation must block at least one gate")

    def manifest(self) -> dict[str, object]:
        return {
            "reservation_id": self.reservation_id,
            "owner": self.owner,
            "reason": self.reason,
            "required_for": list(self.required_for),
            "status": STATUS_BLOCKED,
        }


@dataclass(frozen=True, slots=True)
class CollisionCheck:
    check_id: str
    first_id: str
    second_id: str
    intersection_volume_mm3: float
    required_clear: bool
    status: str

    def __post_init__(self) -> None:
        for label, value in (("check_id", self.check_id), ("first_id", self.first_id), ("second_id", self.second_id), ("status", self.status)):
            _text(value, label=label)
        volume = _real(self.intersection_volume_mm3, label="intersection_volume_mm3")
        if volume < 0.0:
            raise MechanicalIntegrationError("intersection volume cannot be negative")
        if type(self.required_clear) is not bool:
            raise MechanicalIntegrationError("required_clear must be a literal bool")
        if self.required_clear and volume > 0.0 and self.status == "PASS":
            raise MechanicalIntegrationError("penetrating required-clear pair cannot pass")

    @property
    def passes(self) -> bool:
        return not self.required_clear or self.intersection_volume_mm3 == 0.0

    def manifest(self) -> dict[str, object]:
        return {
            "check_id": self.check_id,
            "first_id": self.first_id,
            "second_id": self.second_id,
            "intersection_volume_mm3": self.intersection_volume_mm3,
            "required_clear": self.required_clear,
            "status": self.status,
            "passes": self.passes,
        }


@dataclass(frozen=True, slots=True)
class ServiceMotion:
    motion_id: str
    moving_part_id: str
    waypoints_xyz_mm: tuple[tuple[float, float, float], ...]
    initial_solid: cq.Workplane
    evidence_status: str

    def __post_init__(self) -> None:
        _text(self.motion_id, label="motion_id")
        _text(self.moving_part_id, label="moving_part_id")
        _text(self.evidence_status, label="evidence_status")
        if type(self.waypoints_xyz_mm) is not tuple or len(self.waypoints_xyz_mm) < 2:
            raise MechanicalIntegrationError("service motion requires at least two world-coordinate waypoints")
        for waypoint in self.waypoints_xyz_mm:
            if type(waypoint) is not tuple or len(waypoint) != 3:
                raise MechanicalIntegrationError("service waypoint must be an exact xyz tuple")
            for value in waypoint:
                _real(value, label="service waypoint")

    def sampled_solids(self) -> tuple[cq.Workplane, ...]:
        origin = self.waypoints_xyz_mm[0]
        return tuple(
            self.initial_solid.translate(tuple(point[i] - origin[i] for i in range(3)))
            for point in self.waypoints_xyz_mm
        )

    def collision_volumes(self, obstacles: tuple[PackagePart, ...]) -> dict[str, tuple[float, ...]]:
        return {
            obstacle.part_id: tuple(intersection_volume_mm3(sample, obstacle.solid) for sample in self.sampled_solids())
            for obstacle in obstacles
        }

    def manifest(self) -> dict[str, object]:
        return {
            "motion_id": self.motion_id,
            "moving_part_id": self.moving_part_id,
            "waypoints_xyz_mm": [list(point) for point in self.waypoints_xyz_mm],
            "evidence_status": self.evidence_status,
        }


@dataclass(frozen=True, slots=True)
class MassEntry:
    part_id: str
    mass_g: float | None
    centroid_xyz_mm: tuple[float, float, float]
    provenance: str
    status: str

    def __post_init__(self) -> None:
        _text(self.part_id, label="mass part_id")
        _text(self.provenance, label="mass provenance")
        _text(self.status, label="mass status")
        if self.mass_g is not None:
            object.__setattr__(self, "mass_g", _real(self.mass_g, label="mass_g", positive=True))
        if type(self.centroid_xyz_mm) is not tuple or len(self.centroid_xyz_mm) != 3:
            raise MechanicalIntegrationError("mass centroid must be an exact xyz tuple")

    def manifest(self) -> dict[str, object]:
        return {
            "part_id": self.part_id,
            "mass_g": self.mass_g,
            "centroid_xyz_mm": list(self.centroid_xyz_mm),
            "provenance": self.provenance,
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class MechanicalIntegration:
    authority_revision: str
    parts: tuple[PackagePart, ...]
    protected_keepouts: tuple[PackagePart, ...]
    collision_checks: tuple[CollisionCheck, ...]
    service_motions: tuple[ServiceMotion, ...]
    unresolved: tuple[UnresolvedReservation, ...]
    mass_entries: tuple[MassEntry, ...]
    assembly_sequence: tuple[str, ...]
    source_status: str

    def __post_init__(self) -> None:
        _text(self.authority_revision, label="authority_revision")
        _text(self.source_status, label="source_status")
        for value, label in ((self.parts, "parts"), (self.protected_keepouts, "protected_keepouts"), (self.collision_checks, "collision_checks"), (self.service_motions, "service_motions"), (self.unresolved, "unresolved"), (self.mass_entries, "mass_entries"), (self.assembly_sequence, "assembly_sequence")):
            if type(value) is not tuple or not value:
                raise MechanicalIntegrationError(f"{label} must be a non-empty exact tuple")
        if len({part.part_id for part in self.parts}) != len(self.parts):
            raise MechanicalIntegrationError("package part IDs cannot repeat")
        if any(check.required_clear and not check.passes for check in self.collision_checks):
            raise MechanicalIntegrationError("owned required-clear collision remains in integration candidate")

    @property
    def package_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    @property
    def known_dry_mass_g(self) -> float:
        return sum(entry.mass_g for entry in self.mass_entries if entry.mass_g is not None)

    @property
    def complete_dry_mass_available(self) -> bool:
        return all(entry.mass_g is not None for entry in self.mass_entries)

    @property
    def known_mass_cg_xyz_mm(self) -> tuple[float, float, float]:
        known = tuple(entry for entry in self.mass_entries if entry.mass_g is not None)
        total = sum(entry.mass_g for entry in known)
        if total <= 0.0:
            raise MechanicalIntegrationError("known-mass CG requires at least one controlled mass")
        return (
            sum(entry.mass_g * entry.centroid_xyz_mm[0] for entry in known) / total,
            sum(entry.mass_g * entry.centroid_xyz_mm[1] for entry in known) / total,
            sum(entry.mass_g * entry.centroid_xyz_mm[2] for entry in known) / total,
        )

    @property
    def known_mass_pitch_moment_Nm(self) -> float:
        return (self.known_dry_mass_g / 1000.0) * STANDARD_GRAVITY_M_S2 * (abs(self.known_mass_cg_xyz_mm[2]) / 1000.0)

    def mass_manifest(self, authority: Authority) -> dict[str, object]:
        return {
            "entries": [entry.manifest() for entry in self.mass_entries],
            "known_dry_mass_g": self.known_dry_mass_g,
            "known_mass_cg_xyz_mm": list(self.known_mass_cg_xyz_mm),
            "known_mass_pitch_moment_Nm": self.known_mass_pitch_moment_Nm,
            "dry_target_max_g": float(authority.get("mass", "dry_target_max_g")),
            "loaded_absolute_max_g": float(authority.get("mass", "loaded_absolute_max_g")),
            "cg_z_max_mm": float(authority.get("mass", "cg_z_max_mm")),
            "pitch_torque_max_Nm": float(authority.get("mass", "pitch_torque_max_Nm")),
            "complete_dry_mass_g": self.known_dry_mass_g if self.complete_dry_mass_available else None,
            "loaded_mass_g": None,
            "whole_product_cg_xyz_mm": None,
            "whole_product_pitch_moment_Nm": None,
            "gate_status": "BLOCKED_MATERIAL_DENSITIES_SUPPLIER_MASSES_AND_WET_INVENTORY_MASS_NOT_CONTROLLED" if not self.complete_dry_mass_available else "DIGITAL_LEDGER_COMPLETE",
            "comparison_semantics": "KNOWN_PARTIAL_MASS_MUST_NOT_BE_COMPARED_AS_WHOLE_PRODUCT_PASS",
        }

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "authority_revision": self.authority_revision,
            "source_status": self.source_status,
            "parts": [part.manifest() for part in self.parts],
            "protected_keepouts": [part.manifest() for part in self.protected_keepouts],
            "collision_checks": [check.manifest() for check in self.collision_checks],
            "service_motions": [motion.manifest() for motion in self.service_motions],
            "unresolved": [item.manifest() for item in self.unresolved],
            "mass_entries": [entry.manifest() for entry in self.mass_entries],
            "assembly_sequence": list(self.assembly_sequence),
            "evidence_status": "DIGITAL_PACKAGING_COLLISION_SERVICE_AND_LOAD_PATH_PREFLIGHT_NOT_PHYSICAL_VALIDATION",
        }
        if include_sha:
            payload["package_sha256"] = self.package_sha256
        return payload


def _build_keepouts(authority: Authority) -> tuple[PackagePart, ...]:
    eye_w, eye_h = authority.pair("geometry", "eye", "visual_aperture_wh_mm")
    eye_clear = authority.number("geometry", "eye", "rigid_dynamic_keepout_clearance_mm")
    eye_centers = authority.get("geometry", "eye", "centers_mm")
    mouth_w, mouth_h = authority.pair("geometry", "mouth", "visual_aperture_wh_mm")
    mouth_clear = authority.number("geometry", "mouth", "rigid_dynamic_keepout_clearance_mm")
    mouth_center = authority.get("geometry", "mouth", "center_mm")
    nostril_clear = authority.number("geometry", "nostrils", "rigid_dynamic_keepout_clearance_mm")
    nostril_centers = authority.get("geometry", "nostrils", "centers_mm")
    area = authority.number("geometry", "nostrils", "minimum_deformed_area_each_mm2")
    local = authority.number("geometry", "nostrils", "minimum_local_opening_dimension_mm")
    nostril_d = max(local, math.sqrt(4.0 * area * 1.02 / math.pi))
    raw = (
        ("KEEPOUT-EYE-LEFT", _protected_ellipse(eye_w, eye_h, tuple(eye_centers["left"]), eye_clear)),
        ("KEEPOUT-EYE-RIGHT", _protected_ellipse(eye_w, eye_h, tuple(eye_centers["right"]), eye_clear)),
        ("KEEPOUT-MOUTH", _protected_ellipse(mouth_w, mouth_h, tuple(mouth_center), mouth_clear)),
        ("KEEPOUT-NOSTRIL-LEFT", _protected_circle(nostril_d, tuple(nostril_centers["left"]), nostril_clear)),
        ("KEEPOUT-NOSTRIL-RIGHT", _protected_circle(nostril_d, tuple(nostril_centers["right"]), nostril_clear)),
    )
    return tuple(PackagePart(identifier, solid, "AUTHORITY", "AUTHORITY_DERIVED_DYNAMIC_RIGID_KEEPOUT", "DIGITAL_KEEPOUT_NOT_HUMAN_FIT_EVIDENCE") for identifier, solid in raw)


def _build_frame(authority: Authority) -> PackagePart:
    width, height = authority.pair("geometry", "functional_frame_xy_mm")
    return PackagePart(
        "FRAME-PERIMETER-REACTION",
        _ring(width, height, FRAME_MEMBER_RADIAL_MM, FRAME_DEPTH_MM, FRAME_Z_REAR_MM),
        "MANUAL_A",
        STATUS_CANDIDATE,
        "REALIZED_CLOSED_DIGITAL_REACTION_MEMBER_MATERIAL_DEFLECTION_AND_LOAD_VALIDATION_UNRESOLVED",
    )


def _build_actuation(authority: Authority, frame: PackagePart) -> tuple[tuple[PackagePart, ...], tuple[PackagePart, ...]]:
    angle = authority.number("actuation", "clean", "axis_angle_baseline_deg")
    frame_width, _ = authority.pair("geometry", "functional_frame_xy_mm")
    frame_half_width = frame_width / 2.0
    actuators: list[PackagePart] = []
    reactions: list[PackagePart] = []
    for zone_id, origin, sign in ACTUATOR_PLACEMENTS:
        solid = (
            cq.Workplane("XY").circle(ACTUATOR_PACKAGE_DIAMETER_MM / 2.0).extrude(ACTUATOR_PACKAGE_LENGTH_MM)
            .rotate((0.0, 0.0, 0.0), (0.0, 1.0, 0.0), sign * angle).translate(origin.as_tuple())
        )
        actuators.append(PackagePart(zone_id, solid, "MANUAL_A", "SUPPLIER_PACKAGE_ENVELOPE_AT_MANUAL_A_PLACEMENT_CANDIDATE", "DIGITAL_PACKAGE_REFERENCE_NOT_FORCE_FATIGUE_OR_ACOUSTIC_EVIDENCE"))

        target_x = math.copysign(frame_half_width - FRAME_MEMBER_RADIAL_MM / 2.0, origin.x)
        x_center = (origin.x + target_x) / 2.0
        strut = _box(abs(target_x - origin.x) + FRAME_MEMBER_RADIAL_MM, REACTION_MEMBER_Y_MM, REACTION_MEMBER_Z_MM, Point3(x_center, origin.y, FRAME_Z_REAR_MM + FRAME_DEPTH_MM / 2.0))
        mount = _box(14.0, 14.0, 4.0, Point3(origin.x, origin.y, -1.4))
        reaction = PackagePart(f"REACTION-{zone_id}", strut.union(mount), "MANUAL_A", STATUS_CANDIDATE, "GEOMETRIC_LOAD_PATH_TO_PERIMETER_REALIZED_MATERIAL_DEFLECTION_AND_FATIGUE_UNVALIDATED")
        if intersection_volume_mm3(reaction.solid, frame.solid) <= 0.0:
            raise MechanicalIntegrationError(f"{reaction.part_id} does not connect to perimeter reaction frame")
        reactions.append(reaction)
    return tuple(actuators), tuple(reactions)


def _build_retention(frame: PackagePart) -> tuple[PackagePart, ...]:
    halo = PackagePart("RETENTION-HALO-OCCIPITAL-CROWN", _ring(*HALO_OUTER_XY_MM, HALO_MEMBER_RADIAL_MM, HALO_DEPTH_MM, HALO_Z_REAR_MM), "MANUAL_A", STATUS_CANDIDATE, "DIGITAL_RETENTION_GEOMETRY_NOT_FIT_COMFORT_PRELOAD_OR_DURABILITY_EVIDENCE")
    left = PackagePart("RETENTION-YOKE-LEFT", _box(YOKE_WIDTH_X_MM, YOKE_HEIGHT_Y_MM, 45.0, Point3(-YOKE_X_MM, 0.0, -24.0)), "MANUAL_A", STATUS_CANDIDATE, "CONTINUOUS_DIGITAL_LOAD_PATH_NOT_PHYSICAL_LOAD_EVIDENCE")
    right_front = _box(YOKE_WIDTH_X_MM, YOKE_HEIGHT_Y_MM, 15.0, Point3(YOKE_X_MM, 0.0, -10.5))
    right_rear = _box(YOKE_WIDTH_X_MM, YOKE_HEIGHT_Y_MM, 22.0, Point3(YOKE_X_MM, 0.0, -36.0))
    right = PackagePart("RETENTION-YOKE-RIGHT-FIXED", right_front.union(right_rear), "MANUAL_A", STATUS_CANDIDATE, "SPLIT_YOKE_WITH_UNPOWERED_LATCH_INTERFACE_NOT_PHYSICAL_LOAD_EVIDENCE")
    latch = PackagePart(
        "QUICK-RELEASE-LATCH-MOVING",
        _box(8.0, 14.0, 12.0, Point3(YOKE_X_MM, 0.0, -22.0)).union(_box(16.0, 18.0, 5.0, Point3(YOKE_X_MM + 8.0, 0.0, -22.0))),
        "MANUAL_A",
        STATUS_CANDIDATE,
        "UNPOWERED_GEOMETRIC_RELEASE_PATH_ONLY_FORCE_AND_TIME_REQUIRE_PHYSICAL_VALIDATION",
    )
    for identifier, part, upstream, downstream in (
        ("left yoke", left, frame, halo),
        ("right fixed yoke", right, frame, halo),
    ):
        if intersection_volume_mm3(part.solid, upstream.solid) <= 0.0 or intersection_volume_mm3(part.solid, downstream.solid) <= 0.0:
            raise MechanicalIntegrationError(f"{identifier} does not close frame-to-halo load path")
    if intersection_volume_mm3(latch.solid, right.solid) <= 0.0:
        raise MechanicalIntegrationError("quick-release latch does not engage split right yoke")
    return halo, left, right, latch


def _component_part(component: Component, *, owner: str, status: str) -> PackagePart:
    return PackagePart(component.name.upper().replace("_", "-"), component.solid, owner, status, component.notes or status)


def _clear(check_id: str, first: PackagePart, second: PackagePart) -> CollisionCheck:
    volume = intersection_volume_mm3(first.solid, second.solid)
    return CollisionCheck(check_id, first.part_id, second.part_id, volume, True, "PASS" if volume == 0.0 else "FAIL")


def _assert_motion_clear(motion: ServiceMotion, obstacles: tuple[PackagePart, ...], *, ignore_first: bool = False) -> None:
    for obstacle_id, volumes in motion.collision_volumes(obstacles).items():
        relevant = volumes[1:] if ignore_first else volumes
        if any(value > 0.0 for value in relevant):
            raise MechanicalIntegrationError(f"{motion.motion_id} collides with {obstacle_id}: {volumes}")


def build_mechanical_integration(authority: Authority | None = None) -> MechanicalIntegration:
    authority = authority or load_authority()
    datums = CanonicalDatums.from_authority(authority)
    face = build_facial_reference(authority, datums)
    exterior = PackagePart("EXTERIOR-SHELL-REFINED", build_refined_exterior_shell(authority, face), "MANUAL_B_INGESTED_FROM_LIVE_MAIN", "LIVE_MAIN_CONTROLLED_EXTERIOR_SURFACE", "DIGITAL_CAD_CONVERGENCE_NOT_CLASS_A_OR_PHYSICAL_EVIDENCE")
    model: MasckOneModel = build_model(authority)
    water = _component_part(model.water_reservoir_envelope, owner="RELEASED_BASELINE", status=STATUS_RELEASED_ENVELOPE)
    cartridge = _component_part(model.waste_cartridge_envelope, owner="CELL_4_RELEASED_BASELINE", status=STATUS_RELEASED_ENVELOPE)
    battery = _component_part(model.battery_reference_envelope, owner="ELECTRONICS_BENCHMARK", status="PACKAGING_BENCHMARK_NOT_PRODUCTION_FREEZE")

    frame = _build_frame(authority)
    actuators, reactions = _build_actuation(authority, frame)
    retention = _build_retention(frame)
    keepouts = _build_keepouts(authority)

    service_cut = _box(*LOWER_SERVICE_CUT_XYZ_MM, Point3(*LOWER_SERVICE_CUT_CENTER))
    service_shell = PackagePart("EXTERIOR-SHELL-MECHANICAL-SERVICE-STATE", exterior.solid.cut(service_cut), "MANUAL_A_INTERFACE_HANDOFF_TO_MANUAL_B", "LOWER_CARTRIDGE_ACCESS_CUT_CANDIDATE_REQUIRES_EXTERIOR_CONVERGENCE", "DIGITAL_SERVICE_STATE_ONLY_NOT_SEAL_INGRESS_OR_CMF_EVIDENCE")
    service_door = PackagePart("LOWER-SERVICE-DOOR-ENVELOPE", _box(82.0, 3.0, 28.0, Point3(0.0, -102.0, 7.0)), "MANUAL_A_INTERFACE_HANDOFF_TO_MANUAL_B", STATUS_CANDIDATE, "DOOR_ENVELOPE_ONLY_SEAL_LATCH_TOLERANCE_INGRESS_AND_CMF_UNRESOLVED")

    collision_checks: list[CollisionCheck] = []
    for part in (*actuators, *reactions):
        for keepout in keepouts:
            collision_checks.append(_clear(f"CLEAR-{part.part_id}-{keepout.part_id}", part, keepout))
    latch = retention[3]
    collision_checks.append(_clear("CLEAR-RELEASE-LATCH-SHELL", latch, exterior))
    for keepout in keepouts:
        collision_checks.append(_clear(f"CLEAR-RELEASE-{keepout.part_id}", latch, keepout))

    cartridge_center = cartridge.centroid_xyz_mm
    cartridge_motion = ServiceMotion(
        "SERVICE-WASTE-CARTRIDGE-DOWNWARD",
        cartridge.part_id,
        (cartridge_center, (cartridge_center[0], -100.0, cartridge_center[2]), (cartridge_center[0], -122.0, cartridge_center[2]), (cartridge_center[0], -145.0, cartridge_center[2])),
        cartridge.solid,
        "DIGITAL_INSERTION_REMOVAL_TRAJECTORY_WITH_MANUAL_A_SERVICE_CUT_NOT_HYGIENE_OR_SEAL_EVIDENCE",
    )
    _assert_motion_clear(cartridge_motion, (service_shell, frame, retention[0], retention[1], retention[2]))

    release_center = latch.centroid_xyz_mm
    release_motion = ServiceMotion(
        "SERVICE-QUICK-RELEASE-OUTBOARD",
        latch.part_id,
        (release_center, (release_center[0] + 6.0, release_center[1], release_center[2]), (release_center[0] + 12.0, release_center[1], release_center[2]), (release_center[0] + RELEASE_TRAVEL_MM, release_center[1], release_center[2])),
        latch.solid,
        "UNPOWERED_CONTINUOUS_DIGITAL_LATCH_WITHDRAWAL_5_TO_12_N_AND_2_S_UNVALIDATED",
    )
    _assert_motion_clear(release_motion, (exterior, frame, retention[0], retention[1], retention[2]), ignore_first=True)

    battery_center = battery.centroid_xyz_mm
    battery_motion = ServiceMotion(
        "SERVICE-BATTERY-BENCHMARK-REARWARD",
        battery.part_id,
        (battery_center, (battery_center[0], battery_center[1], -28.0), (battery_center[0], battery_center[1], -40.0), (battery_center[0], battery_center[1], -60.0)),
        battery.solid,
        "BENCHMARK_ENVELOPE_SERVICE_TRAJECTORY_ONLY_FINAL_CELL_SWELLING_CONNECTOR_AND_DRY_BAY_UNRESOLVED",
    )
    _assert_motion_clear(battery_motion, (exterior, frame, retention[1], retention[2]))

    unresolved = (
        UnresolvedReservation("FRESH-FLUID-63-SEGMENT-REALIZED-ROUTES", "CELL_4", "latest green fluidics candidate defines evidence contracts but no released 3D centerlines, cross-sections or bend envelopes", ("tube bend clearance", "wet/dry separation", "prime/dead-volume geometry", "service motion")),
        UnresolvedReservation("CLEANSER-STORAGE-REALIZED-GEOMETRY", "MANUAL_B_CELL_4", "cleanser capacity, port positions, dead volume and purge geometry remain explicitly unresolved", ("refill trajectory", "cleanser package collision", "mass and CG")),
        UnresolvedReservation("PCB-DRY-BAY-AND-HARNESS-GEOMETRY", "MANUAL_B_CELL_2", "no controlled PCB dry-bay, connector or harness-loop geometry exists on live main", ("wet/dry separation", "harness collision", "shell closure", "mass and CG")),
        UnresolvedReservation("HMI-STACK-AND-SEAL-GEOMETRY", "MANUAL_B", "HMI location is reserved but switch, LED and seal stack are not realized", ("control press load path", "user access", "ingress closure")),
        UnresolvedReservation("BATTERY-SWELLING-ALLOWANCE", "MANUAL_B_CELL_2", "authority contains a battery packaging benchmark but no controlled swelling allowance or production cell freeze", ("battery clearance", "dry-bay closure", "service clearance")),
        UnresolvedReservation("WARM-COOL-THERMAL-HARDWARE", "MANUAL_B_CELL_2", "WARM and bounded COOL hardware envelopes are not released", ("thermal reservation collision", "shell closure", "mass and CG")),
        UnresolvedReservation("WASTE-BACKFLOW-AND-TUBE-REALIZED-GEOMETRY", "CELL_4", "waste topology preserves the passive backflow barrier but the physical device and adjacent routes are not realized", ("waste service collision", "wet/dry separation", "hygiene closure")),
    )

    mass_entries = (
        MassEntry(frame.part_id, None, frame.centroid_xyz_mm, "GEOMETRY_CONTROLLED_MATERIAL_DENSITY_UNSELECTED", "UNRESOLVED"),
        MassEntry(exterior.part_id, None, exterior.centroid_xyz_mm, "GEOMETRY_CONTROLLED_MATERIAL_DENSITY_UNSELECTED", "UNRESOLVED"),
        *(MassEntry(part.part_id, None, part.centroid_xyz_mm, "SUPPLIER_PACKAGE_ENVELOPE_PRESENT_MASS_NOT_CONTROLLED_IN_AUTHORITY", "UNRESOLVED") for part in actuators),
        MassEntry(water.part_id, None, water.centroid_xyz_mm, "ENVELOPE_CONTROLLED_EMPTY_RESERVOIR_MATERIAL_AND_WATER_MASS_ACCOUNTING_UNRESOLVED", "UNRESOLVED"),
        MassEntry(cartridge.part_id, None, cartridge.centroid_xyz_mm, "ENVELOPE_CONTROLLED_CARTRIDGE_MATERIAL_MEDIA_AND_RETAINED_WASTE_MASS_UNRESOLVED", "UNRESOLVED"),
        MassEntry(battery.part_id, float(authority.get("battery_reference", "mass_g")), battery.centroid_xyz_mm, "AUTHORITY_BATTERY_REFERENCE_SUPPLIER_BENCHMARK", str(authority.get("battery_reference", "status"))),
        *(MassEntry(part.part_id, None, part.centroid_xyz_mm, "MANUAL_A_CANDIDATE_GEOMETRY_MATERIAL_DENSITY_UNSELECTED", "UNRESOLVED") for part in retention),
    )

    sequence = (
        "1 establish compliant interface and protected-region datums",
        "2 install Manual-A perimeter reaction frame from wearer side before exterior closure",
        "3 install four reaction members and actuator package envelopes from wearer side",
        "4 install fixed retention yokes and rear occipital/crown halo",
        "5 install unpowered right-side quick-release latch and verify full outboard withdrawal sweep",
        "6 insert water, cartridge and battery benchmark packages only through their controlled service corridors",
        "7 close lower cartridge service door after insertion; seal and latch production details remain unresolved",
        "8 add fluidics, harness, PCB/HMI and thermal hardware only after owning lanes release 3D geometry",
        "9 perform final shell closure only after every unresolved reservation has geometry and collision evidence",
    )

    return MechanicalIntegration(
        authority_revision=str(authority.get("project", "authority_revision")),
        parts=(exterior, service_shell, service_door, frame, *actuators, *reactions, *retention, water, cartridge, battery),
        protected_keepouts=keepouts,
        collision_checks=tuple(collision_checks),
        service_motions=(cartridge_motion, release_motion, battery_motion),
        unresolved=unresolved,
        mass_entries=mass_entries,
        assembly_sequence=sequence,
        source_status="LIVE_MAIN_EXTERIOR_PLUS_RELEASED_BASELINE_ENVELOPES_PLUS_MANUAL_A_OWNED_CANDIDATE_GEOMETRY",
    )
