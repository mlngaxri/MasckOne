from __future__ import annotations

"""Treatment-owned terminal kinematic seat for a low-play massage reaction path.

The existing Cell 6 rail remains deliberately clearance-fit for smooth service motion.
This module adds a *terminal* four-face taper candidate around the rigid Cell 6
8 x 8 mm reaction shoulder.  The carrier can therefore run freely on the parallel
rail for most of its stroke, then use axial seating motion to remove X/Z dead-zone
at the final installed coordinate.  The spring/detent is intended only to maintain
axial seating; alternating massage reaction is intended to pass through rigid taper
faces and the rigid shoulder.

Digital geometry and analytical screening only.  Exact contact pressure, friction,
insertion/release force, tolerance closure, wear, creep, acoustics and human-use
performance require nonlinear/physical validation.
"""

from dataclasses import dataclass, field
import hashlib
import json
import math

import cadquery as cq
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCP.gp import gp_Vec

from .model import MasckOneModel, build_model
from .structural_frame_actuator_mates import (
    SHOULDER_GAP_MM,
    SHOULDER_HEIGHT_MM,
    SHOULDER_THICKNESS_MM,
    SHOULDER_WIDTH_MM,
    StructuralFrameActuatorMateArchitecture,
    build_structural_frame_actuator_mates,
)
from .structural_frame_actuator_reactions import (
    REACTION_IDS,
    StructuralFrameActuatorReactionArchitecture,
    build_structural_frame_actuator_reactions,
)
from .structural_frame_carrier_detent import (
    BEAM_HEIGHT_MM,
    BEAM_LENGTH_MM,
    BEAM_WIDTH_MM,
)

SCHEMA = "MASCK_ONE_TREATMENT_TERMINAL_KINEMATIC_SEAT_V1"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
SOURCE_CELL6_HEAD_SHA = "fcccde02b31cc1c4e01136630d92e550e4e09a11"

# The current treatment yoke has 0.16 mm radial X running clearance and 0.12 mm
# radial Z running clearance.  The taper consumes those clearances only at the
# terminal shoulder edge, preserving a low-drag parallel approach elsewhere.
RUNNING_X_CLEARANCE_MM = 0.16
RUNNING_Z_CLEARANCE_MM = 0.12
X_TAPER_SPAN_MM = 0.58
Z_TAPER_SPAN_MM = 0.50
SEAT_PAD_WALL_MM = 0.50
X_PAD_Z_MARGIN_MM = 0.12
Z_PAD_X_WIDTH_MM = 3.20
BACK_ENVELOPE_AVAILABLE_MM = 0.63
BACK_ENVELOPE_MARGIN_MM = 0.03

# Small digital probes.  These prove the directionality of the terminal seat rather
# than production tolerance capability.
AXIAL_OVERTRAVEL_PROBE_MM = 0.05
LATERAL_ENGAGEMENT_PROBE_MM = 0.05
VERTICAL_ENGAGEMENT_PROBE_MM = 0.05
SERVICE_RETRACTION_PROBE_MM = 2.0

# Analytical-only retention screen.  0.60 N is the existing transient treatment
# force reference, not a measured force at this mount.
TRANSIENT_REACTION_REFERENCE_N = 0.60
DETENT_MODULUS_STUDY_MPA = 2500.0
DETENT_RETAINED_DEFLECTION_SEED_MM = 0.09
_INTERSECTION_TOLERANCE_MM3 = 1e-7


class TreatmentTerminalKinematicSeatError(ValueError):
    pass


def _intersection_volume(a: cq.Shape, b: cq.Shape) -> float:
    aa, bb = a.BoundingBox(), b.BoundingBox()
    if (
        aa.xmax < bb.xmin
        or bb.xmax < aa.xmin
        or aa.ymax < bb.ymin
        or bb.ymax < aa.ymin
        or aa.zmax < bb.zmin
        or bb.zmax < aa.zmin
    ):
        return 0.0
    try:
        common = a.intersect(b)
    except Exception as exc:
        raise TreatmentTerminalKinematicSeatError("intersection kernel failure") from exc
    if not common.isValid():
        raise TreatmentTerminalKinematicSeatError("invalid intersection result")
    value = sum(max(0.0, float(s.Volume())) for s in common.Solids())
    if not math.isfinite(value):
        raise TreatmentTerminalKinematicSeatError("nonfinite intersection result")
    return value


def _join(shapes: list[cq.Shape]) -> cq.Shape:
    if not shapes:
        raise TreatmentTerminalKinematicSeatError("cannot join empty seat geometry")
    result = shapes[0]
    for shape in shapes[1:]:
        result = result.fuse(shape)
    result = result.clean()
    if not result.isValid() or not result.Solids():
        raise TreatmentTerminalKinematicSeatError("seat geometry must remain valid positive material")
    return result


