import pytest

import masck_one.hmi_fault_wire as wire
from masck_one.hmi_fault_wire import HmiFaultWireError, assert_fault_wire_contract_complete
from masck_one.hmi_runtime import FaultCode


@pytest.mark.parametrize(
    "malformed",
    [
        "1input_stream_stale",
        "input_2stream_stale",
        "input_stream_3",
        "input_stream_stalé",
        "input__stream_stale",
    ],
)
def test_contract_rejects_noncanonical_identifier_segments(monkeypatch, malformed):
    corrupted = dict(wire._WIRE_IDS)
    corrupted[FaultCode.INPUT_STREAM_STALE] = malformed
    monkeypatch.setattr(wire, "_WIRE_IDS", corrupted)

    with pytest.raises(HmiFaultWireError, match="fault wire contract mismatch"):
        assert_fault_wire_contract_complete()


def test_digit_suffix_is_valid_grammar_but_rejected_as_semantic_drift(monkeypatch):
    identifier = "input_stream_stale2"
    assert wire._canonical_wire_identifier(identifier)

    corrupted = dict(wire._WIRE_IDS)
    corrupted[FaultCode.INPUT_STREAM_STALE] = identifier
    monkeypatch.setattr(wire, "_WIRE_IDS", corrupted)

    with pytest.raises(HmiFaultWireError, match="semantic_mismatches=.*INPUT_STREAM_STALE"):
        assert_fault_wire_contract_complete()
