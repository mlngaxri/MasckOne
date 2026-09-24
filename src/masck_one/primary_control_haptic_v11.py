from __future__ import annotations

"""Primary-control V11 geometry, with rejected series-force path preserved honestly.

V10 closed outward capture and return-datum ambiguity, but inherited V9's 0.22 mm
plunger-to-dome rest gap. That free approach distance is incompatible with the brand
requirement for negligible initial slack. V11 keeps the V10 guides, capture flange,
wet diaphragm, side Hall package, dome seat, progressive landing and rigid abuse stop,
while reducing the plunger rest gap to 0.04 mm.

The existing spring chamber is deliberately not lengthened because its forward roof is
already close to the side magnet package. Instead the first-order spring envelope is
rebalanced from 0.14 mm wire / 4.5 total coils to 0.12 mm wire / 4.0 total coils. In
the unchanged 1.32 mm installed chamber this preserves preload, leaves >=0.10 mm
solid-height clearance through the longer post-contact lost motion, and remains below
the existing 0.08 N incremental-force screen.

The former spring-clearance result assumed the dome had already collapsed. The
source-derived force bound now rejects that assumption: the series spring cannot
reach the captured typical trip-force range before coil bind. Geometry remains
available for passive off-face inspection, never as a functional button release.

The spring remains a supplier-selection/reference envelope only. Force-travel,
tolerance, buckling, fatigue, friction, acoustics, wet aging and subjective feel remain
PHYSICAL VALIDATION REQUIRED.
"""

from dataclasses import dataclass, field
import hashlib
import json
import math
from pathlib import Path

import cadquery as cq

from . import primary_control_haptic as v1
from . import primary_control_haptic_v8 as v8
from . import primary_control_haptic_v9 as v9
from . import primary_control_haptic_v10 as v10
from .model import MasckOneModel, build_model
from .primary_control_force_path import SeriesSpringInputs, evaluate_series_spring
from .primary_control_touch_surface import refine_touch_surface, appearance_contract

SCHEMA = "MASCK_ONE_PRIMARY_CONTROL_HAPTIC_V11"
SOURCE_MAIN_SHA = v10.SOURCE_MAIN_SHA
PLUNGER_REST_GAP_TO_DOME_MM = 0.04
MAX_PRECONTACT_DEAD_TRAVEL_MM = 0.05
DOME_BOTTOM_EVENT_MM = PLUNGER_REST_GAP_TO_DOME_MM + v9.DOME_HEIGHT_MM
LOST_MOTION_TO_HARD_STOP_MM = v1.HARD_STOP_MM - DOME_BOTTOM_EVENT_MM

LOST_MOTION_SPRING_WIRE_MM = 0.12
LOST_MOTION_SPRING_MEAN_COIL_MM = v9.LOST_MOTION_SPRING_MEAN_COIL_MM
LOST_MOTION_SPRING_ACTIVE_COILS = 3.0
LOST_MOTION_SPRING_TOTAL_COILS = 4.0
LOST_MOTION_SPRING_FREE_LENGTH_MM = v9.LOST_MOTION_SPRING_FREE_LENGTH_MM
MIN_SPRING_SOLID_CLEARANCE_MM = v9.MIN_SPRING_SOLID_CLEARANCE_MM
MAX_INCREMENTAL_LOST_MOTION_FORCE_N = v9.MAX_INCREMENTAL_LOST_MOTION_FORCE_N
_INTERSECTION_TOLERANCE_MM3 = 1e-7


class PrimaryControlHapticV11Error(ValueError):
    pass


