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


def verify_promoted_evidence_v11(payload: object) -> None:
    """Fail closed unless a materialized V11 manifest still matches its evidence digest."""
    if type(payload) is not dict:
        raise TreatmentMountedFourZoneV11Error(
            "mounted four-zone V11 evidence verification requires exact dict payload"
        )
    if payload.get("schema") != SCHEMA:
        raise TreatmentMountedFourZoneV11Error(
            "mounted four-zone V11 evidence verification requires V11 schema"
        )
    claimed = payload.get("promoted_evidence_sha256")
    if type(claimed) is not str or len(claimed) != 64:
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
    if upstream_payload.get("source_cell6_head_sha") != SOURCE_CELL6_HEAD_SHA:
        raise TreatmentMountedFourZoneV11Error(
            "mounted four-zone V11 manifest source binding does not match accepted Cell 6 lineage"
        )
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
    payload.pop("promoted_evidence_sha256", None)
    payload["promoted_evidence_sha256"] = _promoted_evidence_sha256(payload)
    verify_promoted_evidence_v11(payload)
    return payload
