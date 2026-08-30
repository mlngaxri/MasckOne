from dataclasses import replace

import pytest

from masck_one.authority import load_authority
from masck_one.cleanser_storage import (
    CompatibilityEvidence,
    CleanserStorageError,
    PORT_IDS,
    build_cleanser_storage_architecture,
)


def test_cleanser_storage_preserves_separate_fluid_identity_and_authority_dose():
    authority = load_authority()
    storage = build_cleanser_storage_architecture(authority)
    assert storage.nominal_cycle_dose_mL == 0.60
    assert tuple(port.port_id for port in storage.ports) == PORT_IDS
    assert {port.fluid_identity for port in storage.ports} == {"CLEANSER"}
    assert storage.storage_capacity_mL is None
    assert storage.dead_volume_mL is None
    assert storage.purge_volume_mL is None
    assert storage.physical_validation_eligible is False


def test_missing_compatibility_evidence_remains_blocked():
    storage = build_cleanser_storage_architecture(load_authority())
    assert storage.compatibility_evidence == ()
    assert "BLOCKED" in storage.compatibility_status


def test_compatibility_evidence_is_provenance_controlled_but_not_auto_promoted():
    storage = build_cleanser_storage_architecture(load_authority())
    evidence = CompatibilityEvidence(
        evidence_id="COMPAT-001",
        cleanser_identity="CONTROLLED-FORMULATION-REV-A",
        wetted_material_identity="COUPON-MATERIAL-REV-B",
        evidence_kind="CONTROLLED_COUPON_TEST",
        source_uri="evidence://compat/COMPAT-001",
        compatible=True,
    )
    updated = storage.with_compatibility_evidence((evidence,))
    assert updated.compatibility_status == "EVIDENCE_ATTACHED_REQUIRES_ENGINEERING_REVIEW"
    assert updated.physical_validation_eligible is False


def test_capacity_dead_volume_and_purge_volume_cannot_be_invented_in_iteration21():
    storage = build_cleanser_storage_architecture(load_authority())
    with pytest.raises(CleanserStorageError, match="cannot invent cleanser capacity"):
        replace(storage, storage_capacity_mL=10.0)
    with pytest.raises(CleanserStorageError, match="cannot invent cleanser capacity"):
        replace(storage, dead_volume_mL=0.1)
    with pytest.raises(CleanserStorageError, match="cannot invent cleanser capacity"):
        replace(storage, purge_volume_mL=0.2)


def test_wrong_fluid_identity_and_uncontrolled_evidence_kind_fail_closed():
    storage = build_cleanser_storage_architecture(load_authority())
    bad_ports = list(storage.ports)
    bad_ports[0] = replace(bad_ports[0], fluid_identity="FRESH_WATER")
    with pytest.raises(CleanserStorageError, match="retain CLEANSER"):
        replace(storage, ports=tuple(bad_ports))
    with pytest.raises(CleanserStorageError, match="controlled evidence kind"):
        CompatibilityEvidence(
            evidence_id="BAD",
            cleanser_identity="FORMULA",
            wetted_material_identity="MATERIAL",
            evidence_kind="INTERNET_OPINION",
            source_uri="evidence://bad",
            compatible=True,
        )


def test_authority_drift_and_evidence_promotion_are_rejected():
    authority = load_authority()
    storage = build_cleanser_storage_architecture(authority)
    stale = replace(storage, nominal_cycle_dose_mL=0.61)
    with pytest.raises(CleanserStorageError, match="dose no longer matches"):
        stale.validate_current_authority(authority)
    with pytest.raises(CleanserStorageError, match="cannot be physical validation"):
        replace(storage, physical_validation_eligible=True)
