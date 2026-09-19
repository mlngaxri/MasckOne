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
    """Raised when an HMI sample violates the runtime contract."""


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

    No wall clock is read, making the behaviour deterministic in firmware simulation
    and unit tests. A stale stream faults rather than preserving a potentially unsafe
    held command. Once faulted, an explicit reset and debounced release are required
    before a new press can be accepted. Sample, arm and watchdog calls share one
    monotonic time contract so no path can silently move the runtime clock backwards.
    That clock contract survives fault reset, preventing recovery from accepting an
    older firmware timestamp as a new epoch. A fault reset also resumes no-sample
    supervision from the last trusted timestamp, so recovery cannot create an
    unbounded unsupervised interval before the next watchdog service. Valid timestamps
    that expose a timeout also advance the clock anchor before the fault is latched, so
    recovery cannot rewind behind the observation that caused the fault. The first
    fault cause remains latched until reset so later bad inputs cannot erase the
    diagnostic that caused the control to fail closed. Faults expose both a
    human-readable message and a stable ``FaultCode`` so firmware does not need to
    parse diagnostic prose. A reset request while healthy is deliberately a no-op so
    an unconditional firmware recovery call cannot erase a valid held state or
    debounce candidate. Firmware may call ``arm`` at input-supervision startup so the
    no-sample timeout is measured from a known boot point rather than from the first
    later watchdog service. Repeated arm calls cannot postpone that deadline. Timing
    gates compare absolute deadlines rather than subtracting floating timestamps,
    avoiding false one-sample delays at an exact debounce or stale-stream boundary.
    """

    def __init__(self, *, debounce_s: float = 0.030, stale_after_s: float = 0.250) -> None:
        if not _positive_finite(debounce_s):
            raise HmiInputError("debounce_s must be finite and positive")
        if not _positive_finite(stale_after_s) or stale_after_s <= debounce_s:
            raise HmiInputError("stale_after_s must be finite and greater than debounce_s")
        self.debounce_s = float(debounce_s)
        self.stale_after_s = float(stale_after_s)
        self._reset_state(require_release=False, preserve_clock=False)

    def reset(self) -> None:
        """Clear a latched fault while preserving clock and recovery supervision."""
        if self._fault is None:
            return
        self._reset_state(require_release=True, preserve_clock=True)

    def _reset_state(self, *, require_release: bool, preserve_clock: bool) -> None:
        last_observed_at = getattr(self, "_last_observed_at", None) if preserve_clock else None
        self._stable = False
        self._candidate = False
        self._candidate_since: float | None = None
        self._last_sample_at: float | None = None
        self._last_observed_at: float | None = last_observed_at
        # A fault reset is itself a recovery lifecycle transition. If a trusted clock
        # anchor exists, supervision resumes there rather than waiting for a future
        # watchdog call to start a fresh timeout window.
        self._watchdog_started_at: float | None = (
            last_observed_at if require_release and last_observed_at is not None else None
        )
        self._fault: str | None = None
        self._fault_code: FaultCode | None = None
        self._require_release = require_release

    @property
    def faulted(self) -> bool:
        return self._fault is not None

    def _fault_event(self) -> InputEvent:
        return InputEvent(False, Edge.NONE, True, self._fault, self._fault_code)

    def arm(self, *, now_s: float) -> InputEvent:
        """Start no-sample supervision from an explicit firmware lifecycle point."""
        if self._fault is not None:
            return self._fault_event()
        if type(now_s) not in (int, float) or not math.isfinite(float(now_s)):
            return self._trip(FaultCode.ARM_TIME_INVALID, "arm time must be finite")
        now = float(now_s)
        if self._last_observed_at is not None and now < self._last_observed_at:
            return self._trip(FaultCode.ARM_TIME_REGRESSION, "arm time moved backwards")
        self._last_observed_at = now
        if self._last_sample_at is not None:
            return InputEvent(self._stable, Edge.NONE)
        if self._watchdog_started_at is None:
            self._watchdog_started_at = now
        if now > self._watchdog_started_at + self.stale_after_s:
            return self._trip(FaultCode.INPUT_STREAM_NOT_STARTED, "input stream did not start")
        return InputEvent(False, Edge.NONE)

    def sample(self, *, pressed: bool, now_s: float) -> InputEvent:
        if self._fault is not None:
            return self._fault_event()
        if type(pressed) is not bool:
            return self._trip(FaultCode.PRESSED_NOT_BOOL, "pressed must be an exact bool")
        if type(now_s) not in (int, float) or not math.isfinite(float(now_s)):
            return self._trip(FaultCode.SAMPLE_TIME_INVALID, "now_s must be finite")
        now = float(now_s)
        if self._last_observed_at is not None and now < self._last_observed_at:
            return self._trip(FaultCode.SAMPLE_TIME_REGRESSION, "input time moved backwards")
        self._last_observed_at = now
        if self._last_sample_at is not None and now > self._last_sample_at + self.stale_after_s:
            return self._trip(FaultCode.INPUT_STREAM_STALE, "input stream became stale")
        if self._last_sample_at is None and self._watchdog_started_at is not None:
            if now > self._watchdog_started_at + self.stale_after_s:
                return self._trip(FaultCode.INPUT_STREAM_NOT_STARTED, "input stream did not start")
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
            return self._fault_event()
        if type(now_s) not in (int, float) or not math.isfinite(float(now_s)):
            return self._trip(FaultCode.WATCHDOG_TIME_INVALID, "watchdog time must be finite")
        now = float(now_s)
        if self._last_observed_at is not None and now < self._last_observed_at:
            return self._trip(FaultCode.WATCHDOG_TIME_REGRESSION, "watchdog time moved backwards")
        self._last_observed_at = now
        if self._last_sample_at is None:
            if self._watchdog_started_at is None:
                self._watchdog_started_at = now
                return InputEvent(False, Edge.NONE)
            if now > self._watchdog_started_at + self.stale_after_s:
                return self._trip(FaultCode.INPUT_STREAM_NOT_STARTED, "input stream did not start")
            return InputEvent(False, Edge.NONE)
        if now > self._last_sample_at + self.stale_after_s:
            return self._trip(FaultCode.INPUT_STREAM_STALE, "input stream became stale")
        return InputEvent(self._stable, Edge.NONE)

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
