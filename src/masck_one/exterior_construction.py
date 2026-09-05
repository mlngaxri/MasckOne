from __future__ import annotations

"""Final Cell 2 exterior construction for the current MVP candidate.

The released/base exterior surface remains the source for perimeter character, Y
proportion and anterior facial-field shaping. This module applies the bounded Prompt 08
cheek/temple A-surface tightening and a localized rear B-side wall reserve to the final
integrated rigid shell. It is deterministic digital CAD evidence, not production-tooling,
fit, comfort, seal or CMF validation.
"""

import math

import cadquery as cq

from .anatomy import FacialReferenceLayer
from .authority import Authority
from .exterior_surface import (
    ANTERIOR_CAVITY_CUT_THROUGH_MM,
    _add_profile,
    _build_anterior_crown,
    _ellipse_cutter,
    _nostril_diameter,
    _profile_loft,
    _profile_points,
    anterior_crown_boundary_z_mm,
    exterior_sections,
)


# Prompt 08 side-body A-surface. The rear datum and overall Y silhouette are preserved;
# only X mass at the cheek/temple stations is reduced. Peak mass remains at Z=16 and
# the anterior perimeter remains materially smaller so the result cannot regress to a pod.
CHEEK_TEMPLE_SCALE_X = (1.000, 1.020, 1.028, 1.036, 1.004)

# Keep the package-clearing rear cavity datum from the accepted pre-wall-fix candidate.
# Wall reserve is restored locally at strongly lateral/superior regions instead of
# globally shifting the cavity anteriorly into the released waste cartridge.
REAR_INNER_Z_OFFSET_MM = -0.60
REAR_SIDE_EXTRA_INSET_X_MM = 0.40
REAR_SUPERIOR_EXTRA_INSET_Y_MM = 0.30
REAR_SIDE_WEIGHT_ZERO_NORM = 0.50
REAR_SIDE_WEIGHT_FULL_NORM = 0.68
REAR_SUPERIOR_WEIGHT_ZERO_NORM = 0.65
REAR_SUPERIOR_WEIGHT_FULL_NORM = 0.85


def constructed_exterior_sections(
    authority: Authority,
) -> tuple[tuple[float, float, float], ...]:
    """Return final side-body stations after bounded cheek/temple tightening."""
    base = exterior_sections(authority)
    outer_w, _ = authority.pair("geometry", "outer_xy_envelope_mm")
    frame_w, _ = authority.pair("geometry", "functional_frame_xy_mm")
    widths = tuple(min(outer_w, frame_w * scale) for scale in CHEEK_TEMPLE_SCALE_X)
    return tuple(
        (base[index][0], widths[index], base[index][2])
        for index in range(len(base))
    )


def _smoothstep_weight(value: float, zero_at: float, full_at: float) -> float:
    magnitude = abs(value)
    if magnitude <= zero_at:
        return 0.0
    if magnitude >= full_at:
        return 1.0
    t = (magnitude - zero_at) / (full_at - zero_at)
    return 3.0 * t * t - 2.0 * t * t * t


def _rear_inner_profile_points(
    width: float,
    height: float,
    wall: float,
) -> tuple[tuple[float, float], ...]:
    """Add B-side reserve outside the central/inferior cartridge occupancy."""
    points = _profile_points(width - 2.0 * wall, height - 2.0 * wall)
    result: list[tuple[float, float]] = []
    half_width = width / 2.0
    half_height = height / 2.0

    for x, y in points:
        x_norm = x / half_width
        y_norm = y / half_height

        side_weight = _smoothstep_weight(
            x_norm,
            REAR_SIDE_WEIGHT_ZERO_NORM,
            REAR_SIDE_WEIGHT_FULL_NORM,
        )
        if abs(x) > 1e-12:
            x -= math.copysign(REAR_SIDE_EXTRA_INSET_X_MM * side_weight, x)

        if y_norm > 0.0:
            superior_weight = _smoothstep_weight(
                y_norm,
                REAR_SUPERIOR_WEIGHT_ZERO_NORM,
                REAR_SUPERIOR_WEIGHT_FULL_NORM,
            )
            y -= REAR_SUPERIOR_EXTRA_INSET_Y_MM * superior_weight

        result.append((x, y))

    return tuple(result)


def _add_profile_points(
    workplane: cq.Workplane,
    points: tuple[tuple[float, float], ...],
) -> cq.Workplane:
    return workplane.moveTo(*points[0]).spline(points[1:], includeCurrent=True).close()


