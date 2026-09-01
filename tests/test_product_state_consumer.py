import pytest

from masck_one.mechanism_state import MechanismState, OperatingMode, TransitionAction
from masck_one.product_state_consumer import (
    CONNECTIVITY_MODEL,
    CONSUMER_CONTRACT,
    HARDWARE_COMMAND_CAPABILITY,
    ConsumerInputChannel,
    ProductStateConsumer,
    legal_actions_for_channel,
    transition_semantics,
)

MECH = "1" * 64


def state(**overrides):
    values = dict(
        mode=OperatingMode.IDLE,
        cycle_active=False,
        retention_engaged=False,
        quick_release_open=False,
        service_access_open=False,
        fault_latched=False,
        mechanism_provenance_sha256=MECH,
    )
    values.update(overrides)
    return MechanismState(**values)


def consumer(initial=None):
    return ProductStateConsumer(
        state() if initial is None else initial,
        current_mechanism_provenance_sha256=MECH,
    )


def test_every_transition_has_one_canonical_consumer_channel():
    channels = {action: transition_semantics(action).channel for action in TransitionAction}
    assert set(channels) == set(TransitionAction)

    assert channels[TransitionAction.MECHANICAL_QUICK_RELEASE] is ConsumerInputChannel.SIMULATED_MECHANICAL_EVENT
    assert channels[TransitionAction.ENGAGE_RETENTION] is ConsumerInputChannel.SIMULATED_MECHANICAL_EVENT
    assert channels[TransitionAction.COMPLETE_CYCLE] is ConsumerInputChannel.SIMULATED_DEVICE_EVENT
    assert channels[TransitionAction.LATCH_FAULT] is ConsumerInputChannel.SIMULATED_DEVICE_EVENT
    assert channels[TransitionAction.CLEAR_FAULT] is ConsumerInputChannel.SIMULATED_DEVICE_EVENT
    assert channels[TransitionAction.START_CLEAN] is ConsumerInputChannel.UI_INTENT
    assert channels[TransitionAction.START_WARM] is ConsumerInputChannel.UI_INTENT
    assert channels[TransitionAction.STOP_CYCLE] is ConsumerInputChannel.UI_INTENT


def test_idle_manifest_exposes_only_legal_ui_intents_and_explicit_nonhardware_semantics():
    c = consumer()
    manifest = c.manifest()

    assert manifest["schema"] == CONSUMER_CONTRACT
    assert manifest["hardware_command_capability"] == HARDWARE_COMMAND_CAPABILITY == "NONE_SIMULATION_ONLY"
    assert manifest["connectivity_model"] == CONNECTIVITY_MODEL == "ABSENT_NOT_MODELED"
    assert manifest["telemetry_source"] == "NONE"
    assert manifest["measured_hardware"] is False
    assert manifest["sequence"] == 0
    assert manifest["last_event"] is None
    assert manifest["available_ui_intents"] == ["ENTER_SERVICE"]
    assert manifest["available_simulated_mechanical_events"] == ["ENGAGE_RETENTION"]
    assert manifest["available_simulated_device_events"] == ["LATCH_FAULT"]
    assert all(item["hardware_command"] is False for item in manifest["action_semantics"])
    assert not any("ble" in key.lower() or "connected" in key.lower() for key in manifest)


def test_retained_state_exposes_cycle_intents_but_never_quick_release_as_ui_control():
    c = consumer(state(retention_engaged=True))
    manifest = c.manifest()
    assert manifest["available_ui_intents"] == ["START_CLEAN", "START_WARM"]
    assert manifest["available_simulated_mechanical_events"] == [
        "RELEASE_RETENTION",
        "MECHANICAL_QUICK_RELEASE",
    ]
    assert "MECHANICAL_QUICK_RELEASE" not in manifest["available_ui_intents"]


def test_ui_cannot_dispatch_mechanical_release_and_rejection_is_transactional():
    c = consumer(state(retention_engaged=True))
    before = c.manifest()
    with pytest.raises(ValueError, match="SIMULATED_MECHANICAL_EVENT, not UI_INTENT"):
        c.submit_ui_intent(TransitionAction.MECHANICAL_QUICK_RELEASE)
    assert c.manifest() == before
    assert c.sequence == 0


