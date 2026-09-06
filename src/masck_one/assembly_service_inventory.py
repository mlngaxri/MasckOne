from __future__ import annotations

"""Live candidate-head and candidate-part overlay for the Cell 15 inventory.

The base inventory records the initial exact reconstruction byte-for-byte. This layer
rebounds concurrent producer movement and adds newly published candidate-only parts
without rewriting historical evidence or promoting unmerged work into release truth.
"""

from dataclasses import replace
from hashlib import sha256
import json

from . import assembly_service_inventory_base as _base
from .assembly_service_inventory_base import *  # noqa: F401,F403


CELL2_REAR_SERVICE_PR = 70
CELL2_REAR_SERVICE_HEAD = "559f89953e6ac7667e79426daabcd54b88f43acb"
CELL2_REAR_SERVICE_PREVIOUS_HEAD = "58b95bc369d3879607ac060a5725426019d65abc"
CELL2_REAR_SERVICE_REBIND_DISPOSITION = (
    "HEAD_MOVED_BY_EXTERIOR_EYE_ROLL_SOLID_NORMALIZATION_ONLY_REAR_SERVICE_MOTION_EVIDENCE_UNCHANGED"
)

CELL3_RETENTION_PR = 92
CELL3_RETENTION_HEAD = "abb806a8e15a1557c8b5a4c754af1bfeea8b6d70"
CELL3_RETENTION_PREVIOUS_HEAD = "e332426526ec4ceb885ad9d35250a89d78b6066c"
CELL3_RETENTION_REBIND_DISPOSITION = (
    "HEAD_MOVED_FOR_ATTACHMENT_SEMANTIC_CORRECTION_WITH_RETENTION_SERVICE_BREP_CONSTRUCTION_UNCHANGED"
)

CELL8_RETENTION_GUARD_PR = 109
CELL8_RETENTION_GUARD_HEAD = "fb586cc1ea1cde92526417593f9e5aa990d2ae4f"
CELL8_RETENTION_GUARD_PREVIOUS_HEAD = "a27757eb4eda54a18b3d89db70f9534e492e588f"
CELL8_RETENTION_GUARD_BLOB = "b497e9154067cef9ee24da4d421ea6c7861c348e"
CELL8_RETENTION_GUARD_INTERFACE_SHA256 = (
    "ce2618f872e01733a2031085ccb402bc40b61ae1e9b427456c0da049bcd72061"
)
CELL8_BOUND_RETENTION_PR = 92
CELL8_BOUND_RETENTION_HEAD = CELL3_RETENTION_HEAD
CELL8_BOUND_RIGHT_RELEASE_PR = 71
CELL8_BOUND_RIGHT_RELEASE_HEAD = "0b5a619c6cea344038b0e8b8cc10a50e3d193390"
CELL8_CANDIDATE_STATUS = "CURRENT_HEAD_UNMERGED_CANDIDATE_NOT_RELEASE_AUTHORITY"
CELL8_ATTACHMENT_STATUS = "POSITIVE_ATTACHMENT_COUNTERPART_NOT_REALIZED"
CELL8_REBIND_DISPOSITION = (
    "HEAD_MOVED_ONLY_TO_REBIND_CELL3_RETENTION_SEMANTIC_REPAIR_GUARD_BREP_AND_FACTORY_SWEEPS_UNCHANGED"
)


def _rebind_service_domains() -> tuple[_base.ServiceDomain, ...]:
    rebound: list[_base.ServiceDomain] = []
    found_rear = False
    found_retention = 0
    for domain in _base._service_domains():
        candidate = domain.candidate
        if domain.domain_id == "MASCK_ONE-SERVICE-REAR-COVER-ACCESS":
            if candidate is None or candidate.pr_number != CELL2_REAR_SERVICE_PR:
                raise _base.AssemblyServiceInventoryError(
                    "rear-cover service domain lost its expected Cell 2 candidate binding"
                )
            found_rear = True
            domain = replace(
                domain,
                candidate=replace(candidate, head_sha=CELL2_REAR_SERVICE_HEAD),
            )
        elif candidate is not None and candidate.pr_number == CELL3_RETENTION_PR:
            found_retention += 1
            domain = replace(
                domain,
                candidate=replace(candidate, head_sha=CELL3_RETENTION_HEAD),
            )
        rebound.append(domain)
    if not found_rear:
        raise _base.AssemblyServiceInventoryError("rear-cover service domain is missing")
    if found_retention != 2:
        raise _base.AssemblyServiceInventoryError(
            "expected exactly two Cell 3 retention service-domain bindings"
        )
    return tuple(rebound)


