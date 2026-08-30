from dataclasses import replace

import pytest

from masck_one.alpha_closure import AlphaClosureError
from masck_one.model import build_model
from masck_one.quarter_architecture import build_quarter_architecture
from masck_one.wearable_architecture import CONTROL_STATE_PRINCIPLES, WearableArchitectureError


@pytest.fixture(scope="module")
def architecture():
    return build_quarter_architecture(build_model())


def test_quick_release_preserves_frozen_safety_contract(architecture):
    release = architecture.wearable.quick_release
    assert release.release_time_max_s == 2.0
    assert release.target_force_N == (5.0, 12.0)
    assert release.one_hand_wet_unpowered is True
    with pytest.raises(WearableArchitectureError, match="one-hand wet unpowered"):
        replace(architecture.wearable, quick_release=replace(release, one_hand_wet_unpowered=False))


def test_retention_and_battery_are_frame_and_authority_bound(architecture):
    wearable = architecture.wearable
    assert wearable.source_structural_frame_sha256 == architecture.structural_frame.topology_sha256
    assert wearable.retention.support_roles == ("HALO", "OCCIPITAL", "CROWN")
    assert len(wearable.retention.cad_interface_references().val().Vertices()) == 5
    assert wearable.dry_bay.battery_envelope_mm == (34.5, 52.0, 6.3)
    assert wearable.dry_bay.swelling_clearance_mm is None


def test_hmi_has_four_controls_without_invented_positions(architecture):
    hmi = architecture.wearable.hmi
    assert len(hmi.controls) == 4
    assert hmi.state_principles == CONTROL_STATE_PRINCIPLES
    assert all(control.position_mm is None for control in hmi.controls)
    assert hmi.controls[-1].semantic_reservation == "UNASSIGNED_PENDING_FIRMWARE_CONTRACT"


def test_thermal_modes_remain_evidence_gated(architecture):
    thermal = architecture.wearable.thermal
    assert "UNRESOLVED" in thermal.warm_heater_geometry_status
    assert "EXPERIMENTAL_RESERVATION" in thermal.cool_implementation_status
    assert "BLOCKED" in thermal.cool_dew_point_model_status


def test_every_cavity_has_one_controlled_hygiene_class(architecture):
    cavities = architecture.alpha_closure.hygiene_cavities
    allowed = {"DRY_ALWAYS", "WET_DRAINABLE", "WET_REMOVABLE", "SEALED_NONUSER"}
    assert len({cavity.cavity_id for cavity in cavities}) == len(cavities)
    assert all(cavity.hygiene_class in allowed for cavity in cavities)


def test_assembly_hierarchy_has_valid_parent_graph(architecture):
    nodes = architecture.alpha_closure.assembly_nodes
    ids = {node.node_id for node in nodes}
    assert "MASCK_ONE_ASSEMBLY" in ids
    assert all(node.parent_id is None or node.parent_id in ids for node in nodes)


def test_dfm_contract_consumes_authority_without_inventing_bosses(architecture):
    dfm = architecture.alpha_closure.dfm
    assert dfm.shell_nominal_wall_mm == 1.8
    assert dfm.shell_development_min_mm == 1.5
    assert dfm.nominal_draft_deg == 1.0
    assert dfm.rib_thickness_ratio_range == (0.4, 0.6)
    assert dfm.visible_seam_gap_mm == 0.4
    assert "UNRESOLVED" in dfm.boss_geometry_status


def test_mass_ledger_reports_known_subtotal_but_refuses_false_closure(architecture):
    ledgers = architecture.alpha_closure.ledgers
    assert ledgers.known_dry_mass_g == pytest.approx(52.4)
    assert ledgers.mass_ledger_complete is False
    assert ledgers.known_component_cg_mm is not None
    assert "INCOMPLETE" in ledgers.closure_status
    assert "BLOCKED" in ledgers.runtime_status


def test_alpha_release_does_not_claim_physical_mvp(architecture):
    alpha = architecture.alpha_closure
    assert alpha.completed_iterations == tuple(range(35, 41))
    assert alpha.release.required_physical_gate_iterations == tuple(range(41, 51))
    assert alpha.release.integrated_mvp_gate_iteration == 64
    assert alpha.physical_validation_eligible is False
    assert "BLOCKED" in alpha.physical_mvp_status
    with pytest.raises(AlphaClosureError, match="physical MVP evidence"):
        replace(alpha, physical_validation_eligible=True)
