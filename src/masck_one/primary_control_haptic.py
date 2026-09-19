from __future__ import annotations

"""Production-intent primary-control CAD candidate for Masck One.

The mechanism is deliberately decomposed by function:

- shell-integral structural barrel carries button loads;
- two axially separated split bearing inserts guide translation and suppress rock;
- a keyed stem plus compliant side leaf controls rotation without an over-tight bore;
- a dedicated formed spring-metal flexure creates the tactile transition;
- two elastomer landing stages absorb normal bottoming before an independent hard stop;
- a Hall/magnet package senses travel without adding a microswitch click;
- the wet diaphragm is separate from the precision bearing force path;
- a constrained lossy annulus damps the spring reaction rim;
- a sealed inertia insert in the cap biases the acoustic structure away from hollow plastic clack.

The CAD is digitally deterministic and Fusion-ready, but the intended force curve,
acoustics, sealing, wear, fatigue and subjective feel require physical validation.
"""

from dataclasses import dataclass, field
import hashlib
import json
import math
from pathlib import Path

import cadquery as cq

from .brand_identity import load_brand_identity
from .model import MasckOneModel, build_model

SCHEMA = "MASCK_ONE_PRIMARY_CONTROL_HAPTIC_V1"
SOURCE_MAIN_SHA = "42fa11818184cde998c6df25d7c46d4fb0e4c3eb"
SOURCE_M_CUT_ASSET_SHA = "66c037bec607bdefd240c4e193bb082d1c46ef72"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"

# Current production-intent location seed. Z is always derived from the live shell.
MOUNT_X_MM = 69.0
MOUNT_Y_MM = 25.0
AXIS_WORLD = (0.0, 0.0, 1.0)

CAP_DIAMETER_MM = 9.72
CAP_THICKNESS_MM = 0.66
FINGER_DISH_SAG_MM = 0.10
CAP_PROUD_MM = 0.02
INERTIA_CORE_DIAMETER_MM = 7.20
INERTIA_CORE_THICKNESS_MM = 0.35

STEM_DIAMETER_MM = 7.18
STEM_LENGTH_MM = 5.65
ANTI_ROTATION_RIB_RADIAL_MM = 0.32
ANTI_ROTATION_RIB_WIDTH_MM = 0.50
ANTI_ROTATION_SLOT_WIDTH_MM = 0.82
ANTI_ROTATION_LEAF_THICKNESS_MM = 0.22
ANTI_ROTATION_LEAF_LENGTH_MM = 2.00
ANTI_ROTATION_LEAF_PRELOAD_SEED_MM = 0.05

BARREL_OD_MM = 12.0
BARREL_BORE_DIAMETER_MM = 8.50
BARREL_REAR_EXTENSION_MM = 6.45
BARREL_FRONT_EXTENSION_MM = 0.48

BUSHING_OD_FREE_MM = 8.36
BUSHING_OD_INSTALLED_MM = 8.28
BUSHING_ID_FREE_MM = 7.09
BUSHING_ID_INSTALLED_MM = 7.18
BUSHING_LENGTH_MM = 0.66
BUSHING_SPLIT_GAP_MM = 0.82
BUSHING_SPAN_MM = 3.35
UPPER_BUSHING_CENTER_FROM_REST_MM = 1.45
LOWER_BUSHING_CENTER_FROM_REST_MM = UPPER_BUSHING_CENTER_FROM_REST_MM + BUSHING_SPAN_MM

DIAPHRAGM_OD_MM = 10.44
DIAPHRAGM_ID_MM = 7.30
DIAPHRAGM_MEMBRANE_THICKNESS_MM = 0.20
DIAPHRAGM_BEAD_THICKNESS_MM = 0.42

TACTILE_SPRING_THICKNESS_MM = 0.18
TACTILE_SPRING_OD_MM = 7.60
TACTILE_RING_ID_MM = 5.10
TACTILE_CENTER_DIAMETER_MM = 3.00
TACTILE_BEAM_WIDTH_MM = 0.72
TACTILE_PREFORM_RISE_MM = 0.33
TACTILE_RIM_FROM_REST_MM = 6.02
DAMPING_LAYER_THICKNESS_MM = 0.055
DAMPING_LAYER_OD_MM = 7.72
DAMPING_LAYER_ID_MM = 6.90
SNAP_RETAINER_OD_MM = 8.72
SNAP_RETAINER_ID_MM = 6.86
SNAP_RETAINER_THICKNESS_MM = 0.28
SNAP_RETAINER_SPLIT_MM = 0.85
SNAP_GROOVE_DEPTH_MM = 0.18
SNAP_GROOVE_HEIGHT_MM = 0.36