def _translation_envelope(shape: cq.Shape, travel: tuple[float, float, float]) -> cq.Shape:
    pieces: list[cq.Shape] = [shape, shape.translate(travel)]
    for face in shape.Faces():
        prism = cq.Shape.cast(BRepPrimAPI_MakePrism(face.wrapped, gp_Vec(*travel)).Shape())
        pieces.extend(prism.Solids())
    return _join(pieces)


def _x_taper_pad(
    *,
    cx: float,
    contact_y: float,
    shoulder_z0: float,
    sign: float,
) -> cq.Shape:
    y0 = contact_y
    y1 = contact_y + X_TAPER_SPAN_MM
    half_w = SHOULDER_WIDTH_MM / 2.0
    inner0 = cx + sign * half_w
    inner1 = cx + sign * (half_w + RUNNING_X_CLEARANCE_MM)
    outer = cx + sign * (half_w + RUNNING_X_CLEARANCE_MM + SEAT_PAD_WALL_MM)
    if sign > 0.0:
        outline = [(inner0, y0), (outer, y0), (outer, y1), (inner1, y1)]
    else:
        outline = [(outer, y0), (inner0, y0), (inner1, y1), (outer, y1)]
    z0 = shoulder_z0 - X_PAD_Z_MARGIN_MM
    height = SHOULDER_THICKNESS_MM + 2.0 * X_PAD_Z_MARGIN_MM
    return (
        cq.Workplane("XY")
        .polyline(outline)
        .close()
        .extrude(height)
        .translate((0.0, 0.0, z0))
        .val()
    )


def _z_taper_pad(
    *,
    cx: float,
    contact_y: float,
    shoulder_z0: float,
    sign: float,
) -> cq.Shape:
    y0 = contact_y
    y1 = contact_y + Z_TAPER_SPAN_MM
    contact_z = shoulder_z0 + (SHOULDER_THICKNESS_MM if sign > 0.0 else 0.0)
    clear_z = contact_z + sign * RUNNING_Z_CLEARANCE_MM
    outer_z = clear_z + sign * SEAT_PAD_WALL_MM
    if sign > 0.0:
        outline = [(y0, contact_z), (y0, outer_z), (y1, outer_z), (y1, clear_z)]
    else:
        outline = [(y0, outer_z), (y0, contact_z), (y1, clear_z), (y1, outer_z)]
    return (
        cq.Workplane("YZ", origin=(cx, 0.0, 0.0))
        .polyline(outline)
        .close()
        .extrude(Z_PAD_X_WIDTH_MM / 2.0, both=True)
        .val()
    )


def taper_half_angles_deg() -> tuple[float, float]:
    return (
        math.degrees(math.atan2(RUNNING_X_CLEARANCE_MM, X_TAPER_SPAN_MM)),
        math.degrees(math.atan2(RUNNING_Z_CLEARANCE_MM, Z_TAPER_SPAN_MM)),
    )


def detent_linear_proxy() -> dict[str, float]:
    # Cantilever screen only.  The real molded/metal beam material, root compliance,
    # large deflection, nose cam and hysteresis are not represented here.
    inertia = BEAM_WIDTH_MM * BEAM_HEIGHT_MM**3 / 12.0
    stiffness = 3.0 * DETENT_MODULUS_STUDY_MPA * inertia / BEAM_LENGTH_MM**3
    force = stiffness * DETENT_RETAINED_DEFLECTION_SEED_MM
    return {
        "second_moment_mm4": inertia,
        "linear_tip_stiffness_N_per_mm": stiffness,
        "retained_deflection_seed_mm": DETENT_RETAINED_DEFLECTION_SEED_MM,
        "retained_force_proxy_N": force,
    }


def seating_backdrive_screen() -> dict[str, float]:
    ax, az = taper_half_angles_deg()
    tx, tz = math.tan(math.radians(ax)), math.tan(math.radians(az))
    # For a fixed resultant lateral reaction, the worst vector direction for the
    # sum of the two ideal frictionless wedge back-drive components is the norm of
    # [tan(ax), tan(az)].
    worst = TRANSIENT_REACTION_REFERENCE_N * math.hypot(tx, tz)
    proxy = detent_linear_proxy()["retained_force_proxy_N"]
    return {
        "x_tan_half_angle": tx,
        "z_tan_half_angle": tz,
        "self_release_mu_threshold_x": tx,
        "self_release_mu_threshold_z": tz,
        "ideal_frictionless_transient_axial_backdrive_upper_bound_N": worst,
        "detent_retained_force_proxy_N": proxy,
        "proxy_margin_N": proxy - worst,
    }


