from __future__ import annotations

"""Retention quick-release tactile V3: exact cam plus rib-cleared damping.

V2 established the exact degree-5 Bezier detent surface but retained the V1 annular
bumper reference unchanged. Exact-head CI exposed a real geometric conflict at the
released endpoint: the anti-rotation rib passed through the outboard installed bumper
ring. V3 preserves the same 0.03 mm guide seed, one-DOF anti-rotation key, Bezier cam,
free-state bumper protrusion and independent rigid hard stops, but gives both bumper
states a small inner relief window aligned to the rib.

The relief opens only the inner annulus around the keyed rib. It does not split the
bumper, remove its keyed root, reduce full release travel, or move either hard-stop
plane. Force, strain, friction, wet use, rebound, acoustics, wear and subjective feel
remain PHYSICAL VALIDATION REQUIRED.
"""

from dataclasses import dataclass
from hashlib import sha256
import json

import cadquery as cq

from . import retention_quick_release_tactile as v1
from . import retention_quick_release_tactile_v2 as v2

SCHEMA = "MASCK_ONE_RETENTION_QUICK_RELEASE_TACTILE_V3"
SUPERSEDES_SCHEMA = v2.SCHEMA
BUMPER_RIB_RELIEF_WIDTH_Y_MM = 0.70
BUMPER_RIB_RELIEF_EXTRA_Z_MM = 0.12
MIN_BUMPER_RELIEF_SIDE_CLEARANCE_MM = 0.05


class RetentionQuickReleaseTactileV3Error(ValueError):
    pass


def _rib_relief_cutter(bumper: cq.Workplane) -> cq.Workplane:
    bb = bumper.val().BoundingBox()
    rib_center_from_axis = (
        v1.PIN_RADIUS_MM
        + v1.ANTI_ROTATION_RIB_DEPTH_Z_MM / 2.0
        - v1.ANTI_ROTATION_RIB_ROOT_OVERLAP_MM / 2.0
    )
    relief_depth = (
        v1.ANTI_ROTATION_RIB_DEPTH_Z_MM
        + v1.ANTI_ROTATION_RIB_ROOT_OVERLAP_MM
        + BUMPER_RIB_RELIEF_EXTRA_Z_MM
    )
    return v1._box(
        (
            bb.xmax - bb.xmin + 0.02,
            BUMPER_RIB_RELIEF_WIDTH_Y_MM,
            relief_depth,
        ),
        (
            (bb.xmin + bb.xmax) / 2.0,
            0.0,
            v1.LATCH_AXIS_Z_MM - rib_center_from_axis,
        ),
    )


def _rib_cleared_bumper(free: bool, inboard: bool) -> cq.Workplane:
    bumper = v1._stop_bumper(free, inboard)
    relieved = bumper.cut(_rib_relief_cutter(bumper))
    solid = relieved.val()
    if not solid.isValid() or len(solid.Solids()) != 1 or solid.Volume() <= 0.0:
        raise RetentionQuickReleaseTactileV3Error(
            "rib relief must preserve one connected positive bumper"
        )
    return relieved


def _guide_with_exact_bumper_pockets() -> tuple[cq.Workplane, tuple[cq.Workplane, cq.Workplane]]:
    guide = v1._guide_base()
    bumpers = (
        _rib_cleared_bumper(True, True),
        _rib_cleared_bumper(True, False),
    )
    before = float(guide.val().Volume())
    for bumper in bumpers:
        guide = guide.cut(bumper)
    removed = before - float(guide.val().Volume())
    if not guide.val().isValid() or len(guide.val().Solids()) != 1 or removed <= 0.0:
        raise RetentionQuickReleaseTactileV3Error(
            "relieved bumper roots must cut positive valid guide pockets"
        )
    return guide, bumpers


@dataclass(frozen=True, slots=True)
class RetentionQuickReleaseTactileV3:
    mechanism: v1.RetentionQuickReleaseTactile
    bumper_relief_side_clearance_mm: float

    def validate(self) -> "RetentionQuickReleaseTactileV3":
        self.mechanism.validate()
        if self.bumper_relief_side_clearance_mm < MIN_BUMPER_RELIEF_SIDE_CLEARANCE_MM:
            raise RetentionQuickReleaseTactileV3Error(
                "bumper rib relief lost bounded side clearance"
            )
        for bumper in (
            *self.mechanism.bumper_free_regions,
            *self.mechanism.bumper_installed_references,
        ):
            solid = bumper.val()
            if not solid.isValid() or len(solid.Solids()) != 1 or solid.Volume() <= 0.0:
                raise RetentionQuickReleaseTactileV3Error(
                    "each relieved bumper state must remain one positive solid"
                )
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        payload = self.mechanism.manifest()
        payload.pop("manifest_sha256", None)
        payload["schema"] = SCHEMA
        payload["supersedes_schema"] = SUPERSEDES_SCHEMA
        payload["detent"] = {
            **payload["detent"],
            "cam_profile": v2.CAM_PROFILE_ID,
            "bezier_degree": 5,
            "faceted_contact_profile": False,
        }
        payload["end_state_damping"] = {
            **payload["end_state_damping"],
            "anti_rotation_rib_relief_width_y_mm": BUMPER_RIB_RELIEF_WIDTH_Y_MM,
            "anti_rotation_rib_relief_side_clearance_mm": self.bumper_relief_side_clearance_mm,
            "free_bumpers_remain_one_connected_solid": True,
            "installed_bumpers_remain_one_connected_solid": True,
            "installed_reference_rib_overlap_mm3": [
                self.mechanism.inboard_bumper_installed_interference_mm3,
                self.mechanism.outboard_bumper_installed_interference_mm3,
            ],
        }
        payload["quality_patch"] = (
            "V2 EXACT BEZIER CAM RETAINED; INNER BUMPER RELIEF PREVENTS THE KEYED "
            "ANTI-ROTATION RIB FROM SHEARING THROUGH THE INSTALLED END-STATE DAMPER"
        )
        payload["physical_validation_eligible"] = False
        payload["manifest_sha256"] = sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()
        return payload


def build_retention_quick_release_tactile_v3() -> RetentionQuickReleaseTactileV3:
    slider = v1._slider()
    guide, bumpers_free = _guide_with_exact_bumper_pockets()
    flexure_free = v2._exact_flexure(True)
    flexure_installed = v2._exact_flexure(False)

    installed_slider_flex = v1._intersection(slider, flexure_installed)
    free_slider_flex = v1._intersection(slider, flexure_free)

    released = slider.translate((v1.RELEASE_TRAVEL_MM, 0.0, 0.0))
    bumpers_installed = (
        _rib_cleared_bumper(False, True),
        _rib_cleared_bumper(False, False),
    )
    in_free = v1._intersection(slider, bumpers_free[0])
    out_free = v1._intersection(released, bumpers_free[1])
    in_inst = v1._intersection(slider, bumpers_installed[0])
    out_inst = v1._intersection(released, bumpers_installed[1])

    if v1._intersection(slider, guide) > v1.TOL_MM3 or v1._intersection(released, guide) > v1.TOL_MM3:
        raise RetentionQuickReleaseTactileV3Error(
            "slider intersects rigid guide at a nominal endpoint"
        )

    in_hard = v1._intersection(slider.translate((-0.05, 0.0, 0.0)), guide)
    out_hard = v1._intersection(released.translate((0.05, 0.0, 0.0)), guide)

    mechanism = v1.RetentionQuickReleaseTactile(
        slider,
        guide,
        flexure_free,
        flexure_installed,
        bumpers_free,
        bumpers_installed,
        v1.SPOOL_RAIL_RADIAL_CLEARANCE_MM,
        v1.ANTI_ROTATION_SIDE_CLEARANCE_MM,
        round(free_slider_flex, 9),
        round(installed_slider_flex, 9),
        round(in_free, 9),
        round(out_free, 9),
        round(in_inst, 9),
        round(out_inst, 9),
        round(in_hard, 9),
        round(out_hard, 9),
        False,
    )
    side_clearance = (BUMPER_RIB_RELIEF_WIDTH_Y_MM - v1.ANTI_ROTATION_RIB_WIDTH_Y_MM) / 2.0
    return RetentionQuickReleaseTactileV3(mechanism, side_clearance).validate()
