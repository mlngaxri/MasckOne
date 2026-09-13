"""Source-bound dry-side producer inputs for the whole-routine resource graph.

Only digital package geometry is promoted. Qualified mass, electrical ratings,
runtime and physical service evidence remain UNKNOWN and are never zero-filled.
"""
from __future__ import annotations

from hashlib import sha1
import math
import re
from pathlib import Path

from .dry_side_harness_service import build_dry_side_harness_service, DRY_BAY_BOUNDS_WORLD_MM

SCHEMA = "MASCK_ONE_DRY_SIDE_RESOURCE_PRODUCER_V2"
OWNER_PR = 142
OWNER_BRANCH = "cell12/compact-dry-side-package-reconstructed-20260909"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
_REPO_ROOT = Path(__file__).resolve().parents[2]
_EXACT_GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_IDENTITY_WORLD_TRANSFORM = [
    [1.0, 0.0, 0.0, 0.0],
    [0.0, 1.0, 0.0, 0.0],
    [0.0, 0.0, 1.0, 0.0],
    [0.0, 0.0, 0.0, 1.0],
]


def _blob(path: Path) -> str:
    data = path.read_bytes()
    return sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def _finite(values: list[float]) -> bool:
    return all(math.isfinite(float(v)) for v in values)


def build_dry_side_resource_producer(*, owner_head_sha: str) -> dict[str, object]:
    if type(owner_head_sha) is not str or _EXACT_GIT_SHA_RE.fullmatch(owner_head_sha) is None:
        raise ValueError("exact lowercase 40-hex owner head SHA required")

    harness = build_dry_side_harness_service().manifest()
    route = harness["geometry"]["harness_route_envelope"]
    clips = harness["geometry"]["clip_reservations"]
    bounds = [float(v) for v in DRY_BAY_BOUNDS_WORLD_MM]
    if len(bounds) != 6 or not _finite(bounds):
        raise ValueError("finite dry-bay bounds required")

    source_paths = (
        "src/masck_one/battery_benchmark.py",
        "src/masck_one/dry_side_disconnect_interface.py",
        "src/masck_one/dry_side_harness_service.py",
    )
    sources = [
        {"path": rel, "git_blob_sha": _blob(_REPO_ROOT / rel), "evidence_class": "SOURCE_BOUND_DIGITAL_PACKAGE"}
        for rel in source_paths
    ]
    source_by_path = {source["path"]: source for source in sources}
    harness_source = source_by_path["src/masck_one/dry_side_harness_service.py"]

    return {
        "schema": SCHEMA,
        "owner": {"pr": OWNER_PR, "branch": OWNER_BRANCH, "head_sha": owner_head_sha},
        "world_frame_id": WORLD_FRAME_ID,
        "sources": sources,
        "components": [
            {
                "component_id": "DRY_SIDE_HARNESS_ROUTE_ENVELOPE",
                "source_path": harness_source["path"],
                "source_git_blob_sha": harness_source["git_blob_sha"],
                "evidence_class": "SOURCE_BOUND_DIGITAL_ENVELOPE",
                "transform_to_world_mm": _IDENTITY_WORLD_TRANSFORM,
                "bounds_world_mm": route["bounds_world_mm"],
                "volume_mm3": route["volume_mm3"],
                "mass_g": None,
                "mass_source": "UNKNOWN_NO_QUALIFIED_CONDUCTOR_OR_INSULATION_MASS",
            }
        ],
        "service_state": "DRY_SIDE_INSTALLED_WITH_REALIZED_DIGITAL_SERVICE_LOOP",
        "service_envelope": {
            "route_bounds_world_mm": route["bounds_world_mm"],
            "clip_bounds_world_mm": [clip["bounds_world_mm"] for clip in clips],
            "transform_to_world_mm": _IDENTITY_WORLD_TRANSFORM,
            "evidence": "DIGITAL_ENVELOPE_ONLY_PHYSICAL_SERVICE_UNVALIDATED",
        },
        "containment": {
            "dry_bay_bounds_world_mm": bounds,
            "evidence": "EXACT_DIGITAL_PACKAGE_BOUND",
        },
        "harness": {
            "route_bounds_world_mm": route["bounds_world_mm"],
            "route_volume_mm3": route["volume_mm3"],
            "route_path_length_mm": harness["route_path_length_mm"],
            "direct_endpoint_span_mm": harness["direct_endpoint_span_mm"],
            "service_loop_extra_path_mm": harness["service_loop_extra_path_mm"],
            "service_loop_min_extra_path_mm": harness["service_loop_min_extra_path_mm"],
            "pcb_handoff_datum_world_mm": harness["pcb_handoff_datum_world_mm"],
            "disconnect_mating_datum_world_mm": harness["source_disconnect_mating_datum_world_mm"],
            "clip_bounds_world_mm": [clip["bounds_world_mm"] for clip in clips],
            "evidence": "DIGITAL_ENVELOPE_NOT_CONDUCTOR_OR_BEND_LIFE_EVIDENCE",
        },
        "resource_contract": {
            "component_masses_g": None,
            "mass_total_g": None,
            "mass_cg_world_mm": None,
            "energy_per_cycle_Wh": None,
            "release_reserve": None,
            "electrical_ratings": None,
            "unknown_policy": "NEVER_ZERO_FILL",
        },
        "unresolved_evidence": [
            "qualified battery PCB connector conductor and harness masses",
            "component mass CG transforms after qualified masses exist",
            "connector and conductor electrical ratings",
            "wet dry bulkhead physical ingress performance",
            "battery runtime and release reserve",
            "bend life retention force EMC and electrical safety",
            "physical service ergonomics and durability",
        ],
        "physical_validation_complete": False,
    }
