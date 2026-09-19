from __future__ import annotations

"""Terminal datum/preload V5: V4 geometry verified with collision kernel V2.

V5 intentionally changes no manufactured geometry, service motion, source binding,
or collision threshold. It promotes the fail-closed collision-kernel successor into
the terminal-datum build so an OCC Common that completes with unusable positive
topology is recovered through the exact Cut/partition chain rather than aborting
before that existing exact fallback can run.
"""

from contextlib import contextmanager
from typing import Iterator

from . import treatment_collision_kernel_v2 as collision_v2
from . import treatment_terminal_datum_preload_v4 as v4

SCHEMA = "MASCK_ONE_TREATMENT_TERMINAL_DATUM_PRELOAD_V5"
SOURCE_CELL6_HEAD_SHA = v4.SOURCE_CELL6_HEAD_SHA
COLLISION_KERNEL = "TREATMENT_COLLISION_KERNEL_V2"

TreatmentTerminalDatumPreloadV5Error = v4.TreatmentTerminalDatumPreloadV4Error
TerminalDatumPreloadV5Architecture = v4.TerminalDatumPreloadV4Architecture


@contextmanager
def _v2_collision_verification() -> Iterator[None]:
    """Bind V4's verification hook to V2 only for this synchronous build.

    V4 imports the collision function into its module namespace. Rebinding that hook
    here avoids copying geometry code while keeping legacy V4 behaviour unchanged for
    historical reproduction. The original hook is restored even if verification
    fails, so importing or building V5 cannot silently alter later V4 callers.
    """
    original = v4.intersection_volume_mm3
    v4.intersection_volume_mm3 = collision_v2.intersection_volume_mm3
    try:
        yield
    finally:
        v4.intersection_volume_mm3 = original


def build_terminal_datum_preload_v5_architecture(**kwargs) -> TerminalDatumPreloadV5Architecture:
    """Build unchanged V4 material geometry under fail-closed collision kernel V2."""
    with _v2_collision_verification():
        architecture = v4.build_terminal_datum_preload_v4_architecture(**kwargs)
    if architecture.source_cell6_head_sha != SOURCE_CELL6_HEAD_SHA:
        raise TreatmentTerminalDatumPreloadV5Error("terminal datum V5 source binding drifted")
    return architecture


def manifest_v5(architecture: TerminalDatumPreloadV5Architecture) -> dict[str, object]:
    payload = architecture.manifest()
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
    return payload
