from __future__ import annotations

from dataclasses import replace
import subprocess

import pytest

from masck_one.component_registry import (
    AUTHORITY_BLOB_SHA,
    AUTHORITY_REVISION,
    CONTROLLED_ENVELOPE,
    REALIZED_SOLID,
    SOURCE_GIT_BLOB_BY_MODULE,
    SOURCE_MAIN_SHA,
    STATUS_VOCABULARY,
    TOPOLOGY_ONLY,
    UNRESOLVED,
    ComponentRecord,
    ComponentRegistryError,
    InterfaceDatum,
    WholeProductComponentRegistry,
    build_whole_product_component_registry,
)
from masck_one.fresh_pump_packaging import STATION_CLEANSER, STATION_WATER
from masck_one.interface_topology import (
    ZONE_OPENING_EYE_LEFT,
    ZONE_OPENING_EYE_RIGHT,
    ZONE_OPENING_MOUTH,
    ZONE_OPENING_NOSTRIL_LEFT,
    ZONE_OPENING_NOSTRIL_RIGHT,
)
from masck_one.waste_pump_architecture import BARRIER_WASTE, STATION_WASTE


@pytest.fixture(scope="module")
def registry() -> WholeProductComponentRegistry:
    return build_whole_product_component_registry()


@pytest.fixture(scope="module")
def by_id(registry: WholeProductComponentRegistry) -> dict[str, ComponentRecord]:
    return {item.component_id: item for item in registry.components}


def test_registry_is_deterministic_complete_and_source_bound(
    registry: WholeProductComponentRegistry,
) -> None:
    second = build_whole_product_component_registry()

    assert registry.manifest() == second.manifest()
    assert registry.registry_sha256 == second.registry_sha256
    assert registry.source_main_sha == SOURCE_MAIN_SHA
    assert registry.authority_revision == AUTHORITY_REVISION
    assert registry.authority_blob_sha == AUTHORITY_BLOB_SHA
    assert registry.physical_validation_eligible is False
    assert tuple(item.component_id for item in registry.components) == tuple(
        sorted(item.component_id for item in registry.components)
    )
    assert len(registry.components) == 36
    assert set(item.status for item in registry.components) <= set(STATUS_VOCABULARY)


def test_registry_git_blob_provenance_matches_checked_out_sources() -> None:
    for path, expected_sha in SOURCE_GIT_BLOB_BY_MODULE.items():
        actual_sha = subprocess.check_output(
            ["git", "hash-object", path],
            text=True,
        ).strip()
        assert actual_sha == expected_sha, f"component registry source binding is stale for {path}"


def test_realized_solids_and_controlled_envelopes_are_not_overstated(
    by_id: dict[str, ComponentRecord],
) -> None:
    assert by_id["MASCK_ONE-COMP-RIGID-SHELL"].status == REALIZED_SOLID
    assert by_id["MASCK_ONE-COMP-NASAL-LOBE-REFERENCE"].status == REALIZED_SOLID
    for component_id in (
        "MASCK_ONE-COMP-ACTUATOR-01",
        "MASCK_ONE-COMP-ACTUATOR-02",
        "MASCK_ONE-COMP-ACTUATOR-03",
        "MASCK_ONE-COMP-ACTUATOR-04",
        "MASCK_ONE-COMP-BATTERY",
        "MASCK_ONE-COMP-WATER-RESERVOIR",
        "MASCK_ONE-COMP-WASTE-CARTRIDGE",
    ):
        assert by_id[component_id].status == CONTROLLED_ENVELOPE

    assert "NOT_CLASS_A_OR_PHYSICAL_VALIDATION" in by_id["MASCK_ONE-COMP-RIGID-SHELL"].evidence_status
    assert "PACKAGING_BENCHMARK_ONLY" in by_id["MASCK_ONE-COMP-BATTERY"].evidence_status