@dataclass(frozen=True, slots=True)
class TerminalKinematicSeat:
    reaction_id: str
    center_xy_mm: tuple[float, float]
    pad_parts: tuple[tuple[str, cq.Shape], ...] = field(repr=False, compare=False)
    service_retraction_sweep: cq.Shape = field(repr=False, compare=False)
    nominal_source_intersection_mm3: float
    axial_overtravel_intersection_mm3: float
    lateral_probe_intersections_mm3: tuple[float, float]
    vertical_probe_intersections_mm3: tuple[float, float]
    service_retraction_intersection_mm3: float

    def __post_init__(self) -> None:
        if self.reaction_id not in REACTION_IDS:
            raise TreatmentTerminalKinematicSeatError("unknown reaction id")
        for name, shape in self.pad_parts:
            if not shape.isValid() or not shape.Solids() or shape.Volume() <= 0.0:
                raise TreatmentTerminalKinematicSeatError(f"invalid seat pad {name}")
        if self.nominal_source_intersection_mm3 > _INTERSECTION_TOLERANCE_MM3:
            raise TreatmentTerminalKinematicSeatError("terminal seat collides with source at nominal contact")
        if self.axial_overtravel_intersection_mm3 <= _INTERSECTION_TOLERANCE_MM3:
            raise TreatmentTerminalKinematicSeatError("terminal seat does not positively engage under axial overtravel")
        if min(self.lateral_probe_intersections_mm3) <= _INTERSECTION_TOLERANCE_MM3:
            raise TreatmentTerminalKinematicSeatError("terminal seat does not constrain both X directions")
        if min(self.vertical_probe_intersections_mm3) <= _INTERSECTION_TOLERANCE_MM3:
            raise TreatmentTerminalKinematicSeatError("terminal seat does not constrain both Z directions")
        if self.service_retraction_intersection_mm3 > _INTERSECTION_TOLERANCE_MM3:
            raise TreatmentTerminalKinematicSeatError("terminal taper does not release cleanly along +Y service motion")

    def manifest(self) -> dict[str, object]:
        ax, az = taper_half_angles_deg()
        return {
            "reaction_id": self.reaction_id,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "center_xy_mm": list(self.center_xy_mm),
            "pad_parts": [name for name, _ in self.pad_parts],
            "architecture": "PARALLEL_LOW_DRAG_APPROACH_PLUS_TERMINAL_FOUR_FACE_RIGID_TAPER_WITH_AXIAL_SEATING_BIAS",
            "working_reaction_path": "RIGID_TAPER_FACES_TO_CELL6_RIGID_SHOULDER; DETENT_MAINTAINS_AXIAL_SEATING_ONLY",
            "dimensions_mm": {
                "running_x_clearance": RUNNING_X_CLEARANCE_MM,
                "running_z_clearance": RUNNING_Z_CLEARANCE_MM,
                "x_taper_span": X_TAPER_SPAN_MM,
                "z_taper_span": Z_TAPER_SPAN_MM,
                "x_taper_half_angle_deg": ax,
                "z_taper_half_angle_deg": az,
                "back_envelope_available": BACK_ENVELOPE_AVAILABLE_MM,
                "back_envelope_margin": BACK_ENVELOPE_MARGIN_MM,
            },
            "measured": {
                "nominal_source_intersection_mm3": self.nominal_source_intersection_mm3,
                "axial_overtravel_probe_mm": AXIAL_OVERTRAVEL_PROBE_MM,
                "axial_overtravel_intersection_mm3": self.axial_overtravel_intersection_mm3,
                "lateral_probe_intersections_mm3": list(self.lateral_probe_intersections_mm3),
                "vertical_probe_intersections_mm3": list(self.vertical_probe_intersections_mm3),
                "service_retraction_probe_mm": SERVICE_RETRACTION_PROBE_MM,
                "service_retraction_intersection_mm3": self.service_retraction_intersection_mm3,
            },
            "retention_screen": seating_backdrive_screen(),
            "nominal_seated_geometric_dead_zone": "ZERO_IN_IDEAL_RIGID_DATUM_MODEL_IF_AXIAL_SEATING_IS_MAINTAINED",
            "tolerance_status": "MATCHED_CONTACT_TOLERANCE_AND_YOKE_ELASTIC_EQUALIZATION_FEA_PHYSICAL_OPEN",
            "friction_status": "SELF_RELEASE_REQUIRES_MEASURED_INTERFACE_FRICTION_BELOW_SELECTED_TAPER_THRESHOLD_OR_ARCHITECTURE_CHANGE",
            "physical_validation": "OPEN_INSERTION_RELEASE_FORCE_CONTACT_PRESSURE_WEAR_CREEP_FRICTION_ACOUSTICS_AND_WET_CYCLING",
        }


