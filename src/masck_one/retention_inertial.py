"""Inertial retention load-path sensitivity model.

Deterministic preflight for prescribed head-motion load cases. Coordinate contract:
+x = wearer right (lateral), +y = anterior, +z = superior. CG offsets are measured
from the retention support reference. Translational moments are r x F. Optional
angular-acceleration terms use a principal-axis rigid-body approximation M = I*alpha;
they are sensitivity inputs, not measured human-motion or mass-property evidence.
Outputs do not establish comfort, damping, resonance or fatigue life.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, sqrt

G = 9.80665


def _finite(value: object, label: str) -> float:
    if type(value) not in (int, float):
        raise ValueError(f"{label} must be an exact numeric scalar")
    value = float(value)
    if not isfinite(value):
        raise ValueError(f"{label} must be finite")
    return value


@dataclass(frozen=True)
class InertialRetentionInputs:
    loaded_mass_g: float
    lateral_accel_g: float
    fore_aft_accel_g: float
    cg_lateral_mm: float
    cg_anterior_mm: float
    cg_vertical_mm: float
    bilateral_support_span_mm: float
    vertical_support_span_mm: float
    vertical_accel_g: float = 0.0
    pitch_angular_accel_rad_s2: float = 0.0
    roll_angular_accel_rad_s2: float = 0.0
    yaw_angular_accel_rad_s2: float = 0.0
    pitch_inertia_kg_m2: float = 0.0
    roll_inertia_kg_m2: float = 0.0
    yaw_inertia_kg_m2: float = 0.0

    def validate(self) -> None:
        for label, value in self.__dict__.items():
            _finite(value, label)
        if self.loaded_mass_g <= 0:
            raise ValueError("loaded_mass_g must be positive")
        if self.bilateral_support_span_mm < 0 or self.vertical_support_span_mm < 0:
            raise ValueError("support spans must be non-negative")
        if min(self.pitch_inertia_kg_m2, self.roll_inertia_kg_m2, self.yaw_inertia_kg_m2) < 0:
            raise ValueError("principal inertias must be non-negative")


@dataclass(frozen=True)
class InertialRetentionResult:
    lateral_force_n: float
    fore_aft_force_n: float
    vertical_force_n: float
    translational_resultant_n: float
    yaw_moment_nm: float
    pitch_moment_nm: float
    roll_moment_nm: float
    yaw_couple_force_n: float | None
    pitch_couple_force_n: float | None
    roll_couple_force_n: float | None
    bilateral_resultant_couple_force_n: float | None
    yaw_load_path_closed: bool
    pitch_load_path_closed: bool
    roll_load_path_closed: bool
    bilateral_load_path_closed: bool
    translational_yaw_moment_nm: float = 0.0
    translational_pitch_moment_nm: float = 0.0
    translational_roll_moment_nm: float = 0.0
    rotational_yaw_moment_nm: float = 0.0
    rotational_pitch_moment_nm: float = 0.0
    rotational_roll_moment_nm: float = 0.0
    evidence_status: str = "DIGITAL_SENSITIVITY_ONLY"


def _resolve_couple(moment_nm: float, span_mm: float) -> tuple[float | None, bool]:
    if moment_nm == 0.0:
        return 0.0, True
    if span_mm > 0.0:
        return abs(moment_nm) / (span_mm / 1000.0), True
    return None, False


def evaluate_inertial_retention(p: InertialRetentionInputs) -> InertialRetentionResult:
    """Resolve prescribed 3D translation and principal-axis rotation into support couples.

    With r=(x,y,z) and F=(Fx,Fy,Fz), r x F gives pitch Mx=y*Fz-z*Fy,
    roll My=z*Fx-x*Fz, and yaw Mz=x*Fy-y*Fx. Vertical translation is included.
    Principal-axis rotational inertia adds I*alpha. Gravity is handled by the separate
    quasi-static ledger. Yaw and roll both terminate through the bilateral support span,
    so their orthogonal couple-force components are also resolved as one resultant.
    Reporting only the two scalar components would understate the actual bilateral
    interface demand when yaw and roll occur simultaneously. Products of inertia and
    gyroscopic terms remain blocked pending controlled CAD mass properties and angular
    velocity inputs.
    """
    p.validate()
    mass_kg = p.loaded_mass_g / 1000.0
    lateral = mass_kg * p.lateral_accel_g * G
    fore_aft = mass_kg * p.fore_aft_accel_g * G
    vertical = mass_kg * p.vertical_accel_g * G
    resultant = sqrt(lateral * lateral + fore_aft * fore_aft + vertical * vertical)
    x = p.cg_lateral_mm / 1000.0
    y = p.cg_anterior_mm / 1000.0
    z = p.cg_vertical_mm / 1000.0

    t_pitch = y * vertical - z * fore_aft
    t_roll = z * lateral - x * vertical
    t_yaw = x * fore_aft - y * lateral
    r_pitch = p.pitch_inertia_kg_m2 * p.pitch_angular_accel_rad_s2
    r_roll = p.roll_inertia_kg_m2 * p.roll_angular_accel_rad_s2
    r_yaw = p.yaw_inertia_kg_m2 * p.yaw_angular_accel_rad_s2
    pitch = t_pitch + r_pitch
    roll = t_roll + r_roll
    yaw = t_yaw + r_yaw

    yaw_force, yaw_closed = _resolve_couple(yaw, p.bilateral_support_span_mm)
    pitch_force, pitch_closed = _resolve_couple(pitch, p.vertical_support_span_mm)
    roll_force, roll_closed = _resolve_couple(roll, p.bilateral_support_span_mm)
    bilateral_closed = yaw_closed and roll_closed
    bilateral_force = (
        sqrt(yaw_force * yaw_force + roll_force * roll_force)
        if bilateral_closed and yaw_force is not None and roll_force is not None
        else None
    )

    return InertialRetentionResult(
        lateral_force_n=lateral,
        fore_aft_force_n=fore_aft,
        vertical_force_n=vertical,
        translational_resultant_n=resultant,
        yaw_moment_nm=yaw,
        pitch_moment_nm=pitch,
        roll_moment_nm=roll,
        yaw_couple_force_n=yaw_force,
        pitch_couple_force_n=pitch_force,
        roll_couple_force_n=roll_force,
        bilateral_resultant_couple_force_n=bilateral_force,
        yaw_load_path_closed=yaw_closed,
        pitch_load_path_closed=pitch_closed,
        roll_load_path_closed=roll_closed,
        bilateral_load_path_closed=bilateral_closed,
        translational_yaw_moment_nm=t_yaw,
        translational_pitch_moment_nm=t_pitch,
        translational_roll_moment_nm=t_roll,
        rotational_yaw_moment_nm=r_yaw,
        rotational_pitch_moment_nm=r_pitch,
        rotational_roll_moment_nm=r_roll,
    )


def inertial_retention_doe(
    base: InertialRetentionInputs, *,
    lateral_accel_g: tuple[float, ...] = (-0.5, 0.0, 0.5),
    fore_aft_accel_g: tuple[float, ...] = (-0.5, 0.0, 0.5),
    vertical_accel_g: tuple[float, ...] = (0.0,),
) -> tuple[InertialRetentionResult, ...]:
    """Bounded prescribed-acceleration sweep, not a human-motion claim."""
    base.validate()
    for label, values in (("lateral_accel_g", lateral_accel_g),
                          ("fore_aft_accel_g", fore_aft_accel_g),
                          ("vertical_accel_g", vertical_accel_g)):
        if type(values) is not tuple or not values:
            raise ValueError(f"{label} DOE must be a non-empty tuple")
    out: list[InertialRetentionResult] = []
    for lat in lateral_accel_g:
        lat = _finite(lat, "DOE lateral_accel_g")
        for fore in fore_aft_accel_g:
            fore = _finite(fore, "DOE fore_aft_accel_g")
            for vert in vertical_accel_g:
                vert = _finite(vert, "DOE vertical_accel_g")
                q = InertialRetentionInputs(**{**base.__dict__, "lateral_accel_g": lat,
                    "fore_aft_accel_g": fore, "vertical_accel_g": vert})
                out.append(evaluate_inertial_retention(q))
    return tuple(out)
