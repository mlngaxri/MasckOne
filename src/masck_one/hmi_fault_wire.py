from __future__ import annotations

"""Stable firmware-facing serialization for HMI fault diagnostics.

``FaultCode`` currently uses Python enum values as an implementation detail. This
module deliberately does not expose those values on a firmware or telemetry boundary.
The explicit identifiers below are the wire contract and therefore do not change if
enum members are reordered or new members are inserted.
"""

from masck_one.hmi_runtime import FaultCode


class HmiFaultWireError(ValueError):
    """Raised when a caller attempts to encode an unsupported fault code."""


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
    """Return the stable identifier used across the firmware/telemetry boundary.

    Exact ``FaultCode`` membership is required. Failing explicitly here prevents a
    malformed or future unsupported value from being silently serialized as a valid
    diagnostic.
    """
    if type(code) is not FaultCode:
        raise HmiFaultWireError("code must be an exact FaultCode")
    try:
        return _WIRE_IDS[code]
    except KeyError as exc:
        raise HmiFaultWireError(f"FaultCode {code.name} has no wire identifier") from exc


def assert_fault_wire_contract_complete() -> None:
    """Fail if a new runtime fault code has not been assigned a wire identifier."""
    missing = set(FaultCode) - set(_WIRE_IDS)
    extra = set(_WIRE_IDS) - set(FaultCode)
    if missing or extra:
        missing_names = sorted(code.name for code in missing)
        extra_names = sorted(code.name for code in extra)
        raise HmiFaultWireError(
            f"fault wire contract mismatch: missing={missing_names}, extra={extra_names}"
        )
