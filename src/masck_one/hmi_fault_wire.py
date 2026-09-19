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
    matches = [code for code, identifier in _WIRE_IDS.items() if identifier == wire_id]
    if len(matches) != 1:
        raise HmiFaultWireError(f"unknown or ambiguous HMI fault wire identifier: {wire_id!r}")
    return matches[0]


def assert_fault_wire_contract_complete() -> None:
    """Fail if runtime coverage or wire identifier uniqueness is incomplete."""
    missing = set(FaultCode) - set(_WIRE_IDS)
    extra = set(_WIRE_IDS) - set(FaultCode)
    identifiers = tuple(_WIRE_IDS.values())
    duplicates = sorted({identifier for identifier in identifiers if identifiers.count(identifier) > 1})
    invalid = sorted(
        repr(identifier)
        for identifier in identifiers
        if type(identifier) is not str or not identifier or identifier.strip() != identifier
    )
    if missing or extra or duplicates or invalid:
        missing_names = sorted(code.name for code in missing)
        extra_names = sorted(code.name for code in extra)
        raise HmiFaultWireError(
            "fault wire contract mismatch: "
            f"missing={missing_names}, extra={extra_names}, "
            f"duplicates={duplicates}, invalid={invalid}"
        )
