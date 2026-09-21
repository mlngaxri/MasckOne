from __future__ import annotations

"""Deterministic firmware-facing HMI input conditioning.

This module deliberately does not assign product functions to physical controls. It
turns an electrical level into a debounced press/release event stream and fails closed
on stale, non-monotonic or malformed input so later firmware can bind functions only
when the HMI mapping is released.
"""

from dataclasses import dataclass
from enum import Enum, auto
import math


class HmiInputError(ValueError):
    """Raised when static HMI configuration violates the runtime contract."""


class Edge(Enum):
    NONE = auto()
    PRESSED = auto()
    RELEASED = auto()


class FaultCode(Enum):
    """Stable machine-readable causes for a latched fail-closed HMI state."""

    PRESSED_NOT_BOOL = auto()
    SAMPLE_TIME_INVALID = auto()
    SAMPLE_TIME_REGRESSION = auto()
    ARM_TIME_INVALID = auto()
    ARM_TIME_REGRESSION = auto()
    WATCHDOG_TIME_INVALID = auto()
    WATCHDOG_TIME_REGRESSION = auto()
    RESET_TIME_INVALID = auto()
    RESET_TIME_REGRESSION = auto()
    INPUT_STREAM_NOT_STARTED = auto()
    INPUT_STREAM_STALE = auto()


@dataclass(frozen=True, slots=True)
class InputEvent:
    stable_pressed: bool
    edge: Edge
    faulted: bool = False
    fault: str | None = None
    fault_code: FaultCode | None = None


