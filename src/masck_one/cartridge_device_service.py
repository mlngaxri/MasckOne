"""Device-side cartridge receiver and coordinated service mechanism.

Consumes the selected Cell 11 cartridge and tactile bolt/key geometry. A single hidden
+Y shuttle retracts both opposed bolts and a floating wet nose before the cartridge
uses the existing oblique service corridor. Free compliant, deformed, service-sweep,
frame-interface and manufactured geometry remain separate. Physical feel, force,
leakage, life, strength, hygiene and process capability remain validation required.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1, sha256
import json
import math
from pathlib import Path

import cadquery as cq

from .cartridge_service_corridor import build_service_corridor
from .cartridge_tactile_service import build_cartridge_tactile_service
from .realized_waste_cartridge import (
    BLIND_KEY_DATUM_WORLD_MM,
    ROUTE_HANDOFF_WORLD_MM,
    box,
    build_realized_waste_cartridge,
    cylinder,
    volume,
)

SCHEMA = "MASCK_ONE_CELL11_DEVICE_CARTRIDGE_SERVICE_V2"
OWNER_PR = 140
OWNER_BRANCH = "sol-high/cartridge-service-20260909"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
TOL_MM3 = 1e-7
SOURCE_GIT_BLOBS = (
    ("config/masck_one_authority.yaml", "2608dda483b995539de422290371c219668a1527"),
    ("config/masck_brand_authority.yaml", "52c90085c474152e6a2adc9e0459cf665d006618"),
    ("src/masck_one/warm_cool_package.py", "96bc48a24bc6d1c81afc3540e9930e9e52470ef6"),
    ("src/masck_one/realized_waste_cartridge.py", "324447c16307cb930358c1cf32a6f1a56d829d8e"),
    ("src/masck_one/cartridge_tactile_service.py", "c50d091d3cf82acc73cc117255da0759e92041d3"),
    ("src/masck_one/cartridge_service_corridor.py", "55c2e04d9ae025ac32c9a435673ecd1d0001d802"),
)

SHUTTLE_TRAVEL_Y_MM = 4.0
BOLT_RETRACTION_MM = 1.60
WET_NOSE_RETRACTION_MM = 1.40
CAM_FOLLOWER_DIAMETER_MM = 0.80
CAM_SLOT_WIDTH_MM = 1.00
CAM_SLOT_LENGTH_MM = 6.20
CAM_RADIAL_CLEARANCE_MM = (CAM_SLOT_WIDTH_MM - CAM_FOLLOWER_DIAMETER_MM) / 2.0
MAX_CAM_RADIAL_CLEARANCE_MM = 0.12
CAM_CENTERLINE_TOL_MM = 1e-10
CAM_CHANNELS = (
    ("left_bolt", -26.0, -BOLT_RETRACTION_MM),
    ("right_bolt", 26.0, BOLT_RETRACTION_MM),
    ("wet_nose", -10.0, -WET_NOSE_RETRACTION_MM),
)

WET_NOSE_START = (-41.0, -82.0, 14.0)
WET_NOSE_LENGTH_MM = 3.80
WET_NOSE_OD_MM = 3.60
WET_LUMEN_DIAMETER_MM = 2.40
POPPET_FREE_DIAMETER_MM = 2.44
POPPET_INSTALLED_DIAMETER_MM = 2.40
POPPET_RADIAL_PRELOAD_SEED_MM = 0.02


class CartridgeDeviceServiceError(ValueError):
    pass


def _blob(path: Path) -> str:
    data = path.read_bytes()
    return sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def _require_sources() -> None:
    root = Path(__file__).resolve().parents[2]
    for name, expected in SOURCE_GIT_BLOBS:
        path = root / name
        if not path.is_file() or _blob(path) != expected:
            raise CartridgeDeviceServiceError(f"device-service source moved: {name}")


def _finite_progress(progress: float) -> float:
    if isinstance(progress, bool) or not isinstance(progress, (int, float)):
        raise CartridgeDeviceServiceError("cam progress must be finite numeric")
    value = float(progress)
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise CartridgeDeviceServiceError("cam progress must be within [0, 1]")
    return value


def _cam_slot_angle_deg(delta_x_mm: float) -> float:
    return math.degrees(math.atan2(-SHUTTLE_TRAVEL_Y_MM, delta_x_mm)) % 180.0


def _cam_slot_center_x(locked_follower_x_mm: float, delta_x_mm: float) -> float:
    return locked_follower_x_mm + delta_x_mm / 2.0


def cam_follower_state(progress: float) -> dict[str, dict[str, float]]:
    """Analytic straight-slot/follower relation over the complete shuttle stroke.

    This is kinematic geometry only. It does not establish friction, force, wear,
    contamination tolerance, production capability or subjective tactile quality.
    """
    p = _finite_progress(progress)
    shuttle_center_y = -84.0 + SHUTTLE_TRAVEL_Y_MM * p
    follower_y = -82.0
    state: dict[str, dict[str, float]] = {}

    for name, locked_x, delta_x in CAM_CHANNELS:
        slot_center_x = _cam_slot_center_x(locked_x, delta_x)
        follower_x = locked_x + delta_x * p
        rel_x = follower_x - slot_center_x
        rel_y = follower_y - shuttle_center_y
        line_dx = delta_x
        line_dy = -SHUTTLE_TRAVEL_Y_MM
        line_length = math.hypot(line_dx, line_dy)
        centerline_residual = abs(rel_x * line_dy - rel_y * line_dx) / line_length
        along_slot = (rel_x * line_dx + rel_y * line_dy) / line_length
        available_center_travel = CAM_SLOT_LENGTH_MM / 2.0 - CAM_FOLLOWER_DIAMETER_MM / 2.0

        state[name] = {
            "progress": p,
            "follower_world_x_mm": follower_x,
            "follower_world_y_mm": follower_y,
            "shuttle_center_world_y_mm": shuttle_center_y,
            "slot_center_world_x_mm": slot_center_x,
            "slot_center_world_y_mm": shuttle_center_y,
            "slot_angle_deg": _cam_slot_angle_deg(delta_x),
            "centerline_residual_mm": centerline_residual,
            "along_slot_mm": along_slot,
            "available_center_travel_mm": available_center_travel,
        }
    return state


def _validate_cam_design() -> dict[str, object]:
    if not 0.0 < CAM_RADIAL_CLEARANCE_MM <= MAX_CAM_RADIAL_CLEARANCE_MM:
        raise CartridgeDeviceServiceError("cam radial clearance is outside bounded low-play seed")
    if CAM_SLOT_WIDTH_MM <= CAM_FOLLOWER_DIAMETER_MM:
        raise CartridgeDeviceServiceError("cam slot must retain positive follower running clearance")

    max_residual = 0.0
    max_utilization = 0.0
    for index in range(21):
        for channel in cam_follower_state(index / 20.0).values():
            residual = channel["centerline_residual_mm"]
            max_residual = max(max_residual, residual)
            if residual > CAM_CENTERLINE_TOL_MM:
                raise CartridgeDeviceServiceError("cam follower left analytic slot centerline")
            available = channel["available_center_travel_mm"]
            along = abs(channel["along_slot_mm"])
            if along > available + CAM_CENTERLINE_TOL_MM:
                raise CartridgeDeviceServiceError("cam follower exceeds bounded slot length")
            max_utilization = max(max_utilization, along / available)

    return {
        "proof": "ANALYTIC_STRAIGHT_SLOT_CENTERLINE_OVER_COMPLETE_NORMALIZED_STROKE",
        "sampled_regression_points": 21,
        "cam_follower_diameter_mm": CAM_FOLLOWER_DIAMETER_MM,
        "cam_slot_width_mm": CAM_SLOT_WIDTH_MM,
        "cam_slot_length_mm": CAM_SLOT_LENGTH_MM,
        "cam_radial_clearance_mm": CAM_RADIAL_CLEARANCE_MM,
        "max_allowed_cam_radial_clearance_mm": MAX_CAM_RADIAL_CLEARANCE_MM,
        "max_centerline_residual_mm": max_residual,
        "max_slot_center_travel_utilization": max_utilization,
        "force_friction_wear_validated": False,
    }


def _annulus(start, length, od, bore):
    outer = cylinder(start, (1, 0, 0), length, od)
    inner = cylinder((start[0] - 0.1, start[1], start[2]), (1, 0, 0), length + 0.2, bore)
    result = outer.cut(inner)
    if not result.val().isValid() or len(result.val().Solids()) != 1:
        raise CartridgeDeviceServiceError("invalid annular wet component")
    return result


def _record(shape):
    bb = shape.val().BoundingBox()
    return {
        "solid_count": len(shape.val().Solids()),
        "volume_mm3": float(volume(shape)),
        "bounds_world_mm": [bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax],
    }


def _shuttle():
    _validate_cam_design()
    part = box((64, 8, 1.6), (0, -84, 21))
    part = part.union(box((4, 6, 1.4), (-33.5, -84, 21)))
    part = part.union(box((4, 6, 1.4), (33.5, -84, 21)))
    for _, locked_x, delta_x in CAM_CHANNELS:
        center_x = _cam_slot_center_x(locked_x, delta_x)
        angle = _cam_slot_angle_deg(delta_x)
        slot = (
            cq.Workplane("XY", origin=(center_x, -84, 20))
            .slot2D(CAM_SLOT_LENGTH_MM, CAM_SLOT_WIDTH_MM, angle)
            .extrude(2)
        )
        part = part.cut(slot)
    if not part.val().isValid() or len(part.val().Solids()) != 1:
        raise CartridgeDeviceServiceError("release shuttle lost one-piece topology")
    return part


def _receiver(tactile):
    left = box((1.6, 5, 33), (-41.1, -82, 8.5))
    right = box((1.6, 5, 33), (41.1, -82, 8.5))
    left = left.cut(cylinder((-42.2, -82, 17), (1, 0, 0), 2.4, 1.9))
    left = left.cut(cylinder((-42.2, -82, 14), (1, 0, 0), 2.4, 4.2))
    right = right.cut(cylinder((39.8, -82, 17), (1, 0, 0), 2.4, 1.9))
    left = left.cut(box((1.4, 1.4, 5.5), (-40.8, -82, 18.4)))
    left = left.cut(box((1.4, 1.4, 6.5), (-40.0, -82, 17.0)))
    right = right.cut(box((1.4, 1.4, 5.5), (40.8, -82, 18.4)))

    fixed = left.union(right)
    fixed = fixed.union(box((84, 5, 2.6), (0, -82, -6)))
    fixed = fixed.union(box((84, 5, 2.0), (0, -82, 24)))
    fixed = fixed.union(box((12, 8, 2.6), (-25, -82, -8.2)))
    fixed = fixed.union(box((12, 8, 2.6), (25, -82, -8.2)))
    fixed = fixed.union(box((4.2, 0.7, 0.6), (-38.4, -80.65, BLIND_KEY_DATUM_WORLD_MM[2])))
    fixed = fixed.union(_annulus((-45.2, -82, 14), 4.8, 5.6, 4.0))
    fixed = fixed.union(tactile.left_bolt_guide).union(tactile.right_bolt_guide)
    fixed = fixed.union(tactile.key_tongue_reference)
    for sign in (-1, 1):
        fixed = fixed.union(box((3.6, 15.5, 4.6), (sign * 34.8, -82, 21)))
        fixed = fixed.cut(box((4.2, 12.5, 2.4), (sign * 34.8, -82, 21)))
    fixed = fixed.cut(box((20, 2, 5.6), (-34, -82, 18.8)))
    fixed = fixed.cut(box((20, 2, 5.6), (34, -82, 18.8)))
    fixed = fixed.cut(box((34.5, 1.8, 8), (-25, -82, 17.2)))
    if not fixed.val().isValid() or len(fixed.val().Solids()) != 1:
        raise CartridgeDeviceServiceError("receiver load path is not one connected B-rep")
    return fixed


def _bolt_drive(bolt, sign):
    part = bolt.union(cylinder((sign * 39.7, -82, 17), (sign, 0, 0), 1.7, 1.3))
    part = part.union(box((0.9, 0.9, 2.8), (sign * 40.8, -82, 18.2)))
    part = part.union(box((14.8, 0.8, 0.6), (sign * 33.4, -82, 19.4)))
    part = part.union(
        cylinder((sign * 26, -82, 19.3), (0, 0, 1), 2.7, CAM_FOLLOWER_DIAMETER_MM)
    )
    if not part.val().isValid() or len(part.val().Solids()) != 1 or volume(bolt.cut(part)) > TOL_MM3:
        raise CartridgeDeviceServiceError("bolt drive lost canonical bolt geometry")
    return part


def _wet_drive():
    part = _annulus(WET_NOSE_START, WET_NOSE_LENGTH_MM, WET_NOSE_OD_MM, WET_LUMEN_DIAMETER_MM)
    part = part.union(box((0.8, 1, 2.2), (-40, -82, 15.4)))
    part = part.union(box((0.8, 0.8, 4.2), (-40, -82, 17.3)))
    part = part.union(box((30, 0.7, 0.7), (-25, -82, 18.9)))
    part = part.union(
        cylinder((-10, -82, 18.7), (0, 0, 1), 3.3, CAM_FOLLOWER_DIAMETER_MM)
    )
    if not part.val().isValid() or len(part.val().Solids()) != 1:
        raise CartridgeDeviceServiceError("wet drive is not one connected B-rep")
    return part


@dataclass(frozen=True)
class CartridgeDeviceService:
    receiver: cq.Workplane
    shuttle_locked: cq.Workplane
    shuttle_service: cq.Workplane
    left_locked: cq.Workplane
    right_locked: cq.Workplane
    left_service: cq.Workplane
    right_service: cq.Workplane
    wet_locked: cq.Workplane
    wet_service: cq.Workplane
    poppet_free: cq.Workplane
    poppet_closed_service: cq.Workplane
    poppet_open_locked: cq.Workplane
    frame_mount_reference: cq.Workplane
    corridor_report: dict[str, object]

    def validate(self):
        _require_sources()
        _validate_cam_design()
        for shape in (
            self.receiver,
            self.shuttle_locked,
            self.shuttle_service,
            self.left_locked,
            self.right_locked,
            self.left_service,
            self.right_service,
            self.wet_locked,
            self.wet_service,
            self.poppet_free,
            self.poppet_closed_service,
            self.poppet_open_locked,
            self.frame_mount_reference,
        ):
            if not shape.val().isValid() or not shape.val().Solids() or volume(shape) <= 0:
                raise CartridgeDeviceServiceError("invalid material/reference geometry")
        for moving, fixed in (
            (self.shuttle_locked, self.receiver),
            (self.shuttle_service, self.receiver),
            (self.left_locked, self.receiver),
            (self.right_locked, self.receiver),
            (self.left_service, self.receiver),
            (self.right_service, self.receiver),
            (self.wet_locked, self.receiver),
            (self.wet_service, self.receiver),
            (self.left_locked, self.shuttle_locked),
            (self.right_locked, self.shuttle_locked),
            (self.wet_locked, self.shuttle_locked),
            (self.left_service, self.shuttle_service),
            (self.right_service, self.shuttle_service),
            (self.wet_service, self.shuttle_service),
        ):
            if volume(moving.intersect(fixed)) > TOL_MM3:
                raise CartridgeDeviceServiceError("unintended rigid service-state overlap")
        if self.corridor_report["continuous_installed_device_path_proven"] is not False:
            raise CartridgeDeviceServiceError("unreleased frame B-rep was silently promoted")
        return self

    def manifest(self):
        self.validate()
        cam = _validate_cam_design()
        materials = {
            "device_receiver": self.receiver,
            "release_shuttle": self.shuttle_locked,
            "left_bolt_drive": self.left_locked,
            "right_bolt_drive": self.right_locked,
            "floating_wet_nose_drive": self.wet_locked,
            "wet_poppet_free_region": self.poppet_free,
        }
        payload = {
            "schema": SCHEMA,
            "owner_pr": OWNER_PR,
            "owner_branch": OWNER_BRANCH,
            "world_frame_id": WORLD_FRAME_ID,
            "source_git_blobs": dict(SOURCE_GIT_BLOBS),
            "selected_architecture": "ONE_GUIDED_SHUTTLE_OPPOSED_BOLTS_FLOATING_WET_NOSE_PASSIVE_POPPET",
            "interaction_sequence": [
                "BROAD_OBLIQUE_APPROACH",
                "FORGIVING_CAPTURE",
                "SELF_CENTER",
                "LOW_DRAG_GUIDANCE",
                "PROGRESSIVE_LOCAL_TAKEUP",
                "ONE_LOCKED_FINAL_STATE",
            ],
            "kinematics": {
                "shuttle_axis_world": [0, 1, 0],
                "shuttle_travel_mm": SHUTTLE_TRAVEL_Y_MM,
                "bolt_retraction_mm_each": BOLT_RETRACTION_MM,
                "wet_nose_retraction_mm": WET_NOSE_RETRACTION_MM,
                "cam_coupling": cam,
            },
            "wet_interface": {
                "route_handoff_world_mm": list(ROUTE_HANDOFF_WORLD_MM),
                "removed_state_closure": "COMPLIANT_PASSIVE_POPPET_GEOMETRIC_SEED",
                "poppet_radial_preload_seed_mm": POPPET_RADIAL_PRELOAD_SEED_MM,
                "wet_nose_retracts_before_cartridge_motion": True,
                "leakage_validated": False,
                "closing_force_validated": False,
                "hydraulic_loss_validated": False,
                "backflow_performance_validated": False,
            },
            "digital_claims": {
                "device_side_key_bolt_capture_realized": True,
                "coordinated_wet_disconnect_realized": True,
                "removed_state_port_closure_geometry_realized": True,
                "cam_follower_centerline_coupling_analytic": True,
                "local_locked_and_service_states_collision_checked": True,
                "continuous_rigid_collision_proven": False,
                "released_shell_package_oblique_corridor_clear": True,
                "whole_device_frame_installed_path_proven": False,
            },
            "structural_support": {
                "receiver_one_connected_brep": len(self.receiver.val().Solids()) == 1,
                "frame_mount_feet_realized": True,
                "frame_counterpart_consumed": False,
                "frame_owner_status": "PR117_CANDIDATE_NOT_RELEASED_MAIN_DO_NOT_DUPLICATE",
            },
            "manufacturing_components": {k: _record(v) for k, v in materials.items()},
            "corridor_status": self.corridor_report["status"],
            "cmf_role": "HIDDEN_RECESSIVE_MECHANICS_CONSUME_BRAND_AUTHORITY",
            "physical_validation_eligible": False,
            "remaining_integration_blockers": [
                "RELEASE_CANONICAL_FRAME_BREP_AND_MATE_RECEIVER_FEET",
                "RECHECK_WHOLE_PRODUCT_SERVICE_SWEEP_WITH_FRAME_AND_CURRENT_EXTERIOR",
                "CONTINUOUS_RIGID_INTERMEDIATE_STATE_COLLISION_PROOF",
                "PHYSICALLY_QUALIFY_CAM_FRICTION_WEAR_CONTAMINATION_AND_SERVICE_FEEL",
                "PHYSICALLY_QUALIFY_WET_POPPET_RETENTION_TOLERANCE_AND_SERVICE_FEEL",
            ],
        }
        payload["manifest_sha256"] = sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()
        return payload


def build_cartridge_device_service():
    _require_sources()
    _validate_cam_design()
    cartridge = build_realized_waste_cartridge()
    tactile = build_cartridge_tactile_service()
    corridor, _ = build_service_corridor(cartridge)
    receiver = _receiver(tactile)
    shuttle = _shuttle()
    left = _bolt_drive(tactile.left_bolt, -1)
    right = _bolt_drive(tactile.right_bolt, 1)
    left_service = left.translate((-BOLT_RETRACTION_MM, 0, 0))
    right_service = right.translate((BOLT_RETRACTION_MM, 0, 0))
    wet = _wet_drive()
    wet_service = wet.translate((-WET_NOSE_RETRACTION_MM, 0, 0))

    moving_cartridge = cq.Workplane(
        obj=cq.Compound.makeCompound(
            [cartridge.body_solid.val(), tactile.closure_with_pad_root_pockets.val()]
        )
    )
    if volume(receiver.intersect(moving_cartridge)) > TOL_MM3:
        raise CartridgeDeviceServiceError("receiver intersects selected cartridge material")
    if volume(receiver.intersect(tactile.key_pad_installed_reference)) > TOL_MM3:
        raise CartridgeDeviceServiceError("receiver overlaps installed key-takeup reference")
    if volume(left.intersect(cartridge.retention_pockets_reference)) <= TOL_MM3:
        raise CartridgeDeviceServiceError("left bolt does not engage retention pocket")
    if volume(right.intersect(cartridge.retention_pockets_reference)) <= TOL_MM3:
        raise CartridgeDeviceServiceError("right bolt does not engage retention pocket")
    if volume(left_service.intersect(cartridge.retention_pockets_reference)) > TOL_MM3:
        raise CartridgeDeviceServiceError("left bolt remains engaged in service state")
    if volume(right_service.intersect(cartridge.retention_pockets_reference)) > TOL_MM3:
        raise CartridgeDeviceServiceError("right bolt remains engaged in service state")

    nose = _annulus(WET_NOSE_START, WET_NOSE_LENGTH_MM, WET_NOSE_OD_MM, WET_LUMEN_DIAMETER_MM)
    if volume(nose.cut(cartridge.inlet_connector_clearance_reference)) > TOL_MM3:
        raise CartridgeDeviceServiceError("wet nose escaped canonical inlet clearance")
    if (
        volume(wet.intersect(moving_cartridge)) > TOL_MM3
        or volume(wet_service.intersect(moving_cartridge)) > TOL_MM3
    ):
        raise CartridgeDeviceServiceError("wet drive intersects cartridge material")

    poppet_free = cylinder((-39.4, -82, 14), (1, 0, 0), 0.35, POPPET_FREE_DIAMETER_MM)
    poppet_fit = cylinder((-39.4, -82, 14), (1, 0, 0), 0.35, POPPET_INSTALLED_DIAMETER_MM)
    if volume(poppet_free.intersect(nose)) <= TOL_MM3 or volume(poppet_fit.intersect(nose)) > TOL_MM3:
        raise CartridgeDeviceServiceError("poppet preload/deformed-state separation failed")

    frame_ref = cq.Workplane(
        obj=cq.Compound.makeCompound(
            [
                box((10, 6, 0.2), (-25, -82, -9.55)).val(),
                box((10, 6, 0.2), (25, -82, -9.55)).val(),
            ]
        )
    )
    result = CartridgeDeviceService(
        receiver,
        shuttle,
        shuttle.translate((0, SHUTTLE_TRAVEL_Y_MM, 0)),
        left,
        right,
        left_service,
        right_service,
        wet,
        wet_service,
        poppet_free,
        poppet_fit.translate((-WET_NOSE_RETRACTION_MM, 0, 0)),
        poppet_fit.translate((-0.8, 0, 0)),
        frame_ref,
        corridor,
    )
    return result.validate()
