from __future__ import annotations

"""Explicit post-recovery COOL heat-rejection path.

This module answers where rejected heat is permitted to go without selecting a TEC,
claiming an onboard heat sink, or inventing thermal performance. Geometry is limited
to the already-reserved dry dock interface from ``warm_cool_package``.
"""

from dataclasses import dataclass
import math

from .warm_cool_package import (
    COOL_STATUS,
    EVIDENCE_STATUS,
    SEQUENCE,
    WarmCoolPackageError,
    build_warm_cool_package,
)

SCHEMA = "MASCK_ONE_COOL_HEAT_REJECTION_PATH_V1"
PATH = (
    "TREATMENT_INTERFACE",
    "DEVICE_THERMAL_SPREADER",
    "DRY_DOCK_CONTACT_INTERFACE",
    "EXTERNAL_DOCK_THERMAL_SINK",
    "AMBIENT",
)


@dataclass(frozen=True, slots=True)
class CoolHeatRejectionPath:
    stages: tuple[str, ...] = PATH
    sequence: tuple[str, ...] = SEQUENCE
    cool_technology: None = None
    onboard_heat_sink_claimed: bool = False
    external_dock_sink_performance_validated: bool = False

    def __post_init__(self) -> None:
        if self.stages != PATH:
            raise WarmCoolPackageError("COOL heat-rejection path cannot bypass the dry dock interface")
        if self.sequence != SEQUENCE:
            raise WarmCoolPackageError("COOL heat rejection must remain after recovery")
        if self.cool_technology is not None:
            raise WarmCoolPackageError("COOL technology remains unfrozen")
        if self.onboard_heat_sink_claimed:
            raise WarmCoolPackageError("onboard heat sink cannot be claimed without evidence")
        if self.external_dock_sink_performance_validated:
            raise WarmCoolPackageError("external dock thermal performance has no physical validation")

    def manifest(self) -> dict[str, object]:
        package = build_warm_cool_package()
        dock = package.dock_heat_rejection_interface.manifest()
        return {
            "schema": SCHEMA,
            "cool_status": COOL_STATUS,
            "evidence_status": EVIDENCE_STATUS,
            "sequence": list(self.sequence),
            "heat_rejection_path": list(self.stages),
            "cool_technology": self.cool_technology,
            "onboard_heat_sink_claimed": self.onboard_heat_sink_claimed,
            "external_dock_sink_performance_validated": self.external_dock_sink_performance_validated,
            "dock_interface": dock,
            "reservation_status": "HISTORICAL_UNREALIZED_PATH; SEE_THERMAL_RESET_HARDWARE_FOR_CURRENT_OFF_FACE_CANDIDATE",
            "interpretation": "GEOMETRIC_PATH_ONLY_NOT_COOLING_CAPABILITY_CONDENSATION_OR_SKIN_SAFETY_EVIDENCE",
        }


def required_external_sink_energy_J(*, heat_to_reject_J: float, transfer_efficiency: float) -> float:
    """Legacy capacity-sizing allowance, NOT heat actually transferred.

    Dividing by a utilization factor enlarges the specified sink capacity. It
    does not create additional heat or close an energy balance. Physical reset
    energy and heat-flow rates are accounted separately in thermal_reset_physics.
    Kept for API compatibility with the reservation owner.
    """
    if type(heat_to_reject_J) not in (int, float) or not math.isfinite(float(heat_to_reject_J)):
        raise WarmCoolPackageError("heat_to_reject_J must be finite numeric evidence")
    if heat_to_reject_J <= 0:
        raise WarmCoolPackageError("heat_to_reject_J must be positive")
    if type(transfer_efficiency) not in (int, float) or not math.isfinite(float(transfer_efficiency)):
        raise WarmCoolPackageError("transfer_efficiency must be finite numeric evidence")
    if not 0 < transfer_efficiency <= 1:
        raise WarmCoolPackageError("transfer_efficiency must be in (0, 1]")
    return float(heat_to_reject_J) / float(transfer_efficiency)
