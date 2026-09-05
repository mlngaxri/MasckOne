from __future__ import annotations

"""Cell 2 controlled exterior-shell geometry for Masck One.

This module owns only the visible rigid exterior form. It uses stable profile points,
controlled Z stations, a smooth non-ruled side loft and an interpolated anterior crown
instead of face/edge indexing. The surface is a digital MVP exterior candidate, not
production Class-A, tooling, fit, comfort, seal, cleanability or CMF durability evidence.
"""

import math

import cadquery as cq

from .anatomy import FacialReferenceLayer
from .authority import Authority


EXTERIOR_Z_STATIONS_MM = (0.0, 4.5, 10.0, 16.0, 22.0)
EXTERIOR_SCALE_X = (1.000, 1.010, 1.022, 1.030, 1.034)
EXTERIOR_SCALE_Y = (1.000, 1.006, 1.014, 1.020, 1.024)

# Normalized wearer-right half profile, superior to inferior. The profile is mirrored
# about X=0. The upper field stays broad, while jaw/chin mass reduces continuously.
# This deliberately rejects the released generic ellipse / late-flare visual language.
PROFILE_RIGHT = (
    (0.00, 1.000),
    (0.52, 0.985),
    (0.84, 0.900),
    (0.98, 0.720),
    (1.00, 0.480),
    (0.97, 0.240),
    (0.94, 0.000),
    (0.91, -0.240),
    (0.85, -0.480),
    (0.74, -0.700),
    (0.56, -0.880),
    (0.30, -0.985),
    (0.00, -1.000),
)

# The wearer-side cavity extends slightly behind the development plane so the rigid
# shell stays open and recessive on the wearer side.
INNER_WEARER_SIDE_OFFSET_MM = -0.6

# The five-station side body terminates at Z=22 mm. A broad shallow interpolated crown
# closes that open anterior perimeter and removes the prototype-like planar facial plate.
# The 0.10 mm join overlap is a numerical Boolean construction allowance only. It is
# not a product seam, tolerance, manufacturing allowance or physical validation value.
ANTERIOR_CROWN_HEIGHT_MM = 5.8
ANTERIOR_CROWN_JOIN_OVERLAP_MM = 0.10
ANTERIOR_CAVITY_CUT_THROUGH_MM = 1.0
ANTERIOR_CROWN_RADIAL_X_NORM = 0.525
ANTERIOR_CROWN_RADIAL_Y_NORM = 0.520
ANTERIOR_CROWN_RADIAL_LIMIT_SQ = 0.82
ANTERIOR_CROWN_FALLOFF_POWER = 1.15
ANTERIOR_CROWN_SAMPLE_X_NORM = (-0.31, -0.155, 0.0, 0.155, 0.31)
ANTERIOR_CROWN_SAMPLE_Y_NORM = (-0.36, -0.24, -0.12, 0.0, 0.12, 0.24, 0.36)
ANTERIOR_CROWN_RELIEF_MIN_MM = 5.2
ANTERIOR_CROWN_RELIEF_MAX_MM = 6.4

# Small compound-shape amplitudes remove a single nose-like dome peak while preserving
# one broad facial field. Positions are derived from live facial landmarks and widths
# scale from the current outer profile. These are Cell 2 digital form parameters only.
ANTERIOR_BROW_CHEEK_LIFT_MM = 0.55
ANTERIOR_NASAL_VALLEY_MM = 1.05
ANTERIOR_LOWER_FACE_LIFT_MM = 0.42
ANTERIOR_BROW_CENTER_Y_OFFSET_NORM = -0.025
ANTERIOR_BROW_SPREAD_X_NORM = 0.300
ANTERIOR_BROW_SPREAD_Y_NORM = 0.165
ANTERIOR_NASAL_SPREAD_X_NORM = 0.174
ANTERIOR_NASAL_SPREAD_Y_NORM = 0.121
ANTERIOR_LOWER_SPREAD_X_NORM = 0.298
ANTERIOR_LOWER_SPREAD_Y_NORM = 0.164


