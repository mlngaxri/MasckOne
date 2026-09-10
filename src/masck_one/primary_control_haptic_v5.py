from __future__ import annotations

"""Primary-control V5: explicit low-part-count sensor-magnet retention.

The donor geometry declared the Hall magnet as a real component while leaving the
same volume filled by stem polymer. V5 replaces that impossible overlap with an
internal insert-mold cavity. The magnet remains fully trapped by polymer and does not
require a separate cap, screw or adhesive retention feature.

Insert molding is a production-intent architecture only. Magnet grade, coating,
molding process window, thermal exposure, corrosion, sensor transfer and lifetime
remain supplier and physical-validation work.
"""

from dataclasses import dataclass, field
import hashlib
import json
import math
from pathlib import Path

import cadquery as cq

from . import primary_control_haptic as v1
from . import primary_control_haptic_v4 as v4
from .model import MasckOneModel, build_model

SCHEMA = "MASCK_ONE_PRIMARY_CONTROL_HAPTIC_V5"
SOURCE_MAIN_SHA = v4.SOURCE_MAIN_SHA
MAGNET_REAR_POLYMER_SKIN_MM = 0.20
MIN_MAGNET_RADIAL_ENCAPSULATION_MM = 1.50
_VOLUME_TOLERANCE_MM3 = 1e-6
_INTERSECTION_TOLERANCE_MM3 = 1e-7


class PrimaryControlHapticV5Error(ValueError):
    pass


def _replace_named(
    parts: tuple[tuple[str, cq.Shape], ...],
    replacements: dict[str, cq.Shape],
) -> tuple[tuple[str, cq.Shape], ...]:
    names = {name for name, _shape in parts}
    missing = set(replacements) - names
    if missing:
        raise PrimaryControlHapticV5Error(f"cannot replace absent parts: {sorted(missing)}")
    return tuple((name, replacements.get(name, shape)) for name, shape in parts)


@dataclass(frozen=True, slots=True)
class PrimaryControlHapticArchitectureV5:
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
    keepout_intersections_mm3: dict[str, float] = field(default_factory=dict)
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        if self.source_main_sha != SOURCE_MAIN_SHA:
            raise PrimaryControlHapticV5Error("V5 source-main mismatch")
        if self.physical_validation_eligible:
            raise PrimaryControlHapticV5Error("digital magnet retention is not physical validation")
        material = dict(self.material_parts)
        moving = material["primary_control_cap_stem"]
        magnet = material["sensor_magnet"]
        if not moving.isValid() or len(moving.Solids()) != 1 or moving.Volume() <= 0.0:
            raise PrimaryControlHapticV5Error("magnet cavity must preserve one positive moving polymer solid")
        if not magnet.isValid() or len(magnet.Solids()) != 1 or magnet.Volume() <= 0.0:
            raise PrimaryControlHapticV5Error("sensor magnet must remain one positive component")
        if self.magnet_cavity_removed_mm3 <= 0.0:
            raise PrimaryControlHapticV5Error("magnet cavity must remove positive polymer volume")
        if abs(self.magnet_cavity_removed_mm3 - magnet.Volume()) > _VOLUME_TOLERANCE_MM3:
            raise PrimaryControlHapticV5Error("insert-mold cavity must match nominal magnet envelope")
        if self.magnet_polymer_intersection_mm3 > _INTERSECTION_TOLERANCE_MM3:
            raise PrimaryControlHapticV5Error("magnet cannot occupy polymer material")
        radial_cover = (v1.STEM_DIAMETER_MM - v1.MAGNET_DIAMETER_MM) / 2.0
        if radial_cover < MIN_MAGNET_RADIAL_ENCAPSULATION_MM:
            raise PrimaryControlHapticV5Error("insufficient radial polymer around insert-molded magnet")
        if not math.isclose(MAGNET_REAR_POLYMER_SKIN_MM, 0.20, abs_tol=1e-12):
            raise PrimaryControlHapticV5Error("rear encapsulation datum changed unexpectedly")
        if any(value > _INTERSECTION_TOLERANCE_MM3 for value in self.keepout_intersections_mm3.values()):
            raise PrimaryControlHapticV5Error("V5 primary control intersects a protected package/visual keepout")

    @property
    def architecture_sha256(self) -> str:
        payload = json.dumps(self.manifest(False), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        return hashlib.sha256(payload).hexdigest()

    def manifest(self, include_sha: bool = True) -> dict[str, object]:
        material = dict(self.material_parts)
        radial_cover = (v1.STEM_DIAMETER_MM - v1.MAGNET_DIAMETER_MM) / 2.0
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "source_main_sha": self.source_main_sha,
            "supersedes": "V4_SENSOR_MAGNET_FALSE_MATERIAL_OVERLAP_WITHOUT_RETENTION_PATH",
            "coordinate_frame_id": v1.WORLD_FRAME_ID,
            "location_world_mm": [v1.MOUNT_X_MM, v1.MOUNT_Y_MM, self.shell_outer_z_mm],
            "button_axis_world_unit": list(v1.AXIS_WORLD),
            "rest_cap_underside_z_mm": self.rest_cap_underside_z_mm,
            "selected_mechanism": (
                "CONNECTED_CAP_STEM_PLUS_SHELL_CAPTURED_SPLIT_GUIDES_PLUS_KEYED_SIDE_PRELOAD_PLUS_"
                "DEDICATED_TACTILE_GENERATOR_PLUS_TWO_STAGE_LANDING_PLUS_HARD_STOP_PLUS_INSERT_MOLDED_HALL_MAGNET"
            ),
            "sensor_magnet_retention": {
                "architecture": "FULLY_TRAPPED_INSERT_MOLDED_MAGNET_IN_STEM",
                "magnet_diameter_mm": v1.MAGNET_DIAMETER_MM,
                "magnet_length_mm": v1.MAGNET_LENGTH_MM,
                "rear_polymer_skin_mm": MAGNET_REAR_POLYMER_SKIN_MM,
                "radial_polymer_cover_mm": radial_cover,
                "magnet_cavity_removed_mm3": self.magnet_cavity_removed_mm3,
                "magnet_polymer_intersection_mm3": self.magnet_polymer_intersection_mm3,
                "separate_retainer_parts": 0,
                "adhesive_required_for_retention": False,
                "post_mold_magnet_serviceable": False,
            },
            "guidance": {
                "architecture": "TWO_SHELL_FIXED_SPLIT_LOW_FRICTION_FLANGED_SLEEVES",
                "capture_groove_removed_mm3": self.bushing_capture_removed_mm3,
            },
            "tactile_reference_rule": (
                "S_T_DUPONT_LIGNE_2_CLASS_PRECISION_FEEL_ONLY; NO_SOUND_MECHANISM_MATERIAL_OR_STYLE_COPY"
            ),
            "cost_rule": (
                "MINIMIZE_HIDDEN_PART_COUNT_AND_MANUAL_ALIGNMENT; SPEND MATERIAL_AND_FINISH_BUDGET_ON_USER_TOUCH_SURFACES"
            ),
            "material_parts": [name for name, _shape in self.material_parts],
            "reference_parts": [name for name, _shape in self.reference_parts],
            "keepout_intersections_mm3": self.keepout_intersections_mm3,
            "fusion_handoff": {
                "cad_platform": "AUTODESK_FUSION_360",
                "grounded_component": "shell_with_primary_control_interface",
                "moving_component": "primary_control_cap_stem",
                "insert_molded_component": "sensor_magnet",
                "button_slider_dof": f"TRANSLATION_-Z_0_TO_{v1.HARD_STOP_MM:.2f}_MM",
            },
            "physical_validation_eligible": False,
            "physical_validation": (
                "OPEN_MAGNET_GRADE_COATING_INSERT_MOLD_PROCESS_TEMPERATURE_CORROSION_SENSOR_TRANSFER_FORCE_TRAVEL_"
                "GUIDE_FRICTION_WOBBLE_SEALING_FATIGUE_BUMPER_RATE_SOUND_LIFETIME_AND_SUBJECTIVE_FEEL"
            ),
        }
        if include_sha:
            payload["architecture_sha256"] = self.architecture_sha256
        return payload


