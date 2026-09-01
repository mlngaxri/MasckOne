from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
import math
from urllib.parse import urlparse


class EvidenceClass(StrEnum):
    PUBLIC_MARKET_BENCHMARK = "PUBLIC_MARKET_BENCHMARK"
    PUBLIC_SUPPLIER_CAPABILITY = "PUBLIC_SUPPLIER_CAPABILITY"
    PRODUCT_MEASUREMENT = "PRODUCT_MEASUREMENT"
    SUPPLIER_QUALIFICATION = "SUPPLIER_QUALIFICATION"


class EvidenceStatus(StrEnum):
    REFERENCE_ONLY = "REFERENCE_ONLY"
    CONTROLLED = "CONTROLLED"


class SupplierState(StrEnum):
    REFERENCE_CANDIDATE = "REFERENCE_CANDIDATE"
    QUALIFICATION_IN_PROGRESS = "QUALIFICATION_IN_PROGRESS"
    APPROVED = "APPROVED"


class BurdenStatus(StrEnum):
    UNRESOLVED = "UNRESOLVED"
    TARGET = "TARGET"
    MEASURED = "MEASURED"


class BurdenKind(StrEnum):
    WATER_REFILL = "WATER_REFILL"
    CLEANSER_REFILL = "CLEANSER_REFILL"
    WASTE_SERVICE = "WASTE_SERVICE"
    CARTRIDGE_REPLACEMENT = "CARTRIDGE_REPLACEMENT"
    CHARGING = "CHARGING"
    CLEANING = "CLEANING"
    SETUP = "SETUP"
    APP_DEPENDENCY = "APP_DEPENDENCY"
    FAULT_RECOVERY = "FAULT_RECOVERY"
    TRAVEL_STORAGE = "TRAVEL_STORAGE"


def _text(value: object, *, label: str) -> str:
    if type(value) is not str or not value or value.strip() != value:
        raise ValueError(f"{label} must be exact built-in non-empty canonical text")
    return value


def _optional_text(value: object, *, label: str) -> str | None:
    if value is None:
        return None
    return _text(value, label=label)


def _text_tuple(value: object, *, label: str, allow_empty: bool = True) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise TypeError(f"{label} must be an immutable exact tuple")
    if not allow_empty and not value:
        raise ValueError(f"{label} must be non-empty")
    for item in value:
        _text(item, label=f"{label} item")
    if len(set(value)) != len(value):
        raise ValueError(f"{label} values must be unique")
    return value


def _exact_enum(value: object, expected_type: type[StrEnum], *, label: str) -> None:
    if type(value) is not expected_type:
        raise TypeError(f"{label} must use the exact controlled enum type")


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    evidence_id: str
    evidence_class: EvidenceClass
    status: EvidenceStatus
    observed_on: date
    source_url: str | None
    statement: str

    def __post_init__(self) -> None:
        _text(self.evidence_id, label="evidence_id")
        _exact_enum(self.evidence_class, EvidenceClass, label="evidence_class")
        _exact_enum(self.status, EvidenceStatus, label="evidence status")
        if type(self.observed_on) is not date:
            raise TypeError("observed_on must be an exact date")
        _text(self.statement, label="evidence statement")
        source_url = _optional_text(self.source_url, label="source_url")
        if self.evidence_class in {
            EvidenceClass.PUBLIC_MARKET_BENCHMARK,
            EvidenceClass.PUBLIC_SUPPLIER_CAPABILITY,
        }:
            if self.status is not EvidenceStatus.REFERENCE_ONLY:
                raise ValueError("public evidence must remain REFERENCE_ONLY")
            if source_url is None:
                raise ValueError("public evidence requires a source URL")
        if self.evidence_class in {
            EvidenceClass.PRODUCT_MEASUREMENT,
            EvidenceClass.SUPPLIER_QUALIFICATION,
        } and self.status is not EvidenceStatus.CONTROLLED:
            raise ValueError("product/qualification evidence must be CONTROLLED")
        if source_url is not None:
            parsed = urlparse(source_url)
            if parsed.scheme != "https" or not parsed.netloc:
                raise ValueError("source_url must be an absolute HTTPS URL")