def _profile_points(width: float, height: float) -> tuple[tuple[float, float], ...]:
    if width <= 0.0 or height <= 0.0:
        raise ValueError("Exterior profile dimensions must be positive")
    right = tuple((x * width / 2.0, y * height / 2.0) for x, y in PROFILE_RIGHT)
    left = tuple((-x, y) for x, y in reversed(right[1:-1]))
    return right + left


def _add_profile(wp: cq.Workplane, width: float, height: float) -> cq.Workplane:
    points = _profile_points(width, height)
    return wp.moveTo(*points[0]).spline(points[1:], includeCurrent=True).close()


def _profile_loft(sections: tuple[tuple[float, float, float], ...]) -> cq.Workplane:
    """Build one smooth non-ruled loft through controlled facial-profile stations."""
    if len(sections) < 4:
        raise ValueError("Exterior surface requires at least four authored stations")
    z0, w0, h0 = sections[0]
    result = _add_profile(cq.Workplane("XY").workplane(offset=z0), w0, h0)
    previous_z = z0
    for z, width, height in sections[1:]:
        if z <= previous_z or width <= 0.0 or height <= 0.0:
            raise ValueError("Exterior stations must be positive and strictly ordered")
        result = _add_profile(result.workplane(offset=z - previous_z), width, height)
        previous_z = z
    return result.loft(combine=True, ruled=False)


def _ellipse_cutter(
    width: float,
    height: float,
    x: float,
    y: float,
    *,
    angle_deg: float = 0.0,
) -> cq.Workplane:
    cutter = (
        cq.Workplane("XY")
        .workplane(offset=-6.0)
        .center(x, y)
        .ellipse(width / 2.0, height / 2.0)
        .extrude(40.0)
    )
    if angle_deg:
        cutter = cutter.rotate((x, y, 0.0), (x, y, 1.0), angle_deg)
    return cutter


def _nostril_diameter(authority: Authority) -> float:
    area = authority.number("geometry", "nostrils", "minimum_deformed_area_each_mm2")
    local = authority.number("geometry", "nostrils", "minimum_local_opening_dimension_mm")
    return max(local, math.sqrt(4.0 * area * 1.02 / math.pi))


def exterior_sections(authority: Authority) -> tuple[tuple[float, float, float], ...]:
    """Return the authority-bounded outer station set used by the side body."""
    outer_w, outer_h = authority.pair("geometry", "outer_xy_envelope_mm")
    frame_w, frame_h = authority.pair("geometry", "functional_frame_xy_mm")
    widths = tuple(min(outer_w, frame_w * scale) for scale in EXTERIOR_SCALE_X)
    heights = tuple(min(outer_h, frame_h * scale) for scale in EXTERIOR_SCALE_Y)
    return tuple(zip(EXTERIOR_Z_STATIONS_MM, widths, heights))


def anterior_crown_boundary_z_mm(authority: Authority) -> float:
    del authority
    return EXTERIOR_Z_STATIONS_MM[-1] - ANTERIOR_CROWN_JOIN_OVERLAP_MM


def anterior_crown_inner_min_z_mm(authority: Authority) -> float:
    """Conservative Z start of new crown material for package-clearance regressions."""
    wall = authority.number("geometry", "shell_nominal_wall_mm")
    return anterior_crown_boundary_z_mm(authority) - wall


