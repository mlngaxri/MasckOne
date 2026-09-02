import math

import pytest

from engineering.cell3.retention_cad import MEMBER_ENDPOINTS, build_retention_cad
from engineering.cell3.retention_package_contract import RetentionDatums


def _datums() -> RetentionDatums:
    return RetentionDatums(
        left_yoke=(-82.0, 8.0, 4.0),
        right_yoke=(82.0, 8.0, 4.0),
        left_junction=(-74.0, 18.0, -42.0),
        right_junction=(74.0, 18.0, -42.0),
        crown_apex=(0.0, 104.0, -28.0),
        occipital_center=(0.0, -50.0, -72.0),
    )


def _radii(radius: float = 2.0) -> dict[str, float]:
    return {name: radius for name in MEMBER_ENDPOINTS}


def test_builds_six_physical_structural_members() -> None:
    assembly = build_retention_cad(_datums(), _radii())
    assert len(assembly.members) == 6
    assert assembly.compound.Volume() > 0.0
    assert {member.name for member in assembly.members} == set(MEMBER_ENDPOINTS)
    assert all(member.solid.Volume() > 0.0 for member in assembly.members)


def test_member_length_matches_released_datums() -> None:
    assembly = build_retention_cad(_datums(), _radii())
    left = next(member for member in assembly.members if member.name == "left_yoke_link")
    expected = math.sqrt(8.0**2 + 10.0**2 + 46.0**2)
    assert left.length_mm == pytest.approx(expected)


def test_manifest_preserves_geometry_without_claiming_validation() -> None:
    manifest = build_retention_cad(_datums(), _radii(1.75)).manifest()
    assert manifest["status"] == "CONTROLLED_CAD_GEOMETRY_NOT_PHYSICAL_VALIDATION"
    assert manifest["member_count"] == 6
    assert all(row["radius_mm"] == pytest.approx(1.75) for row in manifest["members"])
    assert "no anthropometric or comfort inference" in manifest["limitations"]


def test_rejects_incomplete_or_extra_geometry_contract() -> None:
    radii = _radii()
    radii.pop("crown_left")
    with pytest.raises(ValueError, match="missing"):
        build_retention_cad(_datums(), radii)

    radii = _radii()
    radii["decorative_strap"] = 1.0
    with pytest.raises(ValueError, match="unexpected"):
        build_retention_cad(_datums(), radii)


def test_rejects_bad_radii_and_bad_datums() -> None:
    for bad in (float("nan"), float("inf"), 0.0, -1.0, True):
        radii = _radii()
        radii["occipital_left"] = bad
        with pytest.raises(ValueError, match="radius"):
            build_retention_cad(_datums(), radii)

    malformed = RetentionDatums(
        left_yoke=(float("nan"), 8.0, 4.0),
        right_yoke=(82.0, 8.0, 4.0),
        left_junction=(-74.0, 18.0, -42.0),
        right_junction=(74.0, 18.0, -42.0),
        crown_apex=(0.0, 104.0, -28.0),
        occipital_center=(0.0, -50.0, -72.0),
    )
    with pytest.raises(ValueError, match="finite numeric xyz"):
        build_retention_cad(malformed, _radii())
