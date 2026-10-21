"""Composition-agnostic recovery bounds for clean-cycle fluid components.

These bounds use only volume conservation and the configured aggregate recovery
floor. They deliberately do not assume perfect mixing, preferential recovery, or
measured component-specific recovery performance. Because recovery is specified
as a floor, not an exact recovered volume, the upper recovered bound permits the
entire component to be recovered and the lower nonrecovered bound is zero.
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
        if not math.isfinite(total_mL) or not math.isfinite(recovery_floor_mL) or total_mL < 0.0:
            raise WasteFluidAccountingError("aggregate recovery inputs must be finite and nonnegative")
        if recovery_floor_mL < 0.0 or recovery_floor_mL > total_mL + _TOL:
            raise WasteFluidAccountingError("aggregate recovery floor must lie within introduced volume")
        if self.introduced_mL > total_mL + _TOL:
            raise WasteFluidAccountingError("component introduced volume cannot exceed aggregate introduced volume")

        noncomponent = total_mL - self.introduced_mL
        maximum_nonrecovery = total_mL - recovery_floor_mL
        expected_min_recovered = max(0.0, recovery_floor_mL - noncomponent)
        # The aggregate contract is recovery >= floor. It does not pin recovery
        # exactly at the floor, so any component can in principle be fully recovered.
        expected_max_recovered = self.introduced_mL
        expected_min_nonrecovered = 0.0
        expected_max_nonrecovered = min(self.introduced_mL, maximum_nonrecovery)
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


def _bound(name: str, volume: float, total: float, recovery_floor: float) -> ComponentRecoveryBound:
    noncomponent = total - volume
    maximum_nonrecovery = total - recovery_floor
    return ComponentRecoveryBound(
        component=name,
        introduced_mL=volume,
        minimum_recovered_mL=max(0.0, recovery_floor - noncomponent),
        maximum_recovered_mL=volume,
        minimum_nonrecovered_mL=0.0,
        maximum_nonrecovered_mL=min(volume, maximum_nonrecovery),
    )


def reduce_component_recovery_bounds(
    ledger: CleanCycleDeliveryRecoveryLedger | None = None,
) -> DeliveryComponentRecoveryEnvelope:
    """Return tight component intervals implied by an aggregate recovery floor."""
    ledger = ledger or build_authority_delivery_recovery_ledger()
    if type(ledger) is not CleanCycleDeliveryRecoveryLedger:
        raise WasteFluidAccountingError("component recovery envelope requires exact delivery ledger source")
    ledger.__post_init__()
    total = ledger.service_nominal_mL
    recovery_floor = ledger.minimum_service_recovery_mL
    components = (
        _bound("face_water", ledger.service_face_water_mL, total, recovery_floor),
        _bound("cleanser", ledger.service_cleanser_mL, total, recovery_floor),
        _bound("post_flush_water", ledger.service_post_flush_water_mL, total, recovery_floor),
    )
    return DeliveryComponentRecoveryEnvelope(source_ledger=ledger, components=components)
