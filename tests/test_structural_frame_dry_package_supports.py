from __future__ import annotations

import cadquery as cq

from masck_one.model import build_model
from masck_one.structural_frame_dry_package_supports import (
    BATTERY_SIDE_CLEARANCE_MM,
    STOP_PROBE_MM,
    SUPPORT_IDS,
    _ivol,
    build_structural_frame_dry_package_supports,
    export_structural_frame_dry_package_supports,
)


def test_bilateral_dry_package_supports_are_positive_clear_and_source_chained() -> None:
    model = build_model()
    architecture = build_structural_frame_dry_package_supports(model=model)
    assert tuple(s.support_id for s in architecture.supports) == SUPPORT_IDS
    assert len(architecture.source_reaction_architecture_sha256) == 64
    assert architecture.physical_validation_eligible is False
    assert architecture.frame_with_support_counterparts.val().isValid()
    assert len(architecture.frame_with_support_counterparts.solids().vals()) == 1
    for support in architecture.supports:
        assert support.rail.val().isValid()
        assert len(support.rail.solids().vals()) == 1
        assert support.frame_intersection_mm3 == 0.0
        assert support.package_intersection_mm3 == 0.0
        assert support.protected_intersection_mm3 == 0.0
        assert support.hostile_package_stop_intersection_mm3 > 0.0


def test_hostile_lateral_shift_hits_battery_reference_material() -> None:
    model = build_model()
    architecture = build_structural_frame_dry_package_supports(model=model)
    battery = model.battery_reference_envelope.solid
    assert STOP_PROBE_MM > BATTERY_SIDE_CLEARANCE_MM
    for support in architecture.supports:
        hostile = support.rail.translate((-support.side_sign * STOP_PROBE_MM, 0.0, 0.0))
        assert _ivol(hostile, battery) > 0.0


def test_deterministic_dry_package_support_export_roundtrips(tmp_path) -> None:
    manifest = export_structural_frame_dry_package_supports(tmp_path)
    assert manifest["schema"] == "MASCK_ONE_STRUCTURAL_FRAME_DRY_PACKAGE_SUPPORTS_V1"
    assert manifest["physical_validation_eligible"] is False
    paths = [tmp_path / "structural_frame_with_battery_support_counterparts.step"]
    paths += [tmp_path / f"{support_id.lower()}.step" for support_id in SUPPORT_IDS]
    for path in paths:
        assert path.is_file() and path.stat().st_size > 0
        imported = cq.importers.importStep(str(path))
        assert imported.val().isValid()
        assert len(imported.solids().vals()) == 1
    assert (tmp_path / "structural_frame_dry_package_supports_manifest.json").is_file()
