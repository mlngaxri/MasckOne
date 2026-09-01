from dataclasses import replace
import pytest
from masck_one.waste_acquisition import (
    BUFFER_UNRESOLVED,EVIDENCE_STATUS,GEOMETRY_UNRESOLVED,HYGIENE_WET_DRAINABLE,
    PHASE_MIXED_WASTE,REGIONS,ROUTE_DESTINATION,WasteAcquisitionArchitecture,
    WasteAcquisitionError,WasteRegionIntent,
)

def region(name=REGIONS[0]):
    return WasteRegionIntent(name,PHASE_MIXED_WASTE,HYGIENE_WET_DRAINABLE,GEOMETRY_UNRESOLVED,GEOMETRY_UNRESOLVED,BUFFER_UNRESOLVED,ROUTE_DESTINATION)

def architecture():
    return WasteAcquisitionArchitecture("a"*64,"2026-08-30-R1",0.90,400.0,tuple(region(r) for r in REGIONS),False,EVIDENCE_STATUS)

def test_topology_preserves_mixed_phase_and_unresolved_geometry():
    a=architecture()
    assert tuple(r.region_id for r in a.regions)==REGIONS
    assert all(r.phase_semantics==PHASE_MIXED_WASTE for r in a.regions)
    assert all(r.gutter_width_mm is r.gutter_depth_mm is r.transient_buffer_capacity_mL is None for r in a.regions)
    assert len(a.architecture_sha256)==64

def test_dimensions_cannot_be_invented():
    with pytest.raises(WasteAcquisitionError): replace(region(),gutter_width_mm=1.0)
    with pytest.raises(WasteAcquisitionError): replace(region(),transient_buffer_capacity_mL=0.5)

def test_status_promotion_and_wrong_phase_fail_closed():
    with pytest.raises(WasteAcquisitionError): replace(region(),phase_semantics="LIQUID")
    with pytest.raises(WasteAcquisitionError): replace(region(),transient_buffer_status="VALIDATED")
    with pytest.raises(WasteAcquisitionError): replace(architecture(),evidence_status="PHYSICAL_VALIDATED")
    with pytest.raises(WasteAcquisitionError): replace(architecture(),physical_validation_eligible=True)

def test_incomplete_duplicate_or_mutable_region_sets_fail_closed():
    a=architecture()
    with pytest.raises(WasteAcquisitionError): replace(a,regions=a.regions[:-1])
    with pytest.raises(WasteAcquisitionError): replace(a,regions=a.regions[:-1]+(region(REGIONS[0]),))
    with pytest.raises(WasteAcquisitionError): replace(a,regions=list(a.regions))

def test_hostile_string_subclasses_fail_at_controlled_boundaries():
    class Alias(str): pass
    with pytest.raises(WasteAcquisitionError): replace(region(),phase_semantics=Alias(PHASE_MIXED_WASTE))
    with pytest.raises(WasteAcquisitionError): replace(region(),region_id=Alias(REGIONS[0]))
    with pytest.raises(WasteAcquisitionError): replace(architecture(),evidence_status=Alias(EVIDENCE_STATUS))

def test_authority_performance_limits_are_not_promoted_to_measured_results():
    a=architecture()
    assert a.recovery_ratio_min==0.90
    assert a.residual_free_liquid_max_uL==400.0
    assert a.physical_validation_eligible is False