def force_path_screen() -> dict[str, object]:
    """Use the actual current chamber and coil dimensions, not a parallel study seed."""
    installed = (
        v9.PLUNGER_CAVITY_FORWARD_FROM_TRIM_MM
        - v9.PLUNGER_HEAD_Z0_FROM_TRIM_MM
        - v9.PLUNGER_HEAD_HEIGHT_MM
    )
    return evaluate_series_spring(SeriesSpringInputs(
        shear_modulus_seed_N_mm2=v9.LOST_MOTION_SPRING_SHEAR_MODULUS_SEED_N_PER_MM2,
        wire_mm=LOST_MOTION_SPRING_WIRE_MM,
        mean_coil_mm=LOST_MOTION_SPRING_MEAN_COIL_MM,
        active_coils=LOST_MOTION_SPRING_ACTIVE_COILS,
        total_coils=LOST_MOTION_SPRING_TOTAL_COILS,
        free_length_mm=LOST_MOTION_SPRING_FREE_LENGTH_MM,
        installed_length_mm=installed,
        rest_gap_mm=PLUNGER_REST_GAP_TO_DOME_MM,
        hard_travel_mm=v1.HARD_STOP_MM,
        dome_height_mm=v9.DOME_HEIGHT_MM,
        trip_nominal_N=v9.DOME_TRIP_FORCE_GF * 0.00980665,
        trip_typical_tolerance_N=v9.DOME_TRIP_FORCE_TOLERANCE_GF * 0.00980665,
        allowed_postcollapse_increment_N=MAX_INCREMENTAL_LOST_MOTION_FORCE_N,
    ))


def require_functional_architecture() -> None:
    screen = force_path_screen()
    if not screen["reaches_typical_trip_before_bind_or_stop"]:
        raise PrimaryControlHapticV11Error("REJECTED_SERIES_FORCE_PATH: spring cannot drive dome before bind")
    raise PrimaryControlHapticV11Error("force bound alone cannot qualify dome travel or a functional button")


def _near_contact_plunger(rest_z: float) -> cq.Shape:
    trim_z = rest_z - v9.STEM_REAR_FROM_REST_MM
    dome_top_z = rest_z - v9.DOME_SEAT_TOP_FROM_REST_MM + v9.DOME_HEIGHT_MM
    shaft_z0 = dome_top_z + PLUNGER_REST_GAP_TO_DOME_MM
    shaft_top = trim_z + v9.PLUNGER_SHAFT_TOP_FROM_TRIM_MM
    shaft = v1._cylinder(
        v9.PLUNGER_SHAFT_DIAMETER_MM,
        shaft_top - shaft_z0,
        shaft_z0,
    )
    head = v1._cylinder(
        v9.PLUNGER_HEAD_DIAMETER_MM,
        v9.PLUNGER_HEAD_HEIGHT_MM,
        trim_z + v9.PLUNGER_HEAD_Z0_FROM_TRIM_MM,
    )
    plunger = shaft.fuse(head).clean()
    if not plunger.isValid() or len(plunger.Solids()) != 1 or plunger.Volume() <= 0.0:
        raise PrimaryControlHapticV11Error("near-contact plunger must remain one positive solid")
    return plunger


def _spring_screen(rest_z: float) -> tuple[cq.Shape, dict[str, float]]:
    trim_z = rest_z - v9.STEM_REAR_FROM_REST_MM
    head_top_z = trim_z + v9.PLUNGER_HEAD_Z0_FROM_TRIM_MM + v9.PLUNGER_HEAD_HEIGHT_MM
    cavity_roof_z = trim_z + v9.PLUNGER_CAVITY_FORWARD_FROM_TRIM_MM
    installed = cavity_roof_z - head_top_z
    minimum = installed - LOST_MOTION_TO_HARD_STOP_MM
    solid = LOST_MOTION_SPRING_TOTAL_COILS * LOST_MOTION_SPRING_WIRE_MM
    solid_clearance = minimum - solid
    rate = (
        v9.LOST_MOTION_SPRING_SHEAR_MODULUS_SEED_N_PER_MM2
        * LOST_MOTION_SPRING_WIRE_MM**4
        / (
            8.0
            * LOST_MOTION_SPRING_MEAN_COIL_MM**3
            * LOST_MOTION_SPRING_ACTIVE_COILS
        )
    )
    preload_compression = LOST_MOTION_SPRING_FREE_LENGTH_MM - installed
    preload_force = max(0.0, rate * preload_compression)
    incremental = rate * LOST_MOTION_TO_HARD_STOP_MM
    spring_od = LOST_MOTION_SPRING_MEAN_COIL_MM + LOST_MOTION_SPRING_WIRE_MM
    envelope = v1._cylinder(spring_od, installed, head_top_z)
    metrics = {
        "spring_rate_N_per_mm": round(rate, 9),
        "installed_length_mm": round(installed, 9),
        "free_length_seed_mm": LOST_MOTION_SPRING_FREE_LENGTH_MM,
        "wire_diameter_mm": LOST_MOTION_SPRING_WIRE_MM,
        "total_coils_seed": LOST_MOTION_SPRING_TOTAL_COILS,
        "active_coils_seed": LOST_MOTION_SPRING_ACTIVE_COILS,
        "rest_preload_compression_mm": round(preload_compression, 9),
        "rest_preload_force_proxy_N": round(preload_force, 9),
        "minimum_operating_length_mm": round(minimum, 9),
        "solid_height_mm": round(solid, 9),
        "solid_height_clearance_mm": round(solid_clearance, 9),
        "incremental_force_over_lost_motion_N": round(incremental, 9),
    }
    return envelope, metrics


