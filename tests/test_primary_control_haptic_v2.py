from __future__ import annotations

import pytest

from masck_one.primary_control_haptic import (
    PrimaryControlHapticError,
)
from masck_one.primary_control_haptic_v2 import (
    build_primary_control_haptic_architecture_v2,
)
from masck_one.primary_control_haptic_v3 import (
    DONOR_V2_HEAD_SHA,
    build_primary_control_haptic_architecture_v3,
)


def test_historical_v2_is_rejected_for_zero_volume_moving_part_joints():
    """The donor is evidence, not a promotable current candidate.

    Its cap-to-stem and stem-to-rib interfaces are boundary-only contacts. Keeping
    this failure explicit prevents a future refactor from silently promoting the
    historical multi-solid moving part again.
    """
    with pytest.raises(PrimaryControlHapticError, match="cap/stem must be one connected manufactured part"):
        build_primary_control_haptic_architecture_v2()


def test_v3_explicitly_supersedes_the_rejected_v2_donor():
    architecture = build_primary_control_haptic_architecture_v3()
    manifest = architecture.manifest()

    assert DONOR_V2_HEAD_SHA == "5c2b5f030f8d205e108a828fed53d43293f518f4"
    assert manifest["donor_v2_head_sha"] == DONOR_V2_HEAD_SHA
    assert manifest["supersedes"] == "V2_ZERO_VOLUME_CAP_STEM_AND_STEM_RIB_JOINTS"
    assert len(dict(architecture.material_parts)["primary_control_cap_stem"].Solids()) == 1
