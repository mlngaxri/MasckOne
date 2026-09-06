from __future__ import annotations

"""Source-bound mass, CG, pitch, power and fluid truth for current released main.

The ledger deliberately credits only the narrow benchmark subset that has traceable
mass evidence. CAD volume without controlled material/density, liquid volume without
controlled mass/density, and nameplate battery data without selected load evidence do
not become whole-product mass, runtime or physical-performance claims.
"""

from dataclasses import dataclass
from hashlib import sha1, sha256
import json
import math
from pathlib import Path
import re

from .authority import Authority, load_authority
from .model import MasckOneModel, build_model


SCHEMA = "MASCK_ONE_CELL18_QUANTITATIVE_LEDGER_V1"
SOURCE_MAIN_SHA = "afe29ff78419b6625dca5594974b6351f6f80e1b"
AUTHORITY_REVISION = "2026-08-30-R1"
AUTHORITY_BLOB_SHA = "2608dda483b995539de422290371c219668a1527"
MODEL_BLOB_SHA = "9e7fa6c71ac28cc45ebb502444bf6c0ea49f7894"
ACTUATOR_FRAMES_BLOB_SHA = "4c2013f994bdc9e084fe227eb5e166f973500ebb"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
STANDARD_GRAVITY_M_S2 = 9.80665

LEGACY_MASS_DONOR_PR = 63
LEGACY_MASS_DONOR_HEAD_SHA = "23b942bbb7f335eac74b42fa1b1613900e5a9347"
LEGACY_POWER_DONOR_PR = 64
LEGACY_POWER_DONOR_HEAD_SHA = "49a32d0c61bd1057ee707ee2ef20b8ff4e6ede01"

SUPPLIER_ACTUATOR_PACKAGE_MODEL = "H2W NCM01-04-001-2IBH"
SUPPLIER_ACTUATOR_MASS_SOURCE_MODEL = "H2W NCM01-04-001-2IB"
SUPPLIER_ACTUATOR_TOTAL_MASS_G = 5.6
SUPPLIER_ACTUATOR_SOURCE_URL = "https://www.h2wtech.com/product/voice-coil-actuators/NCM01-04-001-2IB"
SUPPLIER_ACTUATOR_SOURCE_RETRIEVED = "2026-09-04"
SUPPLIER_ACTUATOR_PROVENANCE = (
    "SUPPLIER_PUBLISHED_SIBLING_MODEL_TOTAL_MASS_BENCHMARK_"
    "NOT_EXACT_2IBH_OR_PRODUCTION_FREEZE"
)
EXPECTED_KNOWN_BENCHMARK_SUBTOTAL_G = 44.4

MASS_EVIDENCE_STATUS = (
    "KNOWN_DRY_SUBSET_USES_AUTHORITY_BATTERY_BENCHMARK_AND_H2W_2IB_SIBLING_MODEL_"
    "PUBLISHED_MASS_BENCHMARK_ONLY_EXACT_2IBH_MASS_UNRESOLVED_"
    "FULL_DRY_LOADED_CG_AND_PITCH_REMAIN_BLOCKED_NOT_PHYSICAL_VALIDATION"
)
POWER_EVIDENCE_STATUS = "NAMEPLATE_BATTERY_REFERENCE_AND_UNRESOLVED_LOAD_LEDGER_NOT_RUNTIME_EVIDENCE"
FLUID_EVIDENCE_STATUS = (
    "AUTHORITY_CONTROLLED_VOLUME_AND_RATIO_INVENTORY_ONLY_NO_VOLUME_TO_MASS_CONVERSION_"
    "NO_RECOVERY_CAPACITY_OR_FLUID_PERFORMANCE_VALIDATION"
)
EVIDENCE_STATUS = (
    "DIGITAL_SOURCE_BOUND_QUANTITATIVE_ACCOUNTING_ONLY_NOT_MATERIAL_SUPPLIER_RUNTIME_"
    "HYDRAULIC_THERMAL_HUMAN_OR_PHYSICAL_VALIDATION"
)

UNRESOLVED_LOADED_TERMS = (
    "WATER_LOAD_MASS_BLOCKED_PENDING_CONTROLLED_FLUID_MASS_OR_DENSITY_PROVENANCE",
    "CLEANSER_LOAD_MASS_BLOCKED_PENDING_SELECTED_CLEANSER_AND_CONTROLLED_MASS_OR_DENSITY_PROVENANCE",
    "WASTE_LOAD_MASS_BLOCKED_PENDING_REALIZED_CARTRIDGE_MEDIA_AND_CONTROLLED_PHYSICAL_MASS_EVIDENCE",
)

POWER_LOAD_IDS = (
    "ACTUATORS_X4",
    "FRESH_WATER_PUMP",
    "CLEANSER_PUMP",
    "WASTE_PUMP",
    "CONTROL_ELECTRONICS",
    "PHYSICAL_HMI_STATUS",
    "WARM",
    "COOL_EXPERIMENTAL",
)

