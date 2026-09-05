from __future__ import annotations

"""Cell 3 split-guide assembly successor for the right quick release.

Digital geometry only. The connected slider drops into an open lower guide through an
exact vertical sweep; an upper guide half closes with bounded external-hook deflection
and relaxes behind positive shoulders. No force, fatigue, process or safety claim.
"""

from dataclasses import dataclass
from hashlib import sha256
import json, math
from pathlib import Path
import cadquery as cq

from .model import MasckOneModel, build_model
from .right_quick_release_latch import (
    BORE_RADIUS_MM, CAPSULE_CENTER_X_MM, CAVITY_XYZ_MM, GRIP_CENTER_X_MM,
    GRIP_XYZ_MM, LATCH_AXIS_Z_MM, LATCH_CENTER_X_MM, PIN_LENGTH_MM,
    PIN_RADIUS_MM, RELEASE_TRAVEL_MM, SLIDER_JOIN_OVERLAP_MM,
    SPOOL_LEFT_LENGTH_MM, SPOOL_LEFT_RADIUS_MM, SPOOL_NECK_LENGTH_MM,
    SPOOL_NECK_RADIUS_MM, SPOOL_RIGHT_LENGTH_MM, SPOOL_RIGHT_RADIUS_MM,
    SPOOL_START_X_MM, WORLD_FRAME_ID, _bbox, _box, _cylinder_x,
    _intersection_mm3, _source_model_sha,
)
from .right_quick_release_reset import RightQuickReleaseResetMechanics, build_right_quick_release_reset_mechanics
from .right_quick_release_sweep import RightQuickReleaseContinuousSweep, build_right_quick_release_continuous_sweep
from .right_quick_release_travel import STOP_OVERTRAVEL_PROBE_MM

SCHEMA = "MASCK_ONE_CELL3_RIGHT_QUICK_RELEASE_ASSEMBLY_V1"
DIGITAL_ONLY = "DIGITAL_ASSEMBLY_GEOMETRY_ONLY_NOT_PHYSICAL_VALIDATION"
SPLIT_Z = LATCH_AXIS_Z_MM
SLIDER_START_Z = 8.0
CLOSURE_START_Z = 6.0
HOOK_DEFLECTION = 0.40
PROBE_Z = 0.10
PROBE_XY = 0.20
SHOULDER = (4.0, 0.65, 0.80)
SHOULDER_C = (86.0, 3.825, -19.60)
HOOK_X = 2.0
HOOK_TOP = (0.80, 0.50, 4.0, -15.55)
HOOK_BEAM = (4.20, 4.55, -20.30, -15.30)
HOOK_FOOT = (0.50, 0.40, 4.05, -20.25)
POST_R = 0.25
POST_BORE_R = 0.40
POST_X = (84.4, 88.0)
POST_Y = 3.20
POST_Z = -18.40


class RightQuickReleaseAssemblyError(ValueError): pass


def _single(s: cq.Workplane, label: str) -> cq.Workplane:
    sh = s.val()
    if not sh.isValid() or sh.Volume() <= 0 or len(sh.Solids()) != 1:
        raise RightQuickReleaseAssemblyError(f"{label} must be one valid solid")
    return s


def _cyl_z(r: float, length: float, center: tuple[float, float, float]) -> cq.Workplane:
    return cq.Workplane("XY").circle(r).extrude(length / 2, both=True).translate(center)


def _prism_x(points: tuple[tuple[float, float], ...]) -> cq.Workplane:
    wp = cq.Workplane("YZ").moveTo(*points[0])
    for p in points[1:]: wp = wp.lineTo(*p)
    return wp.close().extrude(HOOK_X / 2, both=True).translate((SHOULDER_C[0], 0, 0))


def _half(source: cq.Workplane, upper: bool) -> cq.Workplane:
    span = 40.0
    z = SPLIT_Z + (span / 2 if upper else -span / 2)
    return _single(source.intersect(_box((40, 40, span), (CAPSULE_CENTER_X_MM, 0, z))), "guide half")


def _lower(source: cq.Workplane) -> cq.Workplane:
    s = _half(source, False)
    for side in (-1, 1):
        s = s.union(_box(SHOULDER, (SHOULDER_C[0], side * SHOULDER_C[1], SHOULDER_C[2])))
        for x in POST_X: s = s.union(_cyl_z(POST_R, 1.20, (x, side * POST_Y, POST_Z)))
    return _single(s, "lower guide")


