"""Screen tests for added breathing resistance.

These check the model's internal physics, its binding to the machine authority,
and — most importantly — that it refuses to present a calculation as a
measurement.
"""

from __future__ import annotations

import copy
import math

import pytest

from masck_one.airway_resistance import (
    AIR_DENSITY_KG_M3,
    EDGE_TREATMENTS,
    EVIDENCE_STATUS,
    PARALLEL_AIRWAY_PATHS,
    AirwayResistanceError,
    added_pressure_drop_pa,
    allowable_loss_coefficient,
    build_airway_resistance_screen,
    dynamic_pressure_pa,
    hydraulic_diameter_mm,
    minimum_compliant_area_mm2,
    path_velocity_m_s,
    reynolds_number,
)
from masck_one.authority import Authority, load_authority


@pytest.fixture(scope="module")
def authority() -> Authority:
    return load_authority()


@pytest.fixture(scope="module")
def screen(authority):
    return build_airway_resistance_screen(authority)


# --------------------------------------------------------------------------
# physics
# --------------------------------------------------------------------------

def test_velocity_splits_evenly_across_parallel_nostrils() -> None:
    # 60 L/min total through two 120 mm^2 apertures.
    v = path_velocity_m_s(60.0, 120.0)
    expected = (60.0 / 60_000.0 / 2) / 120e-6
    assert math.isclose(v, expected, rel_tol=1e-12)
    # One path carries twice the velocity of two.
    assert math.isclose(path_velocity_m_s(60.0, 120.0, paths=1), 2 * v, rel_tol=1e-12)


def test_dynamic_pressure_is_quadratic_in_velocity() -> None:
    assert math.isclose(dynamic_pressure_pa(2.0), 0.5 * AIR_DENSITY_KG_M3 * 4.0, rel_tol=1e-12)
    assert math.isclose(dynamic_pressure_pa(4.0), 4 * dynamic_pressure_pa(2.0), rel_tol=1e-12)


def test_pressure_drop_scales_with_square_of_flow() -> None:
    """Doubling flow through a fixed aperture quadruples the added drop."""

    low = added_pressure_drop_pa(30.0, 120.0, 2.8)
    high = added_pressure_drop_pa(60.0, 120.0, 2.8)
    assert math.isclose(high / low, 4.0, rel_tol=1e-12)


def test_pressure_drop_scales_with_inverse_square_of_area() -> None:
    """Halving the aperture quadruples the drop. This is why closure matters."""

    wide = added_pressure_drop_pa(30.0, 120.0, 2.8)
    narrow = added_pressure_drop_pa(30.0, 60.0, 2.8)
    assert math.isclose(narrow / wide, 4.0, rel_tol=1e-12)


def test_hydraulic_diameter_matches_equivalent_circle() -> None:
    d = hydraulic_diameter_mm(120.0)
    assert math.isclose(math.pi * (d / 2) ** 2, 120.0, rel_tol=1e-12)


def test_minimum_compliant_area_round_trips_against_pressure_drop() -> None:
    """The area floor is exactly where the drop equals the limit."""

    area = minimum_compliant_area_mm2(30.0, 10.0, 2.8)
    assert math.isclose(added_pressure_drop_pa(30.0, area, 2.8), 10.0, rel_tol=1e-9)


def test_allowable_coefficient_inverts_pressure_drop() -> None:
    k = allowable_loss_coefficient(30.0, 120.0, 10.0)
    assert math.isclose(added_pressure_drop_pa(30.0, 120.0, k), 10.0, rel_tol=1e-12)


def test_reynolds_number_is_in_the_transitional_range_the_docstring_claims() -> None:
    """The screen states K is only weakly Re-independent here; hold it to that."""

    re_30 = reynolds_number(30.0, 120.0)
    re_120 = reynolds_number(120.0, 120.0)
    assert 1_000 < re_30 < 3_000
    assert 5_000 < re_120 < 10_000


# --------------------------------------------------------------------------
# authority binding
# --------------------------------------------------------------------------

def test_screen_binds_released_authority_geometry(screen, authority) -> None:
    assert screen.minimum_area_mm2 == authority.number(
        "safety", "airway", "minimum_area_each_mm2"
    )
    assert screen.no_collapse_flow_lpm == authority.number(
        "safety", "airway", "no_collapse_test_flow_lpm"
    )
    assert {p.flow_lpm for p in screen.requirement_points} == {30.0, 60.0}


