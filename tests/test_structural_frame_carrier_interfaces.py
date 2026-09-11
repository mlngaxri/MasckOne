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


def test_four_frame_side_carrier_interfaces_are_positive_source_bound_and_continuously_serviceable() -> None:
    mates = build_structural_frame_actuator_mates()
    architecture = build_structural_frame_carrier_interfaces(mates=mates)
    assert architecture.source_mate_architecture_sha256 == mates.architecture_sha256
    assert tuple(i.reaction_id for i in architecture.interfaces) == REACTION_IDS
    assert architecture.physical_validation_eligible is False
    for item in architecture.interfaces:
        value = item.interface.val()
        sweep = item.service_sweep.val()
        assert value.isValid() and len(value.Solids()) == 1 and value.Volume() > 0.0
        assert sweep.isValid() and len(sweep.Solids()) == 1 and sweep.Volume() > 0.0
        assert item.source_mate_intersection_mm3 > 1e-7
        assert item.nominal_service_probe_intersection_mm3 <= 1e-7
        assert item.continuous_service_sweep_intersection_mm3 <= 1e-7
        assert item.hostile_stop_intersection_mm3 > 1e-7


def _rebuild(item, **overrides):
    values = dict(
        reaction_id=item.reaction_id,
        center_xy_mm=item.center_xy_mm,
        interface=item.interface,
        service_sweep=item.service_sweep,
        source_mate_intersection_mm3=item.source_mate_intersection_mm3,
        nominal_service_probe_intersection_mm3=item.nominal_service_probe_intersection_mm3,
        continuous_service_sweep_intersection_mm3=item.continuous_service_sweep_intersection_mm3,
        hostile_stop_intersection_mm3=item.hostile_stop_intersection_mm3,
    )
    values.update(overrides)
    return type(item)(**values)


def test_hostile_loss_of_positive_capture_is_rejected() -> None:
    item = build_structural_frame_carrier_interfaces().interfaces[0]
    with pytest.raises(StructuralFrameCarrierInterfaceError, match="lacks positive source-mate capture"):
        _rebuild(item, source_mate_intersection_mm3=0.0)


def test_hostile_nominal_service_obstruction_is_rejected() -> None:
    item = build_structural_frame_carrier_interfaces().interfaces[0]
    with pytest.raises(StructuralFrameCarrierInterfaceError, match="service entry is obstructed"):
        _rebuild(item, nominal_service_probe_intersection_mm3=0.01)


def test_hostile_continuous_service_sweep_collision_is_rejected() -> None:
    item = build_structural_frame_carrier_interfaces().interfaces[0]
    with pytest.raises(StructuralFrameCarrierInterfaceError, match="continuous carrier service-entry sweep intersects"):
        _rebuild(item, continuous_service_sweep_intersection_mm3=0.01)


def test_hostile_loss_of_end_stop_is_rejected() -> None:
    item = build_structural_frame_carrier_interfaces().interfaces[0]
    with pytest.raises(StructuralFrameCarrierInterfaceError, match="lacks positive service end stop"):
        _rebuild(item, hostile_stop_intersection_mm3=0.0)


def test_manifest_keeps_cell7_counterpart_and_whole_carrier_service_open() -> None:
    manifest = build_structural_frame_carrier_interfaces().manifest()
    assert manifest["carrier_counterpart_status"].endswith("CELL7_FEMALE_COUNTERPART_OPEN")
    assert "CONTINUOUS_FRAME_SIDE_ENTRY_SWEEP" in manifest["service_status"]
    assert "INDEPENDENT_POSITIVE_END_STOP_PROBE_REALIZED" in manifest["service_status"]
    assert manifest["service_status"].endswith("WHOLE_CARRIER_SWEEP_OPEN")
    assert manifest["physical_validation_eligible"] is False


def test_export_roundtrips_all_four_interfaces_and_continuous_sweeps(tmp_path: Path) -> None:
    manifest = export_structural_frame_carrier_interfaces(tmp_path)
    assert manifest["schema"] == "MASCK_ONE_STRUCTURAL_FRAME_CARRIER_INTERFACES_V1"
    for reaction_id in REACTION_IDS:
        for suffix in ("carrier_interface", "carrier_service_sweep"):
            path = tmp_path / f"{reaction_id.lower()}_{suffix}.step"
            assert path.is_file() and path.stat().st_size > 0
            imported = cq.importers.importStep(str(path))
            assert imported.val().isValid()
            assert len(imported.val().Solids()) == 1
