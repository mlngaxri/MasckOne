"""Analytical screen for breathing resistance added by the mask aperture.

`config/masck_one_authority.yaml` states two added-pressure-drop limits and a
frozen no-collapse test flow, but nothing in the repository connected those
numbers to aperture geometry. Two requirements and a geometry floor sat side by
side with no model relating them, so no candidate aperture could be screened and
no structural load could be derived from the safety test.

This module closes that gap analytically.

Model
-----
Incompressible quasi-steady flow at the peak of the breathing cycle. Mach is
below 0.03 at every flow considered, so compressibility is ignored. The added
path is treated as a short aperture in a thin wall, with the loss written in the
standard form

    dP = K * (rho * V^2 / 2),      V = Q_path / A_min

where ``K`` collects contraction, wall-friction and expansion contributions
referenced to the aperture velocity. For the released wall thickness the duct is
hydraulically very short (L/D_h < 0.25), so friction is a small correction and
the separation-driven contraction and expansion terms dominate.

What this establishes and what it does not
------------------------------------------
The screen converts flow-specific requirements into a single geometry-independent
design budget, and derives the suction load implied by the frozen no-collapse
test. Both are model results.

It is NOT a measurement. Real nasal airflow is cyclic, not steady; the aperture
is bounded by compliant material that deflects under the very load being
computed; ``K`` is only weakly Reynolds-independent in the transitional range
these flows occupy; and no allowance is made for humidity, mucus, ambient
temperature or the wearer's own nasal resistance. Measured breathing resistance
on physical hardware remains required.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

from .authority import Authority


class AirwayResistanceError(ValueError):
    """Raised when an airway resistance screen input or contract is invalid."""


EVIDENCE_STATUS = "ANALYTICAL_SCREEN_NOT_MEASURED_BREATHING_RESISTANCE"

# Dry air at 25 degC, 101.325 kPa. Stated explicitly because every result below
# scales with density, and a screen that hides its fluid properties is not a
# screen. Source: NIST reference values for dry air at standard conditions.
AIR_DENSITY_KG_M3 = 1.184
AIR_DYNAMIC_VISCOSITY_PA_S = 1.849e-5
AIR_REFERENCE_TEMPERATURE_C = 25.0
AIR_REFERENCE_PRESSURE_KPA = 101.325

# Masck One presents one aperture per nostril; the two breathe in parallel.
PARALLEL_AIRWAY_PATHS = 2

# Total loss coefficients referenced to aperture velocity, for a short aperture
# discharging into an open region. Handbook values (Idelchik, "Handbook of
# Hydraulic Resistance"; Blevins, "Applied Fluid Dynamics Handbook"), quoted as
# planning values with explicit spread rather than as measured constants for
# this geometry.
#
#   sharp        thin plate, square edges - contraction plus vena contracta
#                recovery plus full exit loss
#   chamfered    ~45 deg lead-in over roughly a quarter of the wall
#   radiused     r/D >= 0.2 bellmouth; contraction loss nearly vanishes and the
#                exit loss dominates
EDGE_TREATMENTS: dict[str, tuple[float, float]] = {
    "sharp": (2.60, 2.90),
    "chamfered": (1.35, 1.70),
    "radiused": (1.00, 1.15),
}

# Reynolds number below which K should be treated as Re-dependent rather than a
# constant. Separation-dominated losses are close to Re-independent well above
# this; the flows of interest sit near it, which is a stated limitation.
FULLY_ROUGH_REYNOLDS_FLOOR = 1.0e4


def _positive(value: float, label: str) -> float:
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise AirwayResistanceError(f"{label} must be finite and positive, got {value!r}")
    return result


def volumetric_flow_m3_s(flow_lpm: float) -> float:
    """Convert a total minute-flow in L/min to SI volumetric flow."""

    return _positive(flow_lpm, "flow_lpm") / 60_000.0


def path_velocity_m_s(flow_lpm: float, area_mm2: float, *, paths: int = PARALLEL_AIRWAY_PATHS) -> float:
    """Mean aperture velocity when total flow splits evenly across parallel paths."""

    if paths < 1:
        raise AirwayResistanceError("paths must be at least 1")
    area_m2 = _positive(area_mm2, "area_mm2") * 1e-6
    return volumetric_flow_m3_s(flow_lpm) / paths / area_m2


def dynamic_pressure_pa(velocity_m_s: float) -> float:
    """rho * V^2 / 2, the inertial scale every loss term is referenced to."""

    velocity = float(velocity_m_s)
    if not math.isfinite(velocity):
        raise AirwayResistanceError("velocity must be finite")
    return 0.5 * AIR_DENSITY_KG_M3 * velocity * velocity


def equivalent_circular_diameter_mm(area_mm2: float) -> float:
    """Diameter of the circle with the same area as the aperture.

    Used as the Reynolds length scale. For a circular aperture this equals the
    hydraulic diameter 4A/P exactly; for a slot or lobed opening of the same
    area it is larger than the true hydraulic diameter, so the Reynolds numbers
    reported here are upper estimates for non-circular geometry. Since the
    screen's conclusion is that K sits *below* the Re-independent range, an
    overestimate is the conservative direction.
    """

    return math.sqrt(4.0 * _positive(area_mm2, "area_mm2") / math.pi)


def reynolds_number(flow_lpm: float, area_mm2: float, *, paths: int = PARALLEL_AIRWAY_PATHS) -> float:
    velocity = path_velocity_m_s(flow_lpm, area_mm2, paths=paths)
    length_scale_m = equivalent_circular_diameter_mm(area_mm2) * 1e-3
    return AIR_DENSITY_KG_M3 * velocity * length_scale_m / AIR_DYNAMIC_VISCOSITY_PA_S


def added_pressure_drop_pa(
    flow_lpm: float,
    area_mm2: float,
    loss_coefficient: float,
    *,
    paths: int = PARALLEL_AIRWAY_PATHS,
) -> float:
    """Added drop across the mask aperture at a given flow."""

    k = _positive(loss_coefficient, "loss_coefficient")
    return k * dynamic_pressure_pa(path_velocity_m_s(flow_lpm, area_mm2, paths=paths))


def allowable_loss_coefficient(
    flow_lpm: float,
    area_mm2: float,
    pressure_limit_pa: float,
    *,
    paths: int = PARALLEL_AIRWAY_PATHS,
) -> float:
    """Largest K that still meets a pressure limit at this flow and area."""

    limit = _positive(pressure_limit_pa, "pressure_limit_pa")
    return limit / dynamic_pressure_pa(path_velocity_m_s(flow_lpm, area_mm2, paths=paths))


def minimum_compliant_area_mm2(
    flow_lpm: float,
    pressure_limit_pa: float,
    loss_coefficient: float,
    *,
    paths: int = PARALLEL_AIRWAY_PATHS,
) -> float:
    """Smallest aperture area that still meets the limit for a given K.

    Because dP scales as 1/A^2, this is the quantity that matters under
    misregistration and membrane deflection: it says how much the aperture may
    close before breathing resistance leaves budget.
    """

    k = _positive(loss_coefficient, "loss_coefficient")
    limit = _positive(pressure_limit_pa, "pressure_limit_pa")
    q_path = volumetric_flow_m3_s(flow_lpm) / max(int(paths), 1)
    area_m2 = q_path * math.sqrt(k * AIR_DENSITY_KG_M3 / (2.0 * limit))
    return area_m2 * 1e6


@dataclass(frozen=True, slots=True)
class AirwayScreenPoint:
    """One flow condition evaluated against one requirement."""

    flow_lpm: float
    area_mm2: float
    velocity_m_s: float
    reynolds: float
    dynamic_pressure_pa: float
    pressure_limit_pa: float | None
    allowable_loss_coefficient: float | None
    reynolds_below_re_independent_floor: bool

    def manifest(self) -> dict[str, object]:
        return {
            "flow_lpm": self.flow_lpm,
            "area_mm2": self.area_mm2,
            "velocity_m_s": round(self.velocity_m_s, 6),
            "reynolds": round(self.reynolds, 1),
            "dynamic_pressure_pa": round(self.dynamic_pressure_pa, 6),
            "pressure_limit_pa": self.pressure_limit_pa,
            "allowable_loss_coefficient": (
                None
                if self.allowable_loss_coefficient is None
                else round(self.allowable_loss_coefficient, 6)
            ),
            "reynolds_below_re_independent_floor": self.reynolds_below_re_independent_floor,
        }


@dataclass(frozen=True, slots=True)
class EdgeTreatmentScreen:
    """One candidate aperture edge treatment screened against the budget."""

    treatment: str
    loss_coefficient_low: float
    loss_coefficient_high: float
    worst_case_pressure_pa: float
    meets_requirement: bool
    minimum_compliant_area_mm2: float
    area_margin_fraction: float

    def manifest(self) -> dict[str, object]:
        return {
            "treatment": self.treatment,
            "loss_coefficient_low": self.loss_coefficient_low,
            "loss_coefficient_high": self.loss_coefficient_high,
            "worst_case_pressure_pa": round(self.worst_case_pressure_pa, 4),
            "meets_requirement": self.meets_requirement,
            "minimum_compliant_area_mm2": round(self.minimum_compliant_area_mm2, 3),
            "area_margin_fraction": round(self.area_margin_fraction, 6),
        }


@dataclass(frozen=True)
class AirwayResistanceScreen:
    """Deterministic breathing-resistance screen bound to the machine authority."""

    minimum_area_mm2: float
    equivalent_circular_diameter_mm: float
    requirement_points: tuple[AirwayScreenPoint, ...]
    implied_loss_coefficient_budget: float
    requirement_points_are_mutually_consistent: bool
    edge_treatments: tuple[EdgeTreatmentScreen, ...]
    no_collapse_flow_lpm: float
    no_collapse_suction_pa_by_treatment: dict[str, float]
    evidence_status: str = EVIDENCE_STATUS

    def manifest(self) -> dict[str, object]:
        return {
            "schema": "MASCK_ONE_AIRWAY_RESISTANCE_SCREEN_V1",
            "evidence_status": self.evidence_status,
            "air_reference": {
                "density_kg_m3": AIR_DENSITY_KG_M3,
                "dynamic_viscosity_pa_s": AIR_DYNAMIC_VISCOSITY_PA_S,
                "temperature_c": AIR_REFERENCE_TEMPERATURE_C,
                "pressure_kpa": AIR_REFERENCE_PRESSURE_KPA,
            },
            "parallel_paths": PARALLEL_AIRWAY_PATHS,
            "minimum_area_mm2": self.minimum_area_mm2,
            "equivalent_circular_diameter_mm": round(self.equivalent_circular_diameter_mm, 4),
            "requirement_points": [p.manifest() for p in self.requirement_points],
            "implied_loss_coefficient_budget": round(self.implied_loss_coefficient_budget, 6),
            "requirement_points_are_mutually_consistent": self.requirement_points_are_mutually_consistent,
            "edge_treatments": [t.manifest() for t in self.edge_treatments],
            "no_collapse_flow_lpm": self.no_collapse_flow_lpm,
            "no_collapse_suction_pa_by_treatment": {
                name: round(value, 3)
                for name, value in sorted(self.no_collapse_suction_pa_by_treatment.items())
            },
            "not_evidence_of": [
                "measured breathing resistance",
                "cyclic or transient airflow behaviour",
                "aperture deflection under load",
                "wearer comfort or perceived effort",
                "nasal collapse margin of the compliant structure",
            ],
        }

    def worst_case_budget_consumer(self) -> EdgeTreatmentScreen:
        """The edge treatment that consumes the most of the K budget."""

        return max(self.edge_treatments, key=lambda t: t.loss_coefficient_high)


def build_airway_resistance_screen(authority: Authority) -> AirwayResistanceScreen:
    """Screen the released airway requirement set against aperture geometry."""

    area = _positive(
        authority.number("safety", "airway", "minimum_area_each_mm2"),
        "safety.airway.minimum_area_each_mm2",
    )
    limits = authority.get("safety", "airway", "max_added_pressure_drop_pa")
    if not isinstance(limits, dict) or not limits:
        raise AirwayResistanceError("safety.airway.max_added_pressure_drop_pa must be a mapping")

    points: list[AirwayScreenPoint] = []
    budgets: list[float] = []
    for key in sorted(limits):
        if not key.startswith("at_") or not key.endswith("_lpm"):
            raise AirwayResistanceError(
                f"airway pressure-drop key {key!r} must be of the form at_<flow>_lpm"
            )
        try:
            flow = float(key[len("at_") : -len("_lpm")])
        except ValueError as exc:
            raise AirwayResistanceError(f"airway pressure-drop key {key!r} has no parsable flow") from exc
        limit = _positive(limits[key], f"safety.airway.max_added_pressure_drop_pa.{key}")
        velocity = path_velocity_m_s(flow, area)
        budget = allowable_loss_coefficient(flow, area, limit)
        budgets.append(budget)
        points.append(
            AirwayScreenPoint(
                flow_lpm=flow,
                area_mm2=area,
                velocity_m_s=velocity,
                reynolds=reynolds_number(flow, area),
                dynamic_pressure_pa=dynamic_pressure_pa(velocity),
                pressure_limit_pa=limit,
                allowable_loss_coefficient=budget,
                reynolds_below_re_independent_floor=(
                    reynolds_number(flow, area) < FULLY_ROUGH_REYNOLDS_FLOOR
                ),
            )
        )

    if not points:
        raise AirwayResistanceError("no airway requirement points were derived")

    # A fixed aperture has one loss coefficient. If two flow-specific limits
    # imply different coefficients, no single geometry can satisfy both and the
    # requirement pair is internally inconsistent regardless of design effort.
    budget = min(budgets)
    consistent = all(
        math.isclose(value, budgets[0], rel_tol=1e-6, abs_tol=1e-9) for value in budgets
    )

    # The binding requirement is the tightest budget; screen against that.
    binding = min(points, key=lambda p: p.allowable_loss_coefficient or math.inf)
    treatments: list[EdgeTreatmentScreen] = []
    for name, (k_low, k_high) in sorted(EDGE_TREATMENTS.items()):
        worst = added_pressure_drop_pa(binding.flow_lpm, area, k_high)
        area_floor = minimum_compliant_area_mm2(
            binding.flow_lpm, binding.pressure_limit_pa or 0.0, k_high
        )
        treatments.append(
            EdgeTreatmentScreen(
                treatment=name,
                loss_coefficient_low=k_low,
                loss_coefficient_high=k_high,
                worst_case_pressure_pa=worst,
                meets_requirement=k_high <= budget,
                minimum_compliant_area_mm2=area_floor,
                area_margin_fraction=(area - area_floor) / area,
            )
        )

    collapse_flow = _positive(
        authority.number("safety", "airway", "no_collapse_test_flow_lpm"),
        "safety.airway.no_collapse_test_flow_lpm",
    )
    collapse_loads = {
        name: added_pressure_drop_pa(collapse_flow, area, k_high)
        for name, (_, k_high) in EDGE_TREATMENTS.items()
    }

    return AirwayResistanceScreen(
        minimum_area_mm2=area,
        equivalent_circular_diameter_mm=equivalent_circular_diameter_mm(area),
        requirement_points=tuple(points),
        implied_loss_coefficient_budget=budget,
        requirement_points_are_mutually_consistent=consistent,
        edge_treatments=tuple(treatments),
        no_collapse_flow_lpm=collapse_flow,
        no_collapse_suction_pa_by_treatment=collapse_loads,
    )
