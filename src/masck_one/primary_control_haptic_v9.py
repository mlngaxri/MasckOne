from __future__ import annotations

"""Primary-control V9: captive lost-motion tactile cartridge.

V8 removed the rear Hall collision but still carried the rejected custom short-beam
spring. V9 removes that spring stack and realizes a package for a small standard
stamped tactile-dome coupon without allowing the long Masck button stroke to crush it.

The broad guided stem is shortened only behind the lower guide. A captive 1.4 mm
polymer plunger lives in a stepped axial cavity and is held against its capture ledge
by a tiny always-preloaded compression-spring envelope. The plunger follows the main
button through the tactile event, then remains at the collapsed-dome datum while the
main button continues through protected lost motion into the progressive elastomer
landing and independent rigid abuse stop.

A rear shell extension carries a vented dome seat. The obsolete tactile-spring shelf
and snap-retainer groove are explicitly superseded rather than left as stale geometry.
The stamped dome, retention film and lost-motion spring remain supplier/coupon
references, not production-selected parts. Force-travel, hysteresis, spring dynamics,
acoustics, fatigue, contamination and subjective feel remain physical validation.
"""

from dataclasses import dataclass, field
import hashlib
import json
import math
from pathlib import Path

import cadquery as cq

from . import primary_control_haptic as v1
from . import primary_control_haptic_v8 as v8
from .model import MasckOneModel, build_model

SCHEMA = "MASCK_ONE_PRIMARY_CONTROL_HAPTIC_V9"
SOURCE_MAIN_SHA = v8.SOURCE_MAIN_SHA

# Current package/coupon seed. Supplier part is not frozen in the BOM.
DOME_BENCHMARK_VENDOR = "Snaptron"
DOME_BENCHMARK_PART = "F06130"
DOME_DIAMETER_MM = 6.00
DOME_HEIGHT_MM = 0.30
DOME_TRIP_FORCE_GF = 130.0
DOME_TRIP_FORCE_TOLERANCE_GF = 30.0
DOME_PUBLISHED_LIFE_CYCLES = 5_000_000
DOME_MAX_ACTUATOR_FRACTION = 0.25

# Broad stem remains positively through the complete lower guide at rest, but no
# longer enters the fixed tactile-cartridge plane at full hard-stop travel.
STEM_REAR_FROM_REST_MM = 5.27
MIN_STEM_BEHIND_LOWER_GUIDE_AT_REST_MM = 0.10
MIN_BROAD_STEM_TO_DOME_CLEARANCE_AT_HARD_STOP_MM = 0.06

NEW_BARREL_REAR_FROM_REST_MM = 6.92
BARREL_EXTENSION_FORWARD_OVERLAP_MM = 0.06
DOME_SEAT_TOP_FROM_REST_MM = 6.72
DOME_SEAT_THICKNESS_MM = 0.18
DOME_SEAT_OD_MM = 8.70
DOME_SEAT_VENT_ID_MM = 2.20

PLUNGER_SHAFT_DIAMETER_MM = 1.40
PLUNGER_SHAFT_BORE_DIAMETER_MM = 1.62
PLUNGER_HEAD_DIAMETER_MM = 2.50
PLUNGER_HEAD_HEIGHT_MM = 0.28
PLUNGER_CAVITY_DIAMETER_MM = 2.90
PLUNGER_RETAINING_LEDGE_FROM_TRIM_MM = 0.20
PLUNGER_HEAD_Z0_FROM_TRIM_MM = 0.25
PLUNGER_SHAFT_TOP_FROM_TRIM_MM = 0.31
PLUNGER_CAVITY_FORWARD_FROM_TRIM_MM = 1.85
PLUNGER_REST_GAP_TO_DOME_MM = 0.22
DOME_BOTTOM_EVENT_MM = PLUNGER_REST_GAP_TO_DOME_MM + DOME_HEIGHT_MM
LOST_MOTION_TO_HARD_STOP_MM = v1.HARD_STOP_MM - DOME_BOTTOM_EVENT_MM

