from __future__ import annotations

"""Mounted four-zone V11: V10 geometry verified through collision kernel V2.

V11 changes no manufactured geometry, motion target, service travel, source binding,
or collision threshold. It promotes the fail-closed collision successor through the
mounted verification path and forces terminal-datum construction through V5. Legacy
V9/V10 module hooks are restored after every synchronous build. Because those hooks
are process-global module state, promoted builds are serialized so concurrent callers
cannot observe or restore another build's temporary verification bindings.
"""

from contextlib import contextmanager
import hashlib
import json
from threading import RLock
from typing import Iterator

from . import treatment_collision_kernel_v2 as collision_v2
from . import treatment_mounted_four_zone_v9 as v9
from . import treatment_mounted_four_zone_v10 as v10
from .treatment_terminal_datum_preload_v5 import (
    COLLISION_KERNEL,
    SOURCE_CELL6_HEAD_SHA,
    TerminalDatumPreloadV5Architecture,
    build_terminal_datum_preload_v5_architecture,
)

SCHEMA = "MASCK_ONE_TREATMENT_MOUNTED_FOUR_ZONE_V11"
TreatmentMountedFourZoneV11Error = v10.TreatmentMountedFourZoneV10Error

_VERIFICATION_HOOK_LOCK = RLock()


@contextmanager
def _v2_mounted_verification() -> Iterator[None]:
    with _VERIFICATION_HOOK_LOCK:
        original_intersection = v9.intersection_volume_mm3
        original_terminal_builder = v9.build_terminal_datum_preload_v4_architecture
        v9.intersection_volume_mm3 = collision_v2.intersection_volume_mm3
        v9.build_terminal_datum_preload_v4_architecture = build_terminal_datum_preload_v5_architecture
        try:
            yield
        finally:
            v9.intersection_volume_mm3 = original_intersection
            v9.build_terminal_datum_preload_v4_architecture = original_terminal_builder


def _require_promoted_build_result(architecture: object, datums: object):
    """Admit only builder-owned mounted and terminal architecture at V11 boundary."""
    if type(architecture) is not v10.MountedFourZoneArchitecture:
        raise TreatmentMountedFourZoneV11Error(
            "mounted four-zone V11 builder requires exact MountedFourZoneArchitecture; "
            f"got {type(architecture).__name__}"
        )
    if type(datums) is not TerminalDatumPreloadV5Architecture:
        raise TreatmentMountedFourZoneV11Error(
            "mounted four-zone V11 builder requires exact terminal datum architecture; "
            f"got {type(datums).__name__}"
        )
    if datums.source_cell6_head_sha != SOURCE_CELL6_HEAD_SHA:
        raise TreatmentMountedFourZoneV11Error(
            "mounted four-zone V11 terminal datum source binding drifted after build"
        )
    return architecture, datums


def _promoted_evidence_sha256(payload: dict[str, object]) -> str:
    """Digest the complete promoted evidence payload with deterministic JSON semantics."""
    try:
        canonical = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise TreatmentMountedFourZoneV11Error(
            "mounted four-zone V11 promoted evidence is not canonically serializable"
        ) from exc
    return hashlib.sha256(canonical).hexdigest()


def _require_cell6_provenance_v11(payload: dict[str, object]) -> None:
    """Require every promoted Cell 6 lineage declaration to agree with the pinned source."""
    required = {
        "source_cell6_head_sha": SOURCE_CELL6_HEAD_SHA,
        "source_cell6_geometry_head_sha": SOURCE_CELL6_HEAD_SHA,
        "source_cell6_head_semantics": v10.SOURCE_CELL6_HEAD_SEMANTICS,
        "active_cell6_owner_head_claimed": False,
        "live_cell6_owner_recheck_required_before_promotion": True,
    }
    for field, accepted in required.items():
        observed = payload.get(field)
        if type(observed) is not type(accepted) or observed != accepted:
            raise TreatmentMountedFourZoneV11Error(
                f"mounted four-zone V11 Cell 6 provenance field {field!r} does not match accepted evidence"
            )

    fusion = payload.get("fusion_handoff")
    if type(fusion) is not dict:
        raise TreatmentMountedFourZoneV11Error(
            "mounted four-zone V11 requires exact fusion_handoff provenance evidence"
        )
    for field, accepted in required.items():
        observed = fusion.get(field)
        if type(observed) is not type(accepted) or observed != accepted:
            raise TreatmentMountedFourZoneV11Error(
                f"mounted four-zone V11 fusion Cell 6 provenance field {field!r} does not match accepted evidence"
            )


