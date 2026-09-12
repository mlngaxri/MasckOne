"""Source-bound thermal producer inputs for the whole-routine resource graph.

This module reports only quantities directly available from the selected thermal
bench geometry or explicitly classified assumptions. Missing physical inputs stay
UNKNOWN. It is not a competing whole-product resource ledger.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
from hashlib import sha1

from .thermal_reset_hardware import build_thermal_reset_hardware

SCHEMA = "MASCK_ONE_THERMAL_RESOURCE_PRODUCER_V1"
OWNER_PR = 143
OWNER_BRANCH = "scheduled/warm-cool-package-20260909"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
_REPO_ROOT = Path(__file__).resolve().parents[2]


def _blob(path: Path) -> str:
    data = path.read_bytes()
    return sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def _finite3(values: tuple[float, float, float], label: str) -> list[float]:
    out = [float(v) for v in values]
    if len(out) != 3 or not all(math.isfinite(v) for v in out):
        raise ValueError(f"{label} must be finite XYZ")
    return out


def build_thermal_resource_producer(*, owner_head_sha: str) -> dict[str, object]:
    if type(owner_head_sha) is not str or len(owner_head_sha) != 40:
        raise ValueError("exact 40-character owner head SHA required")
    parts, refs, geometry = build_thermal_reset_hardware()
    components: list[dict[str, object]] = []
    for component_id in sorted(parts):
        shape = parts[component_id]
        bb = shape.BoundingBox()
        center = shape.Center()
        components.append({
            "component_id": component_id,
            "geometry_role": "MANUFACTURED_BENCH_COMPONENT",
            "volume_mm3": float(shape.Volume()),
            "geometric_centroid_world_mm": _finite3((center.x, center.y, center.z), "centroid"),
            "bounds_world_mm": {
                "min": _finite3((bb.xmin, bb.ymin, bb.zmin), "bounds min"),
                "max": _finite3((bb.xmax, bb.ymax, bb.zmax), "bounds max"),
            },
            "mass_g": None,
            "mass_evidence": "UNKNOWN_NO_QUALIFIED_COMPONENT_MATERIAL_DENSITY",
            "mass_cg_world_mm": None,
        })
    source_path = _REPO_ROOT / "src/masck_one/thermal_reset_hardware.py"
    return {
        "schema": SCHEMA,
        "owner": {"pr": OWNER_PR, "branch": OWNER_BRANCH, "head_sha": owner_head_sha},
        "world_frame_id": WORLD_FRAME_ID,
        "source": {"path": "src/masck_one/thermal_reset_hardware.py", "git_blob_sha": _blob(source_path)},
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
        },
        "energy": {
            "heater_electrical_input": None,
            "cooling_energy": None,
            "dock_reset_energy": None,
            "classification": "UNKNOWN_UNQUALIFIED_PHYSICAL_INPUTS",
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
