from __future__ import annotations

"""Exact authority binding for the Cell 12 battery packaging benchmark.

This module preserves the controlled battery candidate identity, package dimensions,
nameplate values, mass benchmark and evidence status without promoting the reference
cell to a production selection or supplier qualification. It creates no new material.
"""

from dataclasses import dataclass
from hashlib import sha1, sha256
import json
import math
from pathlib import Path

from .authority import Authority, load_authority
from .model import MasckOneModel, build_model

SCHEMA = "MASCK_ONE_CELL12_BATTERY_BENCHMARK_BINDING_V1"
SOURCE_MAIN_SHA = "42fa11818184cde998c6df25d7c46d4fb0e4c3eb"
AUTHORITY_REVISION = "2026-08-30-R1"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
AUTHORITY_PATH = "config/masck_one_authority.yaml"
AUTHORITY_BLOB_SHA = "2608dda483b995539de422290371c219668a1527"
AUTHORITY_SCHEMA_PATH = "schemas/masck_one_authority.schema.json"
AUTHORITY_SCHEMA_BLOB_SHA = "58accbe48619058cb99ab51a0387cf01874c3717"
AUTHORITY_VALIDATOR_PATH = "src/masck_one/authority.py"
AUTHORITY_VALIDATOR_BLOB_SHA = "6866e3a428dab8b32b5a1d9e58da78b8f5aa1aa2"
MODEL_PATH = "src/masck_one/model.py"
MODEL_BLOB_SHA = "9e7fa6c71ac28cc45ebb502444bf6c0ea49f7894"
PACKAGING_ONLY_STATUS = "PACKAGING_BENCHMARK_NOT_PRODUCTION_FREEZE"
SUPPLIER_PROVENANCE_STATUS = "AUTHORITY_CANDIDATE_NAME_ONLY_NO_BOUND_SUPPLIER_DOCUMENT"
_REPO_ROOT = Path(__file__).resolve().parents[2]


class BatteryBenchmarkError(ValueError):
    pass


