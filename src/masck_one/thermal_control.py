from __future__ import annotations

"""Deterministic firmware-facing arbitration for WARM and COOL commands.

This module owns command safety only. It does not define temperatures, power levels,
thermal capability, sensor performance, or hardware selection. COOL is permitted only
after recovery, matching the released CLEAN -> RECOVERY -> COOL_IF_COMMANDED sequence.
"""

from dataclasses import dataclass
from enum import Enum
from typing import TypedDict


class ThermalControlError(ValueError):
    """Raised when a thermal-control input or output violates the command contract."""


class ThermalMode(str, Enum):
    """Stable machine-readable thermal output modes."""

    OFF = "off"
    WARM = "warm"
    COOL = "cool"


class ThermalInhibitReason(str, Enum):
    """Stable machine-readable reasons for a fail-closed thermal command."""

    CONFLICTING_REQUESTS = "conflicting_requests"
    RECOVERY_INCOMPLETE = "recovery_incomplete"


class ThermalCommandWire(TypedDict):
    """Closed firmware-facing representation of a validated thermal command."""

    mode: str
    warm_enable: bool
    cool_enable: bool
    inhibited: bool
    reason: str | None


@dataclass(frozen=True, slots=True)
class ThermalCommand:
    mode: ThermalMode
    warm_enable: bool
    cool_enable: bool
    inhibited: bool = False
    reason: ThermalInhibitReason | None = None

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
        if self.reason is not None and not isinstance(self.reason, ThermalInhibitReason):
            raise ThermalControlError("reason must be a ThermalInhibitReason or None")

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
            if self.reason is None:
                raise ThermalControlError("an inhibited command requires a reason")
        elif self.reason is not None:
            raise ThermalControlError("a non-inhibited command cannot carry a reason")

    def to_wire(self) -> ThermalCommandWire:
        """Serialize only validated, stable primitive values for firmware transport."""

        return {
            "mode": self.mode.value,
            "warm_enable": self.warm_enable,
            "cool_enable": self.cool_enable,
            "inhibited": self.inhibited,
            "reason": self.reason.value if self.reason is not None else None,
        }

    @classmethod
    def from_wire(cls, payload: object) -> ThermalCommand:
        """Decode an exact wire payload and reject malformed or impossible commands."""

        if type(payload) is not dict:
            raise ThermalControlError("thermal wire payload must be an exact dict")
        required = {"mode", "warm_enable", "cool_enable", "inhibited", "reason"}
        keys = set(payload)
        if keys != required:
            missing = sorted(required - keys)
            extra = sorted(keys - required)
            raise ThermalControlError(
                f"thermal wire payload fields mismatch: missing={missing}, extra={extra}"
            )

        mode_value = payload["mode"]
        if type(mode_value) is not str:
            raise ThermalControlError("wire mode must be an exact str")
        try:
            mode = ThermalMode(mode_value)
        except ValueError as exc:
            raise ThermalControlError("wire mode is not a recognized ThermalMode") from exc

        for name in ("warm_enable", "cool_enable", "inhibited"):
            if type(payload[name]) is not bool:
                raise ThermalControlError(f"wire {name} must be an exact bool")

        reason_value = payload["reason"]
        if reason_value is None:
            reason = None
        else:
            if type(reason_value) is not str:
                raise ThermalControlError("wire reason must be an exact str or None")
            try:
                reason = ThermalInhibitReason(reason_value)
            except ValueError as exc:
                raise ThermalControlError(
                    "wire reason is not a recognized ThermalInhibitReason"
                ) from exc

        return cls(
            mode=mode,
            warm_enable=payload["warm_enable"],
            cool_enable=payload["cool_enable"],
            inhibited=payload["inhibited"],
            reason=reason,
        )


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
                reason=ThermalInhibitReason.CONFLICTING_REQUESTS,
            )
        if cool_requested and not recovery_complete:
            return ThermalCommand(
                ThermalMode.OFF,
                False,
                False,
                inhibited=True,
                reason=ThermalInhibitReason.RECOVERY_INCOMPLETE,
            )
        if warm_requested:
            return ThermalCommand(ThermalMode.WARM, True, False)
        if cool_requested:
            return ThermalCommand(ThermalMode.COOL, False, True)
        return ThermalCommand(ThermalMode.OFF, False, False)
