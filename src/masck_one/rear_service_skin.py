from __future__ import annotations

"""Cell 2 visible rear-service skin for the current MVP exterior candidate.

This module owns only the visible rigid service skin and its cover-removal reference.
It deliberately does not turn the conservative Cell 3 central rear package keepout into
an exterior box. Battery, PCB, dry-bay structure, sealing, attachment and extraction
geometry remain owning-lane work. The smaller skin is a packaging interface target that
forces nested dry-side packaging rather than permitting a backpack-like rear enclosure.
"""

from dataclasses import dataclass
import math

import cadquery as cq

from .authority import Authority, load_authority


SCHEMA = "MASCK_ONE_CELL2_REAR_SERVICE_SKIN_V1"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
SOURCE_CELL3_RETENTION_HEAD_SHA = "5a74a129def7e96e58aa1db4c85989bbfd315a9e"
SOURCE_CELL3_OCCIPITAL_BLOB_SHA = "1139b675c4758d8580cf5a18fa7a0b87b2d6ef99"
SOURCE_INTERFACE_STATUS = "UNMERGED_SPECIALIST_CANDIDATE_INTERFACE_RESCREEN_BEFORE_PROMOTION"

CELL3_CENTRAL_REAR_KEEP_OUT_XYZ_MM = (68.0, 104.0, 24.0)
CELL3_CENTRAL_REAR_KEEP_OUT_CENTER_MM = (0.0, 0.0, -36.0)
CELL3_OCCIPITAL_INNER_X_ABS_MM = 44.0
CELL3_CARRIER_INNER_X_ABS_MM = 56.0
CELL3_CROWN_CORRIDOR_Y_MIN_MM = 56.0
CELL3_OCCIPITAL_POSTERIOR_Z_MM = -52.5

# Prompt 11 visible-interface baseline. This is deliberately smaller than the current
# conservative package reservation. The first 74 x 108 mm wrap and a later 58 x 86 mm
# candidate were rejected during the visual loop because rear elevation remained too
# dominant. The current 50 x 68 mm face is the smallest robust bounded target that still
# contains the authority battery benchmark projection and the labelled stale PCB donor
# projection independently without claiming simultaneous internal nesting.
REAR_SKIN_FRONT_XY_MM = (50.0, 68.0)
REAR_SKIN_REAR_XY_MM = (44.0, 60.0)
REAR_SKIN_FRONT_CORNER_RADIUS_MM = 18.0
REAR_SKIN_REAR_CORNER_RADIUS_MM = 16.0
REAR_COVER_REMOVAL_TRAVEL_MM = 8.0
STALE_MANUAL_B_PCB_PROJECTION_XY_MM = (48.0, 26.0)

DIGITAL_ONLY = "DIGITAL_VISIBLE_INTERFACE_NOT_PHYSICAL_SERVICE_OR_PACKAGE_VALIDATION"
PACKAGE_REFLOW_REQUIRED = "CELL4_DRY_SIDE_PACKAGE_REFLOW_REQUIRED_BEFORE_REAR_SKIN_RELEASE"


class RearServiceSkinError(ValueError):
    pass


def _box(size: tuple[float, float, float], center: tuple[float, float, float]) -> cq.Workplane:
    return cq.Workplane("XY").box(*size, centered=(True, True, True)).translate(center)


def _intersection_mm3(first: cq.Shape, second: cq.Shape) -> float:
    value = float(first.intersect(second).Volume())
    if not math.isfinite(value) or value < 0.0:
        raise RearServiceSkinError("intersection volume must be finite and non-negative")
    return 0.0 if value < 1e-8 else value


def _rounded_rect_contains_centered_rect(
    outer_xy: tuple[float, float],
    radius_mm: float,
    inner_xy: tuple[float, float],
) -> bool:
    width, height = outer_xy
    inner_w, inner_h = inner_xy
    if min(width, height, inner_w, inner_h, radius_mm) <= 0.0:
        return False
    half_w = width / 2.0
    half_h = height / 2.0
    x = inner_w / 2.0
    y = inner_h / 2.0
    if x > half_w or y > half_h:
        return False
    straight_x = half_w - radius_mm
    straight_y = half_h - radius_mm
    if x <= straight_x or y <= straight_y:
        return True
    return (x - straight_x) ** 2 + (y - straight_y) ** 2 <= radius_mm**2 + 1e-9


def _rounded_rect_sketch(width_mm: float, height_mm: float, radius_mm: float) -> cq.Sketch:
    if radius_mm <= 0.0 or 2.0 * radius_mm >= min(width_mm, height_mm) + 1e-9:
        raise RearServiceSkinError("rear-service corner radius must fit its profile")
    return cq.Sketch().rect(width_mm, height_mm).vertices().fillet(radius_mm)