def _replace_named(
    parts: tuple[tuple[str, cq.Shape], ...],
    name: str,
    replacement: cq.Shape,
) -> tuple[tuple[str, cq.Shape], ...]:
    output: list[tuple[str, cq.Shape]] = []
    found = False
    for part_name, shape in parts:
        if part_name == name:
            output.append((part_name, replacement))
            found = True
        else:
            output.append((part_name, shape))
    if not found:
        raise PrimaryControlHapticV11Error(f"required predecessor part missing: {name}")
    return tuple(output)


def _plunger_translation_sweep(rest_z: float, travel_mm: float) -> cq.Shape:
    """Exact axial sweep of both analytic cylinders, including every interior pose.

    Minkowski addition distributes over union. Each cylinder's axial sweep is
    its unchanged disk extruded through original height plus translation travel.
    No sampled pose is used to construct this solid.
    """
    if not math.isfinite(travel_mm) or travel_mm <= 0.0:
        raise PrimaryControlHapticV11Error("plunger sweep requires positive finite travel")
    trim = rest_z - v9.STEM_REAR_FROM_REST_MM
    shaft_z0 = rest_z - v9.DOME_SEAT_TOP_FROM_REST_MM + v9.DOME_HEIGHT_MM + PLUNGER_REST_GAP_TO_DOME_MM
    shaft_top = trim + v9.PLUNGER_SHAFT_TOP_FROM_TRIM_MM
    shaft = v1._cylinder(v9.PLUNGER_SHAFT_DIAMETER_MM, shaft_top - shaft_z0 + travel_mm, shaft_z0 - travel_mm)
    head = v1._cylinder(v9.PLUNGER_HEAD_DIAMETER_MM, v9.PLUNGER_HEAD_HEIGHT_MM + travel_mm,
                        trim + v9.PLUNGER_HEAD_Z0_FROM_TRIM_MM - travel_mm)
    sweep = shaft.fuse(head).clean()
    if not sweep.isValid() or len(sweep.Solids()) != 1 or sweep.Volume() <= 0.0:
        raise PrimaryControlHapticV11Error("plunger sweep must be a valid positive reference solid")
    return sweep


