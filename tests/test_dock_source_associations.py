"""Declared dock preparation must keep exact physical source associations."""
from copy import deepcopy

import pytest

from masck_one.core_sketch_contracts import CoreSketchError
from masck_one.dock_preparation import (
    DOSE_BLOCKED, DOSE_PREPARED, account_inventory, derive_session_doses, observe_reservoirs,
    resource_scenario_products,
)


def reservoir(**changes):
    row = dict(slot="a", product="p", sku="SKU-p", market="UK", identity_version="1",
        lot="LOT-1", fill_epoch=0, location="DOCK", readable=True, volume_ml=100.,
        expires_at_s=10000., contamination_state="VERIFIED_CLEAN", density_g_ml=1.)
    return row | changes


def prepare(reservoirs, target=2.):
    binding = {"product_bindings": [dict(id="p", slot="a", sku="SKU-p", market="UK",
        identity_version="1")]}
    demands = {"p": dict(application="MOISTURISE", target_ml=target, min_ml=0., max_ml=3.)}
    return derive_session_doses(demands, reservoirs, binding, now_s=1.)


@pytest.mark.parametrize("reverse", [False, True])
def test_same_product_in_distinct_slots_uses_only_bound_slot(reverse):
    sources = [reservoir(), reservoir(slot="b", lot="OTHER", density_g_ml=9.)]
    if reverse:
        sources.reverse()
    doses = prepare(sources)
    assert doses["doses"][0]["state"] == DOSE_PREPARED
    assert doses["doses"][0]["source_snapshot"]["slot"] == "a"
    rows = resource_scenario_products(doses, sources)
    assert rows["products"][0]["density_g_ml"] == [1., 1.]
    observation = observe_reservoirs(sources, list(reversed(sources)))
    assert observation["preparation_survives"]


@pytest.mark.parametrize("reverse", [False, True])
def test_duplicate_physical_slot_is_rejected_by_producer_and_consumer(reverse):
    sources = [reservoir(), reservoir(product="q", lot="OTHER")]
    if reverse:
        sources.reverse()
    with pytest.raises(CoreSketchError, match="duplicate slot"):
        prepare(sources)
    doses = prepare([reservoir()])
    with pytest.raises(CoreSketchError, match="duplicate slot"):
        resource_scenario_products(doses, sources)


def test_wearable_inventory_cannot_prepare_a_dock_dose():
    doses = prepare([reservoir(location="WEARABLE")])
    assert doses["doses"][0]["state"] == DOSE_BLOCKED
    assert "p:SOURCE_NOT_IN_DOCK" in doses["blockers"]
    assert doses["hardware_execution_authorized"] is False


def test_other_product_in_bound_slot_cannot_be_substituted():
    doses = prepare([reservoir(product="q"), reservoir(slot="b")])
    assert doses["doses"][0]["state"] == DOSE_BLOCKED
    assert "p:LOADED_PRODUCT_DOES_NOT_MATCH_BINDING" in doses["blockers"]


@pytest.mark.parametrize("change", [dict(density_g_ml=2.), dict(lot="LOT-2"),
    dict(fill_epoch=1), dict(contamination_state="UNKNOWN"), dict(expires_at_s=0.),
    dict(location="WEARABLE"), dict(volume_ml=90.)])
def test_consumer_rejects_source_changed_since_declared_preparation(change):
    doses = prepare([reservoir()])
    rows = resource_scenario_products(doses, [reservoir(**change)])
    assert rows["products"][0]["dose_ml"] is None
    assert rows["products"][0]["density_g_ml"] is None
    assert not rows["model_consistent"]
    assert rows["hardware_execution_authorized"] is False


def test_snapshot_is_detached_from_mutable_inventory():
    source = reservoir()
    doses = prepare([source])
    source["density_g_ml"] = 2.
    assert doses["doses"][0]["source_snapshot"]["density_g_ml"] == 1.
    assert resource_scenario_products(doses, [source])["products"][0]["dose_ml"] is None


