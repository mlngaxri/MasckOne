import pytest

from masck_one.commercial_evidence import (
    BurdenKind,
    BurdenStatus,
    CommercialBurden,
    CommercialEvidenceRegistry,
    EvidenceClass,
    EvidenceStatus,
    SupplierState,
    build_cell4_reference_registry,
)


def test_lookup_revalidates_postconstruction_evidence_status_corruption() -> None:
    registry = build_cell4_reference_registry()
    evidence = registry.evidence[0]
    object.__setattr__(evidence, "status", EvidenceStatus.CONTROLLED)
    with pytest.raises(ValueError, match="public evidence must remain REFERENCE_ONLY"):
        registry.burden(BurdenKind.CHARGING)


def test_lookup_revalidates_postconstruction_evidence_class_corruption() -> None:
    registry = build_cell4_reference_registry()
    evidence = registry.evidence[0]
    object.__setattr__(evidence, "evidence_class", EvidenceClass.PRODUCT_MEASUREMENT)
    with pytest.raises(ValueError, match="product/qualification evidence must be CONTROLLED"):
        registry.supplier("PLANET_INNOVATION")


def test_lookup_revalidates_invented_measured_burden_after_construction() -> None:
    registry = build_cell4_reference_registry()
    burden = registry.burden(BurdenKind.CHARGING)
    object.__setattr__(burden, "status", BurdenStatus.MEASURED)
    object.__setattr__(burden, "value", 3.0)
    object.__setattr__(burden, "unit", "cycles_per_week")
    with pytest.raises(ValueError, match="MEASURED burden requires product measurement evidence"):
        registry.burden(BurdenKind.CHARGING)


def test_lookup_revalidates_supplier_approval_promotion_after_construction() -> None:
    registry = build_cell4_reference_registry()
    supplier = registry.supplier("TRELLEBORG_MEDICAL")
    object.__setattr__(supplier, "state", SupplierState.APPROVED)
    object.__setattr__(supplier, "exact_site", "invented site")
    object.__setattr__(supplier, "exact_processes", ("LSR molding",))
    object.__setattr__(supplier, "qualification_evidence_ids", supplier.public_evidence_ids)
    with pytest.raises(ValueError, match="qualification evidence must be SUPPLIER_QUALIFICATION"):
        registry.supplier("TRELLEBORG_MEDICAL")


def test_lookup_revalidates_nested_container_corruption() -> None:
    registry = build_cell4_reference_registry()
    supplier = registry.supplier("CIRCUITWISE")
    object.__setattr__(supplier, "candidate_roles", list(supplier.candidate_roles))
    with pytest.raises(TypeError, match="candidate roles"):
        registry.supplier("CIRCUITWISE")


def test_lookup_revalidates_negative_signed_zero_after_construction() -> None:
    registry = build_cell4_reference_registry()
    target = CommercialBurden(BurdenKind.SETUP, BurdenStatus.TARGET, 1.0, "steps")
    burdens = tuple(target if item.kind is BurdenKind.SETUP else item for item in registry.burdens)
    controlled = CommercialEvidenceRegistry("SIGNED_ZERO_TEST", registry.evidence, burdens, registry.suppliers)
    object.__setattr__(target, "value", -0.0)
    with pytest.raises(ValueError, match="negative signed zero"):
        controlled.burden(BurdenKind.SETUP)


def test_registry_revalidates_referenced_evidence_id_after_construction() -> None:
    registry = build_cell4_reference_registry()
    supplier = registry.supplier("PLANET_INNOVATION")
    evidence_id = supplier.public_evidence_ids[0]
    evidence = next(item for item in registry.evidence if item.evidence_id == evidence_id)
    object.__setattr__(evidence, "evidence_id", "MUTATED_ID")
    with pytest.raises(ValueError, match="unknown evidence ids"):
        registry.validate_invariants()
