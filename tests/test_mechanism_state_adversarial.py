import pytest

from masck_one.mechanism_state import MechanismState, OperatingMode, SimulatedTransport, TransitionAction

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
