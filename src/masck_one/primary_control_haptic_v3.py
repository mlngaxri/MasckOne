from __future__ import annotations

"""Current-main primary-control candidate with physically connected moving geometry.

V3 preserves the V2 interaction architecture and continuous press reference while
repairing a hidden manufacturing defect in the moving polymer part. The donor cap,
stem and anti-rotation rib met only at zero-volume boundaries. This version creates
explicit positive material overlap at both joints without changing the visible cap
or the intended external rib projection.

The S.T. Dupont Ligne 2 is used only as a reference for perceived mechanical
precision. Its sound, mechanism, materials and styling are not reproduced. Premium
feel remains a physical-validation target, not a digital claim.
"""

from dataclasses import dataclass, field
import hashlib
import json
import math
from pathlib import Path

import cadquery as cq

from . import primary_control_haptic as v1
from .primary_control_haptic_v2 import _continuous_press_reference
from .model import MasckOneModel, build_model

SCHEMA = "MASCK_ONE_PRIMARY_CONTROL_HAPTIC_V3"
SOURCE_MAIN_SHA = "ac59fcd59f50b019cb972bfc526c2daea784bd17"
DONOR_V2_HEAD_SHA = "5c2b5f030f8d205e108a828fed53d43293f518f4"
CAP_STEM_ROOT_OVERLAP_MM = 0.08
RIB_STEM_ROOT_OVERLAP_MM = 0.12
MIN_CONNECTED_OVERLAP_MM3 = 0.20
LEGACY_TACTILE_BEAM_ROOT_OVERLAP_MM = 0.10
_INTERSECTION_TOLERANCE_MM3 = 1e-7


