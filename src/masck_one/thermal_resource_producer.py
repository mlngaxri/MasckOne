"""Source-bound thermal producer inputs for the whole-routine resource graph.

This module reports only quantities directly available from the selected thermal
bench geometry or explicitly classified assumptions. Missing physical inputs stay
UNKNOWN. It is not a competing whole-product resource ledger.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path
from hashlib import sha1

from .thermal_reset_hardware import build_thermal_reset_hardware

SCHEMA = "MASCK_ONE_THERMAL_RESOURCE_PRODUCER_V3"
OWNER_PR = 143
OWNER_BRANCH = "scheduled/warm-cool-package-20260909"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
_REPO_ROOT = Path(__file__).resolve().parents[2]
_EXACT_GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_IDENTITY_4X4 = [
    [1.0, 0.0, 0.0, 0.0],
    [0.0, 1.0, 0.0, 0.0],
    [0.0, 0.0, 1.0, 0.0],
    [0.0, 0.0, 0.0, 1.0],
]


def _blob(path: Path) -> str:
    data = path.read_bytes()
    return sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def _finite3(values: tuple[float, float, float], label: str) -> list[float]:
    out = [float(v) for v in values]
    if len(out) != 3 or not all(math.isfinite(v) for v in out):
        raise ValueError(f"{label} must be finite XYZ")
    return out


def build_thermal_resource_producer(*, owner_head_sha: str) -> dict[str, object]:
    if type(owner_head_sha) is not str or _EXACT_GIT_SHA_RE.fullmatch(owner_head_sha) is None:
        raise ValueError("exact lowercase 40-hex owner head SHA required")
    parts, refs, geometry = build_thermal_reset_hardware()
    components: list[dict[str, object]] = []
    for component_id in sorted(parts):
        shape = parts[component_id]
        bb = shape.BoundingBox()
        center = shape.Center()
        components.append({
            "component_id": component_id,
            "geometry_role": "MANUFACTURED_BENCH_COMPONENT",
            "geometry_evidence": "EXACT_SOURCE_BREP",
            "volume_mm3": float(shape.Volume()),
            "geometric_centroid_world_mm": _finite3((center.x, center.y, center.z), "centroid"),
            "bounds_world_mm": {
                "min": _finite3((bb.xmin, bb.ymin, bb.zmin), "bounds min"),
                "max": _finite3((bb.xmax, bb.ymax, bb.zmax), "bounds max"),
            },
            "transform_to_world_4x4": [row[:] for row in _IDENTITY_4X4],
            "transform_evidence": "SOURCE_BREP_ALREADY_AUTHORED_IN_WORLD_FRAME",
            "mass_g": None,
            "mass_evidence": "UNKNOWN_NO_QUALIFIED_COMPONENT_MATERIAL_DENSITY",
            "mass_cg_world_mm": None,
        })
    source_path = _REPO_ROOT / "src/masck_one/thermal_reset_hardware.py"
    return {
        "schema": SCHEMA,
        "owner": {"pr": OWNER_PR, "branch": OWNER_BRANCH, "head_sha": owner_head_sha},
        "world_frame_id": WORLD_FRAME_ID,
        "source": {
            "path": "src/masck_one/thermal_reset_hardware.py",
            "git_blob_sha": _blob(source_path),
            "evidence_class": "SOURCE_BOUND_DIGITAL_GEOMETRY",
        },
        "service_state": "OFF_FACE_RESET_BENCH_CANDIDATE",
        "phase_occupancy": ["WARM", "COOL", "OFF_FACE_RESET"],
        "components": components,
        "reference_count": len(refs),
        "face_facing": {
            "left_contact_plate_footprint_mm": [22.0, 28.0],
            "right_contact_plate_footprint_mm": [22.0, 28.0],
            "evidence": "EXACT_CAD_DIMENSION",
        },
        "fluid": {
            "pcm_internal_void_each_mm3": float(geometry["cavity_mm3"]),
            "classification": "GEOMETRIC_VOID_NOT_RETAINED_CAPACITY",
            "retained_capacity_mm3": None,
        },
        "energy": {
            "heater_electrical_input": None,
            "cooling_energy": None,
            "dock_reset_energy": None,
            "classification": "UNKNOWN_UNQUALIFIED_PHYSICAL_INPUTS",
        },
        "resource_contract": {
            "mass_total_g": None,
            "mass_cg_world_mm": None,
            "energy_per_cycle_Wh": None,
            "thermal_safety": None,
            "condensation_behavior": None,
            "unknown_policy": "NEVER_ZERO_FILL",
        },
        "unresolved_evidence": [
            "component material densities and qualified masses",
            "heater electrical rating and fault hardware",
            "thermal safety and contact resistance",
            "condensation and migration behavior",
            "dock heat rejection performance",
            "whole-product installed transform and service clearance",
        ],
        "physical_validation_complete": False,
    }


def write_thermal_resource_producer(path: str | Path, *, owner_head_sha: str) -> None:
    Path(path).write_text(json.dumps(build_thermal_resource_producer(owner_head_sha=owner_head_sha), indent=2, sort_keys=True, allow_nan=False) + "\n")