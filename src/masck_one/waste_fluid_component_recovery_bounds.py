"""Composition-agnostic recovery bounds for clean-cycle fluid components.

These bounds use only volume conservation and the configured aggregate recovery
floor. They deliberately do not assume perfect mixing, preferential recovery, or
measured component-specific recovery performance.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

from .waste_fluid_accounting import WasteFluidAccountingError
from .waste_fluid_delivery_recovery import (
    CleanCycleDeliveryRecoveryLedger,
    build_authority_delivery_recovery_ledger,
)

_TOL = 1e-12


@dataclass(frozen=True, slots=True)
class ComponentRecoveryBound:
    component: str
    introduced_mL: float
    minimum_recovered_mL: float
    maximum_recovered_mL: float
    minimum_nonrecovered_mL: float
    maximum_nonrecovered_mL: float

    def validate(self, *, total_mL: float, recovery_floor_mL: float) -> None:
        values = (
            self.introduced_mL, self.minimum_recovered_mL, self.maximum_recovered_mL,
            self.minimum_nonrecovered_mL, self.maximum_nonrecovered_mL,
        )
        if not self.component or any(not math.isfinite(v) or v < 0.0 for v in values):
            raise WasteFluidAccountingError("component recovery bounds must be named, finite and nonnegative")
        noncomponent = total_mL - self.introduced_mL
        expected_min_recovered = max(0.0, recovery_floor_mL - noncomponent)
        expected_max_recovered = min(self.introduced_mL, recovery_floor_mL)
        expected_min_nonrecovered = max(0.0, self.introduced_mL - recovery_floor_mL)
        expected_max_nonrecovered = min(self.introduced_mL, total_mL - recovery_floor_mL)
        checks = (
            (self.minimum_recovered_mL, expected_min_recovered),
            (self.maximum_recovered_mL, expected_max_recovered),
            (self.minimum_nonrecovered_mL, expected_min_nonrecovered),
            (self.maximum_nonrecovered_mL, expected_max_nonrecovered),
        )
        if any(not math.isclose(a, b, rel_tol=0.0, abs_tol=_TOL) for a, b in checks):
            raise WasteFluidAccountingError("component recovery bound does not reconcile with aggregate conservation")
        if self.minimum_recovered_mL > self.maximum_recovered_mL + _TOL:
            raise WasteFluidAccountingError("component recovered interval is inverted")
        if self.minimum_nonrecovered_mL > self.maximum_nonrecovered_mL + _TOL:
            raise WasteFluidAccountingError("component nonrecovered interval is inverted")


@dataclass(frozen=True, slots=True)
class DeliveryComponentRecoveryEnvelope:
    source_ledger: CleanCycleDeliveryRecoveryLedger
    components: tuple[ComponentRecoveryBound, ...]

    def __post_init__(self) -> None:
        if type(self.source_ledger) is not CleanCycleDeliveryRecoveryLedger:
            raise WasteFluidAccountingError("component recovery envelope requires exact delivery ledger source")
        self.source_ledger.__post_init__()
        expected_names = ("face_water", "cleanser", "post_flush_water")
        if tuple(item.component for item in self.components) != expected_names:
            raise WasteFluidAccountingError("component recovery envelope requires canonical clean-cycle components")
        expected_volumes = (
            self.source_ledger.service_face_water_mL,
            self.source_ledger.service_cleanser_mL,
            self.source_ledger.service_post_flush_water_mL,
        )
        for item, volume in zip(self.components, expected_volumes):
            if not math.isclose(item.introduced_mL, volume, rel_tol=0.0, abs_tol=_TOL):
                raise WasteFluidAccountingError("component recovery envelope disagrees with delivery ledger")
            item.validate(
                total_mL=self.source_ledger.service_nominal_mL,
                recovery_floor_mL=self.source_ledger.minimum_service_recovery_mL,
            )


def _bound(name: str, volume: float, total: float, recovered: float) -> ComponentRecoveryBound:
    noncomponent = total - volume
    return ComponentRecoveryBound(
        component=name,
        introduced_mL=volume,
        minimum_recovered_mL=max(0.0, recovered - noncomponent),
        maximum_recovered_mL=min(volume, recovered),
        minimum_nonrecovered_mL=max(0.0, volume - recovered),
        maximum_nonrecovered_mL=min(volume, total - recovered),
    )


def reduce_component_recovery_bounds(
    ledger: CleanCycleDeliveryRecoveryLedger | None = None,
) -> DeliveryComponentRecoveryEnvelope:
    """Return tight component intervals implied by aggregate recovery alone."""
    ledger = ledger or build_authority_delivery_recovery_ledger()
    if type(ledger) is not CleanCycleDeliveryRecoveryLedger:
        raise WasteFluidAccountingError("component recovery envelope requires exact delivery ledger source")
    ledger.__post_init__()
    total = ledger.service_nominal_mL
    recovered = ledger.minimum_service_recovery_mL
    components = (
        _bound("face_water", ledger.service_face_water_mL, total, recovered),
        _bound("cleanser", ledger.service_cleanser_mL, total, recovered),
        _bound("post_flush_water", ledger.service_post_flush_water_mL, total, recovered),
    )
    return DeliveryComponentRecoveryEnvelope(source_ledger=ledger, components=components)
