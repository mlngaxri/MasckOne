from dataclasses import replace
import json

import pytest

import masck_one.datum_ctq_inventory as inventory_module
from masck_one.datum_ctq_inventory import (
    AUTHORITY_BLOB_SHA,
    CANDIDATE_EVIDENCE,
    EVIDENCE_STATUS,
    FRAME_CONTRACT_RELEASE_STATUS,
    SCHEMA,
    SOURCE_MAIN_SHA,
    WORLD_FRAME_ID,
    CandidateCell5BlockerSnapshot,
    CtqRecord,
    DatumCtqInventoryError,
    build_datum_ctq_inventory,
    write_datum_ctq_inventory,
)


@pytest.fixture(scope="module")
def inventory():
    return build_datum_ctq_inventory()


def test_inventory_binds_exact_released_main_authority_and_frame_contract_state(inventory):
    assert inventory.schema == SCHEMA
    assert inventory.source_main_sha == SOURCE_MAIN_SHA
    assert inventory.authority_blob_sha == AUTHORITY_BLOB_SHA
    assert inventory.canonical_world_frame_id == WORLD_FRAME_ID
    assert inventory.cross_system_frame_contract_status == FRAME_CONTRACT_RELEASE_STATUS
    assert inventory.candidate_frame_contract_pr_number == 79
    assert inventory.candidate_frame_contract_head_sha == "7f60cae4962ffc49ed8e77faf77534f4fd82b1f5"
    assert inventory.digital_mvp_dimensional_ready is False
    assert inventory.physical_validation_eligible is False
    assert inventory.evidence_status == EVIDENCE_STATUS


def test_authority_world_and_spatial_global_are_explicit_duplicate_identity_aliases(inventory):
    by_id = {item.observation_id: item for item in inventory.datums}
    world = by_id["DATUM_AUTHORITY_WORLD"]
    alias = by_id["DATUM_SPATIAL_GLOBAL_ALIAS"]
    assert world.datum_label == WORLD_FRAME_ID
    assert world.coordinates_xyz_mm == (0.0, 0.0, 0.0)
    assert alias.datum_label == "MASCK_ONE_GLOBAL"
    assert alias.coordinates_xyz_mm == world.coordinates_xyz_mm
    assert alias.resolution == "DUPLICATE_IDENTITY_ALIAS_UNRELEASED_BINDING"
    group = inventory.duplicate_datum_groups[0]
    assert group.observation_ids == ("DATUM_AUTHORITY_WORLD", "DATUM_SPATIAL_GLOBAL_ALIAS")
    assert group.manufacturing_interchangeability_allowed is False


def test_structural_frame_xy_references_are_not_promoted_to_3d_manufacturing_datums(inventory):
    structural = [
        item for item in inventory.datums
        if item.observation_id.startswith("DATUM_FRAME_")
    ]
    assert len(structural) == 5
    assert {item.manufacturing_datum_status for item in structural} == {"NOT_QUALIFIED_3D_DATUM"}
    assert all(item.coordinates_xyz_mm is not None and item.coordinates_xyz_mm[2] is None for item in structural)
    coords = {item.observation_id: item.coordinates_xyz_mm for item in structural}
    assert coords["DATUM_FRAME_CENTER"] == (0.0, 0.0, None)
    assert coords["DATUM_FRAME_SUPERIOR"] == (0.0, 101.0, None)
    assert coords["DATUM_FRAME_INFERIOR"] == (0.0, -101.0, None)
    assert coords["DATUM_FRAME_WEARER_LEFT"] == (-77.5, 0.0, None)
    assert coords["DATUM_FRAME_WEARER_RIGHT"] == (77.5, 0.0, None)


def test_actuator_mount_and_mechanism_clearance_frames_remain_explicitly_unresolved(inventory):
    actuator_mounts = [
        item for item in inventory.datums
        if item.observation_id.startswith("DATUM_ACTUATOR_ZONE_")
    ]
    assert len(actuator_mounts) == 4
    assert all(item.resolution == "IMPLICIT_UNRESOLVED" for item in actuator_mounts)
    assert all(item.coordinates_xyz_mm is None for item in actuator_mounts)
    mechanism = next(
        item for item in inventory.datums
        if item.observation_id == "DATUM_MECHANISM_CLEARANCE_FRAME"
    )
    assert mechanism.coordinate_frame_id == "UNRESOLVED"
    assert mechanism.resolution == "IMPLICIT_UNRESOLVED"


def test_defined_authority_ctqs_preserve_exact_digital_limits_without_capability_claim(inventory):
    ctq = {item.ctq_id: item for item in inventory.ctqs}
    seam = ctq["CTQ_VISIBLE_SEAM_GAP"]
    assert seam.nominal == pytest.approx(0.40)
    assert seam.lower_limit == pytest.approx(0.25)
    assert seam.upper_limit == pytest.approx(0.55)
    flush = ctq["CTQ_VISIBLE_SEAM_FLUSH_MISMATCH"]
    assert flush.lower_limit == 0.0
    assert flush.upper_limit == pytest.approx(0.15)
    wall = ctq["CTQ_SHELL_WALL_MINIMUM"]
    assert wall.nominal == pytest.approx(1.8)
    assert wall.lower_limit == pytest.approx(1.5)
    assert wall.upper_limit is None
    assert all(item.physical_validation_eligible is False for item in (seam, flush, wall))


