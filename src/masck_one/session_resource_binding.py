"""Bind prepared-session consumables to the exact plan and declared sources.

This adapter composes planning models. It neither observes a transfer nor
establishes usable physical capacity. Canonical mass and position unknowns stay
in the full resource report even when bounded consumables permit host simulation.
"""
from __future__ import annotations

from copy import deepcopy

from .authority import Authority
from .core_sketch_contracts import CoreSketchError, digest, number, result, unique, validate_plan
from .core_sketch_resources import assess_electrical_envelope, assess_resources
from .dock_preparation import DOSE_PREPARED, resource_scenario_products


def _interval(bound: dict) -> list[float] | None:
    # An unresolved upper must remain unresolved, including for nominal zero.
    return None if bound["high"] is None else [bound["low"], bound["high"]]


def assess_session_resources(authority: Authority, *, plan: dict, binding: dict,
        dose_result: dict, reservoirs: list[dict], scenario: dict,
        electrical_envelope: dict) -> dict:
    """Derive readiness demands; callers must enforce this report's blockers.

    ``readiness_requirements`` contains conservative upper bounds, never a
    caller's independent requested amount. The full ledger's mass/CG unknowns
    are reported separately: bounded consumables do not resolve those unknowns
    and cannot authorize a worn device.
    """
    digest([binding, dose_result, reservoirs, scenario, electrical_envelope])
    stages = validate_plan(plan)
    expected = unique(binding.get("product_bindings"))
    unique(binding["product_bindings"], "slot")
    held = unique(reservoirs, "slot")
    doses = unique(dose_result.get("doses"), "product_binding")
    blockers = list(dose_result.get("blockers", []))
    authority_digest = digest(authority.data)
    if binding.get("authority_digest") != authority_digest:
        blockers.append("RESOURCE_AUTHORITY_CHANGED")
    if binding.get("plan_digest") != digest(plan) or binding.get("stage_ids") != list(stages):
        blockers.append("RESOURCE_PLAN_BINDING_CHANGED")
    if dose_result.get("binding_digest") != digest(binding):
        blockers.append("RESOURCE_DOSE_BINDING_CHANGED")
    planned_products = {s["product_binding"] for s in stages.values() if s.get("product_binding")}
    if set(expected) != planned_products or set(doses) != set(expected):
        blockers.append("RESOURCE_PRODUCT_SET_DIFFERS_FROM_PLAN")
    for ident, want in expected.items():
        row = doses.get(ident, {})
        bound = row.get("binding")
        source = held.get(want.get("slot"))
        snapshot = row.get("source_snapshot")
        quantity = row.get("quantity_ml")
        kinds = {s["kind"] for s in stages.values() if s.get("product_binding") == ident}
        if kinds != {row.get("application")}:
            blockers.append(ident + ":DOSE_APPLICATION_DIFFERS_FROM_PLAN")
        if bound != want:
            blockers.append(ident + ":RESOURCE_PRODUCT_BINDING_CHANGED")
        if (source is None or not isinstance(snapshot, dict) or digest(source) != digest(snapshot)
            or source.get("location") != "DOCK" or source.get("product") != ident
            or any(source.get(f) != want.get(f) for f in ("sku", "market", "identity_version"))):
            blockers.append(ident + ":RESOURCE_SOURCE_CHANGED")
        if (row.get("state") != DOSE_PREPARED or quantity is None
            or number(quantity, "quantity_ml") == 0
            or row.get("dose_id") != "dose:" + digest([want, quantity, snapshot])[:32]):
            blockers.append(ident + ":RESOURCE_DOSE_UNRESOLVED_OR_CHANGED")
        if "CLEAN" in kinds and quantity != authority.number("fluid", "clean_cycle", "cleanser_mL"):
            blockers.append(ident + ":CLEAN_DOSE_DIFFERS_FROM_AUTHORITY_CLEAN_CYCLE")
    prepared = [r for r in doses.values() if r.get("state") == DOSE_PREPARED]
    if dose_result.get("prepared_doses") != prepared:
        blockers.append("RESOURCE_PREPARED_DOSE_MANIFEST_CHANGED")

    products = resource_scenario_products(dose_result, reservoirs)
    blockers.extend(products["blockers"])
    electrical = assess_electrical_envelope(plan, electrical_envelope)
    blockers.extend(electrical["blockers"])
    derived = deepcopy(scenario)
    derived["products"] = products["products"]
    extra = derived.setdefault("inputs", {})
    if not isinstance(extra, dict):
        raise CoreSketchError("resource scenario inputs must be an object")
    for key in ("electrical_energy_Wh", "routine_duration_s"):
        extra[key] = _interval(electrical["bounds"][key])
    resource = assess_resources(authority, derived)
    bounds = resource["bounds"]
    requirements = {"water_ml": bounds["session_water_ml"]["high"],
        "waste_free_ml": bounds["waste_capacity_demand_ml"]["high"],
        "usable_energy_Wh": electrical["bounds"]["electrical_energy_Wh"]["high"],
        "peak_power_W": electrical["bounds"]["peak_power_W"]["high"]}
    thermal = derived.get("thermal_selected")
    if thermal is not False:
        requirements["thermal_available_J"] = bounds["thermal_state_required_J"]["high"]
    for key, value in requirements.items():
        if value is None:
            blockers.append(key + ":SESSION_DEMAND_UNRESOLVED")
    for key in ("optical_selected", "thermal_selected"):
        if derived.get(key) is None:
            blockers.append(key + ":UNRESOLVED")
    # Capacity violations are meaningful even without canonical mass closure.
    # CG/mass and separate dock reset remain visible in the nested ledger.
    for key in ("prepared_water_vs_gross_capacity", "water_demand_vs_prepared_charge",
                "session_storage", "water_demand_vs_usable_baseline",
                "waste_demand_vs_retained_requirement", "battery_usable_energy"):
        screen = resource["screens"][key]
        if screen in {"VIOLATES_LIMIT", "INTERVAL_CROSSES_LIMIT"}:
            blockers.append(key + ":" + screen)
    return result(blockers, readiness_requirements=requirements,
        thermal_selected=thermal, resource_report=resource, electrical_report=electrical,
        resource_scenario=derived, authority_content_digest=authority_digest,
        plan_digest=digest(plan), binding_digest=digest(binding),
        dose_manifest_digest=digest(dose_result), reservoir_snapshot_digest=digest(reservoirs),
        input_scenario_digest=digest(scenario), electrical_envelope_digest=digest(electrical_envelope),
        full_resource_closure=resource["model_consistent"],
        consumables_closed=not blockers, whole_product_closed=not blockers and resource["model_consistent"],
        evidence_status="DECLARED_PREPARED_SESSION_RESOURCE_CONSISTENCY_NOT_PHYSICAL_CAPACITY")