def _text(value: object, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise BatteryBenchmarkError(f"{label} must be exact nonblank text")
    return value


def _finite(value: object, label: str, *, positive: bool = False) -> float:
    if type(value) not in (int, float):
        raise BatteryBenchmarkError(f"{label} must be an exact numeric scalar")
    result = float(value)
    if not math.isfinite(result):
        raise BatteryBenchmarkError(f"{label} must be finite")
    if positive and result <= 0.0:
        raise BatteryBenchmarkError(f"{label} must be positive")
    return result


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def _require_sources() -> None:
    source_identities = (
        (AUTHORITY_PATH, AUTHORITY_BLOB_SHA),
        (AUTHORITY_SCHEMA_PATH, AUTHORITY_SCHEMA_BLOB_SHA),
        (AUTHORITY_VALIDATOR_PATH, AUTHORITY_VALIDATOR_BLOB_SHA),
        (MODEL_PATH, MODEL_BLOB_SHA),
    )
    for relative_path, expected in source_identities:
        path = _REPO_ROOT / relative_path
        if not path.is_file():
            raise BatteryBenchmarkError(f"battery benchmark source missing: {relative_path}")
        actual = _git_blob_sha(path)
        if actual != expected:
            raise BatteryBenchmarkError(
                f"battery benchmark source moved at {relative_path}; expected {expected}, got {actual}"
            )


@dataclass(frozen=True, slots=True)
class BatteryBenchmarkBinding:
    candidate: str
    envelope_mm: tuple[float, float, float]
    nominal_voltage_V: float
    capacity_mAh: float
    mass_g: float
    status: str
    model_component_status: str
    model_component_spans_mm: tuple[float, float, float]
    production_selected: bool = False
    supplier_document_bound: bool = False
    physical_validation_complete: bool = False

    def __post_init__(self) -> None:
        _text(self.candidate, "battery candidate")
        if type(self.envelope_mm) is not tuple or len(self.envelope_mm) != 3:
            raise BatteryBenchmarkError("battery envelope must be an exact XYZ tuple")
        if type(self.model_component_spans_mm) is not tuple or len(self.model_component_spans_mm) != 3:
            raise BatteryBenchmarkError("model battery spans must be an exact XYZ tuple")
        for index, value in enumerate(self.envelope_mm):
            _finite(value, f"battery envelope[{index}]", positive=True)
        for index, value in enumerate(self.model_component_spans_mm):
            _finite(value, f"model battery span[{index}]", positive=True)
        _finite(self.nominal_voltage_V, "battery nominal voltage", positive=True)
        _finite(self.capacity_mAh, "battery capacity", positive=True)
        _finite(self.mass_g, "battery mass", positive=True)
        if self.status != PACKAGING_ONLY_STATUS or self.model_component_status != PACKAGING_ONLY_STATUS:
            raise BatteryBenchmarkError("battery benchmark status drifted from packaging-only authority")
        if self.production_selected or self.supplier_document_bound or self.physical_validation_complete:
            raise BatteryBenchmarkError("battery benchmark cannot be promoted without controlled evidence")
        for expected, actual in zip(self.envelope_mm, self.model_component_spans_mm, strict=True):
            if not math.isclose(expected, actual, rel_tol=0.0, abs_tol=5e-6):
                raise BatteryBenchmarkError("model battery package geometry differs from authority envelope")

    @property
    def binding_sha256(self) -> str:
        raw = json.dumps(self.manifest(False), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        return sha256(raw).hexdigest()

    def manifest(self, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "authority_revision": AUTHORITY_REVISION,
            "world_frame_id": WORLD_FRAME_ID,
            "sources": {
                "main_sha": SOURCE_MAIN_SHA,
                "authority_path": AUTHORITY_PATH,
                "authority_git_blob_sha": AUTHORITY_BLOB_SHA,
                "authority_field_path": "battery_reference",
                "authority_schema_path": AUTHORITY_SCHEMA_PATH,
                "authority_schema_git_blob_sha": AUTHORITY_SCHEMA_BLOB_SHA,
                "authority_validator_path": AUTHORITY_VALIDATOR_PATH,
                "authority_validator_git_blob_sha": AUTHORITY_VALIDATOR_BLOB_SHA,
                "model_path": MODEL_PATH,
                "model_git_blob_sha": MODEL_BLOB_SHA,
            },
            "benchmark": {
                "candidate": self.candidate,
                "envelope_mm": list(self.envelope_mm),
                "nominal_voltage_V": self.nominal_voltage_V,
                "capacity_mAh": self.capacity_mAh,
                "mass_g": self.mass_g,
                "status": self.status,
                "geometry_role": "REFERENCE_ONLY_PACKAGING_BENCHMARK",
            },
            "model_binding": {
                "component_id": "battery_reference_envelope",
                "component_status": self.model_component_status,
                "measured_brep_spans_mm": list(self.model_component_spans_mm),
                "matches_authority_envelope": True,
            },
            "supplier_provenance": {
                "candidate_identity_source": "MACHINE_AUTHORITY_BATTERY_REFERENCE_CANDIDATE",
                "candidate": self.candidate,
                "status": SUPPLIER_PROVENANCE_STATUS,
                "supplier_document_url": None,
                "supplier_document_sha256": None,
                "supplier_document_bound": self.supplier_document_bound,
            },
            "evidence_firewall": {
                "packaging_only": True,
                "production_selected": self.production_selected,
                "supplier_qualified": False,
                "physical_validation_complete": self.physical_validation_complete,
                "runtime_validated": False,
                "electrical_safety_validated": False,
                "swelling_abuse_clearance_validated": False,
            },
        }
        if include_sha:
            payload["binding_sha256"] = self.binding_sha256
        return payload


def build_battery_benchmark_binding(
    authority: Authority | None = None,
    model: MasckOneModel | None = None,
) -> BatteryBenchmarkBinding:
    _require_sources()
    authority = authority or load_authority()
    if type(authority) is not Authority:
        raise BatteryBenchmarkError("battery benchmark requires exact Authority type")
    canonical = load_authority()
    if authority.data != canonical.data:
        raise BatteryBenchmarkError("supplied authority differs from released machine authority")
    if str(authority.get("project", "authority_revision")) != AUTHORITY_REVISION:
        raise BatteryBenchmarkError("battery benchmark authority revision moved")

    model = model or build_model(authority)
    if type(model) is not MasckOneModel or model.authority.data != authority.data:
        raise BatteryBenchmarkError("battery benchmark requires current exact-authority model")

    envelope = tuple(float(value) for value in authority.get("battery_reference", "envelope_mm"))
    if len(envelope) != 3:
        raise BatteryBenchmarkError("authority battery envelope must contain exactly three dimensions")
    bb = model.battery_reference_envelope.solid.val().BoundingBox()
    spans = (float(bb.xlen), float(bb.ylen), float(bb.zlen))

    return BatteryBenchmarkBinding(
        candidate=str(authority.get("battery_reference", "candidate")),
        envelope_mm=envelope,
        nominal_voltage_V=float(authority.get("battery_reference", "nominal_voltage_V")),
        capacity_mAh=float(authority.get("battery_reference", "capacity_mAh")),
        mass_g=float(authority.get("battery_reference", "mass_g")),
        status=str(authority.get("battery_reference", "status")),
        model_component_status=model.battery_reference_envelope.status,
        model_component_spans_mm=spans,
    )


if __name__ == "__main__":
    print(json.dumps(build_battery_benchmark_binding().manifest(), indent=2))