@dataclass(frozen=True, slots=True)
class CommercialBurden:
    kind: BurdenKind
    status: BurdenStatus
    value: float | None = None
    unit: str | None = None
    evidence_ids: tuple[str, ...] = ()
    note: str = ""

    def __post_init__(self) -> None:
        _exact_enum(self.kind, BurdenKind, label="burden kind")
        _exact_enum(self.status, BurdenStatus, label="burden status")
        _text_tuple(self.evidence_ids, label="burden evidence_ids")
        if type(self.note) is not str:
            raise TypeError("burden note must be exact built-in text")
        if self.note and self.note.strip() != self.note:
            raise ValueError("burden note must be canonical text")
        if self.status is BurdenStatus.UNRESOLVED:
            if self.value is not None or self.unit is not None:
                raise ValueError("UNRESOLVED burden cannot carry a numeric value")
        else:
            if type(self.value) not in (int, float):
                raise TypeError("burden value must be an exact real numeric scalar")
            _text(self.unit, label="burden unit")
            numeric = float(self.value)
            if not math.isfinite(numeric) or numeric < 0.0:
                raise ValueError("burden value must be finite and non-negative")
            if numeric == 0.0 and math.copysign(1.0, numeric) < 0.0:
                raise ValueError("negative signed zero is not canonical")


@dataclass(frozen=True, slots=True)
class SupplierRecord:
    supplier_id: str
    display_name: str
    state: SupplierState
    candidate_roles: tuple[str, ...]
    public_evidence_ids: tuple[str, ...]
    exact_site: str | None = None
    exact_processes: tuple[str, ...] = ()
    qualification_evidence_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _text(self.supplier_id, label="supplier_id")
        _text(self.display_name, label="display_name")
        _exact_enum(self.state, SupplierState, label="supplier state")
        _text_tuple(self.candidate_roles, label="candidate roles", allow_empty=False)
        _text_tuple(self.public_evidence_ids, label="public evidence ids")
        _optional_text(self.exact_site, label="exact qualified site")
        _text_tuple(self.exact_processes, label="exact qualified processes")
        _text_tuple(self.qualification_evidence_ids, label="qualification evidence ids")
        if self.state is SupplierState.APPROVED:
            if self.exact_site is None:
                raise ValueError("APPROVED supplier requires an exact qualified site")
            if not self.exact_processes:
                raise ValueError("APPROVED supplier requires exact qualified processes")
            if not self.qualification_evidence_ids:
                raise ValueError("APPROVED supplier requires qualification evidence")


@dataclass(frozen=True, slots=True)
class CommercialEvidenceRegistry:
    revision: str
    evidence: tuple[EvidenceRecord, ...]
    burdens: tuple[CommercialBurden, ...]
    suppliers: tuple[SupplierRecord, ...]

    def __post_init__(self) -> None:
        _text(self.revision, label="revision")
        if type(self.evidence) is not tuple or any(type(item) is not EvidenceRecord for item in self.evidence):
            raise TypeError("evidence registry must be an immutable tuple of exact EvidenceRecord objects")
        if type(self.burdens) is not tuple or any(type(item) is not CommercialBurden for item in self.burdens):
            raise TypeError("burden registry must be an immutable tuple of exact CommercialBurden objects")
        if type(self.suppliers) is not tuple or any(type(item) is not SupplierRecord for item in self.suppliers):
            raise TypeError("supplier registry must be an immutable tuple of exact SupplierRecord objects")
        for item in self.evidence:
            item.__post_init__()
        for item in self.burdens:
            item.__post_init__()
        for item in self.suppliers:
            item.__post_init__()

        evidence_ids = tuple(item.evidence_id for item in self.evidence)
        if len(set(evidence_ids)) != len(evidence_ids):
            raise ValueError("evidence ids must be globally unique")
        burden_kinds = tuple(item.kind for item in self.burdens)
        if len(set(burden_kinds)) != len(burden_kinds):
            raise ValueError("commercial burden kinds must be unique")
        if set(burden_kinds) != set(BurdenKind):
            raise ValueError("commercial burden registry must contain every controlled burden kind exactly once")
        supplier_ids = tuple(item.supplier_id for item in self.suppliers)
        if len(set(supplier_ids)) != len(supplier_ids):
            raise ValueError("supplier ids must be unique")

        evidence_by_id = {item.evidence_id: item for item in self.evidence}
        for burden in self.burdens:
            self._require_known(evidence_by_id, burden.evidence_ids)
            if burden.status is BurdenStatus.MEASURED:
                if not burden.evidence_ids:
                    raise ValueError("MEASURED burden requires product measurement evidence")
                classes = {evidence_by_id[eid].evidence_class for eid in burden.evidence_ids}
                if EvidenceClass.PRODUCT_MEASUREMENT not in classes:
                    raise ValueError("MEASURED burden requires PRODUCT_MEASUREMENT evidence")

        for supplier in self.suppliers:
            self._require_known(evidence_by_id, supplier.public_evidence_ids)
            self._require_known(evidence_by_id, supplier.qualification_evidence_ids)
            for eid in supplier.public_evidence_ids:
                if evidence_by_id[eid].evidence_class is not EvidenceClass.PUBLIC_SUPPLIER_CAPABILITY:
                    raise ValueError("supplier public evidence must be PUBLIC_SUPPLIER_CAPABILITY")
            for eid in supplier.qualification_evidence_ids:
                if evidence_by_id[eid].evidence_class is not EvidenceClass.SUPPLIER_QUALIFICATION:
                    raise ValueError("qualification evidence must be SUPPLIER_QUALIFICATION")

    @staticmethod
    def _require_known(evidence_by_id: dict[str, EvidenceRecord], ids: tuple[str, ...]) -> None:
        unknown = tuple(eid for eid in ids if eid not in evidence_by_id)
        if unknown:
            raise ValueError(f"unknown evidence ids: {unknown!r}")

    def supplier(self, supplier_id: str) -> SupplierRecord:
        _text(supplier_id, label="supplier lookup id")
        matches = tuple(item for item in self.suppliers if item.supplier_id == supplier_id)
        if len(matches) != 1:
            raise KeyError(supplier_id)
        return matches[0]

    def burden(self, kind: BurdenKind) -> CommercialBurden:
        _exact_enum(kind, BurdenKind, label="burden lookup kind")
        matches = tuple(item for item in self.burdens if item.kind is kind)
        if len(matches) != 1:
            raise KeyError(kind)
        return matches[0]


def _public_supplier(
    evidence_id: str,
    observed: date,
    url: str,
    statement: str,
) -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id,
        EvidenceClass.PUBLIC_SUPPLIER_CAPABILITY,
        EvidenceStatus.REFERENCE_ONLY,
        observed,
        url,
        statement,
    )


def build_cell4_reference_registry() -> CommercialEvidenceRegistry:
    observed = date(2026, 9, 1)
    evidence = (
        EvidenceRecord(
            "MKT_APPLE_BATTERY_SERVICE_2026_09_01",
            EvidenceClass.PUBLIC_MARKET_BENCHMARK,
            EvidenceStatus.REFERENCE_ONLY,
            observed,
            "https://www.apple.com/au/batteries/service-and-recycling/",
            "Apple publicly describes rechargeable-battery ageing and service pathways; this is a service benchmark, not Masck One runtime evidence.",
        ),
        EvidenceRecord(
            "MKT_DYSON_AU_SERVICE_2026_09_01",
            EvidenceClass.PUBLIC_MARKET_BENCHMARK,
            EvidenceStatus.REFERENCE_ONLY,
            observed,
            "https://www.dyson.com.au/dyson-stores-and-service-centres",
            "Dyson Australia publicly exposes repair and service-centre pathways; this is a support benchmark only.",
        ),
        EvidenceRecord(
            "MKT_EIGHTSLEEP_WARRANTY_2026_09_01",
            EvidenceClass.PUBLIC_MARKET_BENCHMARK,
            EvidenceStatus.REFERENCE_ONLY,
            observed,
            "https://www.eightsleep.com/warranty/",
            "Eight Sleep publicly couples some warranty coverage to active membership; this is an ownership-burden reference only.",
        ),
        _public_supplier(
            "SUP_PLANET_INNOVATION_2026_09_01",
            observed,
            "https://planetinnovation.com/manufacturing/",
            "Planet Innovation publicly describes NPI, contract manufacturing, consumables, leak testing and ISO 13485-compliant manufacturing systems.",
        ),
        _public_supplier(
            "SUP_CIRCUITWISE_2026_09_01",
            observed,
            "https://circuitwise.com.au/",
            "Circuitwise publicly describes PCBA, DFM, inspection, integration and functional-test capabilities under ISO 13485 and related systems.",
        ),
        _public_supplier(
            "SUP_REID_PRINT_2026_09_01",
            observed,
            "https://reidprinttechnologies.com.au/",
            "Reid Print Technologies publicly describes flexible printed sensors, membrane interfaces, wearable electronics and ISO 13485/ISO 9001 systems.",
        ),
        _public_supplier(
            "SUP_TRELLEBORG_MEDICAL_2026_09_01",
            observed,
            "https://www.trelleborg.com/en/medical",
            "Trelleborg Medical Solutions publicly describes silicone, plastic injection molding, DFM and prototype-to-serial capabilities.",
        ),
        _public_supplier(
            "SUP_PHILLIPS_MEDISIZE_MOLDING_2026_09_01",
            observed,
            "https://phillipsmedisize.com/capabilities/manufacturing/advanced-injection-molding/",
            "Phillips Medisize publicly describes plastic injection molding, liquid silicone rubber molding, tooling and electromechanical integration capabilities.",
        ),
        _public_supplier(
            "SUP_JABIL_HEALTHCARE_2026_09_01",
            observed,
            "https://www.jabil.com/industries/healthcare.html",
            "Jabil publicly describes healthcare design/manufacturing capabilities and site-specific quality systems; exact Masck One fit remains unqualified.",
        ),
        _public_supplier(
            "SUP_TESSY_2026_09_01",
            observed,
            "https://tessy.com/",
            "Tessy publicly describes precision plastics, tooling, assembly, prototyping and global manufacturing capabilities.",
        ),
    )

    burdens = tuple(CommercialBurden(kind=kind, status=BurdenStatus.UNRESOLVED) for kind in BurdenKind)

    suppliers = (
        SupplierRecord(
            "PLANET_INNOVATION",
            "Planet Innovation",
            SupplierState.REFERENCE_CANDIDATE,
            ("integrated NPI", "alpha-to-pilot manufacturing", "assembly/test architecture"),
            ("SUP_PLANET_INNOVATION_2026_09_01",),
        ),
        SupplierRecord(
            "TRELLEBORG_MEDICAL",
            "Trelleborg Medical Solutions",
            SupplierState.REFERENCE_CANDIDATE,
            ("compliant-interface molding", "rigid plastic molding", "DFM/prototype process development"),
            ("SUP_TRELLEBORG_MEDICAL_2026_09_01",),
        ),
        SupplierRecord(
            "CIRCUITWISE",
            "Circuitwise",
            SupplierState.REFERENCE_CANDIDATE,
            ("PCBA NPI", "electronics inspection", "functional-test integration"),
            ("SUP_CIRCUITWISE_2026_09_01",),
        ),
        SupplierRecord(
            "REID_PRINT_TECHNOLOGIES",
            "Reid Print Technologies",
            SupplierState.REFERENCE_CANDIDATE,
            ("sealed HMI prototypes", "flexible sensor coupons", "heater/sensing coupons"),
            ("SUP_REID_PRINT_2026_09_01",),
        ),
        SupplierRecord(
            "PHILLIPS_MEDISIZE",
            "Phillips Medisize",
            SupplierState.REFERENCE_CANDIDATE,
            ("integrated NPI comparator", "LSR/plastic molding", "electromechanical assembly"),
            ("SUP_PHILLIPS_MEDISIZE_MOLDING_2026_09_01",),
        ),
        SupplierRecord(
            "JABIL_HEALTHCARE",
            "Jabil Healthcare",
            SupplierState.REFERENCE_CANDIDATE,
            ("scale manufacturing", "electronics/plastics integration", "lifecycle manufacturing"),
            ("SUP_JABIL_HEALTHCARE_2026_09_01",),
        ),
        SupplierRecord(
            "TESSY_PLASTICS",
            "Tessy Plastics",
            SupplierState.REFERENCE_CANDIDATE,
            ("precision plastics", "tooling", "complex assembly"),
            ("SUP_TESSY_2026_09_01",),
        ),
    )
    return CommercialEvidenceRegistry(
        revision="CELL4_COMMERCIAL_EVIDENCE_V1_2026_09_01",
        evidence=evidence,
        burdens=burdens,
        suppliers=suppliers,
    )
