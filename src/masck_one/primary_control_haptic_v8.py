from __future__ import annotations

"""Primary-control V8: sidewall Hall sensing outside the complete moving envelope.

The legacy contactless package placed both Hall electronics and their support directly
behind the moving stem. At the 1.07 mm hard-stop travel that geometry has positive
collision volume, so it cannot be a valid production mechanism.

V8 restores the obsolete axial magnet cavity to polymer, moves the same nominal 3 x 1
mm magnetic target off-axis inside the stem between guide stations, and uses a tiny
sidewall Hall/FPC package in a recessed dry-side barrel pocket. The local PCB support
part disappears. A shallow outer-wall flex channel routes rearward without cutting
through the precision guide bore.

The package is digitally collision-free. Magnetic transfer, FPC bonding, calibration,
adhesive/process qualification, temperature behavior and lifetime remain physical and
electrical validation work.
"""

from dataclasses import dataclass, field
import hashlib
import json
import math
from pathlib import Path

import cadquery as cq

from . import primary_control_haptic as v1
from . import primary_control_haptic_v7 as v7
from .model import MasckOneModel, build_model

SCHEMA = "MASCK_ONE_PRIMARY_CONTROL_HAPTIC_V8"
SOURCE_MAIN_SHA = v7.SOURCE_MAIN_SHA

SIDE_MAGNET_CENTER_RADIUS_MM = 1.40
SIDE_MAGNET_CENTER_FROM_REST_MM = 2.85
SIDE_MAGNET_DIAMETER_MM = v1.MAGNET_DIAMETER_MM
SIDE_MAGNET_AXIAL_MM = v1.MAGNET_LENGTH_MM
MIN_SIDE_MAGNET_RADIAL_POLYMER_COVER_MM = 0.60
MIN_SIDE_MAGNET_TO_LOWER_GUIDE_AXIAL_CLEARANCE_MM = 0.04

SIDE_HALL_SENSOR_CENTER_RADIUS_MM = 4.85
SIDE_HALL_SENSOR_CENTER_FROM_REST_MM = SIDE_MAGNET_CENTER_FROM_REST_MM + v1.HARD_STOP_MM / 2.0
SIDE_HALL_SENSOR_RADIAL_MM = 0.80
SIDE_HALL_SENSOR_TANGENTIAL_MM = 2.20
SIDE_HALL_SENSOR_AXIAL_MM = 1.50

SENSOR_RECESS_CENTER_RADIUS_MM = 4.88
SENSOR_RECESS_RADIAL_MM = 0.90
SENSOR_RECESS_TANGENTIAL_MM = 2.40
SENSOR_RECESS_AXIAL_MM = 1.75
MIN_RECESS_INNER_LIGAMENT_MM = 0.15
MIN_RECESS_OUTER_BARREL_COVER_MM = 0.50

FLEX_CHANNEL_CENTER_RADIUS_MM = 5.18
FLEX_CHANNEL_RADIAL_MM = 0.30
FLEX_CHANNEL_TANGENTIAL_MM = 2.40
FLEX_TAIL_RADIAL_MM = 0.12
FLEX_TAIL_TANGENTIAL_MM = 2.00
FLEX_REAR_END_FROM_REST_MM = v1.BARREL_REAR_EXTENSION_MM + v1.CAP_PROUD_MM

SENSOR_BONDLINE_REFERENCE_MM = 0.06
_VOLUME_TOLERANCE_MM3 = 1e-6
_INTERSECTION_TOLERANCE_MM3 = 1e-7


class PrimaryControlHapticV8Error(ValueError):
    pass


def _offset_cylinder(
    diameter_mm: float,
    height_mm: float,
    *,
    center_x_mm: float,
    center_y_mm: float,
    z0_mm: float,
) -> cq.Shape:
    shape = (
        cq.Workplane("XY")
        .workplane(offset=z0_mm)
        .center(center_x_mm, center_y_mm)
        .circle(diameter_mm / 2.0)
        .extrude(height_mm)
        .val()
    )
    if not shape.isValid() or len(shape.Solids()) != 1 or shape.Volume() <= 0.0:
        raise PrimaryControlHapticV8Error("expected one valid offset cylinder")
    return shape


