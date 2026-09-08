from __future__ import annotations

from masck_one import assembly_service_inventory as asi


def test_current_cell2_rear_service_candidate_head_is_rebound_without_promotion() -> None:
    inventory = asi.build_current_assembly_service_inventory()
    rear = next(
        domain
        for domain in inventory.service_domains
        if domain.domain_id == "MASCK_ONE-SERVICE-REAR-COVER-ACCESS"
    )

    assert asi.CELL2_REAR_SERVICE_PR == 70
    assert asi.CELL2_REAR_SERVICE_HEAD == "559f89953e6ac7667e79426daabcd54b88f43acb"
    assert asi.CELL2_REAR_SERVICE_PREVIOUS_HEAD == "58b95bc369d3879607ac060a5725426019d65abc"
    assert rear.candidate is not None
    assert rear.candidate.pr_number == asi.CELL2_REAR_SERVICE_PR
    assert rear.candidate.head_sha == asi.CELL2_REAR_SERVICE_HEAD
    assert rear.candidate.manifest()["authority_status"] == "UNMERGED_CANDIDATE_NOT_RELEASE_AUTHORITY"
    assert rear.released_motion_status == asi.MOTION_MISSING_RELEASED_PRODUCER
    assert rear.candidate_motion_status == asi.MOTION_CANDIDATE_REFERENCE
    assert inventory.manifest()["digital_mvp_service_ready"] is False


def test_cell2_head_movement_disposition_does_not_claim_service_geometry_change() -> None:
    assert asi.CELL2_REAR_SERVICE_REBIND_DISPOSITION == (
        "HEAD_MOVED_BY_EXTERIOR_EYE_ROLL_SOLID_NORMALIZATION_ONLY_REAR_SERVICE_MOTION_EVIDENCE_UNCHANGED"
    )
