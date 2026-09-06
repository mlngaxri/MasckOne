from __future__ import annotations

from functools import lru_cache

import pytest

from masck_one.legacy_actuator_donor_audit import build_legacy_actuator_donor_audit
from masck_one.model import build_model


@lru_cache(maxsize=1)
def _audit():
    return build_legacy_actuator_donor_audit(model=build_model())


def _row(audit, zone_id: str, angle_deg: float, target_suffix: str):
    return next(
        record
        for record in audit.angle_doe_records
        if record.zone_id == zone_id
        and record.angle_deg == angle_deg
        and record.target_id.endswith(target_suffix)
    )


def test_legacy_pr63_actuator_donor_overlap_volumes_remain_deterministic():
    audit = _audit()
    zone = "ACTUATOR_ZONE_SUPERIOR_LEFT"

    assert _row(audit, zone, 61.0, "_MOUNT_COLLAR").intersection_volume_mm3 == 0.0
    assert _row(audit, zone, 61.0, "_REACTION_SHOE").intersection_volume_mm3 == pytest.approx(
        21.99345324, abs=2e-5
    )
    assert _row(audit, zone, 61.0, "FRAME_PERIMETER_REACTION_MEMBER").intersection_volume_mm3 == pytest.approx(
        2.66493183, abs=2e-5
    )
    assert _row(audit, zone, 72.0, "_MOUNT_COLLAR").intersection_volume_mm3 == pytest.approx(
        9.14036228, abs=2e-5
    )
    assert _row(audit, zone, 72.0, "_REACTION_SHOE").intersection_volume_mm3 == pytest.approx(
        43.62846500, abs=2e-5
    )
    assert _row(audit, zone, 72.0, "FRAME_PERIMETER_REACTION_MEMBER").intersection_volume_mm3 == pytest.approx(
        8.18520159, abs=2e-5
    )

    collar_shoe = next(
        record
        for record in audit.static_overlap_records
        if record.zone_id == zone and record.record_id.endswith("COLLAR_TO_SHOE")
    )
    shoe_frame = next(
        record
        for record in audit.static_overlap_records
        if record.zone_id == zone and record.record_id.endswith("SHOE_TO_FRAME")
    )
    assert collar_shoe.intersection_volume_mm3 == pytest.approx(35.88929895, abs=2e-5)
    assert shoe_frame.intersection_volume_mm3 == pytest.approx(127.34208317, abs=3e-5)


def test_legacy_shoe_and_frame_penetration_grows_across_superior_left_doe():
    audit = _audit()
    zone = "ACTUATOR_ZONE_SUPERIOR_LEFT"

    shoe = [
        _row(audit, zone, angle, "_REACTION_SHOE").intersection_volume_mm3
        for angle in audit.angle_doe_deg
    ]
    frame = [
        _row(audit, zone, angle, "FRAME_PERIMETER_REACTION_MEMBER").intersection_volume_mm3
        for angle in audit.angle_doe_deg
    ]
    assert shoe == sorted(shoe)
    assert frame == sorted(frame)
    assert shoe[0] > 0.0
    assert frame[0] > 0.0
