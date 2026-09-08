from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import math

import cadquery as cq

from .model import MasckOneModel, build_model
from .structural_frame_realization import _protected_zone_solid
from .structural_frame_shell_joints import (
    StructuralFrameShellJointArchitecture,
    build_structural_frame_shell_joints,
)

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_ACTUATOR_REACTIONS_V1"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
REACTION_IDS = (
    "ACTUATOR_REACTION_SUPERIOR_LEFT",
    "ACTUATOR_REACTION_SUPERIOR_RIGHT",
    "ACTUATOR_REACTION_INFERIOR_LEFT",
    "ACTUATOR_REACTION_INFERIOR_RIGHT",
)

# Deterministic DIGITAL MVP geometry seeds. These are not production tolerances,
# fastener release dimensions, material allowables, force capability, or fatigue proof.
REACTION_X_MM = 66.0
REACTION_Y_MM = 48.0
BOSS_WIDTH_MM = 10.0
BOSS_HEIGHT_MM = 10.0
SOCKET_WIDTH_MM = 6.0
SOCKET_HEIGHT_MM = 6.0
SOCKET_DEPTH_MM = 1.25
KEY_WIDTH_MM = 2.0
KEY_DEPTH_MM = 0.65
_INTERSECTION_TOLERANCE_MM3 = 1e-7


class StructuralFrameActuatorReactionError(ValueError):
    pass


def _intersection_volume(a: cq.Workplane, b: cq.Workplane) -> float:
    try:
        return max(0.0, float(a.intersect(b).val().Volume()))
    except Exception:
        return 0.0


def _valid_single_solid(shape: cq.Workplane, label: str) -> None:
    value = shape.val()
    if not value.isValid() or len(value.Solids()) != 1 or float(value.Volume()) <= 0.0:
        raise StructuralFrameActuatorReactionError(
            f"{label} must be one valid positive-volume B-rep solid"
        )


def _reaction_centers() -> tuple[tuple[float, float], ...]:
    return (
        (-REACTION_X_MM, REACTION_Y_MM),
        (REACTION_X_MM, REACTION_Y_MM),
        (-REACTION_X_MM, -REACTION_Y_MM),
        (REACTION_X_MM, -REACTION_Y_MM),
    )


@dataclass(frozen=True, slots=True)
class ActuatorReactionCounterpart:
    reaction_id: str
    center_xy_mm: tuple[float, float]
    boss_capture_volume_mm3: float
    socket_removed_volume_mm3: float
    protected_intersection_volume_mm3: float
    boss: cq.Workplane = field(repr=False, compare=False)
    socket_tool: cq.Workplane = field(repr=False, compare=False)
    keyed_socket_tool: cq.Workplane = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.reaction_id not in REACTION_IDS:
            raise StructuralFrameActuatorReactionError(
                f"unknown reaction counterpart {self.reaction_id!r}"
            )
        if len(self.center_xy_mm) != 2 or not all(
            math.isfinite(float(value)) for value in self.center_xy_mm
        ):
            raise StructuralFrameActuatorReactionError("reaction center must be finite XY")
        for label, shape in (
            ("reaction boss", self.boss),
            ("reaction socket tool", self.socket_tool),
            ("reaction keyed socket tool", self.keyed_socket_tool),
        ):
            _valid_single_solid(shape, label)
        if self.boss_capture_volume_mm3 <= _INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameActuatorReactionError(
                "actuator reaction boss must have positive integral capture into source frame"
            )
        if self.socket_removed_volume_mm3 <= _INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameActuatorReactionError(
                "actuator reaction socket must remove real frame-side boss material"
            )
        if self.protected_intersection_volume_mm3 > _INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameActuatorReactionError(
                "actuator reaction counterpart intersects a hard protected envelope"
            )

    def manifest(self) -> dict[str, object]:
        return {
            "reaction_id": self.reaction_id,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "center_xy_mm": list(self.center_xy_mm),
            "interface_semantics": "FRAME_INTEGRAL_BOSS_WITH_KEYED_POSITIVE_FEMALE_REACTION_SOCKET",
            "geometry_seed_status": "DIGITAL_MVP_CLOSURE_SEEDS_NOT_PRODUCTION_TOLERANCE_OR_FORCE_EVIDENCE",
            "dimensions_mm": {
                "boss_width": BOSS_WIDTH_MM,
                "boss_height": BOSS_HEIGHT_MM,
                "socket_width": SOCKET_WIDTH_MM,
                "socket_height": SOCKET_HEIGHT_MM,
                "socket_depth": SOCKET_DEPTH_MM,
                "anti_rotation_key_width": KEY_WIDTH_MM,
                "anti_rotation_key_depth": KEY_DEPTH_MM,
            },
            "measured": {
                "boss_capture_volume_mm3": self.boss_capture_volume_mm3,
                "socket_removed_volume_mm3": self.socket_removed_volume_mm3,
                "protected_intersection_volume_mm3": self.protected_intersection_volume_mm3,
            },
        }


