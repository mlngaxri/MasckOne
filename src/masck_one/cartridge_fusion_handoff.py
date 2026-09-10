"""Deterministic Fusion 360 handoff for the source-bound waste-cartridge service package."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import cadquery as cq

from .cartridge_device_service import build_cartridge_device_service
from .cartridge_service_corridor import build_service_corridor
from .cartridge_tactile_service import build_cartridge_tactile_service
from .realized_waste_cartridge import (
    AUTHORED_AGAINST_MAIN_SHA,
    CARTRIDGE_LOCAL_FRAME_ID,
    WORLD_FRAME_ID,
    build_realized_waste_cartridge,
)
from .step_integrity import verify_step_geometry

SCHEMA = "MASCK_ONE_CELL11_FUSION_HANDOFF_V2"
PREFIX = "cell11_waste_cartridge"


def _file_record(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    return {"size_bytes": len(data), "sha256": sha256(data).hexdigest()}


def _export_step(shape: cq.Workplane, path: Path) -> dict[str, object]:
    cq.exporters.export(shape, str(path))
    return verify_step_geometry(shape.val(), path)


def _solid_bounds_key(shape: cq.Shape) -> tuple[float, ...]:
    bb = shape.BoundingBox()
    return (
        round(float(bb.zmin), 9),
        round(float(bb.zmax), 9),
        round(float(bb.ymin), 9),
        round(float(bb.ymax), 9),
        round(float(bb.xmin), 9),
        round(float(bb.xmax), 9),
    )


def _pad_shapes(tactile) -> dict[str, cq.Workplane]:
    solids = list(tactile.key_pad_free_regions.val().Solids())
    if len(solids) != 3:
        raise ValueError("key take-up source must contain exactly three free-state pad solids")

    def center(solid):
        bb = solid.BoundingBox()
        return (
            (float(bb.xmin) + float(bb.xmax)) / 2.0,
            (float(bb.ymin) + float(bb.ymax)) / 2.0,
            (float(bb.zmin) + float(bb.zmax)) / 2.0,
        )

    posterior = min(solids, key=lambda solid: center(solid)[2])
    side = [solid for solid in solids if solid is not posterior]
    if len(side) != 2:
        raise ValueError("key take-up side-pad partition failed")
    inferior = min(side, key=lambda solid: center(solid)[1])
    superior = max(side, key=lambda solid: center(solid)[1])
    return {
        "key_takeup_pad_inferior_y": cq.Workplane(obj=inferior),
        "key_takeup_pad_superior_y": cq.Workplane(obj=superior),
        "key_takeup_pad_posterior_z": cq.Workplane(obj=posterior),
    }


def _material_shapes(cartridge, tactile, device) -> dict[str, cq.Workplane]:
    shapes = {
        "body": cartridge.body_solid,
        "closure": tactile.closure_with_pad_root_pockets,
        **_pad_shapes(tactile),
        "device_receiver": device.receiver,
        "release_shuttle": device.shuttle_locked,
        "left_bolt_drive": device.left_locked,
        "right_bolt_drive": device.right_locked,
        "floating_wet_nose_drive": device.wet_locked,
        "wet_poppet_free_region": device.poppet_free,
    }
    if len(shapes) != len(set(shapes)):
        raise ValueError("duplicate manufacturing component identity")
    return shapes


def _component_contracts() -> dict[str, dict[str, object]]:
    fixed = "CANDIDATE_MANUFACTURING_MATERIAL"
    return {
        "body": {
            "fusion_component_name": "WasteCartridge_Body",
            "role": fixed,
            "source_shape": "body",
            "joint_intent": "FIXED_TO_CLOSURE_AFTER_UNSELECTED_BOND_PROCESS",
        },
        "closure": {
            "fusion_component_name": "WasteCartridge_Closure_WithKeyPadRoots",
            "role": fixed,
            "source_shape": "closure",
            "joint_intent": "FIXED_TO_BODY_AFTER_UNSELECTED_BOND_PROCESS",
        },
        "key_takeup_pad_inferior_y": {
            "fusion_component_name": "WasteCartridge_KeyTakeupPad_InferiorY",
            "role": fixed,
            "source_shape": "key_takeup_pad_inferior_y",
            "joint_intent": "COMPLIANT_ROOTED_OVERMOLD_INTENT_PHYSICAL_FORCE_UNVALIDATED",
        },
        "key_takeup_pad_superior_y": {
            "fusion_component_name": "WasteCartridge_KeyTakeupPad_SuperiorY",
            "role": fixed,
            "source_shape": "key_takeup_pad_superior_y",
            "joint_intent": "COMPLIANT_ROOTED_OVERMOLD_INTENT_PHYSICAL_FORCE_UNVALIDATED",
        },
        "key_takeup_pad_posterior_z": {
            "fusion_component_name": "WasteCartridge_KeyTakeupPad_PosteriorZ",
            "role": fixed,
            "source_shape": "key_takeup_pad_posterior_z",
            "joint_intent": "COMPLIANT_ROOTED_OVERMOLD_INTENT_PHYSICAL_FORCE_UNVALIDATED",
        },
        "device_receiver": {
            "fusion_component_name": "Device_CartridgeReceiver",
            "role": fixed,
            "source_shape": "device_receiver",
            "joint_intent": "FIXED_TO_FRAME_COUNTERPART_NOT_RELEASED",
            "contains_canonical_subgeometry": ["left_bolt_guide", "right_bolt_guide", "key_tongue"],
        },
        "release_shuttle": {
            "fusion_component_name": "Device_CartridgeReleaseShuttle",
            "role": fixed,
            "source_shape": "release_shuttle",
            "joint_intent": "PRISMATIC_WORLD_POSITIVE_Y_4P0MM_CAM_DRIVER",
        },
        "left_bolt_drive": {
            "fusion_component_name": "Device_LeftRetentionBoltDrive",
            "role": fixed,
            "source_shape": "left_bolt_drive",
            "joint_intent": "CAM_DRIVEN_PRISMATIC_WORLD_NEGATIVE_X_1P60MM",
            "contains_canonical_subgeometry": ["left_bolt"],
        },
        "right_bolt_drive": {
            "fusion_component_name": "Device_RightRetentionBoltDrive",
            "role": fixed,
            "source_shape": "right_bolt_drive",
            "joint_intent": "CAM_DRIVEN_PRISMATIC_WORLD_POSITIVE_X_1P60MM",
            "contains_canonical_subgeometry": ["right_bolt"],
        },
        "floating_wet_nose_drive": {
            "fusion_component_name": "Device_FloatingWasteWetNoseDrive",
            "role": fixed,
            "source_shape": "floating_wet_nose_drive",
            "joint_intent": "CAM_DRIVEN_PRISMATIC_WORLD_NEGATIVE_X_1P40MM",
        },
        "wet_poppet_free_region": {
            "fusion_component_name": "Device_WastePortPoppet_FreeStateSource",
            "role": fixed,
            "source_shape": "wet_poppet_free_region",
            "joint_intent": "COMPLIANT_PASSIVE_CLOSURE_SOURCE_GEOMETRY_NOT_ASSEMBLED_RIGID_STATE",
        },
    }


def _reference_contracts() -> dict[str, str]:
    return {
        "cavity": "REFERENCE_ONLY_GEOMETRIC_FREE_SPACE_NOT_RETAINED_LIQUID",
        "seal_land": "REFERENCE_ONLY_BOND_AND_SEAL_DATUM_NO_LEAKAGE_CLAIM",
        "vent_reservation": "REFERENCE_ONLY_HARDWARE_AND_MEDIA_UNSELECTED",
        "key_channel": "REFERENCE_ONLY_BLIND_INSERTION_RESERVATION",
        "retention_pockets": "REFERENCE_ONLY_BILATERAL_RETENTION_RESERVATIONS",
        "dry_retention_reservation": "REFERENCE_ONLY_EXCLUDED_FROM_CAVITY",
        "inlet_reference": "REFERENCE_ONLY_DEVICE_SIDE_WET_HANDOFF",
        "oblique_service_enclosures": "REFERENCE_ONLY_CONSERVATIVE_MOVING_MATERIAL_ENVELOPES",
        "oblique_service_sweeps": "REFERENCE_ONLY_CONTINUOUS_TRANSLATION_SWEEPS",
        "key_takeup_installed": "REFERENCE_ONLY_DEFORMED_KEY_PAD_STATE_NO_FORCE_PREDICTION",
        "release_shuttle_service": "REFERENCE_ONLY_SHUTTLE_SERVICE_POSE",
        "left_bolt_drive_service": "REFERENCE_ONLY_LEFT_BOLT_RETRACTED_POSE",
        "right_bolt_drive_service": "REFERENCE_ONLY_RIGHT_BOLT_RETRACTED_POSE",
        "floating_wet_nose_service": "REFERENCE_ONLY_WET_NOSE_RETRACTED_POSE",
        "poppet_closed_service": "REFERENCE_ONLY_COMPLIANT_REMOVED_STATE_CLOSURE_POSE",
        "poppet_open_locked": "REFERENCE_ONLY_COMPLIANT_INSTALLED_OPEN_POSE",
        "frame_mount_reference": "REFERENCE_ONLY_FRAME_INTERFACE_FEET_NO_FRAME_COUNTERPART_PROMOTION",
    }


def fusion_handoff_manifest(cartridge=None, *, service_report=None, tactile=None, device=None) -> dict[str, object]:
    cartridge = cartridge or build_realized_waste_cartridge()
    cartridge.validate()
    tactile = tactile or build_cartridge_tactile_service(cartridge)
    device = device or build_cartridge_device_service()
    owner = cartridge.manifest()
    service = service_report
    if service is None:
        service, _ = build_service_corridor(cartridge)

    components = _component_contracts()
    material_shapes = _material_shapes(cartridge, tactile, device)
    if set(components) != set(material_shapes):
        raise ValueError("Fusion manufacturing contract no longer matches source material set")

    legacy_duplicate_parts = {
        "left_bolt",
        "right_bolt",
        "left_bolt_guide",
        "right_bolt_guide",
        "key_tongue",
    }
    if legacy_duplicate_parts & set(components):
        raise ValueError("nested canonical bolt/guide/key geometry cannot be exported twice")

    device_manifest = device.manifest()
    return {
        "schema": SCHEMA,
        "scope": "FUSION_360_EDITABLE_DEVELOPMENT_HANDOFF_NOT_PRODUCTION_RELEASE",
        "authored_against_main_sha": AUTHORED_AGAINST_MAIN_SHA,
        "owner_schema": owner["schema"],
        "owner_producer_content_sha256": owner["producer_content_sha256"],
        "device_service_schema": device_manifest["schema"],
        "device_service_manifest_sha256": device_manifest["manifest_sha256"],
        "world_frame_id": WORLD_FRAME_ID,
        "local_frame_id": CARTRIDGE_LOCAL_FRAME_ID,
        "local_frame": owner["local_frame"],
        "service_datums": owner["service_datums"],
        "step_coordinate_space": "WORLD_MM",
        "step_import_rule": "ONE_STEP_FILE_PER_NAMED_FUSION_COMPONENT_KEEP_REFERENCE_BODIES_SEPARATE",
        "material_assembly_rule": (
            "NESTED_BOLT_GUIDE_KEY_SUBGEOMETRY_EXPORTS_ONLY_INSIDE_SELECTED_SERVICE_COMPONENTS;"
            "NO_DUPLICATE_PHYSICAL_MATERIAL"
        ),
        "reference_partition_rule": (
            "MULTI_SOLID_REFERENCE_COMPOUNDS_EXPORT_AS_DETERMINISTIC_ONE_SOLID_STEP_PARTS; "
            "GLOBAL_STEP_POSITION_VOLUME_AND_MATERIAL_LIMITS_UNCHANGED"
        ),
        "manufacturing_components": components,
        "references": _reference_contracts(),
        "joints_and_dofs": [
            {
                "joint_id": "BODY_TO_CLOSURE",
                "type": "FIXED_INTENT",
                "physical_process": None,
                "status": "BOND_PROCESS_AND_TOLERANCE_UNSELECTED",
            },
            {
                "joint_id": "KEY_TAKEUP_PADS",
                "type": "COMPLIANT_FIXED_ROOT_INTENT",
                "status": "FREE_AND_DEFORMED_GEOMETRY_SEPARATE_FORCE_MATERIAL_WEAR_UNVALIDATED",
            },
            {
                "joint_id": "RELEASE_SHUTTLE",
                "type": "PRISMATIC",
                "axis_world": [0.0, 1.0, 0.0],
                "travel_limits_mm": [0.0, 4.0],
                "status": "ANALYTIC_CAM_CENTERLINE_COUPLING_REALIZED_FORCE_FRICTION_WEAR_UNVALIDATED",
            },
            {
                "joint_id": "LEFT_RETENTION_BOLT_DRIVE",
                "type": "CAM_DRIVEN_PRISMATIC",
                "axis_world": [-1.0, 0.0, 0.0],
                "retraction_mm": 1.60,
                "status": "DRIVEN_BY_RELEASE_SHUTTLE_ANALYTIC_CENTERLINE_COUPLING",
            },
            {
                "joint_id": "RIGHT_RETENTION_BOLT_DRIVE",
                "type": "CAM_DRIVEN_PRISMATIC",
                "axis_world": [1.0, 0.0, 0.0],
                "retraction_mm": 1.60,
                "status": "DRIVEN_BY_RELEASE_SHUTTLE_ANALYTIC_CENTERLINE_COUPLING",
            },
            {
                "joint_id": "FLOATING_WET_NOSE_DRIVE",
                "type": "CAM_DRIVEN_PRISMATIC",
                "axis_world": [-1.0, 0.0, 0.0],
                "retraction_mm": 1.40,
                "status": "RETRACTS_BEFORE_CARTRIDGE_TRANSLATION_LEAKAGE_FORCE_UNVALIDATED",
            },
            {
                "joint_id": "REMOVED_STATE_POPPET",
                "type": "COMPLIANT_PASSIVE_INTENT",
                "status": "FREE_OPEN_CLOSED_GEOMETRY_SEPARATE_CLOSING_FORCE_LEAKAGE_UNVALIDATED",
            },
            {
                "joint_id": "CARTRIDGE_SERVICE_TRANSLATION_REFERENCE",
                "type": "PRISMATIC_REFERENCE_PATH",
                "translation_world_mm": service["translation_world_mm"],
                "status": "RELEASED_SHELL_PACKAGE_CLEAR_FRAME_EXTERIOR_WHOLE_DEVICE_PROOF_OPEN",
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
                "RELEASE_SHUTTLE_RETRACTS_BOTH_BOLTS_AND_FLOATING_WET_NOSE",
                "PASSIVE_POPPET_REMOVED_STATE_CLOSURE_GEOMETRY_SEED",
                "ONLY_THEN_OBLIQUE_CARTRIDGE_TRANSLATION",
            ],
            "removed_state_port_closure_geometry_realized": True,
            "retained_capacity_mL": None,
            "leakage_validation": None,
            "backflow_validation": None,
            "service_force_validation": None,
        },
        "service_corridor": service,
        "selected_architecture": owner["selected_architecture"],
        "selected_device_service_architecture": device_manifest["selected_architecture"],
        "superseded_selected_candidate": owner["superseded_selected_candidate"],
        "geometric_free_capacity_mL": owner["installed_geometric_free_capacity_mL"],
        "retained_capacity_mL": None,
        "development_assembly_material_eligible": False,
        "production_ready": False,
        "physical_validation_eligible": False,
        "remaining_integration_blockers": device_manifest["remaining_integration_blockers"],
    }


def export_fusion_handoff(output_dir: str | Path, cartridge=None) -> dict[str, object]:
    """Write deterministic service-package STEP assets plus a Fusion handoff manifest."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    cartridge = cartridge or build_realized_waste_cartridge()
    cartridge.validate()
    tactile = build_cartridge_tactile_service(cartridge)
    service, service_shapes = build_service_corridor(cartridge)
    device = build_cartridge_device_service()
    manifest = fusion_handoff_manifest(
        cartridge,
        service_report=service,
        tactile=tactile,
        device=device,
    )

    material_shapes = _material_shapes(cartridge, tactile, device)
    reference_shapes = {
        **cartridge.reference_geometry(),
        **service_shapes,
        "key_takeup_installed": tactile.key_pad_installed_reference,
        "release_shuttle_service": device.shuttle_service,
        "left_bolt_drive_service": device.left_service,
        "right_bolt_drive_service": device.right_service,
        "floating_wet_nose_service": device.wet_service,
        "poppet_closed_service": device.poppet_closed_service,
        "poppet_open_locked": device.poppet_open_locked,
        "frame_mount_reference": device.frame_mount_reference,
    }
    files: dict[str, dict[str, object]] = {}
    reference_export_partitions: dict[str, int] = {}

    for name, contract in manifest["manufacturing_components"].items():
        filename = f"{PREFIX}_{name}.step"
        path = output / filename
        roundtrip = _export_step(material_shapes[contract["source_shape"]], path)
        files[filename] = {
            "classification": "CANDIDATE_MANUFACTURING_MATERIAL",
            "assembly_state": (
                "FREE_SOURCE_GEOMETRY_NOT_RIGID_ASSEMBLED_STATE"
                if name == "wet_poppet_free_region"
                else "SELECTED_NOMINAL_SOURCE_STATE"
            ),
            "roundtrip": roundtrip,
            **_file_record(path),
        }

    for name in manifest["references"]:
        shape = reference_shapes[name]
        solids = sorted(shape.val().Solids(), key=_solid_bounds_key)
        if not solids:
            raise ValueError(f"reference {name} contains no solids")
        reference_export_partitions[name] = len(solids)

        if len(solids) == 1:
            filename = f"{PREFIX}_{name}_REFERENCE.step"
            path = output / filename
            roundtrip = _export_step(cq.Workplane(obj=solids[0]), path)
            files[filename] = {
                "classification": "REFERENCE_ONLY_NOT_PRODUCT_MATERIAL",
                "reference_group": name,
                "source_solid_index": 0,
                "roundtrip": roundtrip,
                **_file_record(path),
            }
            continue

        for index, solid in enumerate(solids, start=1):
            filename = f"{PREFIX}_{name}_{index:02d}_REFERENCE.step"
            path = output / filename
            roundtrip = _export_step(cq.Workplane(obj=solid), path)
            files[filename] = {
                "classification": "REFERENCE_ONLY_NOT_PRODUCT_MATERIAL",
                "reference_group": name,
                "source_solid_index": index - 1,
                "roundtrip": roundtrip,
                **_file_record(path),
            }

    manifest["service_corridor"] = service
    manifest["reference_export_partitions"] = reference_export_partitions
    manifest["files"] = files
    manifest_path = output / f"{PREFIX}_fusion_handoff.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return manifest