# First-order spring envelope only. No supplier spring is selected here.
LOST_MOTION_SPRING_WIRE_MM = 0.14
LOST_MOTION_SPRING_MEAN_COIL_MM = 2.20
LOST_MOTION_SPRING_ACTIVE_COILS = 3.0
LOST_MOTION_SPRING_TOTAL_COILS = 4.5
LOST_MOTION_SPRING_FREE_LENGTH_MM = 1.40
LOST_MOTION_SPRING_SHEAR_MODULUS_SEED_N_PER_MM2 = 77_000.0
MIN_SPRING_SOLID_CLEARANCE_MM = 0.10
MAX_INCREMENTAL_LOST_MOTION_FORCE_N = 0.08

DOME_RETENTION_FILM_OD_MM = 6.60
DOME_RETENTION_FILM_ID_MM = 1.80
DOME_RETENTION_FILM_THICKNESS_MM = 0.08
DOME_RETENTION_FILM_VENT_SPLIT_MM = 0.80

_INTERSECTION_TOLERANCE_MM3 = 1e-7


class PrimaryControlHapticV9Error(ValueError):
    pass


def _keepout_shapes(model: MasckOneModel) -> dict[str, cq.Shape]:
    return {
        **{component.name: component.solid.val() for component in model.actuator_envelopes},
        "water_reservoir_envelope": model.water_reservoir_envelope.solid.val(),
        "waste_cartridge_envelope": model.waste_cartridge_envelope.solid.val(),
        "battery_reference_envelope": model.battery_reference_envelope.solid.val(),
        **{component.name: component.solid.val() for component in model.visual_keepouts},
    }


def _remove_obsolete_tactile_shell_features(
    shell: cq.Shape,
    rest_z: float,
) -> cq.Shape:
    spring_rim_z = rest_z - v1.TACTILE_RIM_FROM_REST_MM
    old_groove_z0 = spring_rim_z + v1.TACTILE_SPRING_THICKNESS_MM - 0.02

    # Positively refill the obsolete snap-retainer undercut, then regenerate the
    # straight 8.50 mm rear bore so the old spring shelf and groove do not survive.
    groove_fill = v1._ring(
        v1.BARREL_BORE_DIAMETER_MM + 2.0 * v1.SNAP_GROOVE_DEPTH_MM + 0.04,
        v1.BARREL_BORE_DIAMETER_MM - 0.04,
        v1.SNAP_GROOVE_HEIGHT_MM + 0.04,
        old_groove_z0 - 0.02,
    )
    shell = shell.fuse(groove_fill).clean()

    rebore_z0 = rest_z - NEW_BARREL_REAR_FROM_REST_MM - 0.03
    rebore_top = rest_z - 5.30
    rebore = v1._cylinder(
        v1.BARREL_BORE_DIAMETER_MM,
        rebore_top - rebore_z0,
        rebore_z0,
    )
    shell = shell.cut(rebore).clean()
    if not shell.isValid() or not shell.Solids():
        raise PrimaryControlHapticV9Error("clearing obsolete tactile shell geometry invalidated shell")
    return shell


def _rear_cartridge_shell(
    shell: cq.Shape,
    rest_z: float,
) -> tuple[cq.Shape, cq.Shape]:
    old_rear_from_rest = v1.BARREL_REAR_EXTENSION_MM + v1.CAP_PROUD_MM
    extension_z0 = rest_z - NEW_BARREL_REAR_FROM_REST_MM
    extension_top = rest_z - old_rear_from_rest + BARREL_EXTENSION_FORWARD_OVERLAP_MM
    extension = v1._ring(
        v1.BARREL_OD_MM,
        v1.BARREL_BORE_DIAMETER_MM,
        extension_top - extension_z0,
        extension_z0,
    )
    shell = shell.fuse(extension).clean()

    dome_seat_top = rest_z - DOME_SEAT_TOP_FROM_REST_MM
    seat = v1._ring(
        DOME_SEAT_OD_MM,
        DOME_SEAT_VENT_ID_MM,
        DOME_SEAT_THICKNESS_MM,
        dome_seat_top - DOME_SEAT_THICKNESS_MM,
    )
    shell = shell.fuse(seat).clean()
    if not shell.isValid() or not shell.Solids():
        raise PrimaryControlHapticV9Error("rear tactile-cartridge shell must remain valid")
    return shell, extension


