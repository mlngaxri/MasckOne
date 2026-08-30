from dataclasses import replace

import pytest

from masck_one.actuation_architecture import ActuationArchitectureError
from masck_one.fresh_fluid import FreshFluidArchitectureError
from masck_one.model import build_model
from masck_one.quarter_architecture import build_quarter_architecture
from masck_one.quarter_preflight import run_quarter_preflight
from masck_one.surface_workflow import SurfaceSample, SurfaceWorkflowError
from masck_one.spatial import Point2, Point3
from masck_one.waste_architecture import REQUIRED_FAULT_STATES, WasteArchitectureError


@pytest.fixture(scope="module")
def quarter():
    return build_quarter_architecture(build_model())


def test_continuation_scope_reaches_complete_waste_routing_architecture(quarter):
    assert quarter.completed_iteration_floor == 40
    assert all("MANIFOLD_I23" in route or "TO_PUMP" in route for route in quarter.fresh_fluid.route_ids)


def test_contact_framework_encodes_complete_controlled_doe_without_claiming_solver_readiness(quarter):
    framework = quarter.contact_simulation
    assert len(framework.cases) == 4 * 3
    assert len({case.case_id for case in framework.cases}) == 12
    assert framework.material_card.evidence_eligible is False
    assert framework.material_card.parameters == ()
    assert framework.physical_validation_eligible is False


def test_structural_frame_is_datum_complete_but_does_not_invent_section_or_material(quarter):
    frame = quarter.structural_frame
    assert frame.functional_frame_xy_mm == (155.0, 202.0)
    assert len(frame.datums) == 5
    assert len(frame.reservations) == 6
    assert frame.cross_section_dimensions_mm is None
    assert frame.material_selection is None
    assert frame.perimeter_reaction_path.source_attachment_edge_indices


def test_class_a_numeric_screen_remains_blocked_without_released_reference(quarter):
    workflow = quarter.class_a_workflow
    engineering = (SurfaceSample("A", Point3(0, 0, 0)), SurfaceSample("B", Point3(1, 0, 0)))
    reference = (SurfaceSample("A", Point3(0, 0, 0.1)), SurfaceSample("B", Point3(1, 0, 0.1)))
    report = workflow.evaluate(engineering, reference)
    assert report.numeric_gate_passed is True
    assert report.product_validation_status == "BLOCKED_UNTIL_RELEASED_CLASS_A_REFERENCE"
    with pytest.raises(SurfaceWorkflowError, match="identical"):
        workflow.evaluate(engineering, reference[:1])


def test_actuator_doe_generates_nominal_and_swept_solids(quarter):
    actuation = quarter.actuation
    assert actuation.frequency_doe_hz == (20.0, 40.0, 80.0, 120.0)
    assert len(actuation.cad_envelopes()) == len(actuation.swept_envelopes()) == 4
    assert all(solid.val().Volume() > 0.0 for solid in actuation.swept_envelopes())
    with pytest.raises(ActuationArchitectureError, match="controlled DOE"):
        actuation.cad_envelopes(angle_deg=62.0)


def test_fluid_architecture_preserves_volume_and_rejects_invented_tubing(quarter):
    fluid = quarter.fresh_fluid
    assert fluid.reservoir.cad_envelope().val().Volume() / 1000.0 == pytest.approx(6.5)
    assert fluid.cleanser.storage_capacity_mL is None
    reservoir = fluid.reservoir.cad_envelope()
    pumps = tuple(station.cad_envelope() for station in fluid.pump_stations)
    assert all(reservoir.intersect(pump).val().Volume() <= 1e-9 for pump in pumps)
    assert pumps[0].intersect(pumps[1]).val().Volume() <= 1e-9
    bad_station = replace(fluid.pump_stations[0], tubing_inner_diameter_mm=1.0)
    with pytest.raises(FreshFluidArchitectureError, match="Tubing dimensions"):
        replace(fluid, pump_stations=(bad_station, fluid.pump_stations[1]))


def test_manifold_outlets_match_authority_and_exclude_protected_openings(quarter):
    manifold = quarter.distribution_manifold
    water = [outlet for outlet in manifold.outlets if outlet.fluid_role == "WATER"]
    cleanser = [outlet for outlet in manifold.outlets if outlet.fluid_role == "CLEANSER"]
    assert len(water) == 18
    assert len(cleanser) == 6
    assert len({outlet.source_triangle_index for outlet in manifold.outlets}) == 24
    protected = build_model().protected_volumes
    assert all(
        not protected.excluded_xy(Point2(outlet.center_mm.x, outlet.center_mm.y))
        for outlet in manifold.outlets
    )
    assert all(outlet.direction.z == 0.0 for outlet in manifold.outlets)
    assert len(manifold.cad_outlet_references("WATER").val().Edges()) == 18
    assert len(manifold.cad_outlet_references("CLEANSER").val().Edges()) == 6


def test_manifold_keeps_hydraulic_and_groove_dimensions_evidence_gated(quarter):
    manifold = quarter.distribution_manifold
    assert all(branch.nominal_inner_diameter_mm is None for branch in manifold.branches)
    assert all(branch.metering_restriction_geometry is None for branch in manifold.branches)
    assert all(groove.width_mm is groove.depth_mm is groove.length_mm is None for groove in manifold.grooves)
    assert manifold.physical_validation_eligible is False


def test_waste_acquisition_is_target_bound_and_dimension_gated(quarter):
    waste = quarter.waste
    assert len(waste.acquisition_paths) == len(waste.transient_buffers) == 4
    assert len({path.source_triangle_index for path in waste.acquisition_paths}) == 4
    assert all(path.gutter_width_mm is path.gutter_depth_mm is None for path in waste.acquisition_paths)
    assert all(buffer.usable_capacity_mL is None for buffer in waste.transient_buffers)
    assert len(waste.cad_acquisition_centerlines().val().Wires()) == 4


def test_waste_pump_enumerates_faults_without_claiming_mixed_phase_performance(quarter):
    pump = quarter.waste.pump_station
    assert set(pump.fault_state_ids) == set(REQUIRED_FAULT_STATES)
    assert "REQUIRES_ITERATION45_RIG" in pump.mixed_phase_status
    assert pump.cad_envelope().val().Volume() == pytest.approx(25.0 * 25.0 * 8.2)


def test_cartridge_reserves_capacity_without_promoting_it_to_evidence(quarter):
    cartridge = quarter.waste.cartridge
    assert cartridge.external_envelope_mm == (74.0, 36.0, 20.0)
    assert cartridge.cad_capacity_reservation().val().Volume() / 1000.0 == pytest.approx(35.0)
    assert cartridge.retained_capacity_status == "VALIDATION_GATED"
    assert quarter.waste.physical_validation_eligible is False


def test_complete_fluid_routes_reject_invented_dimensions(quarter):
    routes = quarter.waste.route_contracts
    assert len(routes) == len(quarter.fresh_fluid.route_ids) + 2
    assert all(route.inner_diameter_mm is route.minimum_bend_radius_mm is None for route in routes)
    assert all(route.dead_volume_mL is route.service_clearance_mm is None for route in routes)
    with pytest.raises(WasteArchitectureError, match="Route dimensions"):
        replace(routes[0], inner_diameter_mm=1.0)


def test_quarter_preflight_passes():
    report = run_quarter_preflight()
    assert report["result"] == "PASS"
    assert all(check["status"] == "PASS" for check in report["checks"])
