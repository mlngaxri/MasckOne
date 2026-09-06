from __future__ import annotations

"""Current-main release wrapper for whole-product collision truth.

The geometric core owns exact/protected/conservative measurements. This wrapper owns
current-main source completeness: it binds the producer graph that can alter those
measurements and appends explicit BLOCKED rows for physically relevant package/material
geometry that current main does not yet provide. Missing geometry therefore cannot be
mistaken for collision clearance.
"""

from dataclasses import dataclass, replace
from hashlib import sha1, sha256
import json
from pathlib import Path

from .model import MasckOneModel
from .whole_product_collision_matrix import (
    AUTHORITY_REVISION,
    BLOCKED,
    DIGITAL_ONLY,
    METHOD_UNRESOLVED,
    ROW_BLOCKED,
    SOURCE_MAIN_SHA,
    WORLD_FRAME_ID,
    CollisionCheck,
    UnresolvedInterface,
    WholeProductCollisionMatrix,
    WholeProductCollisionMatrixError,
    build_whole_product_collision_matrix,
)

SCHEMA = "MASCK_ONE_WHOLE_PRODUCT_COLLISION_RELEASE_V1"
_REPO_ROOT = Path(__file__).resolve().parents[2]

# Every current-main producer capable of changing a consumed finite B-rep, protected
# hard envelope, worn-pose screen, released mixed-waste route reservation, or an
# explicit package-geometry blocker. These are Git blob IDs, not content SHA-256s.
PRODUCER_BLOBS = (
    ("config/masck_one_authority.yaml", "2608dda483b995539de422290371c219668a1527"),
    ("src/masck_one/authority.py", "6866e3a428dab8b32b5a1d9e58da78b8f5aa1aa2"),
    ("src/masck_one/spatial.py", "8c1106b523fef5111009cc56236a53e3bc5ee10e"),
    ("src/masck_one/anatomy.py", "872d1e5be1b9ce9baa5b63cb53462eb7b36f40ab"),
    ("src/masck_one/facial_surface.py", "764f6f65b83ac7709d959bb0f37f861c90ea2794"),
    ("src/masck_one/coverage.py", "4a8cec4d94db97e63f634a94dd8c90094f3afcb0"),
    ("src/masck_one/interface_topology.py", "38b7c932f71a8675d45d098ac65154f98ff8bbb5"),
    ("src/masck_one/interface_boundaries.py", "496c9b50867ca0bb319175d1d2e47caf4bc4fb64"),
    ("src/masck_one/nasal_subsystem.py", "f1f22b828d0465636579fc31eff0bfb6a6bf2507"),
    ("src/masck_one/protected_volumes.py", "ff2b9b288559f9b268e5d08a1d6c78335f745cf1"),
    ("src/masck_one/worn_pose.py", "9d4ed65246fbc92ac577ce38bceb95cd2253607b"),
    ("src/masck_one/model.py", "9e7fa6c71ac28cc45ebb502444bf6c0ea49f7894"),
    ("src/masck_one/actuator_frames.py", "4c2013f994bdc9e084fe227eb5e166f973500ebb"),
    ("src/masck_one/actuator_coupling.py", "d56160304190c030e3bc389803eaa456aaab5af0"),
    ("src/masck_one/boundary_release.py", "34a49eed2c521d55e48ac187c2dd33dc9e22a3e3"),
    ("src/masck_one/interface_attachment.py", "c161f99ddd3473f3b9dde30ec73397a72915191a"),
    ("src/masck_one/structural_frame.py", "bda5ba87d232c0e6a22e200975a80414a10c9a83"),
    ("src/masck_one/water_reservoir.py", "6c14a37d07855550f0bd502e8308ed46682bc19c"),
    ("src/masck_one/cleanser_storage.py", "5e087ca8b05da8352ad4800b2ef8280ea8ddcf29"),
    ("src/masck_one/fresh_pump_packaging.py", "40cb6fb4c3efbfcf25ed0b7d7a75a4269d90a1b4"),
    ("src/masck_one/distribution_manifold.py", "8f2a6c784b51734aba4d1f3809015707fc328405"),
    ("src/masck_one/distribution_geometry.py", "d2dd8b47bb6a2aa1edf57ac0632778228add7997"),
    ("src/masck_one/waste_acquisition.py", "7108fcfbe2baeaa9a343199a6817122ac2aea7ab"),
    ("src/masck_one/waste_pump_architecture.py", "ace02ee529070465b11832f475771125636312cb"),
    ("src/masck_one/realized_waste_backbone.py", "6aa79d9a613e278f32da85b4654c0e35cc09b7ca"),
    ("src/masck_one/realized_waste_backbone_release.py", "86f2b12d8721ce0fb233d7b026aed3154de9c964"),
    ("src/masck_one/waste_cartridge_dfm.py", "f9788cce30c14600c8a624509153596e46c1e478"),
)

