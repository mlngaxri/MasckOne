from dataclasses import replace

import cadquery as cq
import pytest

from masck_one.structural_frame_retention_root_capture_v2 import (
    CLIP_HOLE_RELIEF_MM,
    CLIP_THROAT_WIDTH_MM,
    StructuralFrameRetentionRootCaptureV2Error,
    build_structural_frame_retention_root_capture_v2,
)
from masck_one.structural_frame_retention_roots import (
    CLEVIS_CLIP_RADIAL_THICKNESS_MM,
    CLEVIS_PIN_GROOVE_DEPTH_MM,
    CLEVIS_PIN_RADIUS_MM,
    ROOT_Z_MM,
)


def test_controlled_throat_blocks_nominal_radial_escape() -> None:
    audit = build_structural_frame_retention_root_capture_v2()
    assert audit.throat_width_mm == CLIP_THROAT_WIDTH_MM
    assert audit.throat_width_mm < 2.0 * CLEVIS_PIN_RADIUS_MM
    assert audit.installation_margin_mm > 0.0
    assert audit.radial_escape_capture_margin_mm > 0.0
    assert len(audit.retainers) == 2
    assert audit.manifest()["capture_status"] == "CONTROLLED_C_CLIP_THROAT_NARROWER_THAN_PIN_SHAFT"


def test_controlled_throat_is_topologically_open_to_annular_bore() -> None:
    """Regress the V2 chord-floor bug that produced a closed ring.

    A probe on the radial centreline between the bore crown and outer crown must
    be void. If material exists here, the nominal throat does not actually join
    the exterior to the annular bore and the part cannot be installed radially.
    """
    audit = build_structural_frame_retention_root_capture_v2()
    inner = CLEVIS_PIN_RADIUS_MM - CLEVIS_PIN_GROOVE_DEPTH_MM + CLIP_HOLE_RELIEF_MM
    outer = CLEVIS_PIN_RADIUS_MM + CLEVIS_CLIP_RADIAL_THICKNESS_MM
    probe_z = ROOT_Z_MM + (inner + outer) / 2.0
    for retainer in audit.retainers:
        bb = retainer.val().BoundingBox()
        probe = cq.Vector((float(bb.xmin) + float(bb.xmax)) / 2.0, (float(bb.ymin) + float(bb.ymax)) / 2.0, probe_z)
        assert retainer.val().isInside(probe, 1e-7, True) is False


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_root_architecture_sha256", "0" * 64),
        ("source_capture_v1_sha256", "1" * 64),
        ("throat_width_mm", 2.70),
        ("installation_margin_mm", 0.0),
        ("radial_escape_capture_margin_mm", 0.0),
        ("evidence_sha256", "2" * 64),
    ],
)
def test_capture_v2_fails_closed_on_stale_or_unsafe_evidence(field: str, value: object) -> None:
    audit = build_structural_frame_retention_root_capture_v2()
    with pytest.raises(StructuralFrameRetentionRootCaptureV2Error):
        replace(audit, **{field: value}).validate()


def test_capture_v2_cannot_claim_physical_accidental_release_validation() -> None:
    audit = build_structural_frame_retention_root_capture_v2()
    with pytest.raises(StructuralFrameRetentionRootCaptureV2Error):
        replace(audit, accidental_release_validated=True).validate()
    with pytest.raises(StructuralFrameRetentionRootCaptureV2Error):
        replace(audit, physical_validation_eligible=True).validate()
