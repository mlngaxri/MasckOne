from dataclasses import replace

import pytest

import masck_one.wet_electrical_candidate_landscape as landscape_module
from masck_one.wet_electrical_candidate_landscape import (
    CANDIDATE_HEADS,
    EVIDENCE_STATUS,
    SCHEMA,
    SOURCE_MAIN_SHA,
    SPECIALIST_CELLS_WITHOUT_PUBLISHED_HEADS,
    SPECIALIST_CELLS_WITH_PUBLISHED_HEADS,
    CandidateHead,
    WetElectricalCandidateLandscapeError,
    build_candidate_landscape_manifest,
)


PRE_121_BASE_SHA = "afe29ff78419b6625dca5594974b6351f6f80e1b"


def test_landscape_records_complete_current_specialist_metadata_without_consuming_stale_pre121_heads():
    manifest = build_candidate_landscape_manifest()
    assert manifest["schema"] == SCHEMA
    assert manifest["source_main_sha"] == SOURCE_MAIN_SHA
    assert SOURCE_MAIN_SHA == "b3be4c2483f45b2b8dfff6f0c3d9810c2b8511dc"
    assert manifest["evidence_status"] == EVIDENCE_STATUS
    assert manifest["candidate_geometry_consumed"] is False
    specialists = {
        item["cell"]: item for item in manifest["candidate_heads"] if item["cell"] >= 9
    }
    assert tuple(specialists) == (9, 10, 11, 12, 13, 14)
    assert specialists[9]["pr_number"] == 107
    assert specialists[9]["head_sha"] == "22d2e5baccbcfa56aa4a70e4e4dd59693e15affd"
    assert specialists[10]["pr_number"] == 125
    assert specialists[10]["head_sha"] == "3703f9b45defc91e05fbbe4516d28cd012db2efd"
    assert specialists[11]["pr_number"] == 115
    assert specialists[11]["head_sha"] == "4da053e57534c98617b9e8abfae7a35436a3718c"
    assert specialists[12]["pr_number"] == 111
    assert specialists[12]["head_sha"] == "fa017c8379dabaefeecf53bf770858bebfde3067"
    assert specialists[13]["pr_number"] == 113
    assert specialists[13]["head_sha"] == "dde7348002d13da77049dc1d540d79d389aac09f"
    assert specialists[14]["pr_number"] == 110
    assert specialists[14]["head_sha"] == "7b32c674860cab87cbdd1f7e3303a4ce53515e95"
    assert all(item["base_sha"] == PRE_121_BASE_SHA for item in specialists.values())
    assert all(item["based_on_live_main"] is False for item in specialists.values())
    assert all(
        "PRE_121_BASE_REBASE_REQUIRED" in item["disposition"]
        for item in specialists.values()
    )
    assert all(item["geometry_consumed"] is False for item in specialists.values())
    assert SPECIALIST_CELLS_WITH_PUBLISHED_HEADS == (9, 10, 11, 12, 13, 14)
    assert SPECIALIST_CELLS_WITHOUT_PUBLISHED_HEADS == ()


def test_target_cell4_candidates_are_stale_to_current_main_and_unconsumed():
    cell4 = {candidate.pr_number: candidate for candidate in CANDIDATE_HEADS if candidate.cell == 4}
    assert tuple(cell4) == (80, 85, 94, 96, 100)
    assert all(candidate.based_on_live_main is False for candidate in cell4.values())
    assert all(candidate.geometry_consumed is False for candidate in cell4.values())
    assert cell4[100].disposition == "STALE_BASE_REFERENCE_ONLY_CANDIDATE_NOT_RELEASED"
    assert cell4[96].role == "MIXED_WASTE_PUMP_SCREENING_PACKAGE"


def test_candidate_boolean_and_identity_promotions_fail_closed():
    candidate = CANDIDATE_HEADS[0]
    with pytest.raises(WetElectricalCandidateLandscapeError, match="must remain unconsumed"):
        replace(candidate, geometry_consumed=True)
    with pytest.raises(WetElectricalCandidateLandscapeError, match="must remain unconsumed"):
        replace(candidate, geometry_consumed=0)
    with pytest.raises(WetElectricalCandidateLandscapeError, match="canonical lowercase 40-hex"):
        replace(candidate, head_sha="NOT-A-SHA")
    with pytest.raises(WetElectricalCandidateLandscapeError, match="masck_one source path"):
        replace(candidate, source_path="../foreign.py")


def test_lineage_disposition_preserves_domain_specific_remaining_blockers():
    manifest = build_candidate_landscape_manifest()
    by_domain = {item["domain"]: item for item in manifest["lineage_disposition"]}
    assert by_domain["FRESH_WATER_SOURCE"]["strongest_current_candidate_pr"] == 107
    assert by_domain["CLEANSER_SOURCE"]["strongest_current_candidate_pr"] == 125
    assert by_domain["MIXED_WASTE"]["strongest_current_candidate_pr"] == 115
    assert by_domain["DRY_SIDE"]["strongest_current_candidate_pr"] == 111
    assert by_domain["HARNESS_BULKHEAD"]["strongest_current_candidate_pr"] == 113
    assert by_domain["HMI_WARM_THERMAL"]["strongest_current_candidate_pr"] == 110
    assert "PUMP_PASSIVE_BACKFLOW" in by_domain["MIXED_WASTE"]["remaining_dependency"]
    assert "FRAME_POSITIVE_ATTACHMENT" in by_domain["DRY_SIDE"]["remaining_dependency"]
    assert "ELECTRICAL_MATING_DATUMS" in by_domain["HARNESS_BULKHEAD"]["remaining_dependency"]
    assert "FINAL_CONTROL_MAPPING" in by_domain["HMI_WARM_THERMAL"]["remaining_dependency"]


def test_candidate_producer_appearance_forces_reconstruction(tmp_path, monkeypatch):
    producer = tmp_path / "src/masck_one/realized_fresh_water_source.py"
    producer.parent.mkdir(parents=True)
    producer.write_text("released now\n", encoding="utf-8")
    monkeypatch.setattr(landscape_module, "_REPO_ROOT", tmp_path)
    with pytest.raises(WetElectricalCandidateLandscapeError, match="candidate producer appeared"):
        build_candidate_landscape_manifest()


def test_manifest_is_deterministic():
    first = build_candidate_landscape_manifest()
    second = build_candidate_landscape_manifest()
    assert first == second
    assert len(first["manifest_sha256"]) == 64
