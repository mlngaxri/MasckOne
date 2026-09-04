from __future__ import annotations

"""Whole-product projection of the canonical Manual-A mechanical structure.

This module is an integration adapter, not a second mechanical CAD definition. Frame,
actuator, mount, retention and quick-release solids are sourced exclusively from
:mod:`mechanical_structure`. The adapter adds whole-product package references and
bounded service states while keeping other-lane geometry unresolved. Digital CAD is
not physical validation evidence.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math

import cadquery as cq

from .authority import Authority, load_authority
from .mechanical_structure import (
    ACTUATOR_ZONE_CANDIDATES,
    RELEASE_DOG_TRAVEL_MM,
    ManualAMechanicalStructure,
    MechanicalPart,
    build_manual_a_mechanical_structure,
)
from .model import MasckOneModel, build_model
from .spatial import Point3
from .whole_product_package import WholeProductPackage, build_whole_product_package


SCHEMA = "MASCK_ONE_MECHANICAL_REALIZATION_V3"
CANDIDATE = "MANUAL_A_DIGITAL_CAD_CANDIDATE_NOT_AUTHORITY_OR_PHYSICAL_EVIDENCE"
STANDARD_GRAVITY_M_S2 = 9.80665

# Compatibility identities only. Origins and signs are projected from the canonical
# mechanical-structure source; no duplicate actuator coordinates are authored here.
ACTUATOR_PLACEMENTS = tuple(
    (f"ACTUATOR-ZONE-{letter}", origin, sign)
    for letter, (_, origin, sign) in zip("ABCD", ACTUATOR_ZONE_CANDIDATES)
)

# Service-state geometry is an integration handoff, not exterior ownership.
LOWER_SERVICE_CUT_XYZ_MM = (82.0, 45.0, 28.0)
LOWER_SERVICE_CUT_CENTER = (0.0, -102.0, 7.0)

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
        raise MechanicalIntegrationError(
            f"{label} must be finite" + (" and positive" if positive else "")
        )
    return 0.0 if result == 0.0 else result


def _text(value: object, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise MechanicalIntegrationError(f"{label} must be exact nonblank text")
    return value


def _box(x: float, y: float, z: float, center: Point3) -> cq.Workplane:
    for label, value in (("x", x), ("y", y), ("z", z)):
        _finite(value, f"box {label}", positive=True)
    return (
        cq.Workplane("XY")
        .box(x, y, z, centered=(True, True, True))
        .translate(center.as_tuple())
    )


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
        for label, value in (
            ("part_id", self.part_id),
            ("role", self.role),
            ("geometry_status", self.geometry_status),
            ("evidence_status", self.evidence_status),
        ):
            _text(value, label)
        shape = self.solid.val()
        if not shape.isValid() or float(shape.Volume()) <= 0.0:
            raise MechanicalIntegrationError(
                f"{self.part_id} must be a valid positive-volume solid"
            )

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
    state: str
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
            "state": self.state,
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
        for point in self.waypoints_xyz_mm:
            if type(point) is not tuple or len(point) != 3:
                raise MechanicalIntegrationError("service sweep waypoint must be exact XYZ tuple")
            for value in point:
                _finite(value, "service sweep coordinate")

    def sampled_solids(self) -> tuple[cq.Workplane, ...]:
        origin = self.waypoints_xyz_mm[0]
        return tuple(
            self.initial_solid.translate(
                tuple(point[index] - origin[index] for index in range(3))
            )
            for point in self.waypoints_xyz_mm
        )

    def collision_volumes(
        self, obstacles: tuple[RealizedPart, ...]
    ) -> dict[str, tuple[float, ...]]:
        return {
            obstacle.part_id: tuple(
                intersection_volume_mm3(sample, obstacle.solid)
                for sample in self.sampled_solids()
            )
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
    source_structure_sha256: str
    realized_parts: tuple[RealizedPart, ...]
    shape_checks: tuple[ShapeCheck, ...]
    service_sweeps: tuple[ServiceSweep, ...]
    closed_baseline_blockers: tuple[str, ...]
    remaining_blockers: tuple[str, ...]
    unresolved_physical_gates: tuple[str, ...]
    assembly_sequence: tuple[str, ...]

    def __post_init__(self) -> None:
        if len(self.source_structure_sha256) != 64:
            raise MechanicalIntegrationError("source structure digest must be SHA-256")
        if len({part.part_id for part in self.realized_parts}) != len(self.realized_parts):
            raise MechanicalIntegrationError("realized part IDs must be unique")
        if self.closed_baseline_blockers != CLOSED_BASELINE_BLOCKERS:
            raise MechanicalIntegrationError("closed geometry-class set changed unexpectedly")
        if self.remaining_blockers != REMAINING_BLOCKERS:
            raise MechanicalIntegrationError("remaining blocker set changed unexpectedly")
        if not self.unresolved_physical_gates:
            raise MechanicalIntegrationError("physical validation gates must remain explicit")
        if any(not check.passes for check in self.shape_checks):
            raise MechanicalIntegrationError("canonical required-clear collision remains")

    @property
    def realization_sha256(self) -> str:
        raw = json.dumps(
            self.manifest(include_sha=False),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return sha256(raw).hexdigest()

    def mass_cg_manifest(self, authority: Authority) -> dict[str, object]:
        baseline = self.baseline_package.mass_cg
        return {
            "known_mass_g": baseline.known_mass_g,
            "known_cg_mm": None if baseline.known_cg_mm is None else list(baseline.known_cg_mm),
            "known_pitch_moment_Nm": baseline.known_pitch_moment_Nm,
            "new_realized_parts_with_unresolved_mass": [
                part.part_id for part in self.realized_parts
            ],
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
            "comparison_semantics": "BASELINE_KNOWN_SUBSET_CANNOT_ESTABLISH_WHOLE_PRODUCT_PASS;SEE_MECHANICAL_MASS_CG_LEDGER_FOR_TRACEABLE_ADDITIONAL_BENCHMARKS",
        }

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "authority_revision": self.authority_revision,
            "baseline_package_sha256": self.baseline_package.package_sha256,
            "source_structure_sha256": self.source_structure_sha256,
            "realized_parts": [part.manifest() for part in self.realized_parts],
            "shape_checks": [check.manifest() for check in self.shape_checks],
            "service_sweeps": [sweep.manifest() for sweep in self.service_sweeps],
            "closed_baseline_blockers": list(self.closed_baseline_blockers),
            "closed_baseline_blocker_semantics": "OWNED_GEOMETRY_CLASS_PRESENT_ONLY_NOT_PHYSICAL_CAPACITY_OR_VALIDATION",
            "remaining_blockers": list(self.remaining_blockers),
            "unresolved_physical_gates": list(self.unresolved_physical_gates),
            "assembly_sequence": list(self.assembly_sequence),
            "evidence_status": "DIGITAL_MECHANICAL_INTEGRATION_PROJECTION_NOT_PHYSICAL_VALIDATION",
        }
        if include_sha:
            payload["realization_sha256"] = self.realization_sha256
        return payload


def _project_part(alias: str, source: MechanicalPart, role: str | None = None) -> RealizedPart:
    return RealizedPart(
        alias,
        source.solid,
        role or source.role,
        source.geometry_status,
        source.evidence_status,
    )


def _compound_parts(alias: str, sources: tuple[MechanicalPart, ...], role: str) -> RealizedPart:
    if not sources:
        raise MechanicalIntegrationError("compound projection requires source parts")
    solid = sources[0].solid
    for source in sources[1:]:
        solid = solid.union(source.solid)
    return RealizedPart(
        alias,
        solid,
        role,
        "PROJECTED_FROM_CANONICAL_MANUAL_A_STRUCTURE",
        "ASSEMBLY_COMPOUND_FOR_PACKAGE_ACCOUNTING;SOURCE_PART_CLEARANCES_AND_CAPTURE_SEMANTICS_REMAIN_CANONICAL",
    )


def _project_shape_checks(structure: ManualAMechanicalStructure) -> tuple[ShapeCheck, ...]:
    return tuple(
        ShapeCheck(
            item.check_id,
            item.moving_id,
            item.obstacle_id,
            item.state,
            item.intersection_volume_mm3,
            "PASS_DIGITAL_ONLY" if item.passes else "FAIL_INTERFERENCE",
        )
        for item in structure.clearance_results
    )


def _assert_sweep_clear(sweep: ServiceSweep, obstacles: tuple[RealizedPart, ...]) -> None:
    for obstacle_id, volumes in sweep.collision_volumes(obstacles).items():
        if any(value > 0.0 for value in volumes):
            raise MechanicalIntegrationError(
                f"{sweep.sweep_id} collides with {obstacle_id}: {volumes}"
            )


def build_mechanical_realization(authority: Authority | None = None) -> MechanicalRealization:
    authority = authority or load_authority()
    model: MasckOneModel = build_model(authority)
    baseline = build_whole_product_package(model)
    structure = build_manual_a_mechanical_structure(authority, model)
    structure.validate_current_sources(authority, model)

    shell = RealizedPart(
        "LIVE-MAIN-RIGID-SHELL",
        model.shell.solid,
        "released live-main shell used as integration boundary",
        model.shell.status,
        model.shell.notes,
    )
    frame = _project_part("FRAME-PERIMETER-REACTION", structure.frame)

    actuation: list[RealizedPart] = []
    for letter, zone in zip("ABCD", structure.actuator_zones):
        actuation.append(_project_part(f"ACTUATOR-ZONE-{letter}", zone.envelope))
        actuation.append(
            _compound_parts(
                f"REACTION-ACTUATOR-ZONE-{letter}",
                (zone.mount_collar, zone.reaction_shoe),
                "canonical mount collar and reaction shoe projected as one package-accounting assembly",
            )
        )

    release = structure.release
    halo = _project_part("RETENTION-HALO-OCCIPITAL-CROWN", structure.halo)
    left = _compound_parts(
        "RETENTION-YOKE-LEFT",
        (release.left_frame_clevis, release.left_rear_lug, release.left_pivot_pin),
        "captive left frame-to-halo pivot assembly",
    )
    right = _compound_parts(
        "RETENTION-YOKE-RIGHT-FIXED",
        (release.right_frame_socket, release.right_rear_tongue),
        "separable right frame socket and halo tongue assembly",
    )
    latch = _project_part("QUICK-RELEASE-LATCH-MOVING", release.dog_and_grip)
    guard = _project_part("QUICK-RELEASE-GUARD", release.guard)

    service_cut = _box(*LOWER_SERVICE_CUT_XYZ_MM, Point3(*LOWER_SERVICE_CUT_CENTER))
    service_shell = RealizedPart(
        "SERVICE-STATE-SHELL",
        shell.solid.cut(service_cut),
        "live-main shell with bounded lower service access removed for trajectory proof",
        CANDIDATE,
        "MECHANICAL_ACCESS_HANDOFF_REQUIRES_MANUAL_B_SURFACE_SEAL_LATCH_AND_CMF_CONVERGENCE",
    )
    service_door = RealizedPart(
        "LOWER-SERVICE-DOOR-ENVELOPE",
        _box(82.0, 3.0, 28.0, Point3(0.0, -102.0, 7.0)),
        "bounded lower access door envelope",
        CANDIDATE,
        "DOOR_ENVELOPE_ONLY_SEAL_LATCH_TOLERANCE_INGRESS_AND_CMF_UNRESOLVED",
    )

    cartridge = model.waste_cartridge_envelope
    cartridge_center = cartridge.solid.val().Center()
    cartridge_start = (
        float(cartridge_center.x),
        float(cartridge_center.y),
        float(cartridge_center.z),
    )
    cartridge_sweep = ServiceSweep(
        "CARTRIDGE-DOWNWARD-REMOVAL",
        "WASTE-CARTRIDGE-ENVELOPE",
        (
            cartridge_start,
            (cartridge_start[0], -100.0, cartridge_start[2]),
            (cartridge_start[0], -122.0, cartridge_start[2]),
            (cartridge_start[0], -145.0, cartridge_start[2]),
        ),
        cartridge.solid,
        "DIGITAL_WORLD_COORDINATE_TRAJECTORY_WITH_BOUNDED_ACCESS_CUT_NOT_SEAL_OR_HYGIENE_EVIDENCE",
    )
    _assert_sweep_clear(cartridge_sweep, (service_shell, frame, halo, left, right, guard))

    release_center = latch.centroid_xyz_mm
    release_sweep = ServiceSweep(
        "QUICK-RELEASE-OUTBOARD-WITHDRAWAL",
        latch.part_id,
        tuple(
            (
                release_center[0] + offset,
                release_center[1],
                release_center[2],
            )
            for offset in (0.0, 3.5, 7.0, 10.5, RELEASE_DOG_TRAVEL_MM)
        ),
        latch.solid,
        "UNPOWERED_CANONICAL_DOG_WITHDRAWAL_GEOMETRY_ONLY_FORCE_AND_TIME_REQUIRE_PHYSICAL_VALIDATION",
    )
    _assert_sweep_clear(release_sweep, (shell, frame, halo, left, right, guard))

    battery = model.battery_reference_envelope
    battery_center = battery.solid.val().Center()
    battery_start = (
        float(battery_center.x),
        float(battery_center.y),
        float(battery_center.z),
    )
    battery_sweep = ServiceSweep(
        "BATTERY-BENCHMARK-REARWARD-REMOVAL",
        "BATTERY-REFERENCE-ENVELOPE",
        (
            battery_start,
            (battery_start[0], battery_start[1], -28.0),
            (battery_start[0], battery_start[1], -40.0),
            (battery_start[0], battery_start[1], -60.0),
        ),
        battery.solid,
        "PACKAGING_BENCHMARK_TRAJECTORY_REQUIRES_RETENTION_REMOVED;PRODUCTION_CELL_SWELLING_DRY_BAY_CONNECTOR_AND_HARNESS_UNRESOLVED",
    )
    _assert_sweep_clear(battery_sweep, (shell, frame))

    sequence = (
        "1 establish released facial interface and protected-region datums",
        "2 install canonical Manual-A perimeter reaction frame and frame-to-shell attachments",
        "3 install four canonical reaction shoes, removable collars and actuator packages",
        "4 install rear halo, left captive pivot, right tongue/socket and unpowered dog/guard",
        "5 verify full dog withdrawal before any wearer-removal claim",
        "6 insert cartridge through bounded lower service opening and close door envelope",
        "7 remove retention assembly before rearward battery benchmark service trajectory",
        "8 add fluid routes, cleanser module, PCB/harness, HMI and WARM/COOL only after owning lanes release 3D geometry",
        "9 close final shell/service surfaces only after every remaining blocker has shape-level collision evidence",
    )

    realized_parts = (
        shell,
        service_shell,
        service_door,
        frame,
        *actuation,
        halo,
        left,
        right,
        latch,
        guard,
    )
    return MechanicalRealization(
        authority_revision=str(authority.get("project", "authority_revision")),
        baseline_package=baseline,
        source_structure_sha256=structure.package_sha256,
        realized_parts=realized_parts,
        shape_checks=_project_shape_checks(structure),
        service_sweeps=(cartridge_sweep, release_sweep, battery_sweep),
        closed_baseline_blockers=CLOSED_BASELINE_BLOCKERS,
        remaining_blockers=REMAINING_BLOCKERS,
        unresolved_physical_gates=structure.unresolved_physical_gates,
        assembly_sequence=sequence,
    )


# Compatibility alias retained for downstream Prompt-3 modules.
build_mechanical_integration = build_mechanical_realization