SOURCE_GIT_BLOB_IDENTITIES: tuple[tuple[str, str], ...] = (
    ("config/masck_one_authority.yaml", AUTHORITY_BLOB_SHA),
    ("src/masck_one/anatomy.py", "872d1e5be1b9ce9baa5b63cb53462eb7b36f40ab"),
    ("src/masck_one/authority.py", "6866e3a428dab8b32b5a1d9e58da78b8f5aa1aa2"),
    ("src/masck_one/coverage.py", "4a8cec4d94db97e63f634a94dd8c90094f3afcb0"),
    ("src/masck_one/facial_surface.py", "764f6f65b83ac7709d959bb0f37f861c90ea2794"),
    ("src/masck_one/interface_topology.py", "38b7c932f71a8675d45d098ac65154f98ff8bbb5"),
    ("src/masck_one/model.py", MODEL_BLOB_SHA),
    ("src/masck_one/nasal_subsystem.py", "f1f22b828d0465636579fc31eff0bfb6a6bf2507"),
    ("src/masck_one/protected_volumes.py", "ff2b9b288559f9b268e5d08a1d6c78335f745cf1"),
    ("src/masck_one/spatial.py", "8c1106b523fef5111009cc56236a53e3bc5ee10e"),
    ("src/masck_one/worn_pose.py", "9d4ed65246fbc92ac577ce38bceb95cd2253607b"),
    ("src/masck_one/actuator_frames.py", ACTUATOR_FRAMES_BLOB_SHA),
)

EXPECTED_MODEL_COMPONENT_NAMES = (
    "actuator_envelope_1",
    "actuator_envelope_2",
    "actuator_envelope_3",
    "actuator_envelope_4",
    "battery_reference_envelope",
    "nasal_lobe_membrane_reference",
    "rigid_shell",
    "visual_eye_left",
    "visual_eye_right",
    "visual_mouth",
    "visual_nostril_left",
    "visual_nostril_right",
    "waste_cartridge_envelope",
    "water_reservoir_envelope",
)

ROLE_PHYSICAL_MASS_UNKNOWN = "PHYSICAL_MASS_UNKNOWN"
ROLE_BENCHMARK_MASS_CREDIT = "BENCHMARK_MASS_CREDIT"
ROLE_PACKAGE_REFERENCE_MASS_UNKNOWN = "PACKAGE_REFERENCE_MASS_UNKNOWN"
ROLE_REFERENCE_EXCLUDED = "REFERENCE_EXCLUDED_FROM_MASS_ARITHMETIC"
ROLE_VOCABULARY = (
    ROLE_PHYSICAL_MASS_UNKNOWN,
    ROLE_BENCHMARK_MASS_CREDIT,
    ROLE_PACKAGE_REFERENCE_MASS_UNKNOWN,
    ROLE_REFERENCE_EXCLUDED,
)

_GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_REPO_ROOT = Path(__file__).resolve().parents[2]


class QuantitativeLedgerError(ValueError):
    pass


