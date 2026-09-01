from dataclasses import replace

import pytest

from masck_one.boundary_release import build_verified_interface_boundary_topology
from masck_one.interface_attachment import build_interface_attachment_architecture
from masck_one.model import build_model
from masck_one.retention_release_contract import (
    CONTRACT_ID,
    DIGITAL_GEOMETRY_STATUS,
    PHYSICAL_VALIDATION_STATUS,
    PREFERRED_EVALUATION_LANE,
    QuickReleaseRequirements,
    ReleaseArchitectureOption,
    RetentionEdge,
    RetentionLoadPathTopology,
    RetentionReleaseContractError,
    build_retention_release_prework,
)
from masck_one.structural_frame import RESERVATION_RETENTION, build_structural_frame_topology


def _build():
    model = build_model()
    boundaries = build_verified_interface_boundary_topology(
        model.authority,
        model.facial_surface,
        model.coverage_mesh,
        model.compliant_interface_topology,
    )
    attachment = build_interface_attachment_architecture(model.authority, boundaries)
    frame = build_structural_frame_topology(model.authority, attachment)
    contract = build_retention_release_prework(model.authority, frame)
    return model, frame, contract


def test_prework_binds_frozen_release_requirements_without_claiming_measurement():
    model, frame, contract = _build()
    manifest = contract.manifest()

    assert manifest["contract"] == CONTRACT_ID
    assert contract.source_structural_frame_sha256 == frame.topology_sha256
    assert contract.requirements.time_max_s == model.authority.number(
        "safety", "quick_release", "time_max_s"
    ) == 2.0
    assert contract.requirements.force_target_N == (5.0, 12.0)
    assert contract.requirements.one_hand_wet_unpowered is True
    assert manifest["requirements"]["performance_evidence"] == "REQUIREMENT_ONLY_NOT_MEASURED_PERFORMANCE"
    assert contract.physical_validation_eligible is False
    assert manifest["iteration29_complete"] is False
    assert manifest["iteration30_complete"] is False


def test_prework_keeps_geometry_and_physical_validation_blocked():
    _, _, contract = _build()
    assert contract.digital_geometry_status == DIGITAL_GEOMETRY_STATUS
    assert contract.physical_validation_status == PHYSICAL_VALIDATION_STATUS
    assert "BLOCKED_PENDING_CONTROLLED_ITERATION29" in contract.digital_geometry_status
    assert "BLOCKED_PENDING" in contract.physical_validation_status
    manifest_text = repr(contract.manifest())
    assert "PHYSICAL_PASS" not in manifest_text
    assert "MEASURED_PASS" not in manifest_text


def test_topology_has_one_closed_retention_loop_and_release_breaks_all_cycles():
    _, _, contract = _build()
    topology = contract.load_path_topology
    assert topology.cycle_rank(release_open=False) == 1
    assert topology.cycle_rank(release_open=True) == 0
    assert sum(edge.release_interrupt for edge in topology.edges) == 1
    assert sum(edge.preload_adjustment for edge in topology.edges) == 1
    assert topology.release_control_id != topology.preload_adjuster_id


def test_crown_support_is_load_sharing_branch_not_secondary_trap_loop():
    _, _, contract = _build()
    topology = contract.load_path_topology
    adjacency = topology._adjacency(release_open=False)
    assert adjacency[topology.crown_node_id] == {topology.occipital_node_id}
    assert topology.cycle_rank(release_open=True) == 0


def test_preload_adjustment_cannot_double_as_emergency_release_edge():
    with pytest.raises(RetentionReleaseContractError, match="may not also be"):
        RetentionEdge(
            edge_id="RET_BAD_SHARED_FUNCTION",
            node_a="RET_NODE_A",
            node_b="RET_NODE_B",
            role="invalid shared adjust/release function",
            release_interrupt=True,
            preload_adjustment=True,
        )


def test_secondary_closed_loop_after_release_is_rejected():
    _, _, contract = _build()
    topology = contract.load_path_topology
    crown_loop_edge = RetentionEdge(
        edge_id="RET_BAD_CROWN_SECONDARY_LOOP",
        node_a=topology.crown_node_id,
        node_b="RET_PRELOAD_ADJUSTER",
        role="hostile secondary crown closure",
    )
    with pytest.raises(RetentionReleaseContractError, match="exactly one independent retention loop|crown support"):
        replace(topology, edges=topology.edges + (crown_loop_edge,))


def test_missing_or_duplicate_release_interrupt_is_rejected():
    _, _, contract = _build()
    topology = contract.load_path_topology
    without_release = tuple(replace(edge, release_interrupt=False) for edge in topology.edges)
    with pytest.raises(RetentionReleaseContractError, match="exactly one primary loop-break"):
        replace(topology, edges=without_release)

    duplicate_release = tuple(
        replace(edge, release_interrupt=(edge.release_interrupt or edge.preload_adjustment))
        for edge in topology.edges
    )
    # The adjustment edge becomes both adjustment and release and is rejected even earlier.
    with pytest.raises(RetentionReleaseContractError):
        replace(topology, edges=duplicate_release)


