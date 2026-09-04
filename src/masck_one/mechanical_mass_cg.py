"""Geometry-bound, provenance-explicit mass/CG ledger for the Manual A candidate.

Only controlled or traceable supplier masses are numerically credited. Positive-volume
CAD with no controlled material/density remains unresolved rather than receiving an
invented density. Loaded liquid masses also remain unresolved until controlled fluid
mass/density evidence exists.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math

from .authority import Authority, load_authority
from .frame_shell_attachment import build_frame_shell_attachment
from .mechanical_integration import MechanicalRealization, build_mechanical_realization
from .model import MasckOneModel, build_model


SCHEMA = "MASCK_ONE_MECHANICAL_MASS_CG_V2"
STANDARD_GRAVITY_M_S2 = 9.80665

# The package candidate remains the hollow-shaft 2IBH reference. H2W's currently
# published 5.6 g total mass is for the closely related 2IB model, so it is carried
# only as an explicit sibling-model benchmark. It is not an exact 2IBH production mass.
SUPPLIER_ACTUATOR_MODEL = "H2W NCM01-04-001-2IBH"
SUPPLIER_ACTUATOR_MASS_SOURCE_MODEL = "H2W NCM01-04-001-2IB"
SUPPLIER_ACTUATOR_TOTAL_MASS_G = 5.6
SUPPLIER_ACTUATOR_SOURCE_URL = "https://www.h2wtech.com/product/voice-coil-actuators/NCM01-04-001-2IB"
SUPPLIER_ACTUATOR_SOURCE_RETRIEVED = "2026-09-04"
SUPPLIER_ACTUATOR_PROVENANCE = (
    "SUPPLIER_PUBLISHED_SIBLING_MODEL_TOTAL_MASS_BENCHMARK_"
    "NOT_EXACT_2IBH_OR_PRODUCTION_FREEZE"
)


class MechanicalMassCgError(ValueError):
    pass


def _text(value: object, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise MechanicalMassCgError(f"{label} must be exact nonblank text")
    return value


def _mass(value: object, label: str) -> float:
    if type(value) not in (int, float):
        raise MechanicalMassCgError(f"{label} must be exact numeric")
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise MechanicalMassCgError(f"{label} must be finite and non-negative")
    return result


@dataclass(frozen=True, slots=True)
class MassEntry:
    component_id: str
    mass_g: float | None
    centroid_xyz_mm: tuple[float, float, float] | None
    source_kind: str
    source_reference: str
    geometry_status: str
    mass_status: str

    def __post_init__(self) -> None:
        for label, value in (
            ("component_id", self.component_id),
            ("source_kind", self.source_kind),
            ("source_reference", self.source_reference),
            ("geometry_status", self.geometry_status),
            ("mass_status", self.mass_status),
        ):
            _text(value, label)
        if self.mass_g is None:
            if self.centroid_xyz_mm is not None:
                raise MechanicalMassCgError("unresolved mass cannot contribute a numeric centroid to mass arithmetic")
        else:
            object.__setattr__(self, "mass_g", _mass(self.mass_g, "mass_g"))
            if type(self.centroid_xyz_mm) is not tuple or len(self.centroid_xyz_mm) != 3:
                raise MechanicalMassCgError("known mass entry requires exact centroid XYZ tuple")
            if any(type(value) not in (int, float) or not math.isfinite(float(value)) for value in self.centroid_xyz_mm):
                raise MechanicalMassCgError("known mass centroid coordinates must be finite numeric scalars")

    @property
    def known(self) -> bool:
        return self.mass_g is not None

    def manifest(self) -> dict[str, object]:
        return {
            "component_id": self.component_id,
            "mass_g": self.mass_g,
            "centroid_xyz_mm": None if self.centroid_xyz_mm is None else list(self.centroid_xyz_mm),
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

    def manifest(self) -> dict[str, object]:
        return {
            "contributor_id": self.contributor_id,
            "known_mass_g": self.known_mass_g,
            "fraction_of_known_subtotal": self.fraction_of_known_subtotal,
        }


@dataclass(frozen=True, slots=True)
class MechanicalMassCgLedger:
    authority_revision: str
    entries: tuple[MassEntry, ...]
    known_mass_subtotal_g: float
    known_subset_cg_xyz_mm: tuple[float, float, float]
    known_subset_pitch_moment_Nm: float
    dominant_known_contributors: tuple[KnownContributor, ...]
    dry_total_g: float | None
    loaded_total_g: float | None
    whole_product_cg_xyz_mm: tuple[float, float, float] | None
    whole_product_pitch_moment_Nm: float | None
    dry_target_max_g: float
    loaded_absolute_max_g: float
    cg_z_max_mm: float
    pitch_torque_max_Nm: float
    unresolved_loaded_terms: tuple[str, ...]
    evidence_status: str

    def __post_init__(self) -> None:
        _text(self.authority_revision, "authority_revision")
        if type(self.entries) is not tuple or not self.entries:
            raise MechanicalMassCgError("mass ledger requires entries")
        if len({entry.component_id for entry in self.entries}) != len(self.entries):
            raise MechanicalMassCgError("mass ledger component IDs must be unique")
        if any(value is not None for value in (self.dry_total_g, self.loaded_total_g, self.whole_product_cg_xyz_mm, self.whole_product_pitch_moment_Nm)):
            raise MechanicalMassCgError("incomplete component ledger cannot promote whole-product totals")
        _text(self.evidence_status, "evidence_status")

    @property
    def unresolved_component_ids(self) -> tuple[str, ...]:
        return tuple(entry.component_id for entry in self.entries if not entry.known)

    @property
    def ledger_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "authority_revision": self.authority_revision,
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
            "unresolved_component_ids": list(self.unresolved_component_ids),
            "unresolved_loaded_terms": list(self.unresolved_loaded_terms),
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            payload["ledger_sha256"] = self.ledger_sha256
        return payload


def _centroid(solid) -> tuple[float, float, float]:
    center = solid.val().Center()
    return float(center.x), float(center.y), float(center.z)


def _unresolved(component_id: str, source_reference: str, geometry_status: str) -> MassEntry:
    return MassEntry(
        component_id=component_id,
        mass_g=None,
        centroid_xyz_mm=None,
        source_kind="UNRESOLVED_PLACEHOLDER",
        source_reference=source_reference,
        geometry_status=geometry_status,
        mass_status="BLOCKED_NO_CONTROLLED_MATERIAL_DENSITY_SUPPLIER_MASS_OR_MEASURED_PART_MASS",
    )


def _entries(
    authority: Authority,
    model: MasckOneModel,
    realization: MechanicalRealization,
) -> tuple[MassEntry, ...]:
    parts = {part.part_id: part for part in realization.realized_parts}
    attachment = build_frame_shell_attachment(authority)

    result: list[MassEntry] = [
        MassEntry(
            component_id="BATTERY-REFERENCE-BENCHMARK",
            mass_g=float(authority.get("battery_reference", "mass_g")),
            centroid_xyz_mm=_centroid(model.battery_reference_envelope.solid),
            source_kind="AUTHORITY_SUPPLIER_PACKAGING_BENCHMARK",
            source_reference=str(authority.get("battery_reference", "candidate")),
            geometry_status=model.battery_reference_envelope.status,
            mass_status=str(authority.get("battery_reference", "status")),
        )
    ]

    for zone in "ABCD":
        actuator = parts[f"ACTUATOR-ZONE-{zone}"]
        result.append(
            MassEntry(
                component_id=f"ACTUATOR-ZONE-{zone}",
                mass_g=SUPPLIER_ACTUATOR_TOTAL_MASS_G,
                centroid_xyz_mm=actuator.centroid_xyz_mm,
                source_kind="SUPPLIER_SIBLING_MODEL_MASS_BENCHMARK",
                source_reference=(
                    f"package candidate {SUPPLIER_ACTUATOR_MODEL}; mass source sibling "
                    f"{SUPPLIER_ACTUATOR_MASS_SOURCE_MODEL}; published total mass "
                    f"{SUPPLIER_ACTUATOR_TOTAL_MASS_G} g; {SUPPLIER_ACTUATOR_SOURCE_URL}; "
                    f"retrieved {SUPPLIER_ACTUATOR_SOURCE_RETRIEVED}"
                ),
                geometry_status=actuator.geometry_status,
                mass_status=SUPPLIER_ACTUATOR_PROVENANCE,
            )
        )

    unresolved_realized_ids = (
        "LIVE-MAIN-RIGID-SHELL",
        "LOWER-SERVICE-DOOR-ENVELOPE",
        "FRAME-PERIMETER-REACTION",
        *(f"REACTION-ACTUATOR-ZONE-{zone}" for zone in "ABCD"),
        "RETENTION-HALO-OCCIPITAL-CROWN",
        "RETENTION-YOKE-LEFT",
        "RETENTION-YOKE-RIGHT-FIXED",
        "QUICK-RELEASE-LATCH-MOVING",
        "QUICK-RELEASE-GUARD",
    )
    for part_id in unresolved_realized_ids:
        part = parts[part_id]
        result.append(_unresolved(part_id, "MANUAL_A_REALIZED_CAD_VOLUME", part.geometry_status))

    result.extend(
        (
            _unresolved("NASAL-INTERFACE-REFERENCE", "LIVE_MAIN_MODEL_COMPONENT", model.nasal_interface.status),
            _unresolved("WATER-RESERVOIR-DRY-ASSEMBLY", "LIVE_MAIN_MODEL_COMPONENT", model.water_reservoir_envelope.status),
            _unresolved("WASTE-CARTRIDGE-DRY-ASSEMBLY", "LIVE_MAIN_MODEL_COMPONENT", model.waste_cartridge_envelope.status),
        )
    )
    for bridge in attachment.bridges:
        result.append(_unresolved(bridge.bridge_id, "MANUAL_A_FRAME_SHELL_ATTACHMENT_CAD_VOLUME", bridge.geometry_status))
    return tuple(result)


def _known_arithmetic(entries: tuple[MassEntry, ...]) -> tuple[float, tuple[float, float, float], float, tuple[KnownContributor, ...]]:
    known = tuple(entry for entry in entries if entry.known)
    total = sum(float(entry.mass_g) for entry in known)
    if total <= 0.0:
        raise MechanicalMassCgError("known mass subtotal must be positive")
    cg = tuple(
        sum(float(entry.mass_g) * float(entry.centroid_xyz_mm[axis]) for entry in known) / total
        for axis in range(3)
    )
    pitch = total / 1000.0 * STANDARD_GRAVITY_M_S2 * abs(cg[2]) / 1000.0

    grouped: dict[str, float] = {
        "BATTERY_REFERENCE_BENCHMARK": sum(float(entry.mass_g) for entry in known if entry.component_id.startswith("BATTERY-")),
        "FOUR_ACTUATOR_SIBLING_MODEL_MASS_BENCHMARKS": sum(float(entry.mass_g) for entry in known if entry.component_id.startswith("ACTUATOR-ZONE-")),
    }
    dominant = tuple(
        KnownContributor(key, value, value / total)
        for key, value in sorted(grouped.items(), key=lambda item: item[1], reverse=True)
        if value > 0.0
    )
    return total, (cg[0], cg[1], cg[2]), pitch, dominant


def build_mechanical_mass_cg_ledger(
    authority: Authority | None = None,
) -> MechanicalMassCgLedger:
    authority = authority or load_authority()
    model = build_model(authority)
    realization = build_mechanical_realization(authority)
    entries = _entries(authority, model, realization)
    known_mass, known_cg, known_pitch, dominant = _known_arithmetic(entries)
    return MechanicalMassCgLedger(
        authority_revision=str(authority.get("project", "authority_revision")),
        entries=entries,
        known_mass_subtotal_g=known_mass,
        known_subset_cg_xyz_mm=known_cg,
        known_subset_pitch_moment_Nm=known_pitch,
        dominant_known_contributors=dominant,
        dry_total_g=None,
        loaded_total_g=None,
        whole_product_cg_xyz_mm=None,
        whole_product_pitch_moment_Nm=None,
        dry_target_max_g=float(authority.get("mass", "dry_target_max_g")),
        loaded_absolute_max_g=float(authority.get("mass", "loaded_absolute_max_g")),
        cg_z_max_mm=float(authority.get("mass", "cg_z_max_mm")),
        pitch_torque_max_Nm=float(authority.get("mass", "pitch_torque_max_Nm")),
        unresolved_loaded_terms=(
            "WATER_LOAD_MASS_BLOCKED_PENDING_CONTROLLED_FLUID_MASS_OR_DENSITY_PROVENANCE",
            "CLEANSER_LOAD_MASS_BLOCKED_PENDING_SELECTED_CLEANSER_AND_CONTROLLED_MASS_OR_DENSITY_PROVENANCE",
            "WASTE_LOAD_MASS_BLOCKED_PENDING_REALIZED_CARTRIDGE_MEDIA_AND_CONTROLLED_PHYSICAL_MASS_EVIDENCE",
        ),
        evidence_status=(
            "KNOWN_DRY_SUBSET_USES_AUTHORITY_BATTERY_BENCHMARK_AND_H2W_2IB_SIBLING_MODEL_"
            "PUBLISHED_MASS_BENCHMARK_ONLY_EXACT_2IBH_MASS_UNRESOLVED_"
            "FULL_DRY_LOADED_CG_AND_PITCH_REMAIN_BLOCKED_NOT_PHYSICAL_VALIDATION"
        ),
    )