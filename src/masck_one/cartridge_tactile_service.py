"""Low-cost tactile service refinement for the selected Cell 11 cartridge.

This module does not re-author the source-bound supported-liner body or claim a
current-main installed service path. It consumes the existing owner candidate only
after that candidate passes its own validation, then refines local user-facing service
interfaces that are independent of the still-missing released frame B-rep.

The refinement has two jobs:

1. Keep bolt engagement forgiving at the cartridge pocket while making the device-side
   bolt journal much less sloppy inside its local guide. A tapered small capture nose
   transitions to a larger journal running in a slightly smaller guide bore. Two tiny
   longitudinal reliefs interrupt the bearing surface so cleanser residue/debris has
   somewhere to escape instead of turning a precision fit into stiction.
2. Replace a purely clearance-based blind key final state with three local compliant
   take-up pads. The pads remain out of the broad service corridor but intentionally
   have a tiny installed interference seed against the existing rectangular key
   tongue. Their roots are mechanically buried in closure material. Free elastomer and
   installed/deformed reference geometry are kept separate.

The result is a digital precursor to broad entry -> low-drag guidance -> progressive
take-up -> one restrained final state. It is not physical evidence of insertion force,
wear, contamination robustness, rattle, leakage, or subjective feel.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
import math

import cadquery as cq

from .realized_waste_cartridge import (
    BLIND_KEY_DATUM_WORLD_MM,
    LEFT_RETENTION_DATUM_WORLD_MM,
    RIGHT_RETENTION_DATUM_WORLD_MM,
    RealizedWasteCartridgeError,
    box,
    build_realized_waste_cartridge,
    cylinder,
    volume,
)

SCHEMA = "MASCK_ONE_CELL11_CARTRIDGE_TACTILE_SERVICE_V1"
OWNER_BRANCH = "sol-high/cartridge-service-20260909"
OWNER_HEAD_AT_REFINEMENT_START = "9e78f6d30d7023b9d75d96ba2cdb04d1cecc7b08"
TOL_MM3 = 1e-7

# Existing simple latch: 1.20 mm bolt in 1.40 mm guide bore.
LEGACY_BOLT_DIAMETER_MM = 1.20
LEGACY_GUIDE_BORE_DIAMETER_MM = 1.40
LEGACY_RADIAL_GUIDE_CLEARANCE_MM = (
    LEGACY_GUIDE_BORE_DIAMETER_MM - LEGACY_BOLT_DIAMETER_MM
) / 2.0

# Selected local refinement. The capture nose stays deliberately loose in the 1.40 mm
# cartridge pocket while the guide journal carries the precision.
BOLT_CAPTURE_NOSE_DIAMETER_MM = 1.12
BOLT_CAPTURE_SHANK_DIAMETER_MM = 1.18
BOLT_JOURNAL_DIAMETER_MM = 1.30
BOLT_GUIDE_BORE_DIAMETER_MM = 1.36
BOLT_NOSE_CHAMFER_LENGTH_MM = 0.30
BOLT_CAPTURE_SHANK_LENGTH_MM = 1.55
BOLT_TRANSITION_LENGTH_MM = 0.35
BOLT_TOTAL_LENGTH_MM = 4.00
NEW_RADIAL_GUIDE_CLEARANCE_MM = (
    BOLT_GUIDE_BORE_DIAMETER_MM - BOLT_JOURNAL_DIAMETER_MM
) / 2.0
MAX_NEW_RADIAL_GUIDE_CLEARANCE_MM = 0.04
MIN_CAPTURE_POCKET_RADIAL_CLEARANCE_MM = 0.08

GUIDE_BOX_XYZ_MM = (2.40, 4.00, 2.80)
GUIDE_CENTER_X_ABS_MM = 39.50
GUIDE_CENTER_Y_MM = -82.0
GUIDE_CENTER_Z_MM = 17.0
GUIDE_RELIEF_WIDTH_Y_MM = 0.26
GUIDE_RELIEF_DEPTH_Z_MM = 0.16
GUIDE_RELIEF_CENTER_Z_OFFSET_MM = BOLT_GUIDE_BORE_DIAMETER_MM / 2.0 - 0.04

# Existing channel is 2.4 x 1.2 x 0.9 and tongue is 1.6 x 1.0 x 0.7.
KEY_CHANNEL_XYZ_MM = (2.40, 1.20, 0.90)
KEY_TONGUE_XYZ_MM = (1.60, 1.00, 0.70)
KEY_PAD_X_MM = 0.55
KEY_PAD_SIDE_Y_MM = 0.17
KEY_PAD_SIDE_Z_MM = 0.36
KEY_PAD_BOTTOM_Y_MM = 0.42
KEY_PAD_BOTTOM_Z_MM = 0.17
KEY_PAD_ROOT_OUTSIDE_CHANNEL_MM = 0.06
KEY_PAD_INWARD_INTRUSION_MM = 0.11
KEY_PAD_X_CENTER_MM = -35.18
KEY_PAD_PRELOAD_SEED_PER_SIDE_MM = (
    KEY_TONGUE_XYZ_MM[1]
    - (KEY_CHANNEL_XYZ_MM[1] - 2.0 * KEY_PAD_INWARD_INTRUSION_MM)
) / 2.0
KEY_PAD_BOTTOM_PRELOAD_SEED_MM = (
    KEY_TONGUE_XYZ_MM[2] / 2.0
    - (KEY_CHANNEL_XYZ_MM[2] / 2.0 - KEY_PAD_INWARD_INTRUSION_MM)
)
MIN_KEY_PRELOAD_SEED_MM = 0.005
MAX_KEY_PRELOAD_SEED_MM = 0.03


class CartridgeTactileServiceError(ValueError):
    pass


def _cone_x(
    start: tuple[float, float, float],
    sign: int,
    length_mm: float,
    start_diameter_mm: float,
    end_diameter_mm: float,
) -> cq.Workplane:
    if sign not in (-1, 1):
        raise CartridgeTactileServiceError("bolt side sign must be +/-1")
    solid = cq.Solid.makeCone(
        start_diameter_mm / 2.0,
        end_diameter_mm / 2.0,
        length_mm,
        cq.Vector(*start),
        cq.Vector(float(sign), 0.0, 0.0),
    )
    wp = cq.Workplane(obj=solid)
    if not solid.isValid() or solid.Volume() <= 0.0:
        raise CartridgeTactileServiceError("tapered bolt segment must be valid positive material")
    return wp


def _refined_bolt(sign: int) -> cq.Workplane:
    start_x = sign * 35.9
    start = (start_x, GUIDE_CENTER_Y_MM, GUIDE_CENTER_Z_MM)
    nose = _cone_x(
        start,
        sign,
        BOLT_NOSE_CHAMFER_LENGTH_MM,
        BOLT_CAPTURE_NOSE_DIAMETER_MM,
        BOLT_CAPTURE_SHANK_DIAMETER_MM,
    )
    shank_start = (start_x + sign * BOLT_NOSE_CHAMFER_LENGTH_MM, GUIDE_CENTER_Y_MM, GUIDE_CENTER_Z_MM)
    shank = cylinder(
        shank_start,
        (float(sign), 0.0, 0.0),
        BOLT_CAPTURE_SHANK_LENGTH_MM,
        BOLT_CAPTURE_SHANK_DIAMETER_MM,
    )
    transition_start_x = start_x + sign * (
        BOLT_NOSE_CHAMFER_LENGTH_MM + BOLT_CAPTURE_SHANK_LENGTH_MM
    )
    transition = _cone_x(
        (transition_start_x, GUIDE_CENTER_Y_MM, GUIDE_CENTER_Z_MM),
        sign,
        BOLT_TRANSITION_LENGTH_MM,
        BOLT_CAPTURE_SHANK_DIAMETER_MM,
        BOLT_JOURNAL_DIAMETER_MM,
    )
    used = BOLT_NOSE_CHAMFER_LENGTH_MM + BOLT_CAPTURE_SHANK_LENGTH_MM + BOLT_TRANSITION_LENGTH_MM
    journal_start_x = start_x + sign * used
    journal = cylinder(
        (journal_start_x, GUIDE_CENTER_Y_MM, GUIDE_CENTER_Z_MM),
        (float(sign), 0.0, 0.0),
        BOLT_TOTAL_LENGTH_MM - used,
        BOLT_JOURNAL_DIAMETER_MM,
    )
    result = nose.union(shank).union(transition).union(journal)
    if not result.val().isValid() or len(result.val().Solids()) != 1 or volume(result) <= 0.0:
        raise CartridgeTactileServiceError("refined bolt must be one connected solid")
    return result


def _refined_guide(sign: int) -> cq.Workplane:
    guide = box(
        GUIDE_BOX_XYZ_MM,
        (sign * GUIDE_CENTER_X_ABS_MM, GUIDE_CENTER_Y_MM, GUIDE_CENTER_Z_MM),
    )
    bore = cylinder(
        (sign * 37.5, GUIDE_CENTER_Y_MM, GUIDE_CENTER_Z_MM),
        (float(sign), 0.0, 0.0),
        4.0,
        BOLT_GUIDE_BORE_DIAMETER_MM,
    )
    guide = guide.cut(bore)

    # Two small longitudinal debris reliefs break the full annular bearing contact.
    for z_sign in (-1.0, 1.0):
        relief = box(
            (GUIDE_BOX_XYZ_MM[0] + 0.10, GUIDE_RELIEF_WIDTH_Y_MM, GUIDE_RELIEF_DEPTH_Z_MM),
            (
                sign * GUIDE_CENTER_X_ABS_MM,
                GUIDE_CENTER_Y_MM,
                GUIDE_CENTER_Z_MM + z_sign * GUIDE_RELIEF_CENTER_Z_OFFSET_MM,
            ),
        )
        guide = guide.cut(relief)
    if not guide.val().isValid() or len(guide.val().Solids()) != 1 or volume(guide) <= 0.0:
        raise CartridgeTactileServiceError("refined bolt guide must remain one valid solid")
    return guide


def _key_pad_free_regions() -> tuple[cq.Workplane, ...]:
    x, y, z = BLIND_KEY_DATUM_WORLD_MM
    half_y = KEY_CHANNEL_XYZ_MM[1] / 2.0
    half_z = KEY_CHANNEL_XYZ_MM[2] / 2.0
    side_center_offset = half_y + (
        KEY_PAD_ROOT_OUTSIDE_CHANNEL_MM - KEY_PAD_INWARD_INTRUSION_MM
    ) / 2.0
    bottom_center_offset = -half_z - (
        KEY_PAD_ROOT_OUTSIDE_CHANNEL_MM - KEY_PAD_INWARD_INTRUSION_MM
    ) / 2.0
    return (
        box(
            (KEY_PAD_X_MM, KEY_PAD_SIDE_Y_MM, KEY_PAD_SIDE_Z_MM),
            (KEY_PAD_X_CENTER_MM, y + side_center_offset, z),
        ),
        box(
            (KEY_PAD_X_MM, KEY_PAD_SIDE_Y_MM, KEY_PAD_SIDE_Z_MM),
            (KEY_PAD_X_CENTER_MM, y - side_center_offset, z),
        ),
        box(
            (KEY_PAD_X_MM, KEY_PAD_BOTTOM_Y_MM, KEY_PAD_BOTTOM_Z_MM),
            (KEY_PAD_X_CENTER_MM, y, z + bottom_center_offset),
        ),
    )


def _compound(parts: tuple[cq.Workplane, ...]) -> cq.Workplane:
    return cq.Workplane(obj=cq.Compound.makeCompound([part.val() for part in parts]))


def _installed_key_pad_reference(
    free_regions: tuple[cq.Workplane, ...],
    tongue: cq.Workplane,
) -> cq.Workplane:
    # Reference-only deformation removes the nominal interference volume. This does
    # not predict elastomer stress or force.
    installed = tuple(part.cut(tongue) for part in free_regions)
    if any(not part.val().isValid() or volume(part) <= 0.0 for part in installed):
        raise CartridgeTactileServiceError("installed key-pad reference became invalid")
    return _compound(installed)


@dataclass(frozen=True)
class CartridgeTactileService:
    owner_manifest_sha256: str
    closure_with_pad_root_pockets: cq.Workplane
    left_bolt: cq.Workplane
    right_bolt: cq.Workplane
    left_bolt_guide: cq.Workplane
    right_bolt_guide: cq.Workplane
    key_pad_free_regions: cq.Workplane
    key_pad_installed_reference: cq.Workplane
    key_tongue_reference: cq.Workplane
    pad_root_removed_mm3: float
    key_free_interference_mm3: float
    key_installed_interference_mm3: float
    guide_radial_clearance_mm: float
    capture_pocket_radial_clearance_mm: float
    physical_validation_eligible: bool = False

    def validate(self) -> "CartridgeTactileService":
        if self.physical_validation_eligible:
            raise CartridgeTactileServiceError("digital tactile-service geometry is not physical validation")
        if self.pad_root_removed_mm3 <= 0.0:
            raise CartridgeTactileServiceError("key take-up pads need positive mechanical root pockets")
        if self.key_free_interference_mm3 <= 0.0:
            raise CartridgeTactileServiceError("free key pads must carry a small positive preload seed")
        if self.key_installed_interference_mm3 > TOL_MM3:
            raise CartridgeTactileServiceError("installed/deformed key-pad reference cannot rigidly overlap tongue")
        if not (0.0 < self.guide_radial_clearance_mm <= MAX_NEW_RADIAL_GUIDE_CLEARANCE_MM):
            raise CartridgeTactileServiceError("refined bolt guide clearance is outside bounded low-play seed")
        if self.capture_pocket_radial_clearance_mm < MIN_CAPTURE_POCKET_RADIAL_CLEARANCE_MM:
            raise CartridgeTactileServiceError("capture nose is too tight for forgiving blind engagement")
        if not (MIN_KEY_PRELOAD_SEED_MM <= KEY_PAD_PRELOAD_SEED_PER_SIDE_MM <= MAX_KEY_PRELOAD_SEED_MM):
            raise CartridgeTactileServiceError("side key-pad preload seed outside bounded range")
        if not (MIN_KEY_PRELOAD_SEED_MM <= KEY_PAD_BOTTOM_PRELOAD_SEED_MM <= MAX_KEY_PRELOAD_SEED_MM):
            raise CartridgeTactileServiceError("bottom key-pad preload seed outside bounded range")
        for shape in (
            self.closure_with_pad_root_pockets,
            self.left_bolt,
            self.right_bolt,
            self.left_bolt_guide,
            self.right_bolt_guide,
            self.key_pad_free_regions,
            self.key_pad_installed_reference,
        ):
            if not shape.val().isValid() or not shape.val().Solids() or volume(shape) <= 0.0:
                raise CartridgeTactileServiceError("tactile-service body/reference must be valid positive geometry")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "owner_branch": OWNER_BRANCH,
            "owner_head_at_refinement_start": OWNER_HEAD_AT_REFINEMENT_START,
            "owner_manifest_sha256": self.owner_manifest_sha256,
            "scope": "LOCAL_CARTRIDGE_SERVICE_INTERFACES_ONLY_FRAME_SIDE_FINAL_SEAT_STILL_BLOCKED",
            "interaction_sequence": (
                "BROAD_CLEAR_SERVICE_APPROACH -> FORGIVING_CAPTURE_NOSE -> LOW_PLAY_RELIEVED_BOLT_JOURNAL -> "
                "LOCAL_COMPLIANT_KEY_TAKEUP -> RESTRAINED_FINAL_LOCAL_STATE"
            ),
            "bolt_guidance": {
                "legacy_bolt_diameter_mm": LEGACY_BOLT_DIAMETER_MM,
                "legacy_guide_bore_mm": LEGACY_GUIDE_BORE_DIAMETER_MM,
                "legacy_radial_clearance_mm": LEGACY_RADIAL_GUIDE_CLEARANCE_MM,
                "capture_nose_diameter_mm": BOLT_CAPTURE_NOSE_DIAMETER_MM,
                "capture_shank_diameter_mm": BOLT_CAPTURE_SHANK_DIAMETER_MM,
                "journal_diameter_mm": BOLT_JOURNAL_DIAMETER_MM,
                "guide_bore_mm": BOLT_GUIDE_BORE_DIAMETER_MM,
                "new_radial_clearance_mm": self.guide_radial_clearance_mm,
                "capture_pocket_radial_clearance_mm": self.capture_pocket_radial_clearance_mm,
                "debris_relief_count_per_guide": 2,
                "material_direction": "LOW_FRICTION_DIMENSIONALLY_STABLE_ENGINEERING_POLYMER_GUIDE_WITH_SIMPLE_METAL_OR_POLYMER_BOLT_AS_VALIDATED",
            },
            "blind_key_takeup": {
                "architecture": "THREE_LOCAL_MECHANICALLY_ROOTED_COMPLIANT_OVERMOLD_REGIONS",
                "side_preload_seed_each_mm": KEY_PAD_PRELOAD_SEED_PER_SIDE_MM,
                "bottom_preload_seed_mm": KEY_PAD_BOTTOM_PRELOAD_SEED_MM,
                "free_interference_mm3": self.key_free_interference_mm3,
                "installed_rigid_interference_mm3": self.key_installed_interference_mm3,
                "root_pocket_removed_mm3": self.pad_root_removed_mm3,
                "free_and_installed_geometry_separate": True,
                "force_validated": False,
            },
            "cost_rule": (
                "PRECISION_ONLY_AT_LOCAL_GUIDE_AND_FINAL_KEY_TAKEUP; KEEP_CAPTURE_NOSE_AND_SERVICE_CORRIDOR_FORGIVING; "
                "NO_BALL_BEARINGS_NO_MACHINED_CARRIER_NO_SEPARATE_ADJUSTERS"
            ),
            "tactile_reference_rule": "S_T_DUPONT_LIGNE_2_PRECISION_FEEL_ONLY_NOT_SOUND_OR_MECHANISM_COPY",
            "known_blockers": [
                "RELEASED_FRAME_BREP_FOR_TRUE_INSTALLED_SERVICE_SWEEP",
                "DEVICE_SIDE_FINAL_SEAT_AND_BOLT_CAPTURE_LOAD_PATH",
                "WET_DISCONNECT_SEQUENCE",
                "REMOVED_STATE_PORT_CLOSURE",
            ],
            "physical_validation_eligible": False,
            "physical_validation": (
                "OPEN_BOLT_GUIDE_TOLERANCE_FRICTION_STICTION_WEAR_DEBRIS_CONTAMINATION_KEY_PAD_DUROMETER_"
                "COMPRESSION_SET_INSERTION_FORCE_RATTLE_RETURN_SERVICE_LIFE_WET_AGING_AND_SUBJECTIVE_FEEL"
            ),
        }
        payload["manifest_sha256"] = sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()
        return payload


def build_cartridge_tactile_service(cartridge=None) -> CartridgeTactileService:
    cartridge = cartridge or build_realized_waste_cartridge()
    cartridge.validate()
    owner_manifest = cartridge.manifest()

    free_regions = _key_pad_free_regions()
    free_compound = _compound(free_regions)
    tongue = cartridge.device_parts["key_tongue"]

    closure_before = cartridge.closure_solid
    before = volume(closure_before)
    closure_after = closure_before
    for region in free_regions:
        closure_after = closure_after.cut(region)
    root_removed = before - volume(closure_after)
    if volume(closure_after.intersect(free_compound)) > TOL_MM3:
        raise CartridgeTactileServiceError("key overmold free geometry still occupies closure material")

    free_interference = volume(free_compound.intersect(tongue))
    installed = _installed_key_pad_reference(free_regions, tongue)
    installed_interference = volume(installed.intersect(tongue))

    guide_clearance = (BOLT_GUIDE_BORE_DIAMETER_MM - BOLT_JOURNAL_DIAMETER_MM) / 2.0
    capture_clearance = (LEGACY_GUIDE_BORE_DIAMETER_MM - BOLT_CAPTURE_SHANK_DIAMETER_MM) / 2.0

    result = CartridgeTactileService(
        owner_manifest["producer_content_sha256"],
        closure_after,
        _refined_bolt(-1),
        _refined_bolt(1),
        _refined_guide(-1),
        _refined_guide(1),
        free_compound,
        installed,
        tongue,
        round(root_removed, 9),
        round(free_interference, 9),
        round(installed_interference, 9),
        round(guide_clearance, 9),
        round(capture_clearance, 9),
        False,
    )
    return result.validate()