def _continuous_motion_reference(rest_z: float) -> cq.Shape:
    trim_z = rest_z - v9.STEM_REAR_FROM_REST_MM
    cap = v1._cylinder(
        v1.CAP_DIAMETER_MM,
        v1.CAP_THICKNESS_MM + v1.HARD_STOP_MM,
        rest_z - v1.HARD_STOP_MM,
    )
    broad_stem = v1._cylinder(
        v1.STEM_DIAMETER_MM,
        (rest_z - trim_z) + v1.HARD_STOP_MM,
        trim_z - v1.HARD_STOP_MM,
    )
    magnet = v8._offset_cylinder(
        v8.SIDE_MAGNET_DIAMETER_MM,
        v8.SIDE_MAGNET_AXIAL_MM + v1.HARD_STOP_MM,
        center_x_mm=v1.MOUNT_X_MM - v8.SIDE_MAGNET_CENTER_RADIUS_MM,
        center_y_mm=v1.MOUNT_Y_MM,
        z0_mm=(
            rest_z
            - v8.SIDE_MAGNET_CENTER_FROM_REST_MM
            - v8.SIDE_MAGNET_AXIAL_MM / 2.0
            - v1.HARD_STOP_MM
        ),
    )
    # Include the retaining-head axial clearance as well as full cap travel.
    # This is conservative permitted motion, not a claimed dome-collapse path.
    pullout_clearance = v9.PLUNGER_HEAD_Z0_FROM_TRIM_MM - v9.PLUNGER_RETAINING_LEDGE_FROM_TRIM_MM
    plunger_envelope = _plunger_translation_sweep(rest_z, v1.HARD_STOP_MM + pullout_clearance)
    # The cylindrical stem envelope alone misses the positive anti-rotation key.
    # Retain its full legacy axial length conservatively after the rear trim.
    rib_length = v1.STEM_LENGTH_MM - 0.35
    rib_bottom = rest_z - rib_length - 0.18 - v1.HARD_STOP_MM
    rib_height = rib_length + v1.HARD_STOP_MM
    rib = v1._box(v1.ANTI_ROTATION_RIB_RADIAL_MM, v1.ANTI_ROTATION_RIB_WIDTH_MM, rib_height,
                  (v1.MOUNT_X_MM + v1.STEM_DIAMETER_MM/2 + v1.ANTI_ROTATION_RIB_RADIAL_MM/2,
                   v1.MOUNT_Y_MM, rib_bottom + rib_height/2))
    base = cq.Compound.makeCompound([cap, broad_stem, rib, magnet, plunger_envelope])
    return v10._motion_with_capture_flange(base, rest_z)


