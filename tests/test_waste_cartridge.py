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
from masck_one.waste_acquisition import PHASE_MIXED_WASTE, build_waste_acquisition_architecture
from masck_one.waste_cartridge import (
    ARCHITECTURE_EVIDENCE_STATUS,
    CAPACITY_STATUS,
    CARTRIDGE_ID,
    EXTERNAL_ENVELOPE_STATUS,
    INTERFACE_KEY,
    INTERFACE_SEAL,
    INTERFACE_SERVICE,
    KEYING_STATUS,
    RETAINED_CAPACITY_STATUS,
    RETENTION_REGION_ID,
    SEALING_STATUS,
    SERVICE_CYCLES_STATUS,
    SERVICE_STATUS,
    WasteCartridgeError,
    build_waste_cartridge_architecture,
)
from masck_one.waste_pump_packaging import (
    INTERFACE_CARTRIDGE_INLET_I27,
    build_waste_pump_packaging_architecture,
)


@pytest.fixture(scope="module")
def built():
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


def test_cartridge_binds_exact_iteration26_handoff_and_mixed_phase_semantics(built):
    *_, pump, cartridge = built
    assert cartridge.cartridge_id == CARTRIDGE_ID
    assert cartridge.source_waste_pump_sha256 == pump.architecture_sha256
    assert cartridge.phase_semantics == PHASE_MIXED_WASTE
    assert cartridge.interfaces.phase_semantics == PHASE_MIXED_WASTE
    assert cartridge.interfaces.inlet_interface_id == INTERFACE_CARTRIDGE_INLET_I27
    assert pump.routes[-1].target_interface_id == cartridge.interfaces.inlet_interface_id


def test_authority_external_envelope_is_package_geometry_not_capacity_evidence(built):
    *_, cartridge = built
    assert (cartridge.envelope.x_mm, cartridge.envelope.y_mm, cartridge.envelope.z_mm) == (74.0, 36.0, 20.0)
    assert cartridge.envelope.authority_status == EXTERNAL_ENVELOPE_STATUS
    assert cartridge.envelope.bounding_volume_mL == pytest.approx(53.28)
    manifest = cartridge.envelope.manifest()
    assert manifest["bounding_volume_semantics"] == "EXTERNAL_RECTANGULAR_PACKAGE_UPPER_BOUND_NOT_USABLE_CAPACITY"
    assert cartridge.capacity.usable_internal_capacity_mL is None
    assert cartridge.capacity.usable_capacity_evidence_sha256 is None


def test_retained_capacity_and_service_cycles_remain_requirements_only(built):
    *_, cartridge = built
    capacity = cartridge.capacity
    assert capacity.retained_capacity_min_mL == 35.0
    assert capacity.retained_capacity_status == RETAINED_CAPACITY_STATUS
    assert capacity.service_cycles_baseline == 6
    assert capacity.service_cycles_status == SERVICE_CYCLES_STATUS
    assert capacity.capacity_status == CAPACITY_STATUS
    assert capacity.credits_absorbent_or_media_volume is False
    assert capacity.retained_capacity_min_mL < cartridge.envelope.bounding_volume_mL


def test_numeric_usable_capacity_cannot_be_invented_from_bounding_volume_or_target(built):
    *_, cartridge = built
    with pytest.raises(WasteCartridgeError, match="cannot promote or invent usable internal capacity"):
        replace(cartridge.capacity, usable_internal_capacity_mL=35.0)
    with pytest.raises(WasteCartridgeError, match="cannot promote or invent usable internal capacity"):
        replace(cartridge.capacity, usable_internal_capacity_mL=53.28)
    with pytest.raises(WasteCartridgeError, match="cannot promote or invent usable internal capacity"):
        replace(cartridge.capacity, usable_capacity_evidence_sha256="a" * 64)


def test_absorbent_or_media_capacity_credit_is_blocked_without_physical_evidence(built):
    *_, cartridge = built
    with pytest.raises(WasteCartridgeError, match="cannot credit absorbent or media volume"):
        replace(cartridge.capacity, credits_absorbent_or_media_volume=True)
    with pytest.raises(WasteCartridgeError, match="literal bool"):
        replace(cartridge.capacity, credits_absorbent_or_media_volume=0)