FIRST_LANDING_START_MM = 0.78
SECOND_LANDING_START_MM = 0.90
NOMINAL_BOTTOM_MM = 0.93
HARD_STOP_MM = 1.07
HARD_STOP_SHELF_THICKNESS_MM = 0.20
HARD_STOP_INNER_DIAMETER_MM = 7.48
HARD_STOP_OUTER_DIAMETER_MM = 9.30
FIRST_BUMPER_HEIGHT_MM = HARD_STOP_MM - FIRST_LANDING_START_MM
SECOND_BUMPER_HEIGHT_MM = HARD_STOP_MM - SECOND_LANDING_START_MM

MAGNET_DIAMETER_MM = 3.0
MAGNET_LENGTH_MM = 1.0
HALL_PCB_X_MM = 6.0
HALL_PCB_Y_MM = 5.0
HALL_PCB_Z_MM = 0.80
HALL_NOMINAL_AIR_GAP_MM = 0.70
SENSOR_BRACKET_THICKNESS_MM = 0.60

M_CUT_WIDTH_MM = 4.20
M_CUT_HEIGHT_MM = 3.20
M_CUT_STROKE_MM = 0.38
M_CUT_DEBOSS_MM = 0.06

_INTERSECTION_TOLERANCE_MM3 = 1e-7


class PrimaryControlHapticError(ValueError):
    pass


def _shape(workplane: cq.Workplane) -> cq.Shape:
    value = workplane.val()
    if not value.isValid() or not value.Solids():
        raise PrimaryControlHapticError("expected valid positive B-rep")
    return value


def _ring(od: float, id_: float, height: float, z0: float) -> cq.Shape:
    if not (od > id_ > 0.0 and height > 0.0):
        raise PrimaryControlHapticError("invalid annulus dimensions")
    return _shape(
        cq.Workplane("XY")
        .workplane(offset=z0)
        .center(MOUNT_X_MM, MOUNT_Y_MM)
        .circle(od / 2.0)
        .circle(id_ / 2.0)
        .extrude(height)
    )


def _cylinder(diameter: float, height: float, z0: float) -> cq.Shape:
    return _shape(
        cq.Workplane("XY")
        .workplane(offset=z0)
        .center(MOUNT_X_MM, MOUNT_Y_MM)
        .circle(diameter / 2.0)
        .extrude(height)
    )


def _box(x: float, y: float, z: float, center: tuple[float, float, float]) -> cq.Shape:
    return _shape(cq.Workplane("XY").box(x, y, z).translate(center))


def _split_ring(
    od: float,
    id_: float,
    height: float,
    z0: float,
    split_width: float,
) -> cq.Shape:
    ring = _ring(od, id_, height, z0)
    slot = _box(
        od,
        split_width,
        height + 0.20,
        (MOUNT_X_MM + od / 2.0, MOUNT_Y_MM, z0 + height / 2.0),
    )
    result = ring.cut(slot).clean()
    if not result.isValid() or len(result.Solids()) != 1 or float(result.Volume()) <= 0.0:
        raise PrimaryControlHapticError("split ring must remain one positive C-ring")
    return result


def _segment_prism(
    p0: tuple[float, float],
    p1: tuple[float, float],
    width: float,
    depth: float,
    z_center: float,
) -> cq.Shape:
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    length = math.hypot(dx, dy)
    angle = math.degrees(math.atan2(dy, dx))
    body = _box(length + width * 0.35, width, depth, ((p0[0] + p1[0]) / 2.0, (p0[1] + p1[1]) / 2.0, z_center))
    return body.rotate((MOUNT_X_MM, MOUNT_Y_MM, z_center), (MOUNT_X_MM, MOUNT_Y_MM, z_center + 1.0), angle)