@dataclass(frozen=True, slots=True)
class PrimaryControlHapticArchitectureV11:
    predecessor: v10.PrimaryControlHapticArchitectureV10 = field(repr=False, compare=False)
    material_parts: tuple[tuple[str, cq.Shape], ...] = field(repr=False, compare=False)
    reference_parts: tuple[tuple[str, cq.Shape], ...] = field(repr=False, compare=False)
    motion_sweep: cq.Shape = field(repr=False, compare=False)
    spring_metrics: dict[str, float] = field(default_factory=dict)
    plunger_rest_moving_intersection_mm3: float = 0.0
    plunger_event_moving_intersection_mm3: float = 0.0
    plunger_rest_shell_intersection_mm3: float = 0.0
    plunger_event_shell_intersection_mm3: float = 0.0
    keepout_intersections_mm3: dict[str, float] = field(default_factory=dict)
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        self.predecessor.__post_init__()
        if self.predecessor.source_main_sha != SOURCE_MAIN_SHA:
            raise PrimaryControlHapticV11Error("V11 source-main mismatch")
        if self.physical_validation_eligible:
            raise PrimaryControlHapticV11Error("digital tactile geometry is not physical validation")
        if not (0.0 < PLUNGER_REST_GAP_TO_DOME_MM <= MAX_PRECONTACT_DEAD_TRAVEL_MM):
            raise PrimaryControlHapticV11Error("pre-contact dome travel is outside low-slack target")
        if LOST_MOTION_TO_HARD_STOP_MM <= 0.0:
            raise PrimaryControlHapticV11Error("protected post-contact lost motion was lost")
        if self.spring_metrics["rest_preload_compression_mm"] <= 0.0:
            raise PrimaryControlHapticV11Error("plunger spring must remain preloaded at rest")
        if self.spring_metrics["solid_height_clearance_mm"] < MIN_SPRING_SOLID_CLEARANCE_MM:
            raise PrimaryControlHapticV11Error("spring reaches solid height too closely")
        if self.spring_metrics["incremental_force_over_lost_motion_N"] > MAX_INCREMENTAL_LOST_MOTION_FORCE_N:
            raise PrimaryControlHapticV11Error("spring adds excessive post-contact force proxy")
        for value in (
            self.plunger_rest_moving_intersection_mm3,
            self.plunger_event_moving_intersection_mm3,
            self.plunger_rest_shell_intersection_mm3,
            self.plunger_event_shell_intersection_mm3,
        ):
            if value > _INTERSECTION_TOLERANCE_MM3:
                raise PrimaryControlHapticV11Error("near-contact plunger has forbidden rigid collision")
        if any(value > _INTERSECTION_TOLERANCE_MM3 for value in self.keepout_intersections_mm3.values()):
            raise PrimaryControlHapticV11Error("V11 primary-control module intersects released keepout")

    @property
    def architecture_sha256(self) -> str:
        payload = json.dumps(self.manifest(False), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        return hashlib.sha256(payload).hexdigest()

    def manifest(self, include_sha: bool = True) -> dict[str, object]:
        predecessor = self.predecessor.manifest()
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "source_main_sha": SOURCE_MAIN_SHA,
            "supersedes": v10.SCHEMA,
            "architecture_status": "REJECTED_SERIES_FORCE_PATH",
            "functional_architecture_eligible": False,
            "force_path_screen": force_path_screen(),
            "touch_surface": appearance_contract(),
            "predecessor_capture_and_return_hierarchy": predecessor["return_hierarchy"],
            "predecessor_diaphragm": predecessor["diaphragm"],
            "tactile_slack_correction": {
                "v9_v10_rest_gap_mm": v9.PLUNGER_REST_GAP_TO_DOME_MM,
                "v11_rest_gap_mm": PLUNGER_REST_GAP_TO_DOME_MM,
                "maximum_precontact_dead_travel_mm": MAX_PRECONTACT_DEAD_TRAVEL_MM,
                "conservative_dome_bottom_event_mm": DOME_BOTTOM_EVENT_MM,
                "protected_lost_motion_to_hard_stop_mm": LOST_MOTION_TO_HARD_STOP_MM,
                "spring_chamber_extended": False,
                "side_hall_package_relocated": False,
                "rest_pose_status": "DRAWN_REFERENCE_NOT_STATIC_EQUILIBRIUM",
                "head_to_retaining_ledge_axial_clearance_mm": v9.PLUNGER_HEAD_Z0_FROM_TRIM_MM - v9.PLUNGER_RETAINING_LEDGE_FROM_TRIM_MM,
            },
            "lost_motion_spring_screen": self.spring_metrics,
            "lost_motion_spring_screen_scope": "CONDITIONAL_COLLAPSED_DOME_GEOMETRY_ONLY_NOT_ACTUATION_PROOF",
            "motion_reference_scope": {
                "plunger_construction": "EXACT_UNION_OF_AXIAL_CYLINDER_SWEEPS",
                "plunger_translation_upper_bound_mm": v1.HARD_STOP_MM + v9.PLUNGER_HEAD_Z0_FROM_TRIM_MM - v9.PLUNGER_RETAINING_LEDGE_FROM_TRIM_MM,
                "assembly_collision_free": False,
                "reason": "REFERENCE_COVERAGE_IS_NOT_A_FORCE_SUPPORTED_TRAJECTORY_OR_ASSEMBLY_CLEARANCE_PROOF",
            },
            "collision_evidence_mm3": {
                "plunger_rest_vs_moving": self.plunger_rest_moving_intersection_mm3,
                "plunger_event_vs_hard_moving": self.plunger_event_moving_intersection_mm3,
                "plunger_rest_vs_shell": self.plunger_rest_shell_intersection_mm3,
                "plunger_event_vs_shell": self.plunger_event_shell_intersection_mm3,
            },
            "tactile_sequence_status": "INTENT_ONLY_DOME_BREAK_BLOCKED_BY_FORCE_PATH",
            "tactile_sequence": (
                "LOW_SLACK_DUAL_GUIDANCE -> <=0.04_MM_PLUNGER_APPROACH -> DOME_FORCE_BUILD_AND_BREAK -> "
                "PROTECTED_LOST_MOTION -> PROGRESSIVE_ELASTOMER_LANDING -> CONTROLLED_DIAPHRAGM_RETURN -> "
                "SOFT_REST_DATUM_WITH_POSITIVE_ABUSE_CAPTURE"
            ),
            "cost_rule": (
                "REUSE_V10_GUIDES_DIAPHRAGM_CAPTURE; REMOVE_UNQUALIFIED_INERTIA_INSERT_AND_ITS_THIN_SKIN; "
                "SOLID_POLYMER_TOUCH_FACE; DOME_SERIES_FORCE_PATH_REJECTED; "
                "NO_SENSOR_MOVE_NO_EXTRA_CARRIER_NO_EXTRA_FASTENER"
            ),
            "tactile_reference_rule": "S_T_DUPONT_LIGNE_2_PRECISION_FEEL_ONLY_NOT_SOUND_OR_MECHANISM_COPY",
            "keepout_intersections_mm3": self.keepout_intersections_mm3,
            "material_parts": [name for name, _shape in self.material_parts],
            "reference_parts": [name for name, _shape in self.reference_parts],
            "physical_validation_eligible": False,
            "physical_validation": (
                "OPEN_SPRING_SUPPLIER_WIRE_PROCESS_RATE_TOLERANCE_BUCKLING_FATIGUE_DOME_FORCE_TRAVEL_"
                "HYSTERESIS_GUIDE_FRICTION_RETURN_FORCE_REBOUND_SOUND_WET_AGING_LIFETIME_AND_SUBJECTIVE_FEEL"
            ),
        }
        if include_sha:
            payload["architecture_sha256"] = self.architecture_sha256
        return payload


