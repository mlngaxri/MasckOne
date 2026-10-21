from dataclasses import replace

import pytest

from masck_one.waste_fluid_accounting import WasteFluidAccountingError, build_authority_waste_fluid_budget
from masck_one.waste_fluid_capacity_reserve import (
    CapacityReservedServiceProfile,
    CartridgeCapacityReserve,
    screen_service_profile_with_capacity_reserve_evidence,
)
from masck_one.waste_fluid_capacity_sizing_reserve import (
    CapacityReservedServiceSizing,
    derive_capacity_reserved_service_sizing,
)


def _evidence(reserve):
    return screen_service_profile_with_capacity_reserve_evidence(
        build_authority_waste_fluid_budget(), reserve,
        prime_events_by_cycle=(1, 1, 1, 1, 1, 1), target_cycles=6,
    )


def test_typed_reserve_provenance_survives_capacity_sizing():
    reserve = CartridgeCapacityReserve(fill_sensor_trip_mL=1.0, foam_allowance_mL=0.75, manufacturing_tolerance_mL=0.25)
    result = derive_capacity_reserved_service_sizing(_evidence(reserve))
    assert result.reserve is reserve
    assert result.sizing.source.source_capacity_reserve_sha256 == reserve.evidence_sha256
    assert result.sizing.capacity_reserve_mL == pytest.approx(2.0)


def test_equal_total_different_reserve_composition_cannot_replace_sizing_provenance():
    original = CartridgeCapacityReserve(fill_sensor_trip_mL=1.0, foam_allowance_mL=1.0)
    substitute = CartridgeCapacityReserve(manufacturing_tolerance_mL=2.0)
    result = derive_capacity_reserved_service_sizing(_evidence(original))
    assert original.total_mL == substitute.total_mL
    with pytest.raises(WasteFluidAccountingError, match="composition"):
        CapacityReservedServiceSizing(reserve=substitute, sizing=result.sizing)


def test_mutated_profile_reserve_digest_is_rejected_before_sizing():
    reserve = CartridgeCapacityReserve(fill_sensor_trip_mL=1.0)
    evidence = _evidence(reserve)
    forged = replace(evidence.profile, source_capacity_reserve_sha256="0" * 64)
    with pytest.raises(WasteFluidAccountingError, match="composition"):
        derive_capacity_reserved_service_sizing(CapacityReservedServiceProfile(reserve=reserve, profile=forged))


def test_scalar_profile_cannot_masquerade_as_typed_reserve_sizing_evidence():
    reserve = CartridgeCapacityReserve(fill_sensor_trip_mL=1.0)
    evidence = _evidence(reserve)
    forged = replace(evidence.profile, source_capacity_reserve_sha256=None)
    with pytest.raises(WasteFluidAccountingError, match="composition"):
        CapacityReservedServiceProfile(reserve=reserve, profile=forged)


def test_capacity_reserved_sizing_rejects_untyped_input():
    with pytest.raises(WasteFluidAccountingError, match="exact CapacityReservedServiceProfile"):
        derive_capacity_reserved_service_sizing(object())
