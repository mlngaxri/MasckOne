from __future__ import annotations

"""Authority-bound rigid eye inner-edge roll for the Cell 2 exterior.

The visible Prompt 08-11 exterior A-surface is preserved. Released protected-face
geometry requires rigid material to clear the eye hard envelope, so the authority 3.0 mm
rigid edge treatment is applied to that hard rigid opening rather than to the smaller
controlled visual-aperture reference. The future non-rigid visible interface that may
resolve the visual aperture remains intentionally unmodelled.
"""

import cadquery as cq

from .anatomy import FacialReferenceLayer
from .authority import Authority
from .exterior_construction import constructed_exterior_sections
from .exterior_inferior_turnover import (
    build_inferior_turnover_exterior_shell,
    inferior_turnover_constraints,
)
from .exterior_rigid_clearance import (
    build_current_protected_volumes,
    cut_rigid_hard_envelopes,
)
from .exterior_surface import (
    _add_profile,
    _ellipse_cutter,
    anterior_crown_boundary_z_mm,
)
from .protected_volumes import ProtectedVolumeSet


SCHEMA = "MASCK_ONE_CELL2_EYE_INNER_EDGE_ROLL_V2"

# Cell 2 deterministic construction reserves. These are not new product requirements.
# The support band remains hidden behind the existing A-surface and is only wide enough
# to give the roll operator stable local material around the released rigid hard opening.
EYE_ROLL_SUPPORT_BAND_MM = 5.5
EYE_ROLL_SUPPORT_DEPTH_RESERVE_MM = 0.20
EYE_ROLL_MAX_ADDED_VOLUME_MM3 = 2500.0
EYE_EDGE_CENTER_TOLERANCE_MM = 2.0
EYE_EDGE_MIN_X_SPAN_FACTOR = 0.85
EYE_EDGE_MAX_X_SPAN_FACTOR = 1.20
EYE_EDGE_MIN_Y_SPAN_FACTOR = 0.85
EYE_EDGE_MAX_Y_SPAN_FACTOR = 1.25


class EyeInnerRollError(ValueError):
    pass


def _single_valid(shape: cq.Shape, label: str) -> cq.Shape:
    if not shape.isValid() or len(shape.Solids()) != 1 or float(shape.Volume()) <= 0.0:
        raise EyeInnerRollError(f"{label} must be one valid positive-volume solid")
    return shape


def _final_crown_face(
    authority: Authority,
    facial_reference: FacialReferenceLayer,
) -> cq.Face:
    sections = constructed_exterior_sections(authority)
    _, width, height = sections[-1]
    boundary_z = anterior_crown_boundary_z_mm(authority)
    boundary = _add_profile(
        cq.Workplane("XY").workplane(offset=boundary_z),
        width,
        height,
    )
    constraints = inferior_turnover_constraints(
        authority,
        facial_reference,
        width,
        height,
        boundary_z,
    )
    face = (
        cq.Workplane("XY")
        .interpPlate(
            boundary,
            constraints,
            thickness=0.0,
            combine=False,
            degree=3,
            nbPtsOnCur=20,
            nbIter=3,
        )
        .val()
    )
    if not isinstance(face, cq.Face) or not face.isValid():
        raise EyeInnerRollError("final exterior crown A-surface must be one valid face")
    return face


def _supported_eye_depth_mm(wall_mm: float, roll_radius_mm: float) -> float:
    if wall_mm <= 0.0 or roll_radius_mm <= 0.0:
        raise EyeInnerRollError("eye-roll wall and radius must be positive")
    return max(wall_mm, roll_radius_mm + EYE_ROLL_SUPPORT_DEPTH_RESERVE_MM)


def _posterior_eye_support_patch(
    face: cq.Face,
    *,
    wall_mm: float,
    roll_radius_mm: float,
    eye_width_mm: float,
    eye_height_mm: float,
    eye_x_mm: float,
    eye_y_mm: float,
    eye_cant_deg: float,
) -> cq.Shape:
    total_depth = _supported_eye_depth_mm(wall_mm, roll_radius_mm)
    nominal_crown = face.thicken(wall_mm)
    deeper_crown = face.thicken(total_depth)
    if not nominal_crown.isValid() or not deeper_crown.isValid():
        raise EyeInnerRollError("eye-roll support thickening failed")

    # Remove the already-present nominal wall so this patch adds only hidden wearer-side
    # backing material. This keeps the exterior A-surface and its highlight field intact.
    posterior_delta = deeper_crown.cut(nominal_crown)
    outer_support = _ellipse_cutter(
        eye_width_mm + 2.0 * EYE_ROLL_SUPPORT_BAND_MM,
        eye_height_mm + 2.0 * EYE_ROLL_SUPPORT_BAND_MM,
        eye_x_mm,
        eye_y_mm,
        angle_deg=eye_cant_deg,
    ).val()
    patch = posterior_delta.intersect(outer_support)
    return _single_valid(patch, "posterior eye-roll support patch")


def _wearer_side_eye_edge(
    shape: cq.Shape,
    *,
    eye_width_mm: float,
    eye_height_mm: float,
    eye_x_mm: float,
    eye_y_mm: float,
) -> cq.Edge:
    candidates: list[cq.Edge] = []
    for edge in shape.Edges():
        if edge.geomType() not in {"ELLIPSE", "BSPLINE"}:
            continue
        bb = edge.BoundingBox()
        center_x = 0.5 * (float(bb.xmin) + float(bb.xmax))
        center_y = 0.5 * (float(bb.ymin) + float(bb.ymax))
        if abs(center_x - eye_x_mm) > EYE_EDGE_CENTER_TOLERANCE_MM:
            continue
        if abs(center_y - eye_y_mm) > EYE_EDGE_CENTER_TOLERANCE_MM:
            continue
        if not (
            eye_width_mm * EYE_EDGE_MIN_X_SPAN_FACTOR
            <= float(bb.xlen)
            <= eye_width_mm * EYE_EDGE_MAX_X_SPAN_FACTOR
        ):
            continue
        if not (
            eye_height_mm * EYE_EDGE_MIN_Y_SPAN_FACTOR
            <= float(bb.ylen)
            <= eye_height_mm * EYE_EDGE_MAX_Y_SPAN_FACTOR
        ):
            continue
        candidates.append(edge)

    if len(candidates) < 2:
        raise EyeInnerRollError(
            f"expected at least two eye-aperture edges near ({eye_x_mm}, {eye_y_mm}); "
            f"found {len(candidates)}"
        )

    ranked = sorted(
        candidates,
        key=lambda edge: 0.5
        * (float(edge.BoundingBox().zmin) + float(edge.BoundingBox().zmax)),
    )
    wearer = ranked[0]
    wearer_mean_z = 0.5 * (
        float(wearer.BoundingBox().zmin) + float(wearer.BoundingBox().zmax)
    )
    anterior_mean_z = 0.5 * (
        float(ranked[-1].BoundingBox().zmin) + float(ranked[-1].BoundingBox().zmax)
    )
    if wearer_mean_z >= anterior_mean_z:
        raise EyeInnerRollError("wearer-side eye edge is not posterior to rigid opening edge")
    return wearer


