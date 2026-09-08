from pathlib import Path

import cadquery as cq
import pytest

from masck_one.structural_frame_actuator_mates import build_structural_frame_actuator_mates
from masck_one.structural_frame_carrier_interfaces import (
    REACTION_IDS,
    StructuralFrameCarrierInterfaceError,
    build_structural_frame_carrier_interfaces,
    export_structural_frame_carrier_interfaces,
)


def test_four_frame_side_carrier_interfaces_are_positive_and_source_bound() -> None:
    mates = build_structural_frame_actuator_mates()
    architecture = build_structural_frame_carrier_interfaces(mates=mates)
    assert architecture.source_mate_architecture_sha256 == mates.architecture_sha256
    assert tuple(i.reaction_id for i in architecture.interfaces) == REACTION_IDS
    assert architecture.physical_validation_eligible is False
    for item in architecture.interfaces:
        value = item.interface.val()
        assert value.isValid()
        assert len(value.Solids()) == 1
        assert value.Volume() > 0.0
        assert item.source_mate_intersection_mm3 > 1e-7
        assert item.hostile_stop_intersection_mm3 > 1e-7


def test_hostile_loss_of_positive_capture_is_rejected() -> None:
    architecture = build_structural_frame_carrier_interfaces()
    item = architecture.interfaces[0]
    with pytest.raises(StructuralFrameCarrierInterfaceError, match="lacks positive source-mate capture"):
        type(item)(
            reaction_id=item.reaction_id,
            center_xy_mm=item.center_xy_mm,
            interface=item.interface,
            source_mate_intersection_mm3=0.0,
            hostile_stop_intersection_mm3=item.hostile_stop_intersection_mm3,
        )


def test_hostile_loss_of_end_stop_is_rejected() -> None:
    architecture = build_structural_frame_carrier_interfaces()
    item = architecture.interfaces[0]
    with pytest.raises(StructuralFrameCarrierInterfaceError, match="lacks positive service end stop"):
        type(item)(
            reaction_id=item.reaction_id,
            center_xy_mm=item.center_xy_mm,
            interface=item.interface,
            source_mate_intersection_mm3=item.source_mate_intersection_mm3,
            hostile_stop_intersection_mm3=0.0,
        )


def test_manifest_keeps_cell7_counterpart_and_continuous_service_open() -> None:
    manifest = build_structural_frame_carrier_interfaces().manifest()
    assert manifest["carrier_counterpart_status"].endswith("CELL7_FEMALE_COUNTERPART_OPEN")
    assert manifest["service_status"].endswith("CONTINUOUS_WHOLE_CARRIER_SWEEP_OPEN")
    assert manifest["physical_validation_eligible"] is False


def test_export_roundtrips_all_four_interfaces(tmp_path: Path) -> None:
    manifest = export_structural_frame_carrier_interfaces(tmp_path)
    assert manifest["schema"] == "MASCK_ONE_STRUCTURAL_FRAME_CARRIER_INTERFACES_V1"
    for reaction_id in REACTION_IDS:
        path = tmp_path / f"{reaction_id.lower()}_carrier_interface.step"
        assert path.is_file() and path.stat().st_size > 0
        imported = cq.importers.importStep(str(path))
        assert imported.val().isValid()
        assert len(imported.val().Solids()) == 1
