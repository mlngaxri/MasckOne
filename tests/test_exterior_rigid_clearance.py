from dataclasses import replace

import cadquery as cq
import pytest

from masck_one.exterior_eye_roll import build_eye_rolled_exterior_shell
from masck_one.exterior_rigid_clearance import (
    EVIDENCE_STATUS,
    EXPECTED_ZONE_IDS,
    SCHEMA,
    WORLD_FRAME_ID,
    RigidProtectedClearanceError,
    rigid_clearance_manifest,
    rigid_clearance_openings,
)
from masck_one.exterior_surface import _ellipse_cutter
from masck_one.model import build_model
from masck_one.protected_volumes import ProtectedVolume


INTERSECTION_VOLUME_TOLERANCE_MM3 = 1e-7


@pytest.fixture(scope="module")
def clearance_context():
    model = build_model()
    shell = build_eye_rolled_exterior_shell(
        model.authority,
        model.facial_reference,
        model.protected_volumes,
    ).val()
    return model, shell


def test_clearance_manifest_consumes_exact_released_protected_set(clearance_context):
    model, _ = clearance_context
    manifest = rigid_clearance_manifest(model.authority, model.protected_volumes)
    protected_manifest = model.protected_volumes.manifest()

    assert manifest["schema"] == SCHEMA
    assert manifest["coordinate_frame"] == WORLD_FRAME_ID
    assert manifest["protected_source_surface_id"] == model.protected_volumes.source_surface_id
    assert manifest["protected_evidence_status"] == model.protected_volumes.evidence_status
    assert manifest["physical_validation_eligible"] is False
    assert manifest["evidence_status"] == EVIDENCE_STATUS
    assert tuple(item["zone_id"] for item in manifest["openings"]) == EXPECTED_ZONE_IDS
    assert [item["envelope_wh_mm"] for item in manifest["openings"]] == [
        zone["envelope_wh_mm"] for zone in protected_manifest["zones"]
    ]
    assert "NONRIGID_VISIBLE_INTERFACE_GEOMETRY_UNRESOLVED" in manifest["visual_aperture_policy"]


def test_final_rigid_brep_has_zero_material_inside_all_five_planar_hard_envelopes(clearance_context):
    model, shell = clearance_context
    assert shell.isValid()
    assert len(shell.Solids()) == 1

    for opening in rigid_clearance_openings(model.protected_volumes):
        width, height = opening.envelope_wh_mm
        x_mm, y_mm = opening.center_mm
        cutter = _ellipse_cutter(
            width,
            height,
            x_mm,
            y_mm,
            angle_deg=opening.angle_deg,
        ).val()
        overlap = shell.intersect(cutter)
        assert float(overlap.Volume()) == pytest.approx(
            0.0,
            abs=INTERSECTION_VOLUME_TOLERANCE_MM3,
        ), opening.zone_id


def test_eye_mouth_and_nostril_clearances_match_authority_arithmetic(clearance_context):
    model, _ = clearance_context
    authority = model.authority
    openings = {opening.zone_id: opening for opening in rigid_clearance_openings(model.protected_volumes)}

    eye_w, eye_h = authority.pair("geometry", "eye", "visual_aperture_wh_mm")
    eye_clearance = authority.number("geometry", "eye", "rigid_dynamic_keepout_clearance_mm")
    for zone_id in ("MASCK_ONE-PROTECTED-EYE-LEFT", "MASCK_ONE-PROTECTED-EYE-RIGHT"):
        assert openings[zone_id].envelope_wh_mm == (
            eye_w + 2.0 * eye_clearance,
            eye_h + 2.0 * eye_clearance,
        )

    mouth_w, mouth_h = authority.pair("geometry", "mouth", "visual_aperture_wh_mm")
    mouth_clearance = authority.number("geometry", "mouth", "rigid_dynamic_keepout_clearance_mm")
    assert openings["MASCK_ONE-PROTECTED-MOUTH"].envelope_wh_mm == (
        mouth_w + 2.0 * mouth_clearance,
        mouth_h + 2.0 * mouth_clearance,
    )

    nostril_clearance = authority.number("geometry", "nostrils", "rigid_dynamic_keepout_clearance_mm")
    for zone_id in ("MASCK_ONE-PROTECTED-NOSTRIL-LEFT", "MASCK_ONE-PROTECTED-NOSTRIL-RIGHT"):
        zone = model.protected_volumes.by_id(zone_id).zone
        assert openings[zone_id].envelope_wh_mm == (
            zone.aperture_width_mm + 2.0 * nostril_clearance,
            zone.aperture_height_mm + 2.0 * nostril_clearance,
        )


def test_protected_identity_order_and_evidence_spoofing_fail_closed(clearance_context):
    model, _ = clearance_context
    protected = model.protected_volumes

    spoofed_zone = replace(protected.eye_left.zone, zone_id="MASCK_ONE-PROTECTED-EYE-SPOOF")
    spoofed_volume = ProtectedVolume(spoofed_zone)
    spoofed_set = replace(protected, eye_left=spoofed_volume)
    with pytest.raises(RigidProtectedClearanceError, match="identity or order changed"):
        rigid_clearance_openings(spoofed_set)

    evidence_zone = replace(
        protected.eye_left.zone,
        evidence_status="PHYSICAL_VALIDATION",
    )
    evidence_set = replace(protected, eye_left=ProtectedVolume(evidence_zone))
    with pytest.raises(RigidProtectedClearanceError, match="evidence status drifted"):
        rigid_clearance_openings(evidence_set)

    with pytest.raises(RigidProtectedClearanceError, match="exact ProtectedVolumeSet"):
        rigid_clearance_openings(object())  # type: ignore[arg-type]


def test_protected_source_cannot_be_promoted_to_resolved_dynamic_or_anatomical_evidence(clearance_context):
    model, _ = clearance_context
    protected = model.protected_volumes

    with pytest.raises(RigidProtectedClearanceError, match="hard-envelope status"):
        rigid_clearance_openings(replace(protected, evidence_status="UNKNOWN"))
    with pytest.raises(RigidProtectedClearanceError, match="resolved 3D dynamic safety"):
        rigid_clearance_openings(
            replace(protected, evidence_status="DEVELOPMENT_HARD_ENVELOPE;3D_DYNAMIC_GEOMETRY_RESOLVED")
        )