def _intersection_volume(a: cq.Shape, b: cq.Shape) -> float:
    total = 0.0
    for left in a.Solids():
        lb = left.BoundingBox()
        for right in b.Solids():
            rb = right.BoundingBox()
            if (
                lb.xmax < rb.xmin
                or rb.xmax < lb.xmin
                or lb.ymax < rb.ymin
                or rb.ymax < lb.ymin
                or lb.zmax < rb.zmin
                or rb.zmax < lb.zmin
            ):
                continue
            common = left.intersect(right)
            if not common.isValid():
                raise PrimaryControlHapticError("invalid intersection result")
            total += sum(max(0.0, float(s.Volume())) for s in common.Solids())
    return total


def _shell_outer_z(model: MasckOneModel) -> float:
    probe = _cylinder(BARREL_OD_MM, 32.0, -4.0)
    patch = model.shell.solid.val().intersect(probe)
    if not patch.isValid() or not patch.Solids():
        raise PrimaryControlHapticError("primary-control location does not capture live shell")
    return float(patch.BoundingBox().zmax)


def _dish_cap(cap: cq.Shape, top_z: float) -> cq.Shape:
    a = CAP_DIAMETER_MM / 2.0
    sag = FINGER_DISH_SAG_MM
    radius = (a * a + sag * sag) / (2.0 * sag)
    sphere = (
        cq.Workplane("XY")
        .workplane(offset=top_z + radius - sag)
        .center(MOUNT_X_MM, MOUNT_Y_MM)
        .sphere(radius)
        .val()
    )
    result = cap.cut(sphere).clean()
    if not result.isValid() or not result.Solids():
        raise PrimaryControlHapticError("finger dish invalidated cap")
    return result


def _m_cut_grooves(top_z: float) -> cq.Shape:
    half_w = M_CUT_WIDTH_MM / 2.0
    half_h = M_CUT_HEIGHT_MM / 2.0
    tip = 0.32
    points = [
        ((-half_w, -half_h), (-half_w, half_h)),
        ((-half_w, half_h), (-tip, 0.05)),
        ((tip, 0.05), (half_w, half_h)),
        ((half_w, half_h), (half_w, -half_h)),
    ]
    solids = []
    for a, b in points:
        solids.append(
            _segment_prism(
                (MOUNT_X_MM + a[0], MOUNT_Y_MM + a[1]),
                (MOUNT_X_MM + b[0], MOUNT_Y_MM + b[1]),
                M_CUT_STROKE_MM,
                M_CUT_DEBOSS_MM + 0.05,
                top_z - M_CUT_DEBOSS_MM / 2.0,
            )
        )
    return cq.Compound.makeCompound(solids)


def _formed_tactile_spring(rim_z: float) -> cq.Shape:
    ring = _ring(TACTILE_SPRING_OD_MM, TACTILE_RING_ID_MM, TACTILE_SPRING_THICKNESS_MM, rim_z)
    center_z = rim_z + TACTILE_PREFORM_RISE_MM
    center = _cylinder(TACTILE_CENTER_DIAMETER_MM, TACTILE_SPRING_THICKNESS_MM, center_z)

    center_radius = TACTILE_CENTER_DIAMETER_MM / 2.0
    ring_inner = TACTILE_RING_ID_MM / 2.0
    radial_gap = ring_inner - center_radius
    beam_length = radial_gap + 0.34
    beam_center_radius = 0.5 * (center_radius + ring_inner)
    angle = math.degrees(math.atan2(TACTILE_PREFORM_RISE_MM, radial_gap))
    z_mid = rim_z + TACTILE_SPRING_THICKNESS_MM / 2.0 + TACTILE_PREFORM_RISE_MM / 2.0
    beams: list[cq.Shape] = []
    for azimuth in (0.0, 90.0, 180.0, 270.0):
        beam = _box(
            beam_length,
            TACTILE_BEAM_WIDTH_MM,
            TACTILE_SPRING_THICKNESS_MM,
            (MOUNT_X_MM + beam_center_radius, MOUNT_Y_MM, z_mid),
        )
        beam = beam.rotate(
            (MOUNT_X_MM, MOUNT_Y_MM, z_mid),
            (MOUNT_X_MM, MOUNT_Y_MM + 1.0, z_mid),
            angle,
        )
        beam = beam.rotate(
            (MOUNT_X_MM, MOUNT_Y_MM, z_mid),
            (MOUNT_X_MM, MOUNT_Y_MM, z_mid + 1.0),
            azimuth,
        )
        beams.append(beam)
    result = ring
    for part in beams:
        result = result.fuse(part)
    result = result.fuse(center).clean()
    if not result.isValid() or len(result.Solids()) != 1 or float(result.Volume()) <= 0.0:
        raise PrimaryControlHapticError("formed tactile spring must be one connected manufactured solid")
    return result


