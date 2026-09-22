import pytest

from masck_one.actuation_mechanical_curvature import (
    ZoneMechanicalCurvature,
    _angle_triplet_extrema,
)
from masck_one.actuation_parameters import ActuationParameterError


def _item(zone_id: str, scale: float) -> ZoneMechanicalCurvature:
    return ZoneMechanicalCurvature(
        zone_id=zone_id,
        lower_angle_deg=57.0,
        center_angle_deg=61.0,
        upper_angle_deg=65.0,
        lower_record_id=f"{zone_id}-57",
        center_record_id=f"{zone_id}-61",
        upper_record_id=f"{zone_id}-65",
        interval_center_delta_deg=4.0,
        force_slope_change_N_per_deg=0.01 * scale,
        force_curvature_N_per_deg2=0.0025 * scale,
        displacement_slope_change_mm_per_deg=0.002 * scale,
        displacement_curvature_mm_per_deg2=0.0005 * scale,
        phase_slope_change_deg_per_deg=0.4 * scale,
        phase_curvature_deg_per_deg2=0.1 * scale,
        temperature_slope_change_C_per_deg=0.08 * scale,
        temperature_curvature_C_per_deg2=0.02 * scale,
    )


def test_angle_triplet_extrema_retain_worst_zone_and_three_record_provenance():
    items = tuple(_item(f"ZONE_{index}", float(index)) for index in range(1, 5))
    result = _angle_triplet_extrema(items)
    assert len(result) == 1
    triplet = result[0]
    assert (triplet.lower_angle_deg, triplet.center_angle_deg, triplet.upper_angle_deg) == (57.0, 61.0, 65.0)
    assert triplet.zone_count == 4
    for worst in (
        triplet.maximum_abs_force_curvature,
        triplet.maximum_abs_displacement_curvature,
        triplet.maximum_abs_phase_curvature,
        triplet.maximum_abs_temperature_curvature,
    ):
        assert worst.zone_id == "ZONE_4"
        assert (worst.lower_record_id, worst.center_record_id, worst.upper_record_id) == (
            "ZONE_4-57", "ZONE_4-61", "ZONE_4-65"
        )


def test_angle_triplet_extrema_are_order_independent():
    items = tuple(_item(f"ZONE_{index}", float(index)) for index in range(1, 5))
    assert _angle_triplet_extrema(items) == _angle_triplet_extrema(tuple(reversed(items)))


def test_angle_triplet_extrema_fail_closed_when_a_controlled_zone_is_missing():
    items = tuple(_item(f"ZONE_{index}", float(index)) for index in range(1, 4))
    with pytest.raises(ActuationParameterError, match="exactly four controlled zones"):
        _angle_triplet_extrema(items)