def test_key_seal_and_service_interfaces_are_stable_but_geometry_remains_unresolved(built):
    *_, cartridge = built
    interface = cartridge.interfaces
    assert interface.key_interface_id == INTERFACE_KEY
    assert interface.seal_interface_id == INTERFACE_SEAL
    assert interface.service_interface_id == INTERFACE_SERVICE
    assert interface.retention_region_id == RETENTION_REGION_ID
    assert interface.key_geometry_mm is None
    assert interface.allowed_insertion_axis_xyz is None
    assert interface.seal_gland_geometry_mm is None
    assert interface.seal_compression_percent is None
    assert interface.insertion_trajectory_xyz_mm is None
    assert interface.removal_trajectory_xyz_mm is None
    assert interface.service_clearance_mm is None
    assert interface.retention_force_N is None
    assert interface.keying_status == KEYING_STATUS
    assert interface.sealing_status == SEALING_STATUS
    assert interface.service_status == SERVICE_STATUS


def test_invented_key_seal_trajectory_clearance_and_retention_values_fail_closed(built):
    *_, cartridge = built
    interface = cartridge.interfaces
    cases = (
        {"key_geometry_mm": (1.0,)},
        {"allowed_insertion_axis_xyz": (0.0, 0.0, 1.0)},
        {"seal_gland_geometry_mm": (1.0, 2.0)},
        {"seal_compression_percent": 20.0},
        {"insertion_trajectory_xyz_mm": ((0.0, 0.0, 0.0),)},
        {"removal_trajectory_xyz_mm": ((0.0, 0.0, 1.0),)},
        {"service_clearance_mm": 2.0},
        {"retention_force_N": 5.0},
    )
    for changes in cases:
        with pytest.raises(WasteCartridgeError, match="cannot invent key, seal, trajectory"):
            replace(interface, **changes)


def test_incorrect_interface_identity_or_promoted_status_fails_closed(built):
    *_, cartridge = built
    interface = cartridge.interfaces
    with pytest.raises(WasteCartridgeError, match="cartridge inlet interface"):
        replace(interface, inlet_interface_id="ALIAS")
    with pytest.raises(WasteCartridgeError, match="key interface"):
        replace(interface, key_interface_id="ALIAS")
    with pytest.raises(WasteCartridgeError, match="seal interface"):
        replace(interface, seal_interface_id="ALIAS")
    with pytest.raises(WasteCartridgeError, match="service interface"):
        replace(interface, service_interface_id="ALIAS")
    with pytest.raises(WasteCartridgeError, match="keying status"):
        replace(interface, keying_status="VERIFIED")
    with pytest.raises(WasteCartridgeError, match="sealing status"):
        replace(interface, sealing_status="LEAK_TIGHT_VERIFIED")
    with pytest.raises(WasteCartridgeError, match="service status"):
        replace(interface, service_status="CLEARANCE_VERIFIED")


def test_stale_iteration26_authority_envelope_capacity_and_cycles_fail_closed(built):
    model, frame, distribution, acquisition, pump, cartridge = built
    cartridge.validate_current_sources(
        authority=model.authority,
        pump=pump,
        acquisition=acquisition,
        distribution=distribution,
        frame=frame,
    )
    with pytest.raises(WasteCartridgeError, match="stale for current Iteration 26"):
        replace(cartridge, source_waste_pump_sha256="a" * 64).validate_current_sources(
            authority=model.authority,
            pump=pump,
            acquisition=acquisition,
            distribution=distribution,
            frame=frame,
        )
    with pytest.raises(WasteCartridgeError, match="stale for current authority revision"):
        replace(cartridge, source_authority_revision="STALE-REVISION").validate_current_sources(
            authority=model.authority,
            pump=pump,
            acquisition=acquisition,
            distribution=distribution,
            frame=frame,
        )
    with pytest.raises(WasteCartridgeError, match="external envelope is stale"):
        replace(
            cartridge,
            envelope=replace(cartridge.envelope, x_mm=cartridge.envelope.x_mm - 1.0),
        ).validate_current_sources(
            authority=model.authority,
            pump=pump,
            acquisition=acquisition,
            distribution=distribution,
            frame=frame,
        )
    with pytest.raises(WasteCartridgeError, match="retained-capacity requirement is stale"):
        replace(
            cartridge,
            capacity=replace(
                cartridge.capacity,
                retained_capacity_min_mL=cartridge.capacity.retained_capacity_min_mL - 1.0,
            ),
        ).validate_current_sources(
            authority=model.authority,
            pump=pump,
            acquisition=acquisition,
            distribution=distribution,
            frame=frame,
        )
    with pytest.raises(WasteCartridgeError, match="service-cycle baseline is stale"):
        replace(
            cartridge,
            capacity=replace(
                cartridge.capacity,
                service_cycles_baseline=cartridge.capacity.service_cycles_baseline - 1,
            ),
        ).validate_current_sources(
            authority=model.authority,
            pump=pump,
            acquisition=acquisition,
            distribution=distribution,
            frame=frame,
        )