@dataclass(frozen=True, slots=True)
class TerminalKinematicSeatArchitecture:
    source_cell6_head_sha: str
    seats: tuple[TerminalKinematicSeat, ...]
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        if self.source_cell6_head_sha != SOURCE_CELL6_HEAD_SHA:
            raise TreatmentTerminalKinematicSeatError("terminal seat source binding mismatch")
        if tuple(s.reaction_id for s in self.seats) != REACTION_IDS:
            raise TreatmentTerminalKinematicSeatError("all four terminal seats required")
        if self.physical_validation_eligible:
            raise TreatmentTerminalKinematicSeatError("digital terminal seat is not physical evidence")

    @property
    def architecture_sha256(self) -> str:
        raw = json.dumps(self.manifest(False), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        return hashlib.sha256(raw).hexdigest()

    def manifest(self, include_sha: bool = True) -> dict[str, object]:
        payload = {
            "schema": SCHEMA,
            "source_cell6_head_sha": self.source_cell6_head_sha,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "seats": [s.manifest() for s in self.seats],
            "retention_screen": seating_backdrive_screen(),
            "mechanical_status": "FOUR_TERMINAL_KINEMATIC_SEAT_CANDIDATES_REALIZED_AND_DIRECTIONALLY_PROBED_IN_SOURCE_COORDINATES",
            "physical_validation_eligible": self.physical_validation_eligible,
        }
        if include_sha:
            payload["architecture_sha256"] = self.architecture_sha256
        return payload


def build_terminal_kinematic_seats(
    *,
    model: MasckOneModel | None = None,
    reactions: StructuralFrameActuatorReactionArchitecture | None = None,
    mates: StructuralFrameActuatorMateArchitecture | None = None,
) -> TerminalKinematicSeatArchitecture:
    if max(X_TAPER_SPAN_MM, Z_TAPER_SPAN_MM) > BACK_ENVELOPE_AVAILABLE_MM - BACK_ENVELOPE_MARGIN_MM + 1e-12:
        raise TreatmentTerminalKinematicSeatError("terminal taper exceeds current yoke back envelope")
    model = build_model() if model is None else model
    reactions = build_structural_frame_actuator_reactions(model=model) if reactions is None else reactions
    mates = build_structural_frame_actuator_mates(model=model, reactions=reactions) if mates is None else mates
    frame_zmax = float(reactions.frame_with_reaction_counterparts.val().BoundingBox().zmax)
    shoulder_z0 = frame_zmax + SHOULDER_GAP_MM

    built: list[TerminalKinematicSeat] = []
    for mate in mates.mates:
        cx, cy = mate.center_xy_mm
        contact_y = cy + SHOULDER_HEIGHT_MM / 2.0
        parts = (
            ("x_left_datum", _x_taper_pad(cx=cx, contact_y=contact_y, shoulder_z0=shoulder_z0, sign=-1.0)),
            ("x_right_datum", _x_taper_pad(cx=cx, contact_y=contact_y, shoulder_z0=shoulder_z0, sign=1.0)),
            ("z_lower_datum", _z_taper_pad(cx=cx, contact_y=contact_y, shoulder_z0=shoulder_z0, sign=-1.0)),
            ("z_upper_datum", _z_taper_pad(cx=cx, contact_y=contact_y, shoulder_z0=shoulder_z0, sign=1.0)),
        )
        compound = cq.Compound.makeCompound([shape for _name, shape in parts])
        source = mate.mate.val()
        nominal = _intersection_volume(compound, source)
        axial = _intersection_volume(compound.translate((0.0, -AXIAL_OVERTRAVEL_PROBE_MM, 0.0)), source)
        lateral = (
            _intersection_volume(compound.translate((-LATERAL_ENGAGEMENT_PROBE_MM, 0.0, 0.0)), source),
            _intersection_volume(compound.translate((LATERAL_ENGAGEMENT_PROBE_MM, 0.0, 0.0)), source),
        )
        vertical = (
            _intersection_volume(compound.translate((0.0, 0.0, -VERTICAL_ENGAGEMENT_PROBE_MM)), source),
            _intersection_volume(compound.translate((0.0, 0.0, VERTICAL_ENGAGEMENT_PROBE_MM)), source),
        )
        sweep = _translation_envelope(compound, (0.0, SERVICE_RETRACTION_PROBE_MM, 0.0))
        service_intersection = _intersection_volume(sweep, source)
        built.append(
            TerminalKinematicSeat(
                mate.reaction_id,
                mate.center_xy_mm,
                parts,
                sweep,
                round(nominal, 8),
                round(axial, 8),
                tuple(round(v, 8) for v in lateral),
                tuple(round(v, 8) for v in vertical),
                round(service_intersection, 8),
            )
        )
    result = TerminalKinematicSeatArchitecture(SOURCE_CELL6_HEAD_SHA, tuple(built), False)
    result.__post_init__()
    return result