def _build_corrected_inner_cavity(
    authority: Authority,
    sections: tuple[tuple[float, float, float], ...],
) -> cq.Workplane:
    wall = authority.number("geometry", "shell_nominal_wall_mm")
    z0, width0, height0 = sections[0]
    rear_z = z0 + REAR_INNER_Z_OFFSET_MM
    result = _add_profile_points(
        cq.Workplane("XY").workplane(offset=rear_z),
        _rear_inner_profile_points(width0, height0, wall),
    )
    previous_z = rear_z

    for z, width, height in sections[1:]:
        result = _add_profile(
            result.workplane(offset=z - previous_z),
            width - 2.0 * wall,
            height - 2.0 * wall,
        )
        previous_z = z

    _, final_width, final_height = sections[-1]
    result = _add_profile(
        result.workplane(offset=ANTERIOR_CAVITY_CUT_THROUGH_MM),
        final_width - 2.0 * wall,
        final_height - 2.0 * wall,
    )
    return result.loft(combine=True, ruled=False)


def build_constructed_exterior_shell(
    authority: Authority,
    facial_reference: FacialReferenceLayer,
) -> cq.Workplane:
    """Build the final Cell 2 MVP candidate shell."""
    wall = authority.number("geometry", "shell_nominal_wall_mm")
    outer_sections = constructed_exterior_sections(authority)
    side_body = _profile_loft(outer_sections).cut(
        _build_corrected_inner_cavity(authority, outer_sections)
    )

    _, final_width, final_height = outer_sections[-1]
    crown = _build_anterior_crown(
        final_width,
        final_height,
        wall,
        anterior_crown_boundary_z_mm(authority),
        facial_reference,
    )
    fused = side_body.solids().val().fuse(crown)
    if not fused.isValid() or len(fused.Solids()) != 1:
        raise ValueError(
            "Constructed exterior side body and crown must fuse to one valid solid"
        )
    shell = cq.Workplane(obj=fused)

    eye_w, eye_h = authority.pair("geometry", "eye", "visual_aperture_wh_mm")
    cant = authority.number("geometry", "eye", "lateral_cant_deg")
    left_eye = facial_reference.eye_pair.left.point_xy
    right_eye = facial_reference.eye_pair.right.point_xy
    shell = shell.cut(
        _ellipse_cutter(eye_w, eye_h, left_eye.x, left_eye.y, angle_deg=-cant)
    )
    shell = shell.cut(
        _ellipse_cutter(eye_w, eye_h, right_eye.x, right_eye.y, angle_deg=cant)
    )

    mouth_w, mouth_h = authority.pair("geometry", "mouth", "visual_aperture_wh_mm")
    mouth = facial_reference.mouth_center.point_xy
    shell = shell.cut(_ellipse_cutter(mouth_w, mouth_h, mouth.x, mouth.y))

    nostril_d = _nostril_diameter(authority)
    for landmark in (
        facial_reference.nostril_pair.left,
        facial_reference.nostril_pair.right,
    ):
        point = landmark.point_xy
        cutter = (
            cq.Workplane("XY")
            .workplane(offset=-6.0)
            .center(point.x, point.y)
            .circle(nostril_d / 2.0)
            .extrude(40.0)
        )
        shell = shell.cut(cutter)

    if shell.solids().size() != 1 or not shell.val().isValid():
        raise ValueError(
            "Constructed exterior must remain one valid solid after aperture cuts"
        )
    return shell


def exterior_construction_manifest(authority: Authority) -> dict[str, object]:
    base_sections = exterior_sections(authority)
    final_sections = constructed_exterior_sections(authority)
    return {
        "schema": "MASCK_ONE_CELL2_EXTERIOR_CONSTRUCTION_V2",
        "cheek_temple_scale_x": list(CHEEK_TEMPLE_SCALE_X),
        "base_width_mm": [section[1] for section in base_sections],
        "final_width_mm": [section[1] for section in final_sections],
        "height_mm": [section[2] for section in final_sections],
        "rear_inner_z_offset_mm": REAR_INNER_Z_OFFSET_MM,
        "rear_side_extra_inset_x_mm": REAR_SIDE_EXTRA_INSET_X_MM,
        "rear_superior_extra_inset_y_mm": REAR_SUPERIOR_EXTRA_INSET_Y_MM,
        "rear_side_weight_norm": [
            REAR_SIDE_WEIGHT_ZERO_NORM,
            REAR_SIDE_WEIGHT_FULL_NORM,
        ],
        "rear_superior_weight_norm": [
            REAR_SUPERIOR_WEIGHT_ZERO_NORM,
            REAR_SUPERIOR_WEIGHT_FULL_NORM,
        ],
        "absolute_development_min_mm": authority.number(
            "geometry", "shell_absolute_development_min_mm"
        ),
        "massing_policy": (
            "TIGHTEN_CHEEK_TEMPLE_X_MASS_PRESERVE_Y_SILHOUETTE_AND_ANTERIOR_TAPER"
        ),
        "wall_policy": (
            "LOCALIZED_REAR_B_SIDE_RESERVE_PRESERVE_CENTRAL_INFERIOR_PACKAGE_BAND"
        ),
        "evidence_status": (
            "DIGITAL_EXTERIOR_CONSTRUCTION_NOT_FIT_TOOLING_OR_PHYSICAL_EVIDENCE"
        ),
    }