# These are omitted physical/package geometries proven unresolved by released current
# main. They are collision rows, not requests to invent the missing subsystem design.
ADDITIONAL_BLOCKERS = (
    (
        "STRUCTURAL_FRAME_MATERIAL_AND_SHELL_JOIN_GEOMETRY",
        "structural frame and shell-frame join",
        ("rigid shell", "actuators", "retention", "wet routes", "dry package", "service paths"),
        "released structural frame is topology/datum only; no member cross-section, material B-rep or shell-frame join B-rep exists",
    ),
    (
        "NASAL_INTERFACE_FINAL_MATERIAL_ATTACHMENT_AND_SERVICE_GEOMETRY",
        "nasal compliant interface",
        ("shell", "protected nostrils/airway", "fresh distribution", "waste acquisition", "service/removal"),
        "current nasal lobe solid is a development local-thickness reference, not released final material/attachment/service geometry",
    ),
    (
        "WATER_RESERVOIR_REALIZED_BODY_PORT_SEAL_AND_SERVICE_GEOMETRY",
        "fresh-water storage",
        ("shell", "frame", "fresh pump", "harness", "fill/service motion"),
        "current model supplies a controlled reservoir package envelope but not realized body, port, seal, retention or service B-reps",
    ),
    (
        "CLEANSER_STORAGE_BODY_PORT_AND_SERVICE_GEOMETRY",
        "cleanser storage",
        ("shell", "frame", "cleanser pump", "harness", "refill/purge/service motion"),
        "released cleanser architecture deliberately has no controlled storage capacity or body/port/service geometry",
    ),
    (
        "FRESH_WATER_PUMP_PACKAGE_PLACEMENT_AND_SERVICE_GEOMETRY",
        "fresh-water pump",
        ("frame", "shell", "water storage", "fresh routes", "harness", "service motion"),
        "released water pump station has no selected package, envelope, placement, orientation, connectors or service B-rep",
    ),
    (
        "CLEANSER_PUMP_PACKAGE_PLACEMENT_AND_SERVICE_GEOMETRY",
        "cleanser pump",
        ("frame", "shell", "cleanser storage", "fresh routes", "harness", "service motion"),
        "released cleanser pump station has no selected package, envelope, placement, orientation, connectors or service B-rep",
    ),
    (
        "WASTE_PUMP_PACKAGE_PLACEMENT_AND_SERVICE_GEOMETRY",
        "mixed-waste pump",
        ("frame", "shell", "mixed-waste routes", "harness", "cartridge", "service motion"),
        "released mixed-waste pump station explicitly has package candidate, envelope, placement and service geometry unresolved",
    ),
    (
        "PASSIVE_BACKFLOW_PACKAGE_PLACEMENT_AND_SERVICE_GEOMETRY",
        "passive backflow protection",
        ("frame", "shell", "mixed-waste routes", "waste pump", "cartridge", "service motion"),
        "released passive-backflow stage is topology/evidence status only; selected component package and placement geometry are unresolved",
    ),
    (
        "WASTE_CARTRIDGE_REALIZED_BODY_CAVITY_SEAL_AND_RETENTION_GEOMETRY",
        "waste cartridge",
        ("shell", "frame", "mixed-waste route", "retention", "service motion"),
        "merged cartridge DFM gate confirms package proxy only; body, cavity, seal, positive retention and realized service geometry are unresolved",
    ),
    (
        "BATTERY_REALIZED_PACKAGE_RETENTION_AND_SERVICE_GEOMETRY",
        "battery package",
        ("shell", "frame", "PCB/charging", "harness", "service motion"),
        "current battery solid is a packaging benchmark reference, not released battery retention, connector or service geometry",
    ),
    (
        "PCB_CHARGING_DRY_BAY_AND_CONNECTOR_GEOMETRY",
        "PCB, charging and dry bay",
        ("shell", "frame", "battery", "harness", "wet/dry bulkhead", "service motion"),
        "current main has no released PCB, charging, dry-bay enclosure or connector B-reps for collision closure",
    ),
    (
        "WARM_THERMAL_HARDWARE_AND_CLEARANCE_GEOMETRY",
        "WARM thermal hardware",
        ("shell", "protected regions", "wet routes", "harness", "battery/PCB", "user-access surfaces"),
        "current main has no released WARM heater/sensor/spreader/insulation package B-reps or thermal service clearance geometry",
    ),
)


def _git_blob_sha(path: Path) -> str:
    payload = path.read_bytes()
    return sha1(f"blob {len(payload)}\0".encode("ascii") + payload).hexdigest()


def _require_current_producer_blobs() -> None:
    for relative_path, expected in PRODUCER_BLOBS:
        path = _REPO_ROOT / relative_path
        if not path.is_file():
            raise WholeProductCollisionMatrixError(
                f"collision release producer is missing: {relative_path}"
            )
        actual = _git_blob_sha(path)
        if actual != expected:
            raise WholeProductCollisionMatrixError(
                f"collision release producer moved at {relative_path}; expected {expected}, got {actual}"
            )


def _additional_rows() -> tuple[CollisionCheck, ...]:
    return tuple(
        CollisionCheck(
            f"BLOCKED::{interface_id}::CURRENT_MAIN_RELEASE",
            ROW_BLOCKED,
            interface_id,
            "CURRENT_MAIN",
            METHOD_UNRESOLVED,
            BLOCKED,
            None,
            None,
            blocker,
        )
        for interface_id, _, _, blocker in ADDITIONAL_BLOCKERS
    )


def _additional_interfaces() -> tuple[UnresolvedInterface, ...]:
    return tuple(
        UnresolvedInterface(interface_id, subsystem, required_against, blocker)
        for interface_id, subsystem, required_against, blocker in ADDITIONAL_BLOCKERS
    )


@dataclass(frozen=True, slots=True)
class WholeProductCollisionRelease:
    matrix: WholeProductCollisionMatrix
    source_main_sha: str = SOURCE_MAIN_SHA
    authority_revision: str = AUTHORITY_REVISION
    world_frame_id: str = WORLD_FRAME_ID
    producer_blobs: tuple[tuple[str, str], ...] = PRODUCER_BLOBS
    evidence_status: str = DIGITAL_ONLY
    physical_validation_eligible: bool = False

    def validate(self) -> None:
        if self.source_main_sha != SOURCE_MAIN_SHA:
            raise WholeProductCollisionMatrixError("collision release source main moved")
        if self.authority_revision != AUTHORITY_REVISION or self.world_frame_id != WORLD_FRAME_ID:
            raise WholeProductCollisionMatrixError("collision release authority/frame moved")
        if self.producer_blobs != PRODUCER_BLOBS:
            raise WholeProductCollisionMatrixError("collision release producer binding was altered")
        _require_current_producer_blobs()
        self.matrix.validate()
        required = {item[0] for item in ADDITIONAL_BLOCKERS}
        present = {item.interface_id for item in self.matrix.unresolved_interfaces}
        if not required.issubset(present):
            raise WholeProductCollisionMatrixError("collision release silently lost a current-main blocker")
        if self.evidence_status != DIGITAL_ONLY:
            raise WholeProductCollisionMatrixError("collision release evidence firewall changed")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise WholeProductCollisionMatrixError("collision release cannot become physical evidence")

    @property
    def release_sha256(self) -> str:
        payload = self.manifest(include_sha=False)
        return sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        ).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        self.validate()
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "source_main_sha": self.source_main_sha,
            "authority_revision": self.authority_revision,
            "world_frame_id": self.world_frame_id,
            "producer_blobs": [list(item) for item in self.producer_blobs],
            "matrix": self.matrix.manifest(),
            "row_class_counts": self.matrix.row_class_counts,
            "row_count": len(self.matrix.checks),
            "blocked_count": self.matrix.blocked_count,
            "matrix_status": self.matrix.matrix_status,
            "physical_validation_eligible": False,
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            payload["release_sha256"] = sha256(
                json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
            ).hexdigest()
        return payload


def build_current_main_collision_release(
    model: MasckOneModel | None = None,
) -> WholeProductCollisionRelease:
    _require_current_producer_blobs()
    core = build_whole_product_collision_matrix(model)
    existing_ids = {item.interface_id for item in core.unresolved_interfaces}
    duplicates = existing_ids.intersection(item[0] for item in ADDITIONAL_BLOCKERS)
    if duplicates:
        raise WholeProductCollisionMatrixError(
            f"collision release blocker duplicated core ownership: {sorted(duplicates)!r}"
        )
    matrix = replace(
        core,
        checks=core.checks + _additional_rows(),
        unresolved_interfaces=core.unresolved_interfaces + _additional_interfaces(),
    )
    matrix.validate()
    release = WholeProductCollisionRelease(matrix)
    release.validate()
    return release
