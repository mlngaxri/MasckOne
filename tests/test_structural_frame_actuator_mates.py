from pathlib import Path

import cadquery as cq
import pytest

from masck_one.structural_frame_actuator_mates import (
    OVERTRAVEL_PROBE_MM,
    REACTION_IDS,
    StructuralFrameActuatorMateError,
    build_structural_frame_actuator_mates,
    export_structural_frame_actuator_mates,
)
from masck_one.structural_frame_actuator_reactions import build_structural_frame_actuator_reactions


def _intersection_volume(a: cq.Workplane, b: cq.Workplane) -> float:
    try:
        return max(0.0, float(a.intersect(b).val().Volume()))
    except Exception:
        return 0.0


def test_four_keyed_reaction_mates_are_positive_valid_and_clear() -> None:
    architecture = build_structural_frame_actuator_mates()
    assert tuple(m.reaction_id for m in architecture.mates) == REACTION_IDS
    assert architecture.physical_validation_eligible is False
    for mate in architecture.mates:
        value = mate.mate.val()
        assert value.isValid()
        assert len(value.Solids()) == 1
        assert value.Volume() > 0.0
        assert mate.nominal_frame_intersection_mm3 == 0.0
        assert mate.protected_intersection_mm3 == 0.0
        assert mate.overtravel_stop_intersection_mm3 > 0.0


def test_hostile_axial_overtravel_hits_real_frame_stop() -> None:
    reactions = build_structural_frame_actuator_reactions()
    architecture = build_structural_frame_actuator_mates(reactions=reactions)
    frame = reactions.frame_with_reaction_counterparts
    for mate in architecture.mates:
        moved = mate.mate.translate((0.0, 0.0, -OVERTRAVEL_PROBE_MM))
        assert _intersection_volume(moved, frame) > 1e-7


def test_manifest_is_source_chained_and_not_physical_evidence() -> None:
    reactions = build_structural_frame_actuator_reactions()
    architecture = build_structural_frame_actuator_mates(reactions=reactions)
    manifest = architecture.manifest()
    assert manifest["source_reaction_architecture_sha256"] == reactions.architecture_sha256
    assert manifest["physical_validation_eligible"] is False
    assert manifest["coupling_status"].endswith("CARRIER_BODY_MATING_OPEN")


def test_export_roundtrips_all_four_mates(tmp_path: Path) -> None:
    manifest = export_structural_frame_actuator_mates(tmp_path)
    assert manifest["schema"] == "MASCK_ONE_STRUCTURAL_FRAME_ACTUATOR_MATES_V1"
    for reaction_id in REACTION_IDS:
        path = tmp_path / f"{reaction_id.lower()}_reaction_mate.step"
        assert path.is_file() and path.stat().st_size > 0
        imported = cq.importers.importStep(str(path))
        assert imported.val().isValid()
        assert len(imported.val().Solids()) == 1
    assert (tmp_path / "structural_frame_actuator_mates_manifest.json").is_file()


def test_hostile_nominal_frame_overlap_is_rejected() -> None:
    architecture = build_structural_frame_actuator_mates()
    mate = architecture.mates[0]
    with pytest.raises(StructuralFrameActuatorMateError, match="nominal actuator mate intersects frame material"):
        type(mate)(
            reaction_id=mate.reaction_id,
            center_xy_mm=mate.center_xy_mm,
            nominal_frame_intersection_mm3=0.01,
            protected_intersection_mm3=mate.protected_intersection_mm3,
            overtravel_stop_intersection_mm3=mate.overtravel_stop_intersection_mm3,
            mate=mate.mate,
        )
