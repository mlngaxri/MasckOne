"""Physical retention and emergency-release engineering model.

Deterministic engineering preflight only. Outputs do not establish human comfort,
universal fit, production release force/time, fatigue life or acoustic performance.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import sqrt, isfinite

G = 9.80665


def _exact_finite_scalar(value: object, label: str) -> float:
    if type(value) not in (int, float):
        raise ValueError(f"{label} must be an exact numeric scalar")
    value = float(value)
    if not isfinite(value):
        raise ValueError(f"{label} must be finite")
    return value


@dataclass(frozen=True)
class RetentionInputs:
    loaded_mass_g: float
    cg_anterior_mm: float
    support_vertical_offset_mm: float
    occipital_share: float
    crown_share: float
    facial_preload_n: float
    friction_coefficient: float
    release_force_n: float
    release_travel_mm: float
    accidental_pull_n: float
    grip_clearance_mm: float
    hair_keepout_mm: float

    def validate(self) -> None:
        for label, value in self.__dict__.items(): _exact_finite_scalar(value, label)
        if not 0.0 <= self.occipital_share <= 1.0 or not 0.0 <= self.crown_share <= 1.0: raise ValueError("support share outside [0,1]")
        if self.occipital_share + self.crown_share > 1.0 + 1e-9: raise ValueError("occipital and crown load shares exceed unity")
        if self.loaded_mass_g <= 0 or self.friction_coefficient < 0: raise ValueError("mass must be positive and friction non-negative")
        if self.cg_anterior_mm < 0 or self.support_vertical_offset_mm < 0: raise ValueError("CG and support offsets must be non-negative")
        if min(self.facial_preload_n, self.release_force_n, self.release_travel_mm, self.accidental_pull_n, self.grip_clearance_mm, self.hair_keepout_mm) < 0: raise ValueError("mechanical magnitudes cannot be negative")


@dataclass(frozen=True)
class RetentionResult:
    weight_n: float; pitch_moment_nm: float; occipital_vertical_n: float; crown_vertical_n: float; facial_vertical_n: float
    available_facial_friction_n: float; vertical_slip_margin_n: float; pitch_balance_force_n: float | None; pitch_load_path_closed: bool
    release_work_mj: float; accidental_release_margin_n: float; grip_access_ok: bool; hair_keepout_ok: bool
    evidence_status: str = "DIGITAL_SENSITIVITY_ONLY"


def evaluate_retention(p: RetentionInputs, *, min_grip_clearance_mm: float = 12.0, min_hair_keepout_mm: float = 5.0) -> RetentionResult:
    p.validate(); grip_gate = _exact_finite_scalar(min_grip_clearance_mm, "min_grip_clearance_mm"); hair_gate = _exact_finite_scalar(min_hair_keepout_mm, "min_hair_keepout_mm")
    if grip_gate < 0 or hair_gate < 0: raise ValueError("clearance gates must be non-negative")
    weight = p.loaded_mass_g / 1000.0 * G; occ = weight * p.occipital_share; crown = weight * p.crown_share; facial = max(0.0, weight - occ - crown)
    friction = p.facial_preload_n * p.friction_coefficient; pitch = weight * p.cg_anterior_mm / 1000.0
    if pitch == 0.0: pitch_force, pitch_closed = 0.0, True
    elif p.support_vertical_offset_mm > 0.0: pitch_force, pitch_closed = pitch / (p.support_vertical_offset_mm / 1000.0), True
    else: pitch_force, pitch_closed = None, False
    return RetentionResult(weight, pitch, occ, crown, facial, friction, friction - facial, pitch_force, pitch_closed, p.release_force_n * p.release_travel_mm, p.release_force_n - p.accidental_pull_n, p.grip_clearance_mm >= grip_gate, p.hair_keepout_mm >= hair_gate)


def retention_doe(base: RetentionInputs, *, cg_mm=(20.0, 25.0, 30.0), friction=(0.25, 0.40, 0.55), crown_share=(0.35, 0.50, 0.65), support_vertical_offset_mm: tuple[float, ...] | None = None) -> tuple[RetentionResult, ...]:
    base.validate(); offsets = support_vertical_offset_mm if support_vertical_offset_mm is not None else (base.support_vertical_offset_mm,)
    if type(offsets) is not tuple or not offsets: raise ValueError("support_vertical_offset_mm DOE must be a non-empty tuple")
    out=[]
    for z in cg_mm:
        for mu in friction:
            for crown in crown_share:
                for offset in offsets:
                    z=_exact_finite_scalar(z,"DOE cg"); mu=_exact_finite_scalar(mu,"DOE friction"); crown=_exact_finite_scalar(crown,"DOE crown_share"); offset=_exact_finite_scalar(offset,"DOE support_vertical_offset")
                    occ=min(base.occipital_share,1.0-crown); p=RetentionInputs(**{**base.__dict__,"cg_anterior_mm":z,"friction_coefficient":mu,"crown_share":crown,"occipital_share":occ,"support_vertical_offset_mm":offset}); out.append(evaluate_retention(p))
    return tuple(out)


def _vector_mm(value: object, label: str) -> tuple[float,float,float]:
    if type(value) is not tuple or len(value)!=3: raise ValueError(f"{label} must be an xyz 3-tuple in millimetres")
    return tuple(_exact_finite_scalar(v,f"{label} coordinate") for v in value)  # type: ignore[return-value]


def _point_segment_distance_3d(p: object,a: object,b: object)->float:
    p3,a3,b3=_vector_mm(p,"protected point"),_vector_mm(a,"trajectory point"),_vector_mm(b,"trajectory point"); v=tuple(b3[i]-a3[i] for i in range(3)); w=tuple(p3[i]-a3[i] for i in range(3)); vv=sum(q*q for q in v)
    if vv==0.0: return sqrt(sum((p3[i]-a3[i])**2 for i in range(3)))
    t=max(0.0,min(1.0,sum(w[i]*v[i] for i in range(3))/vv)); closest=tuple(a3[i]+t*v[i] for i in range(3)); return sqrt(sum((p3[i]-closest[i])**2 for i in range(3)))


def release_trajectory_clearance(samples_mm, protected_points_mm, *, minimum_clearance_mm: float)->float:
    if type(samples_mm) is not tuple or len(samples_mm)<2 or type(protected_points_mm) is not tuple or not protected_points_mm: raise ValueError("trajectory needs >=2 samples and >=1 protected point")
    gate=_exact_finite_scalar(minimum_clearance_mm,"minimum_clearance_mm")
    if gate<0: raise ValueError("minimum_clearance_mm must be non-negative")
    for i,p in enumerate(samples_mm): _vector_mm(p,f"trajectory sample {i}")
    for i,p in enumerate(protected_points_mm): _vector_mm(p,f"protected point {i}")
    dmin=min(_point_segment_distance_3d(p,a,b) for a,b in zip(samples_mm,samples_mm[1:]) for p in protected_points_mm)
    if dmin<gate: raise ValueError(f"release trajectory violates protected clearance: {dmin:.6g} mm < {gate:.6g} mm")
    return dmin


def release_capsule_clearance(samples_mm, protected_spheres, *, moving_radius_mm: float, minimum_surface_clearance_mm: float)->float:
    """Finite-body piecewise-linear release sweep preflight."""
    if type(samples_mm) is not tuple or len(samples_mm)<2: raise ValueError("trajectory needs >=2 samples")
    if type(protected_spheres) is not tuple or not protected_spheres: raise ValueError("protected_spheres must be a non-empty tuple")
    moving_r=_exact_finite_scalar(moving_radius_mm,"moving_radius_mm"); gate=_exact_finite_scalar(minimum_surface_clearance_mm,"minimum_surface_clearance_mm")
    if moving_r<0 or gate<0: raise ValueError("radii and clearance gates must be non-negative")
    for i,p in enumerate(samples_mm): _vector_mm(p,f"trajectory sample {i}")
    bounded=[]
    for i,item in enumerate(protected_spheres):
        if type(item) is not tuple or len(item)!=2: raise ValueError(f"protected sphere {i} must be (xyz, radius_mm)")
        centre=_vector_mm(item[0],f"protected sphere {i} centre"); radius=_exact_finite_scalar(item[1],f"protected sphere {i} radius_mm")
        if radius<0: raise ValueError("protected radii must be non-negative")
        bounded.append((centre,radius))
    surface_min=min(_point_segment_distance_3d(c,a,b)-moving_r-r for a,b in zip(samples_mm,samples_mm[1:]) for c,r in bounded)
    if surface_min<gate: raise ValueError(f"finite release sweep violates protected surface clearance: {surface_min:.6g} mm < {gate:.6g} mm")
    return surface_min


def release_capsule_tolerance_clearance(samples_mm, protected_spheres, *, moving_radius_mm: float,
    moving_radius_plus_tol_mm: float, protected_radius_plus_tol_mm: float,
    trajectory_position_tol_mm: float, protected_position_tol_mm: float,
    minimum_surface_clearance_mm: float) -> float:
    """Worst-case finite release clearance with explicit radial and datum uncertainty.

    Independent bounded positional uncertainties are conservatively summed as radial
    Minkowski inflation. This is deterministic worst-case preflight, not statistical
    RSS and not continuous CAD collision proof.
    """
    mr=_exact_finite_scalar(moving_radius_mm,"moving_radius_mm")
    mt=_exact_finite_scalar(moving_radius_plus_tol_mm,"moving_radius_plus_tol_mm")
    prt=_exact_finite_scalar(protected_radius_plus_tol_mm,"protected_radius_plus_tol_mm")
    tt=_exact_finite_scalar(trajectory_position_tol_mm,"trajectory_position_tol_mm")
    pt=_exact_finite_scalar(protected_position_tol_mm,"protected_position_tol_mm")
    gate=_exact_finite_scalar(minimum_surface_clearance_mm,"minimum_surface_clearance_mm")
    if min(mr,mt,prt,tt,pt,gate)<0: raise ValueError("release tolerance magnitudes must be non-negative")
    inflated=[]
    if type(protected_spheres) is not tuple or not protected_spheres: raise ValueError("protected_spheres must be a non-empty tuple")
    for i,item in enumerate(protected_spheres):
        if type(item) is not tuple or len(item)!=2: raise ValueError(f"protected sphere {i} must be (xyz, radius_mm)")
        c=_vector_mm(item[0],f"protected sphere {i} centre"); r=_exact_finite_scalar(item[1],f"protected sphere {i} radius_mm")
        if r<0: raise ValueError("protected radii must be non-negative")
        inflated.append((c,r+prt+tt+pt))
    return release_capsule_clearance(samples_mm,tuple(inflated),moving_radius_mm=mr+mt,minimum_surface_clearance_mm=gate)
