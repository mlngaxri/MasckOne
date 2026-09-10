from __future__ import annotations

"""Primary-control V7: one mechanically locked progressive landing overmold.

The donor landing used three early pads plus a later annular bumper as separate
elastomer parts. Those bodies overlap in material space, creating an impossible
assembly and unnecessary part-count/alignment burden.

V7 replaces them with one continuous elastomer body. Three low-area pads remain the
early landing features and the annulus remains the later progressive stage, but all
are fused into one molded part. Three tangential undercut lock tabs pass through the
rigid hard-stop shelf and mechanically key the elastomer without adhesive or loose
retainers. A short local counterbore above the shelf clears the bumper envelope while
the rigid shelf itself remains the independent abuse stop.

Elastomer family, durometer, compression set, rate dependence, wet aging, molding
process and physical force/acoustic behavior remain PHYSICAL VALIDATION REQUIRED.
"""

from dataclasses import dataclass, field
import hashlib
import json
import math
from pathlib import Path

import cadquery as cq

from . import primary_control_haptic as v1
from . import primary_control_haptic_v6 as v6
from .model import MasckOneModel, build_model

SCHEMA = "MASCK_ONE_PRIMARY_CONTROL_HAPTIC_V7"
SOURCE_MAIN_SHA = v6.SOURCE_MAIN_SHA

LANDING_PAD_RADIUS_MM = 4.05
LANDING_PAD_RADIAL_MM = 1.20
LANDING_PAD_TANGENTIAL_MM = 0.72
LANDING_ANNULUS_OD_MM = 9.00
LANDING_ANNULUS_ID_MM = 7.72

LANDING_LOCK_RADIUS_MM = 4.05
LANDING_LOCK_HEAD_RADIUS_MM = 4.00
LANDING_LOCK_SLOT_RADIAL_MM = 0.30
LANDING_LOCK_SLOT_TANGENTIAL_MM = 0.52
LANDING_LOCK_STEM_RADIAL_MM = 0.22
LANDING_LOCK_STEM_TANGENTIAL_MM = 0.40
LANDING_LOCK_HEAD_RADIAL_MM = 0.30
LANDING_LOCK_HEAD_TANGENTIAL_MM = 0.78
LANDING_LOCK_HEAD_HEIGHT_MM = 0.16
LANDING_LOCK_STEM_SHELF_OVERLAP_MM = 0.02
LANDING_LOCK_COUNT = 3
LOCK_AZIMUTHS_DEG = (0.0, 120.0, 240.0)

LANDING_CLEARANCE_RADIAL_MM = 0.03
_LANDING_PAD_OUTER_CORNER_RADIUS_MM = math.hypot(
    LANDING_PAD_RADIUS_MM + LANDING_PAD_RADIAL_MM / 2.0,
    LANDING_PAD_TANGENTIAL_MM / 2.0,
)
LANDING_CLEARANCE_BORE_RADIUS_MM = (
    max(LANDING_ANNULUS_OD_MM / 2.0, _LANDING_PAD_OUTER_CORNER_RADIUS_MM)
    + LANDING_CLEARANCE_RADIAL_MM
)
LANDING_CLEARANCE_BORE_DIAMETER_MM = 2.0 * LANDING_CLEARANCE_BORE_RADIUS_MM
LANDING_CLEARANCE_HEIGHT_MM = v1.FIRST_BUMPER_HEIGHT_MM + 0.03
LANDING_BARREL_WALL_REMAINING_MM = (
    v1.BARREL_OD_MM / 2.0 - LANDING_CLEARANCE_BORE_RADIUS_MM
)
MIN_LANDING_BARREL_WALL_MM = 1.20
if LANDING_BARREL_WALL_REMAINING_MM < MIN_LANDING_BARREL_WALL_MM:
    raise ValueError("landing clearance counterbore leaves insufficient barrel wall")

MIN_RIGID_STOP_PROJECTED_AREA_FRACTION = 0.97
MIN_LOCK_HEAD_TO_BARREL_BORE_RADIAL_CLEARANCE_MM = 0.04
_INTERSECTION_TOLERANCE_MM3 = 1e-7


class PrimaryControlHapticV7Error(ValueError):
    pass


