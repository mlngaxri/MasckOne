from pathlib import Path

import cadquery as cq
import pytest

from masck_one.structural_frame_carrier_landing import (
    HOSTILE_LANDING_OVERTRAVEL_MM,
    REACTION_IDS,
    StructuralFrameCarrierLandingError,
    build_structural_frame_carrier_landing,
    export_structural_frame_carrier_landing,
)


def test_all_four_landing_tongues_are_positive_and_source_captured() -> None:
    architecture = build_structural_frame_carrier_landing()
    assert tuple(item.reaction_id for item in architecture.features) == REACTION_IDS
    assert architecture.physical_validation_eligible is False
    for item in architecture.features:
        assert item.landing_feature.val().isValid()
        assert len(item.landing_feature.val().Solids()) == 1
        assert item.landing_feature.val().Volume() > 0.0
        assert item.source_interface_capture_mm3 > 0.0
        assert item.nominal_probe_intersection_mm3 == pytest.approx(0.0, abs=1e-7)
        assert item.hostile_probe_intersection_mm3 > 0.0


def test_hostile_loss_of_positive_landing_engagement_fails() -> None:
    architecture = build_structural_frame_carrier_landing()
    source = architecture.features[0]
    with pytest.raises(StructuralFrameCarrierLandingError, match="positive overtravel engagement"):
        type(source)(
            source.reaction_id,
            source.center_xy_mm,
            source.landing_feature,
            source.source_interface_capture_mm3,
            source.nominal_probe_intersection_mm3,
            0.0,
        )


def test_landing_artifacts_round_trip(tmp_path: Path) -> None:
    manifest = export_structural_frame_carrier_landing(tmp_path)
    assert manifest["schema"] == "MASCK_ONE_STRUCTURAL_FRAME_CARRIER_LANDING_V1"
    assert manifest["physical_validation_eligible"] is False
    assert HOSTILE_LANDING_OVERTRAVEL_MM > 0.0
    for reaction_id in REACTION_IDS:
        path = tmp_path / f"{reaction_id.lower()}_carrier_landing_tongue.step"
        assert path.exists()
        imported = cq.importers.importStep(str(path))
        assert imported.val().isValid()
        assert imported.val().Volume() > 0.0
