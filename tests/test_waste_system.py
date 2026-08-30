from dataclasses import replace

import pytest

from masck_one.waste_system import (
    CapacityContract,
    CartridgeEnvelope,
    EvidenceState,
    Orientation,
    OrientationCase,
    REQUIRED_MIXED_PHASE_FAULTS,
    WasteArchitecture,
)


MAIN_SHA = "cdcc6c5d7041a4b0d7594a7c8aa4fc58a8346207"


def cases():
    return {
        o: OrientationCase(
            orientation=o,
            pickup_assumption="pickup behavior requires physical characterization",
            air_location_assumption="free-air location is orientation dependent and unresolved",
            drainage_or_capillary_assumption="capillary/drainage behavior is validation gated",
            pump_inlet_assumption="mixed-phase inlet continuity is validation gated",
            cartridge_assumption="retention and vent behavior are validation gated",
            backflow_assumption="anti-backflow behavior requires physical verification",
        )
        for o in Orientation
    }


def architecture():
    return WasteArchitecture(
        source_main_sha=MAIN_SHA,
        authority_revision="2026-08-30-R1",
        envelope=CartridgeEnvelope(74.0, 36.0, 20.0, "ENGINEERING_BASELINE"),
        capacity=CapacityContract(35.0, "VALIDATION_GATED"),
        faults=REQUIRED_MIXED_PHASE_FAULTS,
        orientation_cases=cases(),
    )


def test_package_volume_is_not_usable_capacity():
    a = architecture()
    a.validate()
    assert a.envelope.bounding_volume_ml == pytest.approx(53.28)
    assert a.capacity.usable_capacity_ml is None
    assert a.capacity.retained_capacity_target_ml == 35.0


def test_unverified_numeric_usable_capacity_is_rejected():
    a = architecture()
    bad = replace(a, capacity=CapacityContract(35.0, "VALIDATION_GATED", usable_capacity_ml=36.0))
    with pytest.raises(ValueError, match="blocked until"):
        bad.validate()


def test_absorbent_volume_credit_is_rejected_without_physical_evidence():
    a = architecture()
    bad = replace(a, capacity=CapacityContract(35.0, "VALIDATION_GATED", credits_absorbent_media_volume=True))
    with pytest.raises(ValueError, match="absorbent/media"):
        bad.validate()


def test_missing_mixed_phase_fault_is_rejected():
    a = architecture()
    bad = replace(a, faults=frozenset(REQUIRED_MIXED_PHASE_FAULTS - {"foam_ingestion"}))
    with pytest.raises(ValueError, match="fault registry incomplete"):
        bad.validate()


def test_all_orientation_cases_are_required():
    a = architecture()
    reduced = dict(a.orientation_cases)
    del reduced[Orientation.FACE_DOWN]
    with pytest.raises(ValueError, match="orientation registry mismatch"):
        replace(a, orientation_cases=reduced).validate()


def test_orientation_cannot_claim_verified_without_evidence():
    a = architecture()
    changed = dict(a.orientation_cases)
    changed[Orientation.UPRIGHT] = replace(changed[Orientation.UPRIGHT], evidence_state=EvidenceState.VERIFIED)
    with pytest.raises(ValueError, match="requires evidence_id"):
        replace(a, orientation_cases=changed).validate()


def test_manifest_is_deterministic_and_sensitive_to_architecture():
    a = architecture()
    first = a.manifest_sha256()
    assert first == a.manifest_sha256()
    changed = replace(a, authority_revision="2026-08-30-R2")
    assert changed.manifest_sha256() != first


def test_stale_or_malformed_upstream_identity_is_rejected():
    with pytest.raises(ValueError, match="source_main_sha"):
        replace(architecture(), source_main_sha="stale-main").validate()
