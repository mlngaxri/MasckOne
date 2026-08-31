from dataclasses import replace

import pytest

from masck_one.authority import load_authority
from masck_one.cleanser_storage import (
    CompatibilityEvidence,
    CleanserStorageError,
    PORT_IDS,
    build_cleanser_storage_architecture,
)


def _evidence(**updates):
    values = {
        "evidence_id": "COMPAT-001",
        "revision": "A",
        "cleanser_identity": "CONTROLLED-FORMULATION-REV-A",
        "wetted_material_identity": "COUPON-MATERIAL-REV-B",
        "evidence_kind": "CONTROLLED_COUPON_TEST",
        "artifact_sha256": "a" * 64,
        "compatible": True,
    }
    values.update(updates)
    return CompatibilityEvidence(**values)


def test_storage_preserves_fluid_identity_authority_dose_and_unresolved_geometry():
    authority = load_authority()
    storage = build_cleanser_storage_architecture(authority)
    assert storage.nominal_cycle_dose_mL == 0.60
    assert tuple(port.port_id for port in storage.ports) == PORT_IDS
    assert {port.fluid_identity for port in storage.ports} == {"CLEANSER"}
    assert storage.storage_capacity_mL is None
    assert storage.dead_volume_mL is None
    assert storage.purge_volume_mL is None
    assert storage.physical_validation_eligible is False


def test_missing_compatibility_evidence_remains_blocked_and_deterministic():
    first = build_cleanser_storage_architecture(load_authority())
    second = build_cleanser_storage_architecture(load_authority())
    assert first.compatibility_evidence == ()
    assert "BLOCKED" in first.compatibility_status
    assert first.manifest() == second.manifest()
    assert first.architecture_sha256 == second.architecture_sha256


def test_evidence_is_hash_bound_but_requires_engineering_review():
    storage = build_cleanser_storage_architecture(load_authority())
    updated = storage.with_compatibility_evidence((_evidence(),))
    assert updated.compatibility_status == "EVIDENCE_ATTACHED_REQUIRES_ENGINEERING_REVIEW"
    assert updated.physical_validation_eligible is False
    assert updated.compatibility_evidence[0].artifact_sha256 == "a" * 64


@pytest.mark.parametrize("field", ["storage_capacity_mL", "dead_volume_mL", "purge_volume_mL"])
def test_capacity_dead_volume_and_purge_volume_cannot_be_invented(field):
    storage = build_cleanser_storage_architecture(load_authority())
    with pytest.raises(CleanserStorageError, match="cannot invent cleanser capacity"):
        replace(storage, **{field: 0.1})


def test_wrong_fluid_identity_and_uncontrolled_evidence_fail_closed():
    storage = build_cleanser_storage_architecture(load_authority())
    ports = list(storage.ports)
    with pytest.raises(CleanserStorageError, match="exact CLEANSER"):
        replace(ports[0], fluid_identity="FRESH_WATER")
    with pytest.raises(CleanserStorageError, match="controlled evidence kind"):
        _evidence(evidence_kind="INTERNET_OPINION")
    with pytest.raises(CleanserStorageError, match="canonical lowercase SHA-256"):
        _evidence(artifact_sha256="not-a-hash")


def test_hostile_type_aliases_and_duplicate_evidence_ids_are_rejected():
    class LyingStr(str):
        pass

    with pytest.raises(CleanserStorageError, match="exact built-in nonblank text"):
        _evidence(evidence_id=LyingStr("COMPAT-001"))
    storage = build_cleanser_storage_architecture(load_authority())
    with pytest.raises(CleanserStorageError, match="cannot repeat"):
        storage.with_compatibility_evidence((_evidence(), _evidence()))
    with pytest.raises(CleanserStorageError, match="exact boolean"):
        _evidence(compatible=1)


def test_authority_drift_and_evidence_promotion_are_rejected():
    authority = load_authority()
    storage = build_cleanser_storage_architecture(authority)
    with pytest.raises(CleanserStorageError, match="dose no longer matches"):
        replace(storage, nominal_cycle_dose_mL=0.61).validate_current_authority(authority)
    with pytest.raises(CleanserStorageError, match="cannot be physical validation"):
        replace(storage, physical_validation_eligible=True)


def test_authority_valid_water_only_cycle_can_carry_zero_cleanser_dose():
    storage = build_cleanser_storage_architecture(load_authority())
    assert replace(storage, nominal_cycle_dose_mL=0.0).nominal_cycle_dose_mL == 0.0
    with pytest.raises(CleanserStorageError, match="finite and nonnegative"):
        replace(storage, nominal_cycle_dose_mL=-0.01)
