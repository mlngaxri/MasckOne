"""Inertial retention load-path sensitivity model.

Deterministic preflight for prescribed head-motion load cases. Coordinate contract:
+x = wearer right (lateral), +y = anterior, +z = superior. CG offsets are measured
+from the retention support reference. Moments are computed from r x F. Outputs do
+not establish comfort, human acceleration exposure, damping or fatigue life.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import hypot, isfinite

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

    def validate(self) -> None:
        for label, value in self.__dict__.items():
            _finite(value, label)
        if self.loaded_mass_g <= 0:
            raise ValueError("loaded_mass_g must be positive")
        if self.bilateral_support_span_mm < 0 or self.vertical_support_span_mm < 0:
            raise ValueError("support spans must be non-negative")


@dataclass(frozen=True)
class InertialRetentionResult:
    lateral_force_n: float
    fore_aft_force_n: float
    translational_resultant_n: float
    yaw_moment_nm: float
    pitch_moment_nm: float
    yaw_couple_force_n: float | None
    pitch_couple_force_n: float | None
    yaw_load_path_closed: bool
    pitch_load_path_closed: bool
    evidence_status: str = "DIGITAL_SENSITIVITY_ONLY"


def evaluate_inertial_retention(p: InertialRetentionInputs) -> InertialRetentionResult:
    """Resolve prescribed translational loads and CG moments into support couples.

    With r=(x,y,z) and F=(Fx,Fy,0), r x F gives yaw Mz=x*Fy-y*Fx and
    pitch Mx=-z*Fy. This deliberately prevents an anterior offset parallel to a
    fore-aft force from creating a fictitious pitch moment.
    """
    p.validate()
    mass_kg = p.loaded_mass_g / 1000.0
    lateral = mass_kg * p.lateral_accel_g * G
    fore_aft = mass_kg * p.fore_aft_accel_g * G
    resultant = hypot(lateral, fore_aft)
    x = p.cg_lateral_mm / 1000.0
    y = p.cg_anterior_mm / 1000.0
    z = p.cg_vertical_mm / 1000.0
    yaw = x * fore_aft - y * lateral
    pitch = -z * fore_aft

    if yaw == 0.0:
        yaw_force, yaw_closed = 0.0, True
    elif p.bilateral_support_span_mm > 0.0:
        yaw_force, yaw_closed = abs(yaw) / (p.bilateral_support_span_mm / 1000.0), True
    else:
        yaw_force, yaw_closed = None, False

    if pitch == 0.0:
        pitch_force, pitch_closed = 0.0, True
    elif p.vertical_support_span_mm > 0.0:
        pitch_force, pitch_closed = abs(pitch) / (p.vertical_support_span_mm / 1000.0), True
    else:
        pitch_force, pitch_closed = None, False

    return InertialRetentionResult(lateral, fore_aft, resultant, yaw, pitch,
                                   yaw_force, pitch_force, yaw_closed, pitch_closed)


def inertial_retention_doe(
    base: InertialRetentionInputs, *,
    lateral_accel_g: tuple[float, ...] = (-0.5, 0.0, 0.5),
    fore_aft_accel_g: tuple[float, ...] = (-0.5, 0.0, 0.5),
) -> tuple[InertialRetentionResult, ...]:
    """Bounded prescribed-acceleration sweep, not a human-motion claim."""
    base.validate()
    if type(lateral_accel_g) is not tuple or not lateral_accel_g:
        raise ValueError("lateral_accel_g DOE must be a non-empty tuple")
    if type(fore_aft_accel_g) is not tuple or not fore_aft_accel_g:
        raise ValueError("fore_aft_accel_g DOE must be a non-empty tuple")
    out: list[InertialRetentionResult] = []
    for lat in lateral_accel_g:
        lat = _finite(lat, "DOE lateral_accel_g")
        for fore in fore_aft_accel_g:
            fore = _finite(fore, "DOE fore_aft_accel_g")
            q = InertialRetentionInputs(**{**base.__dict__, "lateral_accel_g": lat,
                                          "fore_aft_accel_g": fore})
            out.append(evaluate_inertial_retention(q))
    return tuple(out)
