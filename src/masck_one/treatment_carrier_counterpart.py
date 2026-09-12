from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path

import cadquery as cq

from .structural_frame_carrier_interfaces import (
    END_STOP_THICKNESS_MM,
    RAIL_HEIGHT_MM,
    RAIL_LENGTH_MM,
    RAIL_ROOT_WIDTH_MM,
    REACTION_IDS,
    StructuralFrameCarrierInterfaceArchitecture,
    build_structural_frame_carrier_interfaces,
)
from .structural_frame_carrier_preload import (
    NOMINAL_LATERAL_GAP_MM,
    StructuralFrameCarrierPreloadArchitecture,
    build_structural_frame_carrier_preload,
)
from .structural_frame_carrier_landing import (
    LANDING_PROBE_HEIGHT_MM,
    LANDING_PROBE_LENGTH_MM,
    NOMINAL_LANDING_GAP_MM,
    ROOT_HEIGHT_MM as LANDING_ROOT_HEIGHT_MM,
    TONGUE_RISE_MM,
    StructuralFrameCarrierLandingArchitecture,
    build_structural_frame_carrier_landing,
)
from .structural_frame_carrier_detent import (
    NOMINAL_COUNTERFACE_GAP_MM,
    NOSE_HEIGHT_MM,
    NOSE_LENGTH_MM,
    NOSE_RISE_MM,
    NOSE_WIDTH_MM,
    ROOT_HEIGHT_MM as DETENT_ROOT_HEIGHT_MM,
    StructuralFrameCarrierDetentArchitecture,
    build_structural_frame_carrier_detent,
)

SCHEMA = "MASCK_ONE_TREATMENT_CARRIER_COUNTERPART_V1"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"

# Treatment-owned nominal digital seeds. These are not production tolerances.
SHOE_LENGTH_MM = 4.60
SHOE_WALL_MM = 0.65
ROOT_SIDE_CLEARANCE_MM = 0.20
CROWN_SIDE_CLEARANCE_MM = 0.25
CROWN_UNDERSIDE_CLEARANCE_MM = 0.10
CROWN_TOP_CLEARANCE_MM = 0.30
SHOE_BOTTOM_OFFSET_MM = 0.25
SHOE_TOP_MARGIN_MM = 0.10
RIGID_END_STOP_GAP_MM = 0.32
SOFT_LANDING_PROBE_MM = 0.20
RIGID_END_STOP_PROBE_MM = 0.35
PRELOAD_ENGAGEMENT_PROBE_MM = 0.18
VERTICAL_CAPTURE_PROBE_MM = 0.15
LANDING_PAD_WIDTH_MM = 0.30
LANDING_PAD_X_OFFSET_MM = 0.75
CONNECTOR_HEIGHT_MM = 0.35
RELIEF_MARGIN_MM = 0.10
_INTERSECTION_TOLERANCE_MM3 = 1e-7


class TreatmentCarrierCounterpartError(ValueError):
    pass


def _box(x: float, y: float, z: float, center: tuple[float, float, float]) -> cq.Workplane:
    if min(x, y, z) <= 0.0:
        raise TreatmentCarrierCounterpartError("box dimensions must be positive")
    return cq.Workplane("XY").box(x, y, z, centered=(True, True, False)).translate(center)


def _intersection_volume(a: cq.Workplane, b: cq.Workplane) -> float:
    aa = a.val().BoundingBox()
    bb = b.val().BoundingBox()
    if (
        aa.xmax < bb.xmin or bb.xmax < aa.xmin
        or aa.ymax < bb.ymin or bb.ymax < aa.ymin
        or aa.zmax < bb.zmin or bb.zmax < aa.zmin
    ):
        return 0.0
    try:
        result = a.intersect(b)
    except Exception as exc:
        raise TreatmentCarrierCounterpartError("intersection kernel failure") from exc
    if not result.objects:
        return 0.0
    value = result.val()
    if not value.isValid():
        raise TreatmentCarrierCounterpartError("intersection result is invalid")
    volume = sum(float(s.Volume()) for s in value.Solids())
    if not (volume >= 0.0):
        raise TreatmentCarrierCounterpartError("intersection volume is nonfinite")
    return volume


