"""Deterministic digital mechanism state contract.

This module describes logically possible product/mechanism states for simulation and
digital consumers. It is not measured hardware telemetry and makes no physical
performance claim.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json


class OperatingMode(str, Enum):
    IDLE = "IDLE"
    CLEAN = "CLEAN"
    WARM = "WARM"
    SERVICE = "SERVICE"
    FAULT = "FAULT"


@dataclass(frozen=True)
class MechanismState:
    """One immutable, fail-closed mechanism state for simulated consumers."""

    mode: OperatingMode
    cycle_active: bool
    retention_engaged: bool
    quick_release_open: bool
    service_access_open: bool
    fault_latched: bool

    def __post_init__(self) -> None:
        if type(self.mode) is not OperatingMode:
            raise TypeError("mode must be exact OperatingMode")
        for name in (
            "cycle_active", "retention_engaged", "quick_release_open",
            "service_access_open", "fault_latched",
        ):
            if type(getattr(self, name)) is not bool:
                raise TypeError(f"{name} must be exact bool")

        if self.quick_release_open and self.retention_engaged:
            raise ValueError("quick release open cannot coexist with engaged retention")
        if self.cycle_active and not self.retention_engaged:
            raise ValueError("active cycle requires engaged retention")
        if self.cycle_active and self.quick_release_open:
            raise ValueError("active cycle cannot coexist with open quick release")
        if self.cycle_active and self.service_access_open:
            raise ValueError("active cycle cannot coexist with open service access")
        if self.service_access_open and self.mode is not OperatingMode.SERVICE:
            raise ValueError("open service access requires SERVICE mode")
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
            "schema": "MASCK_ONE_MECHANISM_STATE_V1",
            "mode": self.mode.value,
            "cycle_active": self.cycle_active,
            "retention_engaged": self.retention_engaged,
            "quick_release_open": self.quick_release_open,
            "service_access_open": self.service_access_open,
            "fault_latched": self.fault_latched,
            "evidence_state": self.evidence_state,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("ascii")).hexdigest()