def _build_shell_interface(model: MasckOneModel, outer_z: float, rest_z: float) -> cq.Shape:
    barrel_z0 = outer_z - BARREL_REAR_EXTENSION_MM
    barrel_h = BARREL_REAR_EXTENSION_MM + BARREL_FRONT_EXTENSION_MM
    barrel = _ring(BARREL_OD_MM, BARREL_BORE_DIAMETER_MM, barrel_h, barrel_z0)
    shell = model.shell.solid.val().fuse(barrel)

    # Through bore is deliberately regenerated after the barrel fuse so shell and
    # barrel share one clean opening rather than coincident overlapping cavities.
    bore = _cylinder(BARREL_BORE_DIAMETER_MM, barrel_h + 4.0, barrel_z0 - 2.0)
    shell = shell.cut(bore)

    # Independent rigid normal overtravel shelf. Normal landing occurs on elastomer.
    shelf_top = rest_z - HARD_STOP_MM
    shelf = _ring(
        HARD_STOP_OUTER_DIAMETER_MM,
        HARD_STOP_INNER_DIAMETER_MM,
        HARD_STOP_SHELF_THICKNESS_MM,
        shelf_top - HARD_STOP_SHELF_THICKNESS_MM,
    )
    shell = shell.fuse(shelf)

    # Reaction shelf supports only the outer tactile spring rim; the moving center is free.
    spring_rim_z = rest_z - TACTILE_RIM_FROM_REST_MM
    spring_shelf = _ring(8.46, 6.90, 0.22, spring_rim_z - DAMPING_LAYER_THICKNESS_MM - 0.22)
    shell = shell.fuse(spring_shelf)

    # Local internal groove captures the split tactile retainer without adhesive.
    groove = _ring(
        BARREL_BORE_DIAMETER_MM + 2.0 * SNAP_GROOVE_DEPTH_MM,
        BARREL_BORE_DIAMETER_MM - 0.02,
        SNAP_GROOVE_HEIGHT_MM,
        spring_rim_z + TACTILE_SPRING_THICKNESS_MM - 0.02,
    )
    shell = shell.cut(groove)
    shell = shell.clean()
    if not shell.isValid() or not shell.Solids():
        raise PrimaryControlHapticError("shell-integral control interface is invalid")
    return shell


