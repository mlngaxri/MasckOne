"""Synthetic host integration, with real producers and no physical qualification.

The named isolated ledger fixture replaces unresolved real hardware mass only
inside tests of host sequencing. Tests against the actual ledger must block.
"""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from masck_one.authority import load_authority
from masck_one.core_sketch_contracts import CoreSketchError, digest, load_manifest
from masck_one.mass_balance import MassEntry, MassEvidence
from masck_one.routine_schedule import offline_manifest
from masck_one.session_pipeline import (
    assess_session_completion, interrupt_pipeline, prepare_session, record_session_intent,
    record_session_report, validate_pipeline,
)
from test_core_sketch_contracts import completed
from test_routine_product_intelligence import make_product, reservoir

ROOT = Path(__file__).resolve().parents[1]


def pipeline_inputs():
    authority = load_authority()
    plan = completed()[0]
    bindings, products, evidence, demands, reservoirs = [], [], [], {}, []
    for index, stage in enumerate(plan["stages"]):
        if "product_binding" not in stage:
            continue
        ident = stage["product_binding"]
        slot = str(index)
        bindings.append(dict(id=ident, sku="SKU-" + ident, market="UK", identity_version="1", slot=slot))
        product, records = make_product(ident=ident, applications=(stage["kind"],), context="pipeline-test")
        products.append(product)
        evidence += records
        qty = authority.number("fluid", "clean_cycle", "cleanser_mL") if stage["kind"] == "CLEAN" else 0.1
        demands[ident] = dict(application=stage["kind"], target_ml=qty, min_ml=qty, max_ml=qty)
        reservoirs.append(reservoir(slot=slot, product=ident, sku="SKU-" + ident))
    binding = dict(routine_id="pipeline-test", routine_revision="1", schedule_context="AM",
        stage_ids=[s["id"] for s in plan["stages"]], plan_digest=digest(plan), product_bindings=bindings,
        hardware_revision="synthetic", profile_revision="1", authority_digest=digest(authority.data))
    request = dict(plan=plan, binding=binding, thermal_stage=False,
        resources={"water_ml": 0},  # Must be replaced by actual calculated bounds.
        dose_requirements={ident: {k: demand[k] for k in ("min_ml", "max_ml")} for ident, demand in demands.items()})
    current = dict(binding=deepcopy(binding), epoch=0, invalidations=[], faults=[], wear_state="CONFIRMED_ELIGIBLE",
        stage_eligibility={s["id"]: "ELIGIBLE_FOR_EXACT_PLAN" for s in plan["stages"]},
        local={key: True for key in ("clock_valid", "profile_cache_verified", "progress_known", "controller_available")},
        service={key: "VERIFIED_COMPLETE" for key in ("cleaning", "changeover", "dry_path_service")},
        resources={"water_ml": 6.5, "waste_free_ml": 100, "usable_energy_Wh": 100, "peak_power_W": 100})
    scenario = deepcopy(load_manifest(ROOT)["resources"]["scenarios"][0])
    scenario.update(optical_selected=False, thermal_selected=False)
    scenario["inputs"] = {key: [0, 0] for key in (
        "wearable_purge_water_ml", "product_changeover_ml", "product_changeover_mass_g",
        "prior_waste_mass_g", "prior_waste_ml", "leave_on_loss_ml", "session_isolation_hardware_mass_g",
        "intended_retained_film_mass_g")}
    scenario["inputs"].update(prepared_water_charge_ml=[6.5, 6.5], cleanser_density_g_ml=[1, 1],
        usable_session_storage_ml=100, usable_battery_energy_Wh=100,
        session_fluid_z_mm=0, session_isolation_hardware_z_mm=0)
    envelope = dict(background=dict(average_power_W=[1, 1], peak_power_W=[1, 1]),
        stages=[dict(id=s["id"], duration_s=[1, 1], average_power_W=[1, 1], peak_power_W=[1, 1]) for s in plan["stages"]])
    cache = {key: binding[key] for key in ("routine_revision", "profile_revision", "hardware_revision", "authority_digest")}
    cache.update(stage_parameters={"plan_digest": binding["plan_digest"]},
        dose_windows={"dose_requirements_digest": digest(request["dose_requirements"])},
        protected_region_map={"plan_digest": binding["plan_digest"]},
        fault_response_table={"hardware_revision": binding["hardware_revision"], "authority_digest": binding["authority_digest"]})
    routine = dict(id=binding["routine_id"], revision="1", contexts={"AM": [
        {k: v for k, v in stage.items() if k in {"id", "kind", "product_binding"}} for stage in plan["stages"]]})
    manifest = offline_manifest(routine, "AM", cache)
    source = dict(request=request, demands=demands, reservoirs=reservoirs, products=products,
        product_evidence=evidence, product_context="pipeline-test", resource_scenario=scenario,
        electrical_envelope=envelope, current=current,
        preparation=dict(service_receipt_id="declared-test-service", expires_at_s=1000, observations_expire_at_s=1000),
        manifest=manifest, cache=cache)
    return authority, source


@pytest.fixture
def isolated_closed_ledger(monkeypatch):
    """A synthetic 1 g at datum; never modifies the production authority/ledger."""
    from masck_one import core_sketch_resources
    monkeypatch.setattr(core_sketch_resources, "build_mass_balance_ledger", lambda authority: SimpleNamespace(entries=[
        MassEntry("synthetic_host_test_hardware", 1, 0, MassEvidence.MEASURED,
            note="synthetic test only", position_evidence=MassEvidence.MEASURED)]))


def prepared_pipeline():
    authority, source = pipeline_inputs()
    return authority, source, prepare_session(authority, "session-1", source, now_s=1, network_reachable=False)


