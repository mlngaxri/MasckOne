import json

from masck_one.export import export_release
from masck_one.harness_endpoint_inventory import build_harness_endpoint_inventory


def test_release_smoke_emits_endpoint_inventory_without_promoting_harness_geometry(tmp_path):
    report = export_release(tmp_path)
    inventory = build_harness_endpoint_inventory()
    expected = inventory.manifest()

    artifact_path = tmp_path / "harness_endpoint_inventory_v1.json"
    assert artifact_path.is_file()
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert artifact == expected
    assert report["electrical_interconnect"]["harness_endpoint_inventory_v1"] == expected
    assert report["exported_manifest_files"] == ["harness_endpoint_inventory_v1.json"]
    assert expected["current_harness_centerlines_released"] is False
    assert expected["wet_dry_bulkhead_geometry_released"] is False
    assert expected["development_assembly_material_eligible"] is False
    assert all("harness" not in filename.lower() for filename in report["exported_step_files"])
