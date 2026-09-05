from dataclasses import replace

import pytest

from masck_one.realized_waste_backbone import (
    AUTHORITY_BLOB_SHA,
    ROUTING_TOPOLOGY_BLOB_SHA,
    RealizedWasteBackboneError,
)
from masck_one.realized_waste_backbone_release import (
    RELEASE_STATE,
    SOURCE_MAIN_SHA,
    SOURCE_ROUTING_STACK_SHA,
    build_current_cell4_waste_backbone_release,
)


def test_current_release_binds_exact_main_and_source_blobs():
    release = build_current_cell4_waste_backbone_release()
    assert SOURCE_ROUTING_STACK_SHA == SOURCE_MAIN_SHA
    assert release.source_routing_stack_sha == SOURCE_MAIN_SHA
    assert release.realization.source_git_sha == SOURCE_MAIN_SHA
    assert release.authority_blob_sha == AUTHORITY_BLOB_SHA
    assert release.routing_topology_blob_sha == ROUTING_TOPOLOGY_BLOB_SHA
    assert release.release_state == RELEASE_STATE


def test_release_manifest_is_deterministic():
    first = build_current_cell4_waste_backbone_release()
    second = build_current_cell4_waste_backbone_release()
    assert first.manifest_sha256 == second.manifest_sha256


def test_stale_main_identity_fails_closed():
    release = build_current_cell4_waste_backbone_release()
    with pytest.raises(RealizedWasteBackboneError, match="current main"):
        replace(release, source_routing_stack_sha="0" * 40).validate()


def test_stale_source_blobs_fail_closed():
    release = build_current_cell4_waste_backbone_release()
    with pytest.raises(RealizedWasteBackboneError, match="authority blob"):
        replace(release, authority_blob_sha="0" * 40).validate()
    with pytest.raises(RealizedWasteBackboneError, match="routing topology blob"):
        replace(release, routing_topology_blob_sha="f" * 40).validate()


def test_internal_realization_cannot_alias_another_main():
    release = build_current_cell4_waste_backbone_release()
    stale_realization = replace(release.realization, source_git_sha="f" * 40)
    with pytest.raises(RealizedWasteBackboneError, match="does not match current main"):
        replace(release, realization=stale_realization).validate()


def test_release_state_cannot_claim_physical_validation():
    release = build_current_cell4_waste_backbone_release()
    with pytest.raises(RealizedWasteBackboneError, match="cannot promote"):
        replace(release, release_state="VERIFIED").validate()
