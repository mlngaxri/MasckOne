"""Shared numeric-guard primitives.

Every module in this repository validates its own inputs, which is right — a
silent NaN or a negative area is how a screen ends up reporting a confident
wrong answer. What is not right is that each module grew its own copy of the
same three guards. Across `src/masck_one/` there are 13 definitions of `_text`,
11 of `_sha`, and a dozen more of `_finite` / `_real` / `_exact`, plus 45
bespoke error classes and no shared module.

That duplication has a real cost. It is not only more code to read: the copies
drift. One rejects `bool`, another does not. One treats zero as valid, another
does not. A caller cannot tell which behaviour it is getting without opening the
file.

This module is the shared target for new code. It is deliberately small — only
guards whose behaviour should genuinely be identical everywhere.

Each guard takes the error type to raise, so a module keeps its own exception
class and its own error vocabulary while sharing the checking logic. Callers see
`AirwayResistanceError` or `MassBalanceError` exactly as before.

Migration is incremental by design. This repository is edited concurrently by
several lanes with a large backlog of open pull requests, so rewriting twenty
existing modules at once would generate the maximum possible number of
conflicts for the minimum benefit. New modules use these; existing ones adopt
them when their owning lane next touches them.
"""

from __future__ import annotations

import math
from typing import TypeVar

_E = TypeVar("_E", bound=Exception)


def finite(value: object, label: str, error: type[Exception]) -> float:
    """Any finite real number.

    Rejects bool explicitly: `True` is an `int` in Python, and a boolean
    arriving where a measurement belongs is a caller bug, not a value of 1.
    """

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise error(f"{label} must be a real number, got {value!r}")
    result = float(value)
    if not math.isfinite(result):
        raise error(f"{label} must be finite, got {value!r}")
    return result


def positive(value: object, label: str, error: type[Exception]) -> float:
    """A finite number strictly greater than zero."""

    result = finite(value, label, error)
    if result <= 0.0:
        raise error(f"{label} must be positive, got {value!r}")
    return result


def non_negative(value: object, label: str, error: type[Exception]) -> float:
    """A finite number at or above zero."""

    result = finite(value, label, error)
    if result < 0.0:
        raise error(f"{label} must not be negative, got {value!r}")
    return result


def positive_int(value: object, label: str, error: type[Exception]) -> int:
    """A whole number of at least one. Rejects bool and float."""

    if isinstance(value, bool) or not isinstance(value, int):
        raise error(f"{label} must be an integer, got {value!r}")
    if value < 1:
        raise error(f"{label} must be at least 1, got {value!r}")
    return value


def non_empty_text(value: object, label: str, error: type[Exception]) -> str:
    """A string with at least one non-whitespace character."""

    if not isinstance(value, str):
        raise error(f"{label} must be text, got {value!r}")
    if not value.strip():
        raise error(f"{label} must not be empty")
    return value