def finished_pipeline():
    authority, source, pipeline = prepared_pipeline()
    for index, stage in enumerate(pipeline["journal"]["stage_ids"]):
        pipeline = record_session_intent(authority, pipeline, source, stage, now_s=2 + index * 2, network_reachable=False)
        pipeline = record_session_report(authority, pipeline, source, stage, report_id="host-report-" + stage,
            now_s=3 + index * 2, network_reachable=False)
    return authority, source, pipeline


def completion_inputs(pipeline):
    _, observations, _, evidence = completed()
    observations.update(session_id=pipeline["journal"]["session_id"], source_digest=pipeline["source_digest"],
                        receipt_digest=digest(pipeline["receipt"]))
    return observations, evidence


def test_actual_canonical_unknown_hardware_blocks_start_and_preserves_causes():
    _, _, pipeline = prepared_pipeline()
    assert pipeline["journal"]["state"] == "SERVICE_REQUIRED"
    assert pipeline["journal"]["revision"] == 0
    assert "WHOLE_PRODUCT_RESOURCE_ENVELOPE_UNCLOSED" in pipeline["blockers"]
    assert not pipeline["whole_product_resource_closed"]
    assert not pipeline["model_start_ready"]
    assert not pipeline["hardware_execution_authorized"]


def test_real_producers_connect_to_offline_gates(isolated_closed_ledger):
    authority, source, pipeline = prepared_pipeline()
    assert pipeline["journal"]["state"] == "PLANNED", pipeline["blockers"]
    assert pipeline["request"]["resources"]["water_ml"] > source["request"]["resources"]["water_ml"]
    assert pipeline["current"]["doses"] == pipeline["dose_result"]["prepared_doses"]
    assert pipeline["current"]["products"] == pipeline["product_result"]["products"]
    assert prepare_session(authority, "session-1", source, now_s=1, network_reachable=True) == pipeline
    assert not pipeline["physical_routine_complete"]


def test_reports_do_not_create_physical_completion(isolated_closed_ledger):
    authority, source, pipeline = finished_pipeline()
    assert pipeline["journal"]["state"] == "REPORT_SEQUENCE_FINISHED"
    assert not pipeline["physical_routine_complete"]
    observations, evidence = completion_inputs(pipeline)
    out = assess_session_completion(authority, pipeline, source, observations, evidence,
        now_s=100, network_reachable=False)
    assert out["completion_claim_admissible"], out["blockers"]
    assert out["completion_assessment"]["reduced_sequence_complete"]
    assert not out["completion_assessment"]["whole_routine_complete"]
    assert not out["physical_routine_complete"] and not out["hardware_execution_authorized"]


@pytest.mark.parametrize("mutation", ["source_lot", "source_missing", "product_evidence", "water_unknown", "cache_missing"])
def test_changed_source_between_plan_and_intent_is_terminal(isolated_closed_ledger, mutation):
    authority, source, pipeline = prepared_pipeline()
    if mutation == "source_lot": source["reservoirs"][0]["lot"] = "other"
    if mutation == "source_missing": source["reservoirs"].pop()
    if mutation == "product_evidence": source["product_evidence"][0]["accepted"] = False
    if mutation == "water_unknown": source["current"]["resources"]["water_ml"] = None
    if mutation == "cache_missing": source["cache"].pop("dose_windows")
    out = record_session_intent(authority, pipeline, source, pipeline["journal"]["stage_ids"][0], now_s=2, network_reachable=True)
    assert out["journal"]["state"] == "SERVICE_REQUIRED"
    assert not out["journal"]["reported_stage_ids"]
    assert not out["model_start_ready"]


def test_missing_products_cannot_be_replaced_by_cached_validated_rows(isolated_closed_ledger):
    authority, source = pipeline_inputs()
    source["current"]["products"] = [dict(trust="VALIDATED")]
    source["products"] = []
    pipeline = prepare_session(authority, "session", source, now_s=1, network_reachable=False)
    assert pipeline["journal"]["state"] == "SERVICE_REQUIRED"
    assert all(row["trust"] == "UNSUPPORTED" for row in pipeline["current"]["products"])


def test_expired_observations_and_partial_delivery_block_reports(isolated_closed_ledger):
    authority, source, pipeline = prepared_pipeline()
    stage = pipeline["journal"]["stage_ids"][0]
    pending = record_session_intent(authority, pipeline, source, stage, now_s=2, network_reachable=False)
    expired = record_session_report(authority, pending, source, stage, report_id="r", now_s=1001, network_reachable=False)
    assert expired["journal"]["state"] == "SERVICE_REQUIRED"
    assert expired["journal"]["uncertain_stage_id"] == stage
    partial = interrupt_pipeline(pending, reason="PARTIAL_DELIVERY")
    with pytest.raises(CoreSketchError):
        record_session_report(authority, partial, source, stage, report_id="r", now_s=3, network_reachable=False)


def test_resealed_boolean_resource_closure_is_not_consumed(isolated_closed_ledger):
    authority, source = pipeline_inputs()
    source["whole_product_closed"] = True
    source["resource_scenario"]["inputs"]["leave_on_loss_ml"] = None
    pipeline = prepare_session(authority, "session", source, now_s=1, network_reachable=False)
    assert pipeline["journal"]["state"] == "SERVICE_REQUIRED"


@pytest.mark.parametrize("field", ["request", "journal", "physical_routine_complete"])
def test_stored_pipeline_corruption_rejected(field, isolated_closed_ledger):
    _, _, pipeline = prepared_pipeline()
    pipeline[field] = True
    with pytest.raises(CoreSketchError): validate_pipeline(pipeline)
