from __future__ import annotations

"""Independent arithmetic guard for the Cell 18 quantitative release ledger."""

import math

from .quantitative_ledger import (
    EXPECTED_KNOWN_BENCHMARK_SUBTOTAL_G,
    STANDARD_GRAVITY_M_S2,
    CurrentQuantitativeLedger,
    MassLedger,
    QuantitativeLedgerError,
)


_ARITHMETIC_ABS_TOL = 1e-12


def _close(actual: float, expected: float) -> bool:
    return math.isclose(float(actual), float(expected), rel_tol=0.0, abs_tol=_ARITHMETIC_ABS_TOL)


def validate_mass_arithmetic(mass: MassLedger) -> None:
    """Reject a finite but internally inconsistent known-subset mass/CG/pitch record."""
    if type(mass) is not MassLedger:
        raise QuantitativeLedgerError("mass arithmetic guard requires exact MassLedger type")
    mass.__post_init__()

    counted = tuple(entry for entry in mass.entries if entry.counted_in_known_subtotal)
    if not counted:
        raise QuantitativeLedgerError("mass arithmetic guard requires known benchmark contributors")

    subtotal = sum(float(entry.mass_g) for entry in counted)
    if not _close(subtotal, EXPECTED_KNOWN_BENCHMARK_SUBTOTAL_G):
        raise QuantitativeLedgerError("mass arithmetic guard known subtotal moved")
    if not _close(mass.known_mass_subtotal_g, subtotal):
        raise QuantitativeLedgerError("mass arithmetic guard subtotal mismatch")

    expected_cg = tuple(
        sum(float(entry.mass_g) * float(entry.centroid_xyz_mm[axis]) for entry in counted) / subtotal
        for axis in range(3)
    )
    if any(
        not _close(actual, expected)
        for actual, expected in zip(mass.known_subset_cg_xyz_mm, expected_cg, strict=True)
    ):
        raise QuantitativeLedgerError("mass arithmetic guard known-subset CG mismatch")

    expected_pitch = subtotal / 1000.0 * STANDARD_GRAVITY_M_S2 * abs(expected_cg[2]) / 1000.0
    if not _close(mass.known_subset_pitch_moment_Nm, expected_pitch):
        raise QuantitativeLedgerError("mass arithmetic guard known-subset pitch mismatch")

    grouped = (
        (
            "FOUR_ACTUATOR_SIBLING_MODEL_MASS_BENCHMARKS",
            sum(float(entry.mass_g) for entry in counted if entry.component_id.startswith("ACTUATOR-ZONE-")),
        ),
        (
            "BATTERY_REFERENCE_BENCHMARK",
            sum(float(entry.mass_g) for entry in counted if entry.component_id.startswith("BATTERY-")),
        ),
    )
    expected_contributors = tuple((identifier, value, value / subtotal) for identifier, value in grouped if value > 0.0)
    actual_contributors = tuple(
        (item.contributor_id, float(item.known_mass_g), float(item.fraction_of_known_subtotal))
        for item in mass.dominant_known_contributors
    )
    if len(actual_contributors) != len(expected_contributors):
        raise QuantitativeLedgerError("mass arithmetic guard dominant-contributor cardinality mismatch")
    for actual, expected in zip(actual_contributors, expected_contributors, strict=True):
        if actual[0] != expected[0] or not _close(actual[1], expected[1]) or not _close(actual[2], expected[2]):
            raise QuantitativeLedgerError("mass arithmetic guard dominant-contributor mismatch")


def validate_quantitative_ledger_arithmetic(ledger: CurrentQuantitativeLedger) -> None:
    if type(ledger) is not CurrentQuantitativeLedger:
        raise QuantitativeLedgerError("quantitative arithmetic guard requires exact CurrentQuantitativeLedger type")
    ledger.__post_init__()
    validate_mass_arithmetic(ledger.mass)
