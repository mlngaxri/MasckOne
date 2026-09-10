from __future__ import annotations

"""Primary-control V6: physically rooted anti-rotation preload reaction path.

The donor side-preload leaf was a free rectangular body with no root, capture or load
reaction. V6 makes it a small stamped spring-metal insert whose buried root is trapped
inside the shell-integral structural barrel. Only the active tongue projects into the
bore. This closes the digital reaction path without adding screws or adhesive.

The 0.05 mm installed preload remains a geometry seed, not a validated force. Leaf
stress, preload force, friction, wear, fatigue and molding process remain open.
"""

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path

import cadquery as cq

from . import primary_control_haptic as v1
from . import primary_control_haptic_v5 as v5
from .model import MasckOneModel, build_model

SCHEMA = "MASCK_ONE_PRIMARY_CONTROL_HAPTIC_V6"
SOURCE_MAIN_SHA = v5.SOURCE_MAIN_SHA
LEAF_ROOT_RADIAL_LENGTH_MM = 1.38
LEAF_ROOT_Y_MM = 0.50
LEAF_ROOT_Z_MM = 0.36
LEAF_ROOT_ACTIVE_OVERLAP_MM = 0.12
MIN_ROOT_OUTER_POLYMER_COVER_MM = 0.35
_INTERSECTION_TOLERANCE_MM3 = 1e-7


class PrimaryControlHapticV6Error(ValueError):
    pass


def _leaf_geometry(rest_z: float, installed: bool = False) -> tuple[cq.Shape, cq.Shape, cq.Shape]:
    active_center_z = rest_z - 2.55
    active_center_x = v1.MOUNT_X_MM + v1.BARREL_BORE_DIAMETER_MM / 2.0 - 0.18
    active_center_y = (
        v1.MOUNT_Y_MM
        + v1.ANTI_ROTATION_SLOT_WIDTH_MM / 2.0
        - v1.ANTI_ROTATION_LEAF_THICKNESS_MM / 2.0
        - v1.ANTI_ROTATION_LEAF_PRELOAD_SEED_MM
    )
    active_y_shift = v1.ANTI_ROTATION_LEAF_PRELOAD_SEED_MM if installed else 0.0
    active = v1._box(
        0.34,
        v1.ANTI_ROTATION_LEAF_THICKNESS_MM,
        v1.ANTI_ROTATION_LEAF_LENGTH_MM,
        (
            active_center_x,
            active_center_y + active_y_shift,
            active_center_z,
        ),
    )

    active_bottom_z = active_center_z - v1.ANTI_ROTATION_LEAF_LENGTH_MM / 2.0
    active_outer_x = active_center_x + 0.34 / 2.0
    root_x0 = active_outer_x - LEAF_ROOT_ACTIVE_OVERLAP_MM
    root_center_x = root_x0 + LEAF_ROOT_RADIAL_LENGTH_MM / 2.0
    root = v1._box(
        LEAF_ROOT_RADIAL_LENGTH_MM,
        LEAF_ROOT_Y_MM,
        LEAF_ROOT_Z_MM,
        (
            root_center_x,
            active_center_y,
            active_bottom_z + LEAF_ROOT_Z_MM / 2.0,
        ),
    )

    # Manufactured free state is one stamped body. Installed reference holds the
    # buried root fixed while showing the intended active-tongue offset as a compound.
    if installed:
        whole = cq.Compound.makeCompound([root, active])
    else:
        whole = root.fuse(active).clean()
        if not whole.isValid() or len(whole.Solids()) != 1 or whole.Volume() <= 0.0:
            raise PrimaryControlHapticV6Error("rooted anti-rotation leaf must be one manufactured solid")
    return whole, root, active


def _replace_and_rename_leaf(
    parts: tuple[tuple[str, cq.Shape], ...],
    shell: cq.Shape,
    rooted_leaf: cq.Shape,
) -> tuple[tuple[str, cq.Shape], ...]:
    output: list[tuple[str, cq.Shape]] = []
    seen_shell = False
    seen_leaf = False
    for name, shape in parts:
        if name == "shell_with_primary_control_interface":
            output.append((name, shell))
            seen_shell = True
        elif name == "anti_rotation_preload_leaf_free":
            output.append(("anti_rotation_preload_leaf_insert_molded", rooted_leaf))
            seen_leaf = True
        else:
            output.append((name, shape))
    if not seen_shell or not seen_leaf:
        raise PrimaryControlHapticV6Error("V6 requires donor shell and free preload leaf")
    return tuple(output)