def _require_v10_predecessor_evidence(payload: dict[str, object]) -> None:
    """Prevent V11 promotion from laundering non-V10 evidence through field overwrite."""
    observed = payload.get("schema")
    if type(observed) is not str or observed != v10.SCHEMA_V10:
        raise TreatmentMountedFourZoneV11Error(
            "mounted four-zone V11 promotion requires authentic V10 predecessor schema"
        )
    if "promoted_evidence_sha256" in payload:
        raise TreatmentMountedFourZoneV11Error(
            "mounted four-zone V11 predecessor evidence must not contain a V11 promotion digest"
        )


def verify_promoted_evidence_v11(payload: object) -> None:
    """Fail closed unless materialized V11 evidence is intact and still qualified."""
    if type(payload) is not dict:
        raise TreatmentMountedFourZoneV11Error(
            "mounted four-zone V11 evidence verification requires exact dict payload"
        )
    if type(payload.get("schema")) is not str or payload.get("schema") != SCHEMA:
        raise TreatmentMountedFourZoneV11Error(
            "mounted four-zone V11 evidence verification requires V11 schema"
        )

    _require_cell6_provenance_v11(payload)

    required_qualification = {
        "supersedes": v10.SCHEMA_V10,
        "collision_kernel": COLLISION_KERNEL,
        "terminal_datum_verification": "TERMINAL_DATUM_PRELOAD_V5",
        "physical_architecture_changed_from_v10": False,
        "collision_threshold_weakened": False,
        "physical_validation_eligible": False,
    }
    for field, accepted in required_qualification.items():
        observed = payload.get(field)
        if type(observed) is not type(accepted) or observed != accepted:
            raise TreatmentMountedFourZoneV11Error(
                f"mounted four-zone V11 qualification field {field!r} does not match accepted evidence"
            )

    claimed = payload.get("promoted_evidence_sha256")
    if (
        type(claimed) is not str
        or len(claimed) != 64
        or any(character not in "0123456789abcdef" for character in claimed)
    ):
        raise TreatmentMountedFourZoneV11Error(
            "mounted four-zone V11 promoted evidence digest is missing or malformed"
        )
    evidence = payload.copy()
    evidence.pop("promoted_evidence_sha256")
    expected = _promoted_evidence_sha256(evidence)
    if not hashlib.compare_digest(claimed, expected):
        raise TreatmentMountedFourZoneV11Error(
            "mounted four-zone V11 promoted evidence digest mismatch"
        )


def build_mounted_four_zone_architecture_v11(**kwargs):
    """Build unchanged V10/V9 material geometry under fail-closed kernel V2."""
    with _v2_mounted_verification():
        architecture, datums = v10.build_mounted_four_zone_architecture_v10(**kwargs)
    return _require_promoted_build_result(architecture, datums)


def manifest_v11(architecture, datums) -> dict[str, object]:
    architecture, datums = _require_promoted_build_result(architecture, datums)
    upstream_payload = v10.manifest_v10(architecture, datums)
    if type(upstream_payload) is not dict:
        raise TreatmentMountedFourZoneV11Error(
            "mounted four-zone V11 requires exact dict manifest materialization"
        )
    _require_promoted_build_result(architecture, datums)
    _require_v10_predecessor_evidence(upstream_payload)
    _require_cell6_provenance_v11(upstream_payload)
    payload = upstream_payload.copy()
    payload.update(
        {
            "schema": SCHEMA,
            "supersedes": v10.SCHEMA_V10,
            "collision_kernel": COLLISION_KERNEL,
            "terminal_datum_verification": "TERMINAL_DATUM_PRELOAD_V5",
            "physical_architecture_changed_from_v10": False,
            "collision_threshold_weakened": False,
            "physical_validation_eligible": False,
        }
    )
    payload["promoted_evidence_sha256"] = _promoted_evidence_sha256(payload)
    verify_promoted_evidence_v11(payload)
    return payload
