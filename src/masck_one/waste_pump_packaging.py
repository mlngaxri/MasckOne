"""Compatibility facade for the reconciled Iteration 26 waste-pump architecture.

This module contains no independent Iteration 26 implementation. It preserves the
historical public names consumed by the already-released Iteration 27 cartridge code
while delegating all construction, validation, topology and evidence semantics to
``masck_one.waste_pump_architecture``.
"""
from __future__ import annotations

from .waste_pump_architecture import (
    INTERFACE_CARTRIDGE_INLET_I27,
    WastePumpArchitecture,
    WastePumpArchitectureError,
    build_waste_pump_architecture,
)


WastePumpPackagingArchitecture = WastePumpArchitecture
WastePumpPackagingError = WastePumpArchitectureError


def build_waste_pump_packaging_architecture(*args, **kwargs) -> WastePumpPackagingArchitecture:
    """Build the sole reconciled Iteration 26 architecture under the legacy API name."""

    return build_waste_pump_architecture(*args, **kwargs)


__all__ = (
    "INTERFACE_CARTRIDGE_INLET_I27",
    "WastePumpPackagingArchitecture",
    "WastePumpPackagingError",
    "build_waste_pump_packaging_architecture",
)
