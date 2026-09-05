from __future__ import annotations

"""Final Cell 2 lower-face and side-mass refinement for the current MVP exterior.

Prompt 09 changes only the anterior rigid-shell field below the mouth. Prompt 10 then
feathers the anterior crown progressively posterior through the temple/upper-cheek band.
The accepted Prompt 08 side-body stations, rear cavity, package band and perimeter
footprint are preserved exactly. The soft-interface geometry remains unresolved rather
than being invented by this aesthetic pass.
"""

import math

import cadquery as cq

from .anatomy import FacialReferenceLayer
from .authority import Authority
from .exterior_construction import (
    _build_corrected_inner_cavity,
    constructed_exterior_sections,
    exterior_construction_manifest,
)
from .exterior_rigid_clearance import (
    build_current_protected_volumes,
    cut_rigid_hard_envelopes,
)
from .exterior_surface import (
    _add_profile,
    _anterior_crown_constraints,
    _profile_loft,
    anterior_crown_boundary_z_mm,
)
from .protected_volumes import ProtectedVolumeSet


# Prompt 09: a broad, shallow anterior-only setback lightens the chin turnover without
# shrinking the cartridge band or moving the perimeter that will ultimately meet the soft
# interface.
INFERIOR_TURNOVER_EXTRA_RECESS_MM = 0.50
INFERIOR_TURNOVER_CENTER_Y_OFFSET_FROM_MOUTH_NORM = -0.180
INFERIOR_TURNOVER_SPREAD_X_NORM = 0.285
INFERIOR_TURNOVER_SPREAD_Y_NORM = 0.155

# Prompt 10: progressively feather only the anterior lateral crown. This does not shrink
# the Z=0..22 side body or move the rear/package cavity. The broad Y falloff avoids a local
# temple dent while the smooth X ramp prevents the outer crown from reading as a separate
# side plate or pod.
SIDE_MASS_FEATHER_RECESS_MM = 0.70
SIDE_MASS_FEATHER_START_X_NORM = 0.050
SIDE_MASS_FEATHER_FULL_X_NORM = 0.310
SIDE_MASS_FEATHER_CENTER_Y_NORM = 0.080
SIDE_MASS_FEATHER_SPREAD_Y_NORM = 0.300


def _smoothstep(value: float, zero_at: float, full_at: float) -> float:
    if full_at <= zero_at:
        raise ValueError("Side-mass feather full point must exceed start point")
    if value <= zero_at:
        return 0.0
    if value >= full_at:
        return 1.0
    t = (value - zero_at) / (full_at - zero_at)
    return 3.0 * t * t - 2.0 * t * t * t


def prompt09_inferior_turnover_constraints(
    authority: Authority,
    facial_reference: FacialReferenceLayer,
    width: float,
    height: float,
    boundary_z: float,
) -> tuple[tuple[float, float, float], ...]:
    """Return the accepted Prompt 09 crown controls before Prompt 10 side feathering."""
    del authority
    base = _anterior_crown_constraints(
        width,
        height,
        boundary_z,
        facial_reference,
    )
    mouth_y = facial_reference.mouth_center.point_xy.y
    center_y = mouth_y + INFERIOR_TURNOVER_CENTER_Y_OFFSET_FROM_MOUTH_NORM * height
    spread_x = width * INFERIOR_TURNOVER_SPREAD_X_NORM
    spread_y = height * INFERIOR_TURNOVER_SPREAD_Y_NORM
    if spread_x <= 0.0 or spread_y <= 0.0:
        raise ValueError("Inferior turnover spreads must be positive")

    return tuple(
        (
            x,
            y,
            z
            - INFERIOR_TURNOVER_EXTRA_RECESS_MM
            * math.exp(
                -(x / spread_x) ** 2
                - ((y - center_y) / spread_y) ** 2
            ),
        )
        for x, y, z in base
    )


def inferior_turnover_constraints(
    authority: Authority,
    facial_reference: FacialReferenceLayer,
    width: float,
    height: float,
    boundary_z: float,
) -> tuple[tuple[float, float, float], ...]:
    """Return the final Prompt 10 crown controls with broad lateral mass feathering."""
    base = prompt09_inferior_turnover_constraints(
        authority,
        facial_reference,
        width,
        height,
        boundary_z,
    )
    spread_y = height * SIDE_MASS_FEATHER_SPREAD_Y_NORM
    center_y = height * SIDE_MASS_FEATHER_CENTER_Y_NORM
    if spread_y <= 0.0:
        raise ValueError("Side-mass feather Y spread must be positive")

    result: list[tuple[float, float, float]] = []
    for x, y, z in base:
        x_norm = abs(x) / width
        lateral_weight = _smoothstep(
            x_norm,
            SIDE_MASS_FEATHER_START_X_NORM,
            SIDE_MASS_FEATHER_FULL_X_NORM,
        )
        y_weight = math.exp(-((y - center_y) / spread_y) ** 2)
        result.append(
            (
                x,
                y,
                z - SIDE_MASS_FEATHER_RECESS_MM * lateral_weight * y_weight,
            )
        )
    return tuple(result)


