from __future__ import annotations

"""Stable firmware-facing serialization for HMI fault diagnostics.

``FaultCode`` currently uses Python enum values as an implementation detail. This
module deliberately does not expose those values on a firmware or telemetry boundary.
The explicit identifiers below are the wire contract and therefore do not change if
enum members are reordered or new members are inserted.
"""

from masck_one.hmi_runtime import FaultCode


class HmiFaultWireError(ValueError):
    """Raised when a fault wire value violates the serialization contract."""


_WIRE_IDS: dict[FaultCode, str] = {
    FaultCode.PRESSED_NOT_BOOL: "pressed_not_bool",
    FaultCode.SAMPLE_TIME_INVALID: "sample_time_invalid",
    FaultCode.SAMPLE_TIME_REGRESSION: "sample_time_regression",
    FaultCode.ARM_TIME_INVALID: "arm_time_invalid",
    FaultCode.ARM_TIME_REGRESSION: "arm_time_regression",
    FaultCode.WATCHDOG_TIME_INVALID: "watchdog_time_invalid",
    FaultCode.WATCHDOG_TIME_REGRESSION: "watchdog_time_regression",
    FaultCode.INPUT_STREAM_NOT_STARTED: "input_stream_not_started",
    FaultCode.INPUT_STREAM_STALE: "input_stream_stale",
}


def fault_code_wire_id(code: FaultCode) -> str:
    """Return the stable identifier used across the firmware/telemetry boundary."""
    if type(code) is not FaultCode:
        raise HmiFaultWireError("code must be an exact FaultCode")
    assert_fault_wire_contract_complete()
    try:
        return _WIRE_IDS[code]
    except KeyError as exc:
        raise HmiFaultWireError(f"FaultCode {code.name} has no wire identifier") from exc


def fault_code_from_wire_id(wire_id: str) -> FaultCode:
    """Decode one exact stable wire identifier into its runtime fault code.

    The decoder intentionally rejects aliases, case folding, whitespace normalization
    and non-string values. Firmware or stored telemetry corruption therefore cannot be
    silently reinterpreted as a different valid fault.
    """
    if type(wire_id) is not str:
        raise HmiFaultWireError("wire_id must be an exact str")
    assert_fault_wire_contract_complete()
    matches = [code for code, identifier in _WIRE_IDS.items() if identifier == wire_id]
    if len(matches) != 1:
        raise HmiFaultWireError(f"unknown or ambiguous HMI fault wire identifier: {wire_id!r}")
    return matches[0]


def _canonical_wire_identifier(value: object) -> bool:
    """Return whether a value is an exact lower-ASCII snake-case wire identifier.

    Every segment starts with ``a`` through ``z`` and may then contain lower-ASCII
    letters or decimal digits. Requiring a leading letter keeps the telemetry grammar
    unambiguous for parsers that treat leading digits as numeric tokens.
    """
    if type(value) is not str or not value or not value.isascii():
        return False
    parts = value.split("_")
    return all(
        part
        and "a" <= part[0] <= "z"
        and all(("a" <= char <= "z") or ("0" <= char <= "9") for char in part[1:])
        for part in parts
    )


def assert_fault_wire_contract_complete() -> None:
    """Fail closed if runtime coverage, keys or wire identifiers are malformed or ambiguous."""
    valid_keys = {key for key in _WIRE_IDS if type(key) is FaultCode}
    invalid_key_reprs = sorted(repr(key) for key in _WIRE_IDS if type(key) is not FaultCode)
    missing = set(FaultCode) - valid_keys
    identifiers = tuple(_WIRE_IDS.values())

    duplicate_reprs = sorted(
        {repr(identifier) for identifier in identifiers if identifiers.count(identifier) > 1}
    )
    invalid_reprs = sorted(
        repr(identifier) for identifier in identifiers if not _canonical_wire_identifier(identifier)
    )
    if missing or invalid_key_reprs or duplicate_reprs or invalid_reprs:
        missing_names = sorted(code.name for code in missing)
        raise HmiFaultWireError(
            "fault wire contract mismatch: "
            f"missing={missing_names}, invalid_keys={invalid_key_reprs}, "
            f"duplicates={duplicate_reprs}, invalid={invalid_reprs}"
        )