def test_topology_only_systems_preserve_controlled_interfaces_without_fake_hardware(
    by_id: dict[str, ComponentRecord],
) -> None:
    assert by_id["MASCK_ONE-COMP-FACIAL-INTERFACE"].status == TOPOLOGY_ONLY
    assert by_id["MASCK_ONE-COMP-CLEANSER-RESERVOIR"].status == TOPOLOGY_ONLY
    assert by_id["MASCK_ONE-COMP-FRESH-MANIFOLD"].status == TOPOLOGY_ONLY
    assert by_id["MASCK_ONE-COMP-FRESH-DISTRIBUTION"].status == TOPOLOGY_ONLY
    assert by_id["MASCK_ONE-COMP-WASTE-ACQUISITION"].status == TOPOLOGY_ONLY
    assert by_id["MASCK_ONE-COMP-MIXED-WASTE-ROUTES"].status == TOPOLOGY_ONLY

    shell_datums = {item.datum_id for item in by_id["MASCK_ONE-COMP-RIGID-SHELL"].interface_datums}
    assert {
        ZONE_OPENING_EYE_LEFT,
        ZONE_OPENING_EYE_RIGHT,
        ZONE_OPENING_MOUTH,
        ZONE_OPENING_NOSTRIL_LEFT,
        ZONE_OPENING_NOSTRIL_RIGHT,
    } <= shell_datums

    assert by_id["MASCK_ONE-COMP-WATER-PUMP"].source_object_id == STATION_WATER
    assert by_id["MASCK_ONE-COMP-CLEANSER-PUMP"].source_object_id == STATION_CLEANSER
    assert by_id["MASCK_ONE-COMP-WASTE-PUMP"].source_object_id == STATION_WASTE
    assert by_id["MASCK_ONE-COMP-WASTE-BACKFLOW-BARRIER"].source_object_id == BARRIER_WASTE


def test_unreleased_specialist_hardware_remains_unresolved_on_main(
    by_id: dict[str, ComponentRecord],
) -> None:
    for component_id in (
        "MASCK_ONE-COMP-RETENTION-HALO",
        "MASCK_ONE-COMP-QUICK-RELEASE-RIGHT",
        "MASCK_ONE-COMP-RETENTION-LEFT-INTERFACE",
        "MASCK_ONE-COMP-WATER-PUMP",
        "MASCK_ONE-COMP-CLEANSER-PUMP",
        "MASCK_ONE-COMP-WASTE-PUMP",
        "MASCK_ONE-COMP-WASTE-BACKFLOW-BARRIER",
        "MASCK_ONE-COMP-PCB",
        "MASCK_ONE-COMP-HARNESS",
        "MASCK_ONE-COMP-CHARGING-INTERFACE",
        "MASCK_ONE-COMP-DRY-BAY",
        "MASCK_ONE-COMP-HMI-CLEAN",
        "MASCK_ONE-COMP-HMI-POWER",
        "MASCK_ONE-COMP-HMI-WARM",
        "MASCK_ONE-COMP-HMI-COOL",
        "MASCK_ONE-COMP-WARM-LEFT",
        "MASCK_ONE-COMP-WARM-RIGHT",
        "MASCK_ONE-COMP-COOL-RESERVATION",
        "MASCK_ONE-COMP-WET-DRY-BULKHEAD",
        "MASCK_ONE-COMP-DRAIN-DRY-PATH",
    ):
        record = by_id[component_id]
        assert record.status == UNRESOLVED
        assert record.source_digest_sha256 is None
        assert all(item.xyz_mm is None for item in record.interface_datums)


def test_distribution_datums_are_development_references_not_registered_anatomy(
    by_id: dict[str, ComponentRecord],
) -> None:
    record = by_id["MASCK_ONE-COMP-FRESH-DISTRIBUTION"]
    assert len(record.interface_datums) == 24
    assert all(item.xyz_mm is not None for item in record.interface_datums)
    assert all(item.direction_xyz is not None for item in record.interface_datums)
    assert all("DEVELOPMENT_TARGET" in item.status for item in record.interface_datums)


def test_unresolved_component_cannot_carry_realized_digest() -> None:
    with pytest.raises(ComponentRegistryError, match="unresolved hardware"):
        ComponentRecord(
            component_id="MASCK_ONE-COMP-INVALID",
            display_name="invalid",
            owner="CELL_1_INTEGRATION",
            source_module="src/masck_one/structural_frame.py",
            source_git_blob_sha=SOURCE_GIT_BLOB_BY_MODULE["src/masck_one/structural_frame.py"],
            source_object_id="INVALID",
            status=UNRESOLVED,
            interface_datums=(InterfaceDatum("INVALID-DATUM", "TEST", "UNRESOLVED"),),
            source_digest_sha256="0" * 64,
            evidence_status="INVALID_TEST",
        )


def test_registry_rejects_promotion_of_unresolved_core_hardware(
    registry: WholeProductComponentRegistry,
) -> None:
    components = list(registry.components)
    index = next(
        index
        for index, item in enumerate(components)
        if item.component_id == "MASCK_ONE-COMP-WATER-PUMP"
    )
    components[index] = replace(components[index], status=CONTROLLED_ENVELOPE)

    with pytest.raises(ComponentRegistryError, match="cannot be promoted"):
        replace(registry, components=tuple(components))
