from __future__ import annotations

import pytest

from masck_one.thermal_heat_rejection import (
    PATH,
    CoolHeatRejectionPath,
    required_external_sink_energy_J,
)
from masck_one.warm_cool_package import WarmCoolPackageError


def test_cool_heat_has_explicit_external_dock_path() -> None:
    manifest = CoolHeatRejectionPath().manifest()
    assert manifest["heat_rejection_path"] == list(PATH)
    assert PATH[-2:] == ("EXTERNAL_DOCK_THERMAL_SINK", "AMBIENT")
    assert manifest["dock_interface"]["package_id"] == "COOL-DOCK-HEAT-REJECTION-INTERFACE"
    assert manifest["cool_technology"] is None
    assert manifest["onboard_heat_sink_claimed"] is False
    assert manifest["external_dock_sink_performance_validated"] is False


def test_cool_path_cannot_bypass_dock() -> None:
    with pytest.raises(WarmCoolPackageError):
        CoolHeatRejectionPath(
            stages=("TREATMENT_INTERFACE", "DEVICE_THERMAL_SPREADER", "AMBIENT")
        )


def test_cool_path_cannot_claim_unvalidated_sink() -> None:
    with pytest.raises(WarmCoolPackageError):
        CoolHeatRejectionPath(external_dock_sink_performance_validated=True)


def test_sink_energy_is_input_driven_not_capability_claim() -> None:
    assert required_external_sink_energy_J(heat_to_reject_J=12.0, transfer_efficiency=0.75) == pytest.approx(16.0)
    with pytest.raises(WarmCoolPackageError):
        required_external_sink_energy_J(heat_to_reject_J=12.0, transfer_efficiency=0.0)
    with pytest.raises(WarmCoolPackageError):
        required_external_sink_energy_J(heat_to_reject_J=-1.0, transfer_efficiency=0.8)