@dataclass(frozen=True, slots=True)
class StructuralFrameActuatorReactionArchitecture:
    source_shell_joint_architecture_sha256: str
    reactions: tuple[ActuatorReactionCounterpart, ...]
    frame_with_reaction_counterparts: cq.Workplane = field(repr=False, compare=False)
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        if len(self.source_shell_joint_architecture_sha256) != 64 or any(
            c not in "0123456789abcdef"
            for c in self.source_shell_joint_architecture_sha256
        ):
            raise StructuralFrameActuatorReactionError(
                "source shell-joint architecture identity must be canonical SHA-256"
            )
        if tuple(reaction.reaction_id for reaction in self.reactions) != REACTION_IDS:
            raise StructuralFrameActuatorReactionError(
                "all four actuator reaction counterparts must exist in controlled order"
            )
        _valid_single_solid(
            self.frame_with_reaction_counterparts,
            "frame with four actuator reaction counterparts",
        )
        if self.physical_validation_eligible is not False:
            raise StructuralFrameActuatorReactionError(
                "digital reaction-counterpart geometry is not physical validation evidence"
            )

    @property
    def architecture_sha256(self) -> str:
        raw = json.dumps(
            self.manifest(include_sha=False),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "source_shell_joint_architecture_sha256": self.source_shell_joint_architecture_sha256,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "reaction_count": len(self.reactions),
            "reactions": [reaction.manifest() for reaction in self.reactions],
            "load_path_status": "FOUR_POSITIVE_FRAME_SIDE_REACTION_COUNTERPARTS_REALIZED_CARRIER_MATES_AND_FORCE_VALIDATION_OPEN",
            "world_mount_status": "FRAME_SIDE_DATUMS_REALIZED_ACTUATOR_PACKAGE_PLACEMENT_NOT_PROMOTED",
            "physical_validation_eligible": self.physical_validation_eligible,
        }
        if include_sha:
            payload["architecture_sha256"] = self.architecture_sha256
        return payload


def build_structural_frame_actuator_reactions(
    *,
    model: MasckOneModel | None = None,
    shell_joints: StructuralFrameShellJointArchitecture | None = None,
) -> StructuralFrameActuatorReactionArchitecture:
    model = build_model() if model is None else model
    shell_joints = (
        build_structural_frame_shell_joints(model=model)
        if shell_joints is None
        else shell_joints
    )
    if type(model) is not MasckOneModel or type(shell_joints) is not StructuralFrameShellJointArchitecture:
        raise StructuralFrameActuatorReactionError(
            "exact model and shell-joint architecture types are required"
        )

    frame = shell_joints.assembled_frame
    bounds = frame.val().BoundingBox()
    z_min = float(bounds.zmin)
    z_max = float(bounds.zmax)
    depth = z_max - z_min
    z_center = (z_min + z_max) / 2.0
    if depth <= SOCKET_DEPTH_MM:
        raise StructuralFrameActuatorReactionError(
            "source frame axial depth is insufficient for keyed reaction socket"
        )

    current_frame = frame
    records: list[ActuatorReactionCounterpart] = []
    for reaction_id, (cx, cy) in zip(REACTION_IDS, _reaction_centers(), strict=True):
        boss = (
            cq.Workplane("XY")
            .box(BOSS_WIDTH_MM, BOSS_HEIGHT_MM, depth, centered=(True, True, True))
            .translate((cx, cy, z_center))
        )
        capture = _intersection_volume(current_frame, boss)
        if capture <= _INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameActuatorReactionError(
                f"{reaction_id} does not positively intersect source frame material"
            )

        socket_center_z = z_max - SOCKET_DEPTH_MM / 2.0
        socket = (
            cq.Workplane("XY")
            .box(SOCKET_WIDTH_MM, SOCKET_HEIGHT_MM, SOCKET_DEPTH_MM, centered=(True, True, True))
            .translate((cx, cy, socket_center_z))
        )
        key = (
            cq.Workplane("XY")
            .box(KEY_WIDTH_MM, SOCKET_HEIGHT_MM / 2.0, KEY_DEPTH_MM, centered=(True, True, True))
            .translate((cx + SOCKET_WIDTH_MM / 2.0 - KEY_WIDTH_MM / 2.0, cy, z_max - KEY_DEPTH_MM / 2.0))
        )
        keyed_socket = socket.union(key)
        frame_with_boss = current_frame.union(boss)
        removed = _intersection_volume(frame_with_boss, keyed_socket)
        if removed <= _INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameActuatorReactionError(
                f"{reaction_id} keyed socket removes no frame-side reaction material"
            )
        next_frame = frame_with_boss.cut(keyed_socket)
        _valid_single_solid(next_frame, f"{reaction_id} integrated frame reaction")

        protected_intersection = 0.0
        for protected in model.protected_volumes.all:
            zone = protected.zone
            keepout = _protected_zone_solid(
                center_x_mm=zone.center.x,
                center_y_mm=zone.center.y,
                envelope_width_mm=zone.envelope_width_mm,
                envelope_height_mm=zone.envelope_height_mm,
                angle_deg=zone.angle_deg,
                z_min_mm=z_min - 1.0,
                z_max_mm=z_max + 1.0,
            )
            protected_intersection += _intersection_volume(boss, keepout)

        record = ActuatorReactionCounterpart(
            reaction_id=reaction_id,
            center_xy_mm=(cx, cy),
            boss_capture_volume_mm3=round(capture, 8),
            socket_removed_volume_mm3=round(removed, 8),
            protected_intersection_volume_mm3=round(protected_intersection, 8),
            boss=boss,
            socket_tool=socket,
            keyed_socket_tool=keyed_socket,
        )
        record.__post_init__()
        current_frame = next_frame
        records.append(record)

    result = StructuralFrameActuatorReactionArchitecture(
        source_shell_joint_architecture_sha256=shell_joints.architecture_sha256,
        reactions=tuple(records),
        frame_with_reaction_counterparts=current_frame,
        physical_validation_eligible=False,
    )
    result.__post_init__()
    return result
