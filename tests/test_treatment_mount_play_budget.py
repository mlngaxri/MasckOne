from __future__ import annotations

from masck_one.structural_frame_carrier_preload import NOMINAL_LATERAL_GAP_MM
from masck_one.treatment_carrier_counterpart import ROOT_SIDE_CLEARANCE_MM
from masck_one.treatment_mounted_four_zone import YOKE_X_CLEARANCE_MM

# studies is intentionally not a package; load the small architecture study by path.
import importlib.util
from pathlib import Path


_PATH = Path(__file__).resolve().parents[1] / "studies" / "treatment_mount_play_budget.py"
_SPEC = importlib.util.spec_from_file_location("treatment_mount_play_budget", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


def test_current_mount_is_not_mislabeled_as_nominally_preloaded():
    report = _MODULE.build_report()
    gaps = report["clearance_seeds_mm"]

    assert gaps["shoulder_yoke_total_x"] == 2.0 * YOKE_X_CLEARANCE_MM
    assert gaps["rail_shoe_root_total_x"] == 2.0 * ROOT_SIDE_CLEARANCE_MM
    assert gaps["cell6_preload_leaf_nominal_gap"] == NOMINAL_LATERAL_GAP_MM
    assert gaps["shoulder_yoke_total_x"] > 0.0
    assert gaps["cell6_preload_leaf_nominal_gap"] > 0.0
    assert report["nominal_elastic_preload_demonstrated"] is False
    assert "ONE_SIDED_RIGID_KINEMATIC_DATUM" in report["required_next_architecture"]


def test_free_play_audit_keeps_tactile_claims_physical_open():
    report = _MODULE.build_report()
    assert all(
        value > 0.0
        for value in report["uncoupled_geometric_rock_indicators_deg"].values()
    )
    assert "PERCEIVED_BUTTERY_FEEL_REQUIRE_PHYSICAL_VALIDATION" in report["evidence_firewall"]