def _text(value: object, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise QuantitativeLedgerError(f"{label} must be exact nonblank text")
    return value


def _finite(value: object, label: str, *, positive: bool = False, nonnegative: bool = False) -> float:
    if type(value) not in (int, float):
        raise QuantitativeLedgerError(f"{label} must be an exact numeric scalar")
    try:
        result = float(value)
    except (OverflowError, ValueError) as exc:
        raise QuantitativeLedgerError(f"{label} must be representable as a finite float") from exc
    if not math.isfinite(result):
        raise QuantitativeLedgerError(f"{label} must be finite")
    if positive and result <= 0.0:
        raise QuantitativeLedgerError(f"{label} must be positive")
    if nonnegative and result < 0.0:
        raise QuantitativeLedgerError(f"{label} must be non-negative")
    return 0.0 if result == 0.0 else result


def _exact_bool(value: object, label: str) -> bool:
    if type(value) is not bool:
        raise QuantitativeLedgerError(f"{label} must be an exact bool")
    return value


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def _require_source_files_current() -> None:
    seen: set[str] = set()
    for relative_path, expected in SOURCE_GIT_BLOB_IDENTITIES:
        if (
            type(relative_path) is not str
            or not relative_path
            or relative_path in seen
            or _GIT_SHA_RE.fullmatch(expected) is None
        ):
            raise QuantitativeLedgerError("quantitative source binding set is malformed")
        seen.add(relative_path)
        path = _REPO_ROOT / relative_path
        if not path.is_file():
            raise QuantitativeLedgerError(f"quantitative source file is missing: {relative_path}")
        actual = _git_blob_sha(path)
        if actual != expected:
            raise QuantitativeLedgerError(
                f"quantitative source moved at {relative_path}; expected {expected}, got {actual}"
            )


def _require_canonical_authority(authority: Authority) -> None:
    if type(authority) is not Authority:
        raise QuantitativeLedgerError("quantitative ledger requires exact Authority type")
    canonical = load_authority()
    if authority.data != canonical.data:
        raise QuantitativeLedgerError("supplied authority differs from released machine authority")
    if str(authority.get("project", "authority_revision")) != AUTHORITY_REVISION:
        raise QuantitativeLedgerError("quantitative authority revision moved")
    if tuple(float(v) for v in authority.get("coordinate_system", "origin")) != (0.0, 0.0, 0.0):
        raise QuantitativeLedgerError("quantitative ledger requires authority-world zero origin")
    if (
        str(authority.get("coordinate_system", "x_positive")) != "wearer_right"
        or str(authority.get("coordinate_system", "y_positive")) != "superior"
        or str(authority.get("coordinate_system", "z_positive")) != "anterior"
    ):
        raise QuantitativeLedgerError("quantitative ledger authority axes moved")
    if str(authority.get("project", "units", "mass")) != "g":
        raise QuantitativeLedgerError("quantitative ledger requires authority mass units in g")
    if str(authority.get("project", "units", "liquid_volume")) != "mL":
        raise QuantitativeLedgerError("quantitative ledger requires authority liquid-volume units in mL")


def _centroid(component) -> tuple[float, float, float]:
    center = component.solid.val().Center()
    values = (float(center.x), float(center.y), float(center.z))
    if not all(math.isfinite(value) for value in values):
        raise QuantitativeLedgerError("component centroid must be finite")
    return values


def _component_map(model: MasckOneModel) -> dict[str, object]:
    if type(model) is not MasckOneModel:
        raise QuantitativeLedgerError("quantitative ledger requires exact MasckOneModel type")
    components = {component.name: component for component in model.components}
    if len(components) != len(model.components):
        raise QuantitativeLedgerError("released model component identities must be unique")
    if tuple(sorted(components)) != EXPECTED_MODEL_COMPONENT_NAMES:
        raise QuantitativeLedgerError("released model component set moved and requires quantitative rebind")
    return components


@dataclass(frozen=True, slots=True)
class MassEntry:
    component_id: str
    source_component_name: str
    accounting_role: str
    mass_g: float | None
    centroid_xyz_mm: tuple[float, float, float] | None
    counted_in_known_subtotal: bool
    source_kind: str
    source_reference: str
    geometry_status: str
    mass_status: str

    def __post_init__(self) -> None:
        for label, value in (
            ("component_id", self.component_id),
            ("source_component_name", self.source_component_name),
            ("source_kind", self.source_kind),
            ("source_reference", self.source_reference),
            ("geometry_status", self.geometry_status),
            ("mass_status", self.mass_status),
        ):
            _text(value, label)
        if self.accounting_role not in ROLE_VOCABULARY:
            raise QuantitativeLedgerError("uncontrolled mass accounting role")
        counted = _exact_bool(self.counted_in_known_subtotal, "counted_in_known_subtotal")
        if counted:
            if self.accounting_role != ROLE_BENCHMARK_MASS_CREDIT:
                raise QuantitativeLedgerError("only explicit benchmark mass credits may enter known subtotal")
            mass = _finite(self.mass_g, "mass_g", positive=True)
            if type(self.centroid_xyz_mm) is not tuple or len(self.centroid_xyz_mm) != 3:
                raise QuantitativeLedgerError("counted mass requires exact centroid XYZ tuple")
            for value in self.centroid_xyz_mm:
                _finite(value, "mass centroid coordinate")
            object.__setattr__(self, "mass_g", mass)
        else:
            if self.mass_g is not None or self.centroid_xyz_mm is not None:
                raise QuantitativeLedgerError("uncounted mass entry cannot silently carry numeric mass arithmetic")

    def manifest(self) -> dict[str, object]:
        self.__post_init__()
        return {
            "component_id": self.component_id,
            "source_component_name": self.source_component_name,
            "accounting_role": self.accounting_role,
            "mass_g": self.mass_g,
            "centroid_xyz_mm": None if self.centroid_xyz_mm is None else list(self.centroid_xyz_mm),
            "counted_in_known_subtotal": self.counted_in_known_subtotal,
            "source_kind": self.source_kind,
            "source_reference": self.source_reference,
            "geometry_status": self.geometry_status,
            "mass_status": self.mass_status,
        }


@dataclass(frozen=True, slots=True)
class KnownContributor:
    contributor_id: str
    known_mass_g: float
    fraction_of_known_subtotal: float

    def __post_init__(self) -> None:
        _text(self.contributor_id, "contributor_id")
        _finite(self.known_mass_g, "known_mass_g", positive=True)
        fraction = _finite(self.fraction_of_known_subtotal, "fraction_of_known_subtotal", positive=True)
        if fraction > 1.0:
            raise QuantitativeLedgerError("known contributor fraction cannot exceed one")

    def manifest(self) -> dict[str, object]:
        self.__post_init__()
        return {
            "contributor_id": self.contributor_id,
            "known_mass_g": self.known_mass_g,
            "fraction_of_known_subtotal": self.fraction_of_known_subtotal,
        }


@dataclass(frozen=True, slots=True)
class MassLedger:
    entries: tuple[MassEntry, ...]
    known_mass_subtotal_g: float
    known_subset_cg_xyz_mm: tuple[float, float, float]
    known_subset_pitch_moment_Nm: float
    dominant_known_contributors: tuple[KnownContributor, ...]
    dry_total_g: None
    loaded_total_g: None
    whole_product_cg_xyz_mm: None
    whole_product_pitch_moment_Nm: None
    dry_target_max_g: float
    loaded_absolute_max_g: float
    cg_z_max_mm: float
    pitch_torque_max_Nm: float
    unresolved_loaded_terms: tuple[str, ...]
    evidence_status: str

    def __post_init__(self) -> None:
        if type(self.entries) is not tuple or not self.entries:
            raise QuantitativeLedgerError("mass ledger requires immutable entries")
        ids = tuple(entry.component_id for entry in self.entries)
        if len(ids) != len(set(ids)):
            raise QuantitativeLedgerError("mass ledger component IDs must be unique")
        for entry in self.entries:
            entry.__post_init__()
        subtotal = _finite(self.known_mass_subtotal_g, "known_mass_subtotal_g", positive=True)
        arithmetic_subtotal = sum(float(entry.mass_g) for entry in self.entries if entry.counted_in_known_subtotal)
        if not math.isclose(subtotal, arithmetic_subtotal, rel_tol=0.0, abs_tol=1e-12):
            raise QuantitativeLedgerError("known mass subtotal does not equal counted entries")
        if not math.isclose(subtotal, EXPECTED_KNOWN_BENCHMARK_SUBTOTAL_G, rel_tol=0.0, abs_tol=1e-12):
            raise QuantitativeLedgerError("legacy known benchmark subtotal must remain exactly 44.4 g")
        if type(self.known_subset_cg_xyz_mm) is not tuple or len(self.known_subset_cg_xyz_mm) != 3:
            raise QuantitativeLedgerError("known subset CG must be exact XYZ tuple")
        for value in self.known_subset_cg_xyz_mm:
            _finite(value, "known subset CG coordinate")
        _finite(self.known_subset_pitch_moment_Nm, "known subset pitch moment", nonnegative=True)
        if type(self.dominant_known_contributors) is not tuple or not self.dominant_known_contributors:
            raise QuantitativeLedgerError("dominant known contributors are required")
        for item in self.dominant_known_contributors:
            item.__post_init__()
        if any(
            value is not None
            for value in (
                self.dry_total_g,
                self.loaded_total_g,
                self.whole_product_cg_xyz_mm,
                self.whole_product_pitch_moment_Nm,
            )
        ):
            raise QuantitativeLedgerError("incomplete ledger cannot promote whole-product mass CG or pitch totals")
        for value, label in (
            (self.dry_target_max_g, "dry target"),
            (self.loaded_absolute_max_g, "loaded absolute max"),
            (self.cg_z_max_mm, "CG Z max"),
            (self.pitch_torque_max_Nm, "pitch torque max"),
        ):
            _finite(value, label, positive=True)
        if self.unresolved_loaded_terms != UNRESOLVED_LOADED_TERMS:
            raise QuantitativeLedgerError("loaded-mass UNKNOWN fields changed")
        if self.evidence_status != MASS_EVIDENCE_STATUS:
            raise QuantitativeLedgerError("mass evidence boundary changed")

    def manifest(self) -> dict[str, object]:
        self.__post_init__()
        return {
            "entries": [entry.manifest() for entry in self.entries],
            "known_mass_subtotal_g": self.known_mass_subtotal_g,
            "known_subset_cg_xyz_mm": list(self.known_subset_cg_xyz_mm),
            "known_subset_pitch_moment_Nm": self.known_subset_pitch_moment_Nm,
            "dominant_known_contributors": [item.manifest() for item in self.dominant_known_contributors],
            "dry_total_g": self.dry_total_g,
            "loaded_total_g": self.loaded_total_g,
            "whole_product_cg_xyz_mm": self.whole_product_cg_xyz_mm,
            "whole_product_pitch_moment_Nm": self.whole_product_pitch_moment_Nm,
            "targets": {
                "dry_target_max_g": self.dry_target_max_g,
                "loaded_absolute_max_g": self.loaded_absolute_max_g,
                "cg_z_max_mm": self.cg_z_max_mm,
                "pitch_torque_max_Nm": self.pitch_torque_max_Nm,
            },
            "unresolved_loaded_terms": list(self.unresolved_loaded_terms),
            "target_pass_claimed": False,
            "evidence_status": self.evidence_status,
        }


@dataclass(frozen=True, slots=True)
class PowerLoad:
    load_id: str
    quantity: int
    nominal_voltage_V: None
    nominal_power_W: None
    source_class: str
    source_status: str
    measured: bool

    def __post_init__(self) -> None:
        if self.load_id not in POWER_LOAD_IDS:
            raise QuantitativeLedgerError("power load ID is not controlled")
        if type(self.quantity) is not int or self.quantity <= 0:
            raise QuantitativeLedgerError("power load quantity must be exact positive int")
        if self.nominal_voltage_V is not None or self.nominal_power_W is not None:
            raise QuantitativeLedgerError("unselected power loads must remain numerically UNKNOWN")
        _text(self.source_class, "power source_class")
        _text(self.source_status, "power source_status")
        if self.source_class != "UNRESOLVED":
            raise QuantitativeLedgerError("power source class cannot be promoted without selected hardware")
        if self.source_status != "BLOCKED_PENDING_SELECTED_HARDWARE_OR_CONTROLLED_SUPPLIER_POWER_EVIDENCE":
            raise QuantitativeLedgerError("power load evidence status changed")
        if _exact_bool(self.measured, "power measured"):
            raise QuantitativeLedgerError("unresolved power load cannot be marked measured")

    def manifest(self) -> dict[str, object]:
        self.__post_init__()
        return {
            "load_id": self.load_id,
            "quantity": self.quantity,
            "nominal_voltage_V": self.nominal_voltage_V,
            "nominal_power_W": self.nominal_power_W,
            "source_class": self.source_class,
            "source_status": self.source_status,
            "measured": self.measured,
        }


@dataclass(frozen=True, slots=True)
class PowerLedger:
    battery_candidate: str
    battery_nominal_voltage_V: float
    battery_nameplate_capacity_mAh: float
    battery_source_status: str
    loads: tuple[PowerLoad, ...]
    total_power_W: None
    runtime_estimate_h: None
    runtime_validated: bool
    evidence_status: str

    def __post_init__(self) -> None:
        _text(self.battery_candidate, "battery candidate")
        _finite(self.battery_nominal_voltage_V, "battery nominal voltage", positive=True)
        _finite(self.battery_nameplate_capacity_mAh, "battery nameplate capacity", positive=True)
        _text(self.battery_source_status, "battery source status")
        if tuple(load.load_id for load in self.loads) != POWER_LOAD_IDS:
            raise QuantitativeLedgerError("power loads must retain controlled donor order")
        for load in self.loads:
            load.__post_init__()
        if self.total_power_W is not None or self.runtime_estimate_h is not None:
            raise QuantitativeLedgerError("power total and runtime must remain UNKNOWN until load evidence closes")
        if _exact_bool(self.runtime_validated, "runtime_validated"):
            raise QuantitativeLedgerError("nameplate arithmetic cannot validate runtime")
        if self.evidence_status != POWER_EVIDENCE_STATUS:
            raise QuantitativeLedgerError("power evidence boundary changed")

    def manifest(self) -> dict[str, object]:
        self.__post_init__()
        return {
            "battery_candidate": self.battery_candidate,
            "battery_nominal_voltage_V": self.battery_nominal_voltage_V,
            "battery_nameplate_capacity_mAh": self.battery_nameplate_capacity_mAh,
            "battery_source_status": self.battery_source_status,
            "loads": [load.manifest() for load in self.loads],
            "total_power_W": self.total_power_W,
            "runtime_estimate_h": self.runtime_estimate_h,
            "runtime_validated": self.runtime_validated,
            "evidence_status": self.evidence_status,
        }


@dataclass(frozen=True, slots=True)
class FluidLedger:
    water_reservoir_gross_mL: float
    water_reservoir_minimum_usable_mL: float
    face_water_per_clean_mL: float
    cleanser_per_clean_mL: float
    post_flush_water_per_clean_mL: float
    nominal_introduced_liquid_per_clean_mL: float
    maximum_initial_prime_mL: float
    waste_recovery_ratio_min: float
    residual_free_liquid_max_uL: float
    cartridge_retained_capacity_min_mL: float
    cartridge_service_cycles_baseline: int
    water_loaded_mass_g: None
    cleanser_loaded_mass_g: None
    waste_loaded_mass_g: None
    evidence_status: str

    def __post_init__(self) -> None:
        values = (
            (self.water_reservoir_gross_mL, "water reservoir gross"),
            (self.water_reservoir_minimum_usable_mL, "water reservoir usable"),
            (self.face_water_per_clean_mL, "face water per CLEAN"),
            (self.cleanser_per_clean_mL, "cleanser per CLEAN"),
            (self.post_flush_water_per_clean_mL, "post-flush water per CLEAN"),
            (self.nominal_introduced_liquid_per_clean_mL, "nominal introduced liquid"),
            (self.maximum_initial_prime_mL, "maximum initial prime"),
            (self.cartridge_retained_capacity_min_mL, "cartridge retained capacity"),
        )
        for value, label in values:
            _finite(value, label, positive=True)
        recovery = _finite(self.waste_recovery_ratio_min, "waste recovery ratio", positive=True)
        if recovery > 1.0:
            raise QuantitativeLedgerError("waste recovery ratio cannot exceed one")
        _finite(self.residual_free_liquid_max_uL, "residual free liquid max", nonnegative=True)
        if type(self.cartridge_service_cycles_baseline) is not int or self.cartridge_service_cycles_baseline <= 0:
            raise QuantitativeLedgerError("cartridge service cycles must be exact positive int")
        expected_cycle = self.face_water_per_clean_mL + self.cleanser_per_clean_mL + self.post_flush_water_per_clean_mL
        if not math.isclose(self.nominal_introduced_liquid_per_clean_mL, expected_cycle, rel_tol=0.0, abs_tol=1e-12):
            raise QuantitativeLedgerError("clean-cycle constituent volumes no longer reconcile to nominal introduced liquid")
        if any(value is not None for value in (self.water_loaded_mass_g, self.cleanser_loaded_mass_g, self.waste_loaded_mass_g)):
            raise QuantitativeLedgerError("fluid volume cannot silently become loaded mass without controlled density/mass provenance")
        if self.evidence_status != FLUID_EVIDENCE_STATUS:
            raise QuantitativeLedgerError("fluid evidence boundary changed")

    def manifest(self) -> dict[str, object]:
        self.__post_init__()
        return {
            "water_reservoir_gross_mL": self.water_reservoir_gross_mL,
            "water_reservoir_minimum_usable_mL": self.water_reservoir_minimum_usable_mL,
            "clean_cycle": {
                "face_water_mL": self.face_water_per_clean_mL,
                "cleanser_mL": self.cleanser_per_clean_mL,
                "post_flush_water_mL": self.post_flush_water_per_clean_mL,
                "nominal_introduced_liquid_mL": self.nominal_introduced_liquid_per_clean_mL,
                "maximum_initial_prime_mL": self.maximum_initial_prime_mL,
            },
            "waste_recovery_ratio_min": self.waste_recovery_ratio_min,
            "residual_free_liquid_max_uL": self.residual_free_liquid_max_uL,
            "cartridge_retained_capacity_min_mL": self.cartridge_retained_capacity_min_mL,
            "cartridge_service_cycles_baseline": self.cartridge_service_cycles_baseline,
            "loaded_mass_g": {
                "water": self.water_loaded_mass_g,
                "cleanser": self.cleanser_loaded_mass_g,
                "waste": self.waste_loaded_mass_g,
            },
            "evidence_status": self.evidence_status,
        }


@dataclass(frozen=True, slots=True)
class CurrentQuantitativeLedger:
    schema: str
    source_main_sha: str
    authority_revision: str
    authority_blob_sha: str
    source_git_blob_identities: tuple[tuple[str, str], ...]
    coordinate_frame_id: str
    transform_semantics: str
    legacy_mass_donor_pr: int
    legacy_mass_donor_head_sha: str
    legacy_power_donor_pr: int
    legacy_power_donor_head_sha: str
    mass: MassLedger
    power: PowerLedger
    fluid: FluidLedger
    whole_product_component_coverage_complete: bool
    physical_validation_eligible: bool
    evidence_status: str

    def __post_init__(self) -> None:
        if self.schema != SCHEMA:
            raise QuantitativeLedgerError("unexpected quantitative ledger schema")
        if self.source_main_sha != SOURCE_MAIN_SHA or _GIT_SHA_RE.fullmatch(self.source_main_sha) is None:
            raise QuantitativeLedgerError("quantitative ledger is stale for released main")
        if self.authority_revision != AUTHORITY_REVISION:
            raise QuantitativeLedgerError("quantitative ledger authority revision moved")
        if self.authority_blob_sha != AUTHORITY_BLOB_SHA or _GIT_SHA_RE.fullmatch(self.authority_blob_sha) is None:
            raise QuantitativeLedgerError("quantitative ledger authority blob moved")
        if self.source_git_blob_identities != SOURCE_GIT_BLOB_IDENTITIES:
            raise QuantitativeLedgerError("quantitative source graph changed")
        if len(self.source_git_blob_identities) != len({path for path, _ in self.source_git_blob_identities}):
            raise QuantitativeLedgerError("quantitative source graph contains duplicate paths")
        if self.coordinate_frame_id != WORLD_FRAME_ID:
            raise QuantitativeLedgerError("quantitative ledger must use canonical authority world frame")
        if self.transform_semantics != "IDENTITY_SOURCE_GEOMETRY_ALREADY_IN_AUTHORITY_WORLD_MM":
            raise QuantitativeLedgerError("quantitative ledger transform semantics changed")
        if self.legacy_mass_donor_pr != LEGACY_MASS_DONOR_PR or self.legacy_mass_donor_head_sha != LEGACY_MASS_DONOR_HEAD_SHA:
            raise QuantitativeLedgerError("legacy mass donor provenance changed")
        if self.legacy_power_donor_pr != LEGACY_POWER_DONOR_PR or self.legacy_power_donor_head_sha != LEGACY_POWER_DONOR_HEAD_SHA:
            raise QuantitativeLedgerError("legacy power donor provenance changed")
        if _GIT_SHA_RE.fullmatch(self.legacy_mass_donor_head_sha) is None or _GIT_SHA_RE.fullmatch(self.legacy_power_donor_head_sha) is None:
            raise QuantitativeLedgerError("legacy donor head identity is malformed")
        self.mass.__post_init__()
        self.power.__post_init__()
        self.fluid.__post_init__()
        if _exact_bool(self.whole_product_component_coverage_complete, "whole_product_component_coverage_complete"):
            raise QuantitativeLedgerError("current quantitative ledger cannot claim complete component mass coverage")
        if _exact_bool(self.physical_validation_eligible, "physical_validation_eligible"):
            raise QuantitativeLedgerError("digital quantitative ledger cannot become physical validation evidence")
        if self.evidence_status != EVIDENCE_STATUS:
            raise QuantitativeLedgerError("quantitative evidence boundary changed")

    @property
    def manifest_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        return sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        self.__post_init__()
        payload: dict[str, object] = {
            "schema": self.schema,
            "source_main_sha": self.source_main_sha,
            "authority_revision": self.authority_revision,
            "authority_blob_sha": self.authority_blob_sha,
            "source_git_blob_identities": [list(item) for item in self.source_git_blob_identities],
            "coordinate_frame_id": self.coordinate_frame_id,
            "transform_semantics": self.transform_semantics,
            "legacy_donor_provenance": {
                "mass": {
                    "pr": self.legacy_mass_donor_pr,
                    "head_sha": self.legacy_mass_donor_head_sha,
                    "consumed_as_authority": False,
                    "ported_semantics": "KNOWN_44_4_G_BENCHMARK_SUBTOTAL_AND_EXPLICIT_UNKNOWN_WHOLE_PRODUCT_FIELDS_ONLY",
                },
                "power": {
                    "pr": self.legacy_power_donor_pr,
                    "head_sha": self.legacy_power_donor_head_sha,
                    "consumed_as_authority": False,
                    "ported_semantics": "CONTROLLED_LOAD_IDENTITY_AND_EXPLICIT_UNKNOWN_POWER_RUNTIME_FIELDS_ONLY",
                },
            },
            "mass": self.mass.manifest(),
            "power": self.power.manifest(),
            "fluid": self.fluid.manifest(),
            "whole_product_component_coverage_complete": self.whole_product_component_coverage_complete,
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            payload["manifest_sha256"] = self.manifest_sha256
        return payload

    def validate_current_sources(self) -> None:
        _require_source_files_current()
        authority = load_authority()
        _require_canonical_authority(authority)
        current = build_current_quantitative_ledger(authority=authority, validate_sources=False)
        if current.manifest() != self.manifest():
            raise QuantitativeLedgerError("quantitative ledger no longer matches current released source reconstruction")


def _unresolved_mass_entry(component, component_id: str, role: str) -> MassEntry:
    return MassEntry(
        component_id=component_id,
        source_component_name=component.name,
        accounting_role=role,
        mass_g=None,
        centroid_xyz_mm=None,
        counted_in_known_subtotal=False,
        source_kind="CURRENT_MAIN_MODEL_GEOMETRY_WITHOUT_CONTROLLED_MASS_EVIDENCE",
        source_reference="src/masck_one/model.py",
        geometry_status=component.status,
        mass_status="BLOCKED_NO_CONTROLLED_MATERIAL_DENSITY_SUPPLIER_MASS_OR_MEASURED_PART_MASS",
    )


def _reference_mass_entry(component, component_id: str) -> MassEntry:
    return MassEntry(
        component_id=component_id,
        source_component_name=component.name,
        accounting_role=ROLE_REFERENCE_EXCLUDED,
        mass_g=None,
        centroid_xyz_mm=None,
        counted_in_known_subtotal=False,
        source_kind="CURRENT_MAIN_REFERENCE_GEOMETRY",
        source_reference="src/masck_one/model.py",
        geometry_status=component.status,
        mass_status="REFERENCE_GEOMETRY_EXCLUDED_FROM_PHYSICAL_MASS_ARITHMETIC",
    )


def _mass_entries(authority: Authority, model: MasckOneModel) -> tuple[MassEntry, ...]:
    components = _component_map(model)
    entries: list[MassEntry] = [
        _unresolved_mass_entry(components["rigid_shell"], "LIVE-MAIN-RIGID-SHELL", ROLE_PHYSICAL_MASS_UNKNOWN),
        _reference_mass_entry(components["nasal_lobe_membrane_reference"], "NASAL-INTERFACE-REFERENCE"),
        _unresolved_mass_entry(
            components["water_reservoir_envelope"],
            "WATER-RESERVOIR-DRY-ASSEMBLY",
            ROLE_PACKAGE_REFERENCE_MASS_UNKNOWN,
        ),
        _unresolved_mass_entry(
            components["waste_cartridge_envelope"],
            "WASTE-CARTRIDGE-DRY-ASSEMBLY",
            ROLE_PACKAGE_REFERENCE_MASS_UNKNOWN,
        ),
        MassEntry(
            component_id="BATTERY-REFERENCE-BENCHMARK",
            source_component_name="battery_reference_envelope",
            accounting_role=ROLE_BENCHMARK_MASS_CREDIT,
            mass_g=float(authority.get("battery_reference", "mass_g")),
            centroid_xyz_mm=_centroid(components["battery_reference_envelope"]),
            counted_in_known_subtotal=True,
            source_kind="AUTHORITY_SUPPLIER_PACKAGING_BENCHMARK",
            source_reference=str(authority.get("battery_reference", "candidate")),
            geometry_status=components["battery_reference_envelope"].status,
            mass_status=str(authority.get("battery_reference", "status")),
        ),
    ]
    for zone, source_name in zip("ABCD", (f"actuator_envelope_{index}" for index in range(1, 5)), strict=True):
        component = components[source_name]
        entries.append(
            MassEntry(
                component_id=f"ACTUATOR-ZONE-{zone}",
                source_component_name=source_name,
                accounting_role=ROLE_BENCHMARK_MASS_CREDIT,
                mass_g=SUPPLIER_ACTUATOR_TOTAL_MASS_G,
                centroid_xyz_mm=_centroid(component),
                counted_in_known_subtotal=True,
                source_kind="SUPPLIER_SIBLING_MODEL_MASS_BENCHMARK",
                source_reference=(
                    f"package candidate {SUPPLIER_ACTUATOR_PACKAGE_MODEL}; mass source sibling "
                    f"{SUPPLIER_ACTUATOR_MASS_SOURCE_MODEL}; published total mass "
                    f"{SUPPLIER_ACTUATOR_TOTAL_MASS_G} g; {SUPPLIER_ACTUATOR_SOURCE_URL}; "
                    f"retrieved {SUPPLIER_ACTUATOR_SOURCE_RETRIEVED}"
                ),
                geometry_status=component.status,
                mass_status=SUPPLIER_ACTUATOR_PROVENANCE,
            )
        )
    for name in (
        "visual_eye_left",
        "visual_eye_right",
        "visual_mouth",
        "visual_nostril_left",
        "visual_nostril_right",
    ):
        entries.append(_reference_mass_entry(components[name], f"REFERENCE-{name.upper().replace('_', '-')}"))
    return tuple(entries)


def _known_arithmetic(entries: tuple[MassEntry, ...]) -> tuple[float, tuple[float, float, float], float, tuple[KnownContributor, ...]]:
    known = tuple(entry for entry in entries if entry.counted_in_known_subtotal)
    subtotal = sum(float(entry.mass_g) for entry in known)
    if not math.isclose(subtotal, EXPECTED_KNOWN_BENCHMARK_SUBTOTAL_G, rel_tol=0.0, abs_tol=1e-12):
        raise QuantitativeLedgerError("known benchmark subtotal moved")
    cg = tuple(
        sum(float(entry.mass_g) * float(entry.centroid_xyz_mm[axis]) for entry in known) / subtotal
        for axis in range(3)
    )
    pitch = subtotal / 1000.0 * STANDARD_GRAVITY_M_S2 * abs(cg[2]) / 1000.0
    grouped = (
        ("FOUR_ACTUATOR_SIBLING_MODEL_MASS_BENCHMARKS", sum(float(entry.mass_g) for entry in known if entry.component_id.startswith("ACTUATOR-ZONE-"))),
        ("BATTERY_REFERENCE_BENCHMARK", sum(float(entry.mass_g) for entry in known if entry.component_id.startswith("BATTERY-"))),
    )
    contributors = tuple(
        KnownContributor(identifier, value, value / subtotal)
        for identifier, value in grouped
        if value > 0.0
    )
    return subtotal, (cg[0], cg[1], cg[2]), pitch, contributors


def _build_mass_ledger(authority: Authority, model: MasckOneModel) -> MassLedger:
    entries = _mass_entries(authority, model)
    subtotal, cg, pitch, contributors = _known_arithmetic(entries)
    return MassLedger(
        entries=entries,
        known_mass_subtotal_g=subtotal,
        known_subset_cg_xyz_mm=cg,
        known_subset_pitch_moment_Nm=pitch,
        dominant_known_contributors=contributors,
        dry_total_g=None,
        loaded_total_g=None,
        whole_product_cg_xyz_mm=None,
        whole_product_pitch_moment_Nm=None,
        dry_target_max_g=float(authority.get("mass", "dry_target_max_g")),
        loaded_absolute_max_g=float(authority.get("mass", "loaded_absolute_max_g")),
        cg_z_max_mm=float(authority.get("mass", "cg_z_max_mm")),
        pitch_torque_max_Nm=float(authority.get("mass", "pitch_torque_max_Nm")),
        unresolved_loaded_terms=UNRESOLVED_LOADED_TERMS,
        evidence_status=MASS_EVIDENCE_STATUS,
    )


def _build_power_ledger(authority: Authority) -> PowerLedger:
    unresolved = "BLOCKED_PENDING_SELECTED_HARDWARE_OR_CONTROLLED_SUPPLIER_POWER_EVIDENCE"
    loads = tuple(
        PowerLoad(load_id, quantity, None, None, "UNRESOLVED", unresolved, False)
        for load_id, quantity in (
            ("ACTUATORS_X4", 4),
            ("FRESH_WATER_PUMP", 1),
            ("CLEANSER_PUMP", 1),
            ("WASTE_PUMP", 1),
            ("CONTROL_ELECTRONICS", 1),
            ("PHYSICAL_HMI_STATUS", 1),
            ("WARM", 2),
            ("COOL_EXPERIMENTAL", 1),
        )
    )
    return PowerLedger(
        battery_candidate=str(authority.get("battery_reference", "candidate")),
        battery_nominal_voltage_V=float(authority.get("battery_reference", "nominal_voltage_V")),
        battery_nameplate_capacity_mAh=float(authority.get("battery_reference", "capacity_mAh")),
        battery_source_status=str(authority.get("battery_reference", "status")),
        loads=loads,
        total_power_W=None,
        runtime_estimate_h=None,
        runtime_validated=False,
        evidence_status=POWER_EVIDENCE_STATUS,
    )


def _build_fluid_ledger(authority: Authority) -> FluidLedger:
    return FluidLedger(
        water_reservoir_gross_mL=float(authority.get("fluid", "water_reservoir", "gross_mL")),
        water_reservoir_minimum_usable_mL=float(authority.get("fluid", "water_reservoir", "minimum_usable_mL")),
        face_water_per_clean_mL=float(authority.get("fluid", "clean_cycle", "face_water_mL")),
        cleanser_per_clean_mL=float(authority.get("fluid", "clean_cycle", "cleanser_mL")),
        post_flush_water_per_clean_mL=float(authority.get("fluid", "clean_cycle", "post_flush_water_mL")),
        nominal_introduced_liquid_per_clean_mL=float(authority.get("fluid", "clean_cycle", "nominal_introduced_liquid_mL")),
        maximum_initial_prime_mL=float(authority.get("fluid", "clean_cycle", "maximum_initial_prime_mL")),
        waste_recovery_ratio_min=float(authority.get("fluid", "waste", "recovery_ratio_min")),
        residual_free_liquid_max_uL=float(authority.get("fluid", "waste", "residual_free_liquid_max_uL")),
        cartridge_retained_capacity_min_mL=float(authority.get("fluid", "cartridge", "retained_capacity_min_mL")),
        cartridge_service_cycles_baseline=int(authority.get("fluid", "cartridge", "service_cycles_baseline")),
        water_loaded_mass_g=None,
        cleanser_loaded_mass_g=None,
        waste_loaded_mass_g=None,
        evidence_status=FLUID_EVIDENCE_STATUS,
    )


def build_current_quantitative_ledger(
    authority: Authority | None = None,
    *,
    validate_sources: bool = True,
) -> CurrentQuantitativeLedger:
    if validate_sources:
        _require_source_files_current()
    authority = authority or load_authority()
    _require_canonical_authority(authority)
    model = build_model(authority)
    _component_map(model)
    ledger = CurrentQuantitativeLedger(
        schema=SCHEMA,
        source_main_sha=SOURCE_MAIN_SHA,
        authority_revision=AUTHORITY_REVISION,
        authority_blob_sha=AUTHORITY_BLOB_SHA,
        source_git_blob_identities=SOURCE_GIT_BLOB_IDENTITIES,
        coordinate_frame_id=WORLD_FRAME_ID,
        transform_semantics="IDENTITY_SOURCE_GEOMETRY_ALREADY_IN_AUTHORITY_WORLD_MM",
        legacy_mass_donor_pr=LEGACY_MASS_DONOR_PR,
        legacy_mass_donor_head_sha=LEGACY_MASS_DONOR_HEAD_SHA,
        legacy_power_donor_pr=LEGACY_POWER_DONOR_PR,
        legacy_power_donor_head_sha=LEGACY_POWER_DONOR_HEAD_SHA,
        mass=_build_mass_ledger(authority, model),
        power=_build_power_ledger(authority),
        fluid=_build_fluid_ledger(authority),
        whole_product_component_coverage_complete=False,
        physical_validation_eligible=False,
        evidence_status=EVIDENCE_STATUS,
    )
    ledger.__post_init__()
    return ledger
