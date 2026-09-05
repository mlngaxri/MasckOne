from __future__ import annotations

import json

import cadquery as cq

from masck_one.export import export_release


def test_repository_release_smoke_emits_captive_latch_and_travel_contract(tmp_path) -> None:
    report = export_release(tmp_path)

    latch = report["digital_topology"]["right_quick_release_latch"]
    travel = report["digital_topology"]["right_quick_release_travel"]
    reset = report["digital_topology"]["right_quick_release_reset"]
    continuous = report["digital_topology"]["right_quick_release_continuous_sweep"]
    assembly = report["digital_topology"]["right_quick_release_assembly"]

    assert travel["source_latch_package_sha256"] == latch["package_sha256"]
    assert travel["travel_limits"]["minimum_offset_mm"] == 0.0
    assert travel["travel_limits"]["maximum_offset_mm"] == 7.3
    assert travel["inboard_hard_stop"]["positive_material_intersection_mm3"] > 0.0
    assert travel["outboard_hard_stop"]["positive_material_intersection_mm3"] > 0.0
    assert travel["captivity"]["no_loose_ejecting_slider_in_released_state"] is True
    assert travel["physical_validation_eligible"] is False

    assert continuous["source_latch_package_sha256"] == latch["package_sha256"]
    assert continuous["source_reset_package_sha256"] == reset["package_sha256"]
    assert continuous["exact_sweep"]["complete_withdrawal_interval_covered"] is True
    assert continuous["all_complete_withdrawal_collision_checks_clear"] is True
    assert continuous["full_head_removal_trajectory_included"] is False

    assert assembly["source_latch_package_sha256"] == latch["package_sha256"]
    assert assembly["source_reset_package_sha256"] == reset["package_sha256"]
    assert assembly["source_continuous_sweep_package_sha256"] == continuous["package_sha256"]
    assert assembly["assembly_sequence"][-1]["state_id"] == "ASSEMBLED_OPERATIONAL"
    assert assembly["assembly_sequence"][-1]["no_factory_teleportation_required"] is True
    assert assembly["assembly_sequence"][-1]["closure_positive_capture"] is True
    assert assembly["operational_preservation"]["exact_complete_withdrawal_sweep_vs_split_guide_mm3"] == 0.0
    assert assembly["positive_closure_retention"]["friction_only"] is False
    assert assembly["physical_validation_eligible"] is False

    required = {
        "right_latch_frame_socket.step",
        "right_latch_halo_tongue.step",
        "right_latch_captive_guide.step",
        "right_latch_flexure_cam_detent.step",
        "right_latch_captive_slider.step",
        "right_latch_continuous_withdrawal_sweep.step",
        "right_latch_exact_continuous_withdrawal_sweep.step",
        "right_latch_captive_slider_released_state.step",
        "right_latch_guide_lower_body.step",
        "right_latch_guide_upper_closure.step",
        "right_latch_guide_upper_closure_deflected.step",
        "right_latch_slider_factory_insertion_sweep.step",
        "right_latch_guide_assembled_reference.step",
    }
    assert required.issubset(set(report["exported_step_files"]))
    assert required.issubset(set(report["mechanism_artifacts"]))
    assert "right_quick_release_latch_manifest.json" in report["mechanism_artifacts"]
    assert "right_quick_release_continuous_sweep_manifest.json" in report["mechanism_artifacts"]
    assert "right_quick_release_assembly_manifest.json" in report["mechanism_artifacts"]

    for filename in required:
        path = tmp_path / filename
        assert path.is_file() and path.stat().st_size > 0
        shape = cq.importers.importStep(str(path)).val()
        assert shape.isValid()
        assert len(shape.Solids()) == 1

    assembly_path = tmp_path / "masck_one_development_assembly.step"
    assert assembly_path.is_file() and assembly_path.stat().st_size > 0
    development_assembly = cq.importers.importStep(str(assembly_path)).val()
    assert development_assembly.isValid()
    assert len(development_assembly.Solids()) >= 6

    disk_report = json.loads((tmp_path / "build_report.json").read_text(encoding="utf-8"))
    disk_latch = disk_report["digital_topology"]["right_quick_release_latch"]
    disk_travel = disk_report["digital_topology"]["right_quick_release_travel"]
    disk_continuous = disk_report["digital_topology"]["right_quick_release_continuous_sweep"]
    disk_assembly = disk_report["digital_topology"]["right_quick_release_assembly"]
    assert disk_latch["package_sha256"] == latch["package_sha256"]
    assert disk_travel["package_sha256"] == travel["package_sha256"]
    assert disk_continuous["package_sha256"] == continuous["package_sha256"]
    assert disk_assembly["package_sha256"] == assembly["package_sha256"]
    assert disk_report["mechanism_artifacts"] == report["mechanism_artifacts"]
