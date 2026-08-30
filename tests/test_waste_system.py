from dataclasses import replace

import pytest

from masck_one.waste_system import (
    CapacityContract, CartridgeEnvelope, EvidenceReference, EvidenceState,
    Orientation, OrientationCase, REQUIRED_MIXED_PHASE_FAULTS, WasteArchitecture,
)

MAIN_SHA = "cdcc6c5d7041a4b0d7594a7c8aa4fc58a8346207"
AUTHORITY_REVISION = "2026-08-30-R1"
OTHER_VALID_SHA = "a" * 40


def cases():
    return {o: OrientationCase(
        orientation=o,
        pickup_assumption="pickup behavior requires physical characterization",
        air_location_assumption="free-air location is orientation dependent and unresolved",
        drainage_or_capillary_assumption="capillary/drainage behavior is validation gated",
        pump_inlet_assumption="mixed-phase inlet continuity is validation gated",
        cartridge_assumption="retention and vent behavior are validation gated",
        backflow_assumption="anti-backflow behavior requires physical verification",
    ) for o in Orientation}


def architecture():
    return WasteArchitecture(
        source_main_sha=MAIN_SHA,
        authority_revision=AUTHORITY_REVISION,
        envelope=CartridgeEnvelope(74.0, 36.0, 20.0, "ENGINEERING_BASELINE"),
        capacity=CapacityContract(35.0, "VALIDATION_GATED"),
        faults=REQUIRED_MIXED_PHASE_FAULTS,
        orientation_cases=cases(),
    )


def test_package_volume_is_not_usable_capacity():
    a = architecture(); a.validate()
    assert a.envelope.bounding_volume_ml == pytest.approx(53.28)
    assert a.capacity.usable_capacity_ml is None
    assert a.capacity.retained_capacity_target_ml == 35.0


def test_unverified_numeric_usable_capacity_is_rejected():
    bad = replace(architecture(), capacity=CapacityContract(35.0, "VALIDATION_GATED", usable_capacity_ml=36.0))
    with pytest.raises(ValueError, match="blocked until"):
        bad.validate()


def test_absorbent_volume_credit_is_rejected_without_physical_evidence():
    bad = replace(architecture(), capacity=CapacityContract(35.0, "VALIDATION_GATED", credits_absorbent_media_volume=True))
    with pytest.raises(ValueError, match="absorbent/media"):
        bad.validate()


def test_missing_mixed_phase_fault_is_rejected():
    bad = replace(architecture(), faults=frozenset(REQUIRED_MIXED_PHASE_FAULTS - {"foam_ingestion"}))
    with pytest.raises(ValueError, match="fault registry incomplete"):
        bad.validate()


def test_all_orientation_cases_are_required():
    a = architecture(); reduced = dict(a.orientation_cases); del reduced[Orientation.FACE_DOWN]
    with pytest.raises(ValueError, match="orientation registry mismatch"):
        replace(a, orientation_cases=reduced).validate()


def test_orientation_cannot_claim_verified_without_cryptographic_evidence():
    a = architecture(); changed = dict(a.orientation_cases)
    changed[Orientation.UPRIGHT] = replace(changed[Orientation.UPRIGHT], evidence_state=EvidenceState.VERIFIED)
    with pytest.raises(ValueError, match="cryptographic evidence"):
        replace(a, orientation_cases=changed).validate()


def test_arbitrary_evidence_text_cannot_promote_capacity():
    bad_evidence = EvidenceReference("bench-run-7", "r1", "not-a-hash")
    bad = replace(architecture(), capacity=CapacityContract(
        35.0, "VALIDATION_GATED", usable_capacity_ml=36.0,
        usable_capacity_state=EvidenceState.VERIFIED, evidence=bad_evidence))
    with pytest.raises(ValueError, match="artifact_sha256"):
        bad.validate()


def test_verified_evidence_identity_is_manifest_bound():
    evidence = EvidenceReference("capacity-rig-7", "r2", "b" * 64)
    verified = replace(architecture(), capacity=CapacityContract(
        35.0, "VALIDATION_GATED", usable_capacity_ml=36.0,
        usable_capacity_state=EvidenceState.VERIFIED, evidence=evidence))
    first = verified.manifest_sha256()
    changed_evidence = replace(evidence, artifact_sha256="c" * 64)
    changed = replace(verified, capacity=replace(verified.capacity, evidence=changed_evidence))
    assert changed.manifest_sha256() != first


def test_manifest_is_deterministic_and_sensitive_to_architecture():
    a = architecture(); first = a.manifest_sha256()
    assert first == a.manifest_sha256()
    assert replace(a, authority_revision="2026-08-30-R2").manifest_sha256() != first


def test_malformed_upstream_identity_is_rejected_intrinsically():
    with pytest.raises(ValueError, match="source_main_sha"):
        replace(architecture(), source_main_sha="stale-main").validate()


def test_valid_but_stale_upstream_sha_is_rejected_at_release():
    historical = replace(architecture(), source_main_sha=OTHER_VALID_SHA)
    historical.validate()  # historical provenance remains representable
    with pytest.raises(ValueError, match="stale for the expected upstream main SHA"):
        historical.validate_current_release(expected_main_sha=MAIN_SHA, expected_authority_revision=AUTHORITY_REVISION)


def test_valid_but_stale_authority_revision_is_rejected_at_release():
    historical = replace(architecture(), authority_revision="2026-08-29-R9")
    historical.validate()
    with pytest.raises(ValueError, match="stale for the expected authority revision"):
        historical.validate_current_release(expected_main_sha=MAIN_SHA, expected_authority_revision=AUTHORITY_REVISION)


def test_current_release_requires_exact_expected_identity():
    architecture().validate_current_release(expected_main_sha=MAIN_SHA, expected_authority_revision=AUTHORITY_REVISION)
    with pytest.raises(ValueError, match="expected_main_sha"):
        architecture().validate_current_release(expected_main_sha="main", expected_authority_revision=AUTHORITY_REVISION)
