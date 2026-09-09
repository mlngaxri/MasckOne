from __future__ import annotations

"""WARM package and COOL heat-rejection decision state for Masck One.

This module deliberately does not freeze skin-safe temperatures, heater capability,
supplier ratings, ingress performance, or COOL technology. It provides deterministic
Fusion-ready package solids, an explicit dock heat-rejection interface, and an
input-driven thermal ledger whose numeric inputs must come from separately sourced
physical evidence.
"""

from dataclasses import dataclass
from hashlib import sha1
import math
from pathlib import Path

import cadquery as cq

from .authority import Authority, load_authority

SCHEMA = "MASCK_ONE_WARM_COOL_PACKAGE_V1"
SOURCE_MAIN_SHA = "42fa11818184cde998c6df25d7c46d4fb0e4c3eb"
AUTHORITY_REVISION = "2026-08-30-R1"
AUTHORITY_BLOB_SHA = "2608dda483b995539de422290371c219668a1527"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"

EVIDENCE_STATUS = (
    "DIGITAL_PACKAGE_ONLY_NOT_THERMAL_SKIN_SAFETY_RUNTIME_CONDENSATION_"
    "INGRESS_DURABILITY_OR_SUPPLIER_VALIDATION"
)
WARM_PACKAGE_STATUS = "PROVISIONAL_PACKAGE_GEOMETRY_REQUIRES_PHYSICAL_THERMAL_VALIDATION"
COOL_STATUS = "POST_RECOVERY_HEAT_REJECTION_ARCHITECTURE_TECHNOLOGY_NOT_FROZEN"
SEQUENCE = ("CLEAN", "RECOVERY", "COOL_IF_COMMANDED")

# Dimensional donor values from legacy Cell 14 are retained only as package seeds.
# They are not capability, safety, or supplier claims.
WARM_SIZE_MM = (22.0, 28.0, 2.4)
WARM_LEFT_CENTER_MM = (-52.0, -4.0, -4.0)
WARM_RIGHT_CENTER_MM = (52.0, -4.0, -4.0)
DOCK_INTERFACE_SIZE_MM = (30.0, 18.0, 3.0)
DOCK_INTERFACE_CENTER_MM = (0.0, 79.0, -10.0)

_REPO_ROOT = Path(__file__).resolve().parents[2]


class WarmCoolPackageError(ValueError):
    pass


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def _require_release_authority(authority: Authority) -> None:
    if type(authority) is not Authority:
        raise WarmCoolPackageError("exact Authority type required")
    canonical = load_authority()
    if authority.data != canonical.data:
        raise WarmCoolPackageError("supplied authority differs from released authority")
    if str(authority.get("project", "authority_revision")) != AUTHORITY_REVISION:
        raise WarmCoolPackageError("authority revision moved")
    actual = _git_blob_sha(_REPO_ROOT / "config/masck_one_authority.yaml")
    if actual != AUTHORITY_BLOB_SHA:
        raise WarmCoolPackageError(f"authority blob moved: {actual}")


def _box(center: tuple[float, float, float], size: tuple[float, float, float]) -> cq.Workplane:
    if len(center) != 3 or len(size) != 3 or any(v <= 0 for v in size):
        raise WarmCoolPackageError("invalid package dimensions")
    solid = cq.Workplane("XY").box(*size, centered=(True, True, True)).translate(center)
    shape = solid.val()
    if not shape.isValid() or len(shape.Solids()) != 1 or shape.Volume() <= 0:
        raise WarmCoolPackageError("package must be one valid positive-volume solid")
    return solid


@dataclass(frozen=True, slots=True)
class PackageReservation:
    package_id: str
    role: str
    center_xyz_mm: tuple[float, float, float]
    size_xyz_mm: tuple[float, float, float]
    hygiene_class: str = "SEALED_NONUSER"
    geometry_status: str = WARM_PACKAGE_STATUS
    evidence_status: str = EVIDENCE_STATUS

    @property
    def solid(self) -> cq.Workplane:
        return _box(self.center_xyz_mm, self.size_xyz_mm)

    def manifest(self) -> dict[str, object]:
        bb = self.solid.val().BoundingBox()
        return {
            "package_id": self.package_id,
            "role": self.role,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "center_xyz_mm": list(self.center_xyz_mm),
            "size_xyz_mm": list(self.size_xyz_mm),
            "hygiene_class": self.hygiene_class,
            "geometry_status": self.geometry_status,
            "evidence_status": self.evidence_status,
            "bbox_min_mm": [bb.xmin, bb.ymin, bb.zmin],
            "bbox_max_mm": [bb.xmax, bb.ymax, bb.zmax],
            "volume_mm3": float(self.solid.val().Volume()),
        }


