from __future__ import annotations

"""Whole-product mechanical packaging and service-motion integration for Masck One.

This module is deliberately evidence bounded. It realizes geometry owned by Manual A,
reuses released package envelopes, and records unresolved other-lane geometry as blockers
rather than inventing production dimensions. Digital clearance is not physical evidence.
"""

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Iterable

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

# Manual-A-owned integration dimensions. These are design-candidate geometry, not new
# authority. They may move during DFM/tolerance convergence without changing frozen
# product requirements.
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


def _finite(value: object, *, label: str) -> float:
    if type(value) not in (int, float):
        raise MechanicalIntegrationError(f"{label} must be an exact numeric scalar")
    result = float(value)
    if not math.isfinite(result):
        raise MechanicalIntegrationError(f"{label} must be finite")
    return 0.0 if result == 0.0 else result


def _positive(value: object, *, label: str) -> float:
    result = _finite(value, label=label)
    if result <= 0.0:
        raise MechanicalIntegrationError(f"{label} must be positive")
    return result


def _text(value: object, *, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise MechanicalIntegrationError(f"{label} must be exact nonblank text")
    return value


def _box(x_mm: float, y_mm: float, z_mm: float, center: Point3) -> cq.Workplane:
    return (
        cq.Workplane("XY")
        .box(_positive(x_mm, label="box x"), _positive(y_mm, label="box y"), _positive(z_mm, label="box z"), centered=(True, True, True))
        .translate(center.as_tuple())
    )


def _elliptic_ring(
    outer_x_mm: float,
    outer_y_mm: float,
    radial_mm: float,
    depth_mm: float,
    z_rear_mm: float,
) -> cq.Workplane:
    outer_x = _positive(outer_x_mm, label="ring outer x")
    outer_y = _positive(outer_y_mm, label="ring outer y")
    radial = _positive(radial_mm, label="ring radial member")
    depth = _positive(depth_mm, label="ring depth")
    inner_x = outer_x - 2.0 * radial
    inner_y = outer_y - 2.0 * radial
    if inner_x <= 0.0 or inner_y <= 0.0:
        raise MechanicalIntegrationError("ring member consumes the full ring aperture")
    outer = cq.Workplane("XY").workplane(offset=z_rear_mm).ellipse(outer_x / 2.0, outer_y / 2.0).extrude(depth)
    inner = cq.Workplane("XY").workplane(offset=z_rear_mm - 0.5).ellipse(inner_x / 2.0, inner_y / 2.0).extrude(depth + 1.0)
    return outer.cut(inner)


def _intersection_volume_mm3(a: cq.Workplane, b: cq.Workplane) -> float:
    intersection = a.val().intersect(b.val())
    volume = float(intersection.Volume())
    if not math.isfinite(volume) or volume < 0.0:
        raise MechanicalIntegrationError("shape intersection volume must be finite and nonnegative")
    return 0.0 if volume < 1e-9 else volume


def _union(shapes: Iterable[cq.Workplane]) -> cq.Workplane:
    shapes = tuple(shapes)
    if not shapes:
        raise MechanicalIntegrationError("union requires at least one shape")
    result = shapes[0]
    for shape in shapes[1:]:
        result = result.union(shape)
    return result


def _dynamic_keepout_ellipse(width: float, height: float, center_xy: tuple[float, float], clearance: float) -> cq.Workplane:
    x, y = center_xy
    return (
        cq.Workplane("XY")
        .workplane(offset=-20.0)
        .center(x, y)
        .ellipse((width + 2.0 * clearance) / 2.0, (height + 2.0 * clearance) / 2.0)
        .extrude(70.0)
    )


def _dynamic_keepout_circle(diameter: float, center_xy: tuple[float, float], clearance: float) -> cq.Workplane:
    x, y = center_xy
    return (
        cq.Workplane("XY")
        .workplane(offset=-20.0)
        .center(x, y)
        .circle((diameter + 2.0 * clearance) / 2.0)
        .extrude(70.0)
    )


@dataclass(frozen=True, slots=True)
class PackagePart:
    part_id: str
    solid: cq.Workplane
    owner: str
    geometry_status: str
    evidence_status: str

    def __post_init__(self) -> None:
        _text(self.part_id, label="part_id")
        _text(self.owner, label="owner")
        _text(self.geometry_status, label="geometry_status")
        _text(self.evidence_status, label="evidence_status")
        solid = self.solid.val()
        if not solid.isValid() or float(solid.Volume()) <= 0.0:
            raise MechanicalIntegrationError(f"{self.part_id} must be a valid positive-volume solid")

    @property
    def volume_mm3(self) -> float:
        return float(self.solid.val().Volume())

    @property
    def centroid_xyz_mm(self) -> tuple[float, float, float]:
        center = self.solid.val().Center()
        return (float(center.x), float(center.y), float(center.z))

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
        _text(self.reservation_id, label="reservation_id")
        _text(self.owner, label="owner")
        _text(self.reason, label="reason")
        if type(self.required_for) is not tuple or not self.required_for:
            raise MechanicalIntegrationError("unresolved reservation must block at least one integration gate")
        for item in self.required_for:
            _text(item, label="required_for item")

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
        volume = _finite(self.intersection_volume_mm3, label="intersection_volume_mm3")
        if volume < 0.0:
            raise MechanicalIntegrationError("intersection volume cannot be negative")
        if type(self.required_clear) is not bool:
            raise MechanicalIntegrationError("required_clear must be a literal bool")
        object.__setattr__(self, "intersection_volume_mm3", volume)
        if self.required_clear and volume > 0.0 and self.status == "PASS":
            raise MechanicalIntegrationError("a penetrating required-clear pair cannot pass")

    @property
    def passes(self) -> bool:
        return (not self.required_clear) or self.intersection_volume_mm3 == 0.0

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
    moving_solid_at_first_waypoint: cq.Workplane
    evidence_status: str

    def __post_init__(self) -> None:
        _text(self.motion_id, label="motion_id")
        _text(self.moving_part_id, label="moving_part_id")
        _text(self.evidence_status, label="evidence_status")
        if type(self.waypoints_xyz_mm) is not tuple or len(self.waypoints_xyz_mm) < 2:
            raise MechanicalIntegrationError("service motion requires at least two waypoints")
        for waypoint in self.waypoints_xyz_mm:
            if type(waypoint) is not tuple or len(waypoint) != 3:
                raise MechanicalIntegrationError("service waypoint must be an exact xyz tuple")
            for value in waypoint:
                _finite(value, label="service waypoint coordinate")

    def sampled_solids(self) -> tuple[cq.Workplane, ...]:
        origin = self.waypoints_xyz_mm[0]
        result = []
        for waypoint in self.waypoints_xyz_mm:
            delta = tuple(waypoint[index] - origin[index] for index in range(3))
            result.append(self.moving_solid_at_first_waypoint.translate(delta))
        return tuple(result)

    def collision_volumes(self, obstacles: tuple[PackagePart, ...]) -> dict[str, tuple[float, ...]]:
        return {
            obstacle.part_id: tuple(_intersection_volume_mm3(sample, obstacle.solid) for sample in self.sampled_solids())
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
            mass = _positive(self.mass_g, label="mass_g")
            object.__setattr__(self, "mass_g", mass)
        if type(self.centroid_xyz_mm) is not tuple or len(self.centroid_xyz_mm) != 3:
            raise MechanicalIntegrationError("mass centroid must be an exact xyz tuple")
        for value in self.centroid_xyz_mm:
            _finite(value, label="mass centroid coordinate")

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
        for collection, label in (
            (self.parts, "parts"),
            (self.protected_keepouts, "protected_keepouts"),
            (self.collision_checks, "collision_checks"),
            (self.service_motions, "service_motions"),
            (self.unresolved, "unresolved"),
            (self.mass_entries, "mass_entries"),
            (self.assembly_sequence, "assembly_sequence"),
        ):
            if type(collection) is not tuple or not collection:
                raise MechanicalIntegrationError(f"{label} must be a non-empty exact tuple")
        if len({part.part_id for part in self.parts}) != len(self.parts):
            raise MechanicalIntegrationError("package part IDs cannot repeat")
        if len({item.reservation_id for item in self.unresolved}) != len(self.unresolved):
            raise MechanicalIntegrationError("unresolved reservation IDs cannot repeat")
        if any(check.required_clear and not check.passes for check in self.collision_checks):
            raise MechanicalIntegrationError("released integration object cannot contain an unacknowledged required-clear penetration")

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
        return tuple(sum(entry.mass_g * entry.centroid_xyz_mm[axis] for entry in known) / total for axis in range(3))  # type: ignore[return-value]

    @property
    def known_mass_pitch_moment_Nm(self) -> float:
        cg_z = abs(self.known_mass_cg_xyz_mm[2])
        return (self.known_dry_mass_g / 1000.0) * STANDARD_GRAVITY_M_S2 * (cg_z / 1000.0)

    def mass_manifest(self, authority: Authority) -> dict[str, object]:
        dry_target = float(authority.get("mass", "dry_target_max_g"))
        loaded_max = float(authority.get("mass", "loaded_absolute_max_g"))
        cg_max = float(authority.get("mass", "cg_z_max_mm"))
        pitch_max = float(authority.get("mass", "pitch_torque_max_Nm"))
        return {
            "entries": [entry.manifest() for entry in self.mass_entries],
            "known_dry_mass_g": self.known_dry_mass_g,
            "known_mass_cg_xyz_mm": list(self.known_mass_cg_xyz_mm),
            "known_mass_pitch_moment_Nm": self.known_mass_pitch_moment_Nm,
            "dry_target_max_g": dry_target,
            "loaded_absolute_max_g": loaded_max,
            "cg_z_max_mm": cg_max,
            "pitch_torque_max_Nm": pitch_max,
            "complete_dry_mass_g": self.known_dry_mass_g if self.complete_dry_mass_available else None,
            "loaded_mass_g": None,
            "whole_product_cg_xyz_mm": None,
            "whole_product_pitch_moment_Nm": None,
            "gate_status": (
                "PASS_DIGITAL_LEDGER_COMPLETE" if self.complete_dry_mass_available else
                "BLOCKED_MATERIAL_DENSITIES_SUPPLIER_MASSES_AND_WET_INVENTORY_MASS_NOT_CONTROLLED"
            ),
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


def _build_protected_keepouts(authority: Authority) -> tuple[PackagePart, ...]:
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
    items = (
        ("KEEPOUT-EYE-LEFT", _dynamic_keepout_ellipse(eye_w, eye_h, tuple(eye_centers["left"]), eye_clear)),
        ("KEEPOUT-EYE-RIGHT", _dynamic_keepout_ellipse(eye_w, eye_h, tuple(eye_centers["right"]), eye_clear)),
        ("KEEPOUT-MOUTH", _dynamic_keepout_ellipse(mouth_w, mouth_h, tuple(mouth_center), mouth_clear)),
        ("KEEPOUT-NOSTRIL-LEFT", _dynamic_keepout_circle(nostril_d, tuple(nostril_centers["left"]), nostril_clear)),
        ("KEEPOUT-NOSTRIL-RIGHT", _dynamic_keepout_circle(nostril_d, tuple(nostril_centers["right"]), nostril_clear)),
    )
    return tuple(
        PackagePart(identifier, solid, "AUTHORITY", "AUTHORITY_DERIVED_DYNAMIC_RIGID_KEEPOUT", "DIGITAL_KEEPOUT_NOT_HUMAN_FIT_EVIDENCE")
        for identifier, solid in items
    )


def _build_structural_frame(authority: Authority) -> PackagePart:
    width, height = authority.pair("geometry", "functional_frame_xy_mm")
    ring = _elliptic_ring(width, height, FRAME_MEMBER_RADIAL_MM, FRAME_DEPTH_MM, FRAME_Z_REAR_MM)
    return PackagePart("FRAME-PERIMETER-REACTION", ring, "MANUAL_A", STATUS_CANDIDATE, "REALIZED_CLOSED_DIGITAL_REACTION_MEMBER_MATERIAL_AND_LOAD_VALIDATION_UNRESOLVED")


def _build_actuation(authority: Authority, frame: PackagePart) -> tuple[tuple[PackagePart, ...], tuple[PackagePart, ...]]:
    angle = authority.number("actuation", "clean", "axis_angle_baseline_deg")
    actuators: list[PackagePart] = []
    reactions: list[PackagePart] = []
    frame_half_width = authority.number("geometry", "functional_frame_xy_mm", 0) / 2.0
    for zone_id, origin, sign in ACTUATOR_PLACEMENTS:
        actuator = (
            cq.Workplane("XY")
            .circle(ACTUATOR_PACKAGE_DIAMETER_MM / 2.0)
            .extrude(ACTUATOR_PACKAGE_LENGTH_MM)
            .rotate((0.0, 0.0, 0.0), (0.0, 1.0, 0.0), sign * angle)
            .translate(origin.as_tuple())
        )
        actuator_part = PackagePart(
            zone_id,
            actuator,
            "MANUAL_A",
            "SUPPLIER_PACKAGE_ENVELOPE_AT_MANUAL_A_PLACEMENT_CANDIDATE",
            "DIGITAL_PACKAGE_AND_SWEEP_REFERENCE_NOT_FORCE_FATIGUE_OR_ACOUSTIC_EVIDENCE",
        )
        actuators.append(actuator_part)

        x_target = math.copysign(frame_half_width - FRAME_MEMBER_RADIAL_MM / 2.0, origin.x)
        x_center = (origin.x + x_target) / 2.0
        x_length = abs(x_target - origin.x) + FRAME_MEMBER_RADIAL_MM
        strut = _box(x_length, REACTION_MEMBER_Y_MM, REACTION_MEMBER_Z_MM, Point3(x_center, origin.y, FRAME_Z_REAR_MM + FRAME_DEPTH_MM / 2.0))
        mount = _box(14.0, 14.0, 4.0, Point3(origin.x, origin.y, -1.4))
        reaction = strut.union(mount)
        reactions.append(PackagePart(
            f"REACTION-{zone_id}",
            reaction,
            "MANUAL_A",
            STATUS_CANDIDATE,
            "GEOMETRIC_LOAD_PATH_TO_PERIMETER_REALIZED_DIGITALLY_MATERIAL_DEFLECTION_FATIGUE_UNVALIDATED",
        ))
    return tuple(actuators), tuple(reactions)


def _build_retention(frame: PackagePart) -> tuple[PackagePart, ...]:
    halo = _elliptic_ring(HALO_OUTER_XY_MM[0], HALO_OUTER_XY_MM[1], HALO_MEMBER_RADIAL_MM, HALO_DEPTH_MM, HALO_Z_REAR_MM)
    halo_part = PackagePart("RETENTION-HALO-OCCIPITAL-CROWN", halo, "MANUAL_A", STATUS_CANDIDATE, "DIGITAL_RETENTION_GEOMETRY_NOT_FIT_COMFORT_PRELOAD_OR_DURABILITY_EVIDENCE")

    left_yoke = _box(YOKE_WIDTH_X_MM, YOKE_HEIGHT_Y_MM, 43.0, Point3(-YOKE_X_MM, 0.0, -24.5))
    left = PackagePart("RETENTION-YOKE-LEFT", left_yoke, "MANUAL_A", STATUS_CANDIDATE, "CONTINUOUS_DIGITAL_LOAD_PATH_NOT_PHYSICAL_LOAD_EVIDENCE")

    right_front = _box(YOKE_WIDTH_X_MM, YOKE_HEIGHT_Y_MM, 13.0, Point3(YOKE_X_MM, 0.0, -10.5))
    right_rear = _box(YOKE_WIDTH_X_MM, YOKE_HEIGHT_Y_MM, 19.0, Point3(YOKE_X_MM, 0.0, -36.5))
    right_fixed = right_front.union(right_rear)
    right = PackagePart("RETENTION-YOKE-RIGHT-FIXED", right_fixed, "MANUAL_A", STATUS_CANDIDATE, "SPLIT_YOKE_WITH_UNPOWERED_LATCH_INTERFACE_NOT_PHYSICAL_LOAD_EVIDENCE")

    latch_body = _box(8.0, 14.0, 12.0, Point3(YOKE_X_MM, 0.0, -22.0))
    pull_tab = _box(16.0, 18.0, 5.0, Point3(YOKE_X_MM + 8.0, 0.0, -22.0))
    latch = PackagePart("QUICK-RELEASE-LATCH-MOVING", latch_body.union(pull_tab), "MANUAL_A", STATUS_CANDIDATE, "UNPOWERED_GEOMETRIC_RELEASE_PATH_ONLY_5_TO_12_N_AND_2_S_REMAIN_PHYSICAL_GATES")

    # Require the geometric chain to be physically connected in the closed state.
    if _intersection_volume_mm3(left.solid, frame.solid) <= 0.0 or _intersection_volume_mm3(left.solid, halo_part.solid) <= 0.0:
        raise MechanicalIntegrationError("left retention yoke does not close frame-to-halo load path")
    if _intersection_volume_mm3(right.solid, frame.solid) <= 0.0 or _intersection_volume_mm3(right.solid, halo_part.solid) <= 0.0:
        raise MechanicalIntegrationError("right fixed yoke does not connect frame and halo")
    if _intersection_volume_mm3(latch.solid, right.solid) <= 0.0:
        raise MechanicalIntegrationError("quick-release latch does not engage the split right yoke")
    return (halo_part, left, right, latch)


def _component_part(component: Component, *, owner: str, status: str) -> PackagePart:
    return PackagePart(component.name.upper().replace("_", "-"), component.solid, owner, status, component.notes or status)


def _collision(check_id: str, first: PackagePart, second: PackagePart, *, required_clear: bool = True) -> CollisionCheck:
    volume = _intersection_volume_mm3(first.solid, second.solid)
    status = "PASS" if (not required_clear or volume == 0.0) else "FAIL"
    return CollisionCheck(check_id, first.part_id, second.part_id, volume, required_clear, status)


def build_mechanical_integration(authority: Authority | None = None) -> MechanicalIntegration:
    authority = authority or load_authority()
    datums = CanonicalDatums.from_authority(authority)
    facial_reference = build_facial_reference(authority, datums)
    exterior = PackagePart(
        "EXTERIOR-SHELL-REFINED",
        build_refined_exterior_shell(authority, facial_reference),
        "MANUAL_B_INGESTED_FROM_LIVE_MAIN",
        "LIVE_MAIN_CONTROLLED_EXTERIOR_SURFACE",
        "DIGITAL_CAD_CONVERGENCE_NOT_CLASS_A_OR_PHYSICAL_EVIDENCE",
    )
    model: MasckOneModel = build_model(authority)
    water = _component_part(model.water_reservoir_envelope, owner="RELEASED_BASELINE", status=STATUS_RELEASED_ENVELOPE)
    cartridge = _component_part(model.waste_cartridge_envelope, owner="CELL_4_RELEASED_BASELINE", status=STATUS_RELEASED_ENVELOPE)
    battery = _component_part(model.battery_reference_envelope, owner="ELECTRONICS_BENCHMARK", status="PACKAGING_BENCHMARK_NOT_PRODUCTION_FREEZE")

    frame = _build_structural_frame(authority)
    actuators, reactions = _build_actuation(authority, frame)
    retention = _build_retention(frame)
    keepouts = _build_protected_keepouts(authority)

    service_cut = _box(*LOWER_SERVICE_CUT_XYZ_MM, Point3(*LOWER_SERVICE_CUT_CENTER))
    service_shell = PackagePart(
        "EXTERIOR-SHELL-MECHANICAL-SERVICE-STATE",
        exterior.solid.cut(service_cut),
        "MANUAL_A_INTERFACE_HANDOFF_TO_MANUAL_B",
        "LOWER_CARTRIDGE_ACCESS_CUT_CANDIDATE_REQUIRES_EXTERIOR_CONVERGENCE",
        "DIGITAL_SERVICE_STATE_ONLY_NOT_SEAL_INGRESS_OR_CMF_EVIDENCE",
    )
    service_door = PackagePart(
        "LOWER-SERVICE-DOOR-ENVELOPE",
        _box(82.0, 3.0, 28.0, Point3(0.0, -102.0, 7.0)),
        "MANUAL_A_INTERFACE_HANDOFF_TO_MANUAL_B",
        STATUS_CANDIDATE,
        "DOOR_ENVELOPE_ONLY_SEAL_LATCH_TOLERANCE_INGRESS_AND_CMF_UNRESOLVED",
    )

    collision_checks: list[CollisionCheck] = []
    for part in (*actuators, *reactions):
        for keepout in keepouts:
            collision_checks.append(_collision(f"CLEAR-{part.part_id}-{keepout.part_id}", part, keepout))
    latch = next(part for part in retention if part.part_id == "QUICK-RELEASE-LATCH-MOVING")
    collision_checks.append(_collision("CLEAR-RELEASE-LATCH-SHELL", latch, exterior))
    for keepout in keepouts:
        collision_checks.append(_collision(f"CLEAR-RELEASE-{keepout.part_id}", latch, keepout))

    # Service motions are represented in world coordinates. Each waypoint is an actual
    # translated package state, not a symbolic 'remove' operation.
    cartridge_center = cartridge.centroid_xyz_mm
    cartridge_motion = ServiceMotion(
        "SERVICE-WASTE-CARTRIDGE-DOWNWARD",
        cartridge.part_id,
        (
            cartridge_center,
            (cartridge_center[0], -100.0, cartridge_center[2]),
            (cartridge_center[0], -122.0, cartridge_center[2]),
            (cartridge_center[0], -145.0, cartridge_center[2]),
        ),
        cartridge.solid,
        "DIGITAL_INSERTION_REMOVAL_TRAJECTORY_WITH_MANUAL_A_SERVICE_CUT_NOT_HYGIENE_OR_SEAL_EVIDENCE",
    )
    cartridge_obstacles = (service_shell, frame, *retention[:-1])
    cartridge_collisions = cartridge_motion.collision_volumes(cartridge_obstacles)
    for obstacle_id, volumes in cartridge_collisions.items():
        if any(volume > 0.0 for volume in volumes):
            raise MechanicalIntegrationError(f"cartridge service motion collides with {obstacle_id}: {volumes}")

    release_origin = latch.centroid_xyz_mm
    release_motion = ServiceMotion(
        "SERVICE-QUICK-RELEASE-OUTBOARD",
        latch.part_id,
        (
            release_origin,
            (release_origin[0] + 6.0, release_origin[1], release_origin[2]),
            (release_origin[0] + 12.0, release_origin[1], release_origin[2]),
            (release_origin[0] + RELEASE_TRAVEL_MM, release_origin[1], release_origin[2]),
        ),
        latch.solid,
        "UNPOWERED_CONTINUOUS_DIGITAL_LATCH_WITHDRAWAL_5_TO_12_N_AND_2_S_UNVALIDATED",
    )
    release_obstacles = (exterior, frame, retention[0], retention[1])
    release_collisions = release_motion.collision_volumes(release_obstacles)
    # The first closed waypoint may overlap the engaged frame-side mechanism by design;
    # after motion begins, no static obstacle penetration is allowed.
    for obstacle_id, volumes in release_collisions.items():
        if any(volume > 0.0 for volume in volumes[1:]):
            raise MechanicalIntegrationError(f"quick-release withdrawal collides with {obstacle_id}: {volumes}")

    battery_center = battery.centroid_xyz_mm
    battery_motion = ServiceMotion(
        "SERVICE-BATTERY-BENCHMARK-REARWARD",
        battery.part_id,
        (
            battery_center,
            (battery_center[0], battery_center[1], -28.0),
            (battery_center[0], battery_center[1], -40.0),
            (battery_center[0], battery_center[1], -60.0),
        ),
        battery.solid,
        "BENCHMARK_ENVELOPE_SERVICE_TRAJECTORY_ONLY_FINAL_CELL_SWELLING_CONNECTOR_AND_DRY_BAY_UNRESOLVED",
    )
    battery_obstacles = (exterior, frame, retention[1], retention[2])
    battery_collisions = battery_motion.collision_volumes(battery_obstacles)
    for obstacle_id, volumes in battery_collisions.items():
        if any(volume > 0.0 for volume in volumes):
            raise MechanicalIntegrationError(f"battery benchmark service motion collides with {obstacle_id}: {volumes}")

    unresolved = (
        UnresolvedReservation("FRESH-FLUID-63-SEGMENT-REALIZED-ROUTES", "CELL_4", "latest green fluidics work defines evidence contracts but no released 3D centerlines/cross-sections/bend envelopes", ("tube bend clearance", "wet/dry separation", "prime/dead-volume geometry", "service motion")),
        UnresolvedReservation("CLEANSER-STORAGE-REALIZED-GEOMETRY", "MANUAL_B_CELL_4", "cleanser capacity, port positions, dead volume and purge geometry remain explicitly unresolved", ("refill trajectory", "cleanser package collision", "mass and CG")),
        UnresolvedReservation("PCB-DRY-BAY-AND-HARNESS-GEOMETRY", "MANUAL_B_CELL_2", "no controlled PCB dry-bay, connector or harness-loop geometry exists on live main", ("wet/dry separation", "harness collision", "shell closure", "mass and CG")),
        UnresolvedReservation("HMI-STACK-AND-SEAL-GEOMETRY", "MANUAL_B", "HMI location is reserved but switch/LED/seal stack is not realized", ("control press load path", "user access", "ingress closure")),
        UnresolvedReservation("BATTERY-SWELLING-ALLOWANCE", "MANUAL_B_CELL_2", "authority contains a battery packaging benchmark but no controlled swelling allowance or production cell freeze", ("battery clearance", "dry-bay closure", "service clearance")),
        UnresolvedReservation("WARM-COOL-THERMAL-HARDWARE", "MANUAL_B_CELL_2", "WARM and bounded COOL hardware envelopes are not released", ("thermal reservation collision", "shell closure", "mass and CG")),
        UnresolvedReservation("WASTE-BACKFLOW-AND-TUBE-REALIZED-GEOMETRY", "CELL_4", "waste topology preserves the passive backflow barrier but physical device and adjacent routes are not realized", ("waste service collision", "wet/dry separation", "hygiene closure")),
    )

    battery_mass = float(authority.get("battery_reference", "mass_g"))
    mass_entries = (
        MassEntry(frame.part_id, None, frame.centroid_xyz_mm, "GEOMETRY_CONTROLLED_MATERIAL_DENSITY_UNSELECTED", "UNRESOLVED"),
        MassEntry(exterior.part_id, None, exterior.centroid_xyz_mm, "GEOMETRY_CONTROLLED_MATERIAL_DENSITY_UNSELECTED", "UNRESOLVED"),
        *(MassEntry(part.part_id, None, part.centroid_xyz_mm, "SUPPLIER_PACKAGE_ENVELOPE_PRESENT_MASS_NOT_CONTROLLED_IN_AUTHORITY", "UNRESOLVED") for part in actuators),
        MassEntry(water.part_id, None, water.centroid_xyz_mm, "ENVELOPE_CONTROLLED_EMPTY_RESERVOIR_MATERIAL_AND_WATER_MASS_ACCOUNTING_UNRESOLVED", "UNRESOLVED"),
        MassEntry(cartridge.part_id, None, cartridge.centroid_xyz_mm, "ENVELOPE_CONTROLLED_CARTRIDGE_MATERIAL_MEDIA_AND_RETAINED_WASTE_MASS_UNRESOLVED", "UNRESOLVED"),
        MassEntry(battery.part_id, battery_mass, battery.centroid_xyz_mm, "AUTHORITY_BATTERY_REFERENCE_SUPPLIER_BENCHMARK", str(authority.get("battery_reference", "status"))),
        *(MassEntry(part.part_id, None, part.centroid_xyz_mm, "MANUAL_A_CANDIDATE_GEOMETRY_MATERIAL_DENSITY_UNSELECTED", "UNRESOLVED") for part in retention),
    )

    parts = (
        exterior,
        service_shell,
        service_door,
        frame,
        *actuators,
        *reactions,
        *retention,
        water,
        cartridge,
        battery,
    )
    assembly_sequence = (
        "1 establish compliant interface and released protected-region datums",
        "2 install Manual-A perimeter reaction frame from wearer side before exterior closure",
        "3 install four actuator reaction members and actuator package envelopes from wearer side",
        "4 install fixed left/right retention yokes and rear occipital/crown halo",
        "5 install unpowered right-side quick-release latch and verify full outboard withdrawal sweep",
        "6 install water, cartridge and battery benchmark packages only after their controlled service corridors are open",
        "7 close lower cartridge service door after cartridge insertion; seal/latch details remain owning-lane unresolved",
        "8 route fresh/waste fluidics, harness, PCB/HMI and thermal hardware only after owning lanes release 3D geometry",
        "9 perform final shell closure only after every unresolved reservation above has geometry and collision evidence",
    )

    return MechanicalIntegration(
        authority_revision=str(authority.get("project", "authority_revision")),
        parts=parts,
        protected_keepouts=keepouts,
        collision_checks=tuple(collision_checks),
        service_motions=(cartridge_motion, release_motion, battery_motion),
        unresolved=unresolved,
        mass_entries=mass_entries,
        assembly_sequence=assembly_sequence,
        source_status="LIVE_MAIN_EXTERIOR_PLUS_RELEASED_BASELINE_ENVELOPES_PLUS_MANUAL_A_OWNED_CANDIDATE_GEOMETRY",
    )
