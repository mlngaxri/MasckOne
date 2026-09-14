from dataclasses import replace

import pytest

from masck_one.wet_dry_route_backbone import (
    ROUTE_ORDER,
    WetDryRouteError,
    released_backbone,
)


def test_released_backbone_preserves_waste_order_and_ownership() -> None:
    backbone = released_backbone()
    assert backbone.sequence == ROUTE_ORDER
    assert backbone.cartridge_body_owner == "EXTERNAL_CARTRIDGE_OWNER"
    assert backbone.removed_state_closure_status == "PHYSICAL_VALIDATION_OPEN"
    assert [i.fluid_identity for i in backbone.interfaces if "WASTE" in i.interface_id] == [
        "MIXED_WASTE",
        "MIXED_WASTE",
        "MIXED_WASTE",
    ]


def test_rejects_reordered_waste_topology() -> None:
    backbone = released_backbone()
    bad = list(backbone.sequence)
    bad[3], bad[4] = bad[4], bad[3]
    with pytest.raises(WetDryRouteError, match="fluid order"):
        replace(backbone, sequence=tuple(bad))


def test_rejects_claimed_cartridge_body_ownership() -> None:
    with pytest.raises(WetDryRouteError, match="cartridge-body ownership"):
        replace(released_backbone(), cartridge_body_owner="SUPPORT_LANE")


def test_rejects_unmeasured_removed_state_closure_claim() -> None:
    with pytest.raises(WetDryRouteError, match="physical-validation-open"):
        replace(released_backbone(), removed_state_closure_status="VALIDATED_LEAK_TIGHT")


def test_manifest_is_deterministic_and_keeps_performance_open() -> None:
    backbone = released_backbone()
    first = backbone.manifest()
    second = backbone.manifest()
    assert first == second
    assert len(first["manifest_sha256"]) == 64
    assert "seal_performance" in first["explicitly_unclaimed"]
    assert "pump_performance" in first["explicitly_unclaimed"]
