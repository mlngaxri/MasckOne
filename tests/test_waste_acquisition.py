from dataclasses import replace

import pytest

from masck_one.boundary_release import build_verified_interface_boundary_topology
from masck_one.cleanser_storage import build_cleanser_storage_architecture
from masck_one.distribution_geometry import build_distribution_geometry_architecture
from masck_one.distribution_manifold import build_distribution_manifold_architecture
from masck_one.fresh_pump_packaging import build_fresh_pump_packaging_architecture
from masck_one.interface_attachment import build_interface_attachment_architecture
from masck_one.model import build_model
from masck_one.structural_frame import build_structural_frame_topology
from masck_one.water_reservoir import build_water_reservoir_architecture
from masck_one.waste_acquisition import (
    BUFFER_UNRESOLVED,
    EVIDENCE_STATUS,
    GEOMETRY_UNRESOLVED,
    HYGIENE_WET_DRAINABLE,
    PHASE_MIXED_WASTE,
    REGIONS,
    ROUTE_DESTINATION,
    WasteAcquisitionArchitecture,
    WasteAcquisitionError,
    WasteRegionIntent,
    build_waste_acquisition_architecture,
)


def region(name=REGIONS[0]):
    return WasteRegionIntent(
        name,
        PHASE_MIXED_WASTE,
        HYGIENE_WET_DRAINABLE,
        GEOMETRY_UNRESOLVED,
        GEOMETRY_UNRESOLVED,
        BUFFER_UNRESOLVED,
        ROUTE_DESTINATION,
    )


def architecture():
    return WasteAcquisitionArchitecture(
        "a" * 64,
        "2026-08-30-R1",
        0.90,
        400.0,
        tuple(region(r) for r in REGIONS),
        False,
        EVIDENCE_STATUS,
    )


@pytest.fixture(scope="module")
def current_sources():
    model = build_model()
    boundaries = build_verified_interface_boundary_topology(
        model.authority,
        model.facial_surface,
        model.coverage_mesh,
        model.compliant_interface_topology,
    )
    attachment = build_interface_attachment_architecture(model.authority, boundaries)
    frame = build_structural_frame_topology(model.authority, attachment)
    water = build_water_reservoir_architecture(model.authority)
    cleanser = build_cleanser_storage_architecture(model.authority)
    pump = build_fresh_pump_packaging_architecture(
        model.authority,
        water,
        cleanser,
        frame,
    )
    manifold = build_distribution_manifold_architecture(
        model.authority,
        pump,
        water,
        cleanser,
        frame,
    )
    distribution = build_distribution_geometry_architecture(
        model.authority,
        manifold,
        pump,
        water,
        cleanser,
        frame,
        model.coverage_mesh,
        model.protected_volumes,
    )
    return model, distribution


def test_topology_preserves_mixed_phase_and_unresolved_geometry():
    a = architecture()
    assert tuple(r.region_id for r in a.regions) == REGIONS
    assert all(r.phase_semantics == PHASE_MIXED_WASTE for r in a.regions)
    assert all(
        r.gutter_width_mm is r.gutter_depth_mm is r.transient_buffer_capacity_mL is None
        for r in a.regions
    )
    assert len(a.architecture_sha256) == 64


def test_dimensions_cannot_be_invented():
    with pytest.raises(WasteAcquisitionError):
        replace(region(), gutter_width_mm=1.0)
    with pytest.raises(WasteAcquisitionError):
        replace(region(), transient_buffer_capacity_mL=0.5)


def test_status_promotion_and_wrong_phase_fail_closed():
    with pytest.raises(WasteAcquisitionError):
        replace(region(), phase_semantics="LIQUID")
    with pytest.raises(WasteAcquisitionError):
        replace(region(), transient_buffer_status="VALIDATED")
    with pytest.raises(WasteAcquisitionError):
        replace(architecture(), evidence_status="PHYSICAL_VALIDATED")
    with pytest.raises(WasteAcquisitionError):
        replace(architecture(), physical_validation_eligible=True)


def test_incomplete_duplicate_or_mutable_region_sets_fail_closed():
    a = architecture()
    with pytest.raises(WasteAcquisitionError):
        replace(a, regions=a.regions[:-1])
    with pytest.raises(WasteAcquisitionError):
        replace(a, regions=a.regions[:-1] + (region(REGIONS[0]),))
    with pytest.raises(WasteAcquisitionError):
        replace(a, regions=list(a.regions))


