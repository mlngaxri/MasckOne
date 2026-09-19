import pytest

from masck_one.hmi_fault_wire import (
    HmiFaultWireError,
    assert_fault_wire_contract_complete,
    fault_code_wire_id,
)
from masck_one.hmi_runtime import FaultCode


def test_every_runtime_fault_has_exactly_one_wire_identifier():
    assert_fault_wire_contract_complete()
    identifiers = [fault_code_wire_id(code) for code in FaultCode]
    assert len(identifiers) == len(FaultCode)
    assert len(set(identifiers)) == len(identifiers)


def test_wire_identifiers_are_explicit_and_stable():
    assert fault_code_wire_id(FaultCode.PRESSED_NOT_BOOL) == "pressed_not_bool"
    assert fault_code_wire_id(FaultCode.SAMPLE_TIME_INVALID) == "sample_time_invalid"
    assert fault_code_wire_id(FaultCode.SAMPLE_TIME_REGRESSION) == "sample_time_regression"
    assert fault_code_wire_id(FaultCode.ARM_TIME_INVALID) == "arm_time_invalid"
    assert fault_code_wire_id(FaultCode.ARM_TIME_REGRESSION) == "arm_time_regression"
    assert fault_code_wire_id(FaultCode.WATCHDOG_TIME_INVALID) == "watchdog_time_invalid"
    assert fault_code_wire_id(FaultCode.WATCHDOG_TIME_REGRESSION) == "watchdog_time_regression"
    assert fault_code_wire_id(FaultCode.INPUT_STREAM_NOT_STARTED) == "input_stream_not_started"
    assert fault_code_wire_id(FaultCode.INPUT_STREAM_STALE) == "input_stream_stale"


@pytest.mark.parametrize("bad", [None, "input_stream_stale", 1, True])
def test_wire_encoder_rejects_non_fault_codes(bad):
    with pytest.raises(HmiFaultWireError, match="exact FaultCode"):
        fault_code_wire_id(bad)  # type: ignore[arg-type]