def _trim_moving_and_cut_plunger_cavity(
    moving: cq.Shape,
    rest_z: float,
) -> tuple[cq.Shape, float, float]:
    trim_z = rest_z - STEM_REAR_FROM_REST_MM
    rear_cutter = v1._box(
        20.0,
        20.0,
        10.0,
        (v1.MOUNT_X_MM, v1.MOUNT_Y_MM, trim_z - 5.0),
    )
    moving = moving.cut(rear_cutter).clean()

    shaft_bore = v1._cylinder(
        PLUNGER_SHAFT_BORE_DIAMETER_MM,
        PLUNGER_RETAINING_LEDGE_FROM_TRIM_MM + 0.10,
        trim_z - 0.05,
    )
    head_cavity = v1._cylinder(
        PLUNGER_CAVITY_DIAMETER_MM,
        PLUNGER_CAVITY_FORWARD_FROM_TRIM_MM - PLUNGER_RETAINING_LEDGE_FROM_TRIM_MM,
        trim_z + PLUNGER_RETAINING_LEDGE_FROM_TRIM_MM,
    )
    before = float(moving.Volume())
    moving = moving.cut(shaft_bore).cut(head_cavity).clean()
    removed = before - float(moving.Volume())
    if not moving.isValid() or len(moving.Solids()) != 1 or moving.Volume() <= 0.0:
        raise PrimaryControlHapticV9Error("plunger cavity invalidated primary moving polymer")
    if removed <= 0.0:
        raise PrimaryControlHapticV9Error("plunger cavity must remove positive moving-polymer volume")
    return moving, trim_z, removed


def _plunger(rest_z: float, trim_z: float) -> cq.Shape:
    dome_top_z = rest_z - DOME_SEAT_TOP_FROM_REST_MM + DOME_HEIGHT_MM
    shaft_z0 = dome_top_z + PLUNGER_REST_GAP_TO_DOME_MM
    shaft_top = trim_z + PLUNGER_SHAFT_TOP_FROM_TRIM_MM
    shaft = v1._cylinder(
        PLUNGER_SHAFT_DIAMETER_MM,
        shaft_top - shaft_z0,
        shaft_z0,
    )
    head = v1._cylinder(
        PLUNGER_HEAD_DIAMETER_MM,
        PLUNGER_HEAD_HEIGHT_MM,
        trim_z + PLUNGER_HEAD_Z0_FROM_TRIM_MM,
    )
    plunger = shaft.fuse(head).clean()
    if not plunger.isValid() or len(plunger.Solids()) != 1 or plunger.Volume() <= 0.0:
        raise PrimaryControlHapticV9Error("lost-motion plunger must be one valid manufactured solid")
    return plunger


def _dome_reference(rest_z: float) -> cq.Shape:
    seat_top = rest_z - DOME_SEAT_TOP_FROM_REST_MM
    return v1._cylinder(DOME_DIAMETER_MM, DOME_HEIGHT_MM, seat_top)


def _retention_film_reference(rest_z: float) -> cq.Shape:
    seat_top = rest_z - DOME_SEAT_TOP_FROM_REST_MM
    return v1._split_ring(
        DOME_RETENTION_FILM_OD_MM,
        DOME_RETENTION_FILM_ID_MM,
        DOME_RETENTION_FILM_THICKNESS_MM,
        seat_top + 0.02,
        DOME_RETENTION_FILM_VENT_SPLIT_MM,
    )