def test_builder_revalidates_iteration26_dependency_chain(built):
    model, frame, distribution, acquisition, pump, _ = built
    stale_pump = replace(
        pump,
        source_waste_acquisition_sha256="a" * 64,
        station=replace(pump.station, source_waste_acquisition_sha256="a" * 64),
    )
    with pytest.raises(WasteCartridgeError, match="Iteration 26 waste-pump architecture is stale"):
        build_waste_cartridge_architecture(
            model.authority,
            stale_pump,
            acquisition,
            distribution,
            frame,
        )


def test_hostile_string_subclasses_and_token_spoofing_fail_closed(built):
    class Alias(str):
        pass

    *_, cartridge = built
    with pytest.raises(WasteCartridgeError, match="cartridge ID"):
        replace(cartridge, cartridge_id=Alias(CARTRIDGE_ID))
    with pytest.raises(WasteCartridgeError, match="canonical lowercase SHA-256"):
        replace(cartridge, source_waste_pump_sha256=Alias("a" * 64))
    with pytest.raises(WasteCartridgeError, match="external envelope status"):
        replace(cartridge.envelope, authority_status="NOT_ENGINEERING_BASELINE_BUT_CONTAINS_TOKEN")
    with pytest.raises(WasteCartridgeError, match="capacity evidence status"):
        replace(cartridge.capacity, capacity_status=Alias(CAPACITY_STATUS))
    with pytest.raises(WasteCartridgeError, match="architecture evidence status"):
        replace(cartridge, evidence_status=Alias(ARCHITECTURE_EVIDENCE_STATUS))


def test_nonfinite_boolean_and_huge_geometry_or_capacity_values_fail_closed(built):
    *_, cartridge = built
    for value in (float("nan"), float("inf"), float("-inf"), True, 10**10000):
        with pytest.raises(WasteCartridgeError):
            replace(cartridge.envelope, x_mm=value)
        with pytest.raises(WasteCartridgeError):
            replace(cartridge.capacity, retained_capacity_min_mL=value)
    for value in (True, 0, -1, 1.0):
        with pytest.raises(WasteCartridgeError, match="exact positive integer"):
            replace(cartridge.capacity, service_cycles_baseline=value)


def test_external_package_bound_prevents_impossible_capacity_requirement(built):
    *_, cartridge = built
    with pytest.raises(WasteCartridgeError, match="exceeds the external package bounding-volume"):
        replace(
            cartridge,
            capacity=replace(cartridge.capacity, retained_capacity_min_mL=53.280001),
        )


def test_manifest_is_deterministic_and_revalidates_nested_corruption(built):
    model, frame, distribution, acquisition, pump, cartridge = built
    second = build_waste_cartridge_architecture(
        model.authority,
        pump,
        acquisition,
        distribution,
        frame,
    )
    assert cartridge.manifest() == second.manifest()
    assert cartridge.architecture_sha256 == second.architecture_sha256
    assert cartridge.physical_validation_eligible is False
    assert cartridge.evidence_status == ARCHITECTURE_EVIDENCE_STATUS

    object.__setattr__(second.interfaces, "sealing_status", "VERIFIED")
    with pytest.raises(WasteCartridgeError, match="sealing status"):
        _ = second.architecture_sha256


def test_physical_evidence_promotion_is_rejected(built):
    *_, cartridge = built
    with pytest.raises(WasteCartridgeError, match="not physical validation evidence"):
        replace(cartridge, physical_validation_eligible=True)
    with pytest.raises(WasteCartridgeError, match="architecture evidence status"):
        replace(cartridge, evidence_status="PHYSICALLY_VERIFIED")
