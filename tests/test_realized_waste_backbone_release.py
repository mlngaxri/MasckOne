from copy import deepcopy
from dataclasses import replace

import pytest

from masck_one.realized_waste_backbone import RealizedWasteBackboneError
from masck_one.realized_waste_backbone_release import (
    AUTHORED_AGAINST_MAIN_SHA,
    RELEASE_STATE,
    build_current_cell4_waste_backbone_release,
    build_current_waste_routing_sources,
)


@pytest.fixture(scope="module")
def sources():
    return build_current_waste_routing_sources()


@pytest.fixture(scope="module")
def release():
    return build_current_cell4_waste_backbone_release()


def test_current_release_binds_live_architecture_and_current_source_graph(sources, release):
    assert release.authored_against_git_sha == AUTHORED_AGAINST_MAIN_SHA
    assert (
        release.source_waste_pump_architecture_sha256
        == sources.architecture.architecture_sha256
    )
    assert (
        release.realization.source_waste_pump_architecture_sha256
        == sources.architecture.architecture_sha256
    )
    assert (
        release.realization.authority_revision
        == sources.architecture.source_authority_revision
    )
    assert release.release_state == RELEASE_STATE
    release.validate_current_sources(sources)


def test_release_manifest_is_deterministic():
    first = build_current_cell4_waste_backbone_release()
    second = build_current_cell4_waste_backbone_release()
    assert first.manifest_sha256 == second.manifest_sha256


def test_trusted_manifest_reconstructs_repository_current_sources(monkeypatch, release):
    calls = 0
    from masck_one import realized_waste_backbone_release as module

    original = module.build_current_waste_routing_sources

    def counted():
        nonlocal calls
        calls += 1
        return original()

    monkeypatch.setattr(module, "build_current_waste_routing_sources", counted)
    manifest = release.manifest()
    assert calls == 1
    assert (
        manifest["source_waste_pump_architecture_sha256"]
        == release.source_waste_pump_architecture_sha256
    )


def test_well_formed_but_stale_architecture_digest_fails_closed(sources, release):
    stale_realization = replace(
        release.realization,
        source_waste_pump_architecture_sha256="0" * 64,
    )
    stale = replace(
        release,
        source_waste_pump_architecture_sha256="0" * 64,
        realization=stale_realization,
    )
    with pytest.raises(RealizedWasteBackboneError, match="current waste-pump architecture"):
        stale.validate_current_sources(sources)


def test_internal_realization_cannot_alias_another_architecture(sources, release):
    stale_realization = replace(
        release.realization,
        source_waste_pump_architecture_sha256="f" * 64,
    )
    stale = replace(release, realization=stale_realization)
    with pytest.raises(RealizedWasteBackboneError, match="does not match release"):
        stale.validate_current_sources(sources)


def test_changed_current_source_graph_fails_closed(sources, release):
    corrupted_distribution = deepcopy(sources.distribution)
    object.__setattr__(corrupted_distribution.grooves[0], "width_mm", 0.4)
    corrupted_sources = replace(sources, distribution=corrupted_distribution)
    with pytest.raises(RealizedWasteBackboneError, match="source graph is stale or corrupted"):
        release.validate_current_sources(corrupted_sources)


def test_current_route_binding_change_fails_closed(sources, release):
    altered_route = replace(
        release.realization.routes[1],
        source_interface_id=release.realization.routes[0].source_interface_id,
    )
    altered_realization = replace(
        release.realization,
        routes=(
            release.realization.routes[0],
            altered_route,
            release.realization.routes[2],
        ),
    )
    altered = replace(release, realization=altered_realization)
    with pytest.raises(RealizedWasteBackboneError, match="passive-backflow topology"):
        altered.validate_current_sources(sources)


def test_release_state_cannot_claim_physical_validation(release):
    altered = replace(release, release_state="VERIFIED")
    with pytest.raises(RealizedWasteBackboneError, match="cannot promote"):
        altered.validate_invariants()