def _valid_single_solid(shape: cq.Workplane, label: str) -> None:
    value = shape.val()
    if not value.isValid() or len(value.Solids()) != 1 or float(value.Volume()) <= 0.0:
        raise TreatmentCarrierCounterpartError(f"{label} must be one valid positive-volume B-rep solid")


@dataclass(frozen=True, slots=True)
class TreatmentCarrierCounterpart:
    reaction_id: str
    center_xy_mm: tuple[float, float]
    shoe: cq.Workplane = field(repr=False, compare=False)
    nominal_source_intersections_mm3: dict[str, float]
    soft_landing_intersections_mm3: dict[str, float]
    rigid_stop_intersection_mm3: float
    lateral_preload_intersection_mm3: float
    lateral_rail_intersection_mm3: float
    vertical_capture_intersections_mm3: tuple[float, float]

    def __post_init__(self) -> None:
        if self.reaction_id not in REACTION_IDS:
            raise TreatmentCarrierCounterpartError("unknown reaction id")
        _valid_single_solid(self.shoe, self.reaction_id)
        if any(v > _INTERSECTION_TOLERANCE_MM3 for v in self.nominal_source_intersections_mm3.values()):
            raise TreatmentCarrierCounterpartError("nominal treatment carrier intersects Cell 6 source material")
        if self.soft_landing_intersections_mm3.get("landing", 0.0) <= _INTERSECTION_TOLERANCE_MM3:
            raise TreatmentCarrierCounterpartError("soft landing probe does not engage landing tongue")
        if self.soft_landing_intersections_mm3.get("detent", 0.0) <= _INTERSECTION_TOLERANCE_MM3:
            raise TreatmentCarrierCounterpartError("soft landing probe does not engage compliant detent")
        if self.soft_landing_intersections_mm3.get("rigid_rail", 0.0) > _INTERSECTION_TOLERANCE_MM3:
            raise TreatmentCarrierCounterpartError("soft landing reaches rigid rail before compliant features")
        if self.rigid_stop_intersection_mm3 <= _INTERSECTION_TOLERANCE_MM3:
            raise TreatmentCarrierCounterpartError("carrier lacks positive rigid overtravel stop")
        if self.lateral_preload_intersection_mm3 <= _INTERSECTION_TOLERANCE_MM3:
            raise TreatmentCarrierCounterpartError("carrier lacks compliant lateral preload engagement")
        if self.lateral_rail_intersection_mm3 > _INTERSECTION_TOLERANCE_MM3:
            raise TreatmentCarrierCounterpartError("preload probe reaches rigid rail before preload feature")
        if min(self.vertical_capture_intersections_mm3) <= _INTERSECTION_TOLERANCE_MM3:
            raise TreatmentCarrierCounterpartError("carrier channel does not positively capture both Z directions")

    def manifest(self) -> dict[str, object]:
        return {
            "reaction_id": self.reaction_id,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "center_xy_mm": list(self.center_xy_mm),
            "semantics": "TREATMENT_OWNED_FEMALE_TAPERED_RAIL_SHOE_WITH_RIGID_UNDERSIDE_CAPTURE_AND_PROGRESSIVE_LANDING",
            "working_load_path": "RIGID_CHANNEL_AND_CELL6_KEYED_REACTION_MATE; PRELOAD_LEAF_AND_DETENT_ARE_NOT_PRIMARY_WORKING_REACTION_MEMBERS",
            "service_insertion_axis": "+Y_TO_-Y",
            "dimensions_mm": {
                "shoe_length": SHOE_LENGTH_MM,
                "shoe_wall": SHOE_WALL_MM,
                "root_side_clearance_seed": ROOT_SIDE_CLEARANCE_MM,
                "crown_side_clearance_seed": CROWN_SIDE_CLEARANCE_MM,
                "crown_underside_clearance_seed": CROWN_UNDERSIDE_CLEARANCE_MM,
                "crown_top_clearance_seed": CROWN_TOP_CLEARANCE_MM,
                "rigid_end_stop_gap_seed": RIGID_END_STOP_GAP_MM,
                "cell6_landing_gap_seed": NOMINAL_LANDING_GAP_MM,
                "cell6_detent_gap_seed": NOMINAL_COUNTERFACE_GAP_MM,
                "cell6_preload_gap_seed": NOMINAL_LATERAL_GAP_MM,
            },
            "measured": {
                "nominal_source_intersections_mm3": self.nominal_source_intersections_mm3,
                "soft_landing_probe_mm": SOFT_LANDING_PROBE_MM,
                "soft_landing_intersections_mm3": self.soft_landing_intersections_mm3,
                "rigid_end_stop_probe_mm": RIGID_END_STOP_PROBE_MM,
                "rigid_stop_intersection_mm3": self.rigid_stop_intersection_mm3,
                "preload_engagement_probe_mm": PRELOAD_ENGAGEMENT_PROBE_MM,
                "lateral_preload_intersection_mm3": self.lateral_preload_intersection_mm3,
                "lateral_rail_intersection_mm3": self.lateral_rail_intersection_mm3,
                "vertical_capture_probe_mm": VERTICAL_CAPTURE_PROBE_MM,
                "vertical_capture_intersections_mm3": list(self.vertical_capture_intersections_mm3),
                "shoe_volume_mm3": float(self.shoe.val().Volume()),
            },
            "continuous_whole_carrier_service_sweep": "OPEN",
            "force_friction_stiffness_fatigue_wear_acoustics": "PHYSICAL_VALIDATION_OPEN",
        }


