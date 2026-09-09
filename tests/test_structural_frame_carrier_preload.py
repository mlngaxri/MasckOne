from pathlib import Path

import cadquery as cq
import pytest

import masck_one.structural_frame_carrier_preload as preload_module
from masck_one.structural_frame_carrier_interfaces import build_structural_frame_carrier_interfaces
from masck_one.structural_frame_carrier_preload import (
    REACTION_IDS,
    StructuralFrameCarrierPreloadArchitecture,
    StructuralFrameCarrierPreloadError,
    build_structural_frame_carrier_preload,
    export_structural_frame_carrier_preload,
)


def test_four_preload_features_are_positive_source_bound_with_nominal_gap_and_hostile_engagement() -> None:
    interfaces = build_structural_frame_carrier_interfaces()
    architecture = build_structural_frame_carrier_preload(interfaces=interfaces)
    assert architecture.source_interface_architecture_sha256 == interfaces.architecture_sha256
    assert tuple(f.reaction_id for f in architecture.features) == REACTION_IDS
    assert architecture.physical_validation_eligible is False
    for item in architecture.features:
        value = item.preload_feature.val()
        assert value.isValid() and len(value.Solids()) == 1 and value.Volume() > 0.0
        assert item.source_interface_capture_mm3 > 1e-7
        assert item.nominal_counterface_intersection_mm3 <= 1e-7
        assert item.hostile_counterface_intersection_mm3 > 1e-7


def _rebuild(item, **overrides):
    values = dict(
        reaction_id=item.reaction_id,
        center_xy_mm=item.center_xy_mm,
        preload_feature=item.preload_feature,
        source_interface_capture_mm3=item.source_interface_capture_mm3,
        nominal_counterface_intersection_mm3=item.nominal_counterface_intersection_mm3,
        hostile_counterface_intersection_mm3=item.hostile_counterface_intersection_mm3,
    )
    values.update(overrides)
    return type(item)(**values)


def test_hostile_loss_of_source_capture_is_rejected() -> None:
    item = build_structural_frame_carrier_preload().features[0]
    with pytest.raises(StructuralFrameCarrierPreloadError, match="lacks positive source-interface capture"):
        _rebuild(item, source_interface_capture_mm3=0.0)


def test_hostile_loss_of_nominal_running_gap_is_rejected() -> None:
    item = build_structural_frame_carrier_preload().features[0]
    with pytest.raises(StructuralFrameCarrierPreloadError, match="no nominal lateral running gap"):
        _rebuild(item, nominal_counterface_intersection_mm3=0.01)


def test_hostile_loss_of_lateral_engagement_is_rejected() -> None:
    item = build_structural_frame_carrier_preload().features[0]
    with pytest.raises(StructuralFrameCarrierPreloadError, match="lacks positive hostile lateral engagement"):
        _rebuild(item, hostile_counterface_intersection_mm3=0.0)


@pytest.mark.parametrize("field", [
    "source_interface_capture_mm3",
    "nominal_counterface_intersection_mm3",
    "hostile_counterface_intersection_mm3",
])
def test_nonfinite_geometric_evidence_is_rejected(field: str) -> None:
    item = build_structural_frame_carrier_preload().features[0]
    with pytest.raises(StructuralFrameCarrierPreloadError, match="finite nonnegative geometric evidence"):
        _rebuild(item, **{field: float("nan")})


def test_intersection_kernel_failure_is_rejected(monkeypatch) -> None:
    class BrokenWorkplane:
        def intersect(self, other):
            raise RuntimeError("forced kernel failure")

    with pytest.raises(StructuralFrameCarrierPreloadError, match="intersection kernel failed"):
        preload_module._intersection_volume(BrokenWorkplane(), object())


@pytest.mark.parametrize("identity", ["g" * 64, "A" * 64, "a" * 63, "a" * 65])
def test_malformed_source_interface_identity_is_rejected(identity: str) -> None:
    architecture = build_structural_frame_carrier_preload()
    with pytest.raises(StructuralFrameCarrierPreloadError, match="lowercase hexadecimal SHA-256"):
        StructuralFrameCarrierPreloadArchitecture(identity, architecture.features, False)


def test_manifest_keeps_force_stiffness_acoustics_and_cell7_counterface_open() -> None:
    manifest = build_structural_frame_carrier_preload().manifest()
    assert manifest["schema"] == "MASCK_ONE_STRUCTURAL_FRAME_CARRIER_PRELOAD_V1"
    assert manifest["mechanical_status"].endswith("CELL7_COUNTERFACE_AND_PHYSICAL_PRELOAD_VALIDATION_OPEN")
    assert manifest["physical_validation_eligible"] is False
    for feature in manifest["features"]:
        assert feature["force_preload_stiffness_and_acoustic_performance"] == "PHYSICAL_VALIDATION_OPEN"


def test_export_roundtrips_all_four_preload_features(tmp_path: Path) -> None:
    manifest = export_structural_frame_carrier_preload(tmp_path)
    assert manifest["schema"] == "MASCK_ONE_STRUCTURAL_FRAME_CARRIER_PRELOAD_V1"
    for reaction_id in REACTION_IDS:
        path = tmp_path / f"{reaction_id.lower()}_carrier_preload_feature.step"
        assert path.is_file() and path.stat().st_size > 0
        imported = cq.importers.importStep(str(path))
        assert imported.val().isValid()
        assert len(imported.val().Solids()) == 1
