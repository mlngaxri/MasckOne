from dataclasses import replace
import math

import pytest

import masck_one.fluid_routing_dfm as dfm
from masck_one.fluid_routing_dfm import (
    EVIDENCE_STATUS,
    REQUIREMENT_IDS,
    FluidRoutingDfmError,
    build_fluid_routing_dfm_audit,
)


@pytest.fixture(scope="module")
def audit():
    return build_fluid_routing_dfm_audit()


def test_released_routing_maturity_is_fail_closed_and_source_bound(audit):
    assert audit.fresh_route_count == 4
    assert audit.realized_fresh_route_count == 0
    assert audit.manifold_branch_count == 2
    assert audit.realized_manifold_branch_count == 0
    assert audit.distribution_groove_count == 24
    assert audit.dimensioned_distribution_groove_count == 0
    assert audit.selected_connector_standard_count == 0
    assert audit.realized_waste_route_count == 3
    assert audit.realized_waste_min_bend_radius_mm == pytest.approx(8.0)
    assert audit.selected_waste_min_bend_requirement_mm is None
    assert audit.released_waste_geometric_dead_volume_mL == pytest.approx(0.29068329701259293)
    assert not audit.digital_mvp_fluid_routing_dfm_ready
    assert not audit.production_moldability_eligible
    assert not audit.physical_validation_eligible
    assert audit.evidence_status == EVIDENCE_STATUS
    audit.validate_current_sources()


def test_only_material_manufacturing_blockers_are_recorded(audit):
    assert tuple(item.requirement_id for item in audit.requirements) == REQUIREMENT_IDS
    assert len(audit.requirements) == 7
    assert all(item.severity == "P0" for item in audit.requirements)
    assert all(item.owner == "CELL4_WET_SYSTEMS" for item in audit.requirements)
    manifest = audit.manifest()
    assert manifest["release_blocker_count"] == 7
    assert manifest["manufacturing_rules"]["rule_role"] == (
        "RELEASED_DESIGN_RULES_NOT_PRODUCTION_PROCESS_CAPABILITY"
    )


def test_manifest_is_deterministic_and_revalidates_nested_mutation(audit):
    second = build_fluid_routing_dfm_audit()
    assert second.manifest() == audit.manifest()
    assert second.manifest_sha256 == audit.manifest_sha256
    assert len(audit.manifest_sha256) == 64

    object.__setattr__(second.requirements[0], "severity", "P1")
    with pytest.raises(FluidRoutingDfmError, match="must remain P0"):
        second.validate_current_sources()


def test_bool_nonfinite_and_readiness_promotion_fail_closed(audit):
    with pytest.raises(FluidRoutingDfmError, match="exact integer"):
        replace(audit, fresh_route_count=True).validate()
    with pytest.raises(FluidRoutingDfmError, match="finite"):
        replace(audit, realized_waste_min_bend_radius_mm=math.nan).validate()
    with pytest.raises(FluidRoutingDfmError, match="not digitally DFM-ready"):
        replace(audit, digital_mvp_fluid_routing_dfm_ready=True).validate()
    with pytest.raises(FluidRoutingDfmError, match="physical validation"):
        replace(audit, physical_validation_eligible=True).validate()


def test_requirement_order_duplicate_and_evidence_spoof_fail_closed(audit):
    with pytest.raises(FluidRoutingDfmError, match="identity or order"):
        replace(audit, requirements=tuple(reversed(audit.requirements))).validate()

    duplicated = audit.requirements[:-1] + (audit.requirements[0],)
    with pytest.raises(FluidRoutingDfmError, match="identity or order"):
        replace(audit, requirements=duplicated).validate()

    spoofed = replace(audit.requirements[0], evidence_status="PHYSICALLY_VERIFIED")
    bad_requirements = (spoofed,) + audit.requirements[1:]
    with pytest.raises(FluidRoutingDfmError, match="cannot imply physical validation"):
        replace(audit, requirements=bad_requirements).validate()


def test_stale_digest_and_source_blob_identity_fail_closed(audit, monkeypatch):
    stale = replace(audit, source_routing_closure_sha256="0" * 64)
    with pytest.raises(FluidRoutingDfmError, match="stale for current released routing maturity"):
        stale.validate_current_sources()

    monkeypatch.setattr(
        dfm,
        "SOURCE_GIT_BLOB_IDENTITIES",
        (("config/masck_one_authority.yaml", "0" * 40),),
    )
    with pytest.raises(FluidRoutingDfmError, match="source moved"):
        audit.validate_current_sources()
