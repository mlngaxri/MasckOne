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


def test_triplet_validator_rejects_cross_zone_measurement_record_reuse():
    items = list(
        _item(zone_id, 55.0, 61.0, 67.0)
        for zone_id in ("Z1", "Z2", "Z3", "Z4")
    )
    z2 = items[1]
    items[1] = ZoneMechanicalSlopeReversal(
        z2.zone_id, z2.lower_angle_deg, z2.center_angle_deg, z2.upper_angle_deg,
        items[0].lower_record_id, z2.center_record_id, z2.upper_record_id,
        z2.force_reversal, z2.displacement_reversal, z2.phase_reversal, z2.temperature_reversal,
        z2.force_turning_point, z2.displacement_turning_point, z2.phase_turning_point, z2.temperature_turning_point,
    )
    with pytest.raises(ActuationParameterError, match="unique measured record provenance across zones"):
        _validate_complete_four_zone_triplets(tuple(items))


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