def test_ui_cannot_fake_device_completion_or_fault_events():
    clean = state(mode=OperatingMode.CLEAN, cycle_active=True, retention_engaged=True)
    c = consumer(clean)
    before = c.manifest()
    with pytest.raises(ValueError, match="SIMULATED_DEVICE_EVENT, not UI_INTENT"):
        c.submit_ui_intent(TransitionAction.COMPLETE_CYCLE)
    assert c.manifest() == before

    idle = consumer()
    before_idle = idle.manifest()
    with pytest.raises(ValueError, match="SIMULATED_DEVICE_EVENT, not UI_INTENT"):
        idle.submit_ui_intent(TransitionAction.LATCH_FAULT)
    assert idle.manifest() == before_idle


def test_mechanical_event_channel_cannot_be_used_to_start_a_cycle():
    c = consumer(state(retention_engaged=True))
    before = c.manifest()
    with pytest.raises(ValueError, match="UI_INTENT, not SIMULATED_MECHANICAL_EVENT"):
        c.observe_simulated_mechanical_event(TransitionAction.START_CLEAN)
    assert c.manifest() == before


def test_device_event_channel_cannot_be_used_for_user_stop():
    clean = state(mode=OperatingMode.CLEAN, cycle_active=True, retention_engaged=True)
    c = consumer(clean)
    before = c.manifest()
    with pytest.raises(ValueError, match="UI_INTENT, not SIMULATED_DEVICE_EVENT"):
        c.observe_simulated_device_event(TransitionAction.STOP_CYCLE)
    assert c.manifest() == before


def test_quick_release_remains_available_as_unpowered_mechanical_observation_during_cycle():
    clean = state(mode=OperatingMode.CLEAN, cycle_active=True, retention_engaged=True)
    c = consumer(clean)
    assert c.manifest()["available_simulated_mechanical_events"] == ["MECHANICAL_QUICK_RELEASE"]

    released = c.observe_simulated_mechanical_event(TransitionAction.MECHANICAL_QUICK_RELEASE)
    assert released.mode is OperatingMode.IDLE
    assert released.cycle_active is False
    assert released.retention_engaged is False
    assert released.quick_release_open is True
    assert c.sequence == 1
    assert c.last_event == "MECHANICAL_QUICK_RELEASE"
    assert c.manifest()["available_ui_intents"] == []


def test_completion_and_fault_clear_are_simulated_device_events_not_ui_authority():
    clean = consumer(state(mode=OperatingMode.CLEAN, cycle_active=True, retention_engaged=True))
    completed = clean.observe_simulated_device_event(TransitionAction.COMPLETE_CYCLE)
    assert completed.mode is OperatingMode.IDLE
    assert completed.retention_engaged is True
    assert clean.last_event == "COMPLETE_CYCLE"

    fault = consumer(
        state(mode=OperatingMode.FAULT, retention_engaged=True, fault_latched=True)
    )
    assert fault.manifest()["available_ui_intents"] == []
    assert fault.manifest()["available_simulated_device_events"] == ["CLEAR_FAULT"]
    cleared = fault.observe_simulated_device_event(TransitionAction.CLEAR_FAULT)
    assert cleared.mode is OperatingMode.IDLE
    assert cleared.fault_latched is False
    assert cleared.retention_engaged is True


def test_legal_action_queries_reject_alias_types_and_preserve_transition_order():
    retained = state(retention_engaged=True)
    assert legal_actions_for_channel(retained, ConsumerInputChannel.UI_INTENT) == (
        TransitionAction.START_CLEAN,
        TransitionAction.START_WARM,
    )
    with pytest.raises(TypeError, match="channel"):
        legal_actions_for_channel(retained, "UI_INTENT")
    with pytest.raises(TypeError, match="action"):
        transition_semantics("START_CLEAN")


def test_consumer_provenance_is_deterministic_and_event_sensitive():
    a = consumer(state(retention_engaged=True))
    b = consumer(state(retention_engaged=True))
    assert a.provenance_sha256 == b.provenance_sha256
    assert a.manifest() == b.manifest()

    a.submit_ui_intent(TransitionAction.START_CLEAN)
    assert a.provenance_sha256 != b.provenance_sha256
    assert a.manifest()["consumer_provenance_sha256"] == a.provenance_sha256


def test_internal_transport_corruption_cannot_be_exported_through_consumer_boundary():
    c = consumer()
    object.__setattr__(c._transport._state, "cycle_active", True)
    with pytest.raises(ValueError, match="active cycle requires engaged retention"):
        c.manifest()


def test_wrong_internal_transport_type_fails_closed():
    c = consumer()
    c._transport = object()
    with pytest.raises(TypeError, match="exact SimulatedTransport"):
        c.manifest()