def _side_magnet(rest_z: float) -> cq.Shape:
    return _offset_cylinder(
        SIDE_MAGNET_DIAMETER_MM,
        SIDE_MAGNET_AXIAL_MM,
        center_x_mm=v1.MOUNT_X_MM - SIDE_MAGNET_CENTER_RADIUS_MM,
        center_y_mm=v1.MOUNT_Y_MM,
        z0_mm=rest_z - SIDE_MAGNET_CENTER_FROM_REST_MM - SIDE_MAGNET_AXIAL_MM / 2.0,
    )


def _side_sensor_reference(rest_z: float) -> cq.Shape:
    return v1._box(
        SIDE_HALL_SENSOR_RADIAL_MM,
        SIDE_HALL_SENSOR_TANGENTIAL_MM,
        SIDE_HALL_SENSOR_AXIAL_MM,
        (
            v1.MOUNT_X_MM - SIDE_HALL_SENSOR_CENTER_RADIUS_MM,
            v1.MOUNT_Y_MM,
            rest_z - SIDE_HALL_SENSOR_CENTER_FROM_REST_MM,
        ),
    )


def _sensor_recess(rest_z: float) -> cq.Shape:
    return v1._box(
        SENSOR_RECESS_RADIAL_MM,
        SENSOR_RECESS_TANGENTIAL_MM,
        SENSOR_RECESS_AXIAL_MM,
        (
            v1.MOUNT_X_MM - SENSOR_RECESS_CENTER_RADIUS_MM,
            v1.MOUNT_Y_MM,
            rest_z - SIDE_HALL_SENSOR_CENTER_FROM_REST_MM,
        ),
    )


def _flex_channel_and_reference(rest_z: float) -> tuple[cq.Shape, cq.Shape]:
    sensor_rear_z = rest_z - SIDE_HALL_SENSOR_CENTER_FROM_REST_MM - SENSOR_RECESS_AXIAL_MM / 2.0
    barrel_rear_z = rest_z - FLEX_REAR_END_FROM_REST_MM
    if not sensor_rear_z > barrel_rear_z:
        raise PrimaryControlHapticV8Error("sensor recess must remain forward of barrel rear")
    axial = sensor_rear_z - barrel_rear_z
    center_z = (sensor_rear_z + barrel_rear_z) / 2.0
    cutter = v1._box(
        FLEX_CHANNEL_RADIAL_MM,
        FLEX_CHANNEL_TANGENTIAL_MM,
        axial,
        (
            v1.MOUNT_X_MM - FLEX_CHANNEL_CENTER_RADIUS_MM,
            v1.MOUNT_Y_MM,
            center_z,
        ),
    )
    reference = v1._box(
        FLEX_TAIL_RADIAL_MM,
        FLEX_TAIL_TANGENTIAL_MM,
        axial,
        (
            v1.MOUNT_X_MM - FLEX_CHANNEL_CENTER_RADIUS_MM,
            v1.MOUNT_Y_MM,
            center_z,
        ),
    )
    return cutter, reference


