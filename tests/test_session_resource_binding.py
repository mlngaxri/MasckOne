"""Prepared-session arithmetic and snapshot consistency, never physical evidence."""
from copy import deepcopy

import pytest

from masck_one.authority import load_authority
from masck_one.core_sketch_contracts import CoreSketchError, assess_readiness, digest
from masck_one.dock_preparation import derive_session_doses
from masck_one.session_resource_binding import assess_session_resources
from test_core_sketch_contracts import completed, ready


def inputs():
    authority = load_authority()
    plan = completed()[0]
    # Separate product identity for every application class; one generic bottle
    # must not stand in for cleanser, moisturiser and facial SPF.
    bindings, sources, demands = [], [], {}
    for stage in plan["stages"]:
        if "product_binding" not in stage:
            continue
        ident = stage["product_binding"]
        bound = dict(id=ident, sku="SKU-" + ident, market="test", identity_version="1", slot=ident)
        bindings.append(bound)
        sources.append(dict(slot=ident, product=ident, sku=bound["sku"], market="test", identity_version="1",
            lot="LOT-1", fill_epoch=0, location="DOCK", readable=True, volume_ml=100.,
            expires_at_s=10000., contamination_state="VERIFIED_CLEAN", density_g_ml=1.))
        quantity = authority.number("fluid", "clean_cycle", "cleanser_mL") if stage["kind"] == "CLEAN" else 1.
        demands[ident] = dict(application=stage["kind"], target_ml=quantity, min_ml=quantity, max_ml=quantity)
    binding = dict(routine_id="synthetic", routine_revision="1", schedule_context="AM",
        stage_ids=[s["id"] for s in plan["stages"]], plan_digest=digest(plan), product_bindings=bindings,
        hardware_revision="test", profile_revision="test", authority_digest=digest(authority.data))
    doses = derive_session_doses(demands, sources, binding, now_s=1.)
    scenario = dict(id="synthetic", status="UNVALIDATED_PLANNING_SCENARIO",
        optical_selected=False, thermal_selected=False, inputs=dict(
            wearable_purge_water_ml=[0, 0], prepared_water_charge_ml=[5, 5],
            prior_waste_ml=[0, 0], product_changeover_ml=[0, 0], leave_on_loss_ml=[0, 0],
            electrical_energy_Wh=[0, 0], routine_duration_s=[0, 0]))
    envelope = dict(background=dict(average_power_W=[0, 0], peak_power_W=[0, 0]),
        stages=[dict(id=s["id"], duration_s=[3600 / len(plan["stages"])] * 2,
            average_power_W=[2, 2], peak_power_W=[4, 6]) for s in plan["stages"]])
    return authority, dict(plan=plan, binding=binding, dose_result=doses, reservoirs=sources,
        scenario=scenario, electrical_envelope=envelope)


def test_prepared_products_and_electrical_demands_feed_one_ledger():
    authority, args = inputs()
    original = deepcopy(args)
    report = assess_session_resources(authority, **args)
    assert report["consumables_closed"]
    assert report["readiness_requirements"] == pytest.approx(dict(
        water_ml=4.4, waste_free_ml=5., usable_energy_Wh=2., peak_power_W=6.))
    assert report["resource_report"]["bounds"]["electrical_energy_Wh"]["high"] == pytest.approx(2.)
    assert report["resource_report"]["bounds"]["routine_duration_s"]["high"] == pytest.approx(3600.)
    assert report["resource_report"]["bounds"]["loaded_mass_g"]["high"] is None
    assert report["resource_report"]["cg_z_mm"] is None
    assert not report["full_resource_closure"] and not report["whole_product_closed"]
    assert not report["hardware_execution_authorized"]
    assert args == original


