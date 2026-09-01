import pytest

from masck_one.mechanism_state import (
    MechanismState,
    OperatingMode,
    ReadinessState,
    SimulatedTransport,
    TransitionAction,
    derive_next_state,
    validate_transition,
)

MECH = "1" * 64
OTHER = "2" * 64


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


def transition(before, after, action, current=MECH):
    validate_transition(
        before, after, action,
        current_mechanism_provenance_sha256=current,
    )


def test_idle_and_engaged_clean_are_valid_and_simulation_only():
    idle = state()
    s = state(mode=OperatingMode.CLEAN, cycle_active=True, retention_engaged=True)
    assert idle.readiness is ReadinessState.NOT_RETAINED
    assert s.evidence_state == "SIMULATED_DIGITAL_STATE_ONLY"
    assert s.readiness is ReadinessState.CYCLE_ACTIVE


@pytest.mark.parametrize("kwargs", [
    dict(quick_release_open=True, retention_engaged=True),
    dict(mode=OperatingMode.CLEAN, cycle_active=True, retention_engaged=False),
    dict(mode=OperatingMode.CLEAN, cycle_active=True, retention_engaged=True, quick_release_open=True),
    dict(mode=OperatingMode.CLEAN, cycle_active=True, retention_engaged=True, service_access_open=True),
    dict(service_access_open=True),
    dict(mode=OperatingMode.SERVICE, cycle_active=True, retention_engaged=True),
    dict(mode=OperatingMode.FAULT, fault_latched=False),
    dict(mode=OperatingMode.IDLE, fault_latched=True),
    dict(mode=OperatingMode.CLEAN, cycle_active=False),
    dict(mode=OperatingMode.IDLE, cycle_active=True, retention_engaged=True),
])
def test_impossible_combinations_fail_closed(kwargs):
    with pytest.raises(ValueError):
        state(**kwargs)


def test_exact_types_and_canonical_mechanism_identity_are_required():
    with pytest.raises(TypeError, match="cycle_active"):
        state(cycle_active=1)
    with pytest.raises(TypeError, match="mode"):
        state(mode="IDLE")
    with pytest.raises(TypeError, match="mechanism_provenance"):
        state(mechanism_provenance_sha256=bytes(32))
    with pytest.raises(ValueError, match="canonical"):
        state(mechanism_provenance_sha256="A" * 64)


def test_nominal_retention_cycle_release_sequence_is_explicit():
    idle = state()
    retained = state(retention_engaged=True)
    clean = state(mode=OperatingMode.CLEAN, cycle_active=True, retention_engaged=True)
    released = state(quick_release_open=True)
    transition(idle, retained, TransitionAction.ENGAGE_RETENTION)
    transition(retained, clean, TransitionAction.START_CLEAN)
    transition(clean, retained, TransitionAction.STOP_CYCLE)
    transition(retained, released, TransitionAction.RELEASE_RETENTION)
    transition(released, idle, TransitionAction.RESET_RELEASE)
    assert retained.readiness is ReadinessState.READY_FOR_CYCLE
    assert released.readiness is ReadinessState.RELEASE_OPEN


def test_service_requires_unretained_closed_release_and_explicit_access_steps():
    idle = state()
    service = state(mode=OperatingMode.SERVICE)
    open_service = state(mode=OperatingMode.SERVICE, service_access_open=True)
    transition(idle, service, TransitionAction.ENTER_SERVICE)
    transition(service, open_service, TransitionAction.OPEN_SERVICE)
    transition(open_service, service, TransitionAction.CLOSE_SERVICE)
    transition(service, idle, TransitionAction.EXIT_SERVICE)
    assert service.readiness is ReadinessState.SERVICE
    assert open_service.readiness is ReadinessState.SERVICE


def test_direct_clean_to_service_and_other_wrong_action_results_fail_closed():
    retained = state(retention_engaged=True)
    clean = state(mode=OperatingMode.CLEAN, cycle_active=True, retention_engaged=True)
    service = state(mode=OperatingMode.SERVICE)
    with pytest.raises(ValueError):
        transition(clean, service, TransitionAction.ENTER_SERVICE)
    with pytest.raises(ValueError):
        transition(retained, service, TransitionAction.RELEASE_RETENTION)
    with pytest.raises(ValueError):
        transition(clean, retained, TransitionAction.START_CLEAN)


def test_fault_latch_is_fail_safe_and_preserves_mechanical_positions():
    clean = state(mode=OperatingMode.CLEAN, cycle_active=True, retention_engaged=True)
    fault = state(mode=OperatingMode.FAULT, retention_engaged=True, fault_latched=True)
    transition(clean, fault, TransitionAction.LATCH_FAULT)
    retained = state(retention_engaged=True)
    transition(fault, retained, TransitionAction.CLEAR_FAULT)
    assert fault.readiness is ReadinessState.FAULT_BLOCKED


def test_stale_mechanism_provenance_is_rejected_on_either_snapshot_or_current():
    current = state()
    stale = state(mechanism_provenance_sha256=OTHER)
    retained = state(retention_engaged=True)
    with pytest.raises(ValueError, match="stale"):
        transition(stale, retained, TransitionAction.ENGAGE_RETENTION)
    stale_retained = state(retention_engaged=True, mechanism_provenance_sha256=OTHER)
    with pytest.raises(ValueError, match="stale"):
        transition(current, stale_retained, TransitionAction.ENGAGE_RETENTION)
    with pytest.raises(ValueError, match="stale"):
        transition(current, retained, TransitionAction.ENGAGE_RETENTION, current=OTHER)