def _build_cover(front_z_mm: float, depth_mm: float) -> cq.Workplane:
    rear_z_mm = front_z_mm - depth_mm
    front = cq.Workplane("XY", origin=(0.0, 0.0, front_z_mm)).placeSketch(
        _rounded_rect_sketch(
            REAR_SKIN_FRONT_XY_MM[0],
            REAR_SKIN_FRONT_XY_MM[1],
            REAR_SKIN_FRONT_CORNER_RADIUS_MM,
        )
    )
    rear = cq.Workplane("XY", origin=(0.0, 0.0, rear_z_mm)).placeSketch(
        _rounded_rect_sketch(
            REAR_SKIN_REAR_XY_MM[0],
            REAR_SKIN_REAR_XY_MM[1],
            REAR_SKIN_REAR_CORNER_RADIUS_MM,
        )
    )
    cover = front.add(rear).loft(combine=True, ruled=False)
    shape = cover.val()
    if not shape.isValid() or len(shape.Solids()) != 1 or float(shape.Volume()) <= 0.0:
        raise RearServiceSkinError("rear-service skin must resolve as one valid solid")
    return cover


@dataclass(frozen=True, slots=True)
class RearServiceSkin:
    cover: cq.Workplane
    package_keepout_reference: cq.Workplane
    cover_removal_envelope_reference: cq.Workplane
    front_z_mm: float
    rear_z_mm: float
    depth_mm: float
    seam_gap_mm: float
    battery_benchmark_xy_mm: tuple[float, float]
    battery_status: str

    @property
    def display_compound(self) -> cq.Shape:
        return cq.Compound.makeCompound([self.cover.val()])

    def manifest(self) -> dict[str, object]:
        cover_bb = self.cover.val().BoundingBox()
        service_bb = self.cover_removal_envelope_reference.val().BoundingBox()
        battery_projection_fits = _rounded_rect_contains_centered_rect(
            REAR_SKIN_FRONT_XY_MM,
            REAR_SKIN_FRONT_CORNER_RADIUS_MM,
            self.battery_benchmark_xy_mm,
        )
        stale_pcb_projection_fits = _rounded_rect_contains_centered_rect(
            REAR_SKIN_FRONT_XY_MM,
            REAR_SKIN_FRONT_CORNER_RADIUS_MM,
            STALE_MANUAL_B_PCB_PROJECTION_XY_MM,
        )
        return {
            "schema": SCHEMA,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "source_cell3_retention_head_sha": SOURCE_CELL3_RETENTION_HEAD_SHA,
            "source_cell3_occipital_blob_sha": SOURCE_CELL3_OCCIPITAL_BLOB_SHA,
            "source_interface_status": SOURCE_INTERFACE_STATUS,
            "cover": {
                "front_xy_mm": list(REAR_SKIN_FRONT_XY_MM),
                "rear_xy_mm": list(REAR_SKIN_REAR_XY_MM),
                "front_corner_radius_mm": REAR_SKIN_FRONT_CORNER_RADIUS_MM,
                "rear_corner_radius_mm": REAR_SKIN_REAR_CORNER_RADIUS_MM,
                "front_z_mm": self.front_z_mm,
                "rear_z_mm": self.rear_z_mm,
                "depth_mm": self.depth_mm,
                "bounds_mm": [
                    float(cover_bb.xmin),
                    float(cover_bb.xmax),
                    float(cover_bb.ymin),
                    float(cover_bb.ymax),
                    float(cover_bb.zmin),
                    float(cover_bb.zmax),
                ],
                "volume_mm3": float(self.cover.val().Volume()),
                "visual_policy": "COMPACT_VERTICAL_SOFT_RECTANGLE_TAPERED_POSTERIOR_NO_REAR_BRICK_NO_ACCENT",
            },
            "current_cell3_package_interface": {
                "keepout_xyz_mm": list(CELL3_CENTRAL_REAR_KEEP_OUT_XYZ_MM),
                "keepout_center_xyz_mm": list(CELL3_CENTRAL_REAR_KEEP_OUT_CENTER_MM),
                "installed_z_gap_mm": self.seam_gap_mm,
                "fully_hidden_by_current_skin_projection": False,
                "package_reflow_required": True,
                "reflow_requirement": PACKAGE_REFLOW_REQUIRED,
            },
            "retention_clearance": {
                "static_lateral_gap_to_occipital_inner_x_mm": CELL3_OCCIPITAL_INNER_X_ABS_MM - REAR_SKIN_FRONT_XY_MM[0] / 2.0,
                "service_lateral_gap_to_occipital_inner_x_mm": CELL3_OCCIPITAL_INNER_X_ABS_MM - REAR_SKIN_FRONT_XY_MM[0] / 2.0,
                "service_lateral_gap_to_carrier_inner_x_mm": CELL3_CARRIER_INNER_X_ABS_MM - REAR_SKIN_FRONT_XY_MM[0] / 2.0,
                "service_superior_gap_to_crown_corridor_mm": CELL3_CROWN_CORRIDOR_Y_MIN_MM - REAR_SKIN_FRONT_XY_MM[1] / 2.0,
                "cover_posterior_face_relative_to_occipital_extreme_mm": self.rear_z_mm - CELL3_OCCIPITAL_POSTERIOR_Z_MM,
            },
            "service_reference": {
                "cover_only_removal_direction": "-Z_POSTERIOR",
                "travel_mm": REAR_COVER_REMOVAL_TRAVEL_MM,
                "bounds_mm": [
                    float(service_bb.xmin),
                    float(service_bb.xmax),
                    float(service_bb.ymin),
                    float(service_bb.ymax),
                    float(service_bb.zmin),
                    float(service_bb.zmax),
                ],
                "battery_extraction_geometry_status": "UNRESOLVED",
                "dry_bay_attachment_geometry_status": "UNRESOLVED",
                "mask_state": "MASK_REMOVED_UNPOWERED_REFERENCE_ONLY",
            },
            "package_screening": {
                "authority_battery_benchmark_xy_mm": list(self.battery_benchmark_xy_mm),
                "authority_battery_status": self.battery_status,
                "battery_projection_fits_visible_target": battery_projection_fits,
                "stale_manual_b_pcb_projection_xy_mm": list(STALE_MANUAL_B_PCB_PROJECTION_XY_MM),
                "stale_manual_b_pcb_projection_fits_visible_target": stale_pcb_projection_fits,
                "pcb_source_status": "STALE_DONOR_SCREENING_ONLY_NOT_AUTHORITY",
                "simultaneous_internal_nesting_validated": False,
            },
            "cmf_intent": "SAME_SATIN_RIGID_FAMILY_AS_MAIN_SHELL_NO_SECONDARY_ACCENT",
            "evidence_status": DIGITAL_ONLY,
        }


def build_rear_service_skin(authority: Authority | None = None) -> RearServiceSkin:
    authority = authority or load_authority()
    if str(authority.get("coordinate_system", "x_positive")) != "wearer_right":
        raise RearServiceSkinError("rear-service skin requires frozen wearer-right +X semantics")
    if str(authority.get("coordinate_system", "y_positive")) != "superior":
        raise RearServiceSkinError("rear-service skin requires frozen superior +Y semantics")
    if str(authority.get("coordinate_system", "z_positive")) != "anterior":
        raise RearServiceSkinError("rear-service skin requires frozen anterior +Z semantics")

    seam_gap = authority.number("geometry", "visible_seam", "gap_mm")
    depth = authority.number("geometry", "shell_nominal_wall_mm")
    keepout_posterior_z = CELL3_CENTRAL_REAR_KEEP_OUT_CENTER_MM[2] - CELL3_CENTRAL_REAR_KEEP_OUT_XYZ_MM[2] / 2.0
    front_z = keepout_posterior_z - seam_gap
    rear_z = front_z - depth

    cover = _build_cover(front_z, depth)
    keepout = _box(CELL3_CENTRAL_REAR_KEEP_OUT_XYZ_MM, CELL3_CENTRAL_REAR_KEEP_OUT_CENTER_MM)
    removal_depth = depth + REAR_COVER_REMOVAL_TRAVEL_MM
    service = _box(
        (REAR_SKIN_FRONT_XY_MM[0], REAR_SKIN_FRONT_XY_MM[1], removal_depth),
        (0.0, 0.0, front_z - removal_depth / 2.0),
    )

    if _intersection_mm3(cover.val(), keepout.val()) != 0.0:
        raise RearServiceSkinError("rear-service skin intersects current Cell 3 package keepout")
    outer_w, outer_h = authority.pair("geometry", "outer_xy_envelope_mm")
    if cover.val().BoundingBox().xlen > outer_w or cover.val().BoundingBox().ylen > outer_h:
        raise RearServiceSkinError("rear-service skin exceeds authority XY envelope")

    battery_w, battery_h, _ = tuple(float(v) for v in authority.get("battery_reference", "envelope_mm"))
    result = RearServiceSkin(
        cover=cover,
        package_keepout_reference=keepout,
        cover_removal_envelope_reference=service,
        front_z_mm=front_z,
        rear_z_mm=rear_z,
        depth_mm=depth,
        seam_gap_mm=seam_gap,
        battery_benchmark_xy_mm=(battery_w, battery_h),
        battery_status=str(authority.get("battery_reference", "status")),
    )
    if not result.manifest()["package_screening"]["battery_projection_fits_visible_target"]:
        raise RearServiceSkinError("authority battery benchmark no longer fits rear visual target")
    return result


def rear_service_skin_manifest(authority: Authority | None = None) -> dict[str, object]:
    return build_rear_service_skin(authority).manifest()
