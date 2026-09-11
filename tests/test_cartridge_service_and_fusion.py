import json

import pytest

from masck_one.cartridge_device_service import SCHEMA as DEVICE_SERVICE_SCHEMA
from masck_one.cartridge_fusion_handoff import (
    SCHEMA,
    export_fusion_handoff,
    fusion_handoff_manifest,
)
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


def test_fusion_manifest_exports_selected_service_package_without_nested_material_duplicates(cartridge):
    manifest = fusion_handoff_manifest(cartridge)
    expected = {
        "body",
        "closure",
        "key_takeup_pad_inferior_y",
        "key_takeup_pad_superior_y",
        "key_takeup_pad_posterior_z",
        "device_receiver",
        "release_shuttle",
        "left_bolt_drive",
        "right_bolt_drive",
        "floating_wet_nose_drive",
        "wet_poppet_free_region",
    }
    forbidden_duplicates = {
        "left_bolt",
        "right_bolt",
        "left_bolt_guide",
        "right_bolt_guide",
        "key_tongue",
    }

    assert manifest["schema"] == SCHEMA
    assert manifest["device_service_schema"] == DEVICE_SERVICE_SCHEMA
    assert manifest["scope"] == "FUSION_360_EDITABLE_DEVELOPMENT_HANDOFF_NOT_PRODUCTION_RELEASE"
    assert manifest["step_coordinate_space"] == "WORLD_MM"
    assert set(manifest["manufacturing_components"]) == expected
    assert not forbidden_duplicates & set(manifest["manufacturing_components"])
    assert "NO_DUPLICATE_PHYSICAL_MATERIAL" in manifest["material_assembly_rule"]
    assert (
        manifest["manufacturing_components"]["closure"]["fusion_component_name"]
        == "WasteCartridge_Closure_WithKeyPadRoots"
    )
    assert manifest["local_frame"]["frame_id"] == manifest["local_frame_id"]
    assert manifest["production_ready"] is False
    assert manifest["physical_validation_eligible"] is False


def test_fusion_manifest_carries_real_service_dofs_and_honest_wet_sequence(cartridge):
    manifest = fusion_handoff_manifest(cartridge)
    joints = {joint["joint_id"]: joint for joint in manifest["joints_and_dofs"]}

    assert joints["RELEASE_SHUTTLE"]["axis_world"] == [0.0, 1.0, 0.0]
    assert joints["RELEASE_SHUTTLE"]["travel_limits_mm"] == [0.0, 4.0]
    assert joints["LEFT_RETENTION_BOLT_DRIVE"]["retraction_mm"] == 1.60
    assert joints["RIGHT_RETENTION_BOLT_DRIVE"]["retraction_mm"] == 1.60
    assert joints["FLOATING_WET_NOSE_DRIVE"]["retraction_mm"] == 1.40
    assert joints["REMOVED_STATE_POPPET"]["type"] == "COMPLIANT_PASSIVE_INTENT"

    wet = manifest["wet_interface"]
    assert wet["topology_order"] == [
        "WASTE_ACQUISITION",
        "WASTE_PUMP",
        "PASSIVE_BACKFLOW",
        "CARTRIDGE",
    ]
    assert wet["service_sequence_contract"][-1] == "ONLY_THEN_OBLIQUE_CARTRIDGE_TRANSLATION"
    assert wet["removed_state_port_closure_geometry_realized"] is True
    assert wet["retained_capacity_mL"] is None
    assert wet["leakage_validation"] is None
    assert wet["backflow_validation"] is None
    assert wet["service_force_validation"] is None


def test_fusion_handoff_exports_material_and_reference_steps_with_roundtrip(cartridge, tmp_path):
    manifest = export_fusion_handoff(tmp_path, cartridge)
    manifest_path = tmp_path / "cell11_waste_cartridge_fusion_handoff.json"
    stored = json.loads(manifest_path.read_text())

    assert stored["schema"] == manifest["schema"]
    assert stored["files"]
    material_rows = [
        row for row in stored["files"].values()
        if row["classification"] == "CANDIDATE_MANUFACTURING_MATERIAL"
    ]
    assert len(material_rows) == len(stored["manufacturing_components"])
    assert any(
        row["classification"] == "REFERENCE_ONLY_NOT_PRODUCT_MATERIAL"
        for row in stored["files"].values()
    )
    for filename, row in stored["files"].items():
        assert (tmp_path / filename).is_file()
        assert row["roundtrip"]["status"] == "PASS"
        assert row["sha256"]

    assert stored["reference_export_partitions"]["oblique_service_enclosures"] == 3
    assert stored["reference_export_partitions"]["oblique_service_sweeps"] == 3
    assert stored["reference_export_partitions"]["frame_mount_reference"] == 2
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