def test_architecture_comparison_keeps_credible_alternatives_and_rejects_adjuster_unwind_as_primary_release():
    _, _, contract = _build()
    assert contract.preferred_evaluation_lane == PREFERRED_EVALUATION_LANE
    options = {option.option_id: option for option in contract.architecture_options}
    assert tuple(option.option_id for option in contract.architecture_options) == (
        "DEDICATED_SINGLE_ACTION_LOOP_BREAK",
        "REAR_CENTER_LOOP_BREAK",
        "FRONT_FRAME_LOOP_BREAK",
        "PRELOAD_ADJUSTER_UNWIND_AS_RELEASE",
    )
    assert options["DEDICATED_SINGLE_ACTION_LOOP_BREAK"].disposition.startswith("PREFERRED_EVALUATION")
    assert options["REAR_CENTER_LOOP_BREAK"].disposition.startswith("CREDIBLE_ALTERNATIVE")
    assert options["FRONT_FRAME_LOOP_BREAK"].disposition.startswith("DEPRIORITIZED")
    assert options["PRELOAD_ADJUSTER_UNWIND_AS_RELEASE"].disposition == "REJECTED_AS_PRIMARY_EMERGENCY_RELEASE_PATH"


def test_preferred_lane_does_not_freeze_side_location_latch_geometry_or_actuation_direction():
    _, _, contract = _build()
    preferred = contract.architecture_options[0]
    text = " ".join((preferred.concept, *preferred.material_risks)).lower()
    assert "exact side" in text
    assert "latch" in text
    assert "actuation direction" in text
    assert "unresolved" in text


def test_source_retention_reservation_cannot_be_promoted_or_mutated_before_iteration29():
    model, frame, _ = _build()
    retention = next(item for item in frame.reservations if item.reservation_id == RESERVATION_RETENTION)
    object.__setattr__(retention, "placement_status", "GEOMETRY_COMPLETE")
    with pytest.raises(RetentionReleaseContractError, match="promoted outside Iteration 29"):
        build_retention_release_prework(model.authority, frame)


def test_source_frame_cannot_claim_physical_validation_or_selected_material():
    model, frame, _ = _build()
    object.__setattr__(frame, "physical_validation_eligible", True)
    with pytest.raises(RetentionReleaseContractError, match="cannot be physical evidence"):
        build_retention_release_prework(model.authority, frame)

    _, frame2, _ = _build()
    object.__setattr__(frame2, "material_selection", "INVENTED_MATERIAL")
    with pytest.raises(RetentionReleaseContractError, match="unresolved structural-frame evidence boundary"):
        build_retention_release_prework(model.authority, frame2)


def test_post_construction_topology_corruption_fails_before_manifest_or_hash():
    _, _, contract = _build()
    object.__setattr__(contract.load_path_topology, "geometry_status", "PHYSICAL_PASS")
    with pytest.raises(RetentionReleaseContractError, match="cannot claim controlled retention geometry"):
        contract.manifest()
    with pytest.raises(RetentionReleaseContractError, match="cannot claim controlled retention geometry"):
        _ = contract.provenance_sha256


def test_post_construction_requirement_corruption_fails_before_manifest_or_hash():
    _, _, contract = _build()
    object.__setattr__(contract.requirements, "one_hand_wet_unpowered", False)
    with pytest.raises(RetentionReleaseContractError, match="frozen requirement"):
        contract.manifest()
    with pytest.raises(RetentionReleaseContractError, match="frozen requirement"):
        _ = contract.provenance_sha256


def test_post_construction_architecture_disposition_corruption_fails_before_consumption():
    _, _, contract = _build()
    bad = contract.architecture_options[0]
    object.__setattr__(bad, "disposition", "")
    with pytest.raises(RetentionReleaseContractError, match="disposition"):
        contract.manifest()


def test_contract_provenance_is_deterministic_and_covers_exact_manifest_payload():
    _, _, first = _build()
    _, _, second = _build()
    assert first.provenance_sha256 == second.provenance_sha256
    assert first.manifest() == second.manifest()
    payload = first.manifest(include_sha=False)
    import hashlib
    import json

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("ascii")
    assert hashlib.sha256(encoded).hexdigest() == first.provenance_sha256


def test_requirement_alias_types_and_invalid_status_promotions_fail_closed():
    with pytest.raises(RetentionReleaseContractError, match="numeric and not bool"):
        QuickReleaseRequirements(
            time_max_s=True,
            time_status="FROZEN_SAFETY_REQUIREMENT",
            force_target_N=(5.0, 12.0),
            force_status="VALIDATION_GATED",
            one_hand_wet_unpowered=True,
            one_hand_wet_unpowered_status="FROZEN_SAFETY_REQUIREMENT",
        )
    with pytest.raises(RetentionReleaseContractError, match="release-force classification drift"):
        QuickReleaseRequirements(
            time_max_s=2.0,
            time_status="FROZEN_SAFETY_REQUIREMENT",
            force_target_N=(5.0, 12.0),
            force_status="MEASURED_PASS",
            one_hand_wet_unpowered=True,
            one_hand_wet_unpowered_status="FROZEN_SAFETY_REQUIREMENT",
        )


def test_architecture_option_cannot_carry_empty_risks_or_duplicate_claims():
    with pytest.raises(RetentionReleaseContractError, match="material_risks"):
        ReleaseArchitectureOption(
            option_id="RET_TEST_OPTION",
            concept="test",
            strengths=("one",),
            material_risks=(),
            disposition="TEST_ONLY",
        )
    with pytest.raises(RetentionReleaseContractError, match="entries must be unique"):
        ReleaseArchitectureOption(
            option_id="RET_TEST_OPTION",
            concept="test",
            strengths=("duplicate", "duplicate"),
            material_risks=("risk",),
            disposition="TEST_ONLY",
        )