def test_derived_two_Wh_replaces_underdeclared_request_one_Wh():
    authority, args = inputs()
    report = assess_session_resources(authority, **args)
    request, receipt, current = ready()
    # Exercise the existing consumer with the derived resource contract. The
    # unrelated synthetic identity bindings already satisfy that consumer.
    request["resources"] = report["readiness_requirements"]
    current["resources"] = dict(water_ml=10, waste_free_ml=10, usable_energy_Wh=1, peak_power_W=6)
    receipt["request_digest"] = digest(request)
    receipt["resources_digest"] = digest(current["resources"])
    checked = assess_readiness(request, receipt, current, 10)
    assert not checked["start_ready"]
    assert "usable_energy_Wh:RESOURCE_INSUFFICIENT" in checked["blockers"]


@pytest.mark.parametrize("kind", ["authority", "plan", "stage_ids", "dose_binding"])
def test_changed_execution_context_blocks(kind):
    authority, args = inputs()
    if kind == "authority": args["binding"]["authority_digest"] = "stale"
    elif kind == "plan": args["binding"]["plan_digest"] = "stale"
    elif kind == "stage_ids": args["binding"]["stage_ids"].reverse()
    else: args["dose_result"]["binding_digest"] = "stale"
    report = assess_session_resources(authority, **args)
    assert not report["consumables_closed"]
    assert any("BINDING_CHANGED" in b or "AUTHORITY_CHANGED" in b for b in report["blockers"])


@pytest.mark.parametrize("field,value", [("density_g_ml", 2.), ("lot", "LOT-2"), ("volume_ml", 90.)])
def test_source_changes_invalidate_dose_and_remain_unknown_in_ledger(field, value):
    authority, args = inputs()
    source = next(r for r in args["reservoirs"] if "moistur" in r["product"])
    source[field] = value
    report = assess_session_resources(authority, **args)
    assert not report["consumables_closed"]
    assert report["resource_report"]["per_product_dose_ml"][source["product"]]["high"] is None
    assert any("SOURCE_CHANGED" in b for b in report["blockers"])


def test_unknown_electrical_power_cannot_be_replaced_by_scenario_zero():
    authority, args = inputs()
    args["electrical_envelope"]["stages"][0]["average_power_W"] = None
    report = assess_session_resources(authority, **args)
    assert report["readiness_requirements"]["usable_energy_Wh"] is None
    assert report["resource_report"]["bounds"]["electrical_energy_Wh"]["high"] is None
    assert not report["consumables_closed"]


def test_unknown_water_or_waste_demand_does_not_become_zero():
    authority, args = inputs()
    args["scenario"]["inputs"]["wearable_purge_water_ml"] = None
    report = assess_session_resources(authority, **args)
    assert report["readiness_requirements"]["water_ml"] is None
    assert report["readiness_requirements"]["waste_free_ml"] is None
    assert not report["consumables_closed"]


def test_thermal_upper_is_required_and_unknown_never_omitted():
    authority, args = inputs()
    args["scenario"]["thermal_selected"] = True
    report = assess_session_resources(authority, **args)
    assert report["readiness_requirements"]["thermal_available_J"] is None
    assert not report["consumables_closed"]
    args["scenario"]["inputs"]["thermal_state_required_J"] = [100, 200]
    report = assess_session_resources(authority, **args)
    assert report["readiness_requirements"]["thermal_available_J"] == 200


@pytest.mark.parametrize("which", ["application", "cleanser_quantity", "prepared_manifest"])
def test_inconsistent_dose_semantics_cannot_enter_resource_budget(which):
    authority, args = inputs()
    row = args["dose_result"]["doses"][0]
    if which == "application": row["application"] = "LEAVE_ON"
    elif which == "cleanser_quantity":
        row = next(r for r in args["dose_result"]["doses"] if r["application"] == "CLEAN")
        row["quantity_ml"] = 1.
        row["dose_id"] = "dose:" + digest([row["binding"], 1., row["source_snapshot"]])[:32]
    else: args["dose_result"]["prepared_doses"] = []
    assert not assess_session_resources(authority, **args)["consumables_closed"]


def test_exact_electrical_stage_inventory_still_required():
    authority, args = inputs()
    args["electrical_envelope"]["stages"].pop()
    with pytest.raises(CoreSketchError, match="exactly cover plan"):
        assess_session_resources(authority, **args)