def _spring_screen(trim_z: float) -> tuple[cq.Shape, dict[str, float]]:
    head_top_z = trim_z + PLUNGER_HEAD_Z0_FROM_TRIM_MM + PLUNGER_HEAD_HEIGHT_MM
    cavity_roof_z = trim_z + PLUNGER_CAVITY_FORWARD_FROM_TRIM_MM
    installed = cavity_roof_z - head_top_z
    minimum = installed - LOST_MOTION_TO_HARD_STOP_MM
    solid = LOST_MOTION_SPRING_TOTAL_COILS * LOST_MOTION_SPRING_WIRE_MM
    solid_clearance = minimum - solid
    rate = (
        LOST_MOTION_SPRING_SHEAR_MODULUS_SEED_N_PER_MM2
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
        "rest_preload_compression_mm": round(preload_compression, 9),
        "rest_preload_force_proxy_N": round(preload_force, 9),
        "minimum_operating_length_mm": round(minimum, 9),
        "solid_height_mm": round(solid, 9),
        "solid_height_clearance_mm": round(solid_clearance, 9),
        "incremental_force_over_lost_motion_N": round(incremental, 9),
    }
    return envelope, metrics


def _replace_tactile_parts(
    parts: tuple[tuple[str, cq.Shape], ...],
    *,
    shell: cq.Shape,
    moving: cq.Shape,
    plunger: cq.Shape,
) -> tuple[tuple[str, cq.Shape], ...]:
    output: list[tuple[str, cq.Shape]] = []
    seen = {"shell": False, "moving": False, "spring": False, "damping": False, "retainer": False}
    for name, shape in parts:
        if name == "shell_with_primary_control_interface":
            output.append((name, shell))
            seen["shell"] = True
        elif name == "primary_control_cap_stem":
            output.append((name, moving))
            seen["moving"] = True
        elif name == "tactile_spring_formed":
            seen["spring"] = True
        elif name == "tactile_damping_annulus":
            seen["damping"] = True
        elif name == "tactile_snap_retainer":
            seen["retainer"] = True
        else:
            output.append((name, shape))
    if not all(seen.values()):
        raise PrimaryControlHapticV9Error(f"V9 donor missing required superseded tactile part: {seen}")
    output.append(("tactile_lost_motion_plunger", plunger))
    return tuple(output)


def _replace_motion_and_add_references(
    parts: tuple[tuple[str, cq.Shape], ...],
    *,
    motion: cq.Shape,
    dome: cq.Shape,
    film: cq.Shape,
    spring: cq.Shape,
) -> tuple[tuple[str, cq.Shape], ...]:
    output: list[tuple[str, cq.Shape]] = []
    saw_motion = False
    for name, shape in parts:
        if name == "cap_motion_sweep":
            output.append((name, motion))
            saw_motion = True
        else:
            output.append((name, shape))
    if not saw_motion:
        raise PrimaryControlHapticV9Error("V9 requires donor motion reference")
    output.extend(
        (
            ("tactile_dome_coupon_conservative_envelope", dome),
            ("tactile_dome_retention_film_reference", film),
            ("lost_motion_spring_envelope_reference", spring),
        )
    )
    return tuple(output)


def _continuous_motion_reference(
    rest_z: float,
    trim_z: float,
    plunger: cq.Shape,
) -> cq.Shape:
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
    plunger_bottom = plunger.translate((0.0, 0.0, -DOME_BOTTOM_EVENT_MM))
    plunger_envelope = cq.Compound.makeCompound([plunger, plunger_bottom])
    return cq.Compound.makeCompound([cap, broad_stem, magnet, plunger_envelope])