def test_released_requirement_points_imply_one_loss_coefficient(screen) -> None:
    """A fixed aperture has one K. Two limits must not demand two.

    30 L/min at 10 Pa and 60 L/min at 40 Pa are exactly consistent: the flow
    doubles, the limit quadruples, and the implied coefficient is unchanged.
    """

    budgets = [p.allowable_loss_coefficient for p in screen.requirement_points]
    assert screen.requirement_points_are_mutually_consistent
    assert all(math.isclose(b, budgets[0], rel_tol=1e-9) for b in budgets)
    assert math.isclose(screen.implied_loss_coefficient_budget, 3.891892, rel_tol=1e-5)


def test_every_catalogued_edge_treatment_fits_the_budget(screen) -> None:
    for treatment in screen.edge_treatments:
        assert treatment.meets_requirement, (
            f"{treatment.treatment} needs K={treatment.loss_coefficient_high} but the "
            f"budget is {screen.implied_loss_coefficient_budget:.3f}"
        )


def test_sharp_edges_consume_most_of_the_budget(screen) -> None:
    """The actionable result: edge treatment dominates the available margin."""

    by_name = {t.treatment: t for t in screen.edge_treatments}
    sharp, radiused = by_name["sharp"], by_name["radiused"]

    assert sharp.area_margin_fraction < radiused.area_margin_fraction
    # A square-edged aperture leaves well under half the closure margin of a
    # radiused one, so edge treatment is a real design decision here.
    assert sharp.area_margin_fraction < 0.20
    assert radiused.area_margin_fraction > 0.40
    assert screen.worst_case_budget_consumer().treatment == "sharp"


def test_no_collapse_load_is_derived_for_every_treatment(screen) -> None:
    """The frozen 120 L/min test implies a suction load on compliant structure."""

    loads = screen.no_collapse_suction_pa_by_treatment
    assert set(loads) == set(EDGE_TREATMENTS)
    assert all(value > 0 for value in loads.values())
    # Sharp edges roughly double the suction a radiused inlet imposes.
    assert loads["sharp"] > 2.0 * loads["radiused"]
    # Load rises as the square of flow relative to the 60 L/min requirement point.
    assert loads["sharp"] > added_pressure_drop_pa(60.0, screen.minimum_area_mm2, 2.90)


# --------------------------------------------------------------------------
# evidence firewall
# --------------------------------------------------------------------------

def test_screen_does_not_claim_measurement(screen) -> None:
    manifest = screen.manifest()
    assert manifest["evidence_status"] == EVIDENCE_STATUS
    assert "NOT_MEASURED" in manifest["evidence_status"]

    disclaimed = " ".join(manifest["not_evidence_of"]).lower()
    for topic in ("measured breathing resistance", "comfort", "deflection", "collapse"):
        assert topic in disclaimed


def test_manifest_states_the_fluid_properties_results_depend_on(screen) -> None:
    """Every number scales with density; a screen that hides it is not a screen."""

    air = screen.manifest()["air_reference"]
    assert air["density_kg_m3"] == AIR_DENSITY_KG_M3
    assert air["temperature_c"] == 25.0
    assert air["pressure_kpa"] == 101.325


def test_manifest_is_deterministic(authority) -> None:
    a = build_airway_resistance_screen(authority).manifest()
    b = build_airway_resistance_screen(authority).manifest()
    assert a == b


def test_manifest_flags_transitional_reynolds(screen) -> None:
    """The limitation must travel with the result, not just the docstring."""

    assert all(
        p.manifest()["reynolds_below_re_independent_floor"] is True
        for p in screen.requirement_points
    )


# --------------------------------------------------------------------------
# hostile inputs
# --------------------------------------------------------------------------

@pytest.mark.parametrize("bad", [0.0, -1.0, float("nan"), float("inf")])
def test_nonpositive_and_nonfinite_inputs_fail_closed(bad) -> None:
    with pytest.raises(AirwayResistanceError):
        path_velocity_m_s(bad, 120.0)
    with pytest.raises(AirwayResistanceError):
        path_velocity_m_s(30.0, bad)
    with pytest.raises(AirwayResistanceError):
        added_pressure_drop_pa(30.0, 120.0, bad)


def test_zero_parallel_paths_fails_closed() -> None:
    with pytest.raises(AirwayResistanceError):
        path_velocity_m_s(30.0, 120.0, paths=0)


