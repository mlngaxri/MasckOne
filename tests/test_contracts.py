"""The shared numeric guards.

These exist because the same three checks had grown a dozen slightly different
copies across src/masck_one/. The copies drifted: some rejected bool, some did
not; some treated zero as valid, some did not. A caller could not tell which
behaviour it was getting without opening the file.

So the behaviour is pinned here, once.
"""

from __future__ import annotations

import math

import pytest

from masck_one import _contracts


class _Err(ValueError):
    pass


# --------------------------------------------------------------------------
# finite
# --------------------------------------------------------------------------

@pytest.mark.parametrize("value", [0, 1, -1, 0.5, -2.5, 1e300])
def test_finite_accepts_real_numbers(value) -> None:
    assert _contracts.finite(value, "x", _Err) == float(value)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_finite_rejects_nonfinite(value) -> None:
    with pytest.raises(_Err, match="must be finite"):
        _contracts.finite(value, "x", _Err)


@pytest.mark.parametrize("value", [True, False])
def test_finite_rejects_bool(value) -> None:
    """True is an int in Python. A boolean where a measurement belongs is a bug.

    This was the drift: some copies accepted True as 1.0 and silently produced a
    plausible-looking number from a caller mistake.
    """

    with pytest.raises(_Err, match="must be a real number"):
        _contracts.finite(value, "x", _Err)


@pytest.mark.parametrize("value", ["1.0", None, [1.0], {"v": 1}])
def test_finite_rejects_non_numbers(value) -> None:
    with pytest.raises(_Err, match="must be a real number"):
        _contracts.finite(value, "x", _Err)


# --------------------------------------------------------------------------
# positive / non_negative — the boundary that drifted
# --------------------------------------------------------------------------

def test_positive_excludes_zero() -> None:
    assert _contracts.positive(1e-12, "x", _Err) == 1e-12
    with pytest.raises(_Err, match="must be positive"):
        _contracts.positive(0.0, "x", _Err)


def test_non_negative_includes_zero() -> None:
    assert _contracts.non_negative(0.0, "x", _Err) == 0.0
    with pytest.raises(_Err, match="must not be negative"):
        _contracts.non_negative(-1e-12, "x", _Err)


def test_positive_and_non_negative_reject_nonfinite() -> None:
    for guard in (_contracts.positive, _contracts.non_negative):
        with pytest.raises(_Err):
            guard(float("nan"), "x", _Err)


# --------------------------------------------------------------------------
# positive_int
# --------------------------------------------------------------------------

def test_positive_int_accepts_whole_numbers_from_one() -> None:
    assert _contracts.positive_int(1, "n", _Err) == 1
    assert _contracts.positive_int(99, "n", _Err) == 99


@pytest.mark.parametrize("value", [0, -1])
def test_positive_int_rejects_below_one(value) -> None:
    with pytest.raises(_Err, match="at least 1"):
        _contracts.positive_int(value, "n", _Err)


@pytest.mark.parametrize("value", [1.0, "1", True, None])
def test_positive_int_rejects_non_integers(value) -> None:
    with pytest.raises(_Err, match="must be an integer"):
        _contracts.positive_int(value, "n", _Err)


# --------------------------------------------------------------------------
# non_empty_text
# --------------------------------------------------------------------------

def test_non_empty_text_accepts_real_strings() -> None:
    assert _contracts.non_empty_text("frame", "id", _Err) == "frame"


@pytest.mark.parametrize("value", ["", "   ", "\n\t"])
def test_non_empty_text_rejects_blank(value) -> None:
    with pytest.raises(_Err, match="must not be empty"):
        _contracts.non_empty_text(value, "id", _Err)


@pytest.mark.parametrize("value", [None, 1, ["a"]])
def test_non_empty_text_rejects_non_strings(value) -> None:
    with pytest.raises(_Err, match="must be text"):
        _contracts.non_empty_text(value, "id", _Err)


# --------------------------------------------------------------------------
# each module keeps its own error vocabulary
# --------------------------------------------------------------------------

def test_guards_raise_the_callers_error_type() -> None:
    """Sharing the check must not flatten every module into one exception."""

    from masck_one.airway_resistance import AirwayResistanceError, path_velocity_m_s
    from masck_one.mass_balance import MassBalanceError, pitch_torque_nm
    from masck_one.process_capability import (
        ProcessCapabilityError,
        required_per_contributor_mm,
    )

    with pytest.raises(AirwayResistanceError):
        path_velocity_m_s(-1.0, 120.0)
    with pytest.raises(MassBalanceError):
        pitch_torque_nm(-1.0, 10.0)
    with pytest.raises(ProcessCapabilityError):
        required_per_contributor_mm(-1.0, 3)


def test_adopting_modules_no_longer_define_their_own_copies() -> None:
    """Guard against the duplication growing back in the modules that migrated."""

    from pathlib import Path

    src = Path(__file__).resolve().parents[1] / "src" / "masck_one"
    for name in (
        "airway_resistance.py",
        "mass_balance.py",
        "process_capability.py",
        "moldability.py",
    ):
        text = (src / name).read_text(encoding="utf-8")
        assert "_contracts" in text, f"{name} stopped using the shared guards"
        assert "math.isfinite(result)" not in text, (
            f"{name} reintroduced a local finiteness check"
        )