@dataclass(frozen=True, slots=True)
class PrimaryControlHapticArchitecture:
    source_main_sha: str
    shell_outer_z_mm: float
    rest_cap_underside_z_mm: float
    material_parts: tuple[tuple[str, cq.Shape], ...] = field(repr=False, compare=False)
    reference_parts: tuple[tuple[str, cq.Shape], ...] = field(repr=False, compare=False)
    motion_sweep: cq.Shape = field(repr=False, compare=False)
    keepout_intersections_mm3: dict[str, float] = field(default_factory=dict)
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        if self.source_main_sha != SOURCE_MAIN_SHA:
            raise PrimaryControlHapticError("primary control source-main mismatch")
        if self.physical_validation_eligible:
            raise PrimaryControlHapticError("digital button CAD is not physical validation")
        for name, shape in self.material_parts:
            if not shape.isValid() or not shape.Solids() or float(shape.Volume()) <= 0.0:
                raise PrimaryControlHapticError(f"{name} must be valid positive material")
        if any(value > _INTERSECTION_TOLERANCE_MM3 for value in self.keepout_intersections_mm3.values()):
            raise PrimaryControlHapticError("primary control intersects a protected package/visual keepout")

    @property
    def architecture_sha256(self) -> str:
        payload = json.dumps(self.manifest(False), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        return hashlib.sha256(payload).hexdigest()

    def manifest(self, include_sha: bool = True) -> dict[str, object]:
        brand = load_brand_identity()
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "source_main_sha": self.source_main_sha,
            "source_m_cut_asset_sha": SOURCE_M_CUT_ASSET_SHA,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "location_world_mm": [MOUNT_X_MM, MOUNT_Y_MM, self.shell_outer_z_mm],
            "button_axis_world_unit": list(AXIS_WORLD),
            "rest_cap_underside_z_mm": self.rest_cap_underside_z_mm,
            "selected_mechanism": (
                "DUAL_SPLIT_BEARING_GUIDANCE_PLUS_KEYED_SIDE_PRELOAD_PLUS_DAMPED_FORMED_TACTILE_FLEXURE_"
                "PLUS_TWO_STAGE_ELASTOMER_LANDING_PLUS_INDEPENDENT_HARD_STOP_PLUS_HALL_SENSING"
            ),
            "feel_intent": list(brand.data["interaction_signature"]["primary_control"]["experience"]["feel"]),
            "sound_intent": list(brand.data["interaction_signature"]["primary_control"]["experience"]["sound"]),
            "travel_events_mm": {
                "force_peak_reference": 0.52,
                "transition_end_reference": 0.61,
                "first_landing": FIRST_LANDING_START_MM,
                "second_landing": SECOND_LANDING_START_MM,
                "nominal_bottom": NOMINAL_BOTTOM_MM,
                "hard_stop": HARD_STOP_MM,
            },
            "guidance": {
                "stem_diameter_mm": STEM_DIAMETER_MM,
                "bushing_span_mm": BUSHING_SPAN_MM,
                "free_bushing_id_mm": BUSHING_ID_FREE_MM,
                "installed_reference_id_mm": BUSHING_ID_INSTALLED_MM,
                "anti_rotation_rib_width_mm": ANTI_ROTATION_RIB_WIDTH_MM,
                "anti_rotation_slot_width_mm": ANTI_ROTATION_SLOT_WIDTH_MM,
                "anti_rotation_leaf_preload_seed_mm": ANTI_ROTATION_LEAF_PRELOAD_SEED_MM,
            },
            "material_parts": [name for name, _shape in self.material_parts],
            "reference_parts": [name for name, _shape in self.reference_parts],
            "keepout_intersections_mm3": self.keepout_intersections_mm3,
            "fusion_handoff": {
                "cad_platform": "AUTODESK_FUSION_360",
                "component_axis": "+Z_OUTWARD_-Z_PRESS",
                "grounded_component": "shell_with_primary_control_interface",
                "button_slider_dof": "TRANSLATION_-Z_0_TO_1P07_MM",
                "compliant_parts": ["tactile_spring_formed", "anti_rotation_preload_leaf", "wet_diaphragm", "landing_stage_1", "landing_stage_2"],
                "reference_only": ["cap_motion_sweep", "hall_sensor_envelope", "installed_bushing_references"],
                "m_cut_status": "PROVISIONAL_MASTER_MARK_DEBOSS_SOURCE_BOUND_TO_BRAND_ASSET",
            },
            "physical_validation_eligible": False,
            "physical_validation": (
                "OPEN_FORCE_TRAVEL_NONLINEAR_SNAP_FATIGUE_GUIDE_FRICTION_WOBBLE_SEAL_LEAKAGE_BUMPER_RATE_"
                "TEMPERATURE_AGING_SENSOR_TRANSFER_ACOUSTIC_SPECTRUM_RING_DECAY_LIFETIME_AND_SUBJECTIVE_FEEL"
            ),
        }
        if include_sha:
            payload["architecture_sha256"] = self.architecture_sha256
        return payload