def _continuous_motion_reference(rest_z: float) -> cq.Compound:
    cap = v1._cylinder(
        v1.CAP_DIAMETER_MM,
        v1.CAP_THICKNESS_MM + v1.HARD_STOP_MM,
        rest_z - v1.HARD_STOP_MM,
    )
    stem = v1._cylinder(
        v1.STEM_DIAMETER_MM,
        v1.STEM_LENGTH_MM + v1.HARD_STOP_MM,
        rest_z - v1.STEM_LENGTH_MM - v1.HARD_STOP_MM,
    )

    rib_length = v1.STEM_LENGTH_MM - 0.35
    rib_rest_zmin = rest_z - rib_length - 0.18
    rib_rest_zmax = rest_z - 0.18
    rib_sweep_zmin = rib_rest_zmin - v1.HARD_STOP_MM
    rib_sweep_height = rib_rest_zmax - rib_sweep_zmin
    rib = v1._box(
        v1.ANTI_ROTATION_RIB_RADIAL_MM,
        v1.ANTI_ROTATION_RIB_WIDTH_MM,
        rib_sweep_height,
        (
            v1.MOUNT_X_MM + v1.STEM_DIAMETER_MM / 2.0 + v1.ANTI_ROTATION_RIB_RADIAL_MM / 2.0,
            v1.MOUNT_Y_MM,
            rib_sweep_zmin + rib_sweep_height / 2.0,
        ),
    )

    core_rest_z0 = rest_z + (v1.CAP_THICKNESS_MM - v1.INERTIA_CORE_THICKNESS_MM) / 2.0
    core = v1._cylinder(
        v1.INERTIA_CORE_DIAMETER_MM,
        v1.INERTIA_CORE_THICKNESS_MM + v1.HARD_STOP_MM,
        core_rest_z0 - v1.HARD_STOP_MM,
    )

    magnet = _offset_cylinder(
        SIDE_MAGNET_DIAMETER_MM,
        SIDE_MAGNET_AXIAL_MM + v1.HARD_STOP_MM,
        center_x_mm=v1.MOUNT_X_MM - SIDE_MAGNET_CENTER_RADIUS_MM,
        center_y_mm=v1.MOUNT_Y_MM,
        z0_mm=(
            rest_z
            - SIDE_MAGNET_CENTER_FROM_REST_MM
            - SIDE_MAGNET_AXIAL_MM / 2.0
            - v1.HARD_STOP_MM
        ),
    )
    envelope = cq.Compound.makeCompound([cap, stem, rib, core, magnet])
    if not envelope.Solids() or any(not solid.isValid() for solid in envelope.Solids()):
        raise PrimaryControlHapticV8Error("continuous side-sensor motion reference must be valid")
    return envelope


def _replace_material_parts(
    parts: tuple[tuple[str, cq.Shape], ...],
    *,
    shell: cq.Shape,
    moving: cq.Shape,
    magnet: cq.Shape,
) -> tuple[tuple[str, cq.Shape], ...]:
    output: list[tuple[str, cq.Shape]] = []
    seen = {"shell": False, "moving": False, "magnet": False, "support": False}
    for name, shape in parts:
        if name == "shell_with_primary_control_interface":
            output.append((name, shell))
            seen["shell"] = True
        elif name == "primary_control_cap_stem":
            output.append((name, moving))
            seen["moving"] = True
        elif name == "sensor_magnet":
            output.append((name, magnet))
            seen["magnet"] = True
        elif name == "hall_pcb_support":
            seen["support"] = True
        else:
            output.append((name, shape))
    if not all(seen.values()):
        raise PrimaryControlHapticV8Error(f"V8 donor material missing required part: {seen}")
    return tuple(output)


def _replace_reference_parts(
    parts: tuple[tuple[str, cq.Shape], ...],
    *,
    hall_sensor: cq.Shape,
    flex_tail: cq.Shape,
    motion: cq.Shape,
) -> tuple[tuple[str, cq.Shape], ...]:
    output: list[tuple[str, cq.Shape]] = []
    saw_hall = False
    saw_motion = False
    for name, shape in parts:
        if name == "hall_sensor_envelope":
            output.append(("hall_side_sensor_fpc_envelope", hall_sensor))
            output.append(("hall_flex_tail_reference", flex_tail))
            saw_hall = True
        elif name == "cap_motion_sweep":
            output.append((name, motion))
            saw_motion = True
        else:
            output.append((name, shape))
    if not saw_hall or not saw_motion:
        raise PrimaryControlHapticV8Error("V8 requires donor Hall and motion references")
    return tuple(output)


def _assembled_module(
    material_parts: tuple[tuple[str, cq.Shape], ...],
    reference_parts: tuple[tuple[str, cq.Shape], ...],
) -> cq.Compound:
    material = dict(material_parts)
    references = dict(reference_parts)
    return cq.Compound.makeCompound(
        [
            material["primary_control_cap_stem"],
            material["cap_inertia_core"],
            references["upper_split_bushing_installed_reference"],
            references["lower_split_bushing_installed_reference"],
            references["anti_rotation_leaf_rooted_installed_reference"],
            material["wet_diaphragm"],
            material["tactile_spring_formed"],
            material["tactile_damping_annulus"],
            material["tactile_snap_retainer"],
            material["landing_progressive_overmold"],
            material["sensor_magnet"],
            references["hall_side_sensor_fpc_envelope"],
            references["hall_flex_tail_reference"],
        ]
    )


