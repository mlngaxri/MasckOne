import pytest

import masck_one.hmi_fault_wire as wire
from masck_one.hmi_runtime import FaultCode


@pytest.mark.parametrize(
    "bad_identifier",
    [
        None,
        7,
        True,
        "",
        "Input_Stream_Stale",
        "input stream stale",
        "input__stream_stale",
        "input_stream_stalé",
        "input-stream-stale",
    ],
)
def test_contract_validation_rejects_malformed_identifiers_predictably(monkeypatch, bad_identifier):
    malformed = dict(wire._WIRE_IDS)
    malformed[FaultCode.INPUT_STREAM_STALE] = bad_identifier
    monkeypatch.setattr(wire, "_WIRE_IDS", malformed)

    with pytest.raises(wire.HmiFaultWireError, match="fault wire contract mismatch"):
        wire.assert_fault_wire_contract_complete()


def test_contract_validation_rejects_duplicate_non_string_values_without_type_error(monkeypatch):
    malformed = dict(wire._WIRE_IDS)
    malformed[FaultCode.INPUT_STREAM_STALE] = 7
    malformed[FaultCode.INPUT_STREAM_NOT_STARTED] = 7
    monkeypatch.setattr(wire, "_WIRE_IDS", malformed)

    with pytest.raises(wire.HmiFaultWireError, match="duplicates=.*7.*invalid=.*7"):
        wire.assert_fault_wire_contract_complete()


def test_contract_validation_rejects_duplicate_valid_identifiers(monkeypatch):
    malformed = dict(wire._WIRE_IDS)
    malformed[FaultCode.INPUT_STREAM_NOT_STARTED] = malformed[FaultCode.INPUT_STREAM_STALE]
    monkeypatch.setattr(wire, "_WIRE_IDS", malformed)

    with pytest.raises(wire.HmiFaultWireError, match="duplicates=.*input_stream_stale"):
        wire.assert_fault_wire_contract_complete()


@pytest.mark.parametrize("bad_key", [None, 7, True, "INPUT_STREAM_STALE"])
def test_contract_validation_rejects_non_faultcode_keys_predictably(monkeypatch, bad_key):
    malformed = dict(wire._WIRE_IDS)
    malformed[bad_key] = "unexpected_fault"
    monkeypatch.setattr(wire, "_WIRE_IDS", malformed)

    with pytest.raises(wire.HmiFaultWireError, match="invalid_keys="):
        wire.assert_fault_wire_contract_complete()


def test_contract_validation_reports_missing_code_with_malformed_key(monkeypatch):
    malformed = dict(wire._WIRE_IDS)
    malformed.pop(FaultCode.INPUT_STREAM_STALE)
    malformed["INPUT_STREAM_STALE"] = "input_stream_stale"
    monkeypatch.setattr(wire, "_WIRE_IDS", malformed)

    with pytest.raises(
        wire.HmiFaultWireError,
        match="missing=.*INPUT_STREAM_STALE.*invalid_keys=.*INPUT_STREAM_STALE",
    ):
        wire.assert_fault_wire_contract_complete()


def test_encoder_rejects_corrupted_contract_before_emitting_wire_value(monkeypatch):
    malformed = dict(wire._WIRE_IDS)
    malformed[FaultCode.INPUT_STREAM_STALE] = "INPUT_STREAM_STALE"
    monkeypatch.setattr(wire, "_WIRE_IDS", malformed)

    with pytest.raises(wire.HmiFaultWireError, match="fault wire contract mismatch"):
        wire.fault_code_wire_id(FaultCode.PRESSED_NOT_BOOL)


def test_decoder_rejects_malformed_key_before_returning_non_faultcode(monkeypatch):
    malformed = dict(wire._WIRE_IDS)
    malformed["corrupt-key"] = "corrupt_fault"
    monkeypatch.setattr(wire, "_WIRE_IDS", malformed)

    with pytest.raises(wire.HmiFaultWireError, match="invalid_keys="):
        wire.fault_code_from_wire_id("corrupt_fault")


def test_decoder_rejects_duplicate_contract_before_ambiguous_lookup(monkeypatch):
    malformed = dict(wire._WIRE_IDS)
    malformed[FaultCode.INPUT_STREAM_NOT_STARTED] = malformed[FaultCode.INPUT_STREAM_STALE]
    monkeypatch.setattr(wire, "_WIRE_IDS", malformed)

    with pytest.raises(wire.HmiFaultWireError, match="duplicates=.*input_stream_stale"):
        wire.fault_code_from_wire_id("input_stream_stale")
