from dataclasses import replace

import pytest

import masck_one.realized_waste_cartridge as module
from masck_one.realized_waste_cartridge import (
    AUTHORED_AGAINST_MAIN_SHA,
    BLIND_SERVICE_CHECKPOINT_SHA,
    OWNER_PREDECESSOR_HEAD_SHA,
    RealizedWasteCartridgeError,
    build_realized_waste_cartridge,
    volume,
)


@pytest.fixture(scope="module")
def cartridge():
    return build_realized_waste_cartridge()


def test_consolidated_owner_keeps_supported_liner_and_never_promotes_retained_capacity(cartridge):
    report = cartridge.manifest()
    assert 35.0 <= cartridge.installed_geometric_free_capacity_mL < 36.0
    assert report["selected_architecture"] == "SUPPORTED_FORMED_LINER_SHALLOW_REINFORCED_CLOSURE"
    assert report["superseded_selected_candidate"]["status"] == "SUPERSEDED_NOT_SELECTED_HISTORICAL_EVIDENCE_ONLY"
    assert report["superseded_selected_candidate"]["geometric_capacity_mL"] < 35.0
    assert report["retained_capacity_mL"] is None
    assert report["retained_capacity_status"].startswith("PHYSICAL_VALIDATION_REQUIRED")
    assert report["physical_validation_eligible"] is False


def test_consolidated_owner_is_rebound_to_live_main_and_preserves_owner_lineage(cartridge):
    report = cartridge.manifest()
    assert report["authored_against_main_sha"] == AUTHORED_AGAINST_MAIN_SHA
    assert report["owner_lineage"]["predecessor_head_sha"] == OWNER_PREDECESSOR_HEAD_SHA
    assert report["owner_lineage"]["blind_service_checkpoint_sha"] == BLIND_SERVICE_CHECKPOINT_SHA
    assert report["source_git_blobs"]["src/masck_one/model.py"] == "9e7fa6c71ac28cc45ebb502444bf6c0ea49f7894"


def test_route_is_still_passive_backflow_to_cartridge(cartridge):
    report = cartridge.manifest()
    assert report["fluid_identity"] == "MIXED_AIR_LIQUID_FOAM_CONTAMINANT"
    assert "BARRIER" in report["route_id"].upper() or "BACKFLOW" in report["route_id"].upper()
    assert report["source_backbone_manifest_sha256"] == cartridge.source_backbone_manifest_sha256


def test_material_reference_and_local_world_frame_separation(cartridge):
    report = cartridge.manifest()
    assert report["parts"]["body"]["role"] == "CANDIDATE_MATERIAL"
    assert report["parts"]["closure"]["role"] == "CANDIDATE_MATERIAL"
    assert report["parts"]["cavity"]["role"] == "REFERENCE_ONLY"
    assert report["parts"]["inlet_reference"]["role"] == "REFERENCE_ONLY"
    assert report["local_frame"]["origin_world_mm"] == [0.0, -80.0, 8.0]
    assert report["local_frame"]["local_to_world_4x4"][1][3] == -80.0
    assert set(report["service_datums"]) >= {
        "cartridge_center",
        "waste_route_handoff",
        "body_inlet_wall",
        "seal_plane",
        "blind_key",
        "left_retention",
        "right_retention",
    }


def test_shell_protected_regions_and_cavity_accounting_remain_fail_closed(cartridge):
    cartridge.validate()
    assert report_zero(cartridge.manifest()["current_released_shell_interference_mm3"])
    assert all(report_zero(value) for value in cartridge.manifest()["protected_zone_intersections_mm3"].values())
    poisoned = replace(
        cartridge,
        installed_free_cavity_reference=cartridge.installed_free_cavity_reference.union(
            cartridge.retention_pockets_reference
        ),
    )
    with pytest.raises(RealizedWasteCartridgeError):
        poisoned.validate()


def test_stale_source_binding_fails_before_geometry(monkeypatch):
    monkeypatch.setattr(
        module,
        "SOURCE_GIT_BLOB_IDENTITIES",
        (("config/masck_one_authority.yaml", "0" * 40),),
    )
    with pytest.raises(RealizedWasteCartridgeError, match="source moved"):
        build_realized_waste_cartridge()


def test_body_closure_and_cavity_are_valid_connected_breps(cartridge):
    for shape in (
        cartridge.body_solid,
        cartridge.closure_solid,
        cartridge.installed_free_cavity_reference,
    ):
        assert shape.val().isValid()
        assert len(shape.val().Solids()) == 1
        assert volume(shape) > 0


def report_zero(value):
    return abs(float(value)) <= 1e-7
