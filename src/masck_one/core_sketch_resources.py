"""Concept scenario overlay on released authority and the canonical mass ledger.

Unknown upper bounds stay unknown. These are planning screens, not validated
routines, doses, usable capacity or hardware permission.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import fsum
from . import _contracts
from .authority import Authority
from .core_sketch_contracts import CoreSketchError, digest, number, result, text, unique
from .mass_balance import build_mass_balance_ledger, STANDARD_GRAVITY_M_S2, WATER_DENSITY_G_ML


@dataclass(frozen=True)
class Bound:
    low: float
    high: float | None
    unknowns: tuple[str, ...] = ()

    def __post_init__(self):
        number(self.low, "lower bound")
        if self.high is not None and number(self.high, "upper bound") < self.low:
            raise CoreSketchError("reversed resource interval")
        if self.high is None and not self.unknowns:
            raise CoreSketchError("unbounded resource must name its unknown")

    def __add__(self, other: Bound) -> Bound:
        return Bound(self.low + other.low,
            None if self.high is None or other.high is None else self.high + other.high,
            tuple(sorted(set(self.unknowns + other.unknowns))))

    def __mul__(self, other: Bound) -> Bound:
        # Even a nominal zero cannot erase an unresolved inventory item.
        return Bound(self.low * other.low,
            None if self.high is None or other.high is None else self.high * other.high,
            tuple(sorted(set(self.unknowns + other.unknowns))))

    def record(self) -> dict:
        return {"low": self.low, "high": self.high, "unknowns": list(self.unknowns)}


def fixed(value: float) -> Bound:
    return Bound(number(value, "quantity"), number(value, "quantity"))


def read(value: list | None, name: str) -> Bound:
    if value is None:
        return Bound(0.0, None, (text(name, "unknown name"),))
    if type(value) is not list or len(value) != 2:
        raise CoreSketchError("resource must be [lower, upper] or null")
    return Bound(number(value[0], name), number(value[1], name))


def total(values: list[Bound]) -> Bound:
    out = fixed(0.0)
    for value in values:
        out = out + value
    return out


def screen(value: Bound, limit: float, *, strict: bool = False) -> str:
    limit = number(limit, "authority limit")
    if value.low > limit or (strict and value.low == limit):
        return "VIOLATES_LIMIT"
    if value.high is None:
        return "UNRESOLVED"
    if value.high < limit or (not strict and value.high == limit):
        return "WITHIN_MODEL_BOUND_NOT_PHYSICAL_PASS"
    return "INTERVAL_CROSSES_LIMIT"


def assess_resources(authority: Authority, scenario: dict) -> dict:
    """Inventory transfers do not add mass; pre-existing waste does.

    Cleaning quantities are live authority study targets. Product quantities,
    density, new hardware, losses and position remain caller-labelled inputs.
    The current ledger's unresolved items cannot be replaced by implicit zero.
    """
    digest(scenario)
    text(scenario.get("id"), "scenario id")
    if scenario.get("status") != "UNVALIDATED_PLANNING_SCENARIO":
        raise CoreSketchError("resource scenario cannot claim a validated routine")
    cc = authority.get("fluid", "clean_cycle")
    products = unique(scenario.get("products"))
    if not any(p.get("role") == "MOISTURISE" for p in products.values()):
        raise CoreSketchError("complete-routine scenario requires moisturiser")
    for p in products.values():
        if p.get("role") not in {"LEAVE_ON", "MOISTURISE", "FACIAL_SPF"}:
            raise CoreSketchError("unknown session product role")
    extra = scenario.get("inputs", {})
    water = fixed(cc["face_water_mL"] + cc["post_flush_water_mL"]) + Bound(0, cc["maximum_initial_prime_mL"])
    water = water + read(extra.get("wearable_purge_water_ml"), "wearable_purge_water_ml")
    cleanser = fixed(cc["cleanser_mL"])
    doses = {i: read(p.get("dose_ml"), i + ".dose_ml") for i, p in products.items()}
    product_volume = total(list(doses.values()))
    product_mass = total([doses[i] * read(p.get("density_g_ml"), i + ".density_g_ml") for i, p in products.items()])
    purge_product = read(extra.get("product_changeover_ml"), "product_changeover_ml")
    purge_mass = read(extra.get("product_changeover_mass_g"), "product_changeover_mass_g")
    # Purge allocation is explicitly wearable here; dock-only servicing has its own resources.
    fluid_mass = (water * fixed(WATER_DENSITY_G_ML)
        + cleanser * read(extra.get("cleanser_density_g_ml"), "cleanser_density_g_ml")
        + product_mass + purge_mass)
    prior_waste_mass = read(extra.get("prior_waste_mass_g"), "prior_waste_mass_g")
    ledger = build_mass_balance_ledger(authority)
    hardware = [e for e in ledger.entries if not e.item_id.startswith("charge_")]
    dry = total([fixed(e.mass_g) if e.is_established else read(None, "hardware." + e.item_id) for e in hardware])
    dry = dry + read(extra.get("session_isolation_hardware_mass_g"), "session_isolation_hardware_mass_g")
    if scenario.get("optical_selected") is True:
        dry = dry + read(extra.get("optical_hardware_mass_g"), "optical_hardware_mass_g")
    loaded = dry + fluid_mass + prior_waste_mass
    # Post-recovery inventory is conservatively bounded by prepared inventory.
    # Recovery is an internal relocation, never +recovered_volume on top of it.
    recovered_target = Bound(cc["nominal_introduced_liquid_mL"] * authority.number("fluid", "waste", "recovery_ratio_min"),
                             cc["nominal_introduced_liquid_mL"])
    waste = recovered_target + read(extra.get("prior_waste_ml"), "prior_waste_ml")
    waste = waste + read(extra.get("wearable_purge_water_ml"), "wearable_purge_water_ml") + purge_product
    waste = waste + read(extra.get("leave_on_loss_ml"), "leave_on_loss_ml") + Bound(0, cc["maximum_initial_prime_mL"])
    free_residual = Bound(0, authority.number("fluid", "waste", "residual_free_liquid_max_uL") / 1000)
    residual_mass = free_residual * fixed(WATER_DENSITY_G_ML)
    # Intended final film is not 'residual free liquid' and is not another on-head charge.
    retained_film_mass = read(extra.get("intended_retained_film_mass_g"), "intended_retained_film_mass_g")
    storage = cleanser + product_volume + purge_product
    storage_capacity = extra.get("usable_session_storage_ml")
    storage_check = "UNRESOLVED" if storage_capacity is None else screen(storage, number(storage_capacity, "storage capacity"))
    energy = read(extra.get("electrical_energy_Wh"), "electrical_energy_Wh")
    duration = read(extra.get("routine_duration_s"), "routine_duration_s")
    thermal = read(extra.get("thermal_state_required_J"), "thermal_state_required_J") if scenario.get("thermal_selected") else fixed(0)
    reset = read(extra.get("dock_reset_energy_J"), "dock_reset_energy_J") if scenario.get("thermal_selected") else fixed(0)
    # Exact positions and post-transfer positions must be supplied for all inventory.
    # Current canonical ledger intentionally withholds unresolved position evidence.
    positions_known = all(e.is_position_established for e in hardware) and not dry.unknowns
    moment = None
    cg = None
    if positions_known and not fluid_mass.unknowns and fluid_mass.low == fluid_mass.high and dry.low == dry.high and prior_waste_mass.high == 0:
        fluid_z = extra.get("session_fluid_z_mm")
        hardware_z = extra.get("session_isolation_hardware_z_mm")
        if fluid_z is not None and hardware_z is not None and scenario.get("optical_selected") is not True:
            z = _contracts.finite(fluid_z, "fluid z", CoreSketchError)
            hz = _contracts.finite(hardware_z, "isolation hardware z", CoreSketchError)
            hm = read(extra.get("session_isolation_hardware_mass_g"), "session hardware")
            if hm.low == hm.high:
                moment = fsum(e.mass_g * e.z_mm for e in hardware) + hm.low * hz + fluid_mass.low * z
                cg = moment / loaded.low if loaded.low else None
    torque = None if moment is None else abs(moment) * STANDARD_GRAVITY_M_S2 / 1_000_000
    limits = authority.get("mass")
    checks = {
        "dry_mass": screen(dry, limits["dry_target_max_g"]),
        "loaded_mass": screen(loaded, limits["loaded_absolute_max_g"], strict=True),
        "cg_z": "UNRESOLVED" if cg is None else screen(fixed(abs(cg)), limits["cg_z_max_mm"]),
        "pitch_torque": "UNRESOLVED" if torque is None else screen(fixed(torque), limits["pitch_torque_max_Nm"]),
        "session_storage": storage_check,
        "water_demand_vs_usable_baseline": screen(water, authority.number("fluid", "water_reservoir", "minimum_usable_mL")),
        "waste_demand_vs_retained_requirement": screen(waste, authority.number("fluid", "cartridge", "retained_capacity_min_mL")),
        "battery_usable_energy": "UNRESOLVED" if extra.get("usable_battery_energy_Wh") is None else screen(energy, extra["usable_battery_energy_Wh"]),
    }
    blockers = [k + ":" + v for k, v in checks.items() if v != "WITHIN_MODEL_BOUND_NOT_PHYSICAL_PASS"]
    values = {"session_water_ml": water, "cleanser_ml": cleanser, "leave_on_total_ml": product_volume,
        "product_changeover_ml": purge_product, "wearable_session_fluid_mass_g": fluid_mass,
        "dry_mass_g": dry, "loaded_mass_g": loaded, "post_recovery_conservative_inventory_g": loaded,
        "expected_recovered_cleaning_target_ml": recovered_target, "waste_capacity_demand_ml": waste,
        "residual_free_water_mass_target_g": residual_mass, "intended_retained_film_mass_g": retained_film_mass,
        "session_product_storage_ml": storage, "electrical_energy_Wh": energy, "thermal_state_required_J": thermal,
        "dock_reset_energy_J": reset, "routine_duration_s": duration}
    blockers += [k + ":UNRESOLVED" for k, v in values.items() if v.high is None]
    return result(blockers, scenario_id=scenario["id"], inputs_digest=digest(scenario),
        authority_content_digest=digest(authority.data), bounds={k: v.record() for k, v in values.items()},
        per_product_dose_ml={k: v.record() for k, v in doses.items()},
        minimum_bulk_product_slots=1 + len(products), water_and_waste_slots_counted_separately=True,
        cg_z_mm=cg, datum_pitch_torque_Nm=torque, screens=checks,
        source_ledger_unresolved=[e.item_id for e in hardware if not e.is_established],
        interpretation="Cleaning and waste numbers are validation-gated planning targets, not observations. Unknown losses, hardware and positions prevent closure. Neck-joint offset and dynamic torque remain unresolved.")