def _upper(source: cq.Workplane, d: float) -> cq.Workplane:
    if not 0 <= d <= HOOK_DEFLECTION or not math.isfinite(d):
        raise RightQuickReleaseAssemblyError("hook deflection outside controlled range")
    s = _half(source, True)
    for side in (-1, 1):
        for x in POST_X: s = s.cut(_cyl_z(POST_BORE_R, 5.0, (x, side * POST_Y, -17.5)))
        s = s.union(_box((HOOK_X, HOOK_TOP[0], HOOK_TOP[1]), (SHOULDER_C[0], side * HOOK_TOP[2], HOOK_TOP[3])))
        yi, yo, z0, z1 = HOOK_BEAM
        if side > 0:
            pts = ((yi+d,z0),(yo+d,z0),(yo,z1),(yi,z1)); fy = HOOK_FOOT[2] + d
        else:
            pts = ((-yi-d,z0),(-yo-d,z0),(-yo,z1),(-yi,z1)); fy = -HOOK_FOOT[2] - d
        s = s.union(_prism_x(pts))
        s = s.union(_box((HOOK_X, HOOK_FOOT[0], HOOK_FOOT[1]), (SHOULDER_C[0], fy, HOOK_FOOT[3])))
    return _single(s, "upper guide")


def _swept_cyl_z(r: float, length: float, center: tuple[float,float,float], travel: float) -> cq.Workplane:
    a = _cylinder_x(r, length, center)
    b = _cylinder_x(r, length, (center[0], center[1], center[2] + travel))
    bridge = _box((length, 2*r, travel), (center[0], center[1], center[2] + travel/2))
    return _single(a.union(b).union(bridge), "vertical cylinder sweep")


def _slider_insertion_sweep() -> cq.Workplane:
    t = SLIDER_START_Z
    pin_xmax = LATCH_CENTER_X_MM + PIN_LENGTH_MM/2
    left = SPOOL_START_X_MM + SPOOL_LEFT_LENGTH_MM/2
    neck = SPOOL_START_X_MM + SPOOL_LEFT_LENGTH_MM + SPOOL_NECK_LENGTH_MM/2
    right = SPOOL_START_X_MM + SPOOL_LEFT_LENGTH_MM + SPOOL_NECK_LENGTH_MM + SPOOL_RIGHT_LENGTH_MM/2
    end = SPOOL_START_X_MM + SPOOL_LEFT_LENGTH_MM + SPOOL_NECK_LENGTH_MM + SPOOL_RIGHT_LENGTH_MM
    b0, b1 = pin_xmax - SLIDER_JOIN_OVERLAP_MM, SPOOL_START_X_MM + SLIDER_JOIN_OVERLAP_MM
    g0, s0 = GRIP_CENTER_X_MM - GRIP_XYZ_MM[0]/2, end - SLIDER_JOIN_OVERLAP_MM
    parts = (
        _swept_cyl_z(PIN_RADIUS_MM, PIN_LENGTH_MM, (LATCH_CENTER_X_MM,0,LATCH_AXIS_Z_MM), t),
        _swept_cyl_z(PIN_RADIUS_MM, b1-b0, ((b0+b1)/2,0,LATCH_AXIS_Z_MM), t),
        _swept_cyl_z(SPOOL_LEFT_RADIUS_MM, SPOOL_LEFT_LENGTH_MM, (left,0,LATCH_AXIS_Z_MM), t),
        _swept_cyl_z(SPOOL_NECK_RADIUS_MM, SPOOL_NECK_LENGTH_MM, (neck,0,LATCH_AXIS_Z_MM), t),
        _swept_cyl_z(SPOOL_RIGHT_RADIUS_MM, SPOOL_RIGHT_LENGTH_MM, (right,0,LATCH_AXIS_Z_MM), t),
        _swept_cyl_z(PIN_RADIUS_MM, g0-s0, ((s0+g0)/2,0,LATCH_AXIS_Z_MM), t),
        _box((GRIP_XYZ_MM[0],GRIP_XYZ_MM[1],GRIP_XYZ_MM[2]+t),(GRIP_CENTER_X_MM,0,LATCH_AXIS_Z_MM+t/2)),
    )
    s = parts[0]
    for p in parts[1:]: s = s.union(p)
    return _single(s, "slider insertion sweep")


@dataclass(frozen=True, slots=True)
class Part:
    part_id: str
    role: str
    solid: cq.Workplane
    def __post_init__(self): _single(self.solid, self.part_id)
    def manifest(self):
        return {"part_id":self.part_id,"role":self.role,"bounds_mm":list(_bbox(self.solid)),"volume_mm3":float(self.solid.val().Volume())}


@dataclass(frozen=True, slots=True)
class RightQuickReleaseAssembly:
    reset: RightQuickReleaseResetMechanics
    continuous: RightQuickReleaseContinuousSweep
    lower: Part
    upper: Part
    upper_deflected: Part
    insertion_sweep: Part
    metrics: tuple[tuple[str,float], ...]
    @property
    def assembled(self): return _single(self.lower.solid.union(self.upper.solid), "assembled guide")
    @property
    def package_sha256(self):
        raw = json.dumps(self.manifest(False), sort_keys=True, separators=(",",":"), allow_nan=False)
        return sha256(raw.encode()).hexdigest()
    def manifest(self, include_sha: bool=True):
        m = dict(self.metrics)
        shoulder_outer = SHOULDER_C[1] + SHOULDER[1]/2
        proof = {
            "source_split_reconstruction_error_mm3":m["source_split_error"],
            "exact_slider_insertion_sweep_vs_lower_mm3":m["insertion_vs_lower"],
            "pin_bore_radial_clearance_mm":BORE_RADIUS_MM-PIN_RADIUS_MM,
            "spool_half_cavity_clearance_mm":min(CAVITY_XYZ_MM[1]/2-max(SPOOL_LEFT_RADIUS_MM,SPOOL_RIGHT_RADIUS_MM),CAVITY_XYZ_MM[2]/2-max(SPOOL_LEFT_RADIUS_MM,SPOOL_RIGHT_RADIUS_MM)),
            "alignment_post_clearance_mm":POST_BORE_R-POST_R,
            "deflected_hook_side_clearance_mm":HOOK_FOOT[2]+HOOK_DEFLECTION-HOOK_FOOT[0]/2-shoulder_outer,
            "nominal_beam_side_clearance_mm":HOOK_BEAM[0]-shoulder_outer,
            "nominal_hook_vertical_gap_mm":SHOULDER_C[2]-SHOULDER[2]/2-(HOOK_FOOT[3]+HOOK_FOOT[1]/2),
            "deflected_closure_vs_lower_mm3":m["deflected_vs_lower"],
            "deflected_closure_vs_slider_mm3":m["deflected_vs_slider"],
            "closure_continuous_bound":"SPLIT_PLANE_PLUS_POSITIVE_CROSS_SECTION_MARGINS",
        }
        payload = {
            "schema":SCHEMA,"coordinate_frame_id":WORLD_FRAME_ID,
            "source_latch_package_sha256":self.reset.latch.package_sha256,
            "source_reset_package_sha256":self.reset.package_sha256,
            "source_continuous_sweep_package_sha256":self.continuous.package_sha256,
            "supersedes_source_guide_for_release_assembly":True,
            "parts":[p.manifest() for p in (self.lower,self.upper,self.upper_deflected,self.insertion_sweep)],
            "assembly_sequence":[
                {"state_id":"GUIDE_OPEN_LOWER_HALF"},
                {"state_id":"SLIDER_INSERTION","motion":"PURE_TRANSLATION_MINUS_Z","offset_mm":[SLIDER_START_Z,0.0],"proof":"EXACT_RIGID_SLIDER_VERTICAL_SWEPT_SOLID"},
                {"state_id":"UPPER_CLOSURE_DESCENT_HOOKS_DEFLECTED","motion":"PURE_TRANSLATION_MINUS_Z","offset_mm":[CLOSURE_START_Z,0.0],"hook_deflection_mm":HOOK_DEFLECTION},
                {"state_id":"HOOK_RELAXATION_TO_POSITIVE_CAPTURE","deflection_mm":[HOOK_DEFLECTION,0.0]},
                {"state_id":"ASSEMBLED_OPERATIONAL","no_factory_teleportation_required":True,"slider_captive":True,"closure_positive_capture":True},
            ],
            "continuous_assembly_proof":proof,
            "positive_closure_retention":{"friction_only":False,"lift_probe_intersection_mm3":m["lift"],"down_probe_intersection_mm3":m["down"],"x_shear_probe_intersection_mm3":m["x_shear"],"y_shear_probe_intersection_mm3":m["y_shear"]},
            "operational_preservation":{"exact_complete_withdrawal_sweep_vs_split_guide_mm3":m["operational"],"inboard_overtravel_probe_intersection_mm3":m["inboard"],"outboard_overtravel_probe_intersection_mm3":m["outboard"],"release_travel_mm":RELEASE_TRAVEL_MM,"four_zone_actuation_preserved":True,"full_head_removal_trajectory_included":False},
            "manufacturing_claims":{"manufacturable_in_principle_digital_sequence":True,"production_process_selected":False,"hook_material_selected":False,"hook_strain_or_fatigue_validated":False,"assembly_force_validated":False},
            "physical_validation_eligible":False,"evidence_status":DIGITAL_ONLY,
        }
        if include_sha: payload["package_sha256"] = self.package_sha256
        return payload


def build_right_quick_release_assembly(*, reset=None, continuous_sweep=None, model:MasckOneModel|None=None) -> RightQuickReleaseAssembly:
    model = model or build_model()
    reset = reset or build_right_quick_release_reset_mechanics(authority=model.authority, model=model)
    continuous_sweep = continuous_sweep or build_right_quick_release_continuous_sweep(reset=reset, model=model)
    if reset.source_model_sha256 != _source_model_sha(model) or continuous_sweep.reset.package_sha256 != reset.package_sha256:
        raise RightQuickReleaseAssemblyError("assembly provenance mismatch")
    source = reset.latch.guide_capsule.solid
    lo0, up0 = _half(source,False), _half(source,True)
    recon = _single(lo0.union(up0), "split reconstruction")
    split_error = max(float(source.val().cut(recon.val()).Volume()), float(recon.val().cut(source.val()).Volume()))
    if split_error > 1e-7: raise RightQuickReleaseAssemblyError("split does not reconstruct source guide")
    lower = Part("RIGHT_LATCH_GUIDE_LOWER_BODY","lower guide with hook shoulders and alignment posts",_lower(source))
    upper = Part("RIGHT_LATCH_GUIDE_UPPER_CLOSURE","upper guide with positive retaining hooks",_upper(source,0.0))
    upper_d = Part("RIGHT_LATCH_GUIDE_UPPER_CLOSURE_DEFLECTED","bounded hook-deflection assembly state",_upper(source,HOOK_DEFLECTION))
    insertion = Part("RIGHT_LATCH_SLIDER_FACTORY_INSERTION_SWEEP","exact connected-slider vertical insertion sweep",_slider_insertion_sweep())
    slider = reset.latch.slider_and_grip.solid
    if _intersection_mm3(slider,lower.solid) or _intersection_mm3(slider,upper.solid): raise RightQuickReleaseAssemblyError("seated slider collision")
    assembled = _single(lower.solid.union(upper.solid), "assembled split guide")
    metrics = {
        "source_split_error":0.0,
        "insertion_vs_lower":_intersection_mm3(insertion.solid,lower.solid),
        "deflected_vs_lower":_intersection_mm3(upper_d.solid,lower.solid),
        "deflected_vs_slider":_intersection_mm3(upper_d.solid,slider),
        "operational":_intersection_mm3(continuous_sweep.exact_slider_sweep,assembled),
        "inboard":_intersection_mm3(slider.translate((-STOP_OVERTRAVEL_PROBE_MM,0,0)),assembled),
        "outboard":_intersection_mm3(slider.translate((RELEASE_TRAVEL_MM+STOP_OVERTRAVEL_PROBE_MM,0,0)),assembled),
        "lift":_intersection_mm3(upper.solid.translate((0,0,PROBE_Z)),lower.solid),
        "down":_intersection_mm3(upper.solid.translate((0,0,-PROBE_Z)),lower.solid),
        "x_shear":_intersection_mm3(upper.solid.translate((PROBE_XY,0,0)),lower.solid),
        "y_shear":_intersection_mm3(upper.solid.translate((0,PROBE_XY,0)),lower.solid),
    }
    for k in ("insertion_vs_lower","deflected_vs_lower","deflected_vs_slider","operational"):
        if metrics[k] != 0.0: raise RightQuickReleaseAssemblyError(f"assembly clearance failed: {k}")
    for k in ("inboard","outboard","lift","down","x_shear","y_shear"):
        if metrics[k] <= 0.0: raise RightQuickReleaseAssemblyError(f"positive blocking failed: {k}")
    if _intersection_mm3(reset.nominal_flexure.solid,upper.solid) <= 0: raise RightQuickReleaseAssemblyError("reset flexure root lost")
    result = RightQuickReleaseAssembly(reset,continuous_sweep,lower,upper,upper_d,insertion,tuple(sorted(metrics.items())))
    for k,v in result.manifest()["continuous_assembly_proof"].items():
        if k.endswith("clearance_mm") or k.endswith("gap_mm"):
            if float(v) <= 0: raise RightQuickReleaseAssemblyError(f"nonpositive analytic margin: {k}")
    return result


def export_right_quick_release_assembly(output_dir: str|Path, assembly:RightQuickReleaseAssembly) -> tuple[Path,...]:
    root=Path(output_dir); root.mkdir(parents=True,exist_ok=True); paths=[]
    solids=(
        ("right_latch_guide_lower_body.step",assembly.lower.solid),
        ("right_latch_guide_upper_closure.step",assembly.upper.solid),
        ("right_latch_guide_upper_closure_deflected.step",assembly.upper_deflected.solid),
        ("right_latch_slider_factory_insertion_sweep.step",assembly.insertion_sweep.solid),
        ("right_latch_guide_assembled_reference.step",assembly.assembled),
    )
    for name,solid in solids:
        path=root/name; _single(solid,name); cq.exporters.export(solid,str(path))
        if not path.is_file() or path.stat().st_size<=0: raise RuntimeError(f"failed to export {name}")
        paths.append(path)
    manifest=root/"right_quick_release_assembly_manifest.json"
    manifest.write_text(json.dumps(assembly.manifest(),sort_keys=True,indent=2,allow_nan=False)+"\n",encoding="utf-8"); paths.append(manifest)
    return tuple(paths)
