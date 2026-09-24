from dataclasses import replace

import pytest

from masck_one.distribution_geometry import DistributionGeometryError
from masck_one.treatment_clean_distribution_evidence import (
    build_treatment_clean_distribution_evidence,
    validate_treatment_clean_distribution_evidence,
)
from masck_one.treatment_recovery_readiness import screen_treatment_recovery_readiness
from masck_one.waste_fluid_accounting import WasteFluidAccountingError, build_authority_waste_fluid_budget
from masck_one.waste_fluid_capacity_reserve import (
    CartridgeCapacityReserve,
    screen_cartridge_capacity_reserve_evidence,
)
from masck_one.waste_fluid_cycle_routing import screen_cycle_resolved_routing_closure
from tests.test_distribution_geometry import built


def _sources(built):
    model, water, cleanser, frame, pump, manifold, geometry = built
    return geometry, dict(
        authority=model.authority,
        manifold=manifold,
        pump=pump,
        water=water,
        cleanser=cleanser,
        frame=frame,
        coverage=model.coverage_mesh,
        protected=model.protected_volumes,
    )


def _capacity_aware_readiness():
    budget = build_authority_waste_fluid_budget()
    reserve = CartridgeCapacityReserve(fill_sensor_trip_mL=1.0)
    capacity = screen_cartridge_capacity_reserve_evidence(
        budget,
        reserve,
        prime_events_by_cycle=(0,),
        prime_recovery_ratio_contract=1.0,
    )
    return screen_treatment_recovery_readiness(capacity)


def test_binds_canonical_distribution_to_capacity_aware_recovery(built):
    geometry, sources = _sources(built)
    recovery = _capacity_aware_readiness()
    evidence = build_treatment_clean_distribution_evidence(geometry, recovery, **sources)

    assert evidence.distribution is geometry
    assert evidence.recovery is recovery
    assert evidence.source_distribution_sha256 == geometry.architecture_sha256
    assert validate_treatment_clean_distribution_evidence(evidence, **sources) is evidence


def test_rejects_closure_only_recovery_without_capacity_guard(built):
    geometry, sources = _sources(built)
    budget = build_authority_waste_fluid_budget()
    closure = screen_cycle_resolved_routing_closure(
        budget,
        prime_events_by_cycle=(0,),
        prime_recovery_ratio_contract=1.0,
    )
    recovery = screen_treatment_recovery_readiness(closure)

    with pytest.raises(WasteFluidAccountingError, match="reserve-aware CartridgeOverflowGuard"):
        build_treatment_clean_distribution_evidence(geometry, recovery, **sources)


def test_rejects_forged_distribution_digest_binding(built):
    geometry, sources = _sources(built)
    evidence = build_treatment_clean_distribution_evidence(
        geometry, _capacity_aware_readiness(), **sources
    )
    forged = replace(evidence, source_distribution_sha256="0" * 64)

    with pytest.raises(DistributionGeometryError, match="digest does not match"):
        validate_treatment_clean_distribution_evidence(forged, **sources)


def test_rejects_wrong_evidence_type(built):
    _, sources = _sources(built)
    with pytest.raises(TypeError, match="exact TreatmentCleanDistributionEvidence"):
        validate_treatment_clean_distribution_evidence(object(), **sources)
