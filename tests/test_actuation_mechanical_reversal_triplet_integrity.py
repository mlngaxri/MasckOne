import pytest

from masck_one.actuation_mechanical_reversal import (
    ZoneMechanicalSlopeReversal,
    _validate_complete_four_zone_triplets,
)
from masck_one.actuation_parameters import ActuationParameterError


def _item(zone_id: str, lower: float, center: float, upper: float) -> ZoneMechanicalSlopeReversal:
    return ZoneMechanicalSlopeReversal(
        zone_id, lower, center, upper,
        f"{zone_id}-{lower}", f"{zone_id}-{center}", f"{zone_id}-{upper}",
        False, False, False, False,
        "NONE", "NONE", "NONE", "NONE",
    )


def test_triplet_validator_requires_four_unique_zones_per_physical_triplet():
    # Total cardinality is deliberately valid (8 records, four zone IDs globally),
    # but each physical triplet contains a duplicate and is missing one zone.
    malformed = (
        _item("Z1", 55.0, 61.0, 67.0),
        _item("Z1", 55.0, 61.0, 67.0),
        _item("Z2", 55.0, 61.0, 67.0),
        _item("Z3", 55.0, 61.0, 67.0),
        _item("Z1", 61.0, 67.0, 73.0),
        _item("Z2", 61.0, 67.0, 73.0),
        _item("Z3", 61.0, 67.0, 73.0),
        _item("Z4", 61.0, 67.0, 73.0),
    )
    with pytest.raises(ActuationParameterError, match="exactly four unique controlled zones"):
        _validate_complete_four_zone_triplets(malformed)


def test_triplet_validator_accepts_complete_unique_four_zone_matrix():
    valid = tuple(
        _item(zone_id, lower, center, upper)
        for lower, center, upper in ((55.0, 61.0, 67.0), (61.0, 67.0, 73.0))
        for zone_id in ("Z1", "Z2", "Z3", "Z4")
    )
    assert _validate_complete_four_zone_triplets(valid) == (
        (55.0, 61.0, 67.0),
        (61.0, 67.0, 73.0),
    )