def _cell8_candidate_parts() -> tuple[dict[str, object], ...]:
    common: dict[str, object] = {
        "producer_pr": CELL8_RETENTION_GUARD_PR,
        "producer_head_sha": CELL8_RETENTION_GUARD_HEAD,
        "producer_previous_head_sha": CELL8_RETENTION_GUARD_PREVIOUS_HEAD,
        "producer_rebind_disposition": CELL8_REBIND_DISPOSITION,
        "producer_source_path": "src/masck_one/retention_hazard_guards.py",
        "producer_source_blob_sha": CELL8_RETENTION_GUARD_BLOB,
        "candidate_interface_sha256": CELL8_RETENTION_GUARD_INTERFACE_SHA256,
        "authority_status": CELL8_CANDIDATE_STATUS,
        "semantic_role": "PHYSICAL_MATERIAL_CANDIDATE",
        "development_assembly_included": False,
        "positive_attachment_realized": False,
        "attachment_status": CELL8_ATTACHMENT_STATUS,
        "cell5_dfm_part_family_present": False,
        "assembly_stage": None,
        "assembly_stage_status": "NOT_PRESENT_IN_CELL5_DFM_DONOR",
        "physical_validation_eligible": False,
    }
    parts = (
        {
            **common,
            "part_id": "CELL8_LEFT_ADJUSTMENT_U_SHROUD",
            "side": "WEARER_LEFT",
            "factory_sequence_group": "BILATERAL_ADJUSTMENT_GUARDS",
            "exact_factory_install_translation_world_mm": [-22.0, 0.0, 0.0],
            "exact_factory_install_sweep_bounds_world_mm": {
                "x": [-87.5, -54.5],
                "y": [-1.5, 29.0],
                "z": [-37.5, -25.75],
            },
            "motion_evidence": "EXACT_CLOSED_INTERVAL_PURE_X_BREP_SWEEP_NOT_SAMPLED_WAYPOINTS",
        },
        {
            **common,
            "part_id": "CELL8_RIGHT_ADJUSTMENT_U_SHROUD",
            "side": "WEARER_RIGHT",
            "factory_sequence_group": "BILATERAL_ADJUSTMENT_GUARDS",
            "exact_factory_install_translation_world_mm": [22.0, 0.0, 0.0],
            "exact_factory_install_sweep_bounds_world_mm": {
                "x": [54.5, 87.5],
                "y": [-1.5, 29.0],
                "z": [-37.5, -25.75],
            },
            "motion_evidence": "EXACT_CLOSED_INTERVAL_PURE_X_BREP_SWEEP_NOT_SAMPLED_WAYPOINTS",
        },
        {
            **common,
            "part_id": "CELL8_RIGHT_QUICK_RELEASE_U_SHROUD",
            "side": "WEARER_RIGHT",
            "factory_sequence_group": "RIGHT_RELEASE_GUARD_AFTER_ADJUSTMENT_GUARDS",
            "exact_factory_install_translation_world_mm": [35.0, 0.0, 0.0],
            "exact_factory_install_sweep_bounds_world_mm": {
                "x": [35.0, 90.0],
                "y": [-8.5, 8.5],
                "z": [-25.0, -10.0],
            },
            "motion_evidence": "EXACT_CLOSED_INTERVAL_PURE_X_BREP_SWEEP_NOT_SAMPLED_WAYPOINTS",
        },
    )
    return tuple(sorted(parts, key=lambda item: str(item["part_id"])))


