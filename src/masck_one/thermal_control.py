from __future__ import annotations

"""Deterministic firmware-facing arbitration for WARM and COOL commands.

This module owns command safety only. It does not define temperatures, power levels,
thermal capability, sensor performance, or hardware selection. COOL is permitted only
after recovery, matching the released CLEAN -> RECOVERY -> COOL_IF_COMMANDED sequence.
"""

from dataclasses import dataclass
from enum import Enum, auto


class ThermalControlError(ValueError):
    """Raised when a thermal-control input or output violates the command contract."""


class ThermalMode(Enum):
    OFF = auto()
    WARM = auto()
    COOL = auto()


@dataclass(frozen=True, slots=True)
class ThermalCommand:
    mode: ThermalMode
    warm_enable: bool
    cool_enable: bool
    inhibited: bool = False
    reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.mode, ThermalMode):
            raise ThermalControlError("mode must be a ThermalMode")
        for name, value in (
            ("warm_enable", self.warm_enable),
            ("cool_enable", self.cool_enable),
            ("inhibited", self.inhibited),
        ):
            if type(value) is not bool:
                raise ThermalControlError(f"{name} must be an exact bool")
        if self.reason is not None and not isinstance(self.reason, str):
            raise ThermalControlError("reason must be a string or None")

        expected_enables = {
            ThermalMode.OFF: (False, False),
            ThermalMode.WARM: (True, False),
            ThermalMode.COOL: (False, True),
        }
        if (self.warm_enable, self.cool_enable) != expected_enables[self.mode]:
            raise ThermalControlError(
                "mode and thermal output enables describe an impossible command"
            )
        if self.inhibited:
            if self.mode is not ThermalMode.OFF:
                raise ThermalControlError("an inhibited command must be OFF")
            if not self.reason:
                raise ThermalControlError("an inhibited command requires a reason")
        elif self.reason is not None:
            raise ThermalControlError("a non-inhibited command cannot carry a reason")


class ThermalCommandInterlock:
    """Fail-closed WARM/COOL command arbiter with explicit recovery gating."""

    def command(
        self,
        *,
        warm_requested: bool,
        cool_requested: bool,
        recovery_complete: bool,
    ) -> ThermalCommand:
        for name, value in (
            ("warm_requested", warm_requested),
            ("cool_requested", cool_requested),
            ("recovery_complete", recovery_complete),
        ):
            if type(value) is not bool:
                raise ThermalControlError(f"{name} must be an exact bool")

        if warm_requested and cool_requested:
            return ThermalCommand(
                ThermalMode.OFF,
                False,
                False,
                inhibited=True,
                reason="warm and cool requests are mutually exclusive",
            )
        if cool_requested and not recovery_complete:
            return ThermalCommand(
                ThermalMode.OFF,
                False,
                False,
                inhibited=True,
                reason="cool request requires completed recovery",
            )
        if warm_requested:
            return ThermalCommand(ThermalMode.WARM, True, False)
        if cool_requested:
            return ThermalCommand(ThermalMode.COOL, False, True)
        return ThermalCommand(ThermalMode.OFF, False, False)
