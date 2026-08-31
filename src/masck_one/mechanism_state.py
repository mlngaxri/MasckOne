"""Deterministic simulated mechanism state and transition contract.

The contract prevents digital consumers from inventing mechanically contradictory
snapshots or temporal jumps. It is simulation-only and is not measured telemetry.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import re

_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


def _require_sha256(name: str, value: object) -> str:
    if type(value) is not str:
        raise TypeError(f"{name} must be exact str")
    if _SHA256_RE.fullmatch(value) is None:
        raise ValueError(f"{name} must be canonical lowercase SHA-256")
    return value


class OperatingMode(str, Enum):
    IDLE = "IDLE"
    CLEAN = "CLEAN"
    WARM = "WARM"
    SERVICE = "SERVICE"
    FAULT = "FAULT"


class TransitionAction(str, Enum):
    ENGAGE_RETENTION = "ENGAGE_RETENTION"
    RELEASE_RETENTION = "RELEASE_RETENTION"
    RESET_RELEASE = "RESET_RELEASE"
    START_CLEAN = "START_CLEAN"
    START_WARM = "START_WARM"
    STOP_CYCLE = "STOP_CYCLE"
    ENTER_SERVICE = "ENTER_SERVICE"
    EXIT_SERVICE = "EXIT_SERVICE"
    OPEN_SERVICE = "OPEN_SERVICE"
    CLOSE_SERVICE = "CLOSE_SERVICE"
    LATCH_FAULT = "LATCH_FAULT"
    CLEAR_FAULT = "CLEAR_FAULT"


@dataclass(frozen=True)
class MechanismState:
    """One immutable, fail-closed snapshot bound to released mechanism identity."""

    mode: OperatingMode
    cycle_active: bool
    retention_engaged: bool
    quick_release_open: bool
    service_access_open: bool
    fault_latched: bool
    mechanism_provenance_sha256: str

    def __post_init__(self) -> None:
        if type(self.mode) is not OperatingMode:
            raise TypeError("mode must be exact OperatingMode")
        for name in (
            "cycle_active", "retention_engaged", "quick_release_open",
            "service_access_open", "fault_latched",
        ):
            if type(getattr(self, name)) is not bool:
                raise TypeError(f"{name} must be exact bool")
        _require_sha256("mechanism_provenance_sha256", self.mechanism_provenance_sha256)

        if self.quick_release_open and self.retention_engaged:
            raise ValueError("quick release open cannot coexist with engaged retention")
        if self.cycle_active and not self.retention_engaged:
            raise ValueError("active cycle requires engaged retention")
        if self.cycle_active and (self.quick_release_open or self.service_access_open):
            raise ValueError("active cycle cannot coexist with release/service access")
        if self.service_access_open and self.mode not in (OperatingMode.SERVICE, OperatingMode.FAULT):
            raise ValueError("open service access requires SERVICE or FAULT mode")
        if self.mode is OperatingMode.SERVICE and self.cycle_active:
            raise ValueError("SERVICE mode cannot run a cycle")
        if self.mode is OperatingMode.FAULT and not self.fault_latched:
            raise ValueError("FAULT mode requires a latched fault")
        if self.fault_latched and self.mode is not OperatingMode.FAULT:
            raise ValueError("latched fault requires FAULT mode")
        if self.mode in (OperatingMode.CLEAN, OperatingMode.WARM) and not self.cycle_active:
            raise ValueError("CLEAN/WARM mode requires active cycle")
        if self.cycle_active and self.mode not in (OperatingMode.CLEAN, OperatingMode.WARM):
            raise ValueError("active cycle requires CLEAN or WARM mode")

    @property
    def evidence_state(self) -> str:
        return "SIMULATED_DIGITAL_STATE_ONLY"

    @property
    def provenance_sha256(self) -> str:
        payload = {
            "schema": "MASCK_ONE_MECHANISM_STATE_V2",
            "mode": self.mode.value,
            "cycle_active": self.cycle_active,
            "retention_engaged": self.retention_engaged,
            "quick_release_open": self.quick_release_open,
            "service_access_open": self.service_access_open,
            "fault_latched": self.fault_latched,
            "mechanism_provenance_sha256": self.mechanism_provenance_sha256,
            "evidence_state": self.evidence_state,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("ascii")
        return hashlib.sha256(encoded).hexdigest()


def _fields(state: MechanismState) -> tuple[object, ...]:
    return (
        state.mode, state.cycle_active, state.retention_engaged,
        state.quick_release_open, state.service_access_open, state.fault_latched,
    )


def validate_transition(
    before: MechanismState,
    after: MechanismState,
    action: TransitionAction,
    *,
    current_mechanism_provenance_sha256: str,
) -> None:
    """Fail closed unless ``after`` is the exact legal result of ``action``.

    Both snapshots must bind the exact current released mechanism identity. Timing,
    sensor response and physical interlocks remain evidence-gated.
    """
    if type(before) is not MechanismState or type(after) is not MechanismState:
        raise TypeError("before and after must be exact MechanismState")
    if type(action) is not TransitionAction:
        raise TypeError("action must be exact TransitionAction")
    current = _require_sha256(
        "current_mechanism_provenance_sha256", current_mechanism_provenance_sha256
    )
    if before.mechanism_provenance_sha256 != current or after.mechanism_provenance_sha256 != current:
        raise ValueError("stale mechanism provenance")

    b = _fields(before)
    a = _fields(after)
    expected: tuple[object, ...] | None = None

    if action is TransitionAction.ENGAGE_RETENTION and b == (OperatingMode.IDLE, False, False, False, False, False):
        expected = (OperatingMode.IDLE, False, True, False, False, False)
    elif action is TransitionAction.RELEASE_RETENTION and b == (OperatingMode.IDLE, False, True, False, False, False):
        expected = (OperatingMode.IDLE, False, False, True, False, False)
    elif action is TransitionAction.RESET_RELEASE and b == (OperatingMode.IDLE, False, False, True, False, False):
        expected = (OperatingMode.IDLE, False, False, False, False, False)
    elif action in (TransitionAction.START_CLEAN, TransitionAction.START_WARM) and b == (OperatingMode.IDLE, False, True, False, False, False):
        mode = OperatingMode.CLEAN if action is TransitionAction.START_CLEAN else OperatingMode.WARM
        expected = (mode, True, True, False, False, False)
    elif action is TransitionAction.STOP_CYCLE and b[0] in (OperatingMode.CLEAN, OperatingMode.WARM) and b[1:6] == (True, True, False, False, False):
        expected = (OperatingMode.IDLE, False, True, False, False, False)
    elif action is TransitionAction.ENTER_SERVICE and b == (OperatingMode.IDLE, False, False, False, False, False):
        expected = (OperatingMode.SERVICE, False, False, False, False, False)
    elif action is TransitionAction.OPEN_SERVICE and b == (OperatingMode.SERVICE, False, False, False, False, False):
        expected = (OperatingMode.SERVICE, False, False, False, True, False)
    elif action is TransitionAction.CLOSE_SERVICE and b == (OperatingMode.SERVICE, False, False, False, True, False):
        expected = (OperatingMode.SERVICE, False, False, False, False, False)
    elif action is TransitionAction.EXIT_SERVICE and b == (OperatingMode.SERVICE, False, False, False, False, False):
        expected = (OperatingMode.IDLE, False, False, False, False, False)
    elif action is TransitionAction.LATCH_FAULT and before.mode is not OperatingMode.FAULT:
        expected = (OperatingMode.FAULT, False, before.retention_engaged, before.quick_release_open, before.service_access_open, True)
    elif action is TransitionAction.CLEAR_FAULT and b[0] is OperatingMode.FAULT and b[1] is False and b[5] is True:
        # Fault clear preserves mechanical positions. It cannot hide open service access.
        mode = OperatingMode.SERVICE if before.service_access_open else OperatingMode.IDLE
        expected = (mode, False, before.retention_engaged, before.quick_release_open, before.service_access_open, False)

    if expected is None:
        raise ValueError(f"action {action.value} is illegal from current state")
    if a != expected:
        raise ValueError(f"after state is not exact result of {action.value}")
