import pytest

from masck_one.mechanism_state import MechanismState, OperatingMode


def state(**overrides):
    values = dict(
        mode=OperatingMode.IDLE,
        cycle_active=False,
        retention_engaged=False,
        quick_release_open=False,
        service_access_open=False,
        fault_latched=False,
    )
    values.update(overrides)
    return MechanismState(**values)


def test_idle_and_engaged_clean_are_valid():
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


def test_bool_numeric_aliases_are_rejected():
    with pytest.raises(TypeError, match="cycle_active"):
        state(cycle_active=1)


def test_mode_string_alias_is_rejected():
    with pytest.raises(TypeError, match="mode"):
        state(mode="IDLE")


def test_provenance_is_deterministic_and_state_sensitive():
    a = state()
    b = state()
    c = state(retention_engaged=True)
    assert a.provenance_sha256 == b.provenance_sha256
    assert a.provenance_sha256 != c.provenance_sha256
