from copy import deepcopy
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
from masck_one.waste_acquisition import build_waste_acquisition_architecture
from masck_one.waste_cartridge import WasteCartridgeError, build_waste_cartridge_architecture
from masck_one.waste_pump_architecture import (
    INTERFACE_CARTRIDGE_INLET_I27,
    ROUTE_PUMP_TO_BARRIER,
)
from masck_one.waste_pump_packaging import build_waste_pump_packaging_architecture


def _released_chain():
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
    acquisition = build_waste_acquisition_architecture(model.authority, distribution)
    pump = build_waste_pump_packaging_architecture(
        model.authority,
        acquisition,
        distribution,
        frame,
    )
    cartridge = build_waste_cartridge_architecture(
        model.authority,
        pump,
        acquisition,
        distribution,
        frame,
    )
    return model, frame, distribution, acquisition, pump, cartridge


def test_iteration27_consumes_reconciled_iteration26_through_repository_rooted_iteration25_proof():
    model, frame, distribution, acquisition, pump, cartridge = _released_chain()

    cartridge.validate_current_sources(
        authority=model.authority,
        pump=pump,
        acquisition=acquisition,
        distribution=distribution,
        frame=frame,
    )

    assert cartridge.source_waste_pump_sha256 == pump.architecture_sha256
    assert pump.routes[-1].target_interface_id == cartridge.interfaces.inlet_interface_id


def test_iteration27_rejects_postconstruction_direct_pump_to_cartridge_bypass():
    model, frame, distribution, acquisition, pump, cartridge = _released_chain()
    corrupted = deepcopy(pump)

    pump_to_barrier = next(route for route in corrupted.routes if route.route_id == ROUTE_PUMP_TO_BARRIER)
    object.__setattr__(
        pump_to_barrier,
        "target_interface_id",
        INTERFACE_CARTRIDGE_INLET_I27,
    )

    with pytest.raises(
        WasteCartridgeError,
        match="Iteration 26 waste-pump architecture is stale for current sources",
    ):
        cartridge.validate_current_sources(
            authority=model.authority,
            pump=corrupted,
            acquisition=acquisition,
            distribution=distribution,
            frame=frame,
        )


def test_iteration27_rejects_locally_self_consistent_stale_iteration25_lineage():
    model, frame, distribution, acquisition, pump, cartridge = _released_chain()

    stale_acquisition = replace(acquisition, source_distribution_sha256="a" * 64)
    stale_pump = replace(
        pump,
        source_waste_acquisition_sha256=stale_acquisition.architecture_sha256,
        station=replace(
            pump.station,
            source_waste_acquisition_sha256=stale_acquisition.architecture_sha256,
        ),
    )
    stale_cartridge = replace(
        cartridge,
        source_waste_pump_sha256=stale_pump.architecture_sha256,
    )

    assert stale_pump.source_waste_acquisition_sha256 == stale_acquisition.architecture_sha256
    assert stale_cartridge.source_waste_pump_sha256 == stale_pump.architecture_sha256

    with pytest.raises(
        WasteCartridgeError,
        match="Iteration 26 waste-pump architecture is stale for current sources",
    ):
        stale_cartridge.validate_current_sources(
            authority=model.authority,
            pump=stale_pump,
            acquisition=stale_acquisition,
            distribution=distribution,
            frame=frame,
        )