class PrimaryControlHapticV3Error(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class PrimaryControlHapticArchitectureV3:
    source_main_sha: str
    shell_outer_z_mm: float
    rest_cap_underside_z_mm: float
    material_parts: tuple[tuple[str, cq.Shape], ...] = field(repr=False, compare=False)
    reference_parts: tuple[tuple[str, cq.Shape], ...] = field(repr=False, compare=False)
    motion_sweep: cq.Shape = field(repr=False, compare=False)
    joint_overlap_mm3: dict[str, float] = field(default_factory=dict)
    keepout_intersections_mm3: dict[str, float] = field(default_factory=dict)
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        if self.source_main_sha != SOURCE_MAIN_SHA:
            raise PrimaryControlHapticV3Error("primary-control V3 source-main mismatch")
        if self.physical_validation_eligible:
            raise PrimaryControlHapticV3Error("digital button CAD is not physical validation")
        if self.joint_overlap_mm3.get("cap_to_stem", 0.0) < MIN_CONNECTED_OVERLAP_MM3:
            raise PrimaryControlHapticV3Error("cap-to-stem joint lacks positive material overlap")
        if self.joint_overlap_mm3.get("stem_to_anti_rotation_rib", 0.0) < MIN_CONNECTED_OVERLAP_MM3:
            raise PrimaryControlHapticV3Error("stem-to-rib joint lacks positive material overlap")
        for name, shape in self.material_parts:
            if not shape.isValid() or not shape.Solids() or float(shape.Volume()) <= 0.0:
                raise PrimaryControlHapticV3Error(f"{name} must be valid positive material")
            if name == "primary_control_cap_stem" and len(shape.Solids()) != 1:
                raise PrimaryControlHapticV3Error("primary-control cap/stem/rib must be one manufactured solid")
        if any(value > _INTERSECTION_TOLERANCE_MM3 for value in self.keepout_intersections_mm3.values()):
            raise PrimaryControlHapticV3Error("primary control intersects a protected package/visual keepout")

    @property
    def architecture_sha256(self) -> str:
        payload = json.dumps(self.manifest(False), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        return hashlib.sha256(payload).hexdigest()

    def manifest(self, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "source_main_sha": self.source_main_sha,
            "donor_v2_head_sha": DONOR_V2_HEAD_SHA,
            "coordinate_frame_id": v1.WORLD_FRAME_ID,
            "location_world_mm": [v1.MOUNT_X_MM, v1.MOUNT_Y_MM, self.shell_outer_z_mm],
            "button_axis_world_unit": list(v1.AXIS_WORLD),
            "rest_cap_underside_z_mm": self.rest_cap_underside_z_mm,
            "supersedes": "V2_ZERO_VOLUME_CAP_STEM_AND_STEM_RIB_JOINTS",
            "selected_mechanism": (
                "DUAL_SPLIT_BEARING_GUIDANCE_PLUS_KEYED_SIDE_PRELOAD_PLUS_DAMPED_FORMED_TACTILE_FLEXURE_"
                "PLUS_TWO_STAGE_ELASTOMER_LANDING_PLUS_INDEPENDENT_HARD_STOP_PLUS_HALL_SENSING"
            ),
            "tactile_reference_rule": (
                "S_T_DUPONT_LIGNE_2_CLASS_PRECISION_OBJECT_FEEL_ONLY; REPLICATE_CONTROLLED_GUIDANCE_LOW_PLAY_"
                "DELIBERATE_RESISTANCE_DECISIVE_STATE_CHANGE_POSITIVE_SEATING_AND_CONTROLLED_RETURN; "
                "DO_NOT_REPLICATE_SOUND_MECHANISM_MATERIALS_OR_STYLING"
            ),
            "cost_rule": (
                "PREMIUM_PERCEIVED_MECHANICS_BY_GEOMETRY_PRELOAD_CONSTRAINT_DAMPING_AND_SELECTIVE_MATERIAL_"
                "PLACEMENT; HIDDEN_PARTS_COST_OPTIMIZED; USER_TOUCH_SURFACES_MAY_RECEIVE_PREMIUM_MATERIAL_FINISH"
            ),
            "sound_rule": "SECONDARY; NO INTENTIONAL_LIGHTER_PING; PREVENT_RATTLE_CLACK_SCRAPE_TWANG_AND_HOLLOW_SHELL_RESPONSE",
            "moving_part_connectivity": {
                "cap_stem_root_overlap_mm": CAP_STEM_ROOT_OVERLAP_MM,
                "rib_stem_root_overlap_mm": RIB_STEM_ROOT_OVERLAP_MM,
                "joint_overlap_mm3": self.joint_overlap_mm3,
                "visible_cap_geometry_changed": False,
                "external_rib_projection_changed": False,
            },
            "travel_events_mm": {
                "first_landing": v1.FIRST_LANDING_START_MM,
                "second_landing": v1.SECOND_LANDING_START_MM,
                "nominal_bottom": v1.NOMINAL_BOTTOM_MM,
                "hard_stop": v1.HARD_STOP_MM,
            },
            "guidance": {
                "stem_diameter_mm": v1.STEM_DIAMETER_MM,
                "bushing_span_mm": v1.BUSHING_SPAN_MM,
                "free_bushing_id_mm": v1.BUSHING_ID_FREE_MM,
                "installed_reference_id_mm": v1.BUSHING_ID_INSTALLED_MM,
                "anti_rotation_rib_external_projection_mm": v1.ANTI_ROTATION_RIB_RADIAL_MM,
                "anti_rotation_leaf_preload_seed_mm": v1.ANTI_ROTATION_LEAF_PRELOAD_SEED_MM,
            },
            "material_parts": [name for name, _shape in self.material_parts],
            "reference_parts": [name for name, _shape in self.reference_parts],
            "keepout_intersections_mm3": self.keepout_intersections_mm3,
            "fusion_handoff": {
                "cad_platform": "AUTODESK_FUSION_360",
                "grounded_component": "shell_with_primary_control_interface",
                "button_slider_dof": f"TRANSLATION_-Z_0_TO_{v1.HARD_STOP_MM:.2f}_MM",
                "continuous_motion_reference": True,
                "moving_component": "primary_control_cap_stem",
                "compliant_parts": [
                    "tactile_spring_formed",
                    "anti_rotation_preload_leaf_free",
                    "wet_diaphragm",
                    "landing_stage_1",
                    "landing_stage_2",
                ],
            },
            "physical_validation_eligible": False,
            "physical_validation": (
                "OPEN_FORCE_TRAVEL_NONLINEAR_SNAP_GUIDE_FRICTION_WOBBLE_SEAL_LEAKAGE_BUMPER_RATE_FATIGUE_"
                "TEMPERATURE_AGING_SENSOR_RETENTION_SENSOR_TRANSFER_SOUND_LIFETIME_ASSEMBLY_TOLERANCE_AND_SUBJECTIVE_FEEL"
            ),
        }
        if include_sha:
            payload["architecture_sha256"] = self.architecture_sha256
        return payload


def _positive_overlap(a: cq.Shape, b: cq.Shape, name: str) -> float:
    value = float(v1._intersection_volume(a, b))
    if not math.isfinite(value) or value < MIN_CONNECTED_OVERLAP_MM3:
        raise PrimaryControlHapticV3Error(f"{name} overlap is insufficient: {value}")
    return value


def _legacy_connected_tactile_spring(rim_z: float) -> cq.Shape:
    """Make the historical V1 spring executable without changing its selected status.

    V1 rotated each beam about the button axis, which also translated its Z datum and
    left the beam floating between the centre disk and reaction ring. The historical
    package is rebuilt with the same ring, centre disk, thickness, width and preform
    rise, but each beam is oriented about its own midpoint and rooted 0.10 mm into both
    adjacent solids. V9 and later still remove this spring from selected material.
    """
    ring = v1._ring(
        v1.TACTILE_SPRING_OD_MM,
        v1.TACTILE_RING_ID_MM,
        v1.TACTILE_SPRING_THICKNESS_MM,
        rim_z,
    )
    center_z = rim_z + v1.TACTILE_PREFORM_RISE_MM
    center = v1._cylinder(
        v1.TACTILE_CENTER_DIAMETER_MM,
        v1.TACTILE_SPRING_THICKNESS_MM,
        center_z,
    )

    center_radius = v1.TACTILE_CENTER_DIAMETER_MM / 2.0
    ring_inner = v1.TACTILE_RING_ID_MM / 2.0
    beam_inner_x = center_radius - LEGACY_TACTILE_BEAM_ROOT_OVERLAP_MM
    beam_outer_x = ring_inner + LEGACY_TACTILE_BEAM_ROOT_OVERLAP_MM
    inner_z = center_z + v1.TACTILE_SPRING_THICKNESS_MM / 2.0
    outer_z = rim_z + v1.TACTILE_SPRING_THICKNESS_MM / 2.0
    dx = beam_outer_x - beam_inner_x
    dz = outer_z - inner_z
    beam_length = math.hypot(dx, dz)
    beam_angle = math.degrees(math.atan2(-dz, dx))
    beam_center_radius = (beam_inner_x + beam_outer_x) / 2.0
    beam_center_z = (inner_z + outer_z) / 2.0

    beams: list[cq.Shape] = []
    for azimuth in (0.0, 90.0, 180.0, 270.0):
        beam = v1._box(
            beam_length,
            v1.TACTILE_BEAM_WIDTH_MM,
            v1.TACTILE_SPRING_THICKNESS_MM,
            (
                v1.MOUNT_X_MM + beam_center_radius,
                v1.MOUNT_Y_MM,
                beam_center_z,
            ),
        )
        beam = beam.rotate(
            (
                v1.MOUNT_X_MM + beam_center_radius,
                v1.MOUNT_Y_MM,
                beam_center_z,
            ),
            (
                v1.MOUNT_X_MM + beam_center_radius,
                v1.MOUNT_Y_MM + 1.0,
                beam_center_z,
            ),
            beam_angle,
        )
        beam = beam.rotate(
            (v1.MOUNT_X_MM, v1.MOUNT_Y_MM, beam_center_z),
            (v1.MOUNT_X_MM, v1.MOUNT_Y_MM, beam_center_z + 1.0),
            azimuth,
        )
        beams.append(beam)

    result = ring
    for beam in beams:
        if v1._intersection_volume(beam, ring) <= 0.0 and v1._intersection_volume(beam, center) <= 0.0:
            raise PrimaryControlHapticV3Error("historical tactile beam lost both positive roots")
        result = result.fuse(beam)
    result = result.fuse(center).clean()
    if not result.isValid() or len(result.Solids()) != 1 or float(result.Volume()) <= 0.0:
        raise PrimaryControlHapticV3Error("historical tactile spring execution repair is not one connected solid")
    return result


def build_primary_control_haptic_architecture_v3(
    *,
    model: MasckOneModel | None = None,
) -> PrimaryControlHapticArchitectureV3:
    model = build_model() if model is None else model
    outer_z = v1._shell_outer_z(model)
    rest_z = outer_z + v1.CAP_PROUD_MM
    top_z = rest_z + v1.CAP_THICKNESS_MM

    shell_interface = v1._build_shell_interface(model, outer_z, rest_z)

    cap = v1._cylinder(v1.CAP_DIAMETER_MM, v1.CAP_THICKNESS_MM, rest_z)
    cap = v1._dish_cap(cap, top_z)
    core_z0 = rest_z + (v1.CAP_THICKNESS_MM - v1.INERTIA_CORE_THICKNESS_MM) / 2.0
    core = v1._cylinder(v1.INERTIA_CORE_DIAMETER_MM, v1.INERTIA_CORE_THICKNESS_MM, core_z0)
    cap = cap.cut(core)

    # Preserve the stem's rear datum while extending its front root into the cap.
    stem = v1._cylinder(
        v1.STEM_DIAMETER_MM,
        v1.STEM_LENGTH_MM + CAP_STEM_ROOT_OVERLAP_MM,
        rest_z - v1.STEM_LENGTH_MM,
    )

    # Preserve the donor's external rib projection while moving material inward
    # across the stem wall. The previous rib began exactly at the stem tangent.
    rib_body_radial_mm = v1.ANTI_ROTATION_RIB_RADIAL_MM + RIB_STEM_ROOT_OVERLAP_MM
    rib_center_x = (
        v1.MOUNT_X_MM
        + v1.STEM_DIAMETER_MM / 2.0
        + (v1.ANTI_ROTATION_RIB_RADIAL_MM - RIB_STEM_ROOT_OVERLAP_MM) / 2.0
    )
    rib = v1._box(
        rib_body_radial_mm,
        v1.ANTI_ROTATION_RIB_WIDTH_MM,
        v1.STEM_LENGTH_MM - 0.35,
        (
            rib_center_x,
            v1.MOUNT_Y_MM,
            rest_z - (v1.STEM_LENGTH_MM - 0.35) / 2.0 - 0.18,
        ),
    )

    joint_overlap = {
        "cap_to_stem": round(_positive_overlap(cap, stem, "cap-to-stem"), 9),
        "stem_to_anti_rotation_rib": round(_positive_overlap(stem, rib, "stem-to-rib"), 9),
    }

    cap_stem = cap.fuse(stem).fuse(rib)
    cap_stem = cap_stem.cut(v1._m_cut_grooves(top_z)).clean()
    if not cap_stem.isValid() or len(cap_stem.Solids()) != 1:
        raise PrimaryControlHapticV3Error("cap/stem/rib must resolve to one valid manufactured solid")

    upper_z0 = rest_z - v1.UPPER_BUSHING_CENTER_FROM_REST_MM - v1.BUSHING_LENGTH_MM / 2.0
    lower_z0 = rest_z - v1.LOWER_BUSHING_CENTER_FROM_REST_MM - v1.BUSHING_LENGTH_MM / 2.0
    upper_bushing_free = v1._split_ring(v1.BUSHING_OD_FREE_MM, v1.BUSHING_ID_FREE_MM, v1.BUSHING_LENGTH_MM, upper_z0, v1.BUSHING_SPLIT_GAP_MM)
    lower_bushing_free = v1._split_ring(v1.BUSHING_OD_FREE_MM, v1.BUSHING_ID_FREE_MM, v1.BUSHING_LENGTH_MM, lower_z0, v1.BUSHING_SPLIT_GAP_MM)
    upper_bushing_installed = v1._split_ring(v1.BUSHING_OD_INSTALLED_MM, v1.BUSHING_ID_INSTALLED_MM, v1.BUSHING_LENGTH_MM, upper_z0, v1.ANTI_ROTATION_SLOT_WIDTH_MM)
    lower_bushing_installed = v1._split_ring(v1.BUSHING_OD_INSTALLED_MM, v1.BUSHING_ID_INSTALLED_MM, v1.BUSHING_LENGTH_MM, lower_z0, v1.ANTI_ROTATION_SLOT_WIDTH_MM)

    leaf_center_z = rest_z - 2.55
    leaf_x = v1.MOUNT_X_MM + v1.BARREL_BORE_DIAMETER_MM / 2.0 - 0.18
    leaf_free = v1._box(
        0.34,
        v1.ANTI_ROTATION_LEAF_THICKNESS_MM,
        v1.ANTI_ROTATION_LEAF_LENGTH_MM,
        (
            leaf_x,
            v1.MOUNT_Y_MM + v1.ANTI_ROTATION_SLOT_WIDTH_MM / 2.0 - v1.ANTI_ROTATION_LEAF_THICKNESS_MM / 2.0 - v1.ANTI_ROTATION_LEAF_PRELOAD_SEED_MM,
            leaf_center_z,
        ),
    )
    leaf_installed = leaf_free.translate((0.0, v1.ANTI_ROTATION_LEAF_PRELOAD_SEED_MM, 0.0))

    diaphragm_z = rest_z - 0.16
    membrane = v1._ring(v1.DIAPHRAGM_OD_MM, v1.DIAPHRAGM_ID_MM, v1.DIAPHRAGM_MEMBRANE_THICKNESS_MM, diaphragm_z)
    outer_bead = v1._ring(v1.DIAPHRAGM_OD_MM + 0.30, v1.DIAPHRAGM_OD_MM - 0.45, v1.DIAPHRAGM_BEAD_THICKNESS_MM, diaphragm_z - 0.11)
    inner_bead = v1._ring(v1.DIAPHRAGM_ID_MM + 0.48, v1.DIAPHRAGM_ID_MM - 0.20, v1.DIAPHRAGM_BEAD_THICKNESS_MM, diaphragm_z - 0.11)
    diaphragm = membrane.fuse(outer_bead).fuse(inner_bead).clean()

    spring_rim_z = rest_z - v1.TACTILE_RIM_FROM_REST_MM
    tactile_spring = _legacy_connected_tactile_spring(spring_rim_z)
    damping = v1._ring(v1.DAMPING_LAYER_OD_MM, v1.DAMPING_LAYER_ID_MM, v1.DAMPING_LAYER_THICKNESS_MM, spring_rim_z - v1.DAMPING_LAYER_THICKNESS_MM)
    spring_retainer = v1._split_ring(
        v1.SNAP_RETAINER_OD_MM,
        v1.SNAP_RETAINER_ID_MM,
        v1.SNAP_RETAINER_THICKNESS_MM,
        spring_rim_z + v1.TACTILE_SPRING_THICKNESS_MM,
        v1.SNAP_RETAINER_SPLIT_MM,
    )

    shelf_top = rest_z - v1.HARD_STOP_MM
    stage1_pads: list[cq.Shape] = []
    for angle_deg in (0.0, 120.0, 240.0):
        angle = math.radians(angle_deg)
        radius = 4.05
        stage1_pads.append(
            v1._box(
                1.20,
                0.72,
                v1.FIRST_BUMPER_HEIGHT_MM,
                (
                    v1.MOUNT_X_MM + radius * math.cos(angle),
                    v1.MOUNT_Y_MM + radius * math.sin(angle),
                    shelf_top + v1.FIRST_BUMPER_HEIGHT_MM / 2.0,
                ),
            ).rotate(
                (v1.MOUNT_X_MM, v1.MOUNT_Y_MM, shelf_top),
                (v1.MOUNT_X_MM, v1.MOUNT_Y_MM, shelf_top + 1.0),
                angle_deg,
            )
        )
    landing1 = cq.Compound.makeCompound(stage1_pads)
    landing2 = v1._ring(9.00, 7.72, v1.SECOND_BUMPER_HEIGHT_MM, shelf_top)

    magnet_z0 = rest_z - v1.STEM_LENGTH_MM + 0.20
    magnet = v1._cylinder(v1.MAGNET_DIAMETER_MM, v1.MAGNET_LENGTH_MM, magnet_z0)
    pcb_center_z = magnet_z0 - v1.HALL_NOMINAL_AIR_GAP_MM - v1.HALL_PCB_Z_MM / 2.0
    hall_pcb = v1._box(v1.HALL_PCB_X_MM, v1.HALL_PCB_Y_MM, v1.HALL_PCB_Z_MM, (v1.MOUNT_X_MM, v1.MOUNT_Y_MM, pcb_center_z))
    sensor_bracket = v1._box(
        v1.HALL_PCB_X_MM + 1.2,
        v1.SENSOR_BRACKET_THICKNESS_MM,
        1.55,
        (v1.MOUNT_X_MM, v1.MOUNT_Y_MM + 3.15, pcb_center_z),
    )

    material_parts: tuple[tuple[str, cq.Shape], ...] = (
        ("shell_with_primary_control_interface", shell_interface),
        ("primary_control_cap_stem", cap_stem),
        ("cap_inertia_core", core),
        ("upper_split_bushing_free", upper_bushing_free),
        ("lower_split_bushing_free", lower_bushing_free),
        ("anti_rotation_preload_leaf_free", leaf_free),
        ("wet_diaphragm", diaphragm),
        ("tactile_spring_formed", tactile_spring),
        ("tactile_damping_annulus", damping),
        ("tactile_snap_retainer", spring_retainer),
        ("landing_stage_1", landing1),
        ("landing_stage_2", landing2),
        ("sensor_magnet", magnet),
        ("hall_pcb_support", sensor_bracket),
    )

    motion_sweep = _continuous_press_reference(rest_z)
    references: tuple[tuple[str, cq.Shape], ...] = (
        ("upper_split_bushing_installed_reference", upper_bushing_installed),
        ("lower_split_bushing_installed_reference", lower_bushing_installed),
        ("anti_rotation_leaf_installed_reference", leaf_installed),
        ("hall_sensor_envelope", hall_pcb),
        ("cap_motion_sweep", motion_sweep),
    )

    module = cq.Compound.makeCompound([
        cap_stem,
        core,
        upper_bushing_installed,
        lower_bushing_installed,
        leaf_installed,
        diaphragm,
        tactile_spring,
        damping,
        spring_retainer,
        landing1,
        landing2,
        magnet,
        hall_pcb,
        sensor_bracket,
    ])
    keepouts = {
        **{component.name: component.solid.val() for component in model.actuator_envelopes},
        "water_reservoir_envelope": model.water_reservoir_envelope.solid.val(),
        "waste_cartridge_envelope": model.waste_cartridge_envelope.solid.val(),
        "battery_reference_envelope": model.battery_reference_envelope.solid.val(),
        **{component.name: component.solid.val() for component in model.visual_keepouts},
    }
    intersections = {
        name: round(v1._intersection_volume(module, target), 8)
        for name, target in keepouts.items()
    }

    result = PrimaryControlHapticArchitectureV3(
        SOURCE_MAIN_SHA,
        outer_z,
        rest_z,
        material_parts,
        references,
        motion_sweep,
        joint_overlap,
        intersections,
        False,
    )
    result.__post_init__()
    return result


def export_primary_control_haptic_architecture_v3(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    architecture = build_primary_control_haptic_architecture_v3()
    for name, shape in architecture.material_parts:
        cq.exporters.export(shape, str(output_dir / f"{name}_MANUFACTURED.step"))
    for name, shape in architecture.reference_parts:
        cq.exporters.export(shape, str(output_dir / f"{name}_REFERENCE.step"))
    manifest = architecture.manifest()
    (output_dir / "primary_control_haptic_v3_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest
