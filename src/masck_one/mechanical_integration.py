from __future__ import annotations

"""Manual A mechanical realization on top of the live-main whole-product registry.

This layer closes only Manual-A-owned geometry: structural reaction members, actuator
package placement/reaction members, retention, unpowered quick release, and bounded
service motions. Other-lane geometry remains explicit and unresolved. Digital CAD is
not physical validation evidence.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math

import cadquery as cq

from .authority import Authority, load_authority
from .model import MasckOneModel, build_model
from .spatial import Point3
from .whole_product_package import WholeProductPackage, build_whole_product_package


SCHEMA = "MASCK_ONE_MECHANICAL_REALIZATION_V2"
CANDIDATE = "MANUAL_A_DIGITAL_CAD_CANDIDATE_NOT_AUTHORITY_OR_PHYSICAL_EVIDENCE"
STANDARD_GRAVITY_M_S2 = 9.80665

FRAME_MEMBER_RADIAL_MM = 6.0
FRAME_DEPTH_MM = 2.4
FRAME_Z_REAR_MM = -4.0
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

CLOSED_BASELINE_BLOCKERS = (
    "STRUCTURAL_FRAME_3D_MEMBERS",
    "RETENTION_AND_EMERGENCY_RELEASE",
)

REMAINING_BLOCKERS = (
    "CLEANSER_STORAGE_REALIZED_GEOMETRY",
    "FRESH_FLUID_REALIZED_CENTERLINES",
    "WASTE_FLUID_REALIZED_CENTERLINES_AND_BACKFLOW_DEVICE",
    "CARTRIDGE_KEY_SEAL_DOOR_AND_SERVICE_OPENING",
    "PCB_DRY_BAY_AND_HARNESS",
    "PHYSICAL_HMI",
    "WARM_HARDWARE",
    "COOL_RESERVATION",
    "SEALS_DOORS_LATCHES",
    "BATTERY_SWELLING_ALLOWANCE",
)


class MechanicalIntegrationError(ValueError):
    pass


def _finite(value: object, label: str, *, positive: bool = False) -> float:
    if type(value) not in (int, float):
        raise MechanicalIntegrationError(f"{label} must be an exact numeric scalar")
    result = float(value)
    if not math.isfinite(result) or (positive and result <= 0.0):
        raise MechanicalIntegrationError(f"{label} must be finite" + (" and positive" if positive else ""))
    return 0.0 if result == 0.0 else result


def _text(value: object, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise MechanicalIntegrationError(f"{label} must be exact nonblank text")
    return value


def _box(x: float, y: float, z: float, center: Point3) -> cq.Workplane:
    for label, value in (("x", x), ("y", y), ("z", z)):
        _finite(value, f"box {label}", positive=True)
    return cq.Workplane("XY").box(x, y, z, centered=(True, True, True)).translate(center.as_tuple())


def _ring(outer_x: float, outer_y: float, radial: float, depth: float, z_rear: float) -> cq.Workplane:
    for label, value in (("outer_x", outer_x), ("outer_y", outer_y), ("radial", radial), ("depth", depth)):
        _finite(value, label, positive=True)
    inner_x = outer_x - 2.0 * radial
    inner_y = outer_y - 2.0 * radial
    if inner_x <= 0.0 or inner_y <= 0.0:
        raise MechanicalIntegrationError("ring member consumes ring aperture")
    outer = cq.Workplane("XY").workplane(offset=z_rear).ellipse(outer_x / 2.0, outer_y / 2.0).extrude(depth)
    inner = cq.Workplane("XY").workplane(offset=z_rear - 0.5).ellipse(inner_x / 2.0, inner_y / 2.0).extrude(depth + 1.0)
    return outer.cut(inner)


def intersection_volume_mm3(first: cq.Workplane, second: cq.Workplane) -> float:
    value = float(first.val().intersect(second.val()).Volume())
    if not math.isfinite(value) or value < 0.0:
        raise MechanicalIntegrationError("intersection volume must be finite and nonnegative")
    return 0.0 if value < 1e-9 else value


@dataclass(frozen=True, slots=True)
class RealizedPart:
    part_id: str
    solid: cq.Workplane
    role: str
    geometry_status: str
    evidence_status: str

    def __post_init__(self) -> None:
        for label, value in (("part_id", self.part_id), ("role", self.role), ("geometry_status", self.geometry_status), ("evidence_status", self.evidence_status)):
            _text(value, label)
        shape = self.solid.val()
        if not shape.isValid() or float(shape.Volume()) <= 0.0:
            raise MechanicalIntegrationError(f"{self.part_id} must be a valid positive-volume solid")

    @property
    def centroid_xyz_mm(self) -> tuple[float, float, float]:
        center = self.solid.val().Center()
        return float(center.x), float(center.y), float(center.z)

    @property
    def volume_mm3(self) -> float:
        return float(self.solid.val().Volume())

    def manifest(self) -> dict[str, object]:
        return {
            "part_id": self.part_id,
            "role": self.role,
            "geometry_status": self.geometry_status,
            "evidence_status": self.evidence_status,
            "centroid_xyz_mm": list(self.centroid_xyz_mm),
            "volume_mm3": self.volume_mm3,
        }


@dataclass(frozen=True, slots=True)
class ShapeCheck:
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
class ServiceSweep:
    sweep_id: str
    moving_part_id: str
    waypoints_xyz_mm: tuple[tuple[float, float, float], ...]
    initial_solid: cq.Workplane
    status: str

    def __post_init__(self) -> None:
        _text(self.sweep_id, "sweep_id")
        _text(self.moving_part_id, "moving_part_id")
        _text(self.status, "status")
        if type(self.waypoints_xyz_mm) is not tuple or len(self.waypoints_xyz_mm) < 2:
            raise MechanicalIntegrationError("service sweep requires at least two waypoints")

    def sampled_solids(self) -> tuple[cq.Workplane, ...]:
        origin = self.waypoints_xyz_mm[0]
        return tuple(
            self.initial_solid.translate(tuple(point[index] - origin[index] for index in range(3)))
            for point in self.waypoints_xyz_mm
        )

    def collision_volumes(self, obstacles: tuple[RealizedPart, ...]) -> dict[str, tuple[float, ...]]:
        return {
            obstacle.part_id: tuple(intersection_volume_mm3(sample, obstacle.solid) for sample in self.sampled_solids())
            for obstacle in obstacles
        }

    def manifest(self) -> dict[str, object]:
        return {
            "sweep_id": self.sweep_id,
            "moving_part_id": self.moving_part_id,
            "waypoints_xyz_mm": [list(point) for point in self.waypoints_xyz_mm],
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class MechanicalRealization:
    authority_revision: str
    baseline_package: WholeProductPackage
    realized_parts: tuple[RealizedPart, ...]
    shape_checks: tuple[ShapeCheck, ...]
    service_sweeps: tuple[ServiceSweep, ...]
    closed_baseline_blockers: tuple[str, ...]
    remaining_blockers: tuple[str, ...]
    assembly_sequence: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.closed_baseline_blockers != CLOSED_BASELINE_BLOCKERS:
            raise MechanicalIntegrationError("closed blocker set changed unexpectedly")
        if self.remaining_blockers != REMAINING_BLOCKERS:
            raise MechanicalIntegrationError("remaining blocker set changed unexpectedly")
        if any(not check.passes for check in self.shape_checks):
            raise MechanicalIntegrationError("owned required-clear shape collision remains")

    @property
    def realization_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        return sha256(raw).hexdigest()

    def mass_cg_manifest(self, authority: Authority) -> dict[str, object]:
        baseline = self.baseline_package.mass_cg
        unresolved_realized = tuple(part.part_id for part in self.realized_parts)
        return {
            "known_mass_g": baseline.known_mass_g,
            "known_cg_mm": None if baseline.known_cg_mm is None else list(baseline.known_cg_mm),
            "known_pitch_moment_Nm": baseline.known_pitch_moment_Nm,
            "new_realized_parts_with_unresolved_mass": list(unresolved_realized),
            "dry_total_g": None,
            "loaded_total_g": None,
            "whole_product_cg_mm": None,
            "whole_product_pitch_moment_Nm": None,
            "targets": {
                "dry_target_max_g": float(authority.get("mass", "dry_target_max_g")),
                "loaded_absolute_max_g": float(authority.get("mass", "loaded_absolute_max_g")),
                "cg_z_max_mm": float(authority.get("mass", "cg_z_max_mm")),
                "pitch_torque_max_Nm": float(authority.get("mass", "pitch_torque_max_Nm")),
            },
            "status": "BLOCKED_UNTIL_CONTROLLED_MATERIAL_DENSITIES_SUPPLIER_MASSES_AND_WET_LOAD_MASSES_EXIST",
            "comparison_semantics": "KNOWN_22_G_BATTERY_SUBSET_AND_PARTIAL_CG_CANNOT_ESTABLISH_WHOLE_PRODUCT_PASS",
        }

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "authority_revision": self.authority_revision,
            "baseline_package_sha256": self.baseline_package.package_sha256,
            "realized_parts": [part.manifest() for part in self.realized_parts],
            "shape_checks": [check.manifest() for check in self.shape_checks],
            "service_sweeps": [sweep.manifest() for sweep in self.service_sweeps],
            "closed_baseline_blockers": list(self.closed_baseline_blockers),
            "remaining_blockers": list(self.remaining_blockers),
            "assembly_sequence": list(self.assembly_sequence),
            "evidence_status": "DIGITAL_MECHANICAL_INTEGRATION_PREFLIGHT_NOT_PHYSICAL_VALIDATION",
        }
        if include_sha:
            payload["realization_sha256"] = self.realization_sha256
        return payload


def _build_frame(authority: Authority) -> RealizedPart:
    width, height = authority.pair("geometry", "functional_frame_xy_mm")
    return RealizedPart(
        "FRAME-PERIMETER-REACTION",
        _ring(width, height, FRAME_MEMBER_RADIAL_MM, FRAME_DEPTH_MM, FRAME_Z_REAR_MM),
        "closed perimeter structural reaction member",
        CANDIDATE,
        "GEOMETRIC_LOAD_PATH_REALIZED_MATERIAL_DEFLECTION_MODAL_FATIGUE_AND_PHYSICAL_LOAD_EVIDENCE_UNRESOLVED",
    )


def _build_actuation(authority: Authority, frame: RealizedPart) -> tuple[RealizedPart, ...]:
    angle = authority.number("actuation", "clean", "axis_angle_baseline_deg")
    width, _ = authority.pair("geometry", "functional_frame_xy_mm")
    half_width = width / 2.0
    parts: list[RealizedPart] = []
    for zone_id, origin, sign in ACTUATOR_PLACEMENTS:
        actuator = (
            cq.Workplane("XY").circle(ACTUATOR_PACKAGE_DIAMETER_MM / 2.0).extrude(ACTUATOR_PACKAGE_LENGTH_MM)
            .rotate((0.0, 0.0, 0.0), (0.0, 1.0, 0.0), sign * angle).translate(origin.as_tuple())
        )
        parts.append(RealizedPart(zone_id, actuator, "actuator supplier package at Manual-A placement", "SUPPLIER_ENVELOPE_AT_MANUAL_A_PLACEMENT_CANDIDATE", "PACKAGE_ONLY_NOT_FORCE_FATIGUE_ACOUSTIC_OR_THERMAL_EVIDENCE"))

        target_x = math.copysign(half_width - FRAME_MEMBER_RADIAL_MM / 2.0, origin.x)
        center_x = (origin.x + target_x) / 2.0
        strut = _box(abs(target_x - origin.x) + FRAME_MEMBER_RADIAL_MM, 8.0, FRAME_DEPTH_MM, Point3(center_x, origin.y, FRAME_Z_REAR_MM + FRAME_DEPTH_MM / 2.0))
        mount = _box(14.0, 14.0, 4.0, Point3(origin.x, origin.y, -1.4))
        reaction = RealizedPart(f"REACTION-{zone_id}", strut.union(mount), "actuator reaction member from mount to perimeter frame", CANDIDATE, "DIGITAL_REACTION_PATH_REALIZED_MATERIAL_DEFLECTION_AND_FATIGUE_UNVALIDATED")
        if intersection_volume_mm3(reaction.solid, frame.solid) <= 0.0:
            raise MechanicalIntegrationError(f"{reaction.part_id} does not intersect perimeter frame")
        parts.append(reaction)
    return tuple(parts)


def _build_retention(frame: RealizedPart) -> tuple[RealizedPart, ...]:
    halo = RealizedPart("RETENTION-HALO-OCCIPITAL-CROWN", _ring(*HALO_OUTER_XY_MM, HALO_MEMBER_RADIAL_MM, HALO_DEPTH_MM, HALO_Z_REAR_MM), "rear halo/occipital/crown reaction loop", CANDIDATE, "DIGITAL_GEOMETRY_NOT_FIT_COMFORT_PRELOAD_OR_DURABILITY_EVIDENCE")
    left = RealizedPart("RETENTION-YOKE-LEFT", _box(YOKE_WIDTH_X_MM, YOKE_HEIGHT_Y_MM, 45.0, Point3(-YOKE_X_MM, 0.0, -24.0)), "continuous left frame-to-halo yoke", CANDIDATE, "DIGITAL_LOAD_PATH_NOT_PHYSICAL_LOAD_EVIDENCE")
    right_front = _box(YOKE_WIDTH_X_MM, YOKE_HEIGHT_Y_MM, 15.0, Point3(YOKE_X_MM, 0.0, -10.5))
    right_rear = _box(YOKE_WIDTH_X_MM, YOKE_HEIGHT_Y_MM, 22.0, Point3(YOKE_X_MM, 0.0, -36.0))
    right = RealizedPart("RETENTION-YOKE-RIGHT-FIXED", right_front.union(right_rear), "split right frame-to-halo yoke", CANDIDATE, "DIGITAL_SPLIT_LOAD_PATH_NOT_PHYSICAL_LOAD_EVIDENCE")
    latch = RealizedPart(
        "QUICK-RELEASE-LATCH-MOVING",
        _box(8.0, 14.0, 12.0, Point3(YOKE_X_MM, 0.0, -22.0)).union(_box(16.0, 18.0, 5.0, Point3(YOKE_X_MM + 8.0, 0.0, -22.0))),
        "unpowered moving latch and wet-finger pull-tab envelope",
        CANDIDATE,
        "GEOMETRIC_WITHDRAWAL_ONLY_RELEASE_FORCE_5_TO_12_N_AND_TIME_2_S_REMAIN_PHYSICAL_GATES",
    )
    for identifier, yoke in (("left", left), ("right", right)):
        if intersection_volume_mm3(yoke.solid, frame.solid) <= 0.0 or intersection_volume_mm3(yoke.solid, halo.solid) <= 0.0:
            raise MechanicalIntegrationError(f"{identifier} yoke does not close frame-to-halo geometry")
    if intersection_volume_mm3(latch.solid, right.solid) <= 0.0:
        raise MechanicalIntegrationError("quick-release latch does not engage split right yoke")
    return halo, left, right, latch


def _protected_keepouts(authority: Authority) -> tuple[RealizedPart, ...]:
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

    def ellipse(identifier: str, width: float, height: float, center: tuple[float, float], clearance: float) -> RealizedPart:
        solid = cq.Workplane("XY").workplane(offset=-20.0).center(*center).ellipse((width + 2.0 * clearance) / 2.0, (height + 2.0 * clearance) / 2.0).extrude(70.0)
        return RealizedPart(identifier, solid, "authority-derived rigid dynamic keepout", "AUTHORITY_DERIVED_KEEP_OUT", "DIGITAL_KEEPOUT_NOT_HUMAN_FIT_EVIDENCE")

    def circle(identifier: str, diameter: float, center: tuple[float, float], clearance: float) -> RealizedPart:
        solid = cq.Workplane("XY").workplane(offset=-20.0).center(*center).circle((diameter + 2.0 * clearance) / 2.0).extrude(70.0)
        return RealizedPart(identifier, solid, "authority-derived rigid dynamic keepout", "AUTHORITY_DERIVED_KEEP_OUT", "DIGITAL_KEEPOUT_NOT_HUMAN_FIT_EVIDENCE")

    return (
        ellipse("KEEPOUT-EYE-LEFT", eye_w, eye_h, tuple(eye_centers["left"]), eye_clear),
        ellipse("KEEPOUT-EYE-RIGHT", eye_w, eye_h, tuple(eye_centers["right"]), eye_clear),
        ellipse("KEEPOUT-MOUTH", mouth_w, mouth_h, tuple(mouth_center), mouth_clear),
        circle("KEEPOUT-NOSTRIL-LEFT", nostril_d, tuple(nostril_centers["left"]), nostril_clear),
        circle("KEEPOUT-NOSTRIL-RIGHT", nostril_d, tuple(nostril_centers["right"]), nostril_clear),
    )


def _check_clear(identifier: str, first: RealizedPart, second: RealizedPart) -> ShapeCheck:
    volume = intersection_volume_mm3(first.solid, second.solid)
    return ShapeCheck(identifier, first.part_id, second.part_id, volume, "PASS" if volume == 0.0 else "FAIL")


def _assert_sweep_clear(sweep: ServiceSweep, obstacles: tuple[RealizedPart, ...], *, ignore_first: bool = False) -> None:
    for obstacle_id, volumes in sweep.collision_volumes(obstacles).items():
        relevant = volumes[1:] if ignore_first else volumes
        if any(value > 0.0 for value in relevant):
            raise MechanicalIntegrationError(f"{sweep.sweep_id} collides with {obstacle_id}: {volumes}")


def build_mechanical_realization(authority: Authority | None = None) -> MechanicalRealization:
    authority = authority or load_authority()
    model: MasckOneModel = build_model(authority)
    baseline = build_whole_product_package(model)

    shell = RealizedPart("LIVE-MAIN-RIGID-SHELL", model.shell.solid, "released live-main shell used as integration boundary", model.shell.status, model.shell.notes)
    frame = _build_frame(authority)
    actuation = _build_actuation(authority, frame)
    retention = _build_retention(frame)
    keepouts = _protected_keepouts(authority)

    checks: list[ShapeCheck] = []
    for part in actuation:
        for keepout in keepouts:
            checks.append(_check_clear(f"CLEAR-{part.part_id}-{keepout.part_id}", part, keepout))
    latch = retention[3]
    checks.append(_check_clear("CLEAR-LATCH-SHELL", latch, shell))
    for keepout in keepouts:
        checks.append(_check_clear(f"CLEAR-LATCH-{keepout.part_id}", latch, keepout))

    # Mechanical service-state shell: bounded lower access opening only. This does not
    # claim final exterior, seal, latch, ingress or CMF closure.
    service_cut = _box(*LOWER_SERVICE_CUT_XYZ_MM, Point3(*LOWER_SERVICE_CUT_CENTER))
    service_shell = RealizedPart("SERVICE-STATE-SHELL", shell.solid.cut(service_cut), "shell with lower cartridge service access removed", CANDIDATE, "MECHANICAL_ACCESS_HANDOFF_REQUIRES_MANUAL_B_SURFACE_SEAL_AND_LATCH_CONVERGENCE")
    service_door = RealizedPart("LOWER-SERVICE-DOOR-ENVELOPE", _box(82.0, 3.0, 28.0, Point3(0.0, -102.0, 7.0)), "bounded lower access door envelope", CANDIDATE, "DOOR_ENVELOPE_ONLY_SEAL_LATCH_TOLERANCE_INGRESS_AND_CMF_UNRESOLVED")

    cartridge = model.waste_cartridge_envelope
    cartridge_center = cartridge.solid.val().Center()
    cartridge_start = (float(cartridge_center.x), float(cartridge_center.y), float(cartridge_center.z))
    cartridge_sweep = ServiceSweep(
        "CARTRIDGE-DOWNWARD-REMOVAL",
        "WASTE-CARTRIDGE-ENVELOPE",
        (cartridge_start, (cartridge_start[0], -100.0, cartridge_start[2]), (cartridge_start[0], -122.0, cartridge_start[2]), (cartridge_start[0], -145.0, cartridge_start[2])),
        cartridge.solid,
        "DIGITAL_WORLD_COORDINATE_TRAJECTORY_WITH_BOUNDED_ACCESS_CUT_NOT_SEAL_OR_HYGIENE_EVIDENCE",
    )
    _assert_sweep_clear(cartridge_sweep, (service_shell, frame, retention[0], retention[1], retention[2]))

    release_center = latch.centroid_xyz_mm
    release_sweep = ServiceSweep(
        "QUICK-RELEASE-OUTBOARD-WITHDRAWAL",
        latch.part_id,
        (release_center, (release_center[0] + 6.0, release_center[1], release_center[2]), (release_center[0] + 12.0, release_center[1], release_center[2]), (release_center[0] + RELEASE_TRAVEL_MM, release_center[1], release_center[2])),
        latch.solid,
        "UNPOWERED_GEOMETRIC_WITHDRAWAL_ONLY_FORCE_AND_TIME_REQUIRE_PHYSICAL_VALIDATION",
    )
    _assert_sweep_clear(release_sweep, (shell, frame, retention[0], retention[1], retention[2]), ignore_first=True)

    battery = model.battery_reference_envelope
    battery_center = battery.solid.val().Center()
    battery_start = (float(battery_center.x), float(battery_center.y), float(battery_center.z))
    battery_sweep = ServiceSweep(
        "BATTERY-BENCHMARK-REARWARD-REMOVAL",
        "BATTERY-REFERENCE-ENVELOPE",
        (battery_start, (battery_start[0], battery_start[1], -28.0), (battery_start[0], battery_start[1], -40.0), (battery_start[0], battery_start[1], -60.0)),
        battery.solid,
        "PACKAGING_BENCHMARK_TRAJECTORY_ONLY_PRODUCTION_CELL_SWELLING_DRY_BAY_CONNECTOR_AND_HARNESS_UNRESOLVED",
    )
    _assert_sweep_clear(battery_sweep, (shell, frame, retention[1], retention[2]))

    sequence = (
        "1 establish released facial interface and protected-region datums",
        "2 install Manual-A perimeter reaction frame from wearer side",
        "3 install four actuator reaction members and actuator packages",
        "4 install left/right yokes and rear halo/occipital/crown loop",
        "5 install unpowered right-side release latch and verify outboard sweep",
        "6 insert cartridge through bounded lower service opening and close door envelope",
        "7 service battery benchmark rearward only while dry-bay and harness geometry remain blocked",
        "8 add fluid routes, cleanser module, PCB/harness, HMI and WARM/COOL only after owning lanes release 3D geometry",
        "9 close final shell/service surfaces only after every remaining blocker has shape-level collision evidence",
    )

    return MechanicalRealization(
        authority_revision=str(authority.get("project", "authority_revision")),
        baseline_package=baseline,
        realized_parts=(shell, service_shell, service_door, frame, *actuation, *retention),
        shape_checks=tuple(checks),
        service_sweeps=(cartridge_sweep, release_sweep, battery_sweep),
        closed_baseline_blockers=CLOSED_BASELINE_BLOCKERS,
        remaining_blockers=REMAINING_BLOCKERS,
        assembly_sequence=sequence,
    )


# Compatibility alias for the first Prompt-3 branch draft.
build_mechanical_integration = build_mechanical_realization