def test_unresolved_geometry_dependent_ctqs_carry_no_invented_numeric_tolerances(inventory):
    blocked = [item for item in inventory.ctqs if item.status == "BLOCKED_UNRESOLVED_GEOMETRY_OR_DATUM"]
    assert {item.ctq_id for item in blocked} == {
        "CTQ_STRUCTURAL_FRAME_3D_DATUM_QUALIFICATION",
        "CTQ_ACTUATOR_MOUNT_DATUM_FIT_STACK",
        "CTQ_MECHANISM_CLEARANCE_FRAME_BINDING",
        "CTQ_WASTE_CARTRIDGE_CRITICAL_FIT_STACKS",
        "CTQ_FLUID_ROUTING_CRITICAL_FIT_STACKS",
    }
    assert all(item.tolerance_kind == "UNRESOLVED" for item in blocked)
    assert all(item.nominal is None and item.lower_limit is None and item.upper_limit is None for item in blocked)


def test_cell5_candidate_blockers_are_exact_head_snapshots_only(inventory):
    by_pr = {item.pr_number: item for item in inventory.candidate_cell5_blockers}
    assert set(by_pr) == {82, 91, 99}
    assert by_pr[82].exact_head_sha == "a52dbf7fab09b0e82715d6c800b07e35c6216965"
    assert by_pr[91].exact_head_sha == "c57b577d4e4d3333ecfb736be7fc4462dd7fa823"
    assert by_pr[99].exact_head_sha == "072d59bd7a278385818cf19af38dbca58b8b1bd7"
    assert all(item.evidence_status == CANDIDATE_EVIDENCE for item in by_pr.values())


def test_inventory_and_candidate_evidence_cannot_be_promoted(inventory):
    with pytest.raises(DatumCtqInventoryError, match="stale for released main"):
        replace(inventory, source_main_sha="0" * 40)
    with pytest.raises(DatumCtqInventoryError, match="authority-world frame"):
        replace(inventory, canonical_world_frame_id="MASCK_ONE_GLOBAL")
    with pytest.raises(DatumCtqInventoryError, match="cannot be dimensionally ready"):
        replace(inventory, digital_mvp_dimensional_ready=True)
    with pytest.raises(DatumCtqInventoryError, match="cannot become physical validation"):
        replace(inventory, physical_validation_eligible=True)
    with pytest.raises(DatumCtqInventoryError, match="evidence boundary"):
        replace(inventory, evidence_status="PHYSICAL_VALIDATION")
    with pytest.raises(DatumCtqInventoryError, match="cannot be promoted"):
        replace(inventory.candidate_cell5_blockers[0], evidence_status="RELEASE_AUTHORITY")


def test_unresolved_ctq_cannot_invent_numbers_and_nonfinite_or_reversed_limits_fail_closed():
    with pytest.raises(DatumCtqInventoryError, match="cannot invent"):
        CtqRecord(
            "CTQ_TEST_UNRESOLVED",
            "test source",
            "test owner",
            "test characteristic",
            "mm",
            "UNRESOLVED",
            1.0,
            None,
            None,
            "BLOCKED_UNRESOLVED_GEOMETRY_OR_DATUM",
            "test inspection reference",
        )
    with pytest.raises(DatumCtqInventoryError, match="finite"):
        CtqRecord(
            "CTQ_TEST_FINITE",
            "test source",
            "test owner",
            "test characteristic",
            "mm",
            "BILATERAL",
            float("nan"),
            0.0,
            1.0,
            "DEFINED_DIGITAL_REQUIREMENT",
            "test inspection reference",
        )
    with pytest.raises(DatumCtqInventoryError, match="reversed"):
        CtqRecord(
            "CTQ_TEST_ORDER",
            "test source",
            "test owner",
            "test characteristic",
            "mm",
            "BILATERAL",
            1.0,
            2.0,
            1.0,
            "DEFINED_DIGITAL_REQUIREMENT",
            "test inspection reference",
        )


def test_duplicate_identity_and_nested_mutation_fail_closed(inventory):
    duplicate = inventory.duplicate_datum_groups[0]
    with pytest.raises(DatumCtqInventoryError, match="interchangeable manufacturing datums"):
        replace(duplicate, manufacturing_interchangeability_allowed=True)

    mutated = build_datum_ctq_inventory()
    object.__setattr__(mutated.datums[-1], "resolution", "CANONICAL")
    with pytest.raises(DatumCtqInventoryError):
        mutated.manifest()


def test_source_movement_and_new_release_contracts_force_reconstruction(monkeypatch):
    original = inventory_module.SOURCE_GIT_BLOB_IDENTITIES
    monkeypatch.setattr(
        inventory_module,
        "SOURCE_GIT_BLOB_IDENTITIES",
        ((original[0][0], "0" * 40), *original[1:]),
    )
    with pytest.raises(DatumCtqInventoryError, match="source moved"):
        build_datum_ctq_inventory()


def test_manifest_and_standalone_review_artifact_are_deterministic(tmp_path, inventory):
    second = build_datum_ctq_inventory()
    assert second.manifest() == inventory.manifest()
    assert second.manifest_sha256 == inventory.manifest_sha256
    assert len(inventory.manifest_sha256) == 64

    payload = write_datum_ctq_inventory(tmp_path, inventory=inventory)
    written = json.loads((tmp_path / "datum_ctq_inventory.json").read_text(encoding="utf-8"))
    assert written == payload == inventory.manifest()
    assert written["manifest_sha256"] == inventory.manifest_sha256
    assert written["blocked_ctq_count"] == 5
    assert written["unresolved_datum_count"] == 5


def test_candidate_snapshot_rejects_malformed_head_and_boolean_pr_number():
    with pytest.raises(DatumCtqInventoryError, match="40-hex"):
        CandidateCell5BlockerSnapshot(
            82,
            "A" * 40,
            "BLOCKER_TEST",
            "owner",
            "closure",
        )
    with pytest.raises(DatumCtqInventoryError, match="positive int"):
        CandidateCell5BlockerSnapshot(
            True,
            "a" * 40,
            "BLOCKER_TEST",
            "owner",
            "closure",
        )
