"""Non-teleporting assembly kinematics for the Manual A mechanical candidate.

The sequence is evaluated in canonical world coordinates against exact B-rep solids.
Intentional final mating contact is declared per motion; all other pre-final and final
intersections remain failures. This is digital assembly feasibility evidence only.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math

import cadquery as cq

from .authority import Authority, load_authority
from .mechanical_integration import MechanicalRealization, RealizedPart, build_mechanical_realization


SCHEMA = "MASCK_ONE_MANUAL_A_ASSEMBLY_KINEMATICS_V1"
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
            raise MechanicalAssemblyKinematicsError(f"{self.part_id} must be a valid positive-volume solid")

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
            raise MechanicalAssemblyKinematicsError("sequence_index must be an exact positive integer")
        _text(self.motion_id, "motion_id")
        if type(self.moving_part) is not AssemblyPart:
            raise TypeError("moving_part must be exact AssemblyPart")
        if type(self.waypoints_xyz_mm) is not tuple or len(self.waypoints_xyz_mm) < 3:
            raise MechanicalAssemblyKinematicsError("assembly motion requires at least three world-coordinate waypoints")
        for point in self.waypoints_xyz_mm:
            if type(point) is not tuple or len(point) != 3:
                raise MechanicalAssemblyKinematicsError("assembly waypoint must be an exact XYZ tuple")
            if any(type(value) not in (int, float) or not math.isfinite(float(value)) for value in point):
                raise MechanicalAssemblyKinematicsError("assembly waypoint coordinates must be finite numeric scalars")
        if any(abs(self.waypoints_xyz_mm[-1][i] - self.moving_part.centroid_xyz_mm[i]) > 1e-6 for i in range(3)):
            raise MechanicalAssemblyKinematicsError("final waypoint must equal the moving part final centroid")
        if type(self.obstacle_ids) is not tuple or len(set(self.obstacle_ids)) != len(self.obstacle_ids):
            raise MechanicalAssemblyKinematicsError("obstacle IDs must be a unique exact tuple")
        if type(self.required_final_contact_ids) is not tuple or any(
            contact not in self.obstacle_ids for contact in self.required_final_contact_ids
        ):
            raise MechanicalAssemblyKinematicsError("required final contacts must be declared obstacles")
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
class MechanicalAssemblyKinematics:
    authority_revision: str
    realization_sha256: str
    parts: tuple[AssemblyPart, ...]
    motions: tuple[AssemblyMotion, ...]
    collision_results: tuple[AssemblyCollisionResult, ...]
    blocked_downstream_steps: tuple[str, ...]
    evidence_status: str

    def __post_init__(self) -> None:
        _text(self.authority_revision, "authority_revision")
        _text(self.realization_sha256, "realization_sha256")
        if len(self.realization_sha256) != 64:
            raise MechanicalAssemblyKinematicsError("realization_sha256 must be a SHA-256 digest")
        if tuple(motion.sequence_index for motion in self.motions) != tuple(range(1, len(self.motions) + 1)):
            raise MechanicalAssemblyKinematicsError("assembly motions must have contiguous sequence indices")
        if type(self.collision_results) is not tuple or not self.collision_results:
            raise MechanicalAssemblyKinematicsError("assembly collision results are required")
        if type(self.blocked_downstream_steps) is not tuple or not self.blocked_downstream_steps:
            raise MechanicalAssemblyKinematicsError("downstream blockers must remain explicit")
        _text(self.evidence_status, "evidence_status")

    @property
    def failures(self) -> tuple[AssemblyCollisionResult, ...]:
        return tuple(result for result in self.collision_results if not result.passes)

    @property
    def kinematics_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "authority_revision": self.authority_revision,
            "realization_sha256": self.realization_sha256,
            "parts": [part.manifest() for part in self.parts],
            "motions": [motion.manifest() for motion in self.motions],
            "collision_results": [result.manifest() for result in self.collision_results],
            "failures": [result.manifest() for result in self.failures],
            "blocked_downstream_steps": list(self.blocked_downstream_steps),
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            payload["kinematics_sha256"] = self.kinematics_sha256
        return payload


def _part(realization: MechanicalRealization, part_id: str) -> RealizedPart:
    matches = tuple(part for part in realization.realized_parts if part.part_id == part_id)
    if len(matches) != 1:
        raise MechanicalAssemblyKinematicsError(f"expected exactly one realized part {part_id}")
    return matches[0]


def _assembly_part(realization: MechanicalRealization, part_id: str, role: str) -> AssemblyPart:
    source = _part(realization, part_id)
    return AssemblyPart(part_id, source.solid, role, source.evidence_status)


def _actuator_module(realization: MechanicalRealization, zone: str) -> AssemblyPart:
    actuator = _part(realization, f"ACTUATOR-ZONE-{zone}")
    reaction = _part(realization, f"REACTION-ACTUATOR-ZONE-{zone}")
    return AssemblyPart(
        f"ACTUATOR-REACTION-MODULE-{zone}",
        actuator.solid.union(reaction.solid),
        f"preassembled actuator zone {zone} plus structural reaction member",
        "DIGITAL_PREASSEMBLY_CANDIDATE_NOT_FASTENER_ADHESIVE_TOLERANCE_OR_PHYSICAL_LOAD_EVIDENCE",
    )


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
                        else "FAIL_DIGITAL_ASSEMBLY_COLLISION_OR_MISSING_FINAL_ENGAGEMENT"
                    ),
                )
            )
    return tuple(results)


def build_mechanical_assembly_kinematics(
    authority: Authority | None = None,
) -> MechanicalAssemblyKinematics:
    authority = authority or load_authority()
    realization = build_mechanical_realization(authority)

    shell = _assembly_part(realization, "LIVE-MAIN-RIGID-SHELL", "released shell boundary")
    frame = _assembly_part(realization, "FRAME-PERIMETER-REACTION", "Manual A perimeter reaction frame")
    modules = tuple(_actuator_module(realization, zone) for zone in "ABCD")
    left_yoke = _assembly_part(realization, "RETENTION-YOKE-LEFT", "left retention yoke")
    right_yoke = _assembly_part(realization, "RETENTION-YOKE-RIGHT-FIXED", "right fixed retention yoke")
    halo = _assembly_part(realization, "RETENTION-HALO-OCCIPITAL-CROWN", "rear halo/occipital/crown loop")
    latch = _assembly_part(realization, "QUICK-RELEASE-LATCH-MOVING", "unpowered quick-release latch")

    parts = (shell, frame, *modules, left_yoke, right_yoke, halo, latch)
    part_map = {part.part_id: part for part in parts}
    if len(part_map) != len(parts):
        raise MechanicalAssemblyKinematicsError("assembly part IDs must be unique")

    installed: list[str] = [shell.part_id]
    motions: list[AssemblyMotion] = []

    motions.append(
        _motion(
            1,
            "ASSEMBLE-FRAME-FROM-WEARER-SIDE",
            frame,
            (0.0, 0.0, -30.0),
            ((0.0, 0.0, -18.0), (0.0, 0.0, -8.0)),
            tuple(installed),
            (),
            "DIGITAL_REAR_INSERTION_THROUGH_OPEN_WEARER_SIDE_NOT_FASTENER_OR_TOLERANCE_EVIDENCE",
        )
    )
    installed.append(frame.part_id)

    for index, module in enumerate(modules, start=2):
        motions.append(
            _motion(
                index,
                f"ASSEMBLE-{module.part_id}-FROM-WEARER-SIDE",
                module,
                (0.0, 0.0, -28.0),
                ((0.0, 0.0, -16.0), (0.0, 0.0, -7.0)),
                tuple(installed),
                (frame.part_id,),
                "DIGITAL_PREASSEMBLED_ACTUATOR_REACTION_MODULE_INSERTION_FINAL_FRAME_ENGAGEMENT_REQUIRED",
            )
        )
        installed.append(module.part_id)

    motions.append(
        _motion(
            6,
            "ASSEMBLE-LEFT-YOKE-FROM-WEARER-LEFT",
            left_yoke,
            (-30.0, 0.0, 0.0),
            ((-18.0, 0.0, 0.0), (-8.0, 0.0, 0.0)),
            tuple(installed),
            (frame.part_id,),
            "DIGITAL_LATERAL_YOKE_INSERTION_FINAL_FRAME_ENGAGEMENT_REQUIRED",
        )
    )
    installed.append(left_yoke.part_id)

    motions.append(
        _motion(
            7,
            "ASSEMBLE-RIGHT-YOKE-FROM-WEARER-RIGHT",
            right_yoke,
            (30.0, 0.0, 0.0),
            ((18.0, 0.0, 0.0), (8.0, 0.0, 0.0)),
            tuple(installed),
            (frame.part_id,),
            "DIGITAL_LATERAL_YOKE_INSERTION_FINAL_FRAME_ENGAGEMENT_REQUIRED",
        )
    )
    installed.append(right_yoke.part_id)

    motions.append(
        _motion(
            8,
            "ASSEMBLE-HALO-FROM-POSTERIOR",
            halo,
            (0.0, 0.0, -34.0),
            ((0.0, 0.0, -20.0), (0.0, 0.0, -9.0)),
            tuple(installed),
            (left_yoke.part_id, right_yoke.part_id),
            "DIGITAL_POSTERIOR_HALO_INSERTION_FINAL_BILATERAL_YOKE_ENGAGEMENT_REQUIRED",
        )
    )
    installed.append(halo.part_id)

    motions.append(
        _motion(
            9,
            "ASSEMBLE-QUICK-RELEASE-LATCH-INBOARD",
            latch,
            (24.0, 0.0, 0.0),
            ((14.0, 0.0, 0.0), (7.0, 0.0, 0.0)),
            tuple(installed),
            (right_yoke.part_id,),
            "DIGITAL_REVERSE_OF_UNPOWERED_RELEASE_WITH_FINAL_RIGHT_YOKE_ENGAGEMENT_REQUIRED",
        )
    )

    motion_tuple = tuple(motions)
    results = _collision_results(motion_tuple, part_map)
    return MechanicalAssemblyKinematics(
        authority_revision=str(authority.get("project", "authority_revision")),
        realization_sha256=realization.realization_sha256,
        parts=parts,
        motions=motion_tuple,
        collision_results=results,
        blocked_downstream_steps=(
            "FINAL_FASTENER_ADHESIVE_OR_WELD_SELECTION",
            "FRAME_AND_RETENTION_TOLERANCE_STACK",
            "CARTRIDGE_DOOR_SEAL_LATCH_ASSEMBLY_AFTER_MANUAL_B_INTERFACE_RELEASE",
            "FLUID_TUBE_PUMP_MANIFOLD_INSTALLATION_AFTER_CELL4_REALIZED_ROUTE_RELEASE",
            "PCB_HARNESS_HMI_WARM_COOL_INSTALLATION_AFTER_MANUAL_B_RELEASE",
            "FINAL_EXTERIOR_CLOSURE_AFTER_ALL_SERVICE_SWEEPS_CLEAR",
        ),
        evidence_status=(
            "EXACT_BREP_SAMPLED_MANUAL_A_ASSEMBLY_KINEMATICS_"
            "NOT_FASTENER_TOLERANCE_ERGONOMIC_OR_PHYSICAL_ASSEMBLY_VALIDATION"
        ),
    )
