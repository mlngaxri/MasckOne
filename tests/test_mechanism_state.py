import pytest

from masck_one.mechanism_state import (
    MechanismState, OperatingMode, TransitionAction, validate_transition,
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
    state()
    s = state(mode=OperatingMode.CLEAN, cycle_active=True, retention_engaged=True)
    assert s.evidence_state == "SIMULATED_DIGITAL_STATE_ONLY"


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


def test_service_requires_unretained_closed_release_and_explicit_access_steps():
    idle = state()
    service = state(mode=OperatingMode.SERVICE)
    open_service = state(mode=OperatingMode.SERVICE, service_access_open=True)
    transition(idle, service, TransitionAction.ENTER_SERVICE)
    transition(service, open_service, TransitionAction.OPEN_SERVICE)
    transition(open_service, service, TransitionAction.CLOSE_SERVICE)
    transition(service, idle, TransitionAction.EXIT_SERVICE)


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


def test_provenance_is_deterministic_state_and_mechanism_sensitive():
    a = state()
    b = state()
    c = state(retention_engaged=True)
    d = state(mechanism_provenance_sha256=OTHER)
    assert a.provenance_sha256 == b.provenance_sha256
    assert a.provenance_sha256 != c.provenance_sha256
    assert a.provenance_sha256 != d.provenance_sha256