def build_primary_control_haptic_architecture_v5(
    *,
    model: MasckOneModel | None = None,
) -> PrimaryControlHapticArchitectureV5:
    model = build_model() if model is None else model
    base = v4.build_primary_control_haptic_architecture_v4(model=model)
    material = dict(base.material_parts)

    moving_before = material["primary_control_cap_stem"]
    magnet = material["sensor_magnet"]
    before_volume = float(moving_before.Volume())
    moving_after = moving_before.cut(magnet).clean()
    removed = before_volume - float(moving_after.Volume())
    overlap = v1._intersection_volume(moving_after, magnet)

    if not moving_after.isValid() or len(moving_after.Solids()) != 1:
        raise PrimaryControlHapticV5Error("insert-mold cavity invalidated moving polymer")

    material_parts = _replace_named(
        base.material_parts,
        {"primary_control_cap_stem": moving_after},
    )

    # The package envelope is unchanged by removing internal polymer, so reuse the
    # already-conservative V4 external keepout result rather than silently weakening it.
    result = PrimaryControlHapticArchitectureV5(
        SOURCE_MAIN_SHA,
        base.shell_outer_z_mm,
        base.rest_cap_underside_z_mm,
        material_parts,
        base.reference_parts,
        base.motion_sweep,
        base.joint_overlap_mm3,
        base.bushing_capture_removed_mm3,
        round(removed, 9),
        round(overlap, 9),
        base.keepout_intersections_mm3,
        False,
    )
    result.__post_init__()
    return result


def export_primary_control_haptic_architecture_v5(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    architecture = build_primary_control_haptic_architecture_v5()
    for name, shape in architecture.material_parts:
        cq.exporters.export(shape, str(output_dir / f"{name}_MANUFACTURED.step"))
    for name, shape in architecture.reference_parts:
        cq.exporters.export(shape, str(output_dir / f"{name}_REFERENCE.step"))
    manifest = architecture.manifest()
    (output_dir / "primary_control_haptic_v5_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest
