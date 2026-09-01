"""Physical retention and emergency-release engineering model.

Calculations are deterministic engineering preflight only. They do not establish human
comfort, universal fit, production release force, release time, fatigue life or acoustic
performance.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import hypot, isfinite

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
    """Controlled inputs for a quasi-static retention/load-path check.

    +z is anterior of the support resultant. Forces are magnitudes in newtons.
    ``support_vertical_offset_mm`` is retained as a controlled datum but is not used to
    manufacture a moment without a controlled horizontal reaction force.
    """

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
        for label, value in self.__dict__.items():
            _exact_finite_scalar(value, label)
        if not 0.0 <= self.occipital_share <= 1.0:
            raise ValueError("occipital_share outside [0,1]")
        if not 0.0 <= self.crown_share <= 1.0:
            raise ValueError("crown_share outside [0,1]")
        if self.occipital_share + self.crown_share > 1.0 + 1e-9:
            raise ValueError("occipital and crown load shares exceed unity")
        if self.loaded_mass_g <= 0 or self.friction_coefficient < 0:
            raise ValueError("mass must be positive and friction non-negative")
        if min(self.facial_preload_n, self.release_force_n, self.release_travel_mm,
               self.accidental_pull_n, self.grip_clearance_mm, self.hair_keepout_mm) < 0:
            raise ValueError("mechanical magnitudes cannot be negative")


@dataclass(frozen=True)
class RetentionResult:
    weight_n: float
    pitch_moment_nm: float
    occipital_vertical_n: float
    crown_vertical_n: float
    facial_vertical_n: float
    available_facial_friction_n: float
    vertical_slip_margin_n: float
    release_work_mj: float
    accidental_release_margin_n: float
    grip_access_ok: bool
    hair_keepout_ok: bool
    evidence_status: str = "DIGITAL_SENSITIVITY_ONLY"


def evaluate_retention(p: RetentionInputs, *, min_grip_clearance_mm: float = 12.0,
                       min_hair_keepout_mm: float = 5.0) -> RetentionResult:
    p.validate()
    grip_gate = _exact_finite_scalar(min_grip_clearance_mm, "min_grip_clearance_mm")
    hair_gate = _exact_finite_scalar(min_hair_keepout_mm, "min_hair_keepout_mm")
    if grip_gate < 0 or hair_gate < 0:
        raise ValueError("clearance gates must be non-negative")
    weight = p.loaded_mass_g / 1000.0 * G
    occ = weight * p.occipital_share
    crown = weight * p.crown_share
    facial = max(0.0, weight - occ - crown)
    friction = p.facial_preload_n * p.friction_coefficient
    pitch = weight * p.cg_anterior_mm / 1000.0
    return RetentionResult(
        weight_n=weight,
        pitch_moment_nm=pitch,
        occipital_vertical_n=occ,
        crown_vertical_n=crown,
        facial_vertical_n=facial,
        available_facial_friction_n=friction,
        vertical_slip_margin_n=friction - facial,
        release_work_mj=p.release_force_n * p.release_travel_mm,
        accidental_release_margin_n=p.release_force_n - p.accidental_pull_n,
        grip_access_ok=p.grip_clearance_mm >= grip_gate,
        hair_keepout_ok=p.hair_keepout_mm >= hair_gate,
    )


def retention_doe(base: RetentionInputs, *, cg_mm=(20.0, 25.0, 30.0),
                  friction=(0.25, 0.40, 0.55), crown_share=(0.35, 0.50, 0.65)) -> tuple[RetentionResult, ...]:
    """Bounded sensitivity sweep for unresolved fit/material inputs."""
    base.validate()
    out: list[RetentionResult] = []
    for z in cg_mm:
        for mu in friction:
            for crown in crown_share:
                z = _exact_finite_scalar(z, "DOE cg")
                mu = _exact_finite_scalar(mu, "DOE friction")
                crown = _exact_finite_scalar(crown, "DOE crown_share")
                occ = min(base.occipital_share, 1.0 - crown)
                p = RetentionInputs(**{**base.__dict__, "cg_anterior_mm": z,
                    "friction_coefficient": mu, "crown_share": crown, "occipital_share": occ})
                out.append(evaluate_retention(p))
    return tuple(out)


def _point_segment_distance(p: tuple[float, float], a: tuple[float, float],
                            b: tuple[float, float]) -> float:
    px, py = map(float, p); ax, ay = map(float, a); bx, by = map(float, b)
    if not all(isfinite(v) for v in (px, py, ax, ay, bx, by)):
        raise ValueError("trajectory coordinates must be finite")
    vx, vy = bx - ax, by - ay
    vv = vx * vx + vy * vy
    if vv == 0.0:
        return hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / vv))
    return hypot(px - (ax + t * vx), py - (ay + t * vy))


def release_trajectory_clearance(samples_mm: tuple[tuple[float, float], ...],
                                 protected_points_mm: tuple[tuple[float, float], ...], *,
                                 minimum_clearance_mm: float) -> float:
    """Return conservative clearance over every straight segment between samples.

    This closes the previous endpoint-only blind spot for piecewise-linear controlled
    trajectories. It is still not proof for an unknown curved path between CAD samples.
    ``minimum_clearance_mm`` is an enforced gate, not decorative metadata.
    """
    if type(samples_mm) is not tuple or len(samples_mm) < 2 or type(protected_points_mm) is not tuple or not protected_points_mm:
        raise ValueError("trajectory needs >=2 samples and >=1 protected point")
    gate = _exact_finite_scalar(minimum_clearance_mm, "minimum_clearance_mm")
    if gate < 0:
        raise ValueError("minimum_clearance_mm must be non-negative")
    dmin = min(_point_segment_distance(p, a, b)
               for a, b in zip(samples_mm, samples_mm[1:]) for p in protected_points_mm)
    if dmin < gate:
        raise ValueError(f"release trajectory violates protected clearance: {dmin:.6g} mm < {gate:.6g} mm")
    return dmin
