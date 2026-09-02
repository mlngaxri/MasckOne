from __future__ import annotations

"""Controlled exterior-shell geometry for Masck One.

This module moves Cell 2 from appearance contracts into authored CAD.  It deliberately
uses stable section parameters and smooth lofting rather than face/edge indexing.  The
surface remains a pre-Class-A digital convergence model until physical/tooling review.
"""

import math
import cadquery as cq

from .authority import Authority
from .anatomy import FacialReferenceLayer


# Stable authored Z stations.  More stations are intentionally concentrated near the
# facial field and rear shoulder so perceived depth is controlled by broad curvature,
# not by a single ruled frustum.
EXTERIOR_Z_STATIONS_MM = (0.0, 4.5, 10.0, 16.0, 22.0)
EXTERIOR_SCALE_X = (1.000, 1.010, 1.022, 1.030, 1.034)
EXTERIOR_SCALE_Y = (1.000, 1.006, 1.014, 1.020, 1.024)

# The inner surface tracks the outer surface by the authority wall target.  These are
# topology controls, not production tolerances.
INNER_FRONT_OFFSET_MM = -0.6


def _ellipse_loft(sections: tuple[tuple[float, float, float], ...]) -> cq.Workplane:
    """Build one smooth loft through canonical ellipse stations.

    `ruled=False` is intentional.  The previous baseline used ruled lofts between only
    three stations, producing visible conical bands and tangent breaks that contradicted
    the calm continuous exterior target even when downstream numeric contracts passed.
    """
    if len(sections) < 4:
        raise ValueError("Exterior surface requires at least four authored stations")
    z0, w0, h0 = sections[0]
    result = cq.Workplane("XY").workplane(offset=z0).ellipse(w0 / 2.0, h0 / 2.0)
    previous_z = z0
    for z, width, height in sections[1:]:
        if z <= previous_z or width <= 0.0 or height <= 0.0:
            raise ValueError("Exterior stations must be positive and strictly ordered")
        result = result.workplane(offset=z - previous_z).ellipse(width / 2.0, height / 2.0)
        previous_z = z
    return result.loft(combine=True, ruled=False)


def _ellipse_cutter(width: float, height: float, x: float, y: float, *, angle_deg: float = 0.0) -> cq.Workplane:
    cutter = cq.Workplane("XY").workplane(offset=-6.0).center(x, y).ellipse(width / 2.0, height / 2.0).extrude(40.0)
    if angle_deg:
        cutter = cutter.rotate((x, y, 0.0), (x, y, 1.0), angle_deg)
    return cutter


def _nostril_diameter(authority: Authority) -> float:
    area = authority.number("geometry", "nostrils", "minimum_deformed_area_each_mm2")
    local = authority.number("geometry", "nostrils", "minimum_local_opening_dimension_mm")
    return max(local, math.sqrt(4.0 * area * 1.02 / math.pi))


def build_refined_exterior_shell(authority: Authority, facial_reference: FacialReferenceLayer) -> cq.Workplane:
    """Return the controlled smooth exterior shell with authority-backed apertures.

    The function changes only exterior Z-form generation.  Protected eye, mouth and
    nostril openings remain authority-derived, and nominal wall thickness remains
    authority-derived.  It therefore cannot cosmetically shrink protected regions or
    invent packaging volume.
    """
    outer_w, outer_h = authority.pair("geometry", "outer_xy_envelope_mm")
    frame_w, frame_h = authority.pair("geometry", "functional_frame_xy_mm")
    wall = authority.number("geometry", "shell_nominal_wall_mm")

    # Front station is governed by the functional frame.  Subsequent stations expand
    # gradually toward, but never beyond, the authoritative outer XY envelope.  This
    # removes the old 10 mm waist followed by a late 22 mm flare, a root cause of
    # plate-plus-bumper / helmet-like side reads.
    widths = tuple(min(outer_w, frame_w * s) for s in EXTERIOR_SCALE_X)
    heights = tuple(min(outer_h, frame_h * s) for s in EXTERIOR_SCALE_Y)
    outer_sections = tuple(zip(EXTERIOR_Z_STATIONS_MM, widths, heights))

    inner_sections = []
    for i, (z, width, height) in enumerate(outer_sections):
        inner_z = z + (INNER_FRONT_OFFSET_MM if i == 0 else 0.0)
        inner_sections.append((inner_z, width - 2.0 * wall, height - 2.0 * wall))

    shell = _ellipse_loft(outer_sections).cut(_ellipse_loft(tuple(inner_sections)))

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
        p = landmark.point_xy
        shell = shell.cut(cq.Workplane("XY").workplane(offset=-6.0).center(p.x, p.y).circle(nostril_d / 2.0).extrude(40.0))

    return shell


def exterior_surface_manifest(authority: Authority) -> dict[str, object]:
    """Deterministic render/CAD handoff values without claiming physical validation."""
    outer_w, outer_h = authority.pair("geometry", "outer_xy_envelope_mm")
    frame_w, frame_h = authority.pair("geometry", "functional_frame_xy_mm")
    return {
        "schema": "MASCK_ONE_EXTERIOR_SURFACE_V1",
        "z_stations_mm": list(EXTERIOR_Z_STATIONS_MM),
        "width_mm": [min(outer_w, frame_w * s) for s in EXTERIOR_SCALE_X],
        "height_mm": [min(outer_h, frame_h * s) for s in EXTERIOR_SCALE_Y],
        "loft_mode": "smooth_non_ruled",
        "evidence_status": "DIGITAL_CAD_CONVERGENCE_NOT_CLASS_A_OR_PHYSICAL_EVIDENCE",
    }