def build_primary_control_haptic_architecture(
    *,
    model: MasckOneModel | None = None,
) -> PrimaryControlHapticArchitecture:
    model = build_model() if model is None else model
    outer_z = _shell_outer_z(model)
    rest_z = outer_z + CAP_PROUD_MM
    top_z = rest_z + CAP_THICKNESS_MM

    shell_interface = _build_shell_interface(model, outer_z, rest_z)

    # Cap/stem polymer with an encapsulated inertia-core cavity and physical M-Cut deboss.
    cap = _cylinder(CAP_DIAMETER_MM, CAP_THICKNESS_MM, rest_z)
    cap = _dish_cap(cap, top_z)
    core_z0 = rest_z + (CAP_THICKNESS_MM - INERTIA_CORE_THICKNESS_MM) / 2.0
    core = _cylinder(INERTIA_CORE_DIAMETER_MM, INERTIA_CORE_THICKNESS_MM, core_z0)
    cap = cap.cut(core)
    stem = _cylinder(STEM_DIAMETER_MM, STEM_LENGTH_MM, rest_z - STEM_LENGTH_MM)
    rib = _box(
        ANTI_ROTATION_RIB_RADIAL_MM,
        ANTI_ROTATION_RIB_WIDTH_MM,
        STEM_LENGTH_MM - 0.35,
        (
            MOUNT_X_MM + STEM_DIAMETER_MM / 2.0 + ANTI_ROTATION_RIB_RADIAL_MM / 2.0,
            MOUNT_Y_MM,
            rest_z - (STEM_LENGTH_MM - 0.35) / 2.0 - 0.18,
        ),
    )
    cap_stem = cap.fuse(stem).fuse(rib)
    grooves = _m_cut_grooves(top_z)
    cap_stem = cap_stem.cut(grooves).clean()
    if not cap_stem.isValid() or len(cap_stem.Solids()) != 1:
        raise PrimaryControlHapticError("cap/stem must be one connected manufactured part")

    # Split low-friction bearing inserts. Free shapes are manufacturing geometry;
    # installed shapes are references after elastic accommodation to the stem/barrel.
    upper_z0 = rest_z - UPPER_BUSHING_CENTER_FROM_REST_MM - BUSHING_LENGTH_MM / 2.0
    lower_z0 = rest_z - LOWER_BUSHING_CENTER_FROM_REST_MM - BUSHING_LENGTH_MM / 2.0
    upper_bushing_free = _split_ring(BUSHING_OD_FREE_MM, BUSHING_ID_FREE_MM, BUSHING_LENGTH_MM, upper_z0, BUSHING_SPLIT_GAP_MM)
    lower_bushing_free = _split_ring(BUSHING_OD_FREE_MM, BUSHING_ID_FREE_MM, BUSHING_LENGTH_MM, lower_z0, BUSHING_SPLIT_GAP_MM)
    upper_bushing_installed = _split_ring(BUSHING_OD_INSTALLED_MM, BUSHING_ID_INSTALLED_MM, BUSHING_LENGTH_MM, upper_z0, ANTI_ROTATION_SLOT_WIDTH_MM)
    lower_bushing_installed = _split_ring(BUSHING_OD_INSTALLED_MM, BUSHING_ID_INSTALLED_MM, BUSHING_LENGTH_MM, lower_z0, ANTI_ROTATION_SLOT_WIDTH_MM)

    # Side-preload leaf eliminates the rib's residual angular clearance without using
    # an over-tight full-diameter stem fit. Free and installed references are separated.
    leaf_center_z = rest_z - 2.55
    leaf_x = MOUNT_X_MM + BARREL_BORE_DIAMETER_MM / 2.0 - 0.18
    leaf_free = _box(
        0.34,
        ANTI_ROTATION_LEAF_THICKNESS_MM,
        ANTI_ROTATION_LEAF_LENGTH_MM,
        (leaf_x, MOUNT_Y_MM + ANTI_ROTATION_SLOT_WIDTH_MM / 2.0 - ANTI_ROTATION_LEAF_THICKNESS_MM / 2.0 - ANTI_ROTATION_LEAF_PRELOAD_SEED_MM, leaf_center_z),
    )
    leaf_installed = leaf_free.translate((0.0, ANTI_ROTATION_LEAF_PRELOAD_SEED_MM, 0.0))

    # Wet barrier has reinforced inner/outer beads and a thin compliant membrane.
    diaphragm_z = rest_z - 0.16
    membrane = _ring(DIAPHRAGM_OD_MM, DIAPHRAGM_ID_MM, DIAPHRAGM_MEMBRANE_THICKNESS_MM, diaphragm_z)
    outer_bead = _ring(DIAPHRAGM_OD_MM + 0.30, DIAPHRAGM_OD_MM - 0.45, DIAPHRAGM_BEAD_THICKNESS_MM, diaphragm_z - 0.11)
    inner_bead = _ring(DIAPHRAGM_ID_MM + 0.48, DIAPHRAGM_ID_MM - 0.20, DIAPHRAGM_BEAD_THICKNESS_MM, diaphragm_z - 0.11)
    diaphragm = membrane.fuse(outer_bead).fuse(inner_bead).clean()

    spring_rim_z = rest_z - TACTILE_RIM_FROM_REST_MM
    tactile_spring = _formed_tactile_spring(spring_rim_z)
    damping = _ring(DAMPING_LAYER_OD_MM, DAMPING_LAYER_ID_MM, DAMPING_LAYER_THICKNESS_MM, spring_rim_z - DAMPING_LAYER_THICKNESS_MM)
    spring_retainer = _split_ring(
        SNAP_RETAINER_OD_MM,
        SNAP_RETAINER_ID_MM,
        SNAP_RETAINER_THICKNESS_MM,
        spring_rim_z + TACTILE_SPRING_THICKNESS_MM,
        SNAP_RETAINER_SPLIT_MM,
    )

    shelf_top = rest_z - HARD_STOP_MM
    # Three low-area first-stage pads produce early soft engagement without a pneumatic ring.
    stage1_pads: list[cq.Shape] = []
    for angle_deg in (0.0, 120.0, 240.0):
        angle = math.radians(angle_deg)
        radius = 4.05
        stage1_pads.append(
            _box(
                1.20,
                0.72,
                FIRST_BUMPER_HEIGHT_MM,
                (
                    MOUNT_X_MM + radius * math.cos(angle),
                    MOUNT_Y_MM + radius * math.sin(angle),
                    shelf_top + FIRST_BUMPER_HEIGHT_MM / 2.0,
                ),
            ).rotate(
                (MOUNT_X_MM, MOUNT_Y_MM, shelf_top),
                (MOUNT_X_MM, MOUNT_Y_MM, shelf_top + 1.0),
                angle_deg,
            )
        )
    landing1 = cq.Compound.makeCompound(stage1_pads)
    landing2 = _ring(9.00, 7.72, SECOND_BUMPER_HEIGHT_MM, shelf_top)

    # Quiet non-contact sensing. Magnet is a real component envelope; PCB remains a
    # package reference until a supplier/part is selected.
    magnet_z0 = rest_z - STEM_LENGTH_MM + 0.20
    magnet = _cylinder(MAGNET_DIAMETER_MM, MAGNET_LENGTH_MM, magnet_z0)
    pcb_center_z = magnet_z0 - HALL_NOMINAL_AIR_GAP_MM - HALL_PCB_Z_MM / 2.0
    hall_pcb = _box(HALL_PCB_X_MM, HALL_PCB_Y_MM, HALL_PCB_Z_MM, (MOUNT_X_MM, MOUNT_Y_MM, pcb_center_z))
    sensor_bracket = _box(
        HALL_PCB_X_MM + 1.2,
        SENSOR_BRACKET_THICKNESS_MM,
        1.55,
        (MOUNT_X_MM, MOUNT_Y_MM + 3.15, pcb_center_z),
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

    moving = cq.Compound.makeCompound([cap_stem, core, magnet])
    # The full hard-stop motion reference is intentionally a compound of sampled
    # endpoints and intermediate poses, not manufactured material.
    motion_poses = [moving.translate((0.0, 0.0, -HARD_STOP_MM * index / 16.0)) for index in range(17)]
    motion_sweep = cq.Compound.makeCompound(motion_poses)

    references: tuple[tuple[str, cq.Shape], ...] = (
        ("upper_split_bushing_installed_reference", upper_bushing_installed),
        ("lower_split_bushing_installed_reference", lower_bushing_installed),
        ("anti_rotation_leaf_installed_reference", leaf_installed),
        ("hall_sensor_envelope", hall_pcb),
        ("cap_motion_sweep", motion_sweep),
    )

    # Package/visual keepout checks exclude the shell derivative itself and compare
    # the compact mechanism against existing authority/model envelopes.
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
        name: round(_intersection_volume(module, target), 8)
        for name, target in keepouts.items()
    }

    result = PrimaryControlHapticArchitecture(
        SOURCE_MAIN_SHA,
        outer_z,
        rest_z,
        material_parts,
        references,
        motion_sweep,
        intersections,
        False,
    )
    result.__post_init__()
    return result


def export_primary_control_haptic_architecture(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    architecture = build_primary_control_haptic_architecture()
    for name, shape in architecture.material_parts:
        cq.exporters.export(shape, str(output_dir / f"{name}_MANUFACTURED.step"))
    for name, shape in architecture.reference_parts:
        cq.exporters.export(shape, str(output_dir / f"{name}_REFERENCE.step"))
    cq.exporters.export(architecture.motion_sweep, str(output_dir / "primary_control_motion_REFERENCE.step"))
    manifest = architecture.manifest()
    (output_dir / "primary_control_haptic_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest
