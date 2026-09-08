from dataclasses import replace

import pytest

import masck_one.dfm_part_family_bindings as dfm
from masck_one.authority import load_authority
from masck_one.dfm_part_family_bindings import (
    BASELINE_FAMILY_COUNT,
    BASELINE_PART_IDS,
    DfmPartFamilyBindingError,
    M_CONTROLLED_ENVELOPE,
    M_REALIZED_CENTERLINE,
    M_TOPOLOGY,
    RETIRE_ENVELOPE_SEMANTICS,
    RETIRE_TOPOLOGY,
    ROLE_CENTERLINE,
    ROLE_PACKAGE_REFERENCE,
    SOURCE_MAIN_SHA,
    build_dfm_part_family_producer_audit,
)
from masck_one.export import _dfm_part_family_producer_manifest


@pytest.fixture(scope="module")
def audit():
    return build_dfm_part_family_producer_audit()


def _binding(audit, part_id):
    return next(item for item in audit.bindings if item.part_id == part_id)


def test_audit_maps_all_47_stable_cell5_family_ids_to_current_main(audit):
    assert audit.source_main_sha == SOURCE_MAIN_SHA
    assert len(audit.bindings) == BASELINE_FAMILY_COUNT == 47
    assert tuple(item.part_id for item in audit.bindings) == BASELINE_PART_IDS
    assert audit.baseline_status == "UNMERGED_DONOR_TAXONOMY_ONLY_NOT_RELEASE_AUTHORITY"
    assert audit.physical_validation_eligible is False
    assert audit.production_validation_eligible is False
    assert audit.digital_mvp_part_architecture_ready is False


def test_realized_waste_centerlines_retire_obsolete_topology_only_entry(audit):
    route = _binding(audit, "MASCK_ONE-DFM-WASTE-BACKBONE-ROUTE-SET")
    assert route.baseline_maturity == "RELEASED_TOPOLOGY"
    assert route.current_maturity == M_REALIZED_CENTERLINE
    assert route.geometry_role == ROLE_CENTERLINE
    assert route.source_path == "src/masck_one/realized_waste_backbone.py"
    assert route.source_blob_sha == "6aa79d9a613e278f32da85b4654c0e35cc09b7ca"
    assert route.retirement_kind == RETIRE_TOPOLOGY
    assert route.physical_material_eligible is False


def test_cartridge_package_envelope_is_not_allowed_to_masquerade_as_body_material(audit):
    cartridge = _binding(audit, "MASCK_ONE-DFM-WASTE-CARTRIDGE-BODY")
    assert cartridge.current_maturity == M_CONTROLLED_ENVELOPE
    assert cartridge.geometry_role == ROLE_PACKAGE_REFERENCE
    assert cartridge.source_path == "src/masck_one/waste_cartridge_dfm.py"
    assert cartridge.source_blob_sha == "f9788cce30c14600c8a624509153596e46c1e478"
    assert cartridge.retirement_kind == RETIRE_ENVELOPE_SEMANTICS
    assert cartridge.physical_material_eligible is False
    assert audit.retired_baseline_entry_ids == (
        "MASCK_ONE-DFM-WASTE-BACKBONE-ROUTE-SET",
        "MASCK_ONE-DFM-WASTE-CARTRIDGE-BODY",
    )


def test_only_actual_released_shell_family_is_classified_as_part_material(audit):
    assert audit.physical_material_part_ids == ("MASCK_ONE-DFM-SHELL-PRIMARY",)
    for item in audit.bindings:
        if item.geometry_role != dfm.ROLE_PHYSICAL_MATERIAL:
            assert item.physical_material_eligible is False


def test_current_pump_topologies_are_successor_family_requirements_not_fake_realized_parts(audit):
    successor = {item.part_id: item for item in audit.successor_required_families}
    assert set(successor) == {
        "MASCK_ONE-DFM-WATER-PUMP-PACKAGE",
        "MASCK_ONE-DFM-CLEANSER-PUMP-PACKAGE",
        "MASCK_ONE-DFM-WASTE-PUMP-PACKAGE",
    }
    assert successor["MASCK_ONE-DFM-WATER-PUMP-PACKAGE"].source_path == "src/masck_one/fresh_pump_packaging.py"
    assert successor["MASCK_ONE-DFM-CLEANSER-PUMP-PACKAGE"].source_path == "src/masck_one/fresh_pump_packaging.py"
    assert successor["MASCK_ONE-DFM-WASTE-PUMP-PACKAGE"].source_path == "src/masck_one/waste_pump_architecture.py"
    assert {item.current_maturity for item in successor.values()} == {M_TOPOLOGY}
    assert audit.successor_architecture_required is True


def test_unmerged_and_legacy_donor_names_never_become_released_producer_sources(audit):
    source_paths = tuple(item.source_path for item in audit.bindings if item.source_path is not None)
    assert all("PR63" not in path and "PR64" not in path and "candidate" not in path for path in source_paths)
    assert all(path.startswith(("src/masck_one/", "config/")) for path in source_paths)


def test_reference_topology_and_centerline_roles_cannot_enter_physical_material(audit):
    candidate = _binding(audit, "MASCK_ONE-DFM-ACTUATOR-PACKAGE")
    with pytest.raises(DfmPartFamilyBindingError, match="reference/topology/centerline|only realized physical"):
        replace(candidate, physical_material_eligible=True)

    route = _binding(audit, "MASCK_ONE-DFM-WASTE-BACKBONE-ROUTE-SET")
    with pytest.raises(DfmPartFamilyBindingError, match="reference/topology/centerline|only realized physical"):
        replace(route, physical_material_eligible=True)


def test_wrong_source_blob_frame_authority_and_evidence_promotion_fail_closed(audit):
    shell = _binding(audit, "MASCK_ONE-DFM-SHELL-PRIMARY")
    with pytest.raises(DfmPartFamilyBindingError, match="exact released source"):
        replace(shell, source_blob_sha="0" * 40)
    with pytest.raises(DfmPartFamilyBindingError, match="canonical authority world frame"):
        replace(audit, coordinate_frame_id="MASCK_ONE_LOCAL_BAD")
    with pytest.raises(DfmPartFamilyBindingError, match="authority identity moved"):
        replace(audit, authority_blob_sha="0" * 40)
    with pytest.raises(DfmPartFamilyBindingError, match="evidence firewall"):
        replace(audit, evidence_status="PHYSICALLY_VALIDATED")
    with pytest.raises(DfmPartFamilyBindingError, match="exact bool"):
        replace(shell, physical_material_eligible=1)


def test_source_movement_invalidates_prior_audit(monkeypatch):
    original = dfm.SOURCE_GIT_BLOB_IDENTITIES
    bad = ((original[0][0], "0" * 40), *original[1:])
    monkeypatch.setattr(dfm, "SOURCE_GIT_BLOB_IDENTITIES", bad)
    with pytest.raises(DfmPartFamilyBindingError, match="source moved"):
        build_dfm_part_family_producer_audit()


def test_manifest_is_deterministic_and_release_helper_matches_audit(audit):
    second = build_dfm_part_family_producer_audit()
    assert second.manifest() == audit.manifest()
    assert second.manifest_sha256 == audit.manifest_sha256
    assert len(audit.manifest_sha256) == 64

    emitted = _dfm_part_family_producer_manifest(load_authority())
    assert emitted["manifest_sha256"] == audit.manifest_sha256
    assert emitted["baseline_family_count"] == 47
    assert emitted["digital_mvp_part_architecture_ready"] is False
