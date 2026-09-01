from dataclasses import replace
from datetime import date

import pytest

from masck_one.commercial_evidence import (
    BurdenKind,
    BurdenStatus,
    CommercialBurden,
    CommercialEvidenceRegistry,
    EvidenceClass,
    EvidenceRecord,
    EvidenceStatus,
    SupplierRecord,
    SupplierState,
    build_cell4_reference_registry,
)


def test_reference_registry_is_fail_closed_and_complete() -> None:
    registry = build_cell4_reference_registry()
    assert registry.revision == "CELL4_COMMERCIAL_EVIDENCE_V1_2026_09_01"
    assert {item.kind for item in registry.burdens} == set(BurdenKind)
    assert all(item.status is BurdenStatus.UNRESOLVED for item in registry.burdens)
    assert all(item.state is SupplierState.REFERENCE_CANDIDATE for item in registry.suppliers)
    assert all(not item.qualification_evidence_ids for item in registry.suppliers)


def test_public_supplier_marketing_cannot_be_controlled_evidence() -> None:
    with pytest.raises(ValueError, match="public evidence must remain REFERENCE_ONLY"):
        EvidenceRecord(
            "BAD",
            EvidenceClass.PUBLIC_SUPPLIER_CAPABILITY,
            EvidenceStatus.CONTROLLED,
            date(2026, 9, 1),
            "https://example.com/capability",
            "marketing statement",
        )


def test_public_evidence_requires_https_provenance() -> None:
    with pytest.raises(ValueError, match="absolute HTTPS URL"):
        EvidenceRecord(
            "BAD_URL",
            EvidenceClass.PUBLIC_MARKET_BENCHMARK,
            EvidenceStatus.REFERENCE_ONLY,
            date(2026, 9, 1),
            "http://example.com/benchmark",
            "benchmark statement",
        )


def test_unresolved_burden_cannot_smuggle_numeric_cadence() -> None:
    with pytest.raises(ValueError, match="UNRESOLVED burden cannot carry a numeric value"):
        CommercialBurden(
            BurdenKind.CARTRIDGE_REPLACEMENT,
            BurdenStatus.UNRESOLVED,
            value=7.0,
            unit="days",
        )


def test_measured_burden_requires_product_measurement_evidence() -> None:
    registry = build_cell4_reference_registry()
    fake_measured = CommercialBurden(
        BurdenKind.CHARGING,
        BurdenStatus.MEASURED,
        value=3.0,
        unit="cycles_per_week",
        evidence_ids=("MKT_APPLE_BATTERY_SERVICE_2026_09_01",),
    )
    burdens = tuple(
        fake_measured if item.kind is BurdenKind.CHARGING else item
        for item in registry.burdens
    )
    with pytest.raises(ValueError, match="PRODUCT_MEASUREMENT"):
        CommercialEvidenceRegistry(
            revision=registry.revision,
            evidence=registry.evidence,
            burdens=burdens,
            suppliers=registry.suppliers,
        )


def test_measured_burden_accepts_controlled_product_measurement() -> None:
    registry = build_cell4_reference_registry()
    measured = EvidenceRecord(
        "MEAS_ALPHA_CHARGING_001",
        EvidenceClass.PRODUCT_MEASUREMENT,
        EvidenceStatus.CONTROLLED,
        date(2026, 9, 1),
        None,
        "Controlled alpha charging-cadence measurement artifact.",
    )
    measured_burden = CommercialBurden(
        BurdenKind.CHARGING,
        BurdenStatus.MEASURED,
        value=3.0,
        unit="cycles_per_week",
        evidence_ids=(measured.evidence_id,),
    )
    burdens = tuple(
        measured_burden if item.kind is BurdenKind.CHARGING else item
        for item in registry.burdens
    )
    result = CommercialEvidenceRegistry(
        revision="TEST_WITH_MEASUREMENT",
        evidence=registry.evidence + (measured,),
        burdens=burdens,
        suppliers=registry.suppliers,
    )
    assert result.burden(BurdenKind.CHARGING).status is BurdenStatus.MEASURED


def test_approved_supplier_requires_exact_site_process_and_qualification() -> None:
    with pytest.raises(ValueError, match="exact qualified site"):
        SupplierRecord(
            "UNSAFE_APPROVAL",
            "Unsafe Approval",
            SupplierState.APPROVED,
            ("molding",),
            (),
            exact_site=None,
            exact_processes=("LSR molding",),
            qualification_evidence_ids=("QUAL_1",),
        )


def test_public_capability_cannot_promote_supplier_to_approved() -> None:
    registry = build_cell4_reference_registry()
    supplier = replace(
        registry.supplier("TRELLEBORG_MEDICAL"),
        state=SupplierState.APPROVED,
        exact_site="example site",
        exact_processes=("LSR molding",),
        qualification_evidence_ids=("SUP_TRELLEBORG_MEDICAL_2026_09_01",),
    )
    suppliers = tuple(
        supplier if item.supplier_id == supplier.supplier_id else item
        for item in registry.suppliers
    )
    with pytest.raises(ValueError, match="qualification evidence must be SUPPLIER_QUALIFICATION"):
        CommercialEvidenceRegistry(
            revision=registry.revision,
            evidence=registry.evidence,
            burdens=registry.burdens,
            suppliers=suppliers,
        )


def test_unknown_evidence_reference_is_rejected() -> None:
    registry = build_cell4_reference_registry()
    poisoned = replace(
        registry.burden(BurdenKind.WASTE_SERVICE),
        evidence_ids=("MISSING",),
    )
    burdens = tuple(
        poisoned if item.kind is BurdenKind.WASTE_SERVICE else item
        for item in registry.burdens
    )
    with pytest.raises(ValueError, match="unknown evidence ids"):
        CommercialEvidenceRegistry(
            revision=registry.revision,
            evidence=registry.evidence,
            burdens=burdens,
            suppliers=registry.suppliers,
        )


def test_duplicate_evidence_and_supplier_ids_are_rejected() -> None:
    registry = build_cell4_reference_registry()
    with pytest.raises(ValueError, match="evidence ids must be globally unique"):
        CommercialEvidenceRegistry(
            revision=registry.revision,
            evidence=registry.evidence + (registry.evidence[0],),
            burdens=registry.burdens,
            suppliers=registry.suppliers,
        )
    with pytest.raises(ValueError, match="supplier ids must be unique"):
        CommercialEvidenceRegistry(
            revision=registry.revision,
            evidence=registry.evidence,
            burdens=registry.burdens,
            suppliers=registry.suppliers + (registry.suppliers[0],),
        )


def test_negative_signed_zero_and_boolean_values_are_rejected() -> None:
    with pytest.raises(ValueError, match="negative signed zero"):
        CommercialBurden(BurdenKind.SETUP, BurdenStatus.TARGET, -0.0, "steps")
    with pytest.raises(TypeError, match="real number"):
        CommercialBurden(BurdenKind.SETUP, BurdenStatus.TARGET, True, "steps")