def _module_keepouts(
    model: MasckOneModel,
    material_parts: tuple[tuple[str, cq.Shape], ...],
    reference_parts: tuple[tuple[str, cq.Shape], ...],
) -> dict[str, float]:
    material = dict(material_parts)
    refs = dict(reference_parts)
    names = [
        "primary_control_cap_stem",
        "cap_inertia_core",
        "tactile_lost_motion_plunger",
        "wet_diaphragm",
        "landing_progressive_overmold",
        "sensor_magnet",
    ]
    bodies = [material[name] for name in names]
    bodies.extend(
        [
            refs["upper_split_bushing_installed_reference"],
            refs["lower_split_bushing_installed_reference"],
            refs["anti_rotation_leaf_rooted_installed_reference"],
            refs["hall_side_sensor_fpc_envelope"],
            refs["hall_flex_tail_reference"],
            refs["tactile_dome_coupon_conservative_envelope"],
            refs["tactile_dome_retention_film_reference"],
            refs["lost_motion_spring_envelope_reference"],
        ]
    )
    module = cq.Compound.makeCompound(bodies)
    return {
        name: round(v1._intersection_volume(module, target), 8)
        for name, target in _keepout_shapes(model).items()
    }


@dataclass(frozen=True, slots=True)
class PrimaryControlHapticArchitectureV9:
    source_main_sha: str
    shell_outer_z_mm: float
    rest_cap_underside_z_mm: float
    material_parts: tuple[tuple[str, cq.Shape], ...] = field(repr=False, compare=False)
    reference_parts: tuple[tuple[str, cq.Shape], ...] = field(repr=False, compare=False)
    motion_sweep: cq.Shape = field(repr=False, compare=False)
    stem_behind_lower_guide_at_rest_mm: float = 0.0
    broad_stem_to_dome_clearance_at_hard_stop_mm: float = 0.0
    plunger_cavity_removed_mm3: float = 0.0
    plunger_rest_moving_intersection_mm3: float = 0.0
    plunger_hard_moving_intersection_mm3: float = 0.0
    plunger_rest_shell_intersection_mm3: float = 0.0
    plunger_bottom_shell_intersection_mm3: float = 0.0
    main_hard_dome_intersection_mm3: float = 0.0
    dome_actuator_fraction: float = 0.0
    spring_metrics: dict[str, float] = field(default_factory=dict)
    rear_extension_keepout_intersections_mm3: dict[str, float] = field(default_factory=dict)
    keepout_intersections_mm3: dict[str, float] = field(default_factory=dict)
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        if self.source_main_sha != SOURCE_MAIN_SHA:
            raise PrimaryControlHapticV9Error("V9 source-main mismatch")
        if self.physical_validation_eligible:
            raise PrimaryControlHapticV9Error("digital tactile-cartridge geometry is not physical validation")
        if self.stem_behind_lower_guide_at_rest_mm < MIN_STEM_BEHIND_LOWER_GUIDE_AT_REST_MM:
            raise PrimaryControlHapticV9Error("trimmed stem no longer remains positively through lower guide at rest")
        if self.broad_stem_to_dome_clearance_at_hard_stop_mm < MIN_BROAD_STEM_TO_DOME_CLEARANCE_AT_HARD_STOP_MM:
            raise PrimaryControlHapticV9Error("broad stem approaches fixed dome too closely at hard stop")
        if self.plunger_cavity_removed_mm3 <= 0.0:
            raise PrimaryControlHapticV9Error("captive plunger cavity requires positive polymer removal")
        if self.dome_actuator_fraction > DOME_MAX_ACTUATOR_FRACTION:
            raise PrimaryControlHapticV9Error("dome actuator exceeds benchmark maximum diameter fraction")
        for value in (
            self.plunger_rest_moving_intersection_mm3,
            self.plunger_hard_moving_intersection_mm3,
            self.plunger_rest_shell_intersection_mm3,
            self.plunger_bottom_shell_intersection_mm3,
            self.main_hard_dome_intersection_mm3,
        ):
            if value > _INTERSECTION_TOLERANCE_MM3:
                raise PrimaryControlHapticV9Error("tactile cartridge has a forbidden positive collision")
        if self.spring_metrics["rest_preload_compression_mm"] <= 0.0:
            raise PrimaryControlHapticV9Error("lost-motion plunger spring must stay preloaded at rest")
        if self.spring_metrics["solid_height_clearance_mm"] < MIN_SPRING_SOLID_CLEARANCE_MM:
            raise PrimaryControlHapticV9Error("lost-motion spring approaches solid height too closely")
        if self.spring_metrics["incremental_force_over_lost_motion_N"] > MAX_INCREMENTAL_LOST_MOTION_FORCE_N:
            raise PrimaryControlHapticV9Error("lost-motion spring adds excessive post-snap force proxy")
        if LOST_MOTION_TO_HARD_STOP_MM <= 0.0:
            raise PrimaryControlHapticV9Error("tactile architecture lost protected post-snap travel")
        if any(value > _INTERSECTION_TOLERANCE_MM3 for value in self.rear_extension_keepout_intersections_mm3.values()):
            raise PrimaryControlHapticV9Error("rear tactile extension intersects released package keepout")
        if any(value > _INTERSECTION_TOLERANCE_MM3 for value in self.keepout_intersections_mm3.values()):
            raise PrimaryControlHapticV9Error("V9 primary-control module intersects released package keepout")
        material = dict(self.material_parts)
        refs = dict(self.reference_parts)
        for rejected in ("tactile_spring_formed", "tactile_damping_annulus", "tactile_snap_retainer"):
            if rejected in material:
                raise PrimaryControlHapticV9Error(f"superseded tactile part remains: {rejected}")
        if "tactile_lost_motion_plunger" not in material:
            raise PrimaryControlHapticV9Error("captive tactile plunger is missing")
        for required in (
            "tactile_dome_coupon_conservative_envelope",
            "tactile_dome_retention_film_reference",
            "lost_motion_spring_envelope_reference",
        ):
            if required not in refs:
                raise PrimaryControlHapticV9Error(f"missing tactile cartridge reference: {required}")

    @property
    def architecture_sha256(self) -> str:
        payload = json.dumps(self.manifest(False), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        return hashlib.sha256(payload).hexdigest()

    def manifest(self, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "source_main_sha": self.source_main_sha,
            "supersedes": "V8_REJECTED_CUSTOM_SHORT_BEAM_TACTILE_SPRING_WITHOUT_PROTECTED_POST_SNAP_LOST_MOTION",
            "coordinate_frame_id": v1.WORLD_FRAME_ID,
            "selected_package_direction": (
                "DUAL_GUIDED_PRIMARY_STEM_PLUS_CAPTIVE_PRELOADED_SMALL_PLUNGER_PLUS_STANDARD_STAMPED_DOME_COUPON_"
                "PLUS_PROTECTED_POST_SNAP_LOST_MOTION_PLUS_PROGRESSIVE_ELASTOMER_LANDING_PLUS_RIGID_ABUSE_STOP"
            ),
            "dome_coupon_benchmark": {
                "vendor": DOME_BENCHMARK_VENDOR,
                "part": DOME_BENCHMARK_PART,
                "diameter_mm": DOME_DIAMETER_MM,
                "height_mm": DOME_HEIGHT_MM,
                "trip_force_gf": DOME_TRIP_FORCE_GF,
                "trip_force_tolerance_gf": DOME_TRIP_FORCE_TOLERANCE_GF,
                "published_life_cycles_up_to": DOME_PUBLISHED_LIFE_CYCLES,
                "production_selected": False,
            },
            "stroke_sequence_mm": {
                "plunger_rest_gap_to_dome": PLUNGER_REST_GAP_TO_DOME_MM,
                "conservative_dome_bottom_event": DOME_BOTTOM_EVENT_MM,
                "nominal_bottom": v1.NOMINAL_BOTTOM_MM,
                "hard_stop": v1.HARD_STOP_MM,
                "protected_lost_motion_to_hard_stop": LOST_MOTION_TO_HARD_STOP_MM,
            },
            "guidance_and_capture": {
                "stem_rear_from_rest_mm": STEM_REAR_FROM_REST_MM,
                "stem_behind_lower_guide_at_rest_mm": self.stem_behind_lower_guide_at_rest_mm,
                "broad_stem_to_dome_clearance_at_hard_stop_mm": self.broad_stem_to_dome_clearance_at_hard_stop_mm,
                "plunger_shaft_diameter_mm": PLUNGER_SHAFT_DIAMETER_MM,
                "plunger_head_diameter_mm": PLUNGER_HEAD_DIAMETER_MM,
                "plunger_cavity_removed_mm3": self.plunger_cavity_removed_mm3,
                "plunger_captive_by_smaller_rear_throat": True,
                "dome_actuator_fraction": self.dome_actuator_fraction,
            },
            "lost_motion_spring_screen": self.spring_metrics,
            "dome_retention": {
                "architecture": "VENTED_THIN_RETENTION_FILM_REFERENCE_OVER_SHELL_INTEGRAL_VENTED_SEAT",
                "adhesive_or_lamination_process_selected": False,
                "film_thickness_mm": DOME_RETENTION_FILM_THICKNESS_MM,
                "seat_vent_id_mm": DOME_SEAT_VENT_ID_MM,
            },
            "collision_evidence_mm3": {
                "plunger_rest_vs_moving": self.plunger_rest_moving_intersection_mm3,
                "plunger_hard_vs_moving": self.plunger_hard_moving_intersection_mm3,
                "plunger_rest_vs_shell": self.plunger_rest_shell_intersection_mm3,
                "plunger_bottom_vs_shell": self.plunger_bottom_shell_intersection_mm3,
                "main_hard_vs_dome_envelope": self.main_hard_dome_intersection_mm3,
            },
            "rear_extension_keepout_intersections_mm3": self.rear_extension_keepout_intersections_mm3,
            "keepout_intersections_mm3": self.keepout_intersections_mm3,
            "tactile_reference_rule": "S_T_DUPONT_LIGNE_2_PRECISION_FEEL_ONLY_NOT_SOUND_OR_MECHANISM_COPY",
            "cost_rule": (
                "STANDARD_STAMPED_TACTILE_ELEMENT_COUPON_PLUS_ONE_SIMPLE_CAPTIVE_POLYMER_PLUNGER; "
                "NO_CUSTOM_SHORT_BEAM_SPRING; NO_MICROSWITCH; NO_EXTRA_METAL_CARRIER"
            ),
            "material_parts": [name for name, _shape in self.material_parts],
            "reference_parts": [name for name, _shape in self.reference_parts],
            "physical_validation_eligible": False,
            "physical_validation": (
                "OPEN_DOME_SUPPLIER_SELECTION_FORCE_TRAVEL_TACTILE_RATIO_HYSTERESIS_ACTUATOR_SENSITIVITY_"
                "SPRING_RATE_TOLERANCE_BUCKLING_FATIGUE_SET_DOME_RETENTION_FILM_PROCESS_VENTING_CONTAMINATION_"
                "RETURN_DYNAMICS_GUIDE_FRICTION_WOBBLE_SEALING_ACOUSTIC_RING_DECAY_LIFETIME_AND_SUBJECTIVE_FEEL"
            ),
        }
        if include_sha:
            payload["architecture_sha256"] = self.architecture_sha256
        return payload


def build_primary_control_haptic_architecture_v9(
    *,
    model: MasckOneModel | None = None,
) -> PrimaryControlHapticArchitectureV9:
    model = build_model() if model is None else model
    base = v8.build_primary_control_haptic_architecture_v8(model=model)
    base.__post_init__()
    material = dict(base.material_parts)

    shell = _remove_obsolete_tactile_shell_features(
        material["shell_with_primary_control_interface"],
        base.rest_cap_underside_z_mm,
    )
    shell, rear_extension = _rear_cartridge_shell(shell, base.rest_cap_underside_z_mm)
    moving, trim_z, cavity_removed = _trim_moving_and_cut_plunger_cavity(
        material["primary_control_cap_stem"],
        base.rest_cap_underside_z_mm,
    )
    plunger = _plunger(base.rest_cap_underside_z_mm, trim_z)
    dome = _dome_reference(base.rest_cap_underside_z_mm)
    film = _retention_film_reference(base.rest_cap_underside_z_mm)
    spring, spring_metrics = _spring_screen(trim_z)

    material_parts = _replace_tactile_parts(
        base.material_parts,
        shell=shell,
        moving=moving,
        plunger=plunger,
    )
    motion = _continuous_motion_reference(base.rest_cap_underside_z_mm, trim_z, plunger)
    reference_parts = _replace_motion_and_add_references(
        base.reference_parts,
        motion=motion,
        dome=dome,
        film=film,
        spring=spring,
    )

    lower_guide_rear_from_rest = (
        v1.LOWER_BUSHING_CENTER_FROM_REST_MM + v1.BUSHING_LENGTH_MM / 2.0
    )
    stem_behind_lower = STEM_REAR_FROM_REST_MM - lower_guide_rear_from_rest
    dome_top_from_rest = DOME_SEAT_TOP_FROM_REST_MM - DOME_HEIGHT_MM
    hard_stem_rear_from_rest = STEM_REAR_FROM_REST_MM + v1.HARD_STOP_MM
    hard_clearance = dome_top_from_rest - hard_stem_rear_from_rest

    main_hard = moving.translate((0.0, 0.0, -v1.HARD_STOP_MM))
    plunger_bottom = plunger.translate((0.0, 0.0, -DOME_BOTTOM_EVENT_MM))
    plunger_rest_moving = v1._intersection_volume(plunger, moving)
    plunger_hard_moving = v1._intersection_volume(plunger_bottom, main_hard)
    plunger_rest_shell = v1._intersection_volume(plunger, shell)
    plunger_bottom_shell = v1._intersection_volume(plunger_bottom, shell)
    main_hard_dome = v1._intersection_volume(main_hard, dome)

    rear_keepouts = {
        name: round(v1._intersection_volume(rear_extension, target), 8)
        for name, target in _keepout_shapes(model).items()
    }
    keepouts = _module_keepouts(model, material_parts, reference_parts)

    result = PrimaryControlHapticArchitectureV9(
        SOURCE_MAIN_SHA,
        base.shell_outer_z_mm,
        base.rest_cap_underside_z_mm,
        material_parts,
        reference_parts,
        motion,
        round(stem_behind_lower, 9),
        round(hard_clearance, 9),
        round(cavity_removed, 9),
        round(plunger_rest_moving, 9),
        round(plunger_hard_moving, 9),
        round(plunger_rest_shell, 9),
        round(plunger_bottom_shell, 9),
        round(main_hard_dome, 9),
        round(PLUNGER_SHAFT_DIAMETER_MM / DOME_DIAMETER_MM, 9),
        spring_metrics,
        rear_keepouts,
        keepouts,
        False,
    )
    result.__post_init__()
    return result


def export_primary_control_haptic_architecture_v9(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    architecture = build_primary_control_haptic_architecture_v9()
    for name, shape in architecture.material_parts:
        cq.exporters.export(shape, str(output_dir / f"{name}_MANUFACTURED.step"))
    for name, shape in architecture.reference_parts:
        cq.exporters.export(shape, str(output_dir / f"{name}_REFERENCE.step"))
    manifest = architecture.manifest()
    (output_dir / "primary_control_haptic_v9_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest
