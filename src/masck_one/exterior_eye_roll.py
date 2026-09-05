from __future__ import annotations

"""Authority-bound rigid eye inner-edge roll for the Cell 2 exterior.

The visible Prompt 08-11 exterior A-surface is preserved.  The current 1.8 mm shell is
locally backed only on the wearer side of each eye opening so the authority 3.0 mm
inner-edge roll can be realized without adding an exterior bezel, insert, panel break,
or raised aperture ring.  This remains deterministic digital geometry, not comfort,
fit, impact, tooling, material, or physical-safety evidence.
"""

import cadquery as cq

from .anatomy import FacialReferenceLayer
from .authority import Authority
from .exterior_construction import constructed_exterior_sections
from .exterior_inferior_turnover import (
    build_inferior_turnover_exterior_shell,
    inferior_turnover_constraints,
)
from .exterior_surface import (
    _add_profile,
    _ellipse_cutter,
    anterior_crown_boundary_z_mm,
)


SCHEMA = "MASCK_ONE_CELL2_EYE_INNER_EDGE_ROLL_V1"

# Cell 2 deterministic construction reserves. These are not new product requirements.
# The support band remains hidden behind the existing A-surface and is only wide enough
# to give the roll operator stable local material around the controlled visual aperture.
EYE_ROLL_SUPPORT_BAND_MM = 5.5
EYE_ROLL_SUPPORT_DEPTH_RESERVE_MM = 0.40
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
    total_depth = wall_mm + roll_radius_mm + EYE_ROLL_SUPPORT_DEPTH_RESERVE_MM
    nominal_crown = face.thicken(wall_mm)
    deeper_crown = face.thicken(total_depth)
    if not nominal_crown.isValid() or not deeper_crown.isValid():
        raise EyeInnerRollError("eye-roll support thickening failed")

    # Remove the already-present nominal wall so this patch adds only hidden wearer-side
    # backing material.  This keeps the exterior A-surface and its highlight field intact.
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

    # The exact controlled visual edge remains on the anterior A-surface.  The edge with
    # the lowest mean Z is therefore the wearer-side edge to roll.  This avoids brittle
    # face/edge numbering while preserving canonical +Z anterior semantics.
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
        raise EyeInnerRollError("wearer-side eye edge is not posterior to visual edge")
    return wearer


def build_eye_rolled_exterior_shell(
    authority: Authority,
    facial_reference: FacialReferenceLayer,
) -> cq.Workplane:
    """Return the current Cell 2 shell with the authority eye inner-edge roll realized."""
    base = build_inferior_turnover_exterior_shell(authority, facial_reference).val()
    _single_valid(base, "pre-roll exterior")

    wall = authority.number("geometry", "shell_nominal_wall_mm")
    roll_radius = authority.number("geometry", "eye", "inner_edge_roll_radius_mm")
    eye_width, eye_height = authority.pair(
        "geometry", "eye", "visual_aperture_wh_mm"
    )
    cant = authority.number("geometry", "eye", "lateral_cant_deg")
    left = facial_reference.eye_pair.left.point_xy
    right = facial_reference.eye_pair.right.point_xy
    face = _final_crown_face(authority, facial_reference)

    supported = base
    for x_mm, y_mm, angle_deg in (
        (left.x, left.y, -cant),
        (right.x, right.y, cant),
    ):
        patch = _posterior_eye_support_patch(
            face,
            wall_mm=wall,
            roll_radius_mm=roll_radius,
            eye_width_mm=eye_width,
            eye_height_mm=eye_height,
            eye_x_mm=x_mm,
            eye_y_mm=y_mm,
            eye_cant_deg=angle_deg,
        )
        supported = supported.fuse(patch)
        _single_valid(supported, "exterior with hidden eye support")

    # Re-cut the exact authority visual apertures after adding hidden backing material.
    shell = cq.Workplane(obj=supported)
    shell = shell.cut(
        _ellipse_cutter(
            eye_width,
            eye_height,
            left.x,
            left.y,
            angle_deg=-cant,
        )
    )
    shell = shell.cut(
        _ellipse_cutter(
            eye_width,
            eye_height,
            right.x,
            right.y,
            angle_deg=cant,
        )
    )
    pre_roll = _single_valid(shell.val(), "supported eye-aperture exterior")

    roll_edges = [
        _wearer_side_eye_edge(
            pre_roll,
            eye_width_mm=eye_width,
            eye_height_mm=eye_height,
            eye_x_mm=left.x,
            eye_y_mm=left.y,
        ),
        _wearer_side_eye_edge(
            pre_roll,
            eye_width_mm=eye_width,
            eye_height_mm=eye_height,
            eye_x_mm=right.x,
            eye_y_mm=right.y,
        ),
    ]
    rolled = pre_roll.fillet(roll_radius, roll_edges)
    _single_valid(rolled, "eye-rolled exterior")
    return cq.Workplane(obj=rolled)


def eye_inner_roll_manifest(authority: Authority) -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "radius_mm": authority.number(
            "geometry", "eye", "inner_edge_roll_radius_mm"
        ),
        "visual_aperture_wh_mm": list(
            authority.pair("geometry", "eye", "visual_aperture_wh_mm")
        ),
        "lateral_cant_deg": authority.number(
            "geometry", "eye", "lateral_cant_deg"
        ),
        "support_band_mm": EYE_ROLL_SUPPORT_BAND_MM,
        "support_depth_reserve_mm": EYE_ROLL_SUPPORT_DEPTH_RESERVE_MM,
        "support_location": "WEARER_SIDE_ONLY_BEHIND_EXISTING_A_SURFACE",
        "visual_aperture_policy": "AUTHORITY_VISUAL_OPENING_RE_CUT_EXACTLY_AFTER_SUPPORT",
        "visible_bezel_added": False,
        "external_a_surface_modified_by_support": False,
        "construction": "LOCAL_POSTERIOR_SUPPORT_PLUS_EXACT_WEARER_SIDE_EDGE_FILLET",
        "evidence_status": (
            "DIGITAL_AUTHORITY_GEOMETRY_NOT_FIT_COMFORT_IMPACT_TOOLING_MATERIAL_OR_PHYSICAL_SAFETY_EVIDENCE"
        ),
    }
