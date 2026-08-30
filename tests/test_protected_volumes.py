from __future__ import annotations

import math

import pytest

from masck_one.anatomy import build_facial_reference
from masck_one.authority import load_authority
from masck_one.facial_surface import build_planar_development_surface
from masck_one.protected_volumes import (
    PlanarProtectedZone,
    ProtectedVolume,
    ProtectedVolumeError,
    build_protected_volumes,
)
from masck_one.spatial import Point2, Point3


def _set():
    authority = load_authority()
    reference = build_facial_reference(authority)
    surface = build_planar_development_surface(authority)
    return authority, build_protected_volumes(authority, reference, surface)


def test_all_five_authority_protected_targets_are_present():
    _, protected = _set()
    assert [volume.zone.zone_id for volume in protected.all] == [
        "MASCK_ONE-PROTECTED-EYE-LEFT",
        "MASCK_ONE-PROTECTED-EYE-RIGHT",
        "MASCK_ONE-PROTECTED-MOUTH",
        "MASCK_ONE-PROTECTED-NOSTRIL-LEFT",
        "MASCK_ONE-PROTECTED-NOSTRIL-RIGHT",
    ]


def test_eye_envelopes_use_exact_aperture_and_clearance_baselines():
    authority, protected = _set()
    eye_w, eye_h = authority.pair("geometry", "eye", "visual_aperture_wh_mm")
    clearance = authority.number("geometry", "eye", "rigid_dynamic_keepout_clearance_mm")

    for volume in (protected.eye_left, protected.eye_right):
        zone = volume.zone
        assert zone.aperture_width_mm == eye_w
        assert zone.aperture_height_mm == eye_h
        assert zone.required_rigid_clearance_mm == clearance
        assert zone.envelope_width_mm == pytest.approx(eye_w + 2 * clearance)
        assert zone.envelope_height_mm == pytest.approx(eye_h + 2 * clearance)
        assert volume.anatomical_validation_eligible is False


def test_eye_zones_are_sagittal_mirrors_in_neutral_baseline():
    _, protected = _set()
    left = protected.eye_left.zone
    right = protected.eye_right.zone

    assert left.center.mirrored_across_sagittal() == right.center
    assert left.aperture_width_mm == right.aperture_width_mm
    assert left.aperture_height_mm == right.aperture_height_mm
    assert left.required_rigid_clearance_mm == right.required_rigid_clearance_mm
    assert left.angle_deg == -right.angle_deg


def test_mouth_envelope_uses_exact_authority_clearance():
    authority, protected = _set()
    zone = protected.mouth.zone
    mouth_w, mouth_h = authority.pair("geometry", "mouth", "visual_aperture_wh_mm")
    clearance = authority.number("geometry", "mouth", "rigid_dynamic_keepout_clearance_mm")

    assert zone.center == Point2(0.0, -50.0)
    assert zone.envelope_width_mm == pytest.approx(mouth_w + 2 * clearance)
    assert zone.envelope_height_mm == pytest.approx(mouth_h + 2 * clearance)


def test_nostril_base_circle_meets_minimum_area_and_local_dimension_before_clearance():
    authority, protected = _set()
    min_area = authority.number("geometry", "nostrils", "minimum_deformed_area_each_mm2")
    min_dim = authority.number("geometry", "nostrils", "minimum_local_opening_dimension_mm")

    for volume in (protected.nostril_left, protected.nostril_right):
        zone = volume.zone
        assert zone.shape == "CIRCLE"
        assert zone.aperture_area_mm2 >= min_area - 1e-9
        assert zone.aperture_width_mm >= min_dim
        assert zone.required_rigid_clearance_mm == 7.5


def test_protected_footprints_contain_their_centers_and_exclude_far_points():
    _, protected = _set()
    for volume in protected.all:
        assert volume.zone.contains_xy(volume.zone.center)
        assert volume.contains_point(Point3(volume.zone.center.x, volume.zone.center.y, -1000.0))
        assert volume.contains_point(Point3(volume.zone.center.x, volume.zone.center.y, 1000.0))
        far = Point2(volume.zone.center.x + 200.0, volume.zone.center.y + 200.0)
        assert not volume.zone.contains_xy(far)


def test_z_policy_is_conservative_and_explicitly_unresolved():
    _, protected = _set()
    assert all(volume.z_policy == "UNBOUNDED_UNTIL_REGISTERED_ANATOMICAL_SURFACE" for volume in protected.all)
    assert "3D_DYNAMIC_GEOMETRY_BLOCKED" in protected.evidence_status


def test_manifest_retains_authority_and_evidence_status():
    _, protected = _set()
    manifest = protected.manifest()

    assert manifest["source_surface_id"] == "MASCK_ONE-FACE-SURFACE-PLANAR-DEV-V1"
    assert len(manifest["zones"]) == 5
    assert all(zone["anatomical_validation_eligible"] is False for zone in manifest["zones"])
    assert all(zone["required_rigid_clearance_mm"] > 0.0 for zone in manifest["zones"])


def test_circle_dimension_mismatch_is_rejected():
    with pytest.raises(ProtectedVolumeError, match="equal aperture"):
        PlanarProtectedZone(
            zone_id="BAD",
            anatomical_target="bad",
            shape="CIRCLE",
            center=Point2(0.0, 0.0),
            aperture_width_mm=10.0,
            aperture_height_mm=11.0,
            required_rigid_clearance_mm=1.0,
            angle_deg=0.0,
            authority_status="TEST",
            evidence_status="TEST",
            source_path="test",
        )


def test_negative_clearance_is_rejected():
    with pytest.raises(ProtectedVolumeError, match="cannot be negative"):
        PlanarProtectedZone(
            zone_id="BAD",
            anatomical_target="bad",
            shape="ELLIPSE",
            center=Point2(0.0, 0.0),
            aperture_width_mm=10.0,
            aperture_height_mm=5.0,
            required_rigid_clearance_mm=-1.0,
            angle_deg=0.0,
            authority_status="TEST",
            evidence_status="TEST",
            source_path="test",
        )


def test_analytical_protected_volume_cannot_be_promoted_to_anatomical_evidence():
    zone = PlanarProtectedZone(
        zone_id="TEST",
        anatomical_target="test",
        shape="ELLIPSE",
        center=Point2(0.0, 0.0),
        aperture_width_mm=10.0,
        aperture_height_mm=5.0,
        required_rigid_clearance_mm=1.0,
        angle_deg=0.0,
        authority_status="TEST",
        evidence_status="TEST",
        source_path="test",
    )
    with pytest.raises(ProtectedVolumeError, match="cannot be promoted"):
        ProtectedVolume(zone, anatomical_validation_eligible=True)