class DebouncedInput:
    """Debounce one active-high input using caller-supplied monotonic time.

    No wall clock is read, making behaviour deterministic in firmware simulation and
    unit tests. A stale stream faults rather than preserving a potentially unsafe held
    command. Once faulted, an explicit reset and debounced release are required before
    a new press can be accepted. Sample, arm, watchdog and timed reset calls share one
    monotonic time contract so no path can silently move the runtime clock backwards.
    That clock contract survives fault reset. While a fault is latched, valid monotonic
    timestamps supplied to sample, arm, watchdog or reset continue to advance the shared
    clock floor without replacing the first fault. Invalid or regressing reset timestamps
    are runtime faults rather than exceptions, keeping the firmware-facing API fail-closed
    and event-observable. Firmware may pass ``now_s`` to ``reset`` so recovery no-sample
    supervision begins at the actual reset request rather than at an older observation.
    Reset returns the resulting ``InputEvent`` so a timed healthy reset cannot silently
    latch a supervision fault. A timed healthy reset preserves state only while the
    existing stream-supervision deadline remains valid; crossing that deadline latches
    the same fail-closed supervision fault as arm, sample or watchdog. Legacy untimed
    reset remains supported and starts its recovery window at the next arm, sample or
    watchdog observation. Valid sample timestamps are clock observations even when the
    electrical level is malformed. Established supervision deadlines are evaluated
    before a new electrical level is classified, so an already-expired stream retains
    chronological first-fault priority. The first fault cause remains latched until a
    valid reset. Timing gates compare absolute deadlines rather than subtracting floating
    timestamps.
    """

    def __init__(self, *, debounce_s: float = 0.030, stale_after_s: float = 0.250) -> None:
        if not _positive_finite(debounce_s):
            raise HmiInputError("debounce_s must be finite and positive")
        if not _positive_finite(stale_after_s) or stale_after_s <= debounce_s:
            raise HmiInputError("stale_after_s must be finite and greater than debounce_s")
        self.debounce_s = float(debounce_s)
        self.stale_after_s = float(stale_after_s)
        self._reset_state(require_release=False, preserve_clock=False)

    def reset(self, *, now_s: float | None = None) -> InputEvent:
        """Clear a latched fault only from a valid reset observation."""
        reset_at: float | None = None
        if now_s is not None:
            if type(now_s) not in (int, float) or not math.isfinite(float(now_s)):
                if self._fault is not None:
                    return self._fault_event()
                return self._trip(FaultCode.RESET_TIME_INVALID, "reset time must be finite")
            reset_at = float(now_s)
            if self._last_observed_at is not None and reset_at < self._last_observed_at:
                if self._fault is not None:
                    return self._fault_event()
                return self._trip(FaultCode.RESET_TIME_REGRESSION, "reset time moved backwards")
        if self._fault is None:
            if reset_at is not None:
                self._last_observed_at = reset_at
                fault = self._supervision_fault(reset_at)
                if fault is not None:
                    return fault
            return InputEvent(self._stable, Edge.NONE)
        self._reset_state(require_release=True, preserve_clock=True, recovery_started_at=reset_at)
        return InputEvent(False, Edge.NONE)

    def _reset_state(self, *, require_release: bool, preserve_clock: bool, recovery_started_at: float | None = None) -> None:
        last_observed_at = getattr(self, "_last_observed_at", None) if preserve_clock else None
        if recovery_started_at is not None:
            last_observed_at = recovery_started_at
        self._stable = False
        self._candidate = False
        self._candidate_since: float | None = None
        self._last_sample_at: float | None = None
        self._last_observed_at: float | None = last_observed_at
        self._watchdog_started_at: float | None = recovery_started_at
        self._fault: str | None = None
        self._fault_code: FaultCode | None = None
        self._require_release = require_release

    @property
    def faulted(self) -> bool:
        return self._fault is not None

    def _fault_event(self) -> InputEvent:
        return InputEvent(False, Edge.NONE, True, self._fault, self._fault_code)

    def _observe_time_while_faulted(self, now_s: object) -> None:
        """Advance the clock floor from a valid post-fault service observation."""
        if type(now_s) not in (int, float) or not math.isfinite(float(now_s)):
            return
        now = float(now_s)
        if self._last_observed_at is None or now >= self._last_observed_at:
            self._last_observed_at = now

    def _supervision_fault(self, now: float) -> InputEvent | None:
        """Apply the single authoritative sample-stream supervision contract."""
        if self._last_sample_at is not None:
            if now > self._last_sample_at + self.stale_after_s:
                return self._trip(FaultCode.INPUT_STREAM_STALE, "input stream became stale")
            return None
        if self._watchdog_started_at is not None:
            if now > self._watchdog_started_at + self.stale_after_s:
                return self._trip(FaultCode.INPUT_STREAM_NOT_STARTED, "input stream did not start")
        return None

    def arm(self, *, now_s: float) -> InputEvent:
        """Start no-sample supervision from an explicit firmware lifecycle point."""
        if self._fault is not None:
            self._observe_time_while_faulted(now_s)
            return self._fault_event()
        if type(now_s) not in (int, float) or not math.isfinite(float(now_s)):
            return self._trip(FaultCode.ARM_TIME_INVALID, "arm time must be finite")
        now = float(now_s)
        if self._last_observed_at is not None and now < self._last_observed_at:
            return self._trip(FaultCode.ARM_TIME_REGRESSION, "arm time moved backwards")
        self._last_observed_at = now
        fault = self._supervision_fault(now)
        if fault is not None:
            return fault
        if self._last_sample_at is not None:
            return InputEvent(self._stable, Edge.NONE)
        if self._watchdog_started_at is None:
            self._watchdog_started_at = now
        return InputEvent(False, Edge.NONE)

    def sample(self, *, pressed: bool, now_s: float) -> InputEvent:
        if self._fault is not None:
            self._observe_time_while_faulted(now_s)
            return self._fault_event()
        if type(now_s) not in (int, float) or not math.isfinite(float(now_s)):
            return self._trip(FaultCode.SAMPLE_TIME_INVALID, "now_s must be finite")
        now = float(now_s)
        if self._last_observed_at is not None and now < self._last_observed_at:
            return self._trip(FaultCode.SAMPLE_TIME_REGRESSION, "input time moved backwards")
        self._last_observed_at = now
        fault = self._supervision_fault(now)
        if fault is not None:
            return fault
        if type(pressed) is not bool:
            return self._trip(FaultCode.PRESSED_NOT_BOOL, "pressed must be an exact bool")
        self._last_sample_at = now
        self._watchdog_started_at = None

        if self._require_release:
            if pressed:
                self._candidate_since = None
                return InputEvent(False, Edge.NONE)
            if self._candidate_since is None:
                self._candidate_since = now
                return InputEvent(False, Edge.NONE)
            if now < self._candidate_since + self.debounce_s:
                return InputEvent(False, Edge.NONE)
            self._require_release = False
            self._candidate = False
            self._candidate_since = None
            return InputEvent(False, Edge.NONE)

        if pressed == self._stable:
            self._candidate = self._stable
            self._candidate_since = None
            return InputEvent(self._stable, Edge.NONE)
        if pressed != self._candidate or self._candidate_since is None:
            self._candidate = pressed
            self._candidate_since = now
            return InputEvent(self._stable, Edge.NONE)
        if now < self._candidate_since + self.debounce_s:
            return InputEvent(self._stable, Edge.NONE)
        self._stable = self._candidate
        self._candidate_since = None
        return InputEvent(self._stable, Edge.PRESSED if self._stable else Edge.RELEASED)

    def watchdog(self, *, now_s: float) -> InputEvent:
        """Fail closed when sampling stops or never starts, without synthesising an edge."""
        if self._fault is not None:
            self._observe_time_while_faulted(now_s)
            return self._fault_event()
        if type(now_s) not in (int, float) or not math.isfinite(float(now_s)):
            return self._trip(FaultCode.WATCHDOG_TIME_INVALID, "watchdog time must be finite")
        now = float(now_s)
        if self._last_observed_at is not None and now < self._last_observed_at:
            return self._trip(FaultCode.WATCHDOG_TIME_REGRESSION, "watchdog time moved backwards")
        self._last_observed_at = now
        if self._last_sample_at is None and self._watchdog_started_at is None:
            self._watchdog_started_at = now
            return InputEvent(False, Edge.NONE)
        fault = self._supervision_fault(now)
        if fault is not None:
            return fault
        return InputEvent(self._stable if self._last_sample_at is not None else False, Edge.NONE)

    def _trip(self, code: FaultCode, reason: str) -> InputEvent:
        self._fault = reason
        self._fault_code = code
        self._stable = False
        self._candidate = False
        self._candidate_since = None
        self._require_release = True
        return self._fault_event()


def _positive_finite(value: object) -> bool:
    return type(value) in (int, float) and math.isfinite(float(value)) and float(value) > 0.0