def _oriented_box(
    radial_mm: float,
    tangential_mm: float,
    axial_mm: float,
    *,
    radius_mm: float,
    azimuth_deg: float,
    z_center_mm: float,
) -> cq.Shape:
    # Create on the +X radial axis first, then rotate both position and local axes
    # together. The previous implementation pre-positioned at azimuth and then
    # rotated again, so the box centre advanced to 2*azimuth while its orientation
    # advanced only once. That broke the intended radial/tangential lock geometry.
    shape = v1._box(
        radial_mm,
        tangential_mm,
        axial_mm,
        (
            v1.MOUNT_X_MM + radius_mm,
            v1.MOUNT_Y_MM,
            z_center_mm,
        ),
    )
    return shape.rotate(
        (v1.MOUNT_X_MM, v1.MOUNT_Y_MM, z_center_mm),
        (v1.MOUNT_X_MM, v1.MOUNT_Y_MM, z_center_mm + 1.0),
        azimuth_deg,
    )


def _progressive_landing(rest_z: float) -> cq.Shape:
    shelf_top = rest_z - v1.HARD_STOP_MM
    landing = v1._ring(
        LANDING_ANNULUS_OD_MM,
        LANDING_ANNULUS_ID_MM,
        v1.SECOND_BUMPER_HEIGHT_MM,
        shelf_top,
    )

    for azimuth_deg in LOCK_AZIMUTHS_DEG:
        pad = _oriented_box(
            LANDING_PAD_RADIAL_MM,
            LANDING_PAD_TANGENTIAL_MM,
            v1.FIRST_BUMPER_HEIGHT_MM,
            radius_mm=LANDING_PAD_RADIUS_MM,
            azimuth_deg=azimuth_deg,
            z_center_mm=shelf_top + v1.FIRST_BUMPER_HEIGHT_MM / 2.0,
        )
        landing = landing.fuse(pad)

        stem_height = v1.HARD_STOP_SHELF_THICKNESS_MM + 2.0 * LANDING_LOCK_STEM_SHELF_OVERLAP_MM
        stem = _oriented_box(
            LANDING_LOCK_STEM_RADIAL_MM,
            LANDING_LOCK_STEM_TANGENTIAL_MM,
            stem_height,
            radius_mm=LANDING_LOCK_RADIUS_MM,
            azimuth_deg=azimuth_deg,
            z_center_mm=(
                shelf_top
                - v1.HARD_STOP_SHELF_THICKNESS_MM / 2.0
            ),
        )
        head = _oriented_box(
            LANDING_LOCK_HEAD_RADIAL_MM,
            LANDING_LOCK_HEAD_TANGENTIAL_MM,
            LANDING_LOCK_HEAD_HEIGHT_MM,
            radius_mm=LANDING_LOCK_HEAD_RADIUS_MM,
            azimuth_deg=azimuth_deg,
            z_center_mm=(
                shelf_top
                - v1.HARD_STOP_SHELF_THICKNESS_MM
                - LANDING_LOCK_HEAD_HEIGHT_MM / 2.0
            ),
        )
        landing = landing.fuse(stem).fuse(head)

    landing = landing.clean()
    if not landing.isValid() or len(landing.Solids()) != 1 or landing.Volume() <= 0.0:
        raise PrimaryControlHapticV7Error("progressive landing must be one connected elastomer body")
    return landing


def _cut_landing_clearance(shell: cq.Shape, rest_z: float) -> cq.Shape:
    """Clear only the elastomer envelope above the independent hard-stop shelf."""
    shelf_top = rest_z - v1.HARD_STOP_MM
    cutter = v1._cylinder(
        LANDING_CLEARANCE_BORE_DIAMETER_MM,
        LANDING_CLEARANCE_HEIGHT_MM,
        shelf_top,
    )
    before = float(shell.Volume())
    cleared = shell.cut(cutter).clean()
    removed = before - float(cleared.Volume())
    if not cleared.isValid() or not cleared.Solids() or removed <= 0.0:
        raise PrimaryControlHapticV7Error("landing clearance counterbore must remove positive barrel material")
    return cleared