def _replace_leaf_reference(
    parts: tuple[tuple[str, cq.Shape], ...],
    installed_reference: cq.Shape,
) -> tuple[tuple[str, cq.Shape], ...]:
    output: list[tuple[str, cq.Shape]] = []
    seen = False
    for name, shape in parts:
        if name == "anti_rotation_leaf_installed_reference":
            output.append(("anti_rotation_leaf_rooted_installed_reference", installed_reference))
            seen = True
        else:
            output.append((name, shape))
    if not seen:
        raise PrimaryControlHapticV6Error("V6 requires donor installed leaf reference")
    return tuple(output)


@dataclass(frozen=True, slots=True)
class PrimaryControlHapticArchitectureV6:
    source_main_sha: str
    shell_outer_z_mm: float
    rest_cap_underside_z_mm: float
    material_parts: tuple[tuple[str, cq.Shape], ...] = field(repr=False, compare=False)
    reference_parts: tuple[tuple[str, cq.Shape], ...] = field(repr=False, compare=False)
    motion_sweep: cq.Shape = field(repr=False, compare=False)
    joint_overlap_mm3: dict[str, float] = field(default_factory=dict)
    bushing_capture_removed_mm3: dict[str, float] = field(default_factory=dict)
    magnet_cavity_removed_mm3: float = 0.0
    magnet_polymer_intersection_mm3: float = 0.0
    leaf_root_shell_removed_mm3: float = 0.0
    leaf_shell_intersection_mm3: float = 0.0
    leaf_outer_polymer_cover_mm: float = 0.0
    keepout_intersections_mm3: dict[str, float] = field(default_factory=dict)
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        if self.source_main_sha != SOURCE_MAIN_SHA:
            raise PrimaryControlHapticV6Error("V6 source-main mismatch")
        if self.physical_validation_eligible:
            raise PrimaryControlHapticV6Error("digital preload reaction path is not physical validation")
        material = dict(self.material_parts)
        leaf = material["anti_rotation_preload_leaf_insert_molded"]
        shell = material["shell_with_primary_control_interface"]
        if not leaf.isValid() or len(leaf.Solids()) != 1 or leaf.Volume() <= 0.0:
            raise PrimaryControlHapticV6Error("insert-molded preload leaf must be one positive solid")
        if not shell.isValid() or not shell.Solids() or shell.Volume() <= 0.0:
            raise PrimaryControlHapticV6Error("leaf-root cavity must preserve valid structural shell")
        if self.leaf_root_shell_removed_mm3 <= 0.0:
            raise PrimaryControlHapticV6Error("buried leaf root must remove positive shell volume")
        if self.leaf_shell_intersection_mm3 > _INTERSECTION_TOLERANCE_MM3:
            raise PrimaryControlHapticV6Error("preload leaf cannot occupy structural-shell material")
        if self.leaf_outer_polymer_cover_mm < MIN_ROOT_OUTER_POLYMER_COVER_MM:
            raise PrimaryControlHapticV6Error("insufficient barrel material outside buried preload root")
        if any(value > _INTERSECTION_TOLERANCE_MM3 for value in self.keepout_intersections_mm3.values()):
            raise PrimaryControlHapticV6Error("V6 primary control intersects a protected package/visual keepout")

    @property
    def architecture_sha256(self) -> str:
        payload = json.dumps(self.manifest(False), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        return hashlib.sha256(payload).hexdigest()

    def manifest(self, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "source_main_sha": self.source_main_sha,
            "supersedes": "V5_FREE_FLOATING_ANTI_ROTATION_PRELOAD_LEAF_WITHOUT_REACTION_PATH",
            "coordinate_frame_id": v1.WORLD_FRAME_ID,
            "anti_rotation_preload": {
                "architecture": "STAMPED_SPRING_METAL_ACTIVE_TONGUE_WITH_INSERT_MOLDED_BURIED_ROOT_IN_STRUCTURAL_BARREL",
                "active_leaf_length_mm": v1.ANTI_ROTATION_LEAF_LENGTH_MM,
                "active_leaf_thickness_mm": v1.ANTI_ROTATION_LEAF_THICKNESS_MM,
                "installed_preload_seed_mm": v1.ANTI_ROTATION_LEAF_PRELOAD_SEED_MM,
                "root_radial_length_mm": LEAF_ROOT_RADIAL_LENGTH_MM,
                "root_y_mm": LEAF_ROOT_Y_MM,
                "root_z_mm": LEAF_ROOT_Z_MM,
                "root_shell_removed_mm3": self.leaf_root_shell_removed_mm3,
                "leaf_shell_intersection_mm3": self.leaf_shell_intersection_mm3,
                "root_outer_polymer_cover_mm": self.leaf_outer_polymer_cover_mm,
                "separate_fastener_parts": 0,
                "adhesive_required": False,
                "preload_force_validated": False,
            },
            "guidance": "TWO_SHELL_FIXED_SPLIT_LOW_FRICTION_FLANGED_SLEEVES_PLUS_ROOTED_SIDE_PRELOAD",
            "sensor_magnet": "FULLY_TRAPPED_INSERT_MOLDED_MAGNET_IN_STEM",
            "tactile_generator_status": "CURRENT_SHORT_BEAM_CUSTOM_SPRING_REJECTED_AS_FORCE_DERIVED_PENDING_REPLACEMENT_OR_NONLINEAR_EVIDENCE",
            "tactile_reference_rule": "S_T_DUPONT_LIGNE_2_PRECISION_FEEL_ONLY_NOT_SOUND_OR_MECHANISM_COPY",
            "cost_rule": "ZERO_EXTRA_LEAF_FASTENERS_OR_ADHESIVE; PRECISION_BY_DATUM_PRELOAD_AND_CAPTURE_GEOMETRY",
            "material_parts": [name for name, _shape in self.material_parts],
            "reference_parts": [name for name, _shape in self.reference_parts],
            "keepout_intersections_mm3": self.keepout_intersections_mm3,
            "physical_validation_eligible": False,
            "physical_validation": (
                "OPEN_LEAF_PRELOAD_FORCE_STRESS_FATIGUE_CREEP_FRICTION_WEAR_INSERT_MOLD_PROCESS_GUIDE_WOBBLE_FORCE_TRAVEL_"
                "TACTILE_GENERATOR_SEALING_SOUND_LIFETIME_AND_SUBJECTIVE_FEEL"
            ),
        }
        if include_sha:
            payload["architecture_sha256"] = self.architecture_sha256
        return payload


def build_primary_control_haptic_architecture_v6(
    *,
    model: MasckOneModel | None = None,
) -> PrimaryControlHapticArchitectureV6:
    model = build_model() if model is None else model
    base = v5.build_primary_control_haptic_architecture_v5(model=model)
    material = dict(base.material_parts)

    free_leaf, root, _active = _leaf_geometry(base.rest_cap_underside_z_mm, installed=False)
    installed_leaf, _installed_root, _installed_active = _leaf_geometry(base.rest_cap_underside_z_mm, installed=True)

    shell_before = material["shell_with_primary_control_interface"]
    before_volume = float(shell_before.Volume())
    shell_after = shell_before.cut(root).clean()
    removed = before_volume - float(shell_after.Volume())
    overlap = v1._intersection_volume(shell_after, free_leaf)

    root_bb = root.BoundingBox()
    barrel_outer_x = v1.MOUNT_X_MM + v1.BARREL_OD_MM / 2.0
    outer_cover = barrel_outer_x - root_bb.xmax

    material_parts = _replace_and_rename_leaf(base.material_parts, shell_after, free_leaf)
    reference_parts = _replace_leaf_reference(base.reference_parts, installed_leaf)

    result = PrimaryControlHapticArchitectureV6(
        SOURCE_MAIN_SHA,
        base.shell_outer_z_mm,
        base.rest_cap_underside_z_mm,
        material_parts,
        reference_parts,
        base.motion_sweep,
        base.joint_overlap_mm3,
        base.bushing_capture_removed_mm3,
        base.magnet_cavity_removed_mm3,
        base.magnet_polymer_intersection_mm3,
        round(removed, 9),
        round(overlap, 9),
        round(outer_cover, 9),
        base.keepout_intersections_mm3,
        False,
    )
    result.__post_init__()
    return result


def export_primary_control_haptic_architecture_v6(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    architecture = build_primary_control_haptic_architecture_v6()
    for name, shape in architecture.material_parts:
        cq.exporters.export(shape, str(output_dir / f"{name}_MANUFACTURED.step"))
    for name, shape in architecture.reference_parts:
        cq.exporters.export(shape, str(output_dir / f"{name}_REFERENCE.step"))
    manifest = architecture.manifest()
    (output_dir / "primary_control_haptic_v6_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest
