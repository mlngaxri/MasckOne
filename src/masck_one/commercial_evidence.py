from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
import math
from typing import Iterable
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


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    evidence_id: str
    evidence_class: EvidenceClass
    status: EvidenceStatus
    observed_on: date
    source_url: str | None
    statement: str

    def __post_init__(self) -> None:
        if not self.evidence_id or self.evidence_id.strip() != self.evidence_id:
            raise ValueError("evidence_id must be a non-empty canonical string")
        if not self.statement or not self.statement.strip():
            raise ValueError("evidence statement must be non-empty")
        if self.evidence_class in {
            EvidenceClass.PUBLIC_MARKET_BENCHMARK,
            EvidenceClass.PUBLIC_SUPPLIER_CAPABILITY,
        }:
            if self.status is not EvidenceStatus.REFERENCE_ONLY:
                raise ValueError("public evidence must remain REFERENCE_ONLY")
            if self.source_url is None:
                raise ValueError("public evidence requires a source URL")
        if self.evidence_class in {
            EvidenceClass.PRODUCT_MEASUREMENT,
            EvidenceClass.SUPPLIER_QUALIFICATION,
        } and self.status is not EvidenceStatus.CONTROLLED:
            raise ValueError("product/qualification evidence must be CONTROLLED")
        if self.source_url is not None:
            parsed = urlparse(self.source_url)
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
        if self.status is BurdenStatus.UNRESOLVED:
            if self.value is not None or self.unit is not None:
                raise ValueError("UNRESOLVED burden cannot carry a numeric value")
        else:
            if self.value is None or self.unit is None or not self.unit.strip():
                raise ValueError("TARGET/MEASURED burden requires value and unit")
            if isinstance(self.value, bool) or not isinstance(self.value, (int, float)):
                raise TypeError("burden value must be a real number, not a bool or alias")
            if not math.isfinite(float(self.value)) or float(self.value) < 0.0:
                raise ValueError("burden value must be finite and non-negative")
            if float(self.value) == 0.0 and math.copysign(1.0, float(self.value)) < 0.0:
                raise ValueError("negative signed zero is not canonical")
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("burden evidence_ids must be unique")


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
        if not self.supplier_id or self.supplier_id.strip() != self.supplier_id:
            raise ValueError("supplier_id must be a non-empty canonical string")
        if not self.display_name.strip():
            raise ValueError("display_name must be non-empty")
        if not self.candidate_roles or any(not role.strip() for role in self.candidate_roles):
            raise ValueError("supplier requires at least one non-empty candidate role")
        if len(set(self.candidate_roles)) != len(self.candidate_roles):
            raise ValueError("candidate roles must be unique")
        if len(set(self.public_evidence_ids)) != len(self.public_evidence_ids):
            raise ValueError("public evidence ids must be unique")
        if len(set(self.qualification_evidence_ids)) != len(self.qualification_evidence_ids):
            raise ValueError("qualification evidence ids must be unique")
        if self.state is SupplierState.APPROVED:
            if self.exact_site is None or not self.exact_site.strip():
                raise ValueError("APPROVED supplier requires an exact qualified site")
            if not self.exact_processes or any(not p.strip() for p in self.exact_processes):
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
        if not self.revision or self.revision.strip() != self.revision:
            raise ValueError("revision must be a non-empty canonical string")
        evidence_ids = tuple(item.evidence_id for item in self.evidence)
        if len(set(evidence_ids)) != len(evidence_ids):
            raise ValueError("evidence ids must be globally unique")
        burden_kinds = tuple(item.kind for item in self.burdens)
        if len(set(burden_kinds)) != len(burden_kinds):
            raise ValueError("commercial burden kinds must be unique")
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
            if supplier.state is SupplierState.APPROVED and not supplier.qualification_evidence_ids:
                raise ValueError("APPROVED supplier cannot rely on public marketing evidence")

    @staticmethod
    def _require_known(evidence_by_id: dict[str, EvidenceRecord], ids: Iterable[str]) -> None:
        unknown = tuple(eid for eid in ids if eid not in evidence_by_id)
        if unknown:
            raise ValueError(f"unknown evidence ids: {unknown!r}")

    def supplier(self, supplier_id: str) -> SupplierRecord:
        matches = tuple(item for item in self.suppliers if item.supplier_id == supplier_id)
        if len(matches) != 1:
            raise KeyError(supplier_id)
        return matches[0]

    def burden(self, kind: BurdenKind) -> CommercialBurden:
        matches = tuple(item for item in self.burdens if item.kind is kind)
        if len(matches) != 1:
            raise KeyError(kind)
        return matches[0]


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
            "Eight Sleep publicly ties warranty conditions to membership in some cases; this is evidence that recurring software burden can affect ownership support.",
        ),
        EvidenceRecord(
            "SUP_TRELLEBORG_MEDICAL_2026_09_01",
            EvidenceClass.PUBLIC_SUPPLIER_CAPABILITY,
            EvidenceStatus.REFERENCE_ONLY,
            observed,
            "https://www.trelleborg.com/en/medical",
            "Trelleborg Medical Solutions publicly describes molding, plastic injection molding, silicone, DFM and prototype-to-serial capabilities.",
        ),
        EvidenceRecord(
            "SUP_PHILLIPS_MEDISIZE_MOLDING_2026_09_01",
            EvidenceClass.PUBLIC_SUPPLIER_CAPABILITY,
            EvidenceStatus.REFERENCE_ONLY,
            observed,
            "https://phillipsmedisize.com/capabilities/manufacturing/advanced-injection-molding/",
            "Phillips Medisize publicly describes plastic injection molding, liquid silicone rubber molding, tooling and electromechanical integration capabilities.",
        ),
        EvidenceRecord(
            "SUP_JABIL_HEALTHCARE_2026_09_01",
            EvidenceClass.PUBLIC_SUPPLIER_CAPABILITY,
            EvidenceStatus.REFERENCE_ONLY,
            observed,
            "https://www.jabil.com/industries/healthcare.html",
            "Jabil publicly describes healthcare design/manufacturing capabilities and site-specific quality systems; exact Masck One site/process fit remains unqualified.",
        ),
        EvidenceRecord(
            "SUP_TESSY_2026_09_01",
            EvidenceClass.PUBLIC_SUPPLIER_CAPABILITY,
            EvidenceStatus.REFERENCE_ONLY,
            observed,
            "https://tessy.com/",
            "Tessy publicly describes precision plastics, tooling, assembly, prototyping and global manufacturing capabilities.",
        ),
    )

    burdens = tuple(
        CommercialBurden(kind=kind, status=BurdenStatus.UNRESOLVED)
        for kind in BurdenKind
    )

    suppliers = (
        SupplierRecord(
            "TRELLEBORG_MEDICAL",
            "Trelleborg Medical Solutions",
            SupplierState.REFERENCE_CANDIDATE,
            ("compliant-interface molding", "rigid plastic molding", "DFM/prototype process development"),
            ("SUP_TRELLEBORG_MEDICAL_2026_09_01",),
        ),
        SupplierRecord(
            "PHILLIPS_MEDISIZE",
            "Phillips Medisize",
            SupplierState.REFERENCE_CANDIDATE,
            ("integrated NPI", "LSR/plastic molding", "electromechanical assembly"),
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
