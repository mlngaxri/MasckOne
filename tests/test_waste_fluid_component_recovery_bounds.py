from dataclasses import replace

import pytest

from masck_one.waste_fluid_accounting import WasteFluidAccountingError
from masck_one.waste_fluid_component_recovery_bounds import (
    DeliveryComponentRecoveryEnvelope,
    reduce_component_recovery_bounds,
)
from masck_one.waste_fluid_delivery_recovery import build_authority_delivery_recovery_ledger


def test_authority_service_component_bounds_are_tight_without_mixing_assumption():
    envelope = reduce_component_recovery_bounds()
    face, cleanser, post = envelope.components
    assert face.introduced_mL == pytest.approx(19.2)
    assert face.minimum_recovered_mL == pytest.approx(16.44)
    assert face.maximum_recovered_mL == pytest.approx(19.2)
    assert face.maximum_nonrecovered_mL == pytest.approx(2.76)
    assert cleanser.introduced_mL == pytest.approx(3.6)
    assert cleanser.minimum_recovered_mL == pytest.approx(0.84)
    assert cleanser.maximum_recovered_mL == pytest.approx(3.6)
    assert cleanser.maximum_nonrecovered_mL == pytest.approx(2.76)
    assert post.introduced_mL == pytest.approx(4.8)
    assert post.minimum_recovered_mL == pytest.approx(2.04)
    assert post.maximum_recovered_mL == pytest.approx(4.8)
    assert post.maximum_nonrecovered_mL == pytest.approx(2.76)


def test_partial_service_scales_bounds_from_exact_delivery_ledger():
    envelope = reduce_component_recovery_bounds(build_authority_delivery_recovery_ledger(cycles=2))
    face, cleanser, post = envelope.components
    assert face.minimum_recovered_mL == pytest.approx(5.48)
    assert cleanser.minimum_recovered_mL == pytest.approx(0.28)
    assert post.minimum_recovered_mL == pytest.approx(0.68)
    assert all(item.maximum_nonrecovered_mL == pytest.approx(0.92) for item in envelope.components)


def test_component_bound_forgery_fails_closed():
    envelope = reduce_component_recovery_bounds()
    forged = replace(envelope.components[1], minimum_recovered_mL=envelope.components[1].minimum_recovered_mL + 0.01)
    with pytest.raises(WasteFluidAccountingError, match="does not reconcile"):
        DeliveryComponentRecoveryEnvelope(envelope.source_ledger, (envelope.components[0], forged, envelope.components[2]))


def test_component_identity_and_source_volume_forgery_fail_closed():
    envelope = reduce_component_recovery_bounds()
    with pytest.raises(WasteFluidAccountingError, match="canonical"):
        DeliveryComponentRecoveryEnvelope(envelope.source_ledger, tuple(reversed(envelope.components)))
    forged = replace(envelope.components[0], introduced_mL=envelope.components[0].introduced_mL + 0.01)
    with pytest.raises(WasteFluidAccountingError, match="disagrees with delivery ledger"):
        DeliveryComponentRecoveryEnvelope(envelope.source_ledger, (forged, envelope.components[1], envelope.components[2]))


def test_component_envelope_requires_exact_delivery_ledger():
    envelope = reduce_component_recovery_bounds()
    with pytest.raises(WasteFluidAccountingError, match="exact delivery ledger"):
        DeliveryComponentRecoveryEnvelope(object(), envelope.components)
