from dataclasses import replace

import pytest

from masck_one.waste_fluid_accounting import WasteFluidAccountingError, build_authority_waste_fluid_budget
from masck_one.waste_fluid_capacity_reserve import (
    CapacityReservedServiceProfile,
    CartridgeCapacityReserve,
    screen_service_profile_with_capacity_reserve_evidence,
)
from masck_one.waste_fluid_profile import screen_service_profile


def test_service_profile_retains_exact_capacity_reserve_composition_identity():
    budget = build_authority_waste_fluid_budget()
    reserve = CartridgeCapacityReserve(fill_sensor_trip_mL=1.0, foam_allowance_mL=1.0)
    evidence = screen_service_profile_with_capacity_reserve_evidence(
        budget, reserve, prime_events_by_cycle=[1] * 6,
    )
    assert evidence.profile.capacity_reserve_mL == pytest.approx(2.0)
    assert evidence.profile.source_capacity_reserve_sha256 == reserve.evidence_sha256


def test_equal_total_different_reserve_composition_cannot_be_substituted():
    budget = build_authority_waste_fluid_budget()
    original = CartridgeCapacityReserve(fill_sensor_trip_mL=1.0, foam_allowance_mL=1.0)
    substituted = CartridgeCapacityReserve(manufacturing_tolerance_mL=2.0)
    evidence = screen_service_profile_with_capacity_reserve_evidence(
        budget, original, prime_events_by_cycle=[0] * 6,
    )
    assert original.total_mL == substituted.total_mL
    assert original.evidence_sha256 != substituted.evidence_sha256
    with pytest.raises(WasteFluidAccountingError, match="composition does not match"):
        CapacityReservedServiceProfile(substituted, evidence.profile)


def test_scalar_only_profile_cannot_masquerade_as_typed_reserve_evidence():
    budget = build_authority_waste_fluid_budget()
    reserve = CartridgeCapacityReserve(fill_sensor_trip_mL=2.0)
    scalar_profile = screen_service_profile(
        budget, prime_events_by_cycle=[0] * 6, capacity_reserve_mL=2.0,
    )
    assert scalar_profile.source_capacity_reserve_sha256 is None
    with pytest.raises(WasteFluidAccountingError, match="composition does not match"):
        CapacityReservedServiceProfile(reserve, scalar_profile)


def test_profile_rejects_mutated_reserve_provenance_digest():
    budget = build_authority_waste_fluid_budget()
    reserve = CartridgeCapacityReserve(fill_sensor_trip_mL=2.0)
    evidence = screen_service_profile_with_capacity_reserve_evidence(
        budget, reserve, prime_events_by_cycle=[0] * 6,
    )
    corrupted = replace(evidence.profile, source_capacity_reserve_sha256="0" * 64)
    with pytest.raises(WasteFluidAccountingError, match="composition does not match"):
        CapacityReservedServiceProfile(reserve, corrupted)


@pytest.mark.parametrize("digest", ["bad", "A" * 64, "g" * 64, 123, True])
def test_service_profile_rejects_noncanonical_reserve_provenance(digest):
    with pytest.raises(WasteFluidAccountingError, match="canonical lowercase SHA-256"):
        screen_service_profile(
            build_authority_waste_fluid_budget(),
            prime_events_by_cycle=[0],
            source_capacity_reserve_sha256=digest,
        )
