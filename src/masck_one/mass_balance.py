"""Whole-product mass, centre-of-gravity and head-load closure.

`config/masck_one_authority.yaml` states four wearer-load limits -- a dry mass
target, an absolute loaded mass, a maximum CG height and a maximum head pitch
torque -- and cross-checks none of them against each other. They are not
independent: for a mask worn on a face, pitch torque is what the three others
produce.

    tau = m * g * z_cg

Checking that relation across the released limit set shows the set does not
close. A Masck One built exactly to its own maxima is non-compliant at the
condition that matters most.

Mass evidence
-------------
This module will not invent mass. The repository holds packaging *envelopes*,
not manufactured material, and an envelope bounds a volume rather than
establishing what is inside it. Every ledger entry therefore carries an explicit
evidence class, and a ledger containing any unresolved entry reports its total
as a lower bound rather than as the product mass.

Liquid charges are the exception: they are real masses derivable from the
released fluid authority and known densities, so they are computed rather than
gated.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math

from . import _contracts
from .authority import Authority


class MassBalanceError(ValueError):
    """Raised when a mass/balance input or contract is invalid."""


# CODATA standard gravity. The wearer-load limits are quasi-static, so this is
# the only dynamic input; head acceleration during normal use is out of scope.
STANDARD_GRAVITY_M_S2 = 9.80665

# Water at 25 degC. Cleanser density is a formulation property and is not known,
# so cleanser is carried at water density and flagged, never asserted.
WATER_DENSITY_G_ML = 0.997


class MassEvidence(Enum):
    """How well a ledger entry's mass is actually known.

    Ordered weakest to strongest. Anything at or below ENVELOPE_UPPER_BOUND may
    not be presented as product mass.
    """

    UNRESOLVED = "UNRESOLVED"
    ENVELOPE_UPPER_BOUND = "ENVELOPE_UPPER_BOUND"
    MATERIAL_AND_REALIZED_VOLUME = "MATERIAL_AND_REALIZED_VOLUME"
    SUPPLIER_DATASHEET = "SUPPLIER_DATASHEET"
    DERIVED_FROM_AUTHORITY = "DERIVED_FROM_AUTHORITY"
    MEASURED = "MEASURED"


_ESTABLISHED_EVIDENCE = frozenset({
    MassEvidence.MATERIAL_AND_REALIZED_VOLUME,
    MassEvidence.SUPPLIER_DATASHEET,
    MassEvidence.DERIVED_FROM_AUTHORITY,
    MassEvidence.MEASURED,
})


def _finite(value: float, label: str) -> float:
    return _contracts.finite(value, label, MassBalanceError)


def _non_negative(value: float, label: str) -> float:
    return _contracts.non_negative(value, label, MassBalanceError)


@dataclass(frozen=True, slots=True)
class MassEntry:
    """One item in the whole-product mass ledger."""

    item_id: str
    mass_g: float
    z_mm: float
    evidence: MassEvidence
    note: str = ""
    # Knowing what a part weighs says nothing about where it sits. The liquid
    # charges have authority-derived masses but only development placeholder
    # positions, so a CG computed from them would be false precision.
    position_evidence: MassEvidence = MassEvidence.UNRESOLVED

    def __post_init__(self) -> None:
        if not self.item_id.strip():
            raise MassBalanceError("item_id must be non-empty")
        if not isinstance(self.evidence, MassEvidence):
            raise MassBalanceError(f"{self.item_id}: evidence must be a MassEvidence")
        object.__setattr__(self, "mass_g", _non_negative(self.mass_g, f"{self.item_id}.mass_g"))
        object.__setattr__(self, "z_mm", _finite(self.z_mm, f"{self.item_id}.z_mm"))
        if self.evidence is MassEvidence.UNRESOLVED and self.mass_g != 0.0:
            raise MassBalanceError(
                f"{self.item_id}: an UNRESOLVED entry cannot also assert a mass; "
                "record it as 0 g and let the ledger report a lower bound"
            )

    @property
    def is_established(self) -> bool:
        return self.evidence in _ESTABLISHED_EVIDENCE

    @property
    def is_position_established(self) -> bool:
        return self.position_evidence in _ESTABLISHED_EVIDENCE

    @property
    def moment_g_mm(self) -> float:
        return self.mass_g * self.z_mm

    def manifest(self) -> dict[str, object]:
        return {
            "item_id": self.item_id,
            "mass_g": round(self.mass_g, 4),
            "z_mm": round(self.z_mm, 4),
            "evidence": self.evidence.value,
            "established": self.is_established,
            "position_evidence": self.position_evidence.value,
            "position_established": self.is_position_established,
            "note": self.note,
        }


def pitch_torque_nm(mass_g: float, z_mm: float) -> float:
    """Quasi-static head pitch torque from mass at an anterior offset.

    The moment arm is taken as the CG's anterior offset in the Masck One datum
    frame, which is how ``mass.cg_z_max_mm`` and ``mass.pitch_torque_max_Nm`` are
    stated relative to each other. The true arm about the atlanto-occipital joint
    is larger by the joint-to-datum offset, so this is a lower bound on the load
    the neck actually sees.
    """

    return (_non_negative(mass_g, "mass_g") / 1000.0) * STANDARD_GRAVITY_M_S2 * (
        _finite(z_mm, "z_mm") / 1000.0
    )


def max_cg_height_mm(mass_g: float, torque_limit_nm: float) -> float:
    """Highest CG that still meets a torque limit at this mass."""

    mass_kg = _non_negative(mass_g, "mass_g") / 1000.0
    if mass_kg == 0.0:
        raise MassBalanceError("mass must be positive to derive a CG bound")
    return _non_negative(torque_limit_nm, "torque_limit_nm") / (mass_kg * STANDARD_GRAVITY_M_S2) * 1000.0


def max_mass_g(z_mm: float, torque_limit_nm: float) -> float:
    """Heaviest product that still meets a torque limit at this CG height."""

    z_m = _finite(z_mm, "z_mm") / 1000.0
    if z_m <= 0.0:
        raise MassBalanceError("CG height must be positive to derive a mass bound")
    return _non_negative(torque_limit_nm, "torque_limit_nm") / (STANDARD_GRAVITY_M_S2 * z_m) * 1000.0


@dataclass(frozen=True, slots=True)
class LimitCorner:
    """One (mass, CG) corner of the released limit set, checked for closure."""

    corner_id: str
    mass_g: float
    cg_z_mm: float
    torque_nm: float
    torque_limit_nm: float
    margin_fraction: float
    closes: bool

    def manifest(self) -> dict[str, object]:
        return {
            "corner_id": self.corner_id,
            "mass_g": self.mass_g,
            "cg_z_mm": self.cg_z_mm,
            "torque_nm": round(self.torque_nm, 8),
            "torque_limit_nm": self.torque_limit_nm,
            "margin_fraction": round(self.margin_fraction, 6),
            "closes": self.closes,
        }


@dataclass(frozen=True)
class MassBalanceLedger:
    """Deterministic whole-product mass and head-load closure report."""

    entries: tuple[MassEntry, ...]
    dry_limit_g: float
    loaded_limit_g: float
    cg_limit_mm: float
    torque_limit_nm: float
    corners: tuple[LimitCorner, ...]
    limit_set_closes: bool
    cg_bound_from_torque_at_loaded_mm: float
    mass_bound_from_torque_at_cg_limit_g: float
    torque_per_gram_nm: float
    torque_per_mm_nm: float

    # ---- ledger state -------------------------------------------------

    @property
    def established_mass_g(self) -> float:
        return math.fsum(e.mass_g for e in self.entries if e.is_established)

    @property
    def unresolved_items(self) -> tuple[str, ...]:
        return tuple(e.item_id for e in self.entries if not e.is_established)

    @property
    def is_complete(self) -> bool:
        return bool(self.entries) and not self.unresolved_items

    @property
    def positions_established(self) -> bool:
        """True only when every mass-bearing entry also has a real position."""

        bearing = [e for e in self.entries if e.is_established and e.mass_g > 0.0]
        return bool(bearing) and all(e.is_position_established for e in bearing)

    def cg_z_mm(self) -> float | None:
        """CG of the established entries.

        Returns None unless every mass-bearing entry has established position
        evidence as well. A mass with a placeholder location produces a number
        that looks like a CG and is not one.
        """

        mass = self.established_mass_g
        if mass <= 0.0 or not self.positions_established:
            return None
        return math.fsum(
            e.moment_g_mm for e in self.entries if e.is_established
        ) / mass

    def manifest(self) -> dict[str, object]:
        cg = self.cg_z_mm()
        return {
            "schema": "MASCK_ONE_MASS_BALANCE_LEDGER_V1",
            "evidence_status": (
                "COMPLETE_LEDGER" if self.is_complete
                else "INCOMPLETE_LEDGER_TOTAL_IS_A_LOWER_BOUND_NOT_PRODUCT_MASS"
            ),
            "standard_gravity_m_s2": STANDARD_GRAVITY_M_S2,
            "entries": [e.manifest() for e in self.entries],
            "established_mass_g": round(self.established_mass_g, 4),
            "established_cg_z_mm": None if cg is None else round(cg, 4),
            "positions_established": self.positions_established,
            "unresolved_items": list(self.unresolved_items),
            "is_complete": self.is_complete,
            "limits": {
                "dry_target_max_g": self.dry_limit_g,
                "loaded_absolute_max_g": self.loaded_limit_g,
                "cg_z_max_mm": self.cg_limit_mm,
                "pitch_torque_max_Nm": self.torque_limit_nm,
            },
            "limit_corners": [c.manifest() for c in self.corners],
            "limit_set_closes": self.limit_set_closes,
            "cg_bound_from_torque_at_loaded_mm": round(self.cg_bound_from_torque_at_loaded_mm, 4),
            "mass_bound_from_torque_at_cg_limit_g": round(self.mass_bound_from_torque_at_cg_limit_g, 3),
            "sensitivity": {
                "torque_per_gram_nm_at_cg_limit": round(self.torque_per_gram_nm, 9),
                "torque_per_mm_nm_at_loaded_mass": round(self.torque_per_mm_nm, 9),
            },
            "not_evidence_of": [
                "as-built product mass",
                "measured centre of gravity",
                "dynamic head load during motion",
                "wearer comfort or perceived weight",
                "neck fatigue over a session",
            ],
        }


def check_limit_closure(
    dry_limit_g: float,
    loaded_limit_g: float,
    cg_limit_mm: float,
    torque_limit_nm: float,
) -> tuple[tuple[LimitCorner, ...], bool]:
    """Evaluate whether the stated limit set is mutually satisfiable.

    The worst allowed configuration is the heaviest permitted product at the
    highest permitted CG. If that corner exceeds the torque limit, a design that
    respects every individual limit can still violate the set as a whole.
    """

    corners: list[LimitCorner] = []
    for corner_id, mass in (("dry_max", dry_limit_g), ("loaded_max", loaded_limit_g)):
        torque = pitch_torque_nm(mass, cg_limit_mm)
        corners.append(
            LimitCorner(
                corner_id=corner_id,
                mass_g=float(mass),
                cg_z_mm=float(cg_limit_mm),
                torque_nm=torque,
                torque_limit_nm=float(torque_limit_nm),
                margin_fraction=(torque_limit_nm - torque) / torque_limit_nm,
                # Same tolerance as authority._semantic_issues, so a corner
                # sitting exactly on the limit cannot be judged differently by
                # the two implementations.
                closes=torque <= torque_limit_nm
                or math.isclose(torque, torque_limit_nm, rel_tol=1e-9, abs_tol=1e-12),
            )
        )
    return tuple(corners), all(c.closes for c in corners)


def liquid_charge_entries(authority: Authority) -> tuple[MassEntry, ...]:
    """Fluid masses derivable from the released authority.

    These are real, not envelope estimates: the authority fixes the volumes and
    water density is known. Cleanser density is a formulation property that is
    not known, so it is carried at water density and the assumption is recorded
    on the entry rather than hidden.
    """

    water_ml = authority.number("fluid", "water_reservoir", "gross_mL")
    cleanser_ml = authority.number("fluid", "clean_cycle", "cleanser_mL")
    reservoir_z = authority.get("fluid", "water_reservoir", "envelope_mm")[2] / 2.0

    return (
        MassEntry(
            item_id="charge_water",
            mass_g=water_ml * WATER_DENSITY_G_ML,
            z_mm=float(reservoir_z),
            evidence=MassEvidence.DERIVED_FROM_AUTHORITY,
            note=(
                f"{water_ml} mL at {WATER_DENSITY_G_ML} g/mL (water, 25 degC); "
                "position is a development placeholder, not the released reservoir "
                "centroid"
            ),
        ),
        MassEntry(
            item_id="charge_cleanser",
            mass_g=cleanser_ml * WATER_DENSITY_G_ML,
            z_mm=float(reservoir_z),
            evidence=MassEvidence.DERIVED_FROM_AUTHORITY,
            note=(
                f"{cleanser_ml} mL carried at water density; cleanser formulation "
                "density is unresolved and must be confirmed"
            ),
        ),
    )


# Every subsystem that must carry a mass before a total may be called product
# mass. Absent entries are materialised as UNRESOLVED rather than omitted: a
# ledger that silently skips the structural frame and reports its liquid charge
# as "complete" is worse than no ledger at all.
REQUIRED_MASS_COVERAGE: tuple[str, ...] = (
    "rigid_shell",
    "compliant_facial_interface",
    "structural_frame",
    "actuator_1",
    "actuator_2",
    "actuator_3",
    "actuator_4",
    "water_reservoir_structure",
    "cleanser_store_structure",
    "fresh_pumps",
    "distribution_manifold",
    "waste_pump",
    "waste_cartridge",
    "battery",
    "electronics_and_harness",
    "primary_control_hmi",
    "retention_system",
    "thermal_system",
    "seals_and_fasteners",
    "charge_water",
    "charge_cleanser",
)


def battery_entry(authority: Authority) -> MassEntry:
    """Battery mass from the named supplier candidate.

    battery_reference names a specific cell (EEMB LP603450HA) and states its
    mass, so this is datasheet evidence rather than an envelope estimate. The
    cell itself remains PACKAGING_BENCHMARK_NOT_PRODUCTION_FREEZE: the mass is
    real for that part, but that part is not a production selection.
    """

    z_mm = float(authority.get("battery_reference", "envelope_mm")[2]) / 2.0
    return MassEntry(
        item_id="battery",
        mass_g=authority.number("battery_reference", "mass_g"),
        z_mm=z_mm,
        evidence=MassEvidence.SUPPLIER_DATASHEET,
        note=(
            f"{authority.get('battery_reference', 'candidate')}; "
            "candidate cell, not a production freeze; position is a development "
            "placeholder"
        ),
    )


def build_mass_balance_ledger(
    authority: Authority,
    entries: tuple[MassEntry, ...] | None = None,
) -> MassBalanceLedger:
    """Build the whole-product mass/balance closure report."""

    dry = authority.number("mass", "dry_target_max_g")
    loaded = authority.number("mass", "loaded_absolute_max_g")
    cg_limit = authority.number("mass", "cg_z_max_mm")
    torque_limit = authority.number("mass", "pitch_torque_max_Nm")

    corners, closes = check_limit_closure(dry, loaded, cg_limit, torque_limit)

    supplied = (
        liquid_charge_entries(authority) + (battery_entry(authority),)
        if entries is None
        else tuple(entries)
    )
    covered = {entry.item_id for entry in supplied}
    # Materialise every uncovered subsystem so the gap is counted, not omitted.
    missing = tuple(
        MassEntry(item_id, 0.0, 0.0, MassEvidence.UNRESOLVED, note="no mass evidence")
        for item_id in REQUIRED_MASS_COVERAGE
        if item_id not in covered
    )
    ledger_entries = supplied + missing

    return MassBalanceLedger(
        entries=ledger_entries,
        dry_limit_g=dry,
        loaded_limit_g=loaded,
        cg_limit_mm=cg_limit,
        torque_limit_nm=torque_limit,
        corners=corners,
        limit_set_closes=closes,
        cg_bound_from_torque_at_loaded_mm=max_cg_height_mm(loaded, torque_limit),
        mass_bound_from_torque_at_cg_limit_g=max_mass_g(cg_limit, torque_limit),
        torque_per_gram_nm=pitch_torque_nm(1.0, cg_limit),
        torque_per_mm_nm=pitch_torque_nm(loaded, 1.0),
    )
