from __future__ import annotations

"""Terminal datum/preload V5: V4 geometry verified with collision kernel V2.

V5 intentionally changes no manufactured geometry, service motion, source binding,
or collision threshold. It promotes the fail-closed collision-kernel successor into
the terminal-datum build so an OCC Common that completes with unusable positive
topology is recovered through the exact Cut/partition chain rather than aborting
before that existing exact fallback can run.
"""

from contextlib import contextmanager
import hashlib
import json
from threading import RLock
from typing import Iterator

from . import treatment_collision_kernel_v2 as collision_v2
from . import treatment_terminal_datum_preload_v4 as v4

SCHEMA = "MASCK_ONE_TREATMENT_TERMINAL_DATUM_PRELOAD_V5"
SOURCE_CELL6_HEAD_SHA = v4.SOURCE_CELL6_HEAD_SHA
COLLISION_KERNEL = "TREATMENT_COLLISION_KERNEL_V2"

TreatmentTerminalDatumPreloadV5Error = v4.TreatmentTerminalDatumPreloadV4Error
TerminalDatumPreloadV5Architecture = v4.TerminalDatumPreloadV4Architecture

_COLLISION_HOOK_LOCK = RLock()


@contextmanager
def _v2_collision_verification() -> Iterator[None]:
    """Bind V4's verification hook to V2 only for this synchronous build."""
    with _COLLISION_HOOK_LOCK:
        original = v4.intersection_volume_mm3
        v4.intersection_volume_mm3 = collision_v2.intersection_volume_mm3
        try:
            yield
        finally:
            v4.intersection_volume_mm3 = original


def _require_exact_architecture(architecture: object, *, context: str) -> TerminalDatumPreloadV5Architecture:
    """Reject proxies and subclasses at the promoted V5 qualification boundary."""
    if type(architecture) is not TerminalDatumPreloadV5Architecture:
        raise TreatmentTerminalDatumPreloadV5Error(
            f"terminal datum V5 {context} requires exact architecture type "
            f"{TerminalDatumPreloadV5Architecture.__name__}; got {type(architecture).__name__}"
        )
    return architecture


def _require_source_binding(architecture: TerminalDatumPreloadV5Architecture, *, context: str) -> None:
    """Require the accepted Cell 6 lineage at every V5 certification boundary."""
    if architecture.source_cell6_head_sha != SOURCE_CELL6_HEAD_SHA:
        raise TreatmentTerminalDatumPreloadV5Error(
            f"terminal datum V5 source binding drifted before {context}"
        )


def build_terminal_datum_preload_v5_architecture(**kwargs) -> TerminalDatumPreloadV5Architecture:
    """Build unchanged V4 material geometry under fail-closed collision kernel V2."""
    with _v2_collision_verification():
        architecture = v4.build_terminal_datum_preload_v4_architecture(**kwargs)
    architecture = _require_exact_architecture(architecture, context="builder")
    _require_source_binding(architecture, context="builder return")
    return architecture


def manifest_v5(architecture: TerminalDatumPreloadV5Architecture) -> dict[str, object]:
    architecture = _require_exact_architecture(architecture, context="manifest")
    _require_source_binding(architecture, context="manifest certification")
    payload = architecture.manifest()
    # The V4 architecture is mutable and manifest construction is not atomic with the
    # pre-check above. Revalidate after materialising the payload and require the
    # payload itself to carry the accepted lineage. This closes a concurrent-mutation
    # window in which a stale/hostile source could otherwise receive a promoted digest.
    _require_source_binding(architecture, context="manifest payload materialization")
    if payload.get("source_cell6_head_sha") != SOURCE_CELL6_HEAD_SHA:
        raise TreatmentTerminalDatumPreloadV5Error(
            "terminal datum V5 manifest payload source binding drifted before certification"
        )
    payload.pop("architecture_sha256", None)
    payload.update(
        {
            "schema": SCHEMA,
            "supersedes": v4.SCHEMA,
            "collision_kernel": COLLISION_KERNEL,
            "physical_geometry_changed_from_v4": False,
            "collision_threshold_weakened": False,
            "physical_validation_eligible": False,
        }
    )
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()
    payload["architecture_sha256"] = hashlib.sha256(canonical).hexdigest()
    return payload
