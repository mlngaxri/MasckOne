import math
from itertools import product
from dataclasses import replace

import pytest

from masck_one.interaction_metrology import Sample, Trace, analyse


def linear_trace():
    return Trace(tuple(Sample(x, 2 * x) for x in (0, .5, 1)),
                 tuple(Sample(x, x) for x in (1, .5, 0)),
                 "synthetic", "analytic linear functions", "off-face primary-control measurement pipeline")


def test_analytic_work_and_signed_loop():
    r = analyse(linear_trace())
    assert r["loading_work"]["nominal_mJ"] == 1
    assert r["unloading_work"]["nominal_mJ"] == .5
    assert r["signed_hysteresis_mJ"] == .5
    assert r["signed_hysteresis_sample_bounds_mJ"] == [.5, .5]
    assert all(w["linear_residual_rms_N"] == 0 for w in r["loading_windows"])
    t = linear_trace()
    inverted = replace(t, loading=tuple(reversed(t.unloading)), unloading=tuple(reversed(t.loading)))
    assert analyse(inverted)["signed_hysteresis_mJ"] == -.5


def test_sample_uncertainty_encloses_extreme_trapezoids():
    t = Trace(tuple(Sample(x, 2, .01, .1) for x in (0, .5, 1)),
              tuple(Sample(x, 1, .01, .1) for x in (1, .5, 0)),
              "measured", "example instrument export (test fixture only)", "coupon")
    r = analyse(t)
    assert r["loading_work"]["sample_bound_lower_mJ"] == pytest.approx(2 * .48 * 1.9)
    assert r["loading_work"]["sample_bound_upper_mJ"] == pytest.approx(2 * .52 * 2.1)
    lo, hi = r["signed_hysteresis_sample_bounds_mJ"]
    assert lo < 1 < hi
    assert r["provenance"] == "measured"
    assert r["physical_validation"] == "not_established_by_this_analysis"


def test_uneven_sampling_linear_fit_and_local_ripple():
    t = linear_trace()
    clean = tuple(Sample(x, 2 * x + .1) for x in (0, .01, .2, .7, 1))
    r = analyse(replace(t, loading=clean))
    assert max(w["linear_residual_rms_N"] for w in r["loading_windows"]) < 1e-14
    ripple = list(clean)
    ripple[2] = replace(ripple[2], compression_N=ripple[2].compression_N + .3)
    r = analyse(replace(t, loading=tuple(ripple)))
    assert max(w["linear_residual_rms_N"] for w in r["loading_windows"]) > .01


@pytest.mark.parametrize("bad", [math.nan, math.inf, -1, True])
def test_invalid_sample_rejected(bad):
    t = linear_trace()
    with pytest.raises(ValueError):
        analyse(replace(t, loading=(Sample(0, 0), Sample(.5, bad), Sample(1, 2))))


@pytest.mark.parametrize("change", [
    {"provenance": "estimated"}, {"source": " "}, {"interaction": ""},
    {"loading": (Sample(0, 0), Sample(.5, 1), Sample(.5, 2))},
    {"unloading": (Sample(1, 1), Sample(.6, .6), Sample(.1, .1))},
    {"unloading": (Sample(0, 0), Sample(.5, 1), Sample(1, 2))},
])
def test_contract_rejects_ambiguous_traces(change):
    with pytest.raises(ValueError):
        analyse(replace(linear_trace(), **change))


@pytest.mark.parametrize("width", [2, 4, True, 3.0])
def test_invalid_window(width):
    with pytest.raises(ValueError):
        analyse(linear_trace(), roughness_window_samples=width)


def test_interval_work_encloses_all_sample_error_corners():
    t = linear_trace()
    samples = tuple(Sample(x, f, .01, .2) for x, f in ((0, .1), (.3, 1), (1, 2)))
    r = analyse(replace(t, loading=samples))["loading_work"]
    for signs in product((-1, 1), repeat=6):
        xs = [s.displacement_mm + signs[2*i] * s.displacement_bound_mm for i, s in enumerate(samples)]
        fs = [max(0, s.compression_N + signs[2*i+1] * s.force_bound_N) for i, s in enumerate(samples)]
        actual = sum((b-a) * (f+g) / 2 for a, b, f, g in zip(xs, xs[1:], fs, fs[1:]))
        assert r["sample_bound_lower_mJ"] <= actual <= r["sample_bound_upper_mJ"]


def test_synthetic_comparison_never_claims_physical_evidence():
    # Import by file path: studies are standalone scripts, not an installed API.
    import runpy
    from pathlib import Path
    comparison = runpy.run_path(str(Path(__file__).parents[1] / "studies" / "interaction_metrology_comparison.py"))["comparison"]()
    results = comparison["results"]
    clean = max(w["linear_residual_rms_N"] for w in results["linear_reference"]["loading_windows"])
    ripple = max(w["linear_residual_rms_N"] for w in results["added_sample_ripple"]["loading_windows"])
    assert clean < 1e-12 < ripple
    assert all(r["provenance"] == "synthetic" and r["physical_validation"] == "not_established_by_this_analysis" for r in results.values())