@dataclass(frozen=True, slots=True)
class ThermalEvidenceInputs:
    heater_electrical_power_W: float
    heater_to_spreader_efficiency: float
    heated_effective_mass_kg: float
    heated_effective_specific_heat_J_kgK: float
    conductive_loss_W: float
    convective_radiative_loss_W: float
    duration_s: float

    def __post_init__(self) -> None:
        vals = (
            self.heater_electrical_power_W,
            self.heater_to_spreader_efficiency,
            self.heated_effective_mass_kg,
            self.heated_effective_specific_heat_J_kgK,
            self.conductive_loss_W,
            self.convective_radiative_loss_W,
            self.duration_s,
        )
        if not all(type(v) in (int, float) and math.isfinite(float(v)) for v in vals):
            raise WarmCoolPackageError("thermal inputs must be finite numeric evidence")
        if self.heater_electrical_power_W <= 0 or self.heated_effective_mass_kg <= 0:
            raise WarmCoolPackageError("power and effective mass must be positive")
        if self.heated_effective_specific_heat_J_kgK <= 0 or self.duration_s <= 0:
            raise WarmCoolPackageError("specific heat and duration must be positive")
        if not 0 < self.heater_to_spreader_efficiency <= 1:
            raise WarmCoolPackageError("efficiency must be in (0, 1]")
        if self.conductive_loss_W < 0 or self.convective_radiative_loss_W < 0:
            raise WarmCoolPackageError("loss terms cannot be negative")

    def ledger(self) -> dict[str, float | str]:
        delivered_W = self.heater_electrical_power_W * self.heater_to_spreader_efficiency
        losses_W = self.conductive_loss_W + self.convective_radiative_loss_W
        net_W = delivered_W - losses_W
        heat_capacity_J_K = self.heated_effective_mass_kg * self.heated_effective_specific_heat_J_kgK
        delta_K = net_W * self.duration_s / heat_capacity_J_K
        return {
            "delivered_to_spreader_W": delivered_W,
            "modeled_losses_W": losses_W,
            "net_heating_W": net_W,
            "effective_heat_capacity_J_K": heat_capacity_J_K,
            "modeled_delta_temperature_K": delta_K,
            "interpretation": "ENERGY_LEDGER_ONLY_NOT_SKIN_TEMPERATURE_OR_SAFETY_PREDICTION",
        }


@dataclass(frozen=True, slots=True)
class WarmCoolPackage:
    warm_left: PackageReservation
    warm_right: PackageReservation
    dock_heat_rejection_interface: PackageReservation
    warm_stack_elements: tuple[str, ...]
    cool_sequence: tuple[str, ...]
    cool_technology: None
    onboard_heat_sink_claimed: bool
    evidence_status: str = EVIDENCE_STATUS

    def __post_init__(self) -> None:
        if self.warm_stack_elements != ("HEATER", "TEMPERATURE_SENSOR", "SPREADER", "INSULATION"):
            raise WarmCoolPackageError("WARM stack must preserve heater/sensor/spreader/insulation roles")
        if self.cool_sequence != SEQUENCE:
            raise WarmCoolPackageError("COOL must remain sequenced after recovery")
        if self.cool_technology is not None:
            raise WarmCoolPackageError("COOL technology is not frozen")
        if self.onboard_heat_sink_claimed:
            raise WarmCoolPackageError("onboard heat rejection cannot be claimed without evidence")

    def manifest(self) -> dict[str, object]:
        return {
            "schema": SCHEMA,
            "source_main_sha": SOURCE_MAIN_SHA,
            "authority_revision": AUTHORITY_REVISION,
            "warm_status": WARM_PACKAGE_STATUS,
            "cool_status": COOL_STATUS,
            "evidence_status": self.evidence_status,
            "warm_stack_elements": list(self.warm_stack_elements),
            "cool_sequence": list(self.cool_sequence),
            "cool_technology": self.cool_technology,
            "onboard_heat_sink_claimed": self.onboard_heat_sink_claimed,
            "warm_left": self.warm_left.manifest(),
            "warm_right": self.warm_right.manifest(),
            "dock_heat_rejection_interface": self.dock_heat_rejection_interface.manifest(),
        }


def build_warm_cool_package(authority: Authority | None = None) -> WarmCoolPackage:
    authority = load_authority() if authority is None else authority
    _require_release_authority(authority)
    return WarmCoolPackage(
        warm_left=PackageReservation(
            "WARM-LEFT-PACKAGE",
            "sealed heater/sensor/spreader/insulation package reservation",
            WARM_LEFT_CENTER_MM,
            WARM_SIZE_MM,
        ),
        warm_right=PackageReservation(
            "WARM-RIGHT-PACKAGE",
            "sealed heater/sensor/spreader/insulation package reservation",
            WARM_RIGHT_CENTER_MM,
            WARM_SIZE_MM,
        ),
        dock_heat_rejection_interface=PackageReservation(
            "COOL-DOCK-HEAT-REJECTION-INTERFACE",
            "external dock heat-rejection contact/interface reservation",
            DOCK_INTERFACE_CENTER_MM,
            DOCK_INTERFACE_SIZE_MM,
            hygiene_class="DRY_ALWAYS",
            geometry_status="PROVISIONAL_DOCK_INTERFACE_GEOMETRY",
        ),
        warm_stack_elements=("HEATER", "TEMPERATURE_SENSOR", "SPREADER", "INSULATION"),
        cool_sequence=SEQUENCE,
        cool_technology=None,
        onboard_heat_sink_claimed=False,
    )