def _keepout_intersections(
    model: MasckOneModel,
    material_parts: tuple[tuple[str, cq.Shape], ...],
    reference_parts: tuple[tuple[str, cq.Shape], ...],
) -> dict[str, float]:
    module = _assembled_module(material_parts, reference_parts)
    keepouts = {
        **{component.name: component.solid.val() for component in model.actuator_envelopes},
        "water_reservoir_envelope": model.water_reservoir_envelope.solid.val(),
        "waste_cartridge_envelope": model.waste_cartridge_envelope.solid.val(),
        "battery_reference_envelope": model.battery_reference_envelope.solid.val(),
        **{component.name: component.solid.val() for component in model.visual_keepouts},
    }
    return {
        name: round(v1._intersection_volume(module, target), 8)
        for name, target in keepouts.items()
    }


@dataclass(frozen=True, slots=True)
class PrimaryControlHapticArchitectureV8:
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
    landing_lock_slot_removed_mm3: float = 0.0
    landing_shell_intersection_mm3: float = 0.0
    rigid_stop_projected_area_fraction: float = 0.0
    lock_head_to_barrel_bore_clearance_mm: float = 0.0
    restored_axial_cavity_polymer_mm3: float = 0.0
    side_magnet_cavity_removed_mm3: float = 0.0
    side_magnet_polymer_intersection_mm3: float = 0.0
    side_magnet_radial_polymer_cover_mm: float = 0.0
    side_magnet_to_lower_guide_axial_clearance_mm: float = 0.0
    sensor_recess_removed_mm3: float = 0.0
    flex_channel_removed_mm3: float = 0.0
    sensor_motion_intersection_mm3: float = 0.0
    flex_motion_intersection_mm3: float = 0.0
    recess_inner_ligament_mm: float = 0.0
    recess_outer_barrel_cover_mm: float = 0.0
    keepout_intersections_mm3: dict[str, float] = field(default_factory=dict)
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        if self.source_main_sha != SOURCE_MAIN_SHA:
            raise PrimaryControlHapticV8Error("V8 source-main mismatch")
        if self.physical_validation_eligible:
            raise PrimaryControlHapticV8Error("digital sensor packaging is not physical validation")

        # Preserve every inherited V7 connectivity, guidance, magnet-retention root,
        # preload-reaction and landing invariant on the modified package.
        v7.PrimaryControlHapticArchitectureV7(
            self.source_main_sha,
            self.shell_outer_z_mm,
            self.rest_cap_underside_z_mm,
            self.material_parts,
            self.reference_parts,
            self.motion_sweep,
            self.joint_overlap_mm3,
            self.bushing_capture_removed_mm3,
            self.side_magnet_cavity_removed_mm3,
            self.side_magnet_polymer_intersection_mm3,
            self.leaf_root_shell_removed_mm3,
            self.leaf_shell_intersection_mm3,
            self.leaf_outer_polymer_cover_mm,
            self.landing_lock_slot_removed_mm3,
            self.landing_shell_intersection_mm3,
            self.rigid_stop_projected_area_fraction,
            self.lock_head_to_barrel_bore_clearance_mm,
            self.keepout_intersections_mm3,
            False,
        ).__post_init__()

        material = dict(self.material_parts)
        references = dict(self.reference_parts)
        if "hall_pcb_support" in material:
            raise PrimaryControlHapticV8Error("rejected rear Hall support part cannot remain")
        if "hall_sensor_envelope" in references:
            raise PrimaryControlHapticV8Error("rejected rear Hall reference cannot remain")
        if "hall_side_sensor_fpc_envelope" not in references or "hall_flex_tail_reference" not in references:
            raise PrimaryControlHapticV8Error("side Hall/FPC references are required")

        if self.restored_axial_cavity_polymer_mm3 <= 0.0:
            raise PrimaryControlHapticV8Error("obsolete axial magnet cavity must be restored to polymer")
        if self.side_magnet_cavity_removed_mm3 <= 0.0:
            raise PrimaryControlHapticV8Error("side magnet requires positive polymer cavity")
        magnet = material["sensor_magnet"]
        if abs(self.side_magnet_cavity_removed_mm3 - magnet.Volume()) > _VOLUME_TOLERANCE_MM3:
            raise PrimaryControlHapticV8Error("side magnet cavity must match nominal magnet volume")
        if self.side_magnet_polymer_intersection_mm3 > _INTERSECTION_TOLERANCE_MM3:
            raise PrimaryControlHapticV8Error("side magnet cannot occupy stem polymer")
        if self.side_magnet_radial_polymer_cover_mm < MIN_SIDE_MAGNET_RADIAL_POLYMER_COVER_MM:
            raise PrimaryControlHapticV8Error("side magnet leaves insufficient stem radial polymer cover")
        if self.side_magnet_to_lower_guide_axial_clearance_mm < MIN_SIDE_MAGNET_TO_LOWER_GUIDE_AXIAL_CLEARANCE_MM:
            raise PrimaryControlHapticV8Error("side magnet sweeps into the lower guide station")

        if self.sensor_recess_removed_mm3 <= 0.0 or self.flex_channel_removed_mm3 <= 0.0:
            raise PrimaryControlHapticV8Error("side Hall package requires positive shell recess and flex channel")
        if self.sensor_motion_intersection_mm3 > _INTERSECTION_TOLERANCE_MM3:
            raise PrimaryControlHapticV8Error("side Hall sensor intersects full moving envelope")
        if self.flex_motion_intersection_mm3 > _INTERSECTION_TOLERANCE_MM3:
            raise PrimaryControlHapticV8Error("Hall flex tail intersects full moving envelope")
        if self.recess_inner_ligament_mm < MIN_RECESS_INNER_LIGAMENT_MM:
            raise PrimaryControlHapticV8Error("sensor recess weakens precision bore ligament below minimum")
        if self.recess_outer_barrel_cover_mm < MIN_RECESS_OUTER_BARREL_COVER_MM:
            raise PrimaryControlHapticV8Error("sensor recess leaves insufficient outer barrel cover")
        if any(value > _INTERSECTION_TOLERANCE_MM3 for value in self.keepout_intersections_mm3.values()):
            raise PrimaryControlHapticV8Error("V8 primary control intersects a protected package/visual keepout")

    @property
    def architecture_sha256(self) -> str:
        payload = json.dumps(self.manifest(False), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        return hashlib.sha256(payload).hexdigest()

    def manifest(self, include_sha: bool = True) -> dict[str, object]:
        payload = v7.PrimaryControlHapticArchitectureV7(
            self.source_main_sha,
            self.shell_outer_z_mm,
            self.rest_cap_underside_z_mm,
            self.material_parts,
            self.reference_parts,
            self.motion_sweep,
            self.joint_overlap_mm3,
            self.bushing_capture_removed_mm3,
            self.side_magnet_cavity_removed_mm3,
            self.side_magnet_polymer_intersection_mm3,
            self.leaf_root_shell_removed_mm3,
            self.leaf_shell_intersection_mm3,
            self.leaf_outer_polymer_cover_mm,
            self.landing_lock_slot_removed_mm3,
            self.landing_shell_intersection_mm3,
            self.rigid_stop_projected_area_fraction,
            self.lock_head_to_barrel_bore_clearance_mm,
            self.keepout_intersections_mm3,
            False,
        ).manifest(False)
        payload.update(
            {
                "schema": SCHEMA,
                "supersedes": "V7_REAR_AXIAL_HALL_PCB_AND_SUPPORT_COLLIDING_WITH_FULL_STEM_TRAVEL",
                "sensor": {
                    "architecture": "OFF_AXIS_STEM_MAGNET_PLUS_BARREL_SIDEWALL_HALL_SENSOR_ON_FPC",
                    "legacy_rear_pcb_support_removed": True,
                    "side_magnet_center_radius_mm": SIDE_MAGNET_CENTER_RADIUS_MM,
                    "side_magnet_center_from_rest_mm": SIDE_MAGNET_CENTER_FROM_REST_MM,
                    "side_magnet_radial_polymer_cover_mm": self.side_magnet_radial_polymer_cover_mm,
                    "side_magnet_to_lower_guide_axial_clearance_mm": self.side_magnet_to_lower_guide_axial_clearance_mm,
                    "hall_sensor_center_radius_mm": SIDE_HALL_SENSOR_CENTER_RADIUS_MM,
                    "hall_sensor_center_from_rest_mm": SIDE_HALL_SENSOR_CENTER_FROM_REST_MM,
                    "sensor_recess_removed_mm3": self.sensor_recess_removed_mm3,
                    "flex_channel_removed_mm3": self.flex_channel_removed_mm3,
                    "recess_inner_ligament_mm": self.recess_inner_ligament_mm,
                    "recess_outer_barrel_cover_mm": self.recess_outer_barrel_cover_mm,
                    "sensor_full_motion_intersection_mm3": self.sensor_motion_intersection_mm3,
                    "flex_full_motion_intersection_mm3": self.flex_motion_intersection_mm3,
                    "bondline_reference_mm": SENSOR_BONDLINE_REFERENCE_MM,
                    "local_support_parts_removed": 1,
                    "electrical_sensor_selected": False,
                    "magnetic_transfer_validated": False,
                    "bond_process_validated": False,
                },
                "motion_reference": "CONTINUOUS_CONSERVATIVE_0_TO_HARD_STOP_WITH_OFF_AXIS_MAGNET_INCLUDED",
                "cost_rule": (
                    "DELETE_LOCAL_HALL_SUPPORT_PART; USE_SMALL_FPC_SENSOR_IN_SHELL_RECESS; "
                    "KEEP_CONTACTLESS_SENSING_OUTSIDE_MOVING_ENVELOPE"
                ),
                "tactile_quality_interpretation": (
                    "DIGITAL PRECURSOR ONLY: FULL BUTTON STROKE NO LONGER APPROACHES SENSOR ELECTRONICS OR A FLOATING SUPPORT, "
                    "REMOVING A HARD COLLISION_AND_INTERNAL_RATTLE_PATH. SENSOR_TRANSFER_AND_BOND_DURABILITY_REMAIN_UNVALIDATED."
                ),
                "physical_validation_eligible": False,
                "physical_validation": (
                    "OPEN_MAGNET_GRADE_FIELD_MAP_HALL_TRANSFER_MONOTONICITY_CALIBRATION_TEMPERATURE_FPC_BOND_"
                    "PEEL_CREEP_EMC_WET_DRY_INTEGRATION_FORCE_TRAVEL_GUIDE_FRICTION_WOBBLE_SOUND_LIFETIME_AND_SUBJECTIVE_FEEL"
                ),
            }
        )
        payload["material_parts"] = [name for name, _shape in self.material_parts]
        payload["reference_parts"] = [name for name, _shape in self.reference_parts]
        if include_sha:
            payload["architecture_sha256"] = self.architecture_sha256
        return payload


def build_primary_control_haptic_architecture_v8(
    *,
    model: MasckOneModel | None = None,
) -> PrimaryControlHapticArchitectureV8:
    model = build_model() if model is None else model
    base = v7.build_primary_control_haptic_architecture_v7(model=model)
    material = dict(base.material_parts)

    moving_with_axial_cavity = material["primary_control_cap_stem"]
    legacy_axial_magnet = material["sensor_magnet"]
    before_restore = float(moving_with_axial_cavity.Volume())
    moving_restored = moving_with_axial_cavity.fuse(legacy_axial_magnet).clean()
    restored_gain = float(moving_restored.Volume()) - before_restore
    if not moving_restored.isValid() or len(moving_restored.Solids()) != 1:
        raise PrimaryControlHapticV8Error("restoring obsolete axial cavity invalidated moving polymer")

    side_magnet = _side_magnet(base.rest_cap_underside_z_mm)
    before_side_cut = float(moving_restored.Volume())
    moving_side = moving_restored.cut(side_magnet).clean()
    side_removed = before_side_cut - float(moving_side.Volume())
    side_overlap = v1._intersection_volume(moving_side, side_magnet)
    if not moving_side.isValid() or len(moving_side.Solids()) != 1:
        raise PrimaryControlHapticV8Error("side magnet cavity invalidated moving polymer")

    side_sensor = _side_sensor_reference(base.rest_cap_underside_z_mm)
    recess = _sensor_recess(base.rest_cap_underside_z_mm)
    flex_cutter, flex_tail = _flex_channel_and_reference(base.rest_cap_underside_z_mm)

    shell_before = material["shell_with_primary_control_interface"]
    shell_volume_before = float(shell_before.Volume())
    shell_after_recess = shell_before.cut(recess).clean()
    recess_removed = shell_volume_before - float(shell_after_recess.Volume())
    before_flex = float(shell_after_recess.Volume())
    shell_after = shell_after_recess.cut(flex_cutter).clean()
    flex_removed = before_flex - float(shell_after.Volume())
    if not shell_after.isValid() or not shell_after.Solids():
        raise PrimaryControlHapticV8Error("side Hall shell packaging invalidated structural shell")

    motion = _continuous_motion_reference(base.rest_cap_underside_z_mm)
    sensor_motion_overlap = v1._intersection_volume(motion, side_sensor)
    flex_motion_overlap = v1._intersection_volume(motion, flex_tail)

    material_parts = _replace_material_parts(
        base.material_parts,
        shell=shell_after,
        moving=moving_side,
        magnet=side_magnet,
    )
    reference_parts = _replace_reference_parts(
        base.reference_parts,
        hall_sensor=side_sensor,
        flex_tail=flex_tail,
        motion=motion,
    )
    keepouts = _keepout_intersections(model, material_parts, reference_parts)

    side_magnet_cover = (
        v1.STEM_DIAMETER_MM / 2.0
        - (SIDE_MAGNET_CENTER_RADIUS_MM + SIDE_MAGNET_DIAMETER_MM / 2.0)
    )
    lower_z0 = (
        base.rest_cap_underside_z_mm
        - v1.LOWER_BUSHING_CENTER_FROM_REST_MM
        - v1.BUSHING_LENGTH_MM / 2.0
    )
    lower_guide_front_z = lower_z0 + v1.BUSHING_LENGTH_MM
    side_magnet_hard_rear_z = (
        base.rest_cap_underside_z_mm
        - SIDE_MAGNET_CENTER_FROM_REST_MM
        - SIDE_MAGNET_AXIAL_MM / 2.0
        - v1.HARD_STOP_MM
    )
    lower_guide_clearance = side_magnet_hard_rear_z - lower_guide_front_z

    recess_inner_radius = SENSOR_RECESS_CENTER_RADIUS_MM - SENSOR_RECESS_RADIAL_MM / 2.0
    recess_inner_ligament = recess_inner_radius - v1.BARREL_BORE_DIAMETER_MM / 2.0
    recess_outer_x = SENSOR_RECESS_CENTER_RADIUS_MM + SENSOR_RECESS_RADIAL_MM / 2.0
    recess_outer_corner_radius = math.hypot(recess_outer_x, SENSOR_RECESS_TANGENTIAL_MM / 2.0)
    recess_outer_cover = v1.BARREL_OD_MM / 2.0 - recess_outer_corner_radius

    result = PrimaryControlHapticArchitectureV8(
        SOURCE_MAIN_SHA,
        base.shell_outer_z_mm,
        base.rest_cap_underside_z_mm,
        material_parts,
        reference_parts,
        motion,
        base.joint_overlap_mm3,
        base.bushing_capture_removed_mm3,
        base.magnet_cavity_removed_mm3,
        base.magnet_polymer_intersection_mm3,
        base.leaf_root_shell_removed_mm3,
        base.leaf_shell_intersection_mm3,
        base.leaf_outer_polymer_cover_mm,
        base.landing_lock_slot_removed_mm3,
        base.landing_shell_intersection_mm3,
        base.rigid_stop_projected_area_fraction,
        base.lock_head_to_barrel_bore_clearance_mm,
        round(restored_gain, 9),
        round(side_removed, 9),
        round(side_overlap, 9),
        round(side_magnet_cover, 9),
        round(lower_guide_clearance, 9),
        round(recess_removed, 9),
        round(flex_removed, 9),
        round(sensor_motion_overlap, 9),
        round(flex_motion_overlap, 9),
        round(recess_inner_ligament, 9),
        round(recess_outer_cover, 9),
        keepouts,
        False,
    )
    result.__post_init__()
    return result


def export_primary_control_haptic_architecture_v8(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    architecture = build_primary_control_haptic_architecture_v8()
    for name, shape in architecture.material_parts:
        cq.exporters.export(shape, str(output_dir / f"{name}_MANUFACTURED.step"))
    for name, shape in architecture.reference_parts:
        cq.exporters.export(shape, str(output_dir / f"{name}_REFERENCE.step"))
    manifest = architecture.manifest()
    (output_dir / "primary_control_haptic_v8_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest
