from __future__ import annotations

"""Exact-C2 tactile successor for the retention quick-release candidate.

V1 established the low-play guide, anti-rotation key, captive slider, rooted end
bumpers, rigid abuse stops and historical-donor firewall. Its detent intent was a
quintic smootherstep, but the manufactured CAD used sixteen straight segments over
the 0.8 mm cam span. V2 changes only that contact surface: the same smootherstep is
represented exactly as one degree-5 Bezier curve.

The six Bezier controls use linear X spacing and Z ordinates [z0,z0,z0,z1,z1,z1].
That is exactly equivalent to 10t^3 - 15t^4 + 6t^5, so entry and exit have zero
slope and zero curvature without faceted slope changes. All V1 package, guidance,
preload, damping and hard-stop seeds are otherwise preserved.

Force, strain, wet use, fatigue, friction, rebound, acoustics and subjective feel
remain PHYSICAL VALIDATION REQUIRED.
"""

from dataclasses import dataclass
from hashlib import sha256
import json

import cadquery as cq

from . import retention_quick_release_tactile as v1

SCHEMA = "MASCK_ONE_RETENTION_QUICK_RELEASE_TACTILE_V2"
SUPERSEDES_SCHEMA = v1.SCHEMA
CAM_PROFILE_ID = "EXACT_DEGREE5_BEZIER_QUINTIC_SMOOTHERSTEP"


class RetentionQuickReleaseTactileV2Error(ValueError):
    pass


def _cam_control_points(preload: bool) -> tuple[tuple[float, float], ...]:
    z_offset = -v1.DETENT_FREE_PRELOAD_INTRUSION_SEED_MM if preload else 0.0
    x0 = v1.DETENT_TOOTH_X_MIN_MM
    x1 = v1.DETENT_TOOTH_X_MAX_MM
    z0 = v1.DETENT_TOOTH_BOTTOM_LEFT_Z_MM + z_offset
    z1 = v1.DETENT_TOOTH_BOTTOM_RIGHT_Z_MM + z_offset
    span = x1 - x0
    return tuple(
        (
            x0 + span * index / 5.0,
            z0 if index < 3 else z1,
        )
        for index in range(6)
    )


def _exact_smooth_cam_tooth(preload: bool) -> cq.Workplane:
    controls = _cam_control_points(preload)
    wp = cq.Workplane("XZ").moveTo(*controls[0]).bezier(list(controls[1:]))
    tooth = (
        wp.lineTo(v1.DETENT_TOOTH_X_MAX_MM, v1.DETENT_TOOTH_TOP_Z_MM)
        .lineTo(v1.DETENT_TOOTH_X_MIN_MM, v1.DETENT_TOOTH_TOP_Z_MM)
        .close()
        .extrude(v1.DETENT_TOOTH_WIDTH_Y_MM / 2.0, both=True)
    )
    solid = tooth.val()
    if not solid.isValid() or len(solid.Solids()) != 1 or solid.Volume() <= 0.0:
        raise RetentionQuickReleaseTactileV2Error("exact Bezier cam tooth is invalid")
    if sum(edge.geomType() == "BEZIER" for edge in solid.Edges()) < 2:
        raise RetentionQuickReleaseTactileV2Error("exact Bezier cam surface was lost")
    return tooth


def _exact_flexure(preload: bool) -> cq.Workplane:
    tooth = _exact_smooth_cam_tooth(preload)
    beam = v1._box(v1.FLEXURE_BEAM_XYZ_MM, v1.FLEXURE_BEAM_CENTER_MM)
    anchor = v1._box(v1.FLEXURE_ANCHOR_XYZ_MM, v1.FLEXURE_ANCHOR_CENTER_MM)
    flexure = tooth.union(beam).union(anchor)
    solid = flexure.val()
    if not solid.isValid() or len(solid.Solids()) != 1 or solid.Volume() <= 0.0:
        raise RetentionQuickReleaseTactileV2Error("exact-C2 flexure must remain one solid")
    return flexure


@dataclass(frozen=True, slots=True)
class RetentionQuickReleaseTactileV2:
    mechanism: v1.RetentionQuickReleaseTactile

    def validate(self) -> "RetentionQuickReleaseTactileV2":
        self.mechanism.validate()
        controls = _cam_control_points(False)
        if not (
            controls[0][1] == controls[1][1] == controls[2][1]
            and controls[3][1] == controls[4][1] == controls[5][1]
        ):
            raise RetentionQuickReleaseTactileV2Error(
                "Bezier controls lost zero-slope/zero-curvature endpoint multiplicity"
            )
        if controls[0][0] != v1.DETENT_TOOTH_X_MIN_MM or controls[-1][0] != v1.DETENT_TOOTH_X_MAX_MM:
            raise RetentionQuickReleaseTactileV2Error("Bezier cam changed the donor X package")
        if controls[0][1] != v1.DETENT_TOOTH_BOTTOM_LEFT_Z_MM or controls[-1][1] != v1.DETENT_TOOTH_BOTTOM_RIGHT_Z_MM:
            raise RetentionQuickReleaseTactileV2Error("Bezier cam changed the detent endpoints")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        payload = self.mechanism.manifest()
        payload.pop("manifest_sha256", None)
        payload["schema"] = SCHEMA
        payload["supersedes_schema"] = SUPERSEDES_SCHEMA
        payload["detent"] = {
            **payload["detent"],
            "cam_profile": CAM_PROFILE_ID,
            "cam_span_mm": v1.DETENT_TOOTH_X_MAX_MM - v1.DETENT_TOOTH_X_MIN_MM,
            "bezier_degree": 5,
            "control_ordinates_normalized": [0, 0, 0, 1, 1, 1],
            "endpoint_zero_slope_by_control_multiplicity": True,
            "endpoint_zero_curvature_by_control_multiplicity": True,
            "faceted_contact_profile": False,
        }
        payload["quality_patch"] = (
            "V1 16-SEGMENT CAM APPROXIMATION SUPERSEDED; EXACT DEGREE-5 BEZIER "
            "PRESERVES THE QUINTIC SMOOTHERSTEP CONTACT LAW WITHOUT FACET SLOPE STEPS"
        )
        payload["physical_validation_eligible"] = False
        payload["manifest_sha256"] = sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()
        return payload


def build_retention_quick_release_tactile_v2() -> RetentionQuickReleaseTactileV2:
    slider = v1._slider()
    guide, bumpers_free = v1._guide_with_bumper_pockets()
    flexure_free = _exact_flexure(True)
    flexure_installed = _exact_flexure(False)

    installed_slider_flex = v1._intersection(slider, flexure_installed)
    free_slider_flex = v1._intersection(slider, flexure_free)

    released = slider.translate((v1.RELEASE_TRAVEL_MM, 0.0, 0.0))
    bumpers_installed = (v1._stop_bumper(False, True), v1._stop_bumper(False, False))
    in_free = v1._intersection(slider, bumpers_free[0])
    out_free = v1._intersection(released, bumpers_free[1])
    in_inst = v1._intersection(slider, bumpers_installed[0])
    out_inst = v1._intersection(released, bumpers_installed[1])

    if v1._intersection(slider, guide) > v1.TOL_MM3 or v1._intersection(released, guide) > v1.TOL_MM3:
        raise RetentionQuickReleaseTactileV2Error("slider intersects rigid guide at a nominal endpoint")

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
    return RetentionQuickReleaseTactileV2(mechanism).validate()
