"""Physical retention and emergency-release engineering model.

This module deliberately models mechanical requirements and sensitivity only.  It does
not claim human comfort, production fit, or measured release performance.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import hypot, isfinite

G = 9.80665


@dataclass(frozen=True)
class RetentionInputs:
    """Controlled inputs for a quasi-static retention/load-path check.

    Coordinates use the product sagittal plane: +z is anterior of the support
    resultant, +y is superior. Forces are magnitudes in newtons.
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
        vals = self.__dict__
        if not all(isfinite(float(v)) for v in vals.values()):
            raise ValueError("retention inputs must be finite")
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


def evaluate_retention(
    p: RetentionInputs,
    *,
    min_grip_clearance_mm: float = 12.0,
    min_hair_keepout_mm: float = 5.0,
) -> RetentionResult:
    """Resolve the primary quasi-static load path and release margins.

    Vertical weight is intentionally split into crown, occipital and residual
    facial reactions. Facial friction is not allowed to disappear from the
    ledger. A positive slip margin means the specified facial preload can
    frictionally react the residual vertical demand under this simple model.
    """
    p.validate()
    weight = p.loaded_mass_g / 1000.0 * G
    occ = weight * p.occipital_share
    crown = weight * p.crown_share
    facial = max(0.0, weight - occ - crown)
    friction = p.facial_preload_n * p.friction_coefficient
    pitch = weight * p.cg_anterior_mm / 1000.0
    release_work = p.release_force_n * p.release_travel_mm
    return RetentionResult(
        weight_n=weight,
        pitch_moment_nm=pitch,
        occipital_vertical_n=occ,
        crown_vertical_n=crown,
        facial_vertical_n=facial,
        available_facial_friction_n=friction,
        vertical_slip_margin_n=friction - facial,
        release_work_mj=release_work,
        accidental_release_margin_n=p.release_force_n - p.accidental_pull_n,
        grip_access_ok=p.grip_clearance_mm >= min_grip_clearance_mm,
        hair_keepout_ok=p.hair_keepout_mm >= min_hair_keepout_mm,
    )


def retention_doe(
    base: RetentionInputs,
    *,
    cg_mm=(20.0, 25.0, 30.0),
    friction=(0.25, 0.40, 0.55),
    crown_share=(0.35, 0.50, 0.65),
) -> tuple[RetentionResult, ...]:
    """Bounded sensitivity sweep for unresolved fit/material inputs."""
    out: list[RetentionResult] = []
    for z in cg_mm:
        for mu in friction:
            for crown in crown_share:
                occ = min(base.occipital_share, 1.0 - crown)
                p = RetentionInputs(**{
                    **base.__dict__,
                    "cg_anterior_mm": float(z),
                    "friction_coefficient": float(mu),
                    "crown_share": float(crown),
                    "occipital_share": float(occ),
                })
                out.append(evaluate_retention(p))
    return tuple(out)


def release_trajectory_clearance(
    samples_mm: tuple[tuple[float, float], ...],
    protected_points_mm: tuple[tuple[float, float], ...],
    *,
    minimum_clearance_mm: float,
) -> float:
    """Return minimum sampled 2D clearance for a release trajectory.

    Sampling is a digital preflight, not proof of continuous collision safety.
    The caller must choose sampling density from the real latch trajectory and
    preserve a separate continuous-sweep or physical-fixture gate.
    """
    if not samples_mm or not protected_points_mm:
        raise ValueError("trajectory and protected points must be non-empty")
    if minimum_clearance_mm < 0 or not isfinite(minimum_clearance_mm):
        raise ValueError("minimum_clearance_mm must be finite and non-negative")
    dmin = min(hypot(sx-px, sy-py) for sx, sy in samples_mm for px, py in protected_points_mm)
    if not isfinite(dmin):
        raise ValueError("trajectory coordinates must be finite")
    return dmin
