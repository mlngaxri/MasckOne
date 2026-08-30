from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any

from .coverage import REGION_T_NOSE_PHILTRUM
from .interface_topology import ZONE_T_NOSE_PHILTRUM
from .model import MasckOneModel
from .nasal_subsystem import (
    ROLE_BRIDGE_DORSUM,
    ROLE_LOBE,
    ROLE_PHILTRUM,
    ROLE_SIDEWALL_LEFT,
    ROLE_SIDEWALL_RIGHT,
)


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
        actual=[round(shell_x, 6), round(shell_y, 6)], limit=[max_x, max_y],
    ))

    water_volume_mL = _volume(model.water_reservoir_envelope) / 1000.0
    target_water = a.number("fluid", "water_reservoir", "gross_mL")
    checks.append(Check(
        "WATER_RESERVOIR_GROSS_VOLUME", "PASS" if abs(water_volume_mL - target_water) <= 1e-6 else "FAIL",
        "Development packaging envelope has the exact gross water volume baseline.",
        actual=round(water_volume_mL, 6), limit=target_water,
    ))

    cartridge_bb = model.waste_cartridge_envelope.solid.val().BoundingBox()
    actual_cartridge = [float(cartridge_bb.xlen), float(cartridge_bb.ylen), float(cartridge_bb.zlen)]
    target_cartridge = [float(v) for v in a.get("fluid", "cartridge", "external_envelope_mm")]
    checks.append(Check(
        "WASTE_CARTRIDGE_ENVELOPE",
        "PASS" if all(abs(x-y) <= 1e-6 for x, y in zip(actual_cartridge, target_cartridge)) else "FAIL",
        "Waste-cartridge external packaging envelope matches authority.",
        actual=[round(v, 6) for v in actual_cartridge], limit=target_cartridge,
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
        "ACTUATOR_COUNT", "PASS" if len(model.actuator_envelopes) == int(a.number("actuation", "count")) else "FAIL",
        "Development assembly contains the frozen four-zone actuator count.",
        actual=len(model.actuator_envelopes), limit=int(a.number("actuation", "count")),
    ))

    protected = model.protected_volumes
    expected_clearances = {
        "MASCK_ONE-PROTECTED-EYE-LEFT": a.number("geometry", "eye", "rigid_dynamic_keepout_clearance_mm"),
        "MASCK_ONE-PROTECTED-EYE-RIGHT": a.number("geometry", "eye", "rigid_dynamic_keepout_clearance_mm"),
        "MASCK_ONE-PROTECTED-MOUTH": a.number("geometry", "mouth", "rigid_dynamic_keepout_clearance_mm"),
        "MASCK_ONE-PROTECTED-NOSTRIL-LEFT": a.number("geometry", "nostrils", "rigid_dynamic_keepout_clearance_mm"),
        "MASCK_ONE-PROTECTED-NOSTRIL-RIGHT": a.number("geometry", "nostrils", "rigid_dynamic_keepout_clearance_mm"),
    }
    actual_clearances = {volume.zone.zone_id: volume.zone.required_rigid_clearance_mm for volume in protected.all}
    protected_xy_pass = (
        len(protected.all) == 5
        and actual_clearances == expected_clearances
        and all(not volume.anatomical_validation_eligible for volume in protected.all)
        and all(volume.z_policy == "UNBOUNDED_UNTIL_REGISTERED_ANATOMICAL_SURFACE" for volume in protected.all)
    )
    checks.append(Check(
        "PROTECTED_ZONE_XY_BASELINES", "PASS" if protected_xy_pass else "FAIL",
        "Authority-derived eye/mouth/nostril planar protected footprints and rigid-clearance baselines are encoded; dynamic 3D anatomy remains blocked.",
        actual={"count": len(protected.all), "clearances_mm": actual_clearances, "z_policy": sorted({volume.z_policy for volume in protected.all}), "validation_eligible": any(volume.anatomical_validation_eligible for volume in protected.all)},
        limit={"count": 5, "clearances_mm": expected_clearances, "validation_eligible": False},
    ))

    regression = model.worn_pose_regression
    translation_limit = a.number("geometry", "misregistration", "translation_radial_max_mm")
    rotation_limit = a.number("geometry", "misregistration", "rotation_max_deg")
    pose_pass = (
        regression.pose_count == 459
        and abs(regression.maximum_sampled_radial_translation_mm - translation_limit) <= 1e-9
        and abs(regression.maximum_sampled_absolute_rotation_deg - rotation_limit) <= 1e-9
        and all(pose.translation_z_mm == 0.0 for pose in regression.poses)
        and regression.evidence_status == "DETERMINISTIC_DISCRETE_SCREEN_NOT_MEASURED_DONNING_DISTRIBUTION"
    )
    checks.append(Check(
        "WORN_POSE_HARD_ENVELOPE_SET", "PASS" if pose_pass else "FAIL",
        "Deterministic regression samples exercise the authority misregistration boundary without inventing Z translation or claiming a measured donning distribution.",
        actual={"pose_count": regression.pose_count, "max_radial_translation_mm": regression.maximum_sampled_radial_translation_mm, "max_abs_rotation_deg": regression.maximum_sampled_absolute_rotation_deg, "translation_z_mm": 0.0, "sha256": regression.sha256},
        limit={"pose_count": 459, "translation_radial_max_mm": translation_limit, "rotation_max_deg": rotation_limit, "translation_z_mm": 0.0},
    ))

    coverage = model.coverage_mesh
    coverage_pass = (
        len(coverage.triangles) == model.facial_surface.mesh.triangle_count
        and coverage.area_conservation_error_mm2 <= 1e-8
        and coverage.target_area_mm2 > 0.0
        and coverage.t_zone_target_area_mm2 > 0.0
        and coverage.philtrum_target_area_mm2 > 0.0
        and coverage.aggregate_min_percent == a.number("coverage", "aggregate_min_percent")
        and coverage.t_zone_min_percent == a.number("coverage", "t_zone_min_percent")
        and coverage.unexplained_hole_max_mm2 == a.number("coverage", "unexplained_hole_max_mm2")
        and coverage.anatomical_validation_eligible is False
        and len(coverage.segmentation_sha256) == 64
        and "NOT_ANATOMICAL_VALIDATION" in coverage.segmentation_status
    )
    checks.append(Check(
        "COVERAGE_MESH_TOPOLOGY", "PASS" if coverage_pass else "FAIL",
        "Facial target/protected/T-zone topology is deterministic, area-conserving, includes the nose-to-upper-lip target region, and carries the authority coverage thresholds without claiming efficacy.",
        actual={"triangle_count": len(coverage.triangles), "surface_triangle_count": model.facial_surface.mesh.triangle_count, "target_area_mm2": round(coverage.target_area_mm2, 6), "protected_area_mm2": round(coverage.protected_area_mm2, 6), "t_zone_target_area_mm2": round(coverage.t_zone_target_area_mm2, 6), "philtrum_target_area_mm2": round(coverage.philtrum_target_area_mm2, 6), "area_conservation_error_mm2": coverage.area_conservation_error_mm2, "aggregate_min_percent": coverage.aggregate_min_percent, "t_zone_min_percent": coverage.t_zone_min_percent, "hole_max_mm2": coverage.unexplained_hole_max_mm2, "anatomical_validation_eligible": coverage.anatomical_validation_eligible, "segmentation_sha256": coverage.segmentation_sha256},
        limit={"area_conservation_error_mm2_max": 1e-8, "aggregate_min_percent": a.number("coverage", "aggregate_min_percent"), "t_zone_min_percent": a.number("coverage", "t_zone_min_percent"), "hole_max_mm2": a.number("coverage", "unexplained_hole_max_mm2"), "anatomical_validation_eligible": False},
    ))

    interface = model.compliant_interface_topology
    nasal_thickness = interface.nasal_lobe_thickness_authority
    nose_zone = interface.zone_by_id[ZONE_T_NOSE_PHILTRUM]
    contact_components = interface.contact_component_count(coverage)
    interface_pass = (
        len(interface.assignments) == len(coverage.triangles)
        and abs(interface.contact_area_mm2 - coverage.target_area_mm2) <= 1e-8
        and abs(interface.protected_opening_area_mm2 - coverage.protected_area_mm2) <= 1e-8
        and abs(interface.t_zone_contact_area_mm2 - coverage.t_zone_target_area_mm2) <= 1e-8
        and contact_components == 1
        and nasal_thickness.center_thickness_mm == a.number("geometry", "nasal_lobe_membrane", "thickness_center_mm")
        and nasal_thickness.doe_mm == tuple(float(value) for value in a.get("geometry", "nasal_lobe_membrane", "thickness_doe_mm"))
        and nose_zone.nominal_thickness_mm is None
        and nose_zone.thickness_doe_mm == ()
        and interface.anatomical_validation_eligible is False
        and len(interface.topology_sha256) == 64
        and "NOT_CONTACT_FIT_MATERIAL_OR_EFFICACY_EVIDENCE" in interface.evidence_status
    )
    checks.append(Check(
        "COMPLIANT_INTERFACE_TOPOLOGY", "PASS" if interface_pass else "FAIL",
        "The main compliant interface is partitioned into deterministic contact/T-zone/protected-opening parameter zones without inventing global membrane thickness, material behavior or contact validation.",
        actual={"zone_count": len(interface.zones), "assignment_count": len(interface.assignments), "contact_area_mm2": round(interface.contact_area_mm2, 6), "protected_area_mm2": round(interface.protected_opening_area_mm2, 6), "t_zone_contact_area_mm2": round(interface.t_zone_contact_area_mm2, 6), "contact_component_count": contact_components, "nasal_lobe_center_thickness_mm": nasal_thickness.center_thickness_mm, "nasal_lobe_doe_mm": list(nasal_thickness.doe_mm), "nasal_thickness_application_status": nasal_thickness.application_status, "full_nose_t_zone_nominal_thickness_mm": nose_zone.nominal_thickness_mm, "anatomical_validation_eligible": interface.anatomical_validation_eligible, "topology_sha256": interface.topology_sha256},
        limit={"assignment_count": len(coverage.triangles), "contact_area_mm2": round(coverage.target_area_mm2, 6), "protected_area_mm2": round(coverage.protected_area_mm2, 6), "t_zone_contact_area_mm2": round(coverage.t_zone_target_area_mm2, 6), "contact_component_count": 1, "nasal_lobe_center_thickness_mm": a.number("geometry", "nasal_lobe_membrane", "thickness_center_mm"), "anatomical_validation_eligible": False},
    ))

    nasal = model.nasal_subsystem_topology
    central_targets = [
        triangle
        for triangle in coverage.triangles
        if triangle.region_id == REGION_T_NOSE_PHILTRUM and triangle.is_target
    ]
    central_ids = {triangle.triangle_index for triangle in central_targets}
    central_area = sum(triangle.area_mm2 for triangle in central_targets)
    role_areas = nasal.role_area_mm2
    lobe_role = nasal.role_by_id[ROLE_LOBE]
    unresolved_roles = [ROLE_BRIDGE_DORSUM, ROLE_SIDEWALL_LEFT, ROLE_SIDEWALL_RIGHT, ROLE_PHILTRUM]
    lobe_bb = model.nasal_interface.solid.val().BoundingBox()
    nasal_pass = (
        nasal.triangle_indices == frozenset(central_ids)
        and abs(nasal.total_target_area_mm2 - central_area) <= 1e-8
        and all(role_areas[role_id] > 0.0 for role_id in role_areas)
        and abs(role_areas[ROLE_SIDEWALL_LEFT] - role_areas[ROLE_SIDEWALL_RIGHT]) <= 1e-6
        and lobe_role.nominal_thickness_mm == a.number("geometry", "nasal_lobe_membrane", "thickness_center_mm")
        and lobe_role.thickness_doe_mm == tuple(float(value) for value in a.get("geometry", "nasal_lobe_membrane", "thickness_doe_mm"))
        and all(nasal.role_by_id[role_id].nominal_thickness_mm is None for role_id in unresolved_roles)
        and all(nasal.role_by_id[role_id].thickness_doe_mm == () for role_id in unresolved_roles)
        and model.nasal_interface.name == "nasal_lobe_membrane_reference"
        and abs(float(lobe_bb.zlen) - lobe_role.nominal_thickness_mm) <= 1e-9
        and nasal.anatomical_validation_eligible is False
        and len(nasal.topology_sha256) == 64
    )
    checks.append(Check(
        "DEDICATED_NASAL_SUBSYSTEM_TOPOLOGY", "PASS" if nasal_pass else "FAIL",
        "The central nose/T-zone is explicitly partitioned into bridge/dorsum, bilateral sidewalls, local-thickness nasal lobe and philtrum roles; the 0.30 mm authority thickness is localized to the lobe development role instead of being extrapolated across the whole saddle.",
        actual={
            "central_target_triangle_count": len(nasal.assignments),
            "central_target_area_mm2": round(nasal.total_target_area_mm2, 6),
            "role_area_mm2": {key: round(value, 6) for key, value in role_areas.items()},
            "left_right_sidewall_area_delta_mm2": round(abs(role_areas[ROLE_SIDEWALL_LEFT] - role_areas[ROLE_SIDEWALL_RIGHT]), 9),
            "lobe_nominal_thickness_mm": lobe_role.nominal_thickness_mm,
            "lobe_thickness_doe_mm": list(lobe_role.thickness_doe_mm),
            "lobe_reference_cad_z_thickness_mm": round(float(lobe_bb.zlen), 9),
            "non_lobe_numeric_thickness_assigned": any(nasal.role_by_id[role_id].nominal_thickness_mm is not None for role_id in unresolved_roles),
            "anatomical_validation_eligible": nasal.anatomical_validation_eligible,
            "topology_sha256": nasal.topology_sha256,
        },
        limit={
            "central_target_area_mm2": round(central_area, 6),
            "all_five_roles_positive_area": True,
            "left_right_sidewall_area_delta_mm2_max": 1e-6,
            "lobe_nominal_thickness_mm": a.number("geometry", "nasal_lobe_membrane", "thickness_center_mm"),
            "non_lobe_numeric_thickness_assigned": False,
            "anatomical_validation_eligible": False,
        },
    ))

    blocked = [
        ("DYNAMIC_EYE_SIGNED_DISTANCE", "Misregistration transforms and planar eye envelopes now exist, but expression-dependent registered anatomical eye volumes are still required."),
        ("DYNAMIC_AIRWAY_SIGNED_DISTANCE", "Dedicated nasal functional topology now exists, but deformable 3D nasal/airway geometry and measured fit states are still required."),
        ("DYNAMIC_MOUTH_SIGNED_DISTANCE", "Misregistration transforms and planar mouth envelope now exist, but jaw/smile/speech anatomical volumes are still required."),
        ("AIRWAY_PRESSURE_DROP", "Requires airflow rig or validated CFD boundary conditions."),
        ("FACIAL_PRESSURE", "Compliant-interface and nasal functional topologies now exist, but closure still requires selected material constitutive data, nonlinear contact analysis and/or measured pressure mapping."),
        ("MEMBRANE_STRAIN", "The 0.30 mm nasal-lobe authority is now localized in CAD/topology, but closure still requires selected silicone constitutive data and converged nonlinear FEA."),
        ("CLEANSING_COVERAGE", "Coverage and nose/T-zone target topology now exist; closure still requires actual delivery/actuation footprint plus physical spatial-efficacy evidence on eligible anatomy."),
        ("WASTE_RETAINED_CAPACITY", "Requires contaminated-waste cartridge test; geometric envelope alone is insufficient."),
        ("MASS_CG_PITCH_TORQUE", "Requires complete component mass/location ledger for the generated CAD revision."),
        ("A_SURFACE_DEVIATION", "Requires an authored and released Class-A reference surface."),
    ]
    for check_id, message in blocked:
        checks.append(Check(check_id, "BLOCKED", message))

    return checks
