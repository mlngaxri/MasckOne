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
from masck_one.waste_acquisition import build_waste_acquisition_architecture
from masck_one.waste_pump_packaging import (
    WastePumpPackagingError,
    build_waste_pump_packaging_architecture,
)


def _released_lineage():
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
    fresh_pumps = build_fresh_pump_packaging_architecture(
        model.authority,
        water,
        cleanser,
        frame,
    )
    manifold = build_distribution_manifold_architecture(
        model.authority,
        fresh_pumps,
        water,
        cleanser,
        frame,
    )
    distribution = build_distribution_geometry_architecture(
        model.authority,
        manifold,
        fresh_pumps,
        water,
        cleanser,
        frame,
        model.coverage_mesh,
        model.protected_volumes,
    )
    return model, frame, distribution


def test_released_iteration26_call_shape_resolves_canonical_iteration25_sources():
    model, frame, distribution = _released_lineage()
    acquisition = build_waste_acquisition_architecture(model.authority, distribution)
    architecture = build_waste_pump_packaging_architecture(
        model.authority,
        acquisition,
        distribution,
        frame,
    )
    architecture.validate_current_sources(
        authority=model.authority,
        acquisition=acquisition,
        distribution=distribution,
        frame=frame,
    )


def test_iteration26_cannot_rebind_postconstruction_corrupted_distribution():
    model, frame, distribution = _released_lineage()
    acquisition = build_waste_acquisition_architecture(model.authority, distribution)

    object.__setattr__(distribution.grooves[0], "width_mm", 0.4)

    with pytest.raises(WastePumpPackagingError, match="Iteration 25 waste acquisition is stale"):
        build_waste_pump_packaging_architecture(
            model.authority,
            acquisition,
            distribution,
            frame,
        )
