from dataclasses import replace

import pytest

from masck_one.waste_system import (
    CapacityContract, CartridgeEnvelope, EvidenceReference, EvidenceState,
    Orientation, OrientationCase, REQUIRED_MIXED_PHASE_FAULTS, REQUIRED_ORIENTATIONS,
    WasteArchitecture,
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


def test_verified_usable_capacity_cannot_be_below_retained_target():
    evidence = EvidenceReference("capacity-rig-under-target", "r1", "9" * 64)
    bad = replace(architecture(), capacity=CapacityContract(
        35.0, "VALIDATION_GATED", usable_capacity_ml=34.999,
        usable_capacity_state=EvidenceState.VERIFIED, evidence=evidence))
    with pytest.raises(ValueError, match="below the retained capacity target"):
        bad.validate()


def test_verified_usable_capacity_cannot_exceed_external_bounding_volume():
    evidence = EvidenceReference("capacity-rig-overvolume", "r1", "d" * 64)
    bad = replace(architecture(), capacity=CapacityContract(
        35.0, "VALIDATION_GATED", usable_capacity_ml=53.280001,
        usable_capacity_state=EvidenceState.VERIFIED, evidence=evidence))
    with pytest.raises(ValueError, match="usable capacity exceeds"):
        bad.validate()


def test_retained_capacity_target_cannot_exceed_external_bounding_volume():
    bad = replace(architecture(), capacity=CapacityContract(53.280001, "VALIDATION_GATED"))
    with pytest.raises(ValueError, match="retained capacity target exceeds"):
        bad.validate()


def test_capacity_equal_to_external_bound_is_only_geometrically_permitted_not_verified():
    evidence = EvidenceReference("capacity-rig-boundary", "r1", "e" * 64)
    boundary = replace(architecture(), capacity=CapacityContract(
        53.28, "VALIDATION_GATED", usable_capacity_ml=53.28,
        usable_capacity_state=EvidenceState.VERIFIED, evidence=evidence))
    boundary.validate()
    assert boundary.envelope.bounding_volume_ml == pytest.approx(53.28)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
@pytest.mark.parametrize("axis", ["x_mm", "y_mm", "z_mm"])
def test_nonfinite_cartridge_envelope_dimension_is_rejected(axis, value):
    a = architecture()
    bad_envelope = replace(a.envelope, **{axis: value})
    with pytest.raises(ValueError, match="must be finite"):
        replace(a, envelope=bad_envelope).validate()


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_retained_capacity_target_is_rejected(value):
    bad = replace(architecture(), capacity=CapacityContract(value, "VALIDATION_GATED"))
    with pytest.raises(ValueError, match="retained capacity target must be finite"):
        bad.validate()


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_verified_usable_capacity_is_rejected(value):
    evidence = EvidenceReference("capacity-rig-nonfinite", "r1", "f" * 64)
    bad = replace(architecture(), capacity=CapacityContract(
        35.0, "VALIDATION_GATED", usable_capacity_ml=value,
        usable_capacity_state=EvidenceState.VERIFIED, evidence=evidence))
    with pytest.raises(ValueError, match="usable capacity must be finite"):
        bad.validate()


def test_boolean_capacity_cannot_alias_numeric_volume():
    bad = replace(architecture(), capacity=CapacityContract(True, "VALIDATION_GATED"))
    with pytest.raises(ValueError, match="finite numeric"):
        bad.validate()


def test_blank_envelope_and_capacity_statuses_are_rejected():
    a = architecture()
    with pytest.raises(ValueError, match="authority_status"):
        replace(a, envelope=replace(a.envelope, authority_status=" ")).validate()
    with pytest.raises(ValueError, match="target status"):
        replace(a, capacity=replace(a.capacity, target_status=" ")).validate()


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
    historical.validate()
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


def test_orientation_mapping_is_snapshotted_against_external_mutation():
    source_cases = cases()
    a = WasteArchitecture(
        source_main_sha=MAIN_SHA,
        authority_revision=AUTHORITY_REVISION,
        envelope=CartridgeEnvelope(74.0, 36.0, 20.0, "ENGINEERING_BASELINE"),
        capacity=CapacityContract(35.0, "VALIDATION_GATED"),
        faults=REQUIRED_MIXED_PHASE_FAULTS,
        orientation_cases=source_cases,
    )
    a.validate()
    identity = a.manifest_sha256()
    source_cases.pop(Orientation.FACE_DOWN)
    source_cases[Orientation.UPRIGHT] = replace(source_cases[Orientation.UPRIGHT], pickup_assumption="tampered")
    a.validate()
    assert len(a.orientation_cases) == len(REQUIRED_ORIENTATIONS)
    assert a.manifest_sha256() == identity


@pytest.mark.parametrize("bad_state", ["UNRESOLVED", "VERIFIED", None, 0, False])
def test_capacity_evidence_state_requires_enum_instance(bad_state):
    bad = replace(architecture(), capacity=CapacityContract(
        35.0, "VALIDATION_GATED", usable_capacity_state=bad_state
    ))
    with pytest.raises(ValueError, match="EvidenceState"):
        bad.validate()


@pytest.mark.parametrize("bad_state", ["VALIDATION_GATED", "VERIFIED", None, 0, False])
def test_orientation_evidence_state_requires_enum_instance(bad_state):
    a = architecture()
    changed = dict(a.orientation_cases)
    changed[Orientation.UPRIGHT] = replace(changed[Orientation.UPRIGHT], evidence_state=bad_state)
    with pytest.raises(ValueError, match="EvidenceState"):
        replace(a, orientation_cases=changed).validate()


def test_mutable_fault_registry_is_rejected():
    with pytest.raises(ValueError, match="immutable frozenset"):
        replace(architecture(), faults=set(REQUIRED_MIXED_PHASE_FAULTS)).validate()


def test_false_like_absorbent_credit_alias_is_rejected():
    bad = replace(architecture(), capacity=replace(architecture().capacity, credits_absorbent_media_volume=0))
    with pytest.raises(ValueError, match="literal bool"):
        bad.validate()


def test_malformed_evidence_text_fails_closed_with_value_error():
    evidence = EvidenceReference(None, "r1", "a" * 64)
    with pytest.raises(ValueError, match="evidence id"):
        evidence.validate()
