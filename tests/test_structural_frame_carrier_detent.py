from pathlib import Path

import cadquery as cq
import pytest

from masck_one.structural_frame_carrier_detent import (
    HOSTILE_SEATING_OVERTRAVEL_MM,
    REACTION_IDS,
    StructuralFrameCarrierDetentError,
    build_structural_frame_carrier_detent,
    export_structural_frame_carrier_detent,
)


def test_all_four_detents_are_positive_source_bound_counterparts() -> None:
    architecture = build_structural_frame_carrier_detent()
    assert tuple(item.reaction_id for item in architecture.features) == REACTION_IDS
    assert architecture.physical_validation_eligible is False
    for item in architecture.features:
        assert item.detent_feature.val().isValid()
        assert len(item.detent_feature.val().Solids()) == 1
        assert item.detent_feature.val().Volume() > 0.0
        assert item.source_interface_capture_mm3 > 0.0
        assert item.nominal_counterface_intersection_mm3 == pytest.approx(0.0, abs=1e-7)
        assert item.hostile_counterface_intersection_mm3 > 0.0


def test_hostile_loss_of_axial_capture_engagement_fails() -> None:
    architecture = build_structural_frame_carrier_detent()
    source = architecture.features[0]
    with pytest.raises(StructuralFrameCarrierDetentError, match="positive seating engagement"):
        type(source)(
            source.reaction_id,
            source.center_xy_mm,
            source.detent_feature,
            source.source_interface_capture_mm3,
            source.nominal_counterface_intersection_mm3,
            0.0,
        )


def test_hostile_loss_of_frame_capture_fails() -> None:
    architecture = build_structural_frame_carrier_detent()
    source = architecture.features[0]
    with pytest.raises(StructuralFrameCarrierDetentError, match="positive frame-side capture"):
        type(source)(
            source.reaction_id,
            source.center_xy_mm,
            source.detent_feature,
            0.0,
            source.nominal_counterface_intersection_mm3,
            source.hostile_counterface_intersection_mm3,
        )


def test_detent_artifacts_round_trip(tmp_path: Path) -> None:
    manifest = export_structural_frame_carrier_detent(tmp_path)
    assert manifest["schema"] == "MASCK_ONE_STRUCTURAL_FRAME_CARRIER_DETENT_V1"
    assert manifest["physical_validation_eligible"] is False
    assert HOSTILE_SEATING_OVERTRAVEL_MM > 0.0
    for reaction_id in REACTION_IDS:
        path = tmp_path / f"{reaction_id.lower()}_carrier_detent.step"
        assert path.exists()
        imported = cq.importers.importStep(str(path))
        assert imported.val().isValid()
        assert imported.val().Volume() > 0.0
