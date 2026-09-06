from dataclasses import replace

import pytest

import masck_one.release_material_truth_audit as audit_module
from masck_one.release_material_truth_audit import (
    BLOCKED_DISPOSITION,
    EXPECTED_CURRENT_INCLUDED_NAMES,
    EXPECTED_NONPHYSICAL_INCLUDED_NAMES,
    ReleaseMaterialTruthError,
    build_current_main_release_material_truth_audit,
)


def test_current_main_development_assembly_is_explicitly_blocked():
    audit = build_current_main_release_material_truth_audit()
    assert audit.included_component_names == EXPECTED_CURRENT_INCLUDED_NAMES
    assert audit.physical_material_names == ("rigid_shell",)
    assert audit.nonphysical_included_names == EXPECTED_NONPHYSICAL_INCLUDED_NAMES
    assert len(audit.nonphysical_included_names) == 7
    assert audit.included_realized_solid_count > audit.physical_realized_solid_count
    assert audit.nonphysical_realized_solid_count > 0
    assert audit.release_disposition == BLOCKED_DISPOSITION
    assert audit.digital_mvp_release_eligible is False
    assert audit.physical_validation_eligible is False


def test_current_false_maturity_membership_is_exact():
    audit = build_current_main_release_material_truth_audit()
    assert audit.nonphysical_included_names == (
        "nasal_lobe_membrane_reference",
        "actuator_envelope_1",
        "actuator_envelope_2",
        "actuator_envelope_3",
        "actuator_envelope_4",
        "water_reservoir_envelope",
        "battery_reference_envelope",
    )
    assert "waste_cartridge_envelope" not in audit.included_component_names
    assert "rigid_shell" not in audit.nonphysical_included_names


def test_manifest_is_deterministic_and_balances_realized_solids():
    first = build_current_main_release_material_truth_audit()
    second = build_current_main_release_material_truth_audit()
    assert first.manifest() == second.manifest()
    assert first.manifest_sha256 == second.manifest_sha256
    assert len(first.manifest_sha256) == 64
    assert first.included_realized_solid_count == (
        first.physical_realized_solid_count + first.nonphysical_realized_solid_count
    )


def test_release_and_physical_evidence_promotion_fail_closed():
    audit = build_current_main_release_material_truth_audit()
    with pytest.raises(ReleaseMaterialTruthError, match="cannot be digitally release-eligible"):
        replace(audit, digital_mvp_release_eligible=True).validate()
    with pytest.raises(ReleaseMaterialTruthError, match="cannot become physical evidence"):
        replace(audit, physical_validation_eligible=True).validate()
    with pytest.raises(ReleaseMaterialTruthError, match="cannot be silently cleared"):
        replace(audit, release_disposition="PASS").validate()


def test_source_movement_invalidates_prior_audit(monkeypatch):
    audit = build_current_main_release_material_truth_audit()
    monkeypatch.setattr(
        audit_module,
        "SOURCE_GIT_BLOB_IDENTITIES",
        (("src/masck_one/export.py", "0" * 40),),
    )
    with pytest.raises(ReleaseMaterialTruthError, match="source moved"):
        audit_module._require_sources_current()
    audit.validate()


def test_membership_or_role_drift_requires_fresh_hostile_review():
    audit = build_current_main_release_material_truth_audit()
    with pytest.raises(ReleaseMaterialTruthError, match="membership moved"):
        replace(audit, included_component_names=tuple(reversed(audit.included_component_names))).validate()
    with pytest.raises(ReleaseMaterialTruthError, match="contamination set moved"):
        replace(audit, nonphysical_included_names=audit.nonphysical_included_names[:-1]).validate()
