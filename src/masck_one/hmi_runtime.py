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


@dataclass(frozen=True, slots=True)
class InputEvent:
    stable_pressed: bool
    edge: Edge
    faulted: bool = False
    fault: str | None = None


class DebouncedInput:
    """Debounce one active-high input using caller-supplied monotonic time.

    No wall clock is read, making the behaviour deterministic in firmware simulation
    and unit tests. A stale stream faults rather than preserving a potentially unsafe
    held command. Once faulted, an explicit reset and debounced release are required
    before a new press can be accepted. Sample, arm and watchdog calls share one
    monotonic time contract so no path can silently move the runtime clock backwards.
    That clock contract survives fault reset, preventing recovery from accepting an
    older firmware timestamp as a new epoch. Valid timestamps that expose a timeout
    also advance the clock anchor before the fault is latched, so recovery cannot
    rewind behind the observation that caused the fault. The first fault cause remains
    latched until reset so later bad inputs cannot erase the diagnostic that caused the
    control to fail closed. Firmware may call ``arm`` at input-supervision startup so
    the no-sample timeout is measured from a known boot point rather than from the
    first later watchdog service. Repeated arm calls cannot postpone that deadline.
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
        """Clear a latched fault while preserving the monotonic clock contract.

        Recovery still requires a debounced release before another press. Preserving
        the latest observed time prevents reset from turning a caller clock regression
        into an apparently valid new timeline.
        """
        self._reset_state(require_release=True, preserve_clock=True)

    def _reset_state(self, *, require_release: bool, preserve_clock: bool) -> None:
        last_observed_at = getattr(self, "_last_observed_at", None) if preserve_clock else None
        self._stable = False
        self._candidate = False
        self._candidate_since: float | None = None
        self._last_sample_at: float | None = None
        self._last_observed_at: float | None = last_observed_at
        self._watchdog_started_at: float | None = None
        self._fault: str | None = None
        self._require_release = require_release

    @property
    def faulted(self) -> bool:
        return self._fault is not None

    def arm(self, *, now_s: float) -> InputEvent:
        """Start no-sample supervision from an explicit firmware lifecycle point.

        Arming is idempotent with respect to the startup deadline: servicing this API
        repeatedly cannot move the deadline forward. A first sample cancels startup
        supervision and transfers responsibility to normal stale-stream supervision.
        """
        if self._fault is not None:
            return InputEvent(False, Edge.NONE, True, self._fault)
        if type(now_s) not in (int, float) or not math.isfinite(float(now_s)):
            return self._trip("arm time must be finite")
        now = float(now_s)
        if self._last_observed_at is not None and now < self._last_observed_at:
            return self._trip("arm time moved backwards")
        self._last_observed_at = now
        if self._last_sample_at is not None:
            return InputEvent(self._stable, Edge.NONE)
        if self._watchdog_started_at is None:
            self._watchdog_started_at = now
        if now - self._watchdog_started_at > self.stale_after_s:
            return self._trip("input stream did not start")
        return InputEvent(False, Edge.NONE)

    def sample(self, *, pressed: bool, now_s: float) -> InputEvent:
        if self._fault is not None:
            return InputEvent(False, Edge.NONE, True, self._fault)
        if type(pressed) is not bool:
            return self._trip("pressed must be an exact bool")
        if type(now_s) not in (int, float) or not math.isfinite(float(now_s)):
            return self._trip("now_s must be finite")
        now = float(now_s)
        if self._last_observed_at is not None and now < self._last_observed_at:
            return self._trip("input time moved backwards")
        self._last_observed_at = now
        if self._last_sample_at is not None and now - self._last_sample_at > self.stale_after_s:
            return self._trip("input stream became stale")
        if self._last_sample_at is None and self._watchdog_started_at is not None:
            if now - self._watchdog_started_at > self.stale_after_s:
                return self._trip("input stream did not start")
        self._last_sample_at = now
        self._watchdog_started_at = None

        if self._require_release:
            if pressed:
                self._candidate_since = None
                return InputEvent(False, Edge.NONE)
            if self._candidate_since is None:
                self._candidate_since = now
                return InputEvent(False, Edge.NONE)
            if now - self._candidate_since < self.debounce_s:
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

        if now - self._candidate_since < self.debounce_s:
            return InputEvent(self._stable, Edge.NONE)

        self._stable = self._candidate
        self._candidate_since = None
        return InputEvent(self._stable, Edge.PRESSED if self._stable else Edge.RELEASED)

    def watchdog(self, *, now_s: float) -> InputEvent:
        """Fail closed when sampling stops or never starts, without synthesising an edge."""
        if self._fault is not None:
            return InputEvent(False, Edge.NONE, True, self._fault)
        if type(now_s) not in (int, float) or not math.isfinite(float(now_s)):
            return self._trip("watchdog time must be finite")
        now = float(now_s)
        if self._last_observed_at is not None and now < self._last_observed_at:
            return self._trip("watchdog time moved backwards")
        self._last_observed_at = now
        if self._last_sample_at is None:
            if self._watchdog_started_at is None:
                self._watchdog_started_at = now
                return InputEvent(False, Edge.NONE)
            if now - self._watchdog_started_at > self.stale_after_s:
                return self._trip("input stream did not start")
            return InputEvent(False, Edge.NONE)
        if now - self._last_sample_at > self.stale_after_s:
            return self._trip("input stream became stale")
        return InputEvent(self._stable, Edge.NONE)

    def _trip(self, reason: str) -> InputEvent:
        self._fault = reason
        self._stable = False
        self._candidate = False
        self._candidate_since = None
        self._require_release = True
        return InputEvent(False, Edge.NONE, True, reason)


def _positive_finite(value: object) -> bool:
    return type(value) in (int, float) and math.isfinite(float(value)) and float(value) > 0.0
