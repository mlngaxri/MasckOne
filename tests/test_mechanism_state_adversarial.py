import pytest

from masck_one.mechanism_state import (
    MechanismState,
    OperatingMode,
    SimulatedTransport,
    TransitionAction,
    TRANSITION_CONTRACT,
)

MECH = "1" * 64
OTHER = "2" * 64


def _idle() -> MechanismState:
    return MechanismState(
        mode=OperatingMode.IDLE,
        cycle_active=False,
        retention_engaged=False,
        quick_release_open=False,
        service_access_open=False,
        fault_latched=False,
        mechanism_provenance_sha256=MECH,
    )


def _clean() -> MechanismState:
    return MechanismState(
        mode=OperatingMode.CLEAN,
        cycle_active=True,
        retention_engaged=True,
        quick_release_open=False,
        service_access_open=False,
        fault_latched=False,
        mechanism_provenance_sha256=MECH,
    )


def _retained_fault() -> MechanismState:
    return MechanismState(
        mode=OperatingMode.FAULT,
        cycle_active=False,
        retention_engaged=True,
        quick_release_open=False,
        service_access_open=False,
        fault_latched=True,
        mechanism_provenance_sha256=MECH,
    )


def test_internal_sequence_corruption_fails_before_snapshot_hash_manifest_or_dispatch():
    transport = SimulatedTransport(_idle(), current_mechanism_provenance_sha256=MECH)
    transport._sequence = True
    with pytest.raises(TypeError, match="sequence"):
        _ = transport.sequence
    with pytest.raises(TypeError, match="sequence"):
        transport.snapshot()
    with pytest.raises(TypeError, match="sequence"):
        _ = transport.provenance_sha256
    with pytest.raises(TypeError, match="sequence"):
        transport.manifest()
    with pytest.raises(TypeError, match="sequence"):
        transport.dispatch(TransitionAction.ENGAGE_RETENTION)


def test_negative_internal_sequence_is_value_domain_failure():
    transport = SimulatedTransport(_idle(), current_mechanism_provenance_sha256=MECH)
    transport._sequence = -1
    with pytest.raises(ValueError, match="nonnegative"):
        transport.manifest()


def test_internal_state_corruption_cannot_be_exported_as_simulated_truth():
    transport = SimulatedTransport(_idle(), current_mechanism_provenance_sha256=MECH)
    object.__setattr__(transport._state, "cycle_active", True)
    with pytest.raises(ValueError, match="active cycle requires engaged retention"):
        transport.snapshot()
    with pytest.raises(ValueError, match="active cycle requires engaged retention"):
        transport.manifest()
    with pytest.raises(ValueError, match="active cycle requires engaged retention"):
        transport.dispatch(TransitionAction.ENGAGE_RETENTION)


def test_internal_mechanism_provenance_corruption_is_rejected_even_if_state_is_locally_valid():
    transport = SimulatedTransport(_idle(), current_mechanism_provenance_sha256=MECH)
    object.__setattr__(transport._state, "mechanism_provenance_sha256", OTHER)
    with pytest.raises(ValueError, match="stale mechanism provenance"):
        transport.snapshot()


def test_internal_contract_object_alias_is_rejected():
    transport = SimulatedTransport(_idle(), current_mechanism_provenance_sha256=MECH)

    class FakeState:
        mechanism_provenance_sha256 = MECH

    transport._state = FakeState()
    with pytest.raises(TypeError, match="exact MechanismState"):
        transport.manifest()


def test_illegal_dispatch_is_transactional_and_does_not_advance_sequence_or_state():
    transport = SimulatedTransport(_idle(), current_mechanism_provenance_sha256=MECH)
    before = transport.manifest()
    with pytest.raises(ValueError, match="illegal"):
        transport.dispatch(TransitionAction.START_CLEAN)
    after = transport.manifest()
    assert after == before
    assert transport.sequence == 0


def test_mechanical_quick_release_does_not_require_stop_cycle_or_firmware_command():
    transport = SimulatedTransport(_clean(), current_mechanism_provenance_sha256=MECH)
    released = transport.dispatch(TransitionAction.MECHANICAL_QUICK_RELEASE)
    assert released.mode is OperatingMode.IDLE
    assert released.cycle_active is False
    assert released.retention_engaged is False
    assert released.quick_release_open is True
    assert released.service_access_open is False
    assert released.fault_latched is False
    assert transport.sequence == 1

    manifest = transport.manifest()
    assert manifest["schema"] == "MASCK_ONE_SIMULATED_TRANSPORT_V2"
    assert manifest["transition_contract"] == TRANSITION_CONTRACT
    assert manifest["dispatch_semantics"] == "LOCAL_SIMULATED_STATE_EVENT_ONLY_NOT_HARDWARE_COMMAND"
    assert manifest["telemetry_source"] == "NONE"
    assert manifest["measured_hardware"] is False


def test_mechanical_quick_release_remains_available_from_retained_fault_without_fault_clear():
    transport = SimulatedTransport(_retained_fault(), current_mechanism_provenance_sha256=MECH)
    released = transport.dispatch(TransitionAction.MECHANICAL_QUICK_RELEASE)
    assert released.mode is OperatingMode.FAULT
    assert released.cycle_active is False
    assert released.retention_engaged is False
    assert released.quick_release_open is True
    assert released.fault_latched is True


def test_normal_doff_event_stays_idle_only_while_mechanical_release_is_cycle_independent():
    normal = SimulatedTransport(_clean(), current_mechanism_provenance_sha256=MECH)
    before = normal.manifest()
    with pytest.raises(ValueError, match="illegal"):
        normal.dispatch(TransitionAction.RELEASE_RETENTION)
    assert normal.manifest() == before

    emergency = SimulatedTransport(_clean(), current_mechanism_provenance_sha256=MECH)
    released = emergency.dispatch(TransitionAction.MECHANICAL_QUICK_RELEASE)
    assert released.quick_release_open is True
    assert released.cycle_active is False


@pytest.mark.parametrize(
    "kwargs,match",
    [
        pytest.param(
            dict(
                mode=OperatingMode.SERVICE,
                cycle_active=False,
                retention_engaged=True,
                quick_release_open=False,
                service_access_open=False,
                fault_latched=False,
                mechanism_provenance_sha256=MECH,
            ),
            "SERVICE mode requires retention disengaged",
            id="service-retained",
        ),
        pytest.param(
            dict(
                mode=OperatingMode.SERVICE,
                cycle_active=False,
                retention_engaged=False,
                quick_release_open=True,
                service_access_open=False,
                fault_latched=False,
                mechanism_provenance_sha256=MECH,
            ),
            "SERVICE mode requires quick release reset",
            id="service-release-open",
        ),
        pytest.param(
            dict(
                mode=OperatingMode.FAULT,
                cycle_active=False,
                retention_engaged=True,
                quick_release_open=False,
                service_access_open=True,
                fault_latched=True,
                mechanism_provenance_sha256=MECH,
            ),
            "open service access cannot coexist with engaged retention",
            id="fault-service-access-retained",
        ),
        pytest.param(
            dict(
                mode=OperatingMode.FAULT,
                cycle_active=False,
                retention_engaged=False,
                quick_release_open=True,
                service_access_open=True,
                fault_latched=True,
                mechanism_provenance_sha256=MECH,
            ),
            "open service access cannot coexist with open quick release",
            id="fault-service-access-release-open",
        ),
    ],
)
def test_service_and_release_mechanical_states_cannot_overlap(kwargs, match):
    with pytest.raises(ValueError, match=match):
        MechanismState(**kwargs)