def test_transition_boundary_rejects_alias_types():
    class LyingStr(str):
        def __eq__(self, other):
            return True

    with pytest.raises(TypeError, match="current_mechanism"):
        transition(state(), state(retention_engaged=True), TransitionAction.ENGAGE_RETENTION, current=LyingStr(OTHER))
    with pytest.raises(TypeError, match="action"):
        transition(state(), state(retention_engaged=True), "ENGAGE_RETENTION")
    with pytest.raises(TypeError, match="action"):
        derive_next_state(state(), "ENGAGE_RETENTION", current_mechanism_provenance_sha256=MECH)


def test_provenance_is_deterministic_state_and_mechanism_sensitive():
    a = state()
    b = state()
    c = state(retention_engaged=True)
    d = state(mechanism_provenance_sha256=OTHER)
    assert a.provenance_sha256 == b.provenance_sha256
    assert a.provenance_sha256 != c.provenance_sha256
    assert a.provenance_sha256 != d.provenance_sha256


def test_postconstruction_corruption_cannot_hash_derive_or_validate():
    corrupted = state()
    object.__setattr__(corrupted, "cycle_active", True)
    with pytest.raises(ValueError, match="active cycle requires engaged retention"):
        _ = corrupted.provenance_sha256
    with pytest.raises(ValueError, match="active cycle requires engaged retention"):
        derive_next_state(
            corrupted,
            TransitionAction.ENGAGE_RETENTION,
            current_mechanism_provenance_sha256=MECH,
        )
    with pytest.raises(ValueError, match="active cycle requires engaged retention"):
        transition(corrupted, state(retention_engaged=True), TransitionAction.ENGAGE_RETENTION)


def test_postconstruction_evidence_or_identity_alias_corruption_fails_closed():
    class LyingStr(str):
        def __eq__(self, other):
            return True

    corrupted = state()
    object.__setattr__(corrupted, "mechanism_provenance_sha256", LyingStr(OTHER))
    with pytest.raises(TypeError, match="mechanism_provenance"):
        _ = corrupted.provenance_sha256

    corrupted_mode = state()
    object.__setattr__(corrupted_mode, "mode", "IDLE")
    with pytest.raises(TypeError, match="mode"):
        _ = corrupted_mode.readiness


def test_derive_next_state_is_the_canonical_transition_constructor():
    idle = state()
    retained = derive_next_state(
        idle,
        TransitionAction.ENGAGE_RETENTION,
        current_mechanism_provenance_sha256=MECH,
    )
    assert retained == state(retention_engaged=True)
    clean = derive_next_state(
        retained,
        TransitionAction.START_CLEAN,
        current_mechanism_provenance_sha256=MECH,
    )
    assert clean == state(mode=OperatingMode.CLEAN, cycle_active=True, retention_engaged=True)


def test_simulated_transport_has_no_ble_or_measured_telemetry_semantics():
    transport = SimulatedTransport(state(), current_mechanism_provenance_sha256=MECH)
    manifest = transport.manifest()
    assert manifest["transport_kind"] == "SIMULATED_LOCAL_ONLY"
    assert manifest["telemetry_source"] == "NONE"
    assert manifest["measured_hardware"] is False
    assert manifest["sequence"] == 0
    assert manifest["state"]["readiness"] == "NOT_RETAINED"
    assert manifest["state"]["evidence_state"] == "SIMULATED_DIGITAL_STATE_ONLY"


def test_simulated_transport_dispatches_only_legal_canonical_states():
    transport = SimulatedTransport(state(), current_mechanism_provenance_sha256=MECH)
    retained = transport.dispatch(TransitionAction.ENGAGE_RETENTION)
    assert retained.readiness is ReadinessState.READY_FOR_CYCLE
    clean = transport.dispatch(TransitionAction.START_CLEAN)
    assert clean.mode is OperatingMode.CLEAN
    assert clean.readiness is ReadinessState.CYCLE_ACTIVE
    idle_retained = transport.dispatch(TransitionAction.STOP_CYCLE)
    assert idle_retained == state(retention_engaged=True)
    assert transport.sequence == 3
    with pytest.raises(ValueError, match="illegal"):
        transport.dispatch(TransitionAction.ENTER_SERVICE)
    with pytest.raises(TypeError, match="action"):
        transport.dispatch("STOP_CYCLE")


def test_simulated_transport_defensive_copy_blocks_caller_state_mutation():
    initial = state()
    transport = SimulatedTransport(initial, current_mechanism_provenance_sha256=MECH)
    object.__setattr__(initial, "cycle_active", True)
    assert transport.snapshot() == state()

    leaked = transport.snapshot()
    object.__setattr__(leaked, "cycle_active", True)
    assert transport.snapshot() == state()
    assert transport.manifest()["state"]["cycle_active"] is False


def test_simulated_transport_rejects_stale_and_hostile_current_identity():
    with pytest.raises(ValueError, match="stale"):
        SimulatedTransport(state(), current_mechanism_provenance_sha256=OTHER)

    class LyingStr(str):
        def __eq__(self, other):
            return True

    with pytest.raises(TypeError, match="current_mechanism"):
        SimulatedTransport(state(), current_mechanism_provenance_sha256=LyingStr(OTHER))


def test_simulated_transport_provenance_changes_with_state_and_sequence_deterministically():
    a = SimulatedTransport(state(), current_mechanism_provenance_sha256=MECH)
    b = SimulatedTransport(state(), current_mechanism_provenance_sha256=MECH)
    assert a.provenance_sha256 == b.provenance_sha256
    a.dispatch(TransitionAction.ENGAGE_RETENTION)
    assert a.provenance_sha256 != b.provenance_sha256
    b.dispatch(TransitionAction.ENGAGE_RETENTION)
    assert a.provenance_sha256 == b.provenance_sha256