class CurrentAssemblyServiceInventory:
    """Read-through current overlay preserving the validated base inventory contract."""

    __slots__ = ("_base_inventory",)

    def __init__(self, base_inventory: _base.AssemblyServiceInventory) -> None:
        if type(base_inventory) is not _base.AssemblyServiceInventory:
            raise _base.AssemblyServiceInventoryError("current overlay requires exact base inventory")
        self._base_inventory = base_inventory

    def __getattr__(self, name: str) -> object:
        return getattr(self._base_inventory, name)

    @property
    def candidate_parts(self) -> tuple[dict[str, object], ...]:
        return _cell8_candidate_parts()

    @property
    def inventory_sha256(self) -> str:
        raw = json.dumps(
            self.manifest(include_sha=False),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload = self._base_inventory.manifest(include_sha=False)
        payload["source_contracts"] = dict(payload["source_contracts"])
        payload["source_contracts"]["cell8_retention_hazard_guards"] = {
            "pr_number": CELL8_RETENTION_GUARD_PR,
            "head_sha": CELL8_RETENTION_GUARD_HEAD,
            "previous_head_sha": CELL8_RETENTION_GUARD_PREVIOUS_HEAD,
            "rebind_disposition": CELL8_REBIND_DISPOSITION,
            "source_path": "src/masck_one/retention_hazard_guards.py",
            "source_blob_sha": CELL8_RETENTION_GUARD_BLOB,
            "candidate_interface_sha256": CELL8_RETENTION_GUARD_INTERFACE_SHA256,
            "bound_cell3_retention_pr": CELL8_BOUND_RETENTION_PR,
            "bound_cell3_retention_head_sha": CELL8_BOUND_RETENTION_HEAD,
            "bound_right_release_pr": CELL8_BOUND_RIGHT_RELEASE_PR,
            "bound_right_release_head_sha": CELL8_BOUND_RIGHT_RELEASE_HEAD,
            "authority_status": CELL8_CANDIDATE_STATUS,
        }
        payload["candidate_part_inventory"] = [dict(part) for part in self.candidate_parts]
        payload["candidate_factory_installation_motion_evidence"] = [
            {
                "part_id": part["part_id"],
                "factory_sequence_group": part["factory_sequence_group"],
                "translation_world_mm": part["exact_factory_install_translation_world_mm"],
                "sweep_bounds_world_mm": part["exact_factory_install_sweep_bounds_world_mm"],
                "motion_evidence": part["motion_evidence"],
                "reference_sweep_is_product_material": False,
                "wearer_present": False,
                "powered": False,
            }
            for part in self.candidate_parts
        ]
        payload["reconciliation_findings"] = dict(payload["reconciliation_findings"])
        payload["reconciliation_findings"]["cell5_dfm_missing_cell8_guard_part_families"] = [
            part["part_id"] for part in self.candidate_parts
        ]
        payload["reconciliation_findings"]["cell8_guard_factory_motion_disposition"] = (
            "NONTELEPORTING_FACTORY_INSTALL_SWEEPS_EXIST_AS_CURRENT_CANDIDATE_EVIDENCE_BUT_"
            "POSITIVE_ATTACHMENT_AND_INTEGRATED_POST_RELEASE_WHOLE_HEAD_REMOVAL_REMAIN_OPEN"
        )
        payload["reconciliation_findings"]["cell2_rear_service_head_rebind"] = {
            "previous_head_sha": CELL2_REAR_SERVICE_PREVIOUS_HEAD,
            "current_head_sha": CELL2_REAR_SERVICE_HEAD,
            "disposition": CELL2_REAR_SERVICE_REBIND_DISPOSITION,
        }
        payload["reconciliation_findings"]["cell3_retention_service_head_rebind"] = {
            "previous_head_sha": CELL3_RETENTION_PREVIOUS_HEAD,
            "current_head_sha": CELL3_RETENTION_HEAD,
            "disposition": CELL3_RETENTION_REBIND_DISPOSITION,
        }
        payload["physical_validation_eligible"] = False
        if include_sha:
            payload["inventory_sha256"] = self.inventory_sha256
        return payload


def build_current_assembly_service_inventory(
    *, validate_sources: bool = True
) -> CurrentAssemblyServiceInventory:
    if validate_sources:
        _base.validate_released_source_bindings()
    base_inventory = _base.AssemblyServiceInventory(
        _base._released_model_instances(),
        _base._dfm_donor_parts(),
        _rebind_service_domains(),
    )
    return CurrentAssemblyServiceInventory(base_inventory)