def test_inconsistent_requirement_pair_is_detected(authority) -> None:
    """Relaxing one limit without the other makes the pair unsatisfiable.

    No single aperture can present two different loss coefficients, so this is
    a genuine requirement defect rather than a design difficulty.
    """

    data = copy.deepcopy(authority.data)
    data["safety"]["airway"]["max_added_pressure_drop_pa"]["at_60_lpm"] = 25.0
    mutated = Authority(data, authority.source, authority.validation_report)

    screen = build_airway_resistance_screen(mutated)
    assert not screen.requirement_points_are_mutually_consistent
    # The screen must bind to the tightest of the two, never the loosest.
    assert screen.implied_loss_coefficient_budget == min(
        p.allowable_loss_coefficient for p in screen.requirement_points
    )


def test_malformed_requirement_keys_fail_closed(authority) -> None:
    data = copy.deepcopy(authority.data)
    data["safety"]["airway"]["max_added_pressure_drop_pa"] = {"thirty": 10.0}
    mutated = Authority(data, authority.source, authority.validation_report)

    with pytest.raises(AirwayResistanceError, match="at_<flow>_lpm"):
        build_airway_resistance_screen(mutated)


def test_empty_requirement_set_fails_closed(authority) -> None:
    data = copy.deepcopy(authority.data)
    data["safety"]["airway"]["max_added_pressure_drop_pa"] = {}
    mutated = Authority(data, authority.source, authority.validation_report)

    with pytest.raises(AirwayResistanceError):
        build_airway_resistance_screen(mutated)


def test_shrinking_the_aperture_eventually_breaks_the_budget(authority) -> None:
    """Guard against a screen that passes for every conceivable geometry."""

    data = copy.deepcopy(authority.data)
    data["safety"]["airway"]["minimum_area_each_mm2"] = 40.0
    mutated = Authority(data, authority.source, authority.validation_report)

    screen = build_airway_resistance_screen(mutated)
    assert not all(t.meets_requirement for t in screen.edge_treatments)
    assert not screen.worst_case_budget_consumer().meets_requirement


def test_parallel_path_count_matches_nostril_count(authority) -> None:
    centers = authority.get("geometry", "nostrils", "centers_mm")
    assert PARALLEL_AIRWAY_PATHS == len(centers) == 2


# --------------------------------------------------------------------------
# authority-level gate
# --------------------------------------------------------------------------

def test_authority_rejects_a_physically_unsatisfiable_requirement_pair(authority) -> None:
    """The invariant is enforced before CAD generation, not only in the screen.

    limit / flow^2 must be constant. Density, aperture area and path count all
    cancel out of that condition, so it holds for any geometry whatsoever - a
    violation is a defective requirement, not a hard design problem.
    """

    from masck_one.authority import _semantic_issues

    assert not _semantic_issues(authority.data)

    data = copy.deepcopy(authority.data)
    data["safety"]["airway"]["max_added_pressure_drop_pa"]["at_60_lpm"] = 25.0
    codes = [issue.code for issue in _semantic_issues(data)]
    assert "AIRWAY_PRESSURE_DROP_REQUIREMENT_INCONSISTENT" in codes


def test_authority_accepts_a_consistently_rescaled_requirement_pair(authority) -> None:
    """Tightening both limits together stays satisfiable and must be allowed."""

    from masck_one.authority import _semantic_issues

    data = copy.deepcopy(authority.data)
    data["safety"]["airway"]["max_added_pressure_drop_pa"] = {
        "at_30_lpm": 5.0,
        "at_60_lpm": 20.0,
    }
    codes = [issue.code for issue in _semantic_issues(data)]
    assert "AIRWAY_PRESSURE_DROP_REQUIREMENT_INCONSISTENT" not in codes


def test_screen_and_authority_gate_agree(authority) -> None:
    """Two implementations of one invariant must not diverge."""

    from masck_one.authority import Authority as _Authority, _semantic_issues

    for limit, expected_consistent in ((40.0, True), (25.0, False)):
        data = copy.deepcopy(authority.data)
        data["safety"]["airway"]["max_added_pressure_drop_pa"]["at_60_lpm"] = limit
        screen = build_airway_resistance_screen(
            _Authority(data, authority.source, authority.validation_report)
        )
        flagged = any(
            issue.code == "AIRWAY_PRESSURE_DROP_REQUIREMENT_INCONSISTENT"
            for issue in _semantic_issues(data)
        )
        assert screen.requirement_points_are_mutually_consistent is expected_consistent
        assert flagged is (not expected_consistent)
