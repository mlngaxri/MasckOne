from __future__ import annotations

"""Live candidate-head rebind for the Cell 15 assembly/service inventory.

The base inventory records the initial exact reconstruction. This thin layer exists so a
concurrent producer head can be rebound without rewriting or relabelling the immutable
source reconstruction. It does not change released-main truth or promote candidate work.
"""

from dataclasses import replace

from . import assembly_service_inventory_base as _base
from .assembly_service_inventory_base import *  # noqa: F401,F403


CELL2_REAR_SERVICE_PR = 70
CELL2_REAR_SERVICE_HEAD = "559f89953e6ac7667e79426daabcd54b88f43acb"
CELL2_REAR_SERVICE_PREVIOUS_HEAD = "58b95bc369d3879607ac060a5725426019d65abc"
CELL2_REAR_SERVICE_REBIND_DISPOSITION = (
    "HEAD_MOVED_BY_EXTERIOR_EYE_ROLL_SOLID_NORMALIZATION_ONLY_REAR_SERVICE_MOTION_EVIDENCE_UNCHANGED"
)


def _rebind_service_domains() -> tuple[_base.ServiceDomain, ...]:
    rebound: list[_base.ServiceDomain] = []
    found = False
    for domain in _base._service_domains():
        if domain.domain_id != "MASCK_ONE-SERVICE-REAR-COVER-ACCESS":
            rebound.append(domain)
            continue
        if domain.candidate is None or domain.candidate.pr_number != CELL2_REAR_SERVICE_PR:
            raise _base.AssemblyServiceInventoryError(
                "rear-cover service domain lost its expected Cell 2 candidate binding"
            )
        found = True
        rebound.append(
            replace(
                domain,
                candidate=replace(domain.candidate, head_sha=CELL2_REAR_SERVICE_HEAD),
            )
        )
    if not found:
        raise _base.AssemblyServiceInventoryError("rear-cover service domain is missing")
    return tuple(rebound)


def build_current_assembly_service_inventory(
    *, validate_sources: bool = True
) -> _base.AssemblyServiceInventory:
    if validate_sources:
        _base.validate_released_source_bindings()
    return _base.AssemblyServiceInventory(
        _base._released_model_instances(),
        _base._dfm_donor_parts(),
        _rebind_service_domains(),
    )