def _cut_lock_slots(shell: cq.Shape, rest_z: float) -> tuple[cq.Shape, float]:
    shelf_top = rest_z - v1.HARD_STOP_MM
    before = float(shell.Volume())
    cutter_height = v1.HARD_STOP_SHELF_THICKNESS_MM + 0.04
    for azimuth_deg in LOCK_AZIMUTHS_DEG:
        cutter = _oriented_box(
            LANDING_LOCK_SLOT_RADIAL_MM,
            LANDING_LOCK_SLOT_TANGENTIAL_MM,
            cutter_height,
            radius_mm=LANDING_LOCK_RADIUS_MM,
            azimuth_deg=azimuth_deg,
            z_center_mm=shelf_top - v1.HARD_STOP_SHELF_THICKNESS_MM / 2.0,
        )
        shell = shell.cut(cutter).clean()
    removed = before - float(shell.Volume())
    if not shell.isValid() or not shell.Solids() or removed <= 0.0:
        raise PrimaryControlHapticV7Error("landing lock slots must remove positive shelf material")
    return shell, removed


def _replace_landing_parts(
    parts: tuple[tuple[str, cq.Shape], ...],
    *,
    shell: cq.Shape,
    landing: cq.Shape,
) -> tuple[tuple[str, cq.Shape], ...]:
    output: list[tuple[str, cq.Shape]] = []
    saw_shell = False
    saw_stage1 = False
    saw_stage2 = False
    for name, shape in parts:
        if name == "shell_with_primary_control_interface":
            output.append((name, shell))
            saw_shell = True
        elif name == "landing_stage_1":
            output.append(("landing_progressive_overmold", landing))
            saw_stage1 = True
        elif name == "landing_stage_2":
            saw_stage2 = True
        else:
            output.append((name, shape))
    if not (saw_shell and saw_stage1 and saw_stage2):
        raise PrimaryControlHapticV7Error("V7 requires donor shell and both landing stages")
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
            references["hall_sensor_envelope"],
            material["hall_pcb_support"],
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
class PrimaryControlHapticArchitectureV7:
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
    keepout_intersections_mm3: dict[str, float] = field(default_factory=dict)
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        if self.source_main_sha != SOURCE_MAIN_SHA:
            raise PrimaryControlHapticV7Error("V7 source-main mismatch")
        if self.physical_validation_eligible:
            raise PrimaryControlHapticV7Error("digital landing geometry is not physical validation")

        # Re-run every inherited V6 structural/capture invariant on the V7 parts.
        v6.PrimaryControlHapticArchitectureV6(
            self.source_main_sha,
            self.shell_outer_z_mm,
            self.rest_cap_underside_z_mm,
            self.material_parts,
            self.reference_parts,
            self.motion_sweep,
            self.joint_overlap_mm3,
            self.bushing_capture_removed_mm3,
            self.magnet_cavity_removed_mm3,
            self.magnet_polymer_intersection_mm3,
            self.leaf_root_shell_removed_mm3,
            self.leaf_shell_intersection_mm3,
            self.leaf_outer_polymer_cover_mm,
            self.keepout_intersections_mm3,
            False,
        ).__post_init__()

        material = dict(self.material_parts)
        names = set(material)
        if "landing_stage_1" in names or "landing_stage_2" in names:
            raise PrimaryControlHapticV7Error("superseded overlapping landing parts cannot remain")
        landing = material["landing_progressive_overmold"]
        shell = material["shell_with_primary_control_interface"]
        if not landing.isValid() or len(landing.Solids()) != 1 or landing.Volume() <= 0.0:
            raise PrimaryControlHapticV7Error("landing overmold must be one valid positive solid")
        if not shell.isValid() or not shell.Solids() or shell.Volume() <= 0.0:
            raise PrimaryControlHapticV7Error("landing lock slots must preserve valid structural shell")
        if self.landing_lock_slot_removed_mm3 <= 0.0:
            raise PrimaryControlHapticV7Error("mechanical landing locks require positive shelf slots")
        if self.landing_shell_intersection_mm3 > _INTERSECTION_TOLERANCE_MM3:
            raise PrimaryControlHapticV7Error("landing elastomer cannot occupy rigid shell material")
        if self.rigid_stop_projected_area_fraction < MIN_RIGID_STOP_PROJECTED_AREA_FRACTION:
            raise PrimaryControlHapticV7Error("landing locks remove too much rigid hard-stop projected area")
        if self.lock_head_to_barrel_bore_clearance_mm < MIN_LOCK_HEAD_TO_BARREL_BORE_RADIAL_CLEARANCE_MM:
            raise PrimaryControlHapticV7Error("landing lock head lacks full-corner radial clearance inside barrel bore")
        if any(value > _INTERSECTION_TOLERANCE_MM3 for value in self.keepout_intersections_mm3.values()):
            raise PrimaryControlHapticV7Error("V7 primary control intersects a protected package/visual keepout")

    @property
    def architecture_sha256(self) -> str:
        payload = json.dumps(self.manifest(False), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        return hashlib.sha256(payload).hexdigest()

    def manifest(self, include_sha: bool = True) -> dict[str, object]:
        payload = v6.PrimaryControlHapticArchitectureV6(
            self.source_main_sha,
            self.shell_outer_z_mm,
            self.rest_cap_underside_z_mm,
            self.material_parts,
            self.reference_parts,
            self.motion_sweep,
            self.joint_overlap_mm3,
            self.bushing_capture_removed_mm3,
            self.magnet_cavity_removed_mm3,
            self.magnet_polymer_intersection_mm3,
            self.leaf_root_shell_removed_mm3,
            self.leaf_shell_intersection_mm3,
            self.leaf_outer_polymer_cover_mm,
            self.keepout_intersections_mm3,
            False,
        ).manifest(False)
        payload.update(
            {
                "schema": SCHEMA,
                "supersedes": "V6_OVERLAPPING_TWO_PART_LANDING_STACK_WITHOUT_POSITIVE_RETENTION",
                "landing": {
                    "architecture": "ONE_PIECE_PROGRESSIVE_ELASTOMER_OVERMOLD_WITH_THREE_TANGENTIAL_UNDERCUT_LOCKS",
                    "first_stage": "THREE_LOW_AREA_PADS",
                    "second_stage": "CONTINUOUS_ANNULUS",
                    "first_landing_start_mm": v1.FIRST_LANDING_START_MM,
                    "second_landing_start_mm": v1.SECOND_LANDING_START_MM,
                    "nominal_bottom_mm": v1.NOMINAL_BOTTOM_MM,
                    "rigid_hard_stop_mm": v1.HARD_STOP_MM,
                    "landing_clearance_bore_diameter_mm": LANDING_CLEARANCE_BORE_DIAMETER_MM,
                    "landing_clearance_radial_mm": LANDING_CLEARANCE_RADIAL_MM,
                    "landing_barrel_wall_remaining_mm": LANDING_BARREL_WALL_REMAINING_MM,
                    "hard_stop_shelf_removed_by_clearance_counterbore": False,
                    "lock_count": LANDING_LOCK_COUNT,
                    "lock_slot_radial_mm": LANDING_LOCK_SLOT_RADIAL_MM,
                    "lock_slot_tangential_mm": LANDING_LOCK_SLOT_TANGENTIAL_MM,
                    "lock_head_radius_mm": LANDING_LOCK_HEAD_RADIUS_MM,
                    "lock_head_radial_mm": LANDING_LOCK_HEAD_RADIAL_MM,
                    "lock_head_tangential_mm": LANDING_LOCK_HEAD_TANGENTIAL_MM,
                    "lock_slot_removed_mm3": self.landing_lock_slot_removed_mm3,
                    "landing_shell_intersection_mm3": self.landing_shell_intersection_mm3,
                    "rigid_stop_projected_area_fraction_remaining": self.rigid_stop_projected_area_fraction,
                    "lock_head_to_barrel_bore_clearance_mm": self.lock_head_to_barrel_bore_clearance_mm,
                    "separate_elastomer_landing_parts": 1,
                    "separate_fasteners": 0,
                    "adhesive_required": False,
                    "durometer_validated": False,
                    "compression_set_validated": False,
                },
                "cost_rule": (
                    "ONE_MOLDED_LANDING_BODY; ZERO_ADHESIVE; ZERO_LOOSE_BUMPER_RETENTION; "
                    "LOCAL_COUNTERBORE_ONLY_WHERE_ELASTOMER_NEEDS_CLEARANCE; PRESERVE_INDEPENDENT_RIGID_ABUSE_STOP"
                ),
                "tactile_quality_interpretation": (
                    "DIGITAL PRECURSOR ONLY: EARLY LOCAL PAD CONTACT AND LATER ANNULAR ENGAGEMENT ARE GEOMETRICALLY "
                    "SEQUENCED WITHOUT DUPLICATE MATERIAL OR LOOSE RETAINERS. ACTUAL FORCE_RATE_HYSTERESIS_SOUND_AND_FEEL_REQUIRE_COUPONS."
                ),
                "physical_validation_eligible": False,
                "physical_validation": (
                    "OPEN_ELASTOMER_FAMILY_DUROMETER_RATE_COMPRESSION_SET_WET_AGING_MOLDING_TOLERANCE_FORCE_TRAVEL_"
                    "RETURN_HYSTERESIS_ACOUSTIC_SPECTRUM_RING_DECAY_GUIDE_FRICTION_WOBBLE_SEALING_LIFETIME_AND_SUBJECTIVE_FEEL"
                ),
            }
        )
        payload["material_parts"] = [name for name, _shape in self.material_parts]
        if include_sha:
            payload["architecture_sha256"] = self.architecture_sha256
        return payload


def build_primary_control_haptic_architecture_v7(
    *,
    model: MasckOneModel | None = None,
) -> PrimaryControlHapticArchitectureV7:
    model = build_model() if model is None else model
    base = v6.build_primary_control_haptic_architecture_v6(model=model)
    material = dict(base.material_parts)

    landing = _progressive_landing(base.rest_cap_underside_z_mm)
    shell_before = material["shell_with_primary_control_interface"]
    shell_cleared = _cut_landing_clearance(shell_before, base.rest_cap_underside_z_mm)
    shell_after, slot_removed = _cut_lock_slots(shell_cleared, base.rest_cap_underside_z_mm)
    landing_shell_overlap = v1._intersection_volume(shell_after, landing)

    material_parts = _replace_landing_parts(
        base.material_parts,
        shell=shell_after,
        landing=landing,
    )
    keepouts = _keepout_intersections(model, material_parts, base.reference_parts)

    stop_outer_radius = v1.HARD_STOP_OUTER_DIAMETER_MM / 2.0
    stop_inner_radius = v1.HARD_STOP_INNER_DIAMETER_MM / 2.0
    stop_area = math.pi * (stop_outer_radius**2 - stop_inner_radius**2)
    slot_area = LANDING_LOCK_COUNT * LANDING_LOCK_SLOT_RADIAL_MM * LANDING_LOCK_SLOT_TANGENTIAL_MM
    remaining_stop_fraction = (stop_area - slot_area) / stop_area
    lock_head_outer_corner_radius = math.hypot(
        LANDING_LOCK_HEAD_RADIUS_MM + LANDING_LOCK_HEAD_RADIAL_MM / 2.0,
        LANDING_LOCK_HEAD_TANGENTIAL_MM / 2.0,
    )
    lock_clearance = v1.BARREL_BORE_DIAMETER_MM / 2.0 - lock_head_outer_corner_radius

    result = PrimaryControlHapticArchitectureV7(
        SOURCE_MAIN_SHA,
        base.shell_outer_z_mm,
        base.rest_cap_underside_z_mm,
        material_parts,
        base.reference_parts,
        base.motion_sweep,
        base.joint_overlap_mm3,
        base.bushing_capture_removed_mm3,
        base.magnet_cavity_removed_mm3,
        base.magnet_polymer_intersection_mm3,
        base.leaf_root_shell_removed_mm3,
        base.leaf_shell_intersection_mm3,
        base.leaf_outer_polymer_cover_mm,
        round(slot_removed, 9),
        round(landing_shell_overlap, 9),
        round(remaining_stop_fraction, 9),
        round(lock_clearance, 9),
        keepouts,
        False,
    )
    result.__post_init__()
    return result


def export_primary_control_haptic_architecture_v7(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    architecture = build_primary_control_haptic_architecture_v7()
    for name, shape in architecture.material_parts:
        cq.exporters.export(shape, str(output_dir / f"{name}_MANUFACTURED.step"))
    for name, shape in architecture.reference_parts:
        cq.exporters.export(shape, str(output_dir / f"{name}_REFERENCE.step"))
    manifest = architecture.manifest()
    (output_dir / "primary_control_haptic_v7_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest