from dataclasses import replace
import pytest
from masck_one import retention_quick_release_tactile_v42 as v42


def test_v42_builds_and_binds_declared_rectangle() -> None:
    audit = v42.build_retention_quick_release_tactile_v42()
    manifest = audit.manifest()["declared_clearance_tolerance_rectangle"]
    assert manifest["corner_count"] == 4
    assert audit.radial_maximum_mm > audit.radial_nominal_mm
    assert audit.side_maximum_mm > audit.side_nominal_mm
    assert len(audit.tolerance_rectangle_sha256) == 64
    assert v42._bound_rectangle(audit.prior) == v42._declared_rectangle()


def test_v42_rejects_stale_bound() -> None:
    audit = v42.build_retention_quick_release_tactile_v42()
    with pytest.raises(v42.RetentionQuickReleaseTactileV42Error):
        replace(audit, radial_maximum_mm=audit.radial_maximum_mm + 0.001).validate()


def test_v42_rejects_stale_digest() -> None:
    audit = v42.build_retention_quick_release_tactile_v42()
    with pytest.raises(v42.RetentionQuickReleaseTactileV42Error):
        replace(audit, tolerance_rectangle_sha256="0" * 64).validate()