def _build_inferior_turnover_crown(
    authority: Authority,
    facial_reference: FacialReferenceLayer,
    width: float,
    height: float,
    wall: float,
    boundary_z: float,
) -> cq.Shape:
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
    crown = face.thicken(wall)
    if not crown.isValid() or len(crown.Solids()) != 1:
        raise ValueError("Inferior-turnover crown must resolve as one valid solid")
    return crown


def build_inferior_turnover_exterior_shell(
    authority: Authority,
    facial_reference: FacialReferenceLayer,
    protected_volumes: ProtectedVolumeSet | None = None,
) -> cq.Workplane:
    """Build the final Prompt 10 rigid shell with released hard-envelope clearance."""
    wall = authority.number("geometry", "shell_nominal_wall_mm")
    outer_sections = constructed_exterior_sections(authority)
    side_body = _profile_loft(outer_sections).cut(
        _build_corrected_inner_cavity(authority, outer_sections)
    )

    _, final_width, final_height = outer_sections[-1]
    crown = _build_inferior_turnover_crown(
        authority,
        facial_reference,
        final_width,
        final_height,
        wall,
        anterior_crown_boundary_z_mm(authority),
    )
    fused = side_body.solids().val().fuse(crown)
    if not fused.isValid() or len(fused.Solids()) != 1:
        raise ValueError(
            "Inferior-turnover side body and crown must fuse to one valid solid"
        )

    protected = protected_volumes or build_current_protected_volumes(
        authority,
        facial_reference,
    )
    shell = cut_rigid_hard_envelopes(cq.Workplane(obj=fused), protected)
    if shell.solids().size() != 1 or not shell.val().isValid():
        raise ValueError(
            "Inferior-turnover exterior must remain one valid solid after protected cuts"
        )
    return shell


def inferior_turnover_manifest(authority: Authority) -> dict[str, object]:
    """Record the bounded visual-form delta without promoting soft-interface evidence."""
    return {
        "schema": "MASCK_ONE_CELL2_INFERIOR_TURNOVER_V3",
        "source_construction": exterior_construction_manifest(authority),
        "extra_anterior_recess_mm": INFERIOR_TURNOVER_EXTRA_RECESS_MM,
        "center_y_offset_from_mouth_norm": (
            INFERIOR_TURNOVER_CENTER_Y_OFFSET_FROM_MOUTH_NORM
        ),
        "spread_x_norm": INFERIOR_TURNOVER_SPREAD_X_NORM,
        "spread_y_norm": INFERIOR_TURNOVER_SPREAD_Y_NORM,
        "side_mass_feather_recess_mm": SIDE_MASS_FEATHER_RECESS_MM,
        "side_mass_feather_start_x_norm": SIDE_MASS_FEATHER_START_X_NORM,
        "side_mass_feather_full_x_norm": SIDE_MASS_FEATHER_FULL_X_NORM,
        "side_mass_feather_center_y_norm": SIDE_MASS_FEATHER_CENTER_Y_NORM,
        "side_mass_feather_spread_y_norm": SIDE_MASS_FEATHER_SPREAD_Y_NORM,
        "side_body_station_policy": "UNCHANGED_FROM_PROMPT08",
        "rear_cavity_policy": "UNCHANGED_FROM_PROMPT08",
        "perimeter_footprint_policy": "UNCHANGED_FROM_PROMPT08",
        "rigid_protected_face_policy": "CONSUME_RELEASED_PLANAR_HARD_ENVELOPES_AS_THROUGH_CUTS",
        "soft_interface_geometry_status": "UNRESOLVED_NOT_INVENTED",
        "visual_intent": (
            "LIGHT_NEUTRAL_INFERIOR_TURNOVER_WITH_GRADUAL_TEMPLE_AND_LATERAL_CROWN_BLEND"
        ),
        "evidence_status": (
            "DIGITAL_RIGID_EXTERIOR_FORM_NOT_FIT_COMFORT_SEAL_TOOLING_OR_PHYSICAL_EVIDENCE"
        ),
    }
