"""One current passive control touch surface, preserving the brand's mark profile.

The surface is solid polymer beneath a shallow dish. A spherical offset makes
the deboss depth follow that dish rather than disappear at its centre. The
unqualified inertia insert is omitted: no acoustic benefit has been measured,
and its cavity left only 0.055 mm polymer at the centre of the old touch face.
"""

import math
import cadquery as cq

from . import primary_control_haptic as base

EDGE_ROUND_MM = 0.10
MIN_TOUCH_FACE_POLYMER_MM = 0.50


def datum_segment(p0, p1, width, depth, z_center):
    midpoint = ((p0[0]+p1[0])/2, (p0[1]+p1[1])/2, z_center)
    angle = math.degrees(math.atan2(p1[1]-p0[1], p1[0]-p0[0]))
    body = base._box(math.dist(p0, p1)+width*0.35, width, depth, midpoint)
    return body.rotate(midpoint, (midpoint[0], midpoint[1], midpoint[2]+1), angle)


def mark_profile(top_z):
    half_w, half_h = base.M_CUT_WIDTH_MM/2, base.M_CUT_HEIGHT_MM/2
    endpoints = [((-half_w,-half_h),(-half_w,half_h)),
                 ((-half_w,half_h),(-0.32,0.05)),
                 ((0.32,0.05),(half_w,half_h)),
                 ((half_w,half_h),(half_w,-half_h))]
    return cq.Compound.makeCompound([
        datum_segment((base.MOUNT_X_MM+a[0], base.MOUNT_Y_MM+a[1]),
                      (base.MOUNT_X_MM+b[0], base.MOUNT_Y_MM+b[1]),
                      base.M_CUT_STROKE_MM, base.M_CUT_DEBOSS_MM+0.05, top_z-base.M_CUT_DEBOSS_MM/2)
        for a,b in endpoints
    ])


def dish_radius_mm() -> float:
    return ((base.CAP_DIAMETER_MM / 2)**2 + base.FINGER_DISH_SAG_MM**2) / (2 * base.FINGER_DISH_SAG_MM)


def dish_surface_z(top_z: float, radius_mm: float) -> float:
    radius = dish_radius_mm()
    return top_z + radius - base.FINGER_DISH_SAG_MM - math.sqrt(radius**2 - radius_mm**2)


def conformal_mark_cutter(top_z: float) -> cq.Shape:
    # Native Fusion intent: project the existing planar mark onto the spherical
    # dish; terminate at the same sphere shifted -Z by the controlled depth.
    profile = mark_profile(top_z)
    lower = top_z - base.FINGER_DISH_SAG_MM - base.M_CUT_DEBOSS_MM - 0.02
    upper = top_z + 0.03
    prisms = []
    for segment in profile.Solids():
        planar = sorted(segment.Faces(), key=lambda face: face.Center().z)[0]
        wire = planar.outerWire().translate((0, 0, lower - planar.Center().z))
        prisms.append(cq.Solid.extrudeLinear(wire, [], (0, 0, upper - lower)))
    radius = dish_radius_mm()
    sphere = cq.Solid.makeSphere(
        radius,
        cq.Vector(base.MOUNT_X_MM, base.MOUNT_Y_MM, top_z + radius - base.FINGER_DISH_SAG_MM - base.M_CUT_DEBOSS_MM),
        angleDegrees1=-90, angleDegrees2=90,
    )
    # Unite the planar profile before clipping to the curved depth surface.
    # Overlapping, independently curved cutters otherwise create redundant
    # coincident faces at the mark's corners and pathological Boolean work.
    profile_union = prisms[0]
    for prism in prisms[1:]:
        profile_union = profile_union.fuse(prism)
    cutter = profile_union.clean().intersect(sphere).clean()
    if not cutter.isValid() or not cutter.Solids() or cutter.Volume() <= 0:
        raise base.PrimaryControlHapticError("dish-conformal mark requires a positive profile cutter")
    return cutter


def refine_touch_surface(moving: cq.Shape, rest_z: float) -> cq.Shape:
    top_z = rest_z + base.CAP_THICKNESS_MM
    # Filling the existing cap first heals both the old mark and the unsupported
    # insert cavity without changing any geometry below the cap underside datum.
    full_cap = base._cylinder(base.CAP_DIAMETER_MM, base.CAP_THICKNESS_MM, rest_z)
    result = base._dish_cap(moving.fuse(full_cap).clean(), top_z)
    rim = [edge for edge in result.Edges()
           if edge.geomType() == "CIRCLE"
           and abs(edge.Center().z - top_z) < 1e-7
           and abs(edge.Length() - math.pi * base.CAP_DIAMETER_MM) < 1e-6]
    if len(rim) != 1:
        raise base.PrimaryControlHapticError("touch rim must resolve from the actual outer circle datum")
    result = result.fillet(EDGE_ROUND_MM, rim)
    result = result.cut(conformal_mark_cutter(top_z)).clean()
    if not result.isValid() or len(result.Solids()) != 1 or result.Volume() <= 0:
        raise base.PrimaryControlHapticError("refined touch surface must remain one positive polymer part")
    return result


def appearance_contract() -> dict[str, object]:
    brand = base.load_brand_identity().data
    old_skin = (base.CAP_THICKNESS_MM - base.INERTIA_CORE_THICKNESS_MM) / 2 - base.FINGER_DISH_SAG_MM
    return {
        "source_brand_revision": brand["brand"]["revision"],
        "palette": brand["cmf"]["palette"]["primary_control"],
        "material_family": brand["cmf"]["material_families"]["primary_control_cap"],
        "cap_diameter_mm": base.CAP_DIAMETER_MM,
        "cap_thickness_mm": base.CAP_THICKNESS_MM,
        "dish_sag_mm": base.FINGER_DISH_SAG_MM,
        "dish_radius_mm": dish_radius_mm(),
        "rim_round_mm": EDGE_ROUND_MM,
        "deboss_depth_vertical_mm": base.M_CUT_DEBOSS_MM,
        "deboss_projection": "EXISTING_MARK_ON_DISH_TO_TRANSLATED_SPHERICAL_FLOOR",
        "former_minimum_skin_above_core_mm": old_skin,
        "new_conservative_polymer_below_mark_mm": base.CAP_THICKNESS_MM - base.FINGER_DISH_SAG_MM - base.M_CUT_DEBOSS_MM,
        "inertia_core_selected": False,
        "manufacturing_parts_removed": ["cap_inertia_core"],
        "native_fusion_features": ["AXIAL_CAP_CYLINDER", "SPHERICAL_FINGER_DISH", "DATUM_SELECTED_OUTER_RIM_ROUND", "PROJECTED_MARK_WITH_OFFSET_SPHERICAL_FLOOR"],
        "physical_validation": "POLYMER_GRADE_MOLDING_SINK_CHEMICAL_RESISTANCE_TOUCH_STIFFNESS_WEAR_AND_FEEL_UNQUALIFIED",
    }
