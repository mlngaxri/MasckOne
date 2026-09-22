from dataclasses import replace
import pytest
from masck_one import retention_quick_release_tactile_v30 as v30


def test_v30_builds_and_binds_all_clearance_corners():
    audit = v30.build_retention_quick_release_tactile_v30()
    manifest = audit.manifest()["clearance_authority_corner_screen"]
    assert manifest["corner_count"] == 4
    assert audit.pose_count == audit.transverse_sample_count * len(v30.v12._canonical_positions())
    assert audit.max_rigid_guide_intersection_mm3 == 0.0
    assert len(audit.evidence_sha256) == 64
    assert manifest["criterion"] == "NO_POSITIVE_RAW_KERNEL_RIGID_GUIDE_INTERSECTION_AT_ANY_NOMINAL_MAX_CLEARANCE_AUTHORITY_CORNER"


def test_v30_rejects_stale_pose_count():
    audit = v30.build_retention_quick_release_tactile_v30()
    with pytest.raises(v30.RetentionQuickReleaseTactileV30Error):
        replace(audit, pose_count=audit.pose_count + 1).validate()


def test_v30_rejects_stale_digest():
    audit = v30.build_retention_quick_release_tactile_v30()
    with pytest.raises(v30.RetentionQuickReleaseTactileV30Error):
        replace(audit, evidence_sha256="0" * 64).validate()


def test_v30_rejects_positive_bound_intersection():
    audit = v30.build_retention_quick_release_tactile_v30()
    with pytest.raises(v30.RetentionQuickReleaseTactileV30Error):
        replace(audit, max_rigid_guide_intersection_mm3=v30.v1.TOL_MM3 + 1e-9).validate()


def test_v30_rejects_sub_tolerance_positive_raw_kernel_intersection(monkeypatch):
    original = v30._raw_intersection
    injected = False

    def _sub_tolerance_overlap(a, b):
        nonlocal injected
        value = original(a, b)
        if not injected and value == 0.0:
            injected = True
            return v30.v1.TOL_MM3 / 2.0
        return value

    monkeypatch.setattr(v30, "_raw_intersection", _sub_tolerance_overlap)
    with pytest.raises(v30.RetentionQuickReleaseTactileV30Error, match="collides with rigid guide"):
        v30._corner_evidence()
    assert injected


def test_v30_raw_intersection_bypasses_v1_clamping_helper(monkeypatch):
    def _forbidden(*_args, **_kwargs):
        raise AssertionError("V30 must use raw kernel volume, not v1._intersection")

    monkeypatch.setattr(v30.v1, "_intersection", _forbidden)
    audit = v30.build_retention_quick_release_tactile_v30()
    assert audit.max_rigid_guide_intersection_mm3 == 0.0


def test_v30_raw_intersection_rejects_invalid_operand_before_kernel_query():
    class InvalidShape:
        def isValid(self):
            return False
        def Solids(self):
            return []
        def Volume(self):
            return 0.0
        def intersect(self, _other):
            raise AssertionError("invalid operand must fail before intersection")

    class InvalidWorkplane:
        def val(self):
            return InvalidShape()

    with pytest.raises(v30.RetentionQuickReleaseTactileV30Error, match="invalid raw clearance-corner operand"):
        v30._raw_intersection(InvalidWorkplane(), InvalidWorkplane())


def test_v30_raw_intersection_rejects_multi_solid_operand_before_kernel_query():
    class MultiSolidShape:
        def isValid(self):
            return True
        def Solids(self):
            return [object(), object()]
        def Volume(self):
            return 1.0
        def intersect(self, _other):
            raise AssertionError("multi-solid operand must fail before intersection")

    class MultiSolidWorkplane:
        def val(self):
            return MultiSolidShape()

    with pytest.raises(v30.RetentionQuickReleaseTactileV30Error, match="invalid raw clearance-corner operand"):
        v30._raw_intersection(MultiSolidWorkplane(), MultiSolidWorkplane())


def test_v30_corner_authority_is_complete():
    mechanism = v30.v1.build_retention_quick_release_tactile()
    corners = v30._clearance_corners(mechanism)
    assert [name for name, _, _ in corners] == ["nominal_nominal", "nominal_max_side", "max_radial_nominal", "max_max"]
    assert len({(radial, side) for _, radial, side in corners}) == 4