def _anterior_crown_constraints(
    width: float,
    height: float,
    boundary_z: float,
    facial_reference: FacialReferenceLayer,
) -> tuple[tuple[float, float, float], ...]:
    radial_x = width * ANTERIOR_CROWN_RADIAL_X_NORM
    radial_y = height * ANTERIOR_CROWN_RADIAL_Y_NORM
    if radial_x <= 0.0 or radial_y <= 0.0:
        raise ValueError("Anterior crown radial scales must be positive")

    eye_y = 0.5 * (
        facial_reference.eye_pair.left.point_xy.y + facial_reference.eye_pair.right.point_xy.y
    )
    nostril_y = 0.5 * (
        facial_reference.nostril_pair.left.point_xy.y + facial_reference.nostril_pair.right.point_xy.y
    )
    mouth_y = facial_reference.mouth_center.point_xy.y
    brow_y = eye_y + ANTERIOR_BROW_CENTER_Y_OFFSET_NORM * height

    brow_spread_x = width * ANTERIOR_BROW_SPREAD_X_NORM
    brow_spread_y = height * ANTERIOR_BROW_SPREAD_Y_NORM
    nasal_spread_x = width * ANTERIOR_NASAL_SPREAD_X_NORM
    nasal_spread_y = height * ANTERIOR_NASAL_SPREAD_Y_NORM
    lower_spread_x = width * ANTERIOR_LOWER_SPREAD_X_NORM
    lower_spread_y = height * ANTERIOR_LOWER_SPREAD_Y_NORM

    points: list[tuple[float, float, float]] = []
    for y_norm in ANTERIOR_CROWN_SAMPLE_Y_NORM:
        y = y_norm * height
        for x_norm in ANTERIOR_CROWN_SAMPLE_X_NORM:
            x = x_norm * width
            radial_sq = (x / radial_x) ** 2 + (y / radial_y) ** 2
            if radial_sq < ANTERIOR_CROWN_RADIAL_LIMIT_SQ:
                base = ANTERIOR_CROWN_HEIGHT_MM * (1.0 - radial_sq) ** ANTERIOR_CROWN_FALLOFF_POWER
                brow_cheek = ANTERIOR_BROW_CHEEK_LIFT_MM * math.exp(
                    -((y - brow_y) / brow_spread_y) ** 2
                ) * (0.78 + 0.22 * min(1.0, (x / brow_spread_x) ** 2))
                nasal_valley = -ANTERIOR_NASAL_VALLEY_MM * math.exp(
                    -(x / nasal_spread_x) ** 2 - ((y - nostril_y) / nasal_spread_y) ** 2
                )
                lower_face = ANTERIOR_LOWER_FACE_LIFT_MM * math.exp(
                    -(x / lower_spread_x) ** 2 - ((y - mouth_y) / lower_spread_y) ** 2
                )
                z = boundary_z + base + brow_cheek + nasal_valley + lower_face
                points.append((x, y, z))
    if len(points) < 12:
        raise ValueError("Anterior crown requires a stable interior constraint field")
    return tuple(points)


def _build_anterior_crown(
    width: float,
    height: float,
    wall: float,
    boundary_z: float,
    facial_reference: FacialReferenceLayer,
) -> cq.Shape:
    boundary = _add_profile(cq.Workplane("XY").workplane(offset=boundary_z), width, height)
    constraints = _anterior_crown_constraints(width, height, boundary_z, facial_reference)
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
    crown = face.thicken(wall)
    if not crown.isValid() or len(crown.Solids()) != 1:
        raise ValueError("Anterior crown must resolve as one valid thickened B-rep solid")
    return crown


