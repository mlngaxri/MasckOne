import pytest

import masck_one.hmi_fault_wire as wire
from masck_one.hmi_runtime import FaultCode


def test_canonical_fault_wire_table_rejects_in_place_mutation() -> None:
    original = wire.fault_code_wire_id(FaultCode.INPUT_STREAM_STALE)

    with pytest.raises(TypeError):
        wire._WIRE_IDS[FaultCode.INPUT_STREAM_STALE] = "input_stream_timeout"  # type: ignore[index]

    assert wire.fault_code_wire_id(FaultCode.INPUT_STREAM_STALE) == original


def test_canonical_fault_wire_table_rejects_in_place_deletion() -> None:
    with pytest.raises(TypeError):
        del wire._WIRE_IDS[FaultCode.INPUT_STREAM_STALE]  # type: ignore[attr-defined]

    wire.assert_fault_wire_contract_complete()
