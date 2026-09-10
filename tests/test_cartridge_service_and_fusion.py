import json

import pytest

from masck_one.cartridge_fusion_handoff import export_fusion_handoff, fusion_handoff_manifest
from masck_one.cartridge_service_corridor import build_service_corridor
from masck_one.realized_waste_cartridge import build_realized_waste_cartridge


@pytest.fixture(scope="module")
def cartridge():
    return build_realized_waste_cartridge()


def test_current_main_oblique_sweep_reuses_shell_package_proof_but_invalidates_stale_frame(cartridge):
    report, shapes = build_service_corridor(cartridge)
    assert report["status"] == "CONTINUOUS_CURRENT_MAIN_SHELL_PACKAGE_CORRIDOR_CLEAR_FRAME_BREP_UNAVAILABLE"
    assert report["continuous_installed_device_path_proven"] is False
    assert report["blind_insertion_proven"] is False
    assert report["frame_geometry_status"].endswith("NO_BREP")
    assert report["stale_checkpoint_frame_evidence_status"].startswith("INVALIDATED_NOT_REUSED")
    assert all(
        abs(value) <= 1e-7
        for row in report["obstacle_intersections_mm3"].values()
        for value in row
    )
    assert set(shapes) == {"oblique_service_enclosures", "oblique_service_sweeps"}
    assert all(shape.val().isValid() for shape in shapes.values())


def test_fusion_manifest_has_named_parts_frames_datums_dofs_and_wet_sequence(cartridge):
    manifest = fusion_handoff_manifest(cartridge)
    assert manifest["scope"] == "FUSION_360_EDITABLE_DEVELOPMENT_HANDOFF_NOT_PRODUCTION_RELEASE"
    assert manifest["step_coordinate_space"] == "WORLD_MM"
    assert "MULTI_SOLID_REFERENCE_COMPOUNDS_EXPORT_AS_DETERMINISTIC_ONE_SOLID_STEP_PARTS" in manifest["reference_partition_rule"]
    assert set(manifest["manufacturing_components"]) == {
        "body",
        "closure",
        "left_bolt",
        "right_bolt",
        "left_bolt_guide",
        "right_bolt_guide",
        "key_tongue",
    }
    assert manifest["local_frame"]["frame_id"] == manifest["local_frame_id"]
    assert {joint["type"] for joint in manifest["joints_and_dofs"]} >= {
        "FIXED_INTENT",
        "PRISMATIC",
        "PRISMATIC_REFERENCE_PATH",
    }
    assert manifest["wet_interface"]["topology_order"] == [
        "WASTE_ACQUISITION",
        "WASTE_PUMP",
        "PASSIVE_BACKFLOW",
        "CARTRIDGE",
    ]
    assert manifest["wet_interface"]["retained_capacity_mL"] is None
    assert manifest["production_ready"] is False


def test_fusion_handoff_exports_separate_material_and_reference_steps_with_roundtrip(cartridge, tmp_path):
    manifest = export_fusion_handoff(tmp_path, cartridge)
    manifest_path = tmp_path / "cell11_waste_cartridge_fusion_handoff.json"
    stored = json.loads(manifest_path.read_text())
    assert stored["schema"] == manifest["schema"]
    assert stored["files"]
    assert any(
        row["classification"] == "CANDIDATE_MANUFACTURING_MATERIAL"
        for row in stored["files"].values()
    )
    assert any(
        row["classification"] == "REFERENCE_ONLY_NOT_PRODUCT_MATERIAL"
        for row in stored["files"].values()
    )
    for filename, row in stored["files"].items():
        assert (tmp_path / filename).is_file()
        assert row["roundtrip"]["status"] == "PASS"
        assert row["sha256"]

    # The conservative service path has three source pieces. Keep them as three
    # independently verified one-solid STEP assets so strict round-trip checks never
    # depend on ambiguous ordering of near-identical compound bounds.
    assert stored["reference_export_partitions"]["oblique_service_enclosures"] == 3
    assert stored["reference_export_partitions"]["oblique_service_sweeps"] == 3
    for group in ("oblique_service_enclosures", "oblique_service_sweeps"):
        grouped = [
            row for row in stored["files"].values()
            if row.get("reference_group") == group
        ]
        assert len(grouped) == 3
        assert sorted(row["source_solid_index"] for row in grouped) == [0, 1, 2]
        assert all(row["roundtrip"]["solid_count"] == 1 for row in grouped)

    assert stored["retained_capacity_mL"] is None
    assert stored["physical_validation_eligible"] is False