def build_refined_exterior_shell(
    authority: Authority,
    facial_reference: FacialReferenceLayer,
) -> cq.Workplane:
    """Return the Cell 2 smooth shell with authority-backed protected apertures."""
    wall = authority.number("geometry", "shell_nominal_wall_mm")
    outer_sections = exterior_sections(authority)

    # Cut the side-body cavity through the anterior station. This removes the previous
    # planar facial cap instead of thickening or wrapping the shell around package space.
    inner_sections: list[tuple[float, float, float]] = []
    final_index = len(outer_sections) - 1
    for index, (z, width, height) in enumerate(outer_sections):
        inner_z = z + INNER_WEARER_SIDE_OFFSET_MM if index == 0 else z
        inner_sections.append((inner_z, width - 2.0 * wall, height - 2.0 * wall))
        if index == final_index:
            inner_sections.append(
                (
                    z + ANTERIOR_CAVITY_CUT_THROUGH_MM,
                    width - 2.0 * wall,
                    height - 2.0 * wall,
                )
            )

    side_body = _profile_loft(outer_sections).cut(_profile_loft(tuple(inner_sections)))
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
        raise ValueError("Exterior side body and anterior crown must fuse into one valid solid")
    shell = cq.Workplane(obj=fused)

    eye_w, eye_h = authority.pair("geometry", "eye", "visual_aperture_wh_mm")
    cant = authority.number("geometry", "eye", "lateral_cant_deg")
    left_eye = facial_reference.eye_pair.left.point_xy
    right_eye = facial_reference.eye_pair.right.point_xy
    shell = shell.cut(_ellipse_cutter(eye_w, eye_h, left_eye.x, left_eye.y, angle_deg=-cant))
    shell = shell.cut(_ellipse_cutter(eye_w, eye_h, right_eye.x, right_eye.y, angle_deg=cant))

    mouth_w, mouth_h = authority.pair("geometry", "mouth", "visual_aperture_wh_mm")
    mouth = facial_reference.mouth_center.point_xy
    shell = shell.cut(_ellipse_cutter(mouth_w, mouth_h, mouth.x, mouth.y))

    nostril_d = _nostril_diameter(authority)
    for landmark in (facial_reference.nostril_pair.left, facial_reference.nostril_pair.right):
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
        raise ValueError("Refined exterior must remain one valid B-rep solid after protected-aperture cuts")
    return shell


def exterior_surface_manifest(authority: Authority) -> dict[str, object]:
    """Deterministic handoff values without promoting physical validation claims."""
    sections = exterior_sections(authority)
    return {
        "schema": "MASCK_ONE_CELL2_EXTERIOR_SURFACE_V2",
        "z_stations_mm": [section[0] for section in sections],
        "nominal_width_mm": [section[1] for section in sections],
        "nominal_height_mm": [section[2] for section in sections],
        "profile_right_normalized": [list(point) for point in PROFILE_RIGHT],
        "loft_mode": "smooth_non_ruled_profile_spline_with_interpolated_anterior_crown",
        "anterior_crown": {
            "height_mm": ANTERIOR_CROWN_HEIGHT_MM,
            "boundary_z_mm": anterior_crown_boundary_z_mm(authority),
            "inner_min_z_mm": anterior_crown_inner_min_z_mm(authority),
            "radial_x_norm": ANTERIOR_CROWN_RADIAL_X_NORM,
            "radial_y_norm": ANTERIOR_CROWN_RADIAL_Y_NORM,
            "falloff_power": ANTERIOR_CROWN_FALLOFF_POWER,
            "visible_relief_guard_mm": [
                ANTERIOR_CROWN_RELIEF_MIN_MM,
                ANTERIOR_CROWN_RELIEF_MAX_MM,
            ],
            "construction": "INTERPOLATED_PLATE_THICKENED_TO_NOMINAL_SHELL_WALL",
            "compound_shaping": "BROW_CHEEK_LIFT_RECESSIVE_NASAL_VALLEY_CONTINUOUS_LOWER_FACE",
            "join_overlap_mm": ANTERIOR_CROWN_JOIN_OVERLAP_MM,
            "join_overlap_status": "NUMERICAL_BOOLEAN_CONSTRUCTION_ONLY",
        },
        "visible_face_policy": "CURVED_ANTERIOR_FACIAL_FIELD_WITH_AUTHORITY_BACKED_APERTURES",
        "design_intent": {
            "facial_field": "broad_continuous_low_gradient_compound_crown",
            "perimeter": "broad_temples_tapered_jaw_soft_chin",
            "side_mass": "laterally_blended_not_podded",
            "rear_mass": "close_and_recessive",
            "nasal_read": "recessive_not_respirator",
            "visible_feature_count": "minimal",
        },
        "evidence_status": "DIGITAL_CAD_MVP_EXTERIOR_NOT_CLASS_A_OR_PHYSICAL_EVIDENCE",
    }
