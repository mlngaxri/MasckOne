from __future__ import annotations

"""Mounted four-zone V11: V10 geometry verified through collision kernel V2.

V11 changes no manufactured geometry, motion target, service travel, source binding,
or collision threshold. It promotes the fail-closed collision successor through the
mounted verification path and forces terminal-datum construction through V5. Legacy
V9/V10 module hooks are restored after every synchronous build.
"""

from contextlib import contextmanager
from typing import Iterator

from . import treatment_collision_kernel_v2 as collision_v2
from . import treatment_mounted_four_zone_v9 as v9
from . import treatment_mounted_four_zone_v10 as v10
from .treatment_terminal_datum_preload_v5 import (
    COLLISION_KERNEL,
    build_terminal_datum_preload_v5_architecture,
)

SCHEMA = "MASCK_ONE_TREATMENT_MOUNTED_FOUR_ZONE_V11"


@contextmanager
def _v2_mounted_verification() -> Iterator[None]:
    original_intersection = v9.intersection_volume_mm3
    original_terminal_builder = v9.build_terminal_datum_preload_v4_architecture
    v9.intersection_volume_mm3 = collision_v2.intersection_volume_mm3
    v9.build_terminal_datum_preload_v4_architecture = build_terminal_datum_preload_v5_architecture
    try:
        yield
    finally:
        v9.intersection_volume_mm3 = original_intersection
        v9.build_terminal_datum_preload_v4_architecture = original_terminal_builder


def build_mounted_four_zone_architecture_v11(**kwargs):
    """Build unchanged V10/V9 material geometry under fail-closed kernel V2."""
    with _v2_mounted_verification():
        architecture, datums = v10.build_mounted_four_zone_architecture_v10(**kwargs)
    return architecture, datums


def manifest_v11(architecture, datums) -> dict[str, object]:
    payload = v10.manifest_v10(architecture, datums)
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
    return payload
