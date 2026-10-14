"""Regression tests for dock source-state invalidation boundaries."""
from copy import deepcopy

import pytest

from masck_one.core_sketch_contracts import INVALIDATION_EVENTS
from masck_one.dock_preparation import apply_observed_events, observe_reservoirs


def reservoir(**overrides):
    record = {
        "slot": "a",
        "product": "p",
        "sku": "SKU-p",
        "market": "UK",
        "identity_version": "1",
        "lot": "LOT-1",
        "fill_epoch": 0,
        "location": "DOCK",
        "readable": True,
        "volume_ml": 100.0,
        "expires_at_s": 10_000.0,
        "contamination_state": "VERIFIED_CLEAN",
    }
    record.update(overrides)
    return record


@pytest.mark.parametrize(
    ("change", "expected_event", "expected_reason"),
    [
        ({"contamination_state": "UNKNOWN"}, "CHANGEOVER_INCOMPLETE",
         "CONTAMINATION_STATE_CHANGED"),
        ({"contamination_state": "UNVERIFIED"}, "CHANGEOVER_INCOMPLETE",
         "CONTAMINATION_STATE_CHANGED"),
        ({"expires_at_s": 200.0}, "RESOURCE_CHANGED",
         "SOURCE_EXPIRY_CHANGED"),
        ({"expires_at_s": 20_000.0}, "RESOURCE_CHANGED",
         "SOURCE_EXPIRY_CHANGED"),
        ({"expires_at_s": None}, "DOSE_EXPIRED",
         "SOURCE_EXPIRY_UNKNOWN"),
    ],
)
def test_changed_source_preservation_invalidates_prepared_session(
    change, expected_event, expected_reason
):
    session = {"epoch": 7, "invalidations": [], "cached_ready": True}
    out = apply_observed_events(session, [reservoir()], [reservoir(**change)])
    assert expected_event in out["observation"]["derived_events"]
    assert any(expected_reason in b for b in out["observation"]["blockers"])
    assert not out["observation"]["preparation_survives"]
    assert out["session"]["epoch"] > session["epoch"]
    assert "cached_ready" not in out["session"]
    assert session == {"epoch": 7, "invalidations": [], "cached_ready": True}
    assert not out["hardware_execution_authorized"]


@pytest.mark.parametrize(
    ("state", "event"),
    [
        ({"contamination_state": "UNKNOWN"}, "CHANGEOVER_INCOMPLETE"),
        ({"expires_at_s": None}, "DOSE_EXPIRED"),
    ],
)
def test_unchanged_unresolved_source_cannot_preserve_preparation(state, event):
    source = reservoir(**state)
    observation = observe_reservoirs([source], [deepcopy(source)])
    assert event in observation["derived_events"]
    assert not observation["preparation_survives"]
    assert set(observation["derived_events"]) <= INVALIDATION_EVENTS


def test_restored_cleanliness_still_invalidates_previous_preparation():
    observation = observe_reservoirs(
        [reservoir(contamination_state="UNKNOWN")], [reservoir()]
    )
    assert "CHANGEOVER_INCOMPLETE" in observation["derived_events"]
    assert not observation["preparation_survives"]


def test_unchanged_verified_source_preserves_observation_epoch():
    session = {"epoch": 7, "invalidations": [], "cached_ready": True}
    out = apply_observed_events(session, [reservoir()], [reservoir()])
    assert out["observation"]["derived_events"] == []
    assert out["observation"]["preparation_survives"]
    assert out["session"] == session
    assert not out["hardware_execution_authorized"]
