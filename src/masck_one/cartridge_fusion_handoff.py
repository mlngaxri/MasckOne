"""Deterministic Fusion 360 handoff for the source-bound waste-cartridge candidate."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import cadquery as cq

from .cartridge_service_corridor import build_service_corridor
from .realized_waste_cartridge import (
    AUTHORED_AGAINST_MAIN_SHA,
    CARTRIDGE_LOCAL_FRAME_ID,
    WORLD_FRAME_ID,
    build_realized_waste_cartridge,
)
from .step_integrity import verify_step_geometry

SCHEMA = "MASCK_ONE_CELL11_FUSION_HANDOFF_V1"
PREFIX = "cell11_waste_cartridge"


def _file_record(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    return {"size_bytes": len(data), "sha256": sha256(data).hexdigest()}


def _export_step(shape: cq.Workplane, path: Path) -> dict[str, object]:
    cq.exporters.export(shape, str(path))
    return verify_step_geometry(shape.val(), path)


def _component_contracts(cartridge) -> dict[str, dict[str, object]]:
    return {
        "body": {
            "fusion_component_name": "WasteCartridge_Body",
            "role": "CANDIDATE_MANUFACTURING_MATERIAL",
            "source_shape": "body",
            "joint_intent": "FIXED_TO_CLOSURE_AFTER_UNSELECTED_BOND_PROCESS",
        },
        "closure": {
            "fusion_component_name": "WasteCartridge_Closure",
            "role": "CANDIDATE_MANUFACTURING_MATERIAL",
            "source_shape": "closure",
            "joint_intent": "FIXED_TO_BODY_AFTER_UNSELECTED_BOND_PROCESS",
        },
        "left_bolt": {
            "fusion_component_name": "WasteCartridge_LeftRetentionBolt",
            "role": "CANDIDATE_MANUFACTURING_MATERIAL",
            "source_shape": "left_bolt",
            "joint_intent": "PRISMATIC_WORLD_X_TRAVEL_LIMITS_UNRESOLVED",
        },
        "right_bolt": {
            "fusion_component_name": "WasteCartridge_RightRetentionBolt",
            "role": "CANDIDATE_MANUFACTURING_MATERIAL",
            "source_shape": "right_bolt",
            "joint_intent": "PRISMATIC_WORLD_X_TRAVEL_LIMITS_UNRESOLVED",
        },
        "left_bolt_guide": {
            "fusion_component_name": "WasteCartridge_LeftBoltGuide",
            "role": "CANDIDATE_MANUFACTURING_MATERIAL",
            "source_shape": "left_bolt_guide",
            "joint_intent": "DEVICE_SIDE_FIXED_ATTACHMENT_UNRESOLVED",
        },
        "right_bolt_guide": {
            "fusion_component_name": "WasteCartridge_RightBoltGuide",
            "role": "CANDIDATE_MANUFACTURING_MATERIAL",
            "source_shape": "right_bolt_guide",
            "joint_intent": "DEVICE_SIDE_FIXED_ATTACHMENT_UNRESOLVED",
        },
        "key_tongue": {
            "fusion_component_name": "WasteCartridge_BlindKeyTongue",
            "role": "CANDIDATE_MANUFACTURING_MATERIAL",
            "source_shape": "key_tongue",
            "joint_intent": "DEVICE_SIDE_FIXED_ATTACHMENT_UNRESOLVED",
        },
    }


def fusion_handoff_manifest(cartridge=None) -> dict[str, object]:
    cartridge = cartridge or build_realized_waste_cartridge()
    cartridge.validate()
    owner = cartridge.manifest()
    service, _ = build_service_corridor(cartridge)
    components = _component_contracts(cartridge)

    return {
        "schema": SCHEMA,
        "scope": "FUSION_360_EDITABLE_DEVELOPMENT_HANDOFF_NOT_PRODUCTION_RELEASE",
        "authored_against_main_sha": AUTHORED_AGAINST_MAIN_SHA,
        "owner_schema": owner["schema"],
        "owner_producer_content_sha256": owner["producer_content_sha256"],
        "world_frame_id": WORLD_FRAME_ID,
        "local_frame_id": CARTRIDGE_LOCAL_FRAME_ID,
        "local_frame": owner["local_frame"],
        "service_datums": owner["service_datums"],
        "step_coordinate_space": "WORLD_MM",
        "step_import_rule": "ONE_STEP_FILE_PER_NAMED_FUSION_COMPONENT_KEEP_REFERENCE_BODIES_SEPARATE",
        "manufacturing_components": components,
        "references": {
            "cavity": "REFERENCE_ONLY_GEOMETRIC_FREE_SPACE_NOT_RETAINED_LIQUID",
            "seal_land": "REFERENCE_ONLY_BOND_AND_SEAL_DATUM_NO_LEAKAGE_CLAIM",
            "vent_reservation": "REFERENCE_ONLY_HARDWARE_AND_MEDIA_UNSELECTED",
            "key_channel": "REFERENCE_ONLY_BLIND_INSERTION_RESERVATION",
            "retention_pockets": "REFERENCE_ONLY_BILATERAL_RETENTION_RESERVATIONS",
            "dry_retention_reservation": "REFERENCE_ONLY_EXCLUDED_FROM_CAVITY",
            "inlet_reference": "REFERENCE_ONLY_DEVICE_SIDE_WET_HANDOFF",
            "oblique_service_enclosures": "REFERENCE_ONLY_CONSERVATIVE_MOVING_MATERIAL_ENVELOPES",
            "oblique_service_sweeps": "REFERENCE_ONLY_CONTINUOUS_TRANSLATION_SWEEPS",
        },
        "joints_and_dofs": [
            {
                "joint_id": "BODY_TO_CLOSURE",
                "type": "FIXED_INTENT",
                "physical_process": None,
                "status": "BOND_PROCESS_AND_TOLERANCE_UNSELECTED",
            },
            {
                "joint_id": "LEFT_RETENTION_BOLT",
                "type": "PRISMATIC",
                "axis_world": [-1.0, 0.0, 0.0],
                "travel_limits_mm": None,
                "status": "GEOMETRY_ONLY_CAPTURE_LOAD_AND_TRAVEL_LIMITS_UNRESOLVED",
            },
            {
                "joint_id": "RIGHT_RETENTION_BOLT",
                "type": "PRISMATIC",
                "axis_world": [1.0, 0.0, 0.0],
                "travel_limits_mm": None,
                "status": "GEOMETRY_ONLY_CAPTURE_LOAD_AND_TRAVEL_LIMITS_UNRESOLVED",
            },
            {
                "joint_id": "CARTRIDGE_SERVICE_TRANSLATION_REFERENCE",
                "type": "PRISMATIC_REFERENCE_PATH",
                "translation_world_mm": service["translation_world_mm"],
                "status": "CURRENT_MAIN_SHELL_PACKAGE_CLEAR_FRAME_AND_INTERFACES_UNRESOLVED",
            },
        ],
        "wet_interface": {
            "fluid_identity": owner["fluid_identity"],
            "route_id": owner["route_id"],
            "inlet_interface_id": owner["inlet_interface_id"],
            "route_handoff_world_mm": owner["released_route_handoff_world_mm"],
            "topology_order": [
                "WASTE_ACQUISITION",
                "WASTE_PUMP",
                "PASSIVE_BACKFLOW",
                "CARTRIDGE",
            ],
            "service_sequence_contract": [
                "MASK_REMOVED_AND_UNPOWERED",
                "WASTE_PUMP_NOT_DRIVING",
                "PASSIVE_BACKFLOW_BOUNDARY_REMAINS_UPSTREAM_OF_CARTRIDGE",
                "REMOVED_STATE_PORT_CLOSURE_MECHANISM_REQUIRED_BUT_UNRESOLVED",
                "RETENTION_RELEASE_AND_WET_DISCONNECT_ORDER_REQUIRES_PHYSICAL_VALIDATION",
            ],
            "retained_capacity_mL": None,
            "leakage_validation": None,
        },
        "service_corridor": service,
        "selected_architecture": owner["selected_architecture"],
        "superseded_selected_candidate": owner["superseded_selected_candidate"],
        "geometric_free_capacity_mL": owner["installed_geometric_free_capacity_mL"],
        "retained_capacity_mL": None,
        "development_assembly_material_eligible": False,
        "production_ready": False,
        "physical_validation_eligible": False,
    }


def export_fusion_handoff(output_dir: str | Path, cartridge=None) -> dict[str, object]:
    """Write flat, deterministic STEP assets plus a Fusion handoff manifest."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    cartridge = cartridge or build_realized_waste_cartridge()
    cartridge.validate()
    service, service_shapes = build_service_corridor(cartridge)
    manifest = fusion_handoff_manifest(cartridge)

    material_shapes = cartridge.manufacturing_components()
    reference_shapes = {**cartridge.reference_geometry(), **service_shapes}
    files: dict[str, dict[str, object]] = {}

    for name, contract in manifest["manufacturing_components"].items():
        filename = f"{PREFIX}_{name}.step"
        path = output / filename
        roundtrip = _export_step(material_shapes[contract["source_shape"]], path)
        files[filename] = {
            "classification": "CANDIDATE_MANUFACTURING_MATERIAL",
            "roundtrip": roundtrip,
            **_file_record(path),
        }

    for name in manifest["references"]:
        filename = f"{PREFIX}_{name}_REFERENCE.step"
        path = output / filename
        roundtrip = _export_step(reference_shapes[name], path)
        files[filename] = {
            "classification": "REFERENCE_ONLY_NOT_PRODUCT_MATERIAL",
            "roundtrip": roundtrip,
            **_file_record(path),
        }

    manifest["service_corridor"] = service
    manifest["files"] = files
    manifest_path = output / f"{PREFIX}_fusion_handoff.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return manifest
