from __future__ import annotations

"""Reversible digital reset kinematics for the Cell 3 right quick-release latch.

The reset successor replaces the earlier whole-flexure translation screen with an
anchored leaf whose moving span is outside the guide. The controlled path is reversible:
lift detent, translate to a detent-clear offset, relax, travel to released hard stop;
then reverse those states and re-seat the tooth. This is geometry/kinematics only, not
a material, force, fatigue, wet-use or durability model.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math

import cadquery as cq

from .authority import Authority, load_authority
from .model import MasckOneModel, build_model
from .right_quick_release_latch import (
    DETENT_RIGID_PULL_PROBE_MM, DETENT_TOOTH_WIDTH_Y_MM,
    DETENT_TOOTH_X_MAX_MM, DETENT_TOOTH_X_MIN_MM, GRIP_CENTER_X_MM,
    GRIP_XYZ_MM, LATCH_AXIS_Z_MM, LATCH_CENTER_X_MM, PIN_LENGTH_MM,
    PIN_RADIUS_MM, RELEASE_TRAVEL_MM, SLIDER_JOIN_OVERLAP_MM, SOURCE_MAIN_SHA,
    SPOOL_LEFT_LENGTH_MM, SPOOL_LEFT_RADIUS_MM, SPOOL_NECK_LENGTH_MM,
    SPOOL_NECK_RADIUS_MM, SPOOL_RIGHT_LENGTH_MM, SPOOL_RIGHT_RADIUS_MM,
    SPOOL_START_X_MM, TONGUE_XYZ_MM, WORLD_FRAME_ID, RightQuickReleaseLatch,
    _box, _cylinder_x, _intersection_mm3, _source_model_sha, _wedge_prism_y,
    build_right_quick_release_latch,
)

SCHEMA = "MASCK_ONE_CELL3_RIGHT_QUICK_RELEASE_RESET_V1"
DIGITAL_ONLY = "DIGITAL_RESET_KINEMATICS_ONLY_NOT_PHYSICAL_VALIDATION"
RESET_BEAM_XYZ_MM = (8.2, 2.4, 0.8)
RESET_BEAM_CENTER_MM = (84.6, 0.0, -14.8)
RESET_ANCHOR_XYZ_MM = (2.0, 4.2, 1.6)
RESET_ANCHOR_CENTER_MM = (88.5, 0.0, -15.0)
RESET_TOOTH_BOTTOM_LEFT_Z_MM = -17.50
RESET_TOOTH_BOTTOM_RIGHT_Z_MM = -16.80
RESET_TOOTH_TOP_Z_MM = -15.05
RESET_FREE_END_LIFT_MM = 1.40
RESET_FLEXURE_FREE_END_LIFT_MM = RESET_FREE_END_LIFT_MM
RESET_DETENT_CLEAR_OFFSET_MM = 1.60


class RightQuickReleaseResetError(ValueError):
    pass


def _single(solid: cq.Workplane, label: str) -> cq.Workplane:
    shape = solid.val()
    if not shape.isValid() or float(shape.Volume()) <= 0.0 or len(shape.Solids()) != 1:
        raise RightQuickReleaseResetError(f"{label} must be one valid positive-volume solid")
    return solid


def _bounds(solid: cq.Workplane) -> list[float]:
    bb = solid.val().BoundingBox()
    return [float(v) for v in (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)]


def _beam_limits() -> tuple[float, float, float, float]:
    x0 = RESET_BEAM_CENTER_MM[0] - RESET_BEAM_XYZ_MM[0] / 2.0
    x1 = RESET_BEAM_CENTER_MM[0] + RESET_BEAM_XYZ_MM[0] / 2.0
    z0 = RESET_BEAM_CENTER_MM[2] - RESET_BEAM_XYZ_MM[2] / 2.0
    z1 = RESET_BEAM_CENTER_MM[2] + RESET_BEAM_XYZ_MM[2] / 2.0
    return x0, x1, z0, z1


def _lift_at(x: float, lift: float) -> float:
    x0, x1, _, _ = _beam_limits()
    return lift * (x1 - x) / (x1 - x0)


def _flexure(lift: float) -> tuple[cq.Workplane, cq.Workplane, cq.Workplane]:
    if not math.isfinite(lift) or not 0.0 <= lift <= RESET_FREE_END_LIFT_MM:
        raise RightQuickReleaseResetError("reset flexure lift outside controlled interval")
    x0, x1, z0, z1 = _beam_limits()
    beam = _wedge_prism_y(((x0, z0 + lift), (x1, z0), (x1, z1), (x0, z1 + lift)), RESET_BEAM_XYZ_MM[1])
    tooth = _wedge_prism_y((
        (DETENT_TOOTH_X_MIN_MM, RESET_TOOTH_BOTTOM_LEFT_Z_MM + _lift_at(DETENT_TOOTH_X_MIN_MM, lift)),
        (DETENT_TOOTH_X_MAX_MM, RESET_TOOTH_BOTTOM_RIGHT_Z_MM + _lift_at(DETENT_TOOTH_X_MAX_MM, lift)),
        (DETENT_TOOTH_X_MAX_MM, RESET_TOOTH_TOP_Z_MM + _lift_at(DETENT_TOOTH_X_MAX_MM, lift)),
        (DETENT_TOOTH_X_MIN_MM, RESET_TOOTH_TOP_Z_MM + _lift_at(DETENT_TOOTH_X_MIN_MM, lift)),
    ), DETENT_TOOTH_WIDTH_Y_MM)
    anchor = _box(RESET_ANCHOR_XYZ_MM, RESET_ANCHOR_CENTER_MM)
    moving = _single(beam.union(tooth), "moving reset flexure")
    return _single(moving.union(anchor), "reset flexure"), moving, _single(anchor, "reset anchor")


def _deformation_envelope() -> cq.Workplane:
    x0, x1, z0, z1 = _beam_limits()
    beam = _wedge_prism_y(((x0, z0), (x1, z0), (x1, z1), (x0, z1 + RESET_FREE_END_LIFT_MM)), RESET_BEAM_XYZ_MM[1])
    zs = (
        RESET_TOOTH_BOTTOM_LEFT_Z_MM, RESET_TOOTH_BOTTOM_RIGHT_Z_MM, RESET_TOOTH_TOP_Z_MM,
        RESET_TOOTH_BOTTOM_LEFT_Z_MM + _lift_at(DETENT_TOOTH_X_MIN_MM, RESET_FREE_END_LIFT_MM),
        RESET_TOOTH_BOTTOM_RIGHT_Z_MM + _lift_at(DETENT_TOOTH_X_MAX_MM, RESET_FREE_END_LIFT_MM),
        RESET_TOOTH_TOP_Z_MM + _lift_at(DETENT_TOOTH_X_MIN_MM, RESET_FREE_END_LIFT_MM),
        RESET_TOOTH_TOP_Z_MM + _lift_at(DETENT_TOOTH_X_MAX_MM, RESET_FREE_END_LIFT_MM),
    )
    tooth = _box((DETENT_TOOTH_X_MAX_MM - DETENT_TOOTH_X_MIN_MM, DETENT_TOOTH_WIDTH_Y_MM, max(zs) - min(zs)),
                 ((DETENT_TOOTH_X_MIN_MM + DETENT_TOOTH_X_MAX_MM) / 2.0, 0.0, (max(zs) + min(zs)) / 2.0))
    return _single(beam.union(tooth), "reset flexure deformation envelope")


def _translation_sweep(a: float, b: float) -> cq.Workplane:
    if not (0.0 <= a <= RELEASE_TRAVEL_MM and 0.0 <= b <= RELEASE_TRAVEL_MM):
        raise RightQuickReleaseResetError("reset sweep endpoint outside hard stops")
    lo, hi = sorted((a, b)); span = hi - lo; mid = (lo + hi) / 2.0
    pin_xmax = LATCH_CENTER_X_MM + PIN_LENGTH_MM / 2.0
    left = SPOOL_START_X_MM + SPOOL_LEFT_LENGTH_MM / 2.0
    neck = SPOOL_START_X_MM + SPOOL_LEFT_LENGTH_MM + SPOOL_NECK_LENGTH_MM / 2.0
    right = SPOOL_START_X_MM + SPOOL_LEFT_LENGTH_MM + SPOOL_NECK_LENGTH_MM + SPOOL_RIGHT_LENGTH_MM / 2.0
    spool_end = SPOOL_START_X_MM + SPOOL_LEFT_LENGTH_MM + SPOOL_NECK_LENGTH_MM + SPOOL_RIGHT_LENGTH_MM
    bridge0 = pin_xmax - SLIDER_JOIN_OVERLAP_MM; bridge1 = SPOOL_START_X_MM + SLIDER_JOIN_OVERLAP_MM
    grip0 = GRIP_CENTER_X_MM - GRIP_XYZ_MM[0] / 2.0; stem0 = spool_end - SLIDER_JOIN_OVERLAP_MM
    parts = (
        _cylinder_x(PIN_RADIUS_MM, PIN_LENGTH_MM + span, (LATCH_CENTER_X_MM + mid, 0.0, LATCH_AXIS_Z_MM)),
        _cylinder_x(PIN_RADIUS_MM, bridge1 - bridge0 + span, ((bridge0 + bridge1) / 2.0 + mid, 0.0, LATCH_AXIS_Z_MM)),
        _cylinder_x(SPOOL_LEFT_RADIUS_MM, SPOOL_LEFT_LENGTH_MM + span, (left + mid, 0.0, LATCH_AXIS_Z_MM)),
        _cylinder_x(SPOOL_NECK_RADIUS_MM, SPOOL_NECK_LENGTH_MM + span, (neck + mid, 0.0, LATCH_AXIS_Z_MM)),
        _cylinder_x(SPOOL_RIGHT_RADIUS_MM, SPOOL_RIGHT_LENGTH_MM + span, (right + mid, 0.0, LATCH_AXIS_Z_MM)),
        _cylinder_x(PIN_RADIUS_MM, grip0 - stem0 + span, ((stem0 + grip0) / 2.0 + mid, 0.0, LATCH_AXIS_Z_MM)),
        _box((GRIP_XYZ_MM[0] + span, GRIP_XYZ_MM[1], GRIP_XYZ_MM[2]), (GRIP_CENTER_X_MM + mid, 0.0, LATCH_AXIS_Z_MM)),
    )
    result = parts[0]
    for part in parts[1:]: result = result.union(part)
    return _single(result, "exact reset slider translation sweep")


@dataclass(frozen=True, slots=True)
class ResetPart:
    part_id: str
    role: str
    solid: cq.Workplane

    def __post_init__(self) -> None:
        _single(self.solid, self.part_id)

    def manifest(self) -> dict[str, object]:
        return {"part_id": self.part_id, "role": self.role, "solid_count": 1,
                "volume_mm3": float(self.solid.val().Volume()), "bounds_mm": _bounds(self.solid),
                "evidence_status": DIGITAL_ONLY}


@dataclass(frozen=True, slots=True)
class RightQuickReleaseResetMechanics:
    latch: RightQuickReleaseLatch
    nominal_flexure: ResetPart
    lifted_flexure: ResetPart
    deformation_envelope: ResetPart
    low_offset_translation_sweep: ResetPart
    high_offset_translation_sweep: ResetPart
    source_model_sha256: str
    canonical_main_model_sha256: str

    @property
    def package_sha256(self) -> str:
        raw = json.dumps(self.manifest(False), sort_keys=True, separators=(",", ":"), allow_nan=False)
        return sha256(raw.encode()).hexdigest()

    @property
    def combined_keepout_bounds_mm(self) -> list[float]:
        boxes = [p.solid.val().BoundingBox() for p in (self.nominal_flexure, self.lifted_flexure,
                 self.deformation_envelope, self.low_offset_translation_sweep, self.high_offset_translation_sweep)]
        return [min(float(b.xmin) for b in boxes), max(float(b.xmax) for b in boxes),
                min(float(b.ymin) for b in boxes), max(float(b.ymax) for b in boxes),
                min(float(b.zmin) for b in boxes), max(float(b.zmax) for b in boxes)]

    def manifest(self, include_sha: bool = True) -> dict[str, object]:
        neck0 = SPOOL_START_X_MM + SPOOL_LEFT_LENGTH_MM; neck1 = neck0 + SPOOL_NECK_LENGTH_MM
        pin0 = LATCH_CENTER_X_MM - PIN_LENGTH_MM / 2.0; pin1 = LATCH_CENTER_X_MM + PIN_LENGTH_MM / 2.0
        tongue0 = LATCH_CENTER_X_MM - TONGUE_XYZ_MM[0] / 2.0; tongue1 = LATCH_CENTER_X_MM + TONGUE_XYZ_MM[0] / 2.0
        states = [
            {"state_id":"LATCHED","slider_offset_mm":0.0,"flexure_free_end_lift_mm":0.0,
             "detent_reseated_in_neck":DETENT_TOOTH_X_MIN_MM >= neck0 and DETENT_TOOTH_X_MAX_MM <= neck1,
             "pin_positive_capture":pin0 < tongue0 and pin1 > tongue1,"reset_required":False},
            {"state_id":"RELEASING_DETENT_LIFTED","slider_offset_mm":0.0,"flexure_free_end_lift_mm":RESET_FREE_END_LIFT_MM},
            {"state_id":"RELEASE_TRAVEL_LOW_OFFSET","slider_offset_mm":[0.0,RESET_DETENT_CLEAR_OFFSET_MM],"flexure_free_end_lift_mm":RESET_FREE_END_LIFT_MM},
            {"state_id":"RELEASE_TRAVEL_HIGH_OFFSET","slider_offset_mm":[RESET_DETENT_CLEAR_OFFSET_MM,RELEASE_TRAVEL_MM],"flexure_free_end_lift_mm":0.0},
            {"state_id":"RELEASED_RESET_REQUIRED","slider_offset_mm":RELEASE_TRAVEL_MM,"slider_captive":True,"tongue_capture":False,"reset_required":True},
            {"state_id":"RESET_TRAVEL_HIGH_OFFSET","slider_offset_mm":[RELEASE_TRAVEL_MM,RESET_DETENT_CLEAR_OFFSET_MM],"reset_direction_xyz":[-1.0,0.0,0.0]},
            {"state_id":"RESET_DETENT_LIFTED","slider_offset_mm":RESET_DETENT_CLEAR_OFFSET_MM,"flexure_free_end_lift_mm":RESET_FREE_END_LIFT_MM},
            {"state_id":"RESET_TRAVEL_LOW_OFFSET","slider_offset_mm":[RESET_DETENT_CLEAR_OFFSET_MM,0.0],"reset_direction_xyz":[-1.0,0.0,0.0]},
            {"state_id":"RESET_RESEATED_LATCHED","slider_offset_mm":0.0,"detent_reseated_in_neck":True,"positive_capture_restored":True,"reset_required":False},
        ]
        payload = {"schema":SCHEMA,"coordinate_frame_id":WORLD_FRAME_ID,"source_main_sha":SOURCE_MAIN_SHA,
            "source_latch_package_sha256":self.latch.package_sha256,"source_model_sha256":self.source_model_sha256,
            "canonical_main_model_sha256":self.canonical_main_model_sha256,
            "source_model_matches_current_main":self.source_model_sha256 == self.canonical_main_model_sha256,
            "supersedes_source_part_id_for_reset_states":"RIGHT_LATCH_FLEXURE_CAM_DETENT",
            "parts":[p.manifest() for p in (self.nominal_flexure,self.lifted_flexure,self.deformation_envelope,
                     self.low_offset_translation_sweep,self.high_offset_translation_sweep)],"state_machine":states,
            "kinematic_proof":{"flexure_model":"ANCHORED_LINEAR_DEFLECTION_SURROGATE_NOT_MATERIAL_OR_FEA_MODEL",
                "moving_leaf_clear_of_guide_in_nominal_and_lifted_states":True,"fixed_root_positive_attachment_to_guide":True,
                "rigid_plus_x_probe_blocked_before_detent_lift":True,"continuous_flexure_deformation_envelope_clear":True,
                "low_offset_translation_sweep_clear_with_lifted_flexure":True,"high_offset_translation_sweep_clear_with_nominal_flexure":True,
                "release_and_reset_use_same_reversible_geometric_path":True,"passive_cam_force_mapping_validated":False},
            "detent_geometry":{"tooth_bottom_left_z_mm":RESET_TOOTH_BOTTOM_LEFT_Z_MM,
                "tooth_bottom_right_z_mm":RESET_TOOTH_BOTTOM_RIGHT_Z_MM,"tooth_top_z_mm":RESET_TOOTH_TOP_Z_MM,
                "detent_clear_translation_offset_mm":RESET_DETENT_CLEAR_OFFSET_MM},
            "combined_keepout_bounds_mm":self.combined_keepout_bounds_mm,"physical_gates":self.latch.manifest()["physical_gates"],
            "physical_validation_eligible":False,"evidence_status":DIGITAL_ONLY}
        if include_sha: payload["package_sha256"] = self.package_sha256
        return payload


def build_right_quick_release_reset_mechanics(latch: RightQuickReleaseLatch | None = None,
        authority: Authority | None = None, model: MasckOneModel | None = None) -> RightQuickReleaseResetMechanics:
    authority = authority or (model.authority if model is not None else load_authority())
    model = model or build_model(authority)
    canonical = build_model(authority)
    source_sha = _source_model_sha(model); canonical_sha = _source_model_sha(canonical)
    if source_sha != canonical_sha:
        raise RightQuickReleaseResetError("consumed shell/actuator model does not match current-main canonical geometry")
    latch = latch or build_right_quick_release_latch(authority, model)
    if latch.source_main_sha != SOURCE_MAIN_SHA or latch.source_model_sha256 != source_sha:
        raise RightQuickReleaseResetError("latch provenance does not match verified current-main model")

    nominal, moving, anchor = _flexure(0.0); lifted, lifted_moving, _ = _flexure(RESET_FREE_END_LIFT_MM)
    deformation = _deformation_envelope(); low = _translation_sweep(0.0, RESET_DETENT_CLEAR_OFFSET_MM)
    high = _translation_sweep(RESET_DETENT_CLEAR_OFFSET_MM, RELEASE_TRAVEL_MM)
    if _intersection_mm3(moving, latch.guide_capsule.solid) != 0.0 or _intersection_mm3(lifted_moving, latch.guide_capsule.solid) != 0.0:
        raise RightQuickReleaseResetError("moving reset leaf penetrates guide")
    if _intersection_mm3(anchor, latch.guide_capsule.solid) <= 0.0:
        raise RightQuickReleaseResetError("reset flexure root lacks positive guide attachment")
    if _intersection_mm3(nominal, latch.slider_and_grip.solid) != 0.0:
        raise RightQuickReleaseResetError("nominal reset flexure penetrates latched slider")
    if _intersection_mm3(latch.slider_and_grip.solid.translate((DETENT_RIGID_PULL_PROBE_MM,0.0,0.0)), nominal) <= 0.0:
        raise RightQuickReleaseResetError("rigid pull is not blocked before detent deflection")
    slider_clear = latch.slider_and_grip.solid.translate((RESET_DETENT_CLEAR_OFFSET_MM,0.0,0.0))
    for solid, obstacle, label in ((deformation,latch.guide_capsule.solid,"deformation vs guide"),
            (deformation,latch.slider_and_grip.solid,"deformation vs latched slider"),(deformation,slider_clear,"deformation vs clear-offset slider")):
        if _intersection_mm3(solid, obstacle) != 0.0: raise RightQuickReleaseResetError(f"{label} collision")
    for sweep, flexure, label in ((low,lifted,"low-offset"),(high,nominal,"high-offset")):
        for obstacle, name in ((latch.guide_capsule.solid,"guide"),(latch.socket.solid,"socket"),(latch.tongue.solid,"tongue"),(flexure,"flexure")):
            if _intersection_mm3(sweep, obstacle) != 0.0: raise RightQuickReleaseResetError(f"{label} reset sweep penetrates {name}")
    neck0 = SPOOL_START_X_MM + SPOOL_LEFT_LENGTH_MM; neck1 = neck0 + SPOOL_NECK_LENGTH_MM
    if DETENT_TOOTH_X_MIN_MM < neck0 or DETENT_TOOTH_X_MAX_MM > neck1:
        raise RightQuickReleaseResetError("final reset tooth does not re-seat in spool neck")
    return RightQuickReleaseResetMechanics(latch,
        ResetPart("RIGHT_LATCH_FLEXURE_CAM_DETENT_RESET_NOMINAL","anchored reset-capable detent leaf; material response unvalidated",nominal),
        ResetPart("RIGHT_LATCH_FLEXURE_CAM_DETENT_RESET_LIFTED","maximum digital detent-clear deflection state",lifted),
        ResetPart("RIGHT_LATCH_FLEXURE_RESET_DEFORMATION_ENVELOPE","continuous anchored deflection envelope",deformation),
        ResetPart("RIGHT_LATCH_RESET_LOW_OFFSET_TRANSLATION_SWEEP","exact slider sweep over detent-contact interval",low),
        ResetPart("RIGHT_LATCH_RESET_HIGH_OFFSET_TRANSLATION_SWEEP","exact slider sweep over detent-clear interval",high),
        source_sha, canonical_sha)
