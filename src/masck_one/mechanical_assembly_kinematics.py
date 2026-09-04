"""Non-teleporting assembly kinematics for the canonical Manual A candidate.

Assembly motion is evaluated in canonical world coordinates against exact B-rep solids.
Material contact and clearance-fit capture are deliberately different semantics: frame
bridges and actuator reaction shoes require positive final engagement, while pivot pins,
release dogs and tongue/socket capture must remain in aligned voids with zero material
penetration. Digital assembly feasibility is not physical assembly validation.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math

import cadquery as cq

from .authority import Authority, load_authority
from .frame_shell_attachment import build_frame_shell_attachment
from .mechanical_integration import build_mechanical_realization
from .mechanical_structure import (
    PIVOT_BORE_RADIUS_MM,
    PIVOT_PIN_RADIUS_MM,
    build_manual_a_mechanical_structure,
)
from .model import build_model


SCHEMA = "MASCK_ONE_MANUAL_A_ASSEMBLY_KINEMATICS_V2"
KERNEL_ZERO_VOLUME_MM3 = 1e-9


class MechanicalAssemblyKinematicsError(ValueError):
    pass


def _text(value: object, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise MechanicalAssemblyKinematicsError(f"{label} must be exact nonblank text")
    return value


def _intersection(first: cq.Workplane, second: cq.Workplane) -> float:
    value = float(first.val().intersect(second.val()).Volume())
    if not math.isfinite(value) or value < 0.0:
        raise MechanicalAssemblyKinematicsError("intersection volume must be finite and non-negative")
    return 0.0 if value < KERNEL_ZERO_VOLUME_MM3 else value


def _centroid(solid: cq.Workplane) -> tuple[float, float, float]:
    center = solid.val().Center()
    return float(center.x), float(center.y), float(center.z)


def _compound(solids: tuple[cq.Workplane, ...]) -> cq.Workplane:
    if not solids:
        raise MechanicalAssemblyKinematicsError("compound requires at least one solid")
    result = solids[0]
    for solid in solids[1:]:
        result = result.union(solid)
    return result


@dataclass(frozen=True, slots=True)
class AssemblyPart:
    part_id: str
    solid: cq.Workplane
    role: str
    evidence_status: str

    def __post_init__(self) -> None:
        _text(self.part_id, "part_id")
        _text(self.role, "role")
        _text(self.evidence_status, "evidence_status")
        shape = self.solid.val()
        if not shape.isValid() or float(shape.Volume()) <= 0.0:
            raise MechanicalAssemblyKinematicsError(
                f"{self.part_id} must be a valid positive-volume solid"
            )

    @property
    def centroid_xyz_mm(self) -> tuple[float, float, float]:
        return _centroid(self.solid)

    def manifest(self) -> dict[str, object]:
        return {
            "part_id": self.part_id,
            "role": self.role,
            "centroid_xyz_mm": list(self.centroid_xyz_mm),
            "volume_mm3": float(self.solid.val().Volume()),
            "evidence_status": self.evidence_status,
        }


@dataclass(frozen=True, slots=True)
class AssemblyMotion:
    sequence_index: int
    motion_id: str
    moving_part: AssemblyPart
    waypoints_xyz_mm: tuple[tuple[float, float, float], ...]
    obstacle_ids: tuple[str, ...]
    required_final_contact_ids: tuple[str, ...]
    status: str

    def __post_init__(self) -> None:
        if type(self.sequence_index) is not int or self.sequence_index < 1:
            raise MechanicalAssemblyKinematicsError(
                "sequence_index must be an exact positive integer"
            )
        _text(self.motion_id, "motion_id")
        if type(self.moving_part) is not AssemblyPart:
            raise TypeError("moving_part must be exact AssemblyPart")
        if type(self.waypoints_xyz_mm) is not tuple or len(self.waypoints_xyz_mm) < 3:
            raise MechanicalAssemblyKinematicsError(
                "assembly motion requires at least three world-coordinate waypoints"
            )
        for point in self.waypoints_xyz_mm:
            if type(point) is not tuple or len(point) != 3:
                raise MechanicalAssemblyKinematicsError(
                    "assembly waypoint must be an exact XYZ tuple"
                )
            if any(
                type(value) not in (int, float) or not math.isfinite(float(value))
                for value in point
            ):
                raise MechanicalAssemblyKinematicsError(
                    "assembly waypoint coordinates must be finite numeric scalars"
                )
        if any(
            abs(self.waypoints_xyz_mm[-1][i] - self.moving_part.centroid_xyz_mm[i]) > 1e-6
            for i in range(3)
        ):
            raise MechanicalAssemblyKinematicsError(
                "final waypoint must equal the moving part final centroid"
            )
        if type(self.obstacle_ids) is not tuple or len(set(self.obstacle_ids)) != len(
            self.obstacle_ids
        ):
            raise MechanicalAssemblyKinematicsError(
                "obstacle IDs must be a unique exact tuple"
            )
        if type(self.required_final_contact_ids) is not tuple or any(
            contact not in self.obstacle_ids
            for contact in self.required_final_contact_ids
        ):
            raise MechanicalAssemblyKinematicsError(
                "required final contacts must be declared obstacles"
            )
        _text(self.status, "status")

    def sampled_solids(self) -> tuple[cq.Workplane, ...]:
        final = self.moving_part.centroid_xyz_mm
        return tuple(
            self.moving_part.solid.translate(
                (
                    point[0] - final[0],
                    point[1] - final[1],
                    point[2] - final[2],
                )
            )
            for point in self.waypoints_xyz_mm
        )

    def manifest(self) -> dict[str, object]:
        return {
            "sequence_index": self.sequence_index,
            "motion_id": self.motion_id,
            "moving_part_id": self.moving_part.part_id,
            "waypoints_xyz_mm": [list(point) for point in self.waypoints_xyz_mm],
            "obstacle_ids": list(self.obstacle_ids),
            "required_final_contact_ids": list(self.required_final_contact_ids),
            "final_clearance_ids": [
                obstacle
                for obstacle in self.obstacle_ids
                if obstacle not in self.required_final_contact_ids
            ],
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class AssemblyCollisionResult:
    motion_id: str
    obstacle_id: str
    sample_intersection_mm3: tuple[float, ...]
    required_final_contact: bool
    pre_final_clear: bool
    final_state_valid: bool
    status: str

    @property
    def passes(self) -> bool:
        return self.pre_final_clear and self.final_state_valid

    def manifest(self) -> dict[str, object]:
        return {
            "motion_id": self.motion_id,
            "obstacle_id": self.obstacle_id,
            "sample_intersection_mm3": list(self.sample_intersection_mm3),
            "required_final_contact": self.required_final_contact,
            "pre_final_clear": self.pre_final_clear,
            "final_state_valid": self.final_state_valid,
            "passes": self.passes,
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class CaptureInvariant:
    invariant_id: str
    participants: tuple[str, ...]
    value: float | bool
    requirement: str
    passes: bool
    evidence_status: str

    def __post_init__(self) -> None:
        _text(self.invariant_id, "invariant_id")
        if type(self.participants) is not tuple or not self.participants:
            raise MechanicalAssemblyKinematicsError(
                "capture invariant requires participants"
            )
        if type(self.value) not in (int, float, bool):
            raise MechanicalAssemblyKinematicsError(
                "capture invariant value must be numeric or bool"
            )
        if type(self.value) in (int, float) and not math.isfinite(float(self.value)):
            raise MechanicalAssemblyKinematicsError(
                "capture invariant numeric value must be finite"
            )
        _text(self.requirement, "requirement")
        if type(self.passes) is not bool:
            raise MechanicalAssemblyKinematicsError(
                "capture invariant passes must be exact bool"
            )
        _text(self.evidence_status, "evidence_status")

    def manifest(self) -> dict[str, object]:
        return {
            "invariant_id": self.invariant_id,
            "participants": list(self.participants),
            "value": self.value,
            "requirement": self.requirement,
            "passes": self.passes,
            "evidence_status": self.evidence_status,
        }


@dataclass(frozen=True, slots=True)
class MechanicalAssemblyKinematics:
    authority_revision: str
    realization_sha256: str
    source_structure_sha256: str
    parts: tuple[AssemblyPart, ...]
    motions: tuple[AssemblyMotion, ...]
    collision_results: tuple[AssemblyCollisionResult, ...]
    capture_invariants: tuple[CaptureInvariant, ...]
    blocked_downstream_steps: tuple[str, ...]
    evidence_status: str

    def __post_init__(self) -> None:
        _text(self.authority_revision, "authority_revision")
        for label, value in (
            ("realization_sha256", self.realization_sha256),
            ("source_structure_sha256", self.source_structure_sha256),
        ):
            _text(value, label)
            if len(value) != 64:
                raise MechanicalAssemblyKinematicsError(
                    f"{label} must be a SHA-256 digest"
                )
        if tuple(motion.sequence_index for motion in self.motions) != tuple(
            range(1, len(self.motions) + 1)
        ):
            raise MechanicalAssemblyKinematicsError(
                "assembly motions must have contiguous sequence indices"
            )
        if type(self.collision_results) is not tuple or not self.collision_results:
            raise MechanicalAssemblyKinematicsError(
                "assembly collision results are required"
            )
        if type(self.capture_invariants) is not tuple or not self.capture_invariants:
            raise MechanicalAssemblyKinematicsError(
                "capture invariants are required"
            )
        if type(self.blocked_downstream_steps) is not tuple or not self.blocked_downstream_steps:
            raise MechanicalAssemblyKinematicsError(
                "downstream blockers must remain explicit"
            )
        _text(self.evidence_status, "evidence_status")

    @property
    def failures(self) -> tuple[AssemblyCollisionResult, ...]:
        return tuple(result for result in self.collision_results if not result.passes)

    @property
    def capture_failures(self) -> tuple[CaptureInvariant, ...]:
        return tuple(item for item in self.capture_invariants if not item.passes)

    @property
    def kinematics_sha256(self) -> str:
        raw = json.dumps(
            self.manifest(include_sha=False),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "authority_revision": self.authority_revision,
            "realization_sha256": self.realization_sha256,
            "source_structure_sha256": self.source_structure_sha256,
            "parts": [part.manifest() for part in self.parts],
            "motions": [motion.manifest() for motion in self.motions],
            "collision_results": [result.manifest() for result in self.collision_results],
            "failures": [result.manifest() for result in self.failures],
            "capture_invariants": [item.manifest() for item in self.capture_invariants],
            "capture_failures": [item.manifest() for item in self.capture_failures],
            "blocked_downstream_steps": list(self.blocked_downstream_steps),
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            payload["kinematics_sha256"] = self.kinematics_sha256
        return payload


def _part(part_id: str, solid: cq.Workplane, role: str, evidence: str) -> AssemblyPart:
    return AssemblyPart(part_id, solid, role, evidence)


def _motion(
    index: int,
    motion_id: str,
    part: AssemblyPart,
    start_offset_xyz_mm: tuple[float, float, float],
    intermediate_offsets_xyz_mm: tuple[tuple[float, float, float], ...],
    obstacle_ids: tuple[str, ...],
    required_final_contact_ids: tuple[str, ...],
    status: str,
) -> AssemblyMotion:
    final = part.centroid_xyz_mm
    offsets = (start_offset_xyz_mm, *intermediate_offsets_xyz_mm, (0.0, 0.0, 0.0))
    waypoints = tuple(
        (final[0] + offset[0], final[1] + offset[1], final[2] + offset[2])
        for offset in offsets
    )
    return AssemblyMotion(
        sequence_index=index,
        motion_id=motion_id,
        moving_part=part,
        waypoints_xyz_mm=waypoints,
        obstacle_ids=obstacle_ids,
        required_final_contact_ids=required_final_contact_ids,
        status=status,
    )


def _collision_results(
    motions: tuple[AssemblyMotion, ...],
    part_map: dict[str, AssemblyPart],
) -> tuple[AssemblyCollisionResult, ...]:
    results: list[AssemblyCollisionResult] = []
    for motion in motions:
        samples = motion.sampled_solids()
        for obstacle_id in motion.obstacle_ids:
            obstacle = part_map[obstacle_id]
            volumes = tuple(_intersection(sample, obstacle.solid) for sample in samples)
            pre_final_clear = all(value == 0.0 for value in volumes[:-1])
            required = obstacle_id in motion.required_final_contact_ids
            final_state_valid = volumes[-1] > 0.0 if required else volumes[-1] == 0.0
            results.append(
                AssemblyCollisionResult(
                    motion_id=motion.motion_id,
                    obstacle_id=obstacle_id,
                    sample_intersection_mm3=volumes,
                    required_final_contact=required,
                    pre_final_clear=pre_final_clear,
                    final_state_valid=final_state_valid,
                    status=(
                        "PASS_DIGITAL_NONTELEPORTING_ASSEMBLY_MOTION"
                        if pre_final_clear and final_state_valid
                        else "FAIL_DIGITAL_ASSEMBLY_COLLISION_OR_FINAL_STATE_RULE"
                    ),
                )
            )
    return tuple(results)


def build_mechanical_assembly_kinematics(
    authority: Authority | None = None,
) -> MechanicalAssemblyKinematics:
    authority = authority or load_authority()
    model = build_model(authority)
    structure = build_manual_a_mechanical_structure(authority, model)
    realization = build_mechanical_realization(authority)
    attachment = build_frame_shell_attachment(authority)
    if realization.source_structure_sha256 != structure.package_sha256:
        raise MechanicalAssemblyKinematicsError(
            "integration projection is stale for canonical mechanical structure"
        )

    release = structure.release
    shell = _part(
        "LIVE-MAIN-RIGID-SHELL",
        model.shell.solid,
        "released shell boundary",
        model.shell.notes or model.shell.status,
    )
    frame_assembly = _part(
        "FRAME-ASSEMBLY-WITH-BRIDGES-AND-RETENTION-FEATURES",
        _compound(
            (
                structure.frame.solid,
                release.left_frame_clevis.solid,
                release.right_frame_socket.solid,
                release.guard.solid,
                *(bridge.solid for bridge in attachment.bridges),
            )
        ),
        "perimeter frame with frame-side retention features, guard and three shell bridges",
        "DIGITAL_PREASSEMBLY_CANDIDATE_MATERIAL_FASTENER_ADHESIVE_STIFFNESS_AND_FATIGUE_UNVALIDATED",
    )
    modules = tuple(
        _part(
            f"ACTUATOR-REACTION-MODULE-{letter}",
            _compound((zone.envelope.solid, zone.mount_collar.solid, zone.reaction_shoe.solid)),
            f"canonical actuator zone {letter} plus removable collar and reaction shoe",
            "DIGITAL_PREASSEMBLY_CANDIDATE_NOT_FASTENER_TOLERANCE_FORCE_FATIGUE_OR_PHYSICAL_EVIDENCE",
        )
        for letter, zone in zip("ABCD", structure.actuator_zones)
    )
    halo_assembly = _part(
        "HALO-ASSEMBLY-WITH-PIVOT-LUG-AND-RELEASE-TONGUE",
        _compound(
            (
                structure.halo.solid,
                release.left_rear_lug.solid,
                release.right_rear_tongue.solid,
            )
        ),
        "rear halo with integral left pivot lug and right release tongue",
        "DIGITAL_PREASSEMBLY_CANDIDATE_FIT_COMFORT_PRELOAD_MATERIAL_AND_DURABILITY_UNVALIDATED",
    )
    pivot_pin = _part(
        "LEFT-CAPTIVE-PIVOT-PIN",
        release.left_pivot_pin.solid,
        "captive pivot pin inserted through aligned clevis/lug bores",
        release.left_pivot_pin.evidence_status,
    )
    dog = _part(
        "QUICK-RELEASE-DOG-AND-WET-GRIP",
        release.dog_and_grip.solid,
        "unpowered transverse release dog and wet-finger grip",
        release.dog_and_grip.evidence_status,
    )

    parts = (shell, frame_assembly, *modules, halo_assembly, pivot_pin, dog)
    part_map = {part.part_id: part for part in parts}
    if len(part_map) != len(parts):
        raise MechanicalAssemblyKinematicsError("assembly part IDs must be unique")

    installed: list[str] = [shell.part_id]
    motions: list[AssemblyMotion] = []

    motions.append(
        _motion(
            1,
            "ASSEMBLE-FRAME-BRIDGE-PACKAGE-FROM-WEARER-SIDE",
            frame_assembly,
            (0.0, 0.0, -30.0),
            ((0.0, 0.0, -18.0), (0.0, 0.0, -8.0)),
            tuple(installed),
            (shell.part_id,),
            "DIGITAL_REAR_INSERTION_WITH_FINAL_THREE_BRIDGE_SHELL_ENGAGEMENT_REQUIRED",
        )
    )
    installed.append(frame_assembly.part_id)

    for index, module in enumerate(modules, start=2):
        motions.append(
            _motion(
                index,
                f"ASSEMBLE-{module.part_id}-FROM-WEARER-SIDE",
                module,
                (0.0, 0.0, -28.0),
                ((0.0, 0.0, -16.0), (0.0, 0.0, -7.0)),
                tuple(installed),
                (frame_assembly.part_id,),
                "DIGITAL_ACTUATOR_MODULE_INSERTION_WITH_FINAL_REACTION_SHOE_FRAME_ENGAGEMENT_REQUIRED",
            )
        )
        installed.append(module.part_id)

    motions.append(
        _motion(
            6,
            "ASSEMBLE-HALO-CAPTURE-FEATURES-FROM-POSTERIOR",
            halo_assembly,
            (0.0, 0.0, -30.0),
            ((0.0, 0.0, -18.0), (0.0, 0.0, -8.0)),
            tuple(installed),
            (),
            "DIGITAL_POSTERIOR_INSERTION_INTO_LEFT_CLEVIS_AND_RIGHT_SOCKET_CLEARANCE_CHANNELS;CAPTURE_VERIFIED_BY_INVARIANTS_NOT_MATERIAL_OVERLAP",
        )
    )
    installed.append(halo_assembly.part_id)

    motions.append(
        _motion(
            7,
            "ASSEMBLE-LEFT-CAPTIVE-PIVOT-PIN-THROUGH-ALIGNED-BORES",
            pivot_pin,
            (0.0, 24.0, 0.0),
            ((0.0, 14.0, 0.0), (0.0, 7.0, 0.0)),
            tuple(installed),
            (),
            "DIGITAL_PIN_INSERTION_THROUGH_CLEARANCE_BORES;PIN_RETENTION_DETAIL_DFM_PENDING",
        )
    )
    installed.append(pivot_pin.part_id)

    motions.append(
        _motion(
            8,
            "ASSEMBLE-QUICK-RELEASE-DOG-INBOARD-THROUGH-ALIGNED-BORES",
            dog,
            (release.dog_travel_mm, 0.0, 0.0),
            ((10.5, 0.0, 0.0), (7.0, 0.0, 0.0), (3.5, 0.0, 0.0)),
            tuple(installed),
            (),
            "DIGITAL_REVERSE_OF_UNPOWERED_RELEASE;CAPTURE_IS_CLEARANCE_BORE_ALIGNMENT_NOT_SOLID_OVERLAP",
        )
    )

    guard_socket_overlap = _intersection(release.guard.solid, release.right_frame_socket.solid)
    capture_invariants = (
        CaptureInvariant(
            "FRAME-SHELL-BRIDGES-HAVE-POSITIVE-GEOMETRIC-ENGAGEMENT",
            tuple(bridge.bridge_id for bridge in attachment.bridges),
            min(min(bridge.frame_intersection_mm3, bridge.shell_intersection_mm3) for bridge in attachment.bridges),
            ">0 mm3 intersection to frame and shell for every bridge",
            all(bridge.frame_intersection_mm3 > 0.0 and bridge.shell_intersection_mm3 > 0.0 for bridge in attachment.bridges),
            "GEOMETRIC_ATTACHMENT_ONLY_NOT_PHYSICAL_LOAD_CAPACITY",
        ),
        CaptureInvariant(
            "LEFT-PIVOT-RADIAL-CLEARANCE",
            ("RETENTION_LEFT_CAPTIVE_PIVOT_PIN", "RETENTION_LEFT_FRAME_CLEVIS", "RETENTION_LEFT_REAR_PIVOT_LUG"),
            PIVOT_BORE_RADIUS_MM - PIVOT_PIN_RADIUS_MM,
            ">0 mm radial clearance",
            PIVOT_BORE_RADIUS_MM > PIVOT_PIN_RADIUS_MM,
            "DIGITAL_CLEARANCE_ONLY_PIN_RETENTION_TOLERANCE_WEAR_AND_LOAD_UNVALIDATED",
        ),
        CaptureInvariant(
            "RIGHT-DOG-RADIAL-CLEARANCE",
            ("QUICK_RELEASE_DOG_AND_WET_GRIP", "RETENTION_RIGHT_FRAME_SOCKET", "RETENTION_RIGHT_REAR_TONGUE"),
            release.dog_radial_clearance_mm,
            ">0 mm radial clearance",
            release.dog_radial_clearance_mm > 0.0,
            "DIGITAL_CLEARANCE_ONLY_FORCE_WEAR_CONTAMINATION_AND_TOLERANCE_UNVALIDATED",
        ),
        CaptureInvariant(
            "RIGHT-TONGUE-CHANNEL-MIN-XY-CLEARANCE",
            ("RETENTION_RIGHT_FRAME_SOCKET", "RETENTION_RIGHT_REAR_TONGUE"),
            min(release.tongue_clearance_xy_mm),
            ">0 mm diametral/planar channel clearance",
            min(release.tongue_clearance_xy_mm) > 0.0,
            "DIGITAL_CLEARANCE_ONLY_WEAR_DEBRIS_AND_PROCESS_CAPABILITY_UNVALIDATED",
        ),
        CaptureInvariant(
            "DOG-FULL-WITHDRAWAL-CLEARS-RIGHT-TONGUE",
            ("QUICK_RELEASE_DOG_AND_WET_GRIP", "RETENTION_RIGHT_REAR_TONGUE"),
            release.dog_final_clears_tongue,
            "true after full authored dog travel",
            release.dog_final_clears_tongue,
            "DIGITAL_WITHDRAWAL_GEOMETRY_ONLY_RELEASE_FORCE_AND_TIME_REMAIN_PHYSICAL_GATES",
        ),
        CaptureInvariant(
            "ACCIDENTAL-ACTUATION-GUARD-ATTACHES-TO-RIGHT-SOCKET",
            ("QUICK_RELEASE_ACCIDENTAL_ACTUATION_GUARD", "RETENTION_RIGHT_FRAME_SOCKET"),
            guard_socket_overlap,
            ">0 mm3 geometric attachment",
            guard_socket_overlap > 0.0,
            "GEOMETRIC_ATTACHMENT_ONLY_GUARD_LOAD_STRENGTH_AND_ERGONOMICS_UNVALIDATED",
        ),
    )

    motion_tuple = tuple(motions)
    results = _collision_results(motion_tuple, part_map)
    return MechanicalAssemblyKinematics(
        authority_revision=str(authority.get("project", "authority_revision")),
        realization_sha256=realization.realization_sha256,
        source_structure_sha256=structure.package_sha256,
        parts=parts,
        motions=motion_tuple,
        collision_results=results,
        capture_invariants=capture_invariants,
        blocked_downstream_steps=(
            "FINAL_FASTENER_ADHESIVE_OR_WELD_SELECTION",
            "FRAME_RETENTION_AND_RELEASE_TOLERANCE_STACK",
            "PIN_RETENTION_AND_RESET_SERVICE_DETAIL",
            "CARTRIDGE_DOOR_SEAL_LATCH_ASSEMBLY_AFTER_MANUAL_B_INTERFACE_RELEASE",
            "FLUID_TUBE_PUMP_MANIFOLD_INSTALLATION_AFTER_CELL4_REALIZED_ROUTE_RELEASE",
            "PCB_HARNESS_HMI_WARM_COOL_INSTALLATION_AFTER_MANUAL_B_RELEASE",
            "BATTERY_SERVICE_REQUIRES_RETENTION_REMOVED_UNTIL_DRY_BAY_AND_HARNESS_GEOMETRY_RELEASE",
            "FINAL_EXTERIOR_CLOSURE_AFTER_ALL_SERVICE_SWEEPS_CLEAR",
        ),
        evidence_status=(
            "EXACT_BREP_SAMPLED_CANONICAL_MANUAL_A_ASSEMBLY_KINEMATICS_WITH_CLEARANCE_CAPTURE_INVARIANTS_"
            "NOT_FASTENER_TOLERANCE_ERGONOMIC_OR_PHYSICAL_ASSEMBLY_VALIDATION"
        ),
    )