def build_primary_control_haptic_architecture_v11(
    *, model: MasckOneModel | None = None,
) -> PrimaryControlHapticArchitectureV11:
    model = build_model() if model is None else model
    base = v10.build_primary_control_haptic_architecture_v10(model=model)
    base.__post_init__()
    material = dict(base.material_parts)

    plunger = _near_contact_plunger(base.rest_cap_underside_z_mm)
    spring, spring_metrics = _spring_screen(base.rest_cap_underside_z_mm)
    material_parts = _replace_named(base.material_parts, "tactile_lost_motion_plunger", plunger)
    moving = refine_touch_surface(material["primary_control_cap_stem"], base.rest_cap_underside_z_mm)
    material_parts = _replace_named(material_parts, "primary_control_cap_stem", moving)
    material_parts = tuple((name, shape) for name, shape in material_parts if name != "cap_inertia_core")
    reference_parts = _replace_named(base.reference_parts, "lost_motion_spring_envelope_reference", spring)
    motion = _continuous_motion_reference(base.rest_cap_underside_z_mm)
    reference_parts = _replace_named(reference_parts, "cap_motion_sweep", motion)

    shell = material["shell_with_primary_control_interface"]
    main_hard = moving.translate((0.0, 0.0, -v1.HARD_STOP_MM))
    plunger_event = plunger.translate((0.0, 0.0, -DOME_BOTTOM_EVENT_MM))

    rest_moving = v1._intersection_volume(plunger, moving)
    event_moving = v1._intersection_volume(plunger_event, main_hard)
    rest_shell = v1._intersection_volume(plunger, shell)
    event_shell = v1._intersection_volume(plunger_event, shell)
    # All current non-shell material is screened, including the solid polymer
    # replacing the removed insert. Do not pass a fictitious core to V9's list.
    module = cq.Compound.makeCompound(
        [shape for name, shape in material_parts if name != "shell_with_primary_control_interface"]
        + [shape for name, shape in reference_parts if name != "cap_motion_sweep"]
    )
    keepouts = {
        name: round(v1._intersection_volume(module, target), 8)
        for name, target in v9._keepout_shapes(model).items()
    }

    result = PrimaryControlHapticArchitectureV11(
        base,
        material_parts,
        reference_parts,
        motion,
        spring_metrics,
        round(rest_moving, 9),
        round(event_moving, 9),
        round(rest_shell, 9),
        round(event_shell, 9),
        keepouts,
        False,
    )
    result.__post_init__()
    return result


def export_primary_control_haptic_architecture_v11(output_dir: Path, *, purpose: str = "inspection") -> dict[str, object]:
    if purpose == "functional":
        require_functional_architecture()
    if purpose != "inspection":
        raise PrimaryControlHapticV11Error("export purpose must be inspection or functional")
    output_dir.mkdir(parents=True, exist_ok=True)
    architecture = build_primary_control_haptic_architecture_v11()
    for name, shape in architecture.material_parts:
        cq.exporters.export(shape, str(output_dir / f"{name}_MANUFACTURED.step"))
    for name, shape in architecture.reference_parts:
        cq.exporters.export(shape, str(output_dir / f"{name}_REFERENCE.step"))
    manifest = architecture.manifest()
    (output_dir / "primary_control_haptic_v11_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest
