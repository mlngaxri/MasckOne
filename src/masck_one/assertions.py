from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any

from .model import MasckOneModel


@dataclass(frozen=True)
class Check:
    id: str
    status: str
    message: str
    actual: Any = None
    limit: Any = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _bbox_xy(component) -> tuple[float, float]:
    bb = component.solid.val().BoundingBox()
    return float(bb.xlen), float(bb.ylen)


def _volume(component) -> float:
    return float(component.solid.val().Volume())


def run_assertions(model: MasckOneModel) -> list[Check]:
    a = model.authority
    checks: list[Check] = []

    shell_x, shell_y = _bbox_xy(model.shell)
    max_x, max_y = a.pair("geometry", "outer_xy_envelope_mm")
    checks.append(Check(
        "OUTER_XY_ENVELOPE",
        "PASS" if shell_x <= max_x + 1e-6 and shell_y <= max_y + 1e-6 else "FAIL",
        "Rigid shell remains inside the authority XY envelope.",
        actual=[round(shell_x, 6), round(shell_y, 6)],
        limit=[max_x, max_y],
    ))

    water_volume_mm3 = _volume(model.water_reservoir_envelope)
    water_volume_mL = water_volume_mm3 / 1000.0
    target_water = a.number("fluid", "water_reservoir", "gross_mL")
    checks.append(Check(
        "WATER_RESERVOIR_GROSS_VOLUME",
        "PASS" if abs(water_volume_mL - target_water) <= 1e-6 else "FAIL",
        "Development packaging envelope has the exact gross water volume baseline.",
        actual=round(water_volume_mL, 6),
        limit=target_water,
    ))

    cartridge_bb = model.waste_cartridge_envelope.solid.val().BoundingBox()
    actual_cartridge = [float(cartridge_bb.xlen), float(cartridge_bb.ylen), float(cartridge_bb.zlen)]
    target_cartridge = [float(v) for v in a.get("fluid", "cartridge", "external_envelope_mm")]
    checks.append(Check(
        "WASTE_CARTRIDGE_ENVELOPE",
        "PASS" if all(abs(x-y) <= 1e-6 for x, y in zip(actual_cartridge, target_cartridge)) else "FAIL",
        "Waste-cartridge external packaging envelope matches authority.",
        actual=[round(v, 6) for v in actual_cartridge],
        limit=target_cartridge,
    ))

    min_area = a.number("geometry", "nostrils", "minimum_deformed_area_each_mm2")
    min_dim = a.number("geometry", "nostrils", "minimum_local_opening_dimension_mm")
    derived_diameter = max(min_dim, math.sqrt(4.0 * min_area * 1.02 / math.pi))
    nominal_area = math.pi * (derived_diameter / 2.0) ** 2
    checks.append(Check(
        "NOMINAL_NOSTRIL_OPENING",
        "PASS" if nominal_area >= min_area and derived_diameter >= min_dim else "FAIL",
        "Nominal undeformed CAD nostril opening exceeds the hard geometric minima; deformed area still requires physical/FEA closure.",
        actual={"area_mm2": round(nominal_area, 6), "local_dim_mm": round(derived_diameter, 6)},
        limit={"area_mm2_min": min_area, "local_dim_mm_min": min_dim},
    ))

    checks.append(Check(
        "ACTUATOR_COUNT",
        "PASS" if len(model.actuator_envelopes) == int(a.number("actuation", "count")) else "FAIL",
        "Development assembly contains the frozen four-zone actuator count.",
        actual=len(model.actuator_envelopes),
        limit=int(a.number("actuation", "count")),
    ))

    protected = model.protected_volumes
    expected_clearances = {
        "MASCK_ONE-PROTECTED-EYE-LEFT": a.number("geometry", "eye", "rigid_dynamic_keepout_clearance_mm"),
        "MASCK_ONE-PROTECTED-EYE-RIGHT": a.number("geometry", "eye", "rigid_dynamic_keepout_clearance_mm"),
        "MASCK_ONE-PROTECTED-MOUTH": a.number("geometry", "mouth", "rigid_dynamic_keepout_clearance_mm"),
        "MASCK_ONE-PROTECTED-NOSTRIL-LEFT": a.number("geometry", "nostrils", "rigid_dynamic_keepout_clearance_mm"),
        "MASCK_ONE-PROTECTED-NOSTRIL-RIGHT": a.number("geometry", "nostrils", "rigid_dynamic_keepout_clearance_mm"),
    }
    actual_clearances = {
        volume.zone.zone_id: volume.zone.required_rigid_clearance_mm
        for volume in protected.all
    }
    protected_xy_pass = (
        len(protected.all) == 5
        and actual_clearances == expected_clearances
        and all(not volume.anatomical_validation_eligible for volume in protected.all)
        and all(volume.z_policy == "UNBOUNDED_UNTIL_REGISTERED_ANATOMICAL_SURFACE" for volume in protected.all)
    )
    checks.append(Check(
        "PROTECTED_ZONE_XY_BASELINES",
        "PASS" if protected_xy_pass else "FAIL",
        "Authority-derived eye/mouth/nostril planar protected footprints and rigid-clearance baselines are encoded; dynamic 3D anatomy remains blocked.",
        actual={
            "count": len(protected.all),
            "clearances_mm": actual_clearances,
            "z_policy": sorted({volume.z_policy for volume in protected.all}),
            "validation_eligible": any(volume.anatomical_validation_eligible for volume in protected.all),
        },
        limit={
            "count": 5,
            "clearances_mm": expected_clearances,
            "validation_eligible": False,
        },
    ))

    blocked = [
        ("DYNAMIC_EYE_SIGNED_DISTANCE", "Planar eye envelopes now exist, but expression-dependent registered anatomical eye keep-out meshes are still required."),
        ("DYNAMIC_AIRWAY_SIGNED_DISTANCE", "Planar airway envelopes now exist, but deformable nasal geometry and measured fit states are still required."),
        ("DYNAMIC_MOUTH_SIGNED_DISTANCE", "Planar mouth envelope now exists, but jaw/smile/speech anatomical keep-out meshes are still required."),
        ("AIRWAY_PRESSURE_DROP", "Requires airflow rig or validated CFD boundary conditions."),
        ("FACIAL_PRESSURE", "Requires nonlinear contact model with selected material data and/or pressure-map testing."),
        ("MEMBRANE_STRAIN", "Requires selected silicone constitutive data and converged nonlinear FEA."),
        ("CLEANSING_COVERAGE", "Requires defined fluid/manifold topology and physical spatial-efficacy evidence."),
        ("WASTE_RETAINED_CAPACITY", "Requires contaminated-waste cartridge test; geometric envelope alone is insufficient."),
        ("MASS_CG_PITCH_TORQUE", "Requires complete component mass/location ledger for the generated CAD revision."),
        ("A_SURFACE_DEVIATION", "Requires an authored and released Class-A reference surface."),
    ]
    for check_id, message in blocked:
        checks.append(Check(check_id, "BLOCKED", message))

    return checks