def test_hostile_string_subclasses_fail_at_controlled_boundaries():
    class Alias(str):
        pass

    with pytest.raises(WasteAcquisitionError):
        replace(region(), phase_semantics=Alias(PHASE_MIXED_WASTE))
    with pytest.raises(WasteAcquisitionError):
        replace(region(), region_id=Alias(REGIONS[0]))
    with pytest.raises(WasteAcquisitionError):
        replace(architecture(), evidence_status=Alias(EVIDENCE_STATUS))
    with pytest.raises(WasteAcquisitionError):
        replace(architecture(), authority_revision=Alias("2026-08-30-R1"))
    with pytest.raises(WasteAcquisitionError):
        replace(architecture(), source_distribution_sha256=Alias("a" * 64))


def test_authority_performance_limits_are_not_promoted_to_measured_results():
    a = architecture()
    assert a.recovery_ratio_min == 0.90
    assert a.residual_free_liquid_max_uL == 400.0
    assert a.physical_validation_eligible is False


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("recovery_ratio_min", float("nan")),
        ("recovery_ratio_min", float("inf")),
        ("recovery_ratio_min", float("-inf")),
        ("residual_free_liquid_max_uL", float("nan")),
        ("residual_free_liquid_max_uL", float("inf")),
        ("residual_free_liquid_max_uL", float("-inf")),
    ),
)
def test_non_finite_authority_limits_fail_closed(field, value):
    with pytest.raises(WasteAcquisitionError):
        replace(architecture(), **{field: value})


@pytest.mark.parametrize("field", ("recovery_ratio_min", "residual_free_liquid_max_uL"))
def test_oversized_integers_fail_as_domain_errors(field):
    with pytest.raises(WasteAcquisitionError):
        replace(architecture(), **{field: 10**10000})


def test_boolean_numeric_aliases_fail_closed():
    with pytest.raises(WasteAcquisitionError):
        replace(architecture(), recovery_ratio_min=True)
    with pytest.raises(WasteAcquisitionError):
        replace(architecture(), residual_free_liquid_max_uL=False)


def test_numeric_aliases_are_canonicalized_before_provenance_hashing():
    integer_form = replace(
        architecture(),
        recovery_ratio_min=1,
        residual_free_liquid_max_uL=-0.0,
    )
    float_form = replace(
        architecture(),
        recovery_ratio_min=1.0,
        residual_free_liquid_max_uL=0.0,
    )
    assert type(integer_form.recovery_ratio_min) is float
    assert type(integer_form.residual_free_liquid_max_uL) is float
    assert integer_form.residual_free_liquid_max_uL == 0.0
    assert integer_form.architecture_sha256 == float_form.architecture_sha256


def test_manifest_revalidates_post_construction_region_corruption():
    a = architecture()
    object.__setattr__(a.regions[0], "phase_semantics", "LIQUID")
    with pytest.raises(WasteAcquisitionError, match="phase semantics"):
        _ = a.architecture_sha256


def test_manifest_revalidates_post_construction_architecture_corruption():
    a = architecture()
    object.__setattr__(a, "residual_free_liquid_max_uL", float("nan"))
    with pytest.raises(WasteAcquisitionError, match="must be finite"):
        _ = a.architecture_sha256


def test_current_source_validation_rejects_distribution_and_authority_drift(current_sources):
    model, distribution = current_sources
    a = build_waste_acquisition_architecture(model.authority, distribution)
    a.validate_current_sources(authority=model.authority, distribution=distribution)

    with pytest.raises(WasteAcquisitionError, match="stale for current distribution geometry"):
        replace(a, source_distribution_sha256="a" * 64).validate_current_sources(
            authority=model.authority,
            distribution=distribution,
        )
    with pytest.raises(WasteAcquisitionError, match="stale for current authority revision"):
        replace(a, authority_revision="STALE-REVISION").validate_current_sources(
            authority=model.authority,
            distribution=distribution,
        )
    with pytest.raises(WasteAcquisitionError, match="recovery requirement is stale"):
        replace(a, recovery_ratio_min=a.recovery_ratio_min - 0.01).validate_current_sources(
            authority=model.authority,
            distribution=distribution,
        )
    with pytest.raises(WasteAcquisitionError, match="residual-liquid requirement is stale"):
        replace(
            a,
            residual_free_liquid_max_uL=a.residual_free_liquid_max_uL + 1.0,
        ).validate_current_sources(
            authority=model.authority,
            distribution=distribution,
        )
