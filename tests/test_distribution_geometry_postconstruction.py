from dataclasses import replace

import pytest

from masck_one.boundary_release import build_verified_interface_boundary_topology
from masck_one.cleanser_storage import build_cleanser_storage_architecture
from masck_one.distribution_geometry import (
    DistributionGeometryError,
    build_distribution_geometry_architecture,
)
from masck_one.distribution_manifold import build_distribution_manifold_architecture
from masck_one.fresh_pump_packaging import build_fresh_pump_packaging_architecture
from masck_one.interface_attachment import build_interface_attachment_architecture
from masck_one.model import build_model
from masck_one.structural_frame import build_structural_frame_topology
from masck_one.waste_acquisition import build_waste_acquisition_architecture
from masck_one.water_reservoir import build_water_reservoir_architecture


@pytest.fixture(scope="module")
def current_stack():
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
    return model, water, cleanser, frame, pump, manifold, distribution


def clone_distribution(distribution):
    return replace(
        distribution,
        placements=tuple(replace(item) for item in distribution.placements),
        grooves=tuple(replace(item) for item in distribution.grooves),
    )


def validate_current(stack, distribution):
    model, water, cleanser, frame, pump, manifold, _ = stack
    distribution.validate_current_sources(
        authority=model.authority,
        manifold=manifold,
        pump=pump,
        water=water,
        cleanser=cleanser,
        frame=frame,
        coverage=model.coverage_mesh,
        protected=model.protected_volumes,
    )


def test_postconstruction_corruption_cannot_be_hashed_or_validated(current_stack):
    *_, source = current_stack

    class HostileStr(str):
        pass

    corruptions = (
        (
            lambda item: object.__setattr__(item, "physical_validation_eligible", True),
            "physical validation evidence",
        ),
        (
            lambda item: object.__setattr__(
                item,
                "source_manifold_architecture_sha256",
                HostileStr(item.source_manifold_architecture_sha256),
            ),
            "source manifold architecture",
        ),
        (
            lambda item: object.__setattr__(
                item.placements[0],
                "evidence_status",
                "PHYSICALLY_VALIDATED",
            ),
            "outlet evidence status",
        ),
        (
            lambda item: object.__setattr__(
                item.placements[0],
                "outlet_id",
                HostileStr(item.placements[0].outlet_id),
            ),
            "outlet placement ID",
        ),
        (
            lambda item: object.__setattr__(item.grooves[0], "width_mm", 0.4),
            "cannot invent distribution-groove dimensions",
        ),
        (
            lambda item: object.__setattr__(
                item.grooves[0],
                "surface_status",
                "REGISTERED_SURFACE_VALIDATED",
            ),
            "groove surface status",
        ),
    )

    for corrupt, message in corruptions:
        candidate = clone_distribution(source)
        corrupt(candidate)
        with pytest.raises(DistributionGeometryError, match=message):
            _ = candidate.architecture_sha256
        with pytest.raises(DistributionGeometryError, match=message):
            candidate.manifest()
        with pytest.raises(DistributionGeometryError, match=message):
            validate_current(current_stack, candidate)


def test_iteration25_cannot_rebind_corrupted_iteration24_snapshot(current_stack):
    model, water, cleanser, frame, pump, manifold, source = current_stack
    candidate = clone_distribution(source)
    object.__setattr__(candidate.grooves[0], "width_mm", 0.4)

    with pytest.raises(
        DistributionGeometryError,
        match="Iteration 24 cannot invent distribution-groove dimensions",
    ):
        build_waste_acquisition_architecture(
            model.authority,
            candidate,
            manifold,
            pump,
            water,
            cleanser,
            frame,
            model.coverage_mesh,
            model.protected_volumes,
        )
