"""Caller-bound completion evidence cannot be replaced by host progress reports.

All measurements, products and accepted evidence in these tests are synthetic.
The isolated ledger fixture permits host-flow tests without changing production
hardware qualification or granting physical execution authority.
"""
from copy import deepcopy

import pytest

from masck_one.session_pipeline import assess_session_completion, interrupt_pipeline
from test_session_pipeline import (
    completion_inputs, finished_pipeline, isolated_closed_ledger, prepared_pipeline,
)


@pytest.fixture
def finished(isolated_closed_ledger):
    authority, source, pipeline = finished_pipeline()
    assert pipeline["journal"]["state"] == "REPORT_SEQUENCE_FINISHED"
    observations, evidence = completion_inputs(pipeline)
    return authority, source, pipeline, observations, evidence


def assess(values, *, now_s=100, online=False):
    authority, source, pipeline, observations, evidence = values
    return assess_session_completion(authority, pipeline, source, observations, evidence,
                                     now_s=now_s, network_reachable=online)


def blocked(out):
    assert not out["completion_claim_admissible"]
    assert out["blockers"]
    assert not out["physical_routine_complete"]
    assert not out["hardware_execution_authorized"]


def test_scoped_synthetic_completion_stays_reduced_and_does_not_authorize_hardware(finished):
    out = assess(finished)
    assert out["completion_claim_admissible"], out["blockers"]
    assert out["scope"] == "REDUCED_REGION_SURROGATE"
    assert out["completion_assessment"]["reduced_sequence_complete"]
    assert not out["completion_assessment"]["whole_routine_complete"]
    assert not out["physical_routine_complete"]
    assert not out["hardware_execution_authorized"]
    assert assess(finished, online=True) == out


def test_finished_software_sequence_with_scalar_success_cannot_replace_spatial_observations(finished):
    observations = finished[3]
    for key in ("stages", "completed_order", "routine_state"):
        observations.pop(key)
    observations.update(aggregate_coverage_fraction=1, pump_command_count=100,
                        app_animation_state="COMPLETE", physical_routine_complete=True)
    blocked(assess(finished))


@pytest.mark.parametrize("field", ["session_id", "source_digest", "receipt_digest", "plan_digest"])
def test_observations_cannot_be_replayed_from_another_prepared_context(finished, field):
    finished[3][field] = "foreign-context"
    out = assess(finished)
    blocked(out)
    assert ("PLAN_BINDING_CHANGED" if field == "plan_digest" else
            "COMPLETION_" + field.upper() + "_MISMATCH") in out["blockers"]


@pytest.mark.parametrize("field", ["session_id", "source_digest", "receipt_digest"])
def test_missing_caller_binding_is_not_filled_from_pipeline(finished, field):
    finished[3].pop(field)
    blocked(assess(finished))


@pytest.mark.parametrize("mutation", ["missing_stage", "missing_region", "hole", "unknown_holes", "not_complete"])
def test_required_region_obligations_survive_host_pipeline(finished, mutation):
    observations = finished[3]
    stage = observations["stages"]["moisturise"]
    if mutation == "missing_stage":
        observations["stages"].pop("moisturise")
    elif mutation == "missing_region":
        stage.pop("left_cheek")
    elif mutation == "hole":
        stage["left_cheek"]["uncovered_subregions"] = ["stationary-support-shadow"]
    elif mutation == "unknown_holes":
        stage["left_cheek"].pop("uncovered_subregions")
    else:
        stage["left_cheek"]["state"] = "UNKNOWN"
    blocked(assess(finished))


@pytest.mark.parametrize("mutation", ["missing", "wrong_scope", "digital_only", "unaccepted", "failed"])
def test_normal_release_string_requires_separate_scoped_region_evidence(finished, mutation):
    observations, evidence = finished[3:]
    release = next(stage for stage in finished[2]["request"]["plan"]["stages"] if stage["kind"] == "RELEASE")
    region = observations["stages"][release["id"]]["left_cheek"]
    record = next(row for row in evidence if row["id"] in region["evidence_ids"] and row["class"] == "BENCH")
    assert observations["routine_state"] == "NORMAL_RELEASE_COMPLETED"
    if mutation == "missing":
        evidence.remove(record)
    elif mutation == "wrong_scope":
        record["scope"] += "/other-region"
    elif mutation == "digital_only":
        record["class"] = "DIGITAL"
    elif mutation == "unaccepted":
        record["accepted"] = False
    else:
        record["result"] = "FAIL"
    out = assess(finished)
    blocked(out)
    assert release["id"] + ":left_cheek:UNRESOLVED" in out["blockers"]


def test_spf_cannot_inherit_non_claim_product_or_region_evidence(finished):
    evidence = finished[4]
    evidence[:] = [row for row in evidence if row["class"] != "REG_CLAIM"]
    out = assess(finished)
    blocked(out)
    assert "facial_spf:left_cheek:UNRESOLVED" in out["blockers"]


@pytest.mark.parametrize("mutation", ["missing_product", "unaccepted_identity", "unqualified_application"])
def test_completion_rederives_products_instead_of_trusting_cached_validated_rows(finished, mutation):
    source = finished[1]
    if mutation == "missing_product":
        source["products"].pop(0)
    elif mutation == "unaccepted_identity":
        source["product_evidence"][0]["accepted"] = False
    else:
        application = next(iter(source["products"][0]["applications"].values()))
        application["promoted_by"] = "USER_SELF_REPORT"
    out = assess(finished)
    blocked(out)
    assert "SOURCE_CHANGED_AFTER_PREPARATION" in out["blockers"]
    assert any("UNSUPPORTED_PRODUCT_OR_CONTEXT" in b for b in out["blockers"])


def test_completed_evidence_cannot_skip_unfinished_software_sequence(isolated_closed_ledger):
    authority, source, pipeline = prepared_pipeline()
    observations, evidence = completion_inputs(pipeline)
    out = assess((authority, source, pipeline, observations, evidence))
    blocked(out)
    assert "REPORT_SEQUENCE_NOT_FINISHED" in out["blockers"]


def test_emergency_interruption_cannot_reuse_pre_interruption_completion(finished):
    authority, source, pipeline, observations, evidence = finished
    interrupted = interrupt_pipeline(pipeline, reason="EMERGENCY_RELEASE")
    out = assess((authority, source, interrupted, observations, evidence))
    blocked(out)
    assert "REPORT_SEQUENCE_NOT_FINISHED" in out["blockers"]


def test_expired_preparation_blocks_even_fully_scoped_completion_evidence(finished):
    out = assess(finished, now_s=1001)
    blocked(out)
    assert "PREPARATION_OR_OBSERVATIONS_EXPIRED" in out["blockers"]


def test_assessment_does_not_fill_or_mutate_caller_observations_or_evidence(finished):
    _, source, pipeline, observations, evidence = finished
    before = deepcopy((source, pipeline, observations, evidence))
    assess(finished)
    assert (source, pipeline, observations, evidence) == before

