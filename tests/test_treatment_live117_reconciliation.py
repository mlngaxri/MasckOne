from __future__ import annotations

import importlib.util
from pathlib import Path


def _module():
    path = Path(__file__).resolve().parents[1] / "studies" / "treatment_live117_reconciliation.py"
    spec = importlib.util.spec_from_file_location("treatment_live117_reconciliation", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_live117_treatment_reconciliation_fails_closed_on_current_decisions():
    m = _module()
    report = m.build_report()

    assert report["source_bindings"]["cell6_head_sha"] == "3e840d52d641b429669928ab9e4c207f08086ca1"
    assert len(report["four_station_candidate"]) == 4
    assert report["four_station_candidate"]["ACTUATOR_REACTION_SUPERIOR_LEFT"]["axis_rotation_about_y_deg"] == -61.0
    assert report["four_station_candidate"]["ACTUATOR_REACTION_SUPERIOR_RIGHT"]["axis_rotation_about_y_deg"] == 61.0

    control = report["control"]
    assert control["nominal_1ms_force_margin_N"] > 0.04
    assert control["cases"]["delay_2ms"]["full_stroke"] is False
    assert control["cases"]["delay_4ms"]["hard_stop_exceeded"] is True
    assert "REJECTED_AS_V1_BASELINE" in control["observer_only_status"]

    saddle = report["saddle_stiffness"]
    assert saddle["worst_planar_span_mm"] > 47.0
    assert 28000.0 < saddle["minimum_modulus_MPa_for_current_section_at_allocation"] < 30000.0
    assert saddle["material_class_studies"]["UNFILLED_ENGINEERING_POLYMER_STUDY_2P5GPA"]["continuous_z_component_deflection_mm"] > 0.5
    assert saddle["material_class_studies"]["ALUMINUM_CLASS_STUDY_70GPA"]["continuous_z_component_deflection_mm"] < 0.03

    mount = report["mount"]
    assert "DELETE_THE_TREATMENT_STRIKE_REQUIREMENT_FOR_NEW_CENTRAL_DRAW_PIN_BORE" in mount["source_change"]
    assert "RX" in mount["female_counterpart_requirements"]["must_rigidly_react_working_load_dofs"]
    assert mount["whole_carrier_service_sweep"] == "OPEN_REQUIRES_BREP_ON_NEXT_INCREMENT"
