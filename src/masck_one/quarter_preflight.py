from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math

from .model import build_model
from .quarter_architecture import build_quarter_architecture
from .spatial import Point2
from .waste_architecture import REQUIRED_FAULT_STATES


@dataclass(frozen=True, slots=True)
class QuarterPreflightCheck:
    id: str
    status: str
    message: str
    actual: object | None = None
    expected: object | None = None

    def to_dict(self) -> dict[str, object | None]:
        return asdict(self)


def run_quarter_preflight() -> dict[str, object]:
    model = build_model()
    authority = model.authority
    quarter = build_quarter_architecture(model)
    simulation = quarter.contact_simulation
    frame = quarter.structural_frame
    actuation = quarter.actuation
    fluid = quarter.fresh_fluid
    manifold = quarter.distribution_manifold
    waste = quarter.waste
    wearable = quarter.wearable
    alpha = quarter.alpha_closure

    actuator_shapes = actuation.cad_envelopes()
    swept_shapes = actuation.swept_envelopes()
    outer_x, outer_y = authority.pair("geometry", "outer_xy_envelope_mm")
    swept_inside_xy = all(
        shape.val().BoundingBox().xlen < outer_x and shape.val().BoundingBox().ylen < outer_y
        for shape in swept_shapes
    )
    reservoir_shape = fluid.reservoir.cad_envelope()
    pump_shapes = tuple(station.cad_envelope() for station in fluid.pump_stations)

    def overlap_volume(left, right) -> float:
        return float(left.intersect(right).val().Volume())

    packaging_shapes = (reservoir_shape, *pump_shapes, *swept_shapes)
    collision_pairs = {
        f"{left_index}:{right_index}": overlap_volume(left, right)
        for left_index, left in enumerate(packaging_shapes)
        for right_index, right in enumerate(
            packaging_shapes[left_index + 1 :], start=left_index + 1
        )
    }

    checks = [
        QuarterPreflightCheck(
            "CONTINUATION_SCOPE",
            "PASS" if quarter.completed_iteration_floor == 40 else "FAIL",
            "Candidate implementation continues coherently through the digital Alpha release boundary.",
            {"iteration": quarter.completed_iteration_floor},
            40,
        ),
        QuarterPreflightCheck(
            "ITERATION14_CONTACT_FRAMEWORK",
            "PASS" if (
                len(simulation.cases) == 12
                and simulation.material_card.evidence_eligible is False
                and simulation.material_card.parameters == ()
                and dict(simulation.pressure_limits_kPa)["bridge_p95_max_kPa"]
                == authority.number("safety", "pressure", "bridge_p95_max_kPa")
                and simulation.physical_validation_eligible is False
            ) else "FAIL",
            "The merged Iteration-14 contact framework remains source-bound and evidence-gated without invented material constants or a simulated physical pass.",
        ),
        QuarterPreflightCheck(
            "ITERATION15_STRUCTURAL_FRAME",
            "PASS" if (
                frame.functional_frame_xy_mm == authority.pair("geometry", "functional_frame_xy_mm")
                and len(frame.datums) == 5
                and len(frame.reservations) == 6
                and frame.cross_section_dimensions_mm is None
                and frame.material_selection is None
                and frame.source_attachment_topology_sha256 == simulation.source_attachment_topology_sha256
                and frame.physical_validation_eligible is False
            ) else "FAIL",
            "The merged structural reaction topology, datum network and subsystem reservations are authority-bound while 3D members, section and material remain unresolved.",
        ),
        QuarterPreflightCheck(
            "ITERATION16_CLASS_A_WORKFLOW",
            "PASS" if (
                quarter.class_a_workflow.rms_limit_mm
                == authority.number("manufacturing", "a_surface", "rms_deviation_max_mm")
                and quarter.class_a_workflow.maximum_limit_mm
                == authority.number("manufacturing", "a_surface", "max_deviation_mm")
                and quarter.class_a_workflow.reference_surface_id is None
            ) else "FAIL",
            "Class-A deviation governance consumes authority limits and remains blocked until a released reference surface exists.",
        ),
        QuarterPreflightCheck(
            "ITERATIONS17_19_ACTUATION",
            "PASS" if (
                len(actuation.stations) == int(authority.number("actuation", "count"))
                and len(actuator_shapes) == len(swept_shapes) == 4
                and all(shape.val().Volume() > 0.0 for shape in (*actuator_shapes, *swept_shapes))
                and swept_inside_xy
                and actuation.axis_angle_doe_deg
                == tuple(float(v) for v in authority.get("actuation", "clean", "axis_angle_doe_deg"))
                and actuation.frequency_doe_hz == (20.0, 40.0, 80.0, 120.0)
                and actuation.physical_validation_eligible is False
            ) else "FAIL",
            "Four local frames, development supplier envelopes, DOE swept volumes and impedance handoff are deterministic without freezing mounts or efficacy.",
        ),
        QuarterPreflightCheck(
            "ITERATION20_WATER_RESERVOIR",
            "PASS" if (
                math.isclose(math.prod(fluid.reservoir.development_envelope_mm) / 1000.0,
                             authority.number("fluid", "water_reservoir", "gross_mL"), abs_tol=1e-9)
                and fluid.reservoir.minimum_usable_mL
                == authority.number("fluid", "water_reservoir", "minimum_usable_mL")
            ) else "FAIL",
            "Reservoir architecture preserves gross and usable-volume authority while fill, vent, service and dead volume remain gated.",
        ),
        QuarterPreflightCheck(
            "ITERATION21_CLEANSER_ARCHITECTURE",
            "PASS" if (
                fluid.cleanser.dose_per_cycle_mL
                == authority.number("fluid", "clean_cycle", "cleanser_mL")
                and fluid.cleanser.storage_capacity_mL is None
                and "UNRESOLVED" in fluid.cleanser.refill_interface_status
            ) else "FAIL",
            "Cleanser dose is authoritative; storage, refill, compatibility and purge geometry are not invented.",
        ),
        QuarterPreflightCheck(
            "ITERATION22_PUMP_AND_TUBING",
            "PASS" if (
                len(fluid.pump_stations) == 2
                and {station.fluid_role for station in fluid.pump_stations} == {"WATER", "CLEANSER"}
                and all(station.cad_envelope().val().Volume() > 0.0 for station in fluid.pump_stations)
                and all(
                    value is None
                    for station in fluid.pump_stations
                    for value in (station.tubing_inner_diameter_mm, station.minimum_bend_radius_mm, station.connector_standard)
                )
                and all("MANIFOLD_I23" in route or "TO_PUMP" in route for route in fluid.route_ids)
                and fluid.physical_validation_eligible is False
                and all(volume <= 1e-9 for volume in collision_pairs.values())
            ) else "FAIL",
            "Separate fresh-fluid pump packaging and route interfaces feed the controlled Iteration-23 manifold boundary.",
            {"packaging_overlap_volume_mm3": collision_pairs},
            "all pairwise overlap volumes <= 1e-9 mm3",
        ),
        QuarterPreflightCheck(
            "ITERATIONS23_24_MANIFOLD_AND_DISTRIBUTION",
            "PASS" if (
                manifold.source_coverage_sha256 == model.coverage_mesh.segmentation_sha256
                and len([outlet for outlet in manifold.outlets if outlet.fluid_role == "WATER"])
                == int(authority.number("fluid", "outlets", "water_count_first_manifold"))
                and len([outlet for outlet in manifold.outlets if outlet.fluid_role == "CLEANSER"])
                == int(authority.number("fluid", "outlets", "cleanser_count_first_manifold"))
                and all(
                    not model.protected_volumes.excluded_xy(
                        Point2(outlet.center_mm.x, outlet.center_mm.y)
                    )
                    for outlet in manifold.outlets
                )
                and all(abs(outlet.direction.z) <= 1e-12 for outlet in manifold.outlets)
                and all(
                    value is None
                    for branch in manifold.branches
                    for value in (branch.nominal_inner_diameter_mm, branch.metering_restriction_geometry)
                )
                and all(
                    groove.width_mm is groove.depth_mm is groove.length_mm is None
                    for groove in manifold.grooves
                )
                and manifold.physical_validation_eligible is False
            ) else "FAIL",
            "First-manifold counts, target-only outlets and lateral groove intent are deterministic without inventing bores, restrictions or groove dimensions.",
        ),
        QuarterPreflightCheck(
            "ITERATION25_WASTE_ACQUISITION",
            "PASS" if (
                waste.source_coverage_sha256 == model.coverage_mesh.segmentation_sha256
                and len(waste.acquisition_paths) == len(waste.transient_buffers) == 4
                and len({path.source_triangle_index for path in waste.acquisition_paths}) == 4
                and all(path.gutter_width_mm is path.gutter_depth_mm is None for path in waste.acquisition_paths)
                and all(buffer.usable_capacity_mL is None for buffer in waste.transient_buffers)
                and sum(
                    edge.Length() for edge in waste.cad_acquisition_centerlines().val().Edges()
                ) > 0.0
            ) else "FAIL",
            "Regional acquisition, capillary/gutter centerlines and transient-buffer handoffs are explicit while hydraulic dimensions remain rig-gated.",
        ),
        QuarterPreflightCheck(
            "ITERATION26_MIXED_PHASE_PUMP_AND_FAULTS",
            "PASS" if (
                waste.pump_station.cad_envelope().val().Volume() > 0.0
                and set(waste.pump_station.fault_state_ids) == set(REQUIRED_FAULT_STATES)
                and "REQUIRES_ITERATION45_RIG" in waste.pump_station.mixed_phase_status
            ) else "FAIL",
            "Waste-pump packaging enumerates every required fault state and does not infer mixed-phase performance from a fresh-fluid datasheet.",
        ),
        QuarterPreflightCheck(
            "ITERATION27_CARTRIDGE",
            "PASS" if (
                waste.cartridge.external_envelope_mm
                == tuple(float(value) for value in authority.get("fluid", "cartridge", "external_envelope_mm"))
                and math.isclose(
                    math.prod(waste.cartridge.capacity_reservation_envelope_mm) / 1000.0,
                    authority.number("fluid", "cartridge", "retained_capacity_min_mL"),
                    abs_tol=1e-9,
                )
                and waste.cartridge.retained_capacity_status == "VALIDATION_GATED"
                and math.isclose(
                    waste.cartridge.cad_external_envelope().intersect(
                        waste.cartridge.cad_capacity_reservation()
                    ).val().Volume(),
                    waste.cartridge.cad_capacity_reservation().val().Volume(),
                    abs_tol=1e-6,
                )
            ) else "FAIL",
            "The keyed-cartridge contract preserves the authority envelope and reserves the retained-capacity target without claiming a sealed usable volume.",
        ),
        QuarterPreflightCheck(
            "ITERATION28_COMPLETE_FLUID_ROUTING",
            "PASS" if (
                len(waste.route_contracts) == len(fluid.route_ids) + 2
                and {route.route_id for route in waste.route_contracts}.issuperset(fluid.route_ids)
                and all(
                    value is None
                    for route in waste.route_contracts
                    for value in (
                        route.inner_diameter_mm,
                        route.minimum_bend_radius_mm,
                        route.dead_volume_mL,
                        route.service_clearance_mm,
                    )
                )
                and waste.pump_station.cad_envelope().intersect(
                    waste.cartridge.cad_external_envelope()
                ).val().Volume() <= 1e-9
            ) else "FAIL",
            "Every fresh and waste route has a stable interface contract while bend radius, dead volume and service clearance remain unresolved.",
        ),
        QuarterPreflightCheck(
            "ITERATIONS29_34_WEARABLE_POWER_HMI_THERMAL",
            "PASS" if (
                wearable.source_structural_frame_sha256 == frame.topology_sha256
                and wearable.retention.support_roles == ("HALO", "OCCIPITAL", "CROWN")
                and wearable.quick_release.one_hand_wet_unpowered
                and wearable.quick_release.release_time_max_s
                == authority.number("safety", "quick_release", "time_max_s")
                and wearable.dry_bay.battery_envelope_mm
                == tuple(float(value) for value in authority.get("battery_reference", "envelope_mm"))
                and wearable.dry_bay.swelling_clearance_mm is None
                and len(wearable.hmi.controls) == 4
                and all(control.position_mm is None for control in wearable.hmi.controls)
                and "EXPERIMENTAL_RESERVATION" in wearable.thermal.cool_implementation_status
                and wearable.physical_validation_eligible is False
            ) else "FAIL",
            "Retention, unpowered release, dry-bay, four-control HMI and WARM/COOL reservations preserve authority and unresolved evidence boundaries.",
        ),
        QuarterPreflightCheck(
            "ITERATIONS35_40_DIGITAL_ALPHA_CLOSURE",
            "PASS" if (
                len(alpha.hygiene_cavities) >= 7
                and all(cavity.hygiene_class in authority.get("manufacturing", "hygiene_classes") for cavity in alpha.hygiene_cavities)
                and alpha.dfm.nominal_draft_deg == authority.number("manufacturing", "mold_draft_nominal_deg")
                and alpha.ledgers.mass_ledger_complete is False
                and alpha.ledgers.known_dry_mass_g > 0.0
                and alpha.release.exact_head_ci_required
                and alpha.release.integrated_mvp_gate_iteration == 64
                and alpha.physical_validation_eligible is False
            ) else "FAIL",
            "Hygiene, assembly, DFM, ledgers and release manifests are digitally closed while incomplete mass/power/thermal and physical MVP gates remain blocked.",
        ),
        QuarterPreflightCheck(
            "EVIDENCE_BOUNDARY",
            "PASS" if all(not item for item in (
                simulation.physical_validation_eligible,
                frame.physical_validation_eligible,
                actuation.physical_validation_eligible,
                fluid.physical_validation_eligible,
                manifold.physical_validation_eligible,
                waste.physical_validation_eligible,
                wearable.physical_validation_eligible,
                alpha.physical_validation_eligible,
            )) else "FAIL",
            "No candidate iteration promotes digital architecture to physical fit, safety, efficacy, material, supplier or manufacturing evidence.",
        ),
    ]
    result = "PASS" if all(check.status == "PASS" for check in checks) else "FAIL"
    return {
        "project": "Masck One",
        "merged_dependency_iterations": [14, 15],
        "candidate_iterations": list(range(16, 41)),
        "result": result,
        "checks": [check.to_dict() for check in checks],
        "manifest": quarter.manifest(),
    }


def main() -> int:
    report = run_quarter_preflight()
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
