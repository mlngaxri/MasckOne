from dataclasses import replace
import json
import math

import pytest

from masck_one.whole_product_dfm import (
    AUTHORITY_REVISION,
    DFM_SCHEMA,
    H_DRY,
    MATURITY_RELEASED_ENVELOPE,
    MATURITY_RELEASED_GEOMETRY,
    MATURITY_UNRESOLVED_REQUIRED,
    PATH_CLOSED,
    PATH_REQUIRED,
    ROLE_SEAL,
    SOURCE_MAIN_SHA,
    CandidateBinding,
    DfmArchitectureError,
    ManufacturingRules,
    WholeProductDfmArchitecture,
    build_whole_product_dfm_architecture,
)


def _by_id(architecture):
    return {part.part_id: part for part in architecture.parts}


def test_whole_product_dfm_contract_covers_required_part_splits_and_authority_rules():
    architecture = build_whole_product_dfm_architecture()
    parts = _by_id(architecture)

    assert architecture.schema == DFM_SCHEMA
    assert architecture.source_main_sha == SOURCE_MAIN_SHA
    assert architecture.authority_revision == AUTHORITY_REVISION
    assert architecture.rules.mold_draft_nominal_deg == 1.0
    assert (
        architecture.rules.rib_thickness_ratio_min,
        architecture.rules.rib_thickness_ratio_max,
    ) == (0.40, 0.60)
    assert architecture.rules.visible_seam_gap_mm == 0.40
    assert architecture.rules.visible_seam_tolerance_mm == 0.15
    assert architecture.rules.flush_mismatch_max_mm == 0.15

    required = {
        "MASCK_ONE-DFM-SHELL-PRIMARY",
        "MASCK_ONE-DFM-REACTION-FRAME",
        "MASCK_ONE-DFM-FACIAL-INTERFACE-CARRIER",
        "MASCK_ONE-DFM-RETENTION-HALO-LEFT",
        "MASCK_ONE-DFM-RETENTION-HALO-RIGHT-TONGUE",
        "MASCK_ONE-DFM-LATCH-SOCKET-GUIDE",
        "MASCK_ONE-DFM-LATCH-SLIDER-GRIP",
        "MASCK_ONE-DFM-LATCH-GUIDE-CLOSURE",
        "MASCK_ONE-DFM-ACTUATOR-CARRIER",
        "MASCK_ONE-DFM-ACTUATOR-REACTION-SHOE",
        "MASCK_ONE-DFM-WATER-RESERVOIR-BODY",
        "MASCK_ONE-DFM-WATER-RESERVOIR-LID",
        "MASCK_ONE-DFM-WATER-RESERVOIR-LID-SEAL",
        "MASCK_ONE-DFM-WASTE-CARTRIDGE-BODY",
        "MASCK_ONE-DFM-WASTE-CARTRIDGE-SEAL-KEY",
        "MASCK_ONE-DFM-FRESH-MANIFOLD-BODY",
        "MASCK_ONE-DFM-FRESH-ROUTE-SET",
        "MASCK_ONE-DFM-WASTE-BACKBONE-ROUTE-SET",
        "MASCK_ONE-DFM-DRY-BAY-HOUSING",
        "MASCK_ONE-DFM-DRY-BAY-COVER-SEAL",
        "MASCK_ONE-DFM-HARNESS-SET",
        "MASCK_ONE-DFM-WET-DRY-BULKHEAD",
        "MASCK_ONE-DFM-HMI-CONTROL-MEMBRANE",
        "MASCK_ONE-DFM-REAR-SERVICE-COVER",
    }
    assert required.issubset(parts)
    assert parts["MASCK_ONE-DFM-ACTUATOR-PACKAGE"].quantity == 4
    assert parts["MASCK_ONE-DFM-ACTUATOR-CARRIER"].quantity == 4
    assert parts["MASCK_ONE-DFM-ACTUATOR-REACTION-SHOE"].quantity == 4
    assert parts["MASCK_ONE-DFM-HMI-CONTROL-CAP-SET"].quantity == 4


def test_released_main_maturity_is_not_promoted_by_unmerged_candidates():
    architecture = build_whole_product_dfm_architecture()
    parts = _by_id(architecture)

    assert parts["MASCK_ONE-DFM-SHELL-PRIMARY"].maturity == MATURITY_RELEASED_GEOMETRY
    assert parts["MASCK_ONE-DFM-ACTUATOR-PACKAGE"].maturity == MATURITY_RELEASED_ENVELOPE
    assert parts["MASCK_ONE-DFM-WATER-RESERVOIR-BODY"].maturity == MATURITY_UNRESOLVED_REQUIRED
    assert parts["MASCK_ONE-DFM-LATCH-SOCKET-GUIDE"].maturity == MATURITY_UNRESOLVED_REQUIRED
    assert parts["MASCK_ONE-DFM-DRY-BAY-HOUSING"].maturity == MATURITY_UNRESOLVED_REQUIRED

    bindings = {item.pr_number: item for item in architecture.observed_candidates}
    assert bindings[68].head_sha == "f4d366ab4ee819cc6be79186c5cc77ef89519fa9"
    assert bindings[70].head_sha == "44dbd355858e93db45c6988f66774259e2dc3ed5"
    assert bindings[71].head_sha == "f4798831e73f9cc190a200e50abc4b7ab93b75be"
    assert bindings[75].head_sha == "08b5769753858cb457f0117bf25498875072d812"
    assert all(item.authority_status == "OBSERVED_UNMERGED_CANDIDATE_NOT_RELEASE_AUTHORITY" for item in bindings.values())


def test_user_service_items_fail_closed_until_real_trajectories_exist():
    architecture = build_whole_product_dfm_architecture()
    blockers = set(architecture.user_service_blocker_ids)
    assert "MASCK_ONE-DFM-WATER-RESERVOIR-BODY" in blockers
    assert "MASCK_ONE-DFM-WATER-RESERVOIR-LID" in blockers
    assert "MASCK_ONE-DFM-WASTE-CARTRIDGE-BODY" in blockers
    assert "MASCK_ONE-DFM-WASTE-CARTRIDGE-CLOSURE" in blockers
    assert architecture.digital_mvp_part_architecture_ready is False


def test_assembly_dependency_graph_is_strictly_forward_only():
    architecture = build_whole_product_dfm_architecture()
    by_id = _by_id(architecture)
    for part in architecture.parts:
        for dependency in part.prerequisites:
            assert by_id[dependency].assembly_stage < part.assembly_stage

    target = by_id["MASCK_ONE-DFM-WATER-RESERVOIR-LID"]
    bad = replace(target, prerequisites=("MASCK_ONE-DFM-REAR-SERVICE-COVER",))
    changed = tuple(bad if part.part_id == target.part_id else part for part in architecture.parts)
    with pytest.raises(DfmArchitectureError, match="earlier stage"):
        replace(architecture, parts=changed)


def test_service_and_seal_semantics_reject_category_coercion():
    architecture = build_whole_product_dfm_architecture()
    by_id = _by_id(architecture)

    seal = by_id["MASCK_ONE-DFM-WATER-RESERVOIR-LID-SEAL"]
    assert seal.role == ROLE_SEAL
    with pytest.raises(DfmArchitectureError, match="seal part"):
        replace(seal, hygiene_class=H_DRY)

    body = by_id["MASCK_ONE-DFM-WATER-RESERVOIR-BODY"]
    with pytest.raises(DfmArchitectureError, match="quantity"):
        replace(body, quantity=True)
    with pytest.raises(DfmArchitectureError, match="service-path state"):
        replace(body, service_path_status="true")


def test_nonfinite_manufacturing_values_and_stale_candidate_ids_fail_closed():
    architecture = build_whole_product_dfm_architecture()
    rules = architecture.rules

    with pytest.raises(DfmArchitectureError, match="finite"):
        replace(rules, visible_seam_gap_mm=math.nan)

    with pytest.raises(DfmArchitectureError, match="canonical"):
        CandidateBinding(75, "not-a-sha", architecture.observed_candidates[-1].owner, ("MASCK_ONE-DFM-WATER-RESERVOIR-BODY",))

    bad_binding = CandidateBinding(
        999,
        "0" * 40,
        architecture.observed_candidates[-1].owner,
        ("MASCK_ONE-DFM-DOES-NOT-EXIST",),
    )
    with pytest.raises(DfmArchitectureError, match="unknown DFM part"):
        replace(architecture, observed_candidates=architecture.observed_candidates + (bad_binding,))


def test_unknown_prerequisite_and_duplicate_part_id_fail_closed():
    architecture = build_whole_product_dfm_architecture()
    by_id = _by_id(architecture)
    target = by_id["MASCK_ONE-DFM-HMI-STATUS-WINDOW"]
    bad = replace(target, prerequisites=("MASCK_ONE-DFM-NOT-A-PART",))
    changed = tuple(bad if part.part_id == target.part_id else part for part in architecture.parts)
    with pytest.raises(DfmArchitectureError, match="unknown assembly prerequisite"):
        replace(architecture, parts=changed)

    duplicate = tuple(sorted(architecture.parts + (architecture.parts[0],), key=lambda part: part.part_id))
    with pytest.raises(DfmArchitectureError, match="globally unique"):
        replace(architecture, parts=duplicate)


def test_manifest_is_deterministic_and_preserves_evidence_firewall():
    first = build_whole_product_dfm_architecture()
    second = build_whole_product_dfm_architecture()
    first_manifest = first.manifest()
    second_manifest = second.manifest()

    assert json.dumps(first_manifest, sort_keys=True, allow_nan=False) == json.dumps(
        second_manifest, sort_keys=True, allow_nan=False
    )
    assert first_manifest["dfm_architecture_sha256"] == second_manifest["dfm_architecture_sha256"]
    assert first.physical_validation_eligible is False
    assert first.production_validation_eligible is False
    assert "NOT_TOOLING_SUPPLIER" in first.evidence_status


def test_service_path_cannot_be_closed_for_nonuser_fixed_part():
    architecture = build_whole_product_dfm_architecture()
    shell = _by_id(architecture)["MASCK_ONE-DFM-SHELL-PRIMARY"]
    with pytest.raises(DfmArchitectureError, match="nonuser fixed"):
        replace(shell, service_path_status=PATH_CLOSED)


def test_manufacturing_rules_reject_bool_and_reversed_rib_range():
    architecture = build_whole_product_dfm_architecture()
    rules = architecture.rules
    with pytest.raises(DfmArchitectureError, match="numeric scalar"):
        replace(rules, mold_draft_nominal_deg=True)
    with pytest.raises(DfmArchitectureError, match="strictly increasing"):
        replace(rules, rib_thickness_ratio_min=0.7, rib_thickness_ratio_max=0.6)