def build_eye_rolled_exterior_shell(
    authority: Authority,
    facial_reference: FacialReferenceLayer,
    protected_volumes: ProtectedVolumeSet | None = None,
) -> cq.Workplane:
    """Return the current Cell 2 shell with hard-envelope clearance and rigid eye roll."""
    protected = protected_volumes or build_current_protected_volumes(
        authority,
        facial_reference,
    )
    base = build_inferior_turnover_exterior_shell(
        authority,
        facial_reference,
        protected,
    ).val()
    _single_valid(base, "pre-roll exterior")

    wall = authority.number("geometry", "shell_nominal_wall_mm")
    roll_radius = authority.number("geometry", "eye", "inner_edge_roll_radius_mm")
    left_zone = protected.eye_left.zone
    right_zone = protected.eye_right.zone
    face = _final_crown_face(authority, facial_reference)

    supported = base
    for zone in (left_zone, right_zone):
        patch = _posterior_eye_support_patch(
            face,
            wall_mm=wall,
            roll_radius_mm=roll_radius,
            eye_width_mm=zone.envelope_width_mm,
            eye_height_mm=zone.envelope_height_mm,
            eye_x_mm=zone.center.x,
            eye_y_mm=zone.center.y,
            eye_cant_deg=zone.angle_deg,
        )
        supported = supported.fuse(patch)
        _single_valid(supported, "exterior with hidden eye support")

    # Hidden backing can intrude into the protected footprint. Re-apply all five exact
    # released hard-envelope cuts before selecting the wearer-side rigid eye edges.
    shell = cut_rigid_hard_envelopes(cq.Workplane(obj=supported), protected)
    pre_roll = _single_valid(shell.val(), "supported protected-clearance exterior")

    roll_edges = [
        _wearer_side_eye_edge(
            pre_roll,
            eye_width_mm=zone.envelope_width_mm,
            eye_height_mm=zone.envelope_height_mm,
            eye_x_mm=zone.center.x,
            eye_y_mm=zone.center.y,
        )
        for zone in (left_zone, right_zone)
    ]
    rolled = pre_roll.fillet(roll_radius, roll_edges)
    _single_valid(rolled, "eye-rolled exterior")

    # Filleting the wearer-side edge removes material, so it cannot invade the original
    # hard footprint. This final cut is intentionally redundant and fail-closed against
    # CAD-kernel edge behavior changes.
    final_shell = cut_rigid_hard_envelopes(cq.Workplane(obj=rolled), protected).val()
    _single_valid(final_shell, "final protected-clearance eye-rolled exterior")

    added_volume = float(final_shell.Volume()) - float(base.Volume())
    if added_volume <= 0.0 or added_volume > EYE_ROLL_MAX_ADDED_VOLUME_MM3:
        raise EyeInnerRollError(
            "eye-roll hidden support added volume is outside the bounded Cell 2 reserve"
        )
    return cq.Workplane(obj=final_shell)


def eye_inner_roll_manifest(authority: Authority) -> dict[str, object]:
    wall = authority.number("geometry", "shell_nominal_wall_mm")
    radius = authority.number("geometry", "eye", "inner_edge_roll_radius_mm")
    visual_width, visual_height = authority.pair(
        "geometry", "eye", "visual_aperture_wh_mm"
    )
    rigid_clearance = authority.number(
        "geometry", "eye", "rigid_dynamic_keepout_clearance_mm"
    )
    supported_depth = _supported_eye_depth_mm(wall, radius)
    return {
        "schema": SCHEMA,
        "radius_mm": radius,
        "visual_aperture_wh_mm": [visual_width, visual_height],
        "rigid_hard_envelope_wh_mm": [
            visual_width + 2.0 * rigid_clearance,
            visual_height + 2.0 * rigid_clearance,
        ],
        "rigid_dynamic_keepout_clearance_mm": rigid_clearance,
        "lateral_cant_deg": authority.number(
            "geometry", "eye", "lateral_cant_deg"
        ),
        "support_band_mm": EYE_ROLL_SUPPORT_BAND_MM,
        "support_depth_reserve_mm": EYE_ROLL_SUPPORT_DEPTH_RESERVE_MM,
        "supported_local_depth_mm": supported_depth,
        "hidden_added_depth_mm": supported_depth - wall,
        "max_added_volume_mm3": EYE_ROLL_MAX_ADDED_VOLUME_MM3,
        "support_location": "WEARER_SIDE_ONLY_BEHIND_EXISTING_A_SURFACE",
        "rigid_edge_policy": "AUTHORITY_ROLL_APPLIED_TO_RELEASED_RIGID_HARD_ENVELOPE_EDGE",
        "visual_aperture_policy": (
            "CONTROLLED_REFERENCE_REQUIRES_FUTURE_NONRIGID_VISIBLE_INTERFACE;"
            "NOT_REALIZED_AS_RIGID_MATERIAL"
        ),
        "visible_bezel_added": False,
        "external_a_surface_modified_by_support": False,
        "construction": "LOCAL_POSTERIOR_SUPPORT_PLUS_EXACT_WEARER_SIDE_RIGID_EDGE_FILLET",
        "evidence_status": (
            "DIGITAL_AUTHORITY_GEOMETRY_NOT_FIT_COMFORT_IMPACT_TOOLING_MATERIAL_OR_PHYSICAL_SAFETY_EVIDENCE"
        ),
    }
