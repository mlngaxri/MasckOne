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
TRANSITION_CONTRACT = "MASCK_ONE_MECHANISM_TRANSITIONS_V2"


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


class ReadinessState(str, Enum):
    """Derived digital readiness vocabulary, never measured device readiness."""

    NOT_RETAINED = "NOT_RETAINED"
    READY_FOR_CYCLE = "READY_FOR_CYCLE"
    CYCLE_ACTIVE = "CYCLE_ACTIVE"
    RELEASE_OPEN = "RELEASE_OPEN"
    SERVICE = "SERVICE"
    FAULT_BLOCKED = "FAULT_BLOCKED"


class TransitionAction(str, Enum):
    ENGAGE_RETENTION = "ENGAGE_RETENTION"
    RELEASE_RETENTION = "RELEASE_RETENTION"
    MECHANICAL_QUICK_RELEASE = "MECHANICAL_QUICK_RELEASE"
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
        self.validate_invariants()

    def validate_invariants(self) -> None:
        """Revalidate the complete stored state before hashing or transition use."""

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
        if self.service_access_open and self.retention_engaged:
            raise ValueError("open service access cannot coexist with engaged retention")
        if self.service_access_open and self.quick_release_open:
            raise ValueError("open service access cannot coexist with open quick release")
        if self.cycle_active and not self.retention_engaged:
            raise ValueError("active cycle requires engaged retention")
        if self.cycle_active and (self.quick_release_open or self.service_access_open):
            raise ValueError("active cycle cannot coexist with release/service access")
        if self.service_access_open and self.mode not in (OperatingMode.SERVICE, OperatingMode.FAULT):
            raise ValueError("open service access requires SERVICE or FAULT mode")
        if self.mode is OperatingMode.SERVICE and self.retention_engaged:
            raise ValueError("SERVICE mode requires retention disengaged")
        if self.mode is OperatingMode.SERVICE and self.quick_release_open:
            raise ValueError("SERVICE mode requires quick release reset")
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
        self.validate_invariants()
        return "SIMULATED_DIGITAL_STATE_ONLY"

    @property
    def readiness(self) -> ReadinessState:
        """Return deterministic UI readiness without implying sensed hardware state."""

        self.validate_invariants()
        if self.mode is OperatingMode.FAULT:
            return ReadinessState.FAULT_BLOCKED
        if self.mode is OperatingMode.SERVICE or self.service_access_open:
            return ReadinessState.SERVICE
        if self.quick_release_open:
            return ReadinessState.RELEASE_OPEN
        if self.cycle_active:
            return ReadinessState.CYCLE_ACTIVE
        if self.retention_engaged:
            return ReadinessState.READY_FOR_CYCLE
        return ReadinessState.NOT_RETAINED

    @property
    def provenance_sha256(self) -> str:
        self.validate_invariants()
        payload = {
            "schema": "MASCK_ONE_MECHANISM_STATE_V3",
            "mode": self.mode.value,
            "cycle_active": self.cycle_active,
            "retention_engaged": self.retention_engaged,
            "quick_release_open": self.quick_release_open,
            "service_access_open": self.service_access_open,
            "fault_latched": self.fault_latched,
            "mechanism_provenance_sha256": self.mechanism_provenance_sha256,
            "evidence_state": self.evidence_state,
            "readiness": self.readiness.value,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("ascii")
        return hashlib.sha256(encoded).hexdigest()


def _copy_state(state: MechanismState) -> MechanismState:
    if type(state) is not MechanismState:
        raise TypeError("state must be exact MechanismState")
    state.validate_invariants()
    return MechanismState(
        mode=state.mode,
        cycle_active=state.cycle_active,
        retention_engaged=state.retention_engaged,
        quick_release_open=state.quick_release_open,
        service_access_open=state.service_access_open,
        fault_latched=state.fault_latched,
        mechanism_provenance_sha256=state.mechanism_provenance_sha256,
    )


def _fields(state: MechanismState) -> tuple[object, ...]:
    state.validate_invariants()
    return (
        state.mode, state.cycle_active, state.retention_engaged,
        state.quick_release_open, state.service_access_open, state.fault_latched,
    )


def derive_next_state(
    before: MechanismState,
    action: TransitionAction,
    *,
    current_mechanism_provenance_sha256: str,
) -> MechanismState:
    """Construct the only legal next simulated state for ``action``.

    The function encodes digital state semantics only. It does not assert actuator,
    retention, release, sensor or interlock timing, force, travel or physical success.
    ``MECHANICAL_QUICK_RELEASE`` represents observation/simulation of the independent
    unpowered release event. It is not a firmware command path.
    """

    if type(before) is not MechanismState:
        raise TypeError("before must be exact MechanismState")
    if type(action) is not TransitionAction:
        raise TypeError("action must be exact TransitionAction")
    before.validate_invariants()
    current = _require_sha256(
        "current_mechanism_provenance_sha256", current_mechanism_provenance_sha256
    )
    if before.mechanism_provenance_sha256 != current:
        raise ValueError("stale mechanism provenance")

    b = _fields(before)
    expected: tuple[object, ...] | None = None

    if action is TransitionAction.ENGAGE_RETENTION and b == (OperatingMode.IDLE, False, False, False, False, False):
        expected = (OperatingMode.IDLE, False, True, False, False, False)
    elif action is TransitionAction.RELEASE_RETENTION and b == (OperatingMode.IDLE, False, True, False, False, False):
        # Legacy normal doff event retained for compatibility.
        expected = (OperatingMode.IDLE, False, False, True, False, False)
    elif (
        action is TransitionAction.MECHANICAL_QUICK_RELEASE
        and before.retention_engaged
        and not before.quick_release_open
        and not before.service_access_open
    ):
        # A physical emergency release must not require STOP_CYCLE, fault clearing,
        # connectivity, firmware or power. The digital model immediately terminates
        # any active cycle while preserving an already-latched fault.
        fault = before.fault_latched
        mode = OperatingMode.FAULT if fault else OperatingMode.IDLE
        expected = (mode, False, False, True, False, fault)
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

    return MechanismState(
        mode=expected[0],
        cycle_active=expected[1],
        retention_engaged=expected[2],
        quick_release_open=expected[3],
        service_access_open=expected[4],
        fault_latched=expected[5],
        mechanism_provenance_sha256=current,
    )


def validate_transition(
    before: MechanismState,
    after: MechanismState,
    action: TransitionAction,
    *,
    current_mechanism_provenance_sha256: str,
) -> None:
    """Fail closed unless ``after`` is the exact legal result of ``action``."""

    if type(before) is not MechanismState or type(after) is not MechanismState:
        raise TypeError("before and after must be exact MechanismState")
    before.validate_invariants()
    after.validate_invariants()
    expected = derive_next_state(
        before,
        action,
        current_mechanism_provenance_sha256=current_mechanism_provenance_sha256,
    )
    if after.mechanism_provenance_sha256 != expected.mechanism_provenance_sha256:
        raise ValueError("stale mechanism provenance")
    if _fields(after) != _fields(expected):
        raise ValueError(f"after state is not exact result of {action.value}")


class SimulatedTransport:
    """Local deterministic state-event transport with explicitly no hardware telemetry.

    This object exists so Web/App prototypes can consume the exact product-state
    transition contract without inventing BLE connectivity, sensor observations or
    physical readiness. ``dispatch`` advances local simulated events only; it is not a
    hardware-command API. The transport stores a defensive state copy and returns
    defensive snapshots so caller mutation cannot alter internal state.
    """

    __slots__ = ("_current_mechanism_provenance_sha256", "_state", "_sequence")

    def __init__(
        self,
        initial_state: MechanismState,
        *,
        current_mechanism_provenance_sha256: str,
    ) -> None:
        current = _require_sha256(
            "current_mechanism_provenance_sha256", current_mechanism_provenance_sha256
        )
        initial = _copy_state(initial_state)
        if initial.mechanism_provenance_sha256 != current:
            raise ValueError("stale mechanism provenance")
        self._current_mechanism_provenance_sha256 = current
        self._state = initial
        self._sequence = 0
        self.validate_invariants()

    def validate_invariants(self) -> None:
        """Revalidate internal simulation-only state before any consumer-visible use."""

        current = _require_sha256(
            "current_mechanism_provenance_sha256", self._current_mechanism_provenance_sha256
        )
        if type(self._state) is not MechanismState:
            raise TypeError("internal state must be exact MechanismState")
        self._state.validate_invariants()
        if self._state.mechanism_provenance_sha256 != current:
            raise ValueError("stale mechanism provenance")
        if type(self._sequence) is not int:
            raise TypeError("simulation sequence must be exact int")
        if self._sequence < 0:
            raise ValueError("simulation sequence must be nonnegative")

    @property
    def transport_kind(self) -> str:
        return "SIMULATED_LOCAL_ONLY"

    @property
    def telemetry_source(self) -> str:
        return "NONE"

    @property
    def measured_hardware(self) -> bool:
        return False

    @property
    def dispatch_semantics(self) -> str:
        return "LOCAL_SIMULATED_STATE_EVENT_ONLY_NOT_HARDWARE_COMMAND"

    @property
    def sequence(self) -> int:
        self.validate_invariants()
        return self._sequence

    def snapshot(self) -> MechanismState:
        self.validate_invariants()
        return _copy_state(self._state)

    def dispatch(self, action: TransitionAction) -> MechanismState:
        if type(action) is not TransitionAction:
            raise TypeError("action must be exact TransitionAction")
        self.validate_invariants()
        next_state = derive_next_state(
            self._state,
            action,
            current_mechanism_provenance_sha256=self._current_mechanism_provenance_sha256,
        )
        self._state = next_state
        self._sequence += 1
        self.validate_invariants()
        return self.snapshot()

    @property
    def provenance_sha256(self) -> str:
        self.validate_invariants()
        payload = {
            "schema": "MASCK_ONE_SIMULATED_TRANSPORT_V2",
            "transition_contract": TRANSITION_CONTRACT,
            "transport_kind": self.transport_kind,
            "telemetry_source": self.telemetry_source,
            "measured_hardware": self.measured_hardware,
            "dispatch_semantics": self.dispatch_semantics,
            "sequence": self._sequence,
            "current_mechanism_provenance_sha256": self._current_mechanism_provenance_sha256,
            "state_provenance_sha256": self._state.provenance_sha256,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("ascii")
        return hashlib.sha256(encoded).hexdigest()

    def manifest(self) -> dict[str, object]:
        self.validate_invariants()
        snapshot = self.snapshot()
        return {
            "schema": "MASCK_ONE_SIMULATED_TRANSPORT_V2",
            "transition_contract": TRANSITION_CONTRACT,
            "transport_kind": self.transport_kind,
            "telemetry_source": self.telemetry_source,
            "measured_hardware": self.measured_hardware,
            "dispatch_semantics": self.dispatch_semantics,
            "sequence": self._sequence,
            "current_mechanism_provenance_sha256": self._current_mechanism_provenance_sha256,
            "state": {
                "mode": snapshot.mode.value,
                "cycle_active": snapshot.cycle_active,
                "retention_engaged": snapshot.retention_engaged,
                "quick_release_open": snapshot.quick_release_open,
                "service_access_open": snapshot.service_access_open,
                "fault_latched": snapshot.fault_latched,
                "readiness": snapshot.readiness.value,
                "evidence_state": snapshot.evidence_state,
                "provenance_sha256": snapshot.provenance_sha256,
            },
            "transport_provenance_sha256": self.provenance_sha256,
        }