@pytest.mark.parametrize("mutation", ["missing_snapshot", "quantity", "dose_id"])
def test_incomplete_or_changed_manifest_cannot_restore_resolved_resource_dose(mutation):
    doses = deepcopy(prepare([reservoir()]))
    row = doses["doses"][0]
    if mutation == "missing_snapshot":
        del row["source_snapshot"]
    elif mutation == "quantity":
        row["quantity_ml"] = 1.
    else:
        row["dose_id"] = "unbound"
    assert resource_scenario_products(doses, [reservoir()])["products"][0]["dose_ml"] is None


def test_missing_source_remains_unknown_even_after_preparation():
    doses = prepare([reservoir()])
    row = resource_scenario_products(doses, [reservoir(slot="b")])["products"][0]
    assert row["dose_ml"] is None and row["density_g_ml"] is None


def test_zero_required_dose_is_blocked_even_when_profile_window_allows_zero():
    doses = prepare([reservoir()], target=0.)
    assert doses["doses"][0]["state"] == DOSE_BLOCKED
    assert "p:REQUIRED_DOSE_MUST_BE_POSITIVE" in doses["blockers"]
    assert doses["wearable_session_product_ml"]["high"] is None


@pytest.mark.parametrize("change,event", [
    (dict(contamination_state="UNKNOWN"), "CHANGEOVER_INCOMPLETE"),
    (dict(expires_at_s=500.), "DOSE_EXPIRED"),
    (dict(storage_valid=False), "DOSE_DISTURBED"),
    (dict(storage_state="UNKNOWN"), "DOSE_DISTURBED"),
    (dict(storage_validity="UNKNOWN"), "DOSE_DISTURBED"),
    (dict(hold_history=["interrupted"]), "DOSE_DISTURBED"),
    (dict(preservation="UNPROVED"), "DOSE_DISTURBED"),
    (dict(density_g_ml=2.), "RESOURCE_CHANGED"),
])
def test_storage_cleanliness_and_density_changes_invalidate(change, event):
    observed = observe_reservoirs([reservoir()], [reservoir(**change)])
    assert event in observed["derived_events"]
    assert not observed["preparation_survives"]


@pytest.mark.parametrize("valid", [False, None, "true", 1])
def test_explicit_storage_validity_must_be_true_to_prepare(valid):
    doses = prepare([reservoir(storage_valid=valid)])
    assert doses["doses"][0]["state"] == DOSE_BLOCKED
    assert "p:SOURCE_STORAGE_INVALID_OR_UNKNOWN" in doses["blockers"]


def test_resource_consumer_rejects_duplicate_manifest_binding():
    doses = prepare([reservoir()])
    doses["doses"].append(deepcopy(doses["doses"][0]))
    with pytest.raises(CoreSketchError, match="duplicate product_binding"):
        resource_scenario_products(doses, [reservoir()])


@pytest.mark.parametrize("location", ["DOCK", "WEARABLE"])
def test_zero_known_density_cannot_report_zero_inventory_mass(location):
    with pytest.raises(CoreSketchError, match="strictly positive"):
        account_inventory([reservoir(density_g_ml=0., location=location)], [])


def test_zero_known_density_cannot_report_zero_session_product_mass():
    sources = [reservoir(density_g_ml=0.)]
    doses = prepare(sources)
    with pytest.raises(CoreSketchError, match="strictly positive"):
        resource_scenario_products(doses, sources)


@pytest.mark.parametrize("state", [None, "", "PREPARED", "UNKNOWN"])
def test_undeclared_dose_states_are_rejected_by_resource_and_inventory_consumers(state):
    doses = prepare([reservoir()])
    doses["doses"][0]["state"] = state
    with pytest.raises(CoreSketchError, match="state must be explicit"):
        resource_scenario_products(doses, [reservoir()])
    with pytest.raises(CoreSketchError, match="state must be explicit"):
        account_inventory([reservoir()], doses["doses"])