@dataclass(frozen=True, slots=True)
class TreatmentCarrierCounterpartArchitecture:
    source_interface_architecture_sha256: str
    source_preload_architecture_sha256: str
    source_landing_architecture_sha256: str
    source_detent_architecture_sha256: str
    counterparts: tuple[TreatmentCarrierCounterpart, ...]
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        for value in (
            self.source_interface_architecture_sha256,
            self.source_preload_architecture_sha256,
            self.source_landing_architecture_sha256,
            self.source_detent_architecture_sha256,
        ):
            if len(value) != 64:
                raise TreatmentCarrierCounterpartError("source architecture identity must be SHA-256")
        if tuple(c.reaction_id for c in self.counterparts) != REACTION_IDS:
            raise TreatmentCarrierCounterpartError("all four treatment carrier counterparts must exist")
        if self.physical_validation_eligible:
            raise TreatmentCarrierCounterpartError("digital carrier geometry is not physical validation")

    @property
    def architecture_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        return hashlib.sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "source_interface_architecture_sha256": self.source_interface_architecture_sha256,
            "source_preload_architecture_sha256": self.source_preload_architecture_sha256,
            "source_landing_architecture_sha256": self.source_landing_architecture_sha256,
            "source_detent_architecture_sha256": self.source_detent_architecture_sha256,
            "counterparts": [c.manifest() for c in self.counterparts],
            "mechanical_status": "FOUR_TREATMENT_OWNED_FEMALE_COUNTERPARTS_REALIZED; POSTERIOR_SADDLE_AND_WHOLE_CARRIER_SWEEP_OPEN",
            "physical_validation_eligible": self.physical_validation_eligible,
        }
        if include_sha:
            payload["architecture_sha256"] = self.architecture_sha256
        return payload


def _counterpart_shape(interface, preload_feature, landing_feature, detent_feature) -> cq.Workplane:
    ibb = interface.interface.val().BoundingBox()
    pbb = preload_feature.preload_feature.val().BoundingBox()
    lbb = landing_feature.landing_feature.val().BoundingBox()
    dbb = detent_feature.detent_feature.val().BoundingBox()
    cx, cy = interface.center_xy_mm
    sign = 1.0 if cx >= 0.0 else -1.0
    z0 = float(ibb.zmin)

    stop_inner_y = cy - RAIL_LENGTH_MM / 2.0 + END_STOP_THICKNESS_MM
    negative_face_y = stop_inner_y + RIGID_END_STOP_GAP_MM
    center_y = negative_face_y + SHOE_LENGTH_MM / 2.0
    end_y = negative_face_y + SHOE_LENGTH_MM

    preload_outer = (float(pbb.xmax) - cx) if sign > 0.0 else (cx - float(pbb.xmin))
    upper_cavity_width = 2.0 * (preload_outer + NOMINAL_LATERAL_GAP_MM)
    outer_width = upper_cavity_width + 2.0 * SHOE_WALL_MM
    lower_throat_width = RAIL_ROOT_WIDTH_MM + 2.0 * ROOT_SIDE_CLEARANCE_MM

    z_bottom = z0 + SHOE_BOTTOM_OFFSET_MM
    lip_top = z0 + RAIL_HEIGHT_MM * 0.55 - CROWN_UNDERSIDE_CLEARANCE_MM
    upper_cavity_top = z0 + RAIL_HEIGHT_MM + CROWN_TOP_CLEARANCE_MM
    z_outer_top = max(float(pbb.zmax), float(lbb.zmax), float(dbb.zmax)) + SHOE_TOP_MARGIN_MM

    shoe = _box(outer_width, SHOE_LENGTH_MM, z_outer_top - z_bottom, (cx, center_y, z_bottom))
    throat = _box(lower_throat_width, SHOE_LENGTH_MM + 0.4, lip_top - z_bottom + 0.05, (cx, center_y, z_bottom - 0.05))
    upper = _box(upper_cavity_width, SHOE_LENGTH_MM + 0.4, upper_cavity_top - lip_top, (cx, center_y, lip_top))
    shoe = shoe.cut(throat.union(upper))

    central_clear_y0 = min(float(lbb.ymin), float(dbb.ymin)) - RELIEF_MARGIN_MM
    detent_pad_negative_y = float(dbb.ymax) + NOMINAL_COUNTERFACE_GAP_MM
    central_clear_width = max(float(lbb.xlen), float(dbb.xlen)) + 0.4
    shoe = shoe.cut(_box(
        central_clear_width,
        detent_pad_negative_y - central_clear_y0,
        z_outer_top - min(float(lbb.zmin), float(dbb.zmin)) + 0.2,
        (cx, (central_clear_y0 + detent_pad_negative_y) / 2.0, min(float(lbb.zmin), float(dbb.zmin)) - 0.1),
    ))

    counterface_x = (float(pbb.xmax) + NOMINAL_LATERAL_GAP_MM) if sign > 0.0 else (float(pbb.xmin) - NOMINAL_LATERAL_GAP_MM)
    if sign > 0.0:
        relief_x0, relief_x1 = float(pbb.xmin) - RELIEF_MARGIN_MM, counterface_x
    else:
        relief_x0, relief_x1 = counterface_x, float(pbb.xmax) + RELIEF_MARGIN_MM
    shoe = shoe.cut(_box(
        relief_x1 - relief_x0,
        float(pbb.ylen) + 2.0 * RELIEF_MARGIN_MM,
        z_outer_top - float(pbb.zmin) + 0.2,
        ((relief_x0 + relief_x1) / 2.0, cy, float(pbb.zmin) - 0.1),
    ))

    landing_z0 = float(ibb.zmax) - LANDING_ROOT_HEIGHT_MM + TONGUE_RISE_MM
    landing_pad_center_y = float(lbb.ymax) + NOMINAL_LANDING_GAP_MM + LANDING_PROBE_LENGTH_MM / 2.0
    pieces: list[cq.Workplane] = []
    for sx in (-1.0, 1.0):
        x = cx + sx * LANDING_PAD_X_OFFSET_MM
        pieces.append(_box(LANDING_PAD_WIDTH_MM, LANDING_PROBE_LENGTH_MM, LANDING_PROBE_HEIGHT_MM, (x, landing_pad_center_y, landing_z0)))
        rib_y0 = landing_pad_center_y + LANDING_PROBE_LENGTH_MM / 2.0
        pieces.append(_box(LANDING_PAD_WIDTH_MM, end_y - rib_y0, CONNECTOR_HEIGHT_MM, (x, (rib_y0 + end_y) / 2.0, landing_z0 + 0.08)))

    detent_z0 = float(ibb.zmax) - DETENT_ROOT_HEIGHT_MM + NOSE_RISE_MM
    detent_pad_center_y = float(dbb.ymax) + NOMINAL_COUNTERFACE_GAP_MM + NOSE_LENGTH_MM / 2.0
    pieces.append(_box(NOSE_WIDTH_MM, NOSE_LENGTH_MM, NOSE_HEIGHT_MM, (cx, detent_pad_center_y, detent_z0)))
    detent_y0 = detent_pad_center_y + NOSE_LENGTH_MM / 2.0
    pieces.append(_box(NOSE_WIDTH_MM, end_y - detent_y0, 0.45, (cx, (detent_y0 + end_y) / 2.0, detent_z0 + 0.15)))

    for piece in pieces:
        shoe = shoe.union(piece)
    return shoe.clean()


def build_treatment_carrier_counterparts(
    *,
    interfaces: StructuralFrameCarrierInterfaceArchitecture | None = None,
    preload: StructuralFrameCarrierPreloadArchitecture | None = None,
    landing: StructuralFrameCarrierLandingArchitecture | None = None,
    detent: StructuralFrameCarrierDetentArchitecture | None = None,
) -> TreatmentCarrierCounterpartArchitecture:
    interfaces = build_structural_frame_carrier_interfaces() if interfaces is None else interfaces
    preload = build_structural_frame_carrier_preload(interfaces=interfaces) if preload is None else preload
    landing = build_structural_frame_carrier_landing(interfaces=interfaces) if landing is None else landing
    detent = build_structural_frame_carrier_detent(interfaces=interfaces) if detent is None else detent

    pmap = {item.reaction_id: item for item in preload.features}
    lmap = {item.reaction_id: item for item in landing.features}
    dmap = {item.reaction_id: item for item in detent.features}
    built: list[TreatmentCarrierCounterpart] = []

    for source in interfaces.interfaces:
        p = pmap[source.reaction_id]
        l = lmap[source.reaction_id]
        d = dmap[source.reaction_id]
        shoe = _counterpart_shape(source, p, l, d)
        _valid_single_solid(shoe, source.reaction_id)
        nominal = {
            "rigid_rail": round(_intersection_volume(shoe, source.interface), 8),
            "preload": round(_intersection_volume(shoe, p.preload_feature), 8),
            "landing": round(_intersection_volume(shoe, l.landing_feature), 8),
            "detent": round(_intersection_volume(shoe, d.detent_feature), 8),
        }
        soft = shoe.translate((0.0, -SOFT_LANDING_PROBE_MM, 0.0))
        soft_intersections = {
            "landing": round(_intersection_volume(soft, l.landing_feature), 8),
            "detent": round(_intersection_volume(soft, d.detent_feature), 8),
            "rigid_rail": round(_intersection_volume(soft, source.interface), 8),
        }
        rigid = round(_intersection_volume(shoe.translate((0.0, -RIGID_END_STOP_PROBE_MM, 0.0)), source.interface), 8)
        sign = 1.0 if source.center_xy_mm[0] >= 0.0 else -1.0
        lateral = shoe.translate((-sign * PRELOAD_ENGAGEMENT_PROBE_MM, 0.0, 0.0))
        lateral_preload = round(_intersection_volume(lateral, p.preload_feature), 8)
        lateral_rail = round(_intersection_volume(lateral, source.interface), 8)
        vertical = (
            round(_intersection_volume(shoe.translate((0.0, 0.0, -VERTICAL_CAPTURE_PROBE_MM)), source.interface), 8),
            round(_intersection_volume(shoe.translate((0.0, 0.0, VERTICAL_CAPTURE_PROBE_MM)), source.interface), 8),
        )
        built.append(TreatmentCarrierCounterpart(
            source.reaction_id,
            source.center_xy_mm,
            shoe,
            nominal,
            soft_intersections,
            rigid,
            lateral_preload,
            lateral_rail,
            vertical,
        ))

    result = TreatmentCarrierCounterpartArchitecture(
        interfaces.architecture_sha256,
        preload.architecture_sha256,
        landing.architecture_sha256,
        detent.architecture_sha256,
        tuple(built),
        False,
    )
    result.__post_init__()
    return result


def export_treatment_carrier_counterparts(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    architecture = build_treatment_carrier_counterparts()
    for item in architecture.counterparts:
        cq.exporters.export(item.shoe, str(output_dir / f"{item.reaction_id.lower()}_treatment_carrier_shoe.step"))
    manifest = architecture.manifest()
    (output_dir / "treatment_carrier_counterparts_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest
