from __future__ import annotations

"""Exact-head integration wrapper for the Manual B power/electronics package.

The underlying package owns Manual-B CAD. This wrapper binds that geometry to the
current stacked Manual-A head and adds checks introduced by later Manual-A mechanism
work, notably the fixed quick-release guard. It is the release-facing entry point for
Prompt 3 and supersedes the earlier authored-source label embedded in V1.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math

import cadquery as cq

from .authority import Authority, load_authority
from .electronics_package import ElectronicsPackage, PackagePart, HarnessRoute, PhysicalControl, build_electronics_package
from .mechanical_integration import MechanicalRealization, build_mechanical_realization

SCHEMA = "MASCK_ONE_MANUAL_B_POWER_ELECTRONICS_INTEGRATION_V2"
CURRENT_MANUAL_A_HEAD_SHA = "4ac8e04cd73e7cc496a381edffd29ca18cf8daf5"
CURRENT_MAIN_SHA = "b2c2d2d94972e4615e281e86e2feddaaa3c4e0c8"
DIGITAL_ONLY = "EXACT_HEAD_DIGITAL_PACKAGE_INTEGRATION_NOT_PHYSICAL_VALIDATION"


class PowerElectronicsIntegrationError(ValueError):
    pass


def _text(value: object, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise PowerElectronicsIntegrationError(f"{label} must be exact nonblank text")
    return value


def _intersection(first: cq.Workplane, second: cq.Workplane) -> float:
    value = float(first.val().intersect(second.val()).Volume())
    if not math.isfinite(value) or value < 0.0:
        raise PowerElectronicsIntegrationError("intersection volume must be finite and non-negative")
    return 0.0 if value < 1e-9 else value


def _mechanical_part(realization: MechanicalRealization, part_id: str) -> cq.Workplane:
    matches = tuple(part.solid for part in realization.realized_parts if part.part_id == part_id)
    if len(matches) != 1:
        raise PowerElectronicsIntegrationError(f"expected exactly one Manual A part {part_id}")
    return matches[0]


def _mechanical_sweep(realization: MechanicalRealization, sweep_id: str):
    matches = tuple(sweep for sweep in realization.service_sweeps if sweep.sweep_id == sweep_id)
    if len(matches) != 1:
        raise PowerElectronicsIntegrationError(f"expected exactly one Manual A sweep {sweep_id}")
    return matches[0]


@dataclass(frozen=True, slots=True)
class ExactHeadClearance:
    check_id: str
    moving_or_package_id: str
    obstacle_id: str
    state_id: str
    intersection_volume_mm3: float
    status: str

    def __post_init__(self) -> None:
        for label, value in (
            ("check_id", self.check_id),
            ("moving_or_package_id", self.moving_or_package_id),
            ("obstacle_id", self.obstacle_id),
            ("state_id", self.state_id),
            ("status", self.status),
        ):
            _text(value, label)
        if type(self.intersection_volume_mm3) not in (int, float) or not math.isfinite(float(self.intersection_volume_mm3)) or float(self.intersection_volume_mm3) < 0.0:
            raise PowerElectronicsIntegrationError("intersection volume must be finite and non-negative")

    @property
    def passes(self) -> bool:
        return float(self.intersection_volume_mm3) == 0.0

    def manifest(self) -> dict[str, object]:
        return {
            "check_id": self.check_id,
            "moving_or_package_id": self.moving_or_package_id,
            "obstacle_id": self.obstacle_id,
            "state_id": self.state_id,
            "intersection_volume_mm3": float(self.intersection_volume_mm3),
            "status": self.status,
            "passes": self.passes,
        }


@dataclass(frozen=True, slots=True)
class ShellIntegrationRecord:
    item_id: str
    shell_intersection_volume_mm3: float
    relationship: str
    status: str

    def __post_init__(self) -> None:
        _text(self.item_id, "item_id")
        _text(self.relationship, "relationship")
        _text(self.status, "status")
        if type(self.shell_intersection_volume_mm3) not in (int, float) or not math.isfinite(float(self.shell_intersection_volume_mm3)) or float(self.shell_intersection_volume_mm3) < 0.0:
            raise PowerElectronicsIntegrationError("shell intersection must be finite and non-negative")

    def manifest(self) -> dict[str, object]:
        return {
            "item_id": self.item_id,
            "shell_intersection_volume_mm3": float(self.shell_intersection_volume_mm3),
            "relationship": self.relationship,
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class PowerElectronicsIntegration:
    authority_revision: str
    current_main_sha: str
    current_manual_a_head_sha: str
    manual_a_realization_sha256: str
    base_package: ElectronicsPackage
    exact_head_clearances: tuple[ExactHeadClearance, ...]
    shell_integration_records: tuple[ShellIntegrationRecord, ...]
    remaining_cross_lane_blockers: tuple[str, ...]
    physical_validation_eligible: bool
    evidence_status: str

    def __post_init__(self) -> None:
        _text(self.authority_revision, "authority_revision")
        if self.current_main_sha != CURRENT_MAIN_SHA:
            raise PowerElectronicsIntegrationError("main source identity is stale")
        if self.current_manual_a_head_sha != CURRENT_MANUAL_A_HEAD_SHA:
            raise PowerElectronicsIntegrationError("Manual A source identity is stale")
        if type(self.manual_a_realization_sha256) is not str or len(self.manual_a_realization_sha256) != 64 or any(ch not in "0123456789abcdef" for ch in self.manual_a_realization_sha256):
            raise PowerElectronicsIntegrationError("Manual A realization digest must be canonical SHA-256")
        if type(self.base_package) is not ElectronicsPackage:
            raise TypeError("base_package must be exact ElectronicsPackage")
        if not self.exact_head_clearances or any(type(item) is not ExactHeadClearance for item in self.exact_head_clearances):
            raise PowerElectronicsIntegrationError("exact-head clearance ledger is required")
        if any(not item.passes for item in self.exact_head_clearances):
            failures = tuple(item.check_id for item in self.exact_head_clearances if not item.passes)
            raise PowerElectronicsIntegrationError(f"exact-head interference remains: {failures}")
        if type(self.shell_integration_records) is not tuple or not self.shell_integration_records:
            raise PowerElectronicsIntegrationError("shell integration ledger is required")
        if type(self.remaining_cross_lane_blockers) is not tuple or not self.remaining_cross_lane_blockers:
            raise PowerElectronicsIntegrationError("cross-lane blockers must remain explicit")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise PowerElectronicsIntegrationError("digital integration cannot be physical validation evidence")
        if self.evidence_status != DIGITAL_ONLY:
            raise PowerElectronicsIntegrationError("integration evidence status changed unexpectedly")

    @property
    def integration_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        return sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "authority_revision": self.authority_revision,
            "current_main_sha": self.current_main_sha,
            "current_manual_a_head_sha": self.current_manual_a_head_sha,
            "manual_a_realization_sha256": self.manual_a_realization_sha256,
            "base_package_sha256": self.base_package.package_sha256,
            "base_package_authored_manual_a_source_label": self.base_package.source_manual_a_head_sha,
            "source_label_semantics": "V1_AUTHORED_SOURCE_LABEL_IS_HISTORICAL;THIS_V2_WRAPPER_IS_EXACT_HEAD_AUTHORITY_FOR_STACKED_INTEGRATION",
            "exact_head_clearances": [item.manifest() for item in self.exact_head_clearances],
            "shell_integration_records": [item.manifest() for item in self.shell_integration_records],
            "remaining_cross_lane_blockers": list(self.remaining_cross_lane_blockers),
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            payload["integration_sha256"] = self.integration_sha256
        return payload


def _clear(check_id: str, item_id: str, item: cq.Workplane, obstacle_id: str, obstacle: cq.Workplane, state_id: str) -> ExactHeadClearance:
    volume = _intersection(item, obstacle)
    return ExactHeadClearance(check_id, item_id, obstacle_id, state_id, volume, "PASS_DIGITAL_CLEAR" if volume == 0.0 else "FAIL_DIGITAL_INTERFERENCE")


def _all_package_geometry(package: ElectronicsPackage) -> tuple[tuple[str, cq.Workplane], ...]:
    result: list[tuple[str, cq.Workplane]] = []
    result.extend((part.part_id, part.solid) for part in package.parts)
    result.extend((route.route_id, route.clearance_solid) for route in package.harness_routes)
    result.extend((f"HMI-{control.control_id}", control.solid) for control in package.controls)
    return tuple(result)


def build_power_electronics_integration(authority: Authority | None = None) -> PowerElectronicsIntegration:
    authority = authority or load_authority()
    package = build_electronics_package(authority)
    mechanical = build_mechanical_realization(authority)

    guard = _mechanical_part(mechanical, "QUICK-RELEASE-GUARD")
    shell = _mechanical_part(mechanical, "LIVE-MAIN-RIGID-SHELL")
    cartridge_sweep = _mechanical_sweep(mechanical, "CARTRIDGE-DOWNWARD-REMOVAL")
    release_sweep = _mechanical_sweep(mechanical, "QUICK-RELEASE-OUTBOARD-WITHDRAWAL")

    checks: list[ExactHeadClearance] = []
    geometry = _all_package_geometry(package)
    for item_id, solid in geometry:
        checks.append(_clear(f"CLEAR-{item_id}-QUICK-RELEASE-GUARD", item_id, solid, "QUICK-RELEASE-GUARD", guard, "INSTALLED"))

    # Re-run exact moving states against the new head as a source-bound promotion gate.
    for sweep in (release_sweep, cartridge_sweep):
        for index, sample in enumerate(sweep.sampled_solids()):
            state = f"{sweep.sweep_id}-S{index}"
            for item_id, solid in geometry:
                checks.append(_clear(f"CLEAR-{item_id}-{state}", item_id, solid, sweep.moving_part_id, sample, state))

    # Battery and dry-bay door service remain clear of the newly introduced guard.
    part_by_id = {part.part_id: part for part in package.parts}
    for part_id, trajectory in (
        ("BATTERY_REFERENCE", package.battery_service_trajectory_xyz_mm),
        ("DRY_BAY_DOOR", package.door_service_trajectory_xyz_mm),
    ):
        part = part_by_id[part_id]
        origin = trajectory[0]
        for index, point in enumerate(trajectory):
            moved = part.solid.translate(tuple(point[i] - origin[i] for i in range(3)))
            checks.append(_clear(f"CLEAR-{part_id}-SERVICE-S{index}-GUARD", part_id, moved, "QUICK-RELEASE-GUARD", guard, f"SERVICE-S{index}"))

    # Shell ledger distinguishes required-clear buried packages from intentional HMI handoffs.
    records: list[ShellIntegrationRecord] = []
    for part in package.parts:
        volume = _intersection(part.solid, shell)
        intentional = part.part_id in {"STATUS_WINDOW_RESERVATION"}
        records.append(ShellIntegrationRecord(
            part.part_id,
            volume,
            "INTENTIONAL_EXTERIOR_INTERFACE_RESERVATION" if intentional else "REQUIRED_CLEAR_FROM_RELEASED_SHELL_SOLID",
            "INTERFACE_REQUIRES_FINAL_EXTERIOR_FAIRING" if intentional else ("PASS_DIGITAL_CLEAR" if volume == 0.0 else "BLOCKED_SHELL_INTERSECTION"),
        ))
    for control in package.controls:
        volume = _intersection(control.solid, shell)
        records.append(ShellIntegrationRecord(
            f"HMI-{control.control_id}",
            volume,
            "INTENTIONAL_SIDE_CONTROL_SHELL_INTERFACE",
            "FINAL_EXTERIOR_CUT_SEAL_AND_FAIRING_REQUIRES_EXTERIOR_PR_CONVERGENCE",
        ))

    blocked_required_clear = tuple(record.item_id for record in records if record.relationship == "REQUIRED_CLEAR_FROM_RELEASED_SHELL_SOLID" and record.shell_intersection_volume_mm3 > 0.0)
    if blocked_required_clear:
        raise PowerElectronicsIntegrationError(f"buried electronics intersect released shell: {blocked_required_clear}")

    return PowerElectronicsIntegration(
        authority_revision=str(authority.get("project", "authority_revision")),
        current_main_sha=CURRENT_MAIN_SHA,
        current_manual_a_head_sha=CURRENT_MANUAL_A_HEAD_SHA,
        manual_a_realization_sha256=mechanical.realization_sha256,
        base_package=package,
        exact_head_clearances=tuple(checks),
        shell_integration_records=tuple(records),
        remaining_cross_lane_blockers=(
            "EXTERIOR_PR_62_REBASE_AND_FINAL_HMI_STATUS_WINDOW_CUT_SEAL_FAIRING",
            "FLUID_PR_61_RELEASE_AND_REALIZED_CENTERLINES_FOR_EXACT_HARNESS_TO_FLUID_ROUTE_CLEARANCE",
            "SELECTED_PCB_CONNECTOR_WIRE_SWITCH_CHARGER_PROTECTION_AND_THERMAL_HARDWARE",
            "BATTERY_SUPPLIER_SWELLING_ABUSE_RETENTION_AND_CONNECTOR_REQUIREMENTS",
            "PHYSICAL_INGRESS_ELECTRICAL_THERMAL_HMI_SERVICE_AND_RUNTIME_VALIDATION",
        ),
        physical_validation_eligible=False,
        evidence_status=DIGITAL_ONLY,
    )
