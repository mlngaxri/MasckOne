from dataclasses import replace
from hashlib import sha1
from pathlib import Path
import json
import math

import pytest

from masck_one.cleanser_graph import (
    AUTHORED_AGAINST_RELEASED_MAIN_SHA,
    CANDIDATE_PUMP_HEAD,
    CANDIDATE_PUMP_PR,
    CANDIDATE_ROUTING_AUDIT_HEAD,
    CANDIDATE_ROUTING_AUDIT_PR,
    CANDIDATE_STORAGE_HEAD,
    CANDIDATE_STORAGE_PR,
    DISPOSITION_AUDIT_ONLY,
    DISPOSITION_REBASE_REQUIRED,
    DISPOSITION_REWORK,
    FLUID_IDENTITY,
    GROOVE_STATUS,
    MANIFOLD_BRANCH_STATUS,
    MANIFOLD_ROUTE_STATUS,
    OUTLET_STATUS,
    PHYSICAL_EVIDENCE_STATUS,
    PUMP_RELEASE_STATUS,
    RELEASED_SOURCE_BLOBS,
    SOURCE_ROUTE_STATUS,
    STORAGE_RELEASE_STATUS,
    WORLD_FRAME_ID,
    CandidateSourceReceipt,
    CleanserGraphError,
    build_cleanser_graph_receipt,
    build_current_cleanser_graph_sources,
)
from masck_one.cleanser_storage import CLEANSER_STORAGE_ID, PORT_OUTLET
from masck_one.distribution_manifold import BRANCH_CLEANSER, INLET_CLEANSER
from masck_one.fresh_pump_packaging import (
    INTERFACE_CLEANSER_PUMP_OUTLET,
    ROUTE_CLEANSER_MANIFOLD,
    ROUTE_CLEANSER_SOURCE,
    STATION_CLEANSER,
)


@pytest.fixture(scope="module")
def built():
    sources = build_current_cleanser_graph_sources()
    receipt = build_cleanser_graph_receipt(sources)
    return sources, receipt


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode("ascii")
    return sha1(header + data).hexdigest()


def test_released_cleanser_identity_chain_is_exact(built):
    sources, receipt = built
    assert receipt.authored_against_released_main_sha == AUTHORED_AGAINST_RELEASED_MAIN_SHA
    assert receipt.frame_id == WORLD_FRAME_ID
    assert receipt.fluid_identity == FLUID_IDENTITY == "CLEANSER"
    assert receipt.reservoir_id == CLEANSER_STORAGE_ID
    assert receipt.source_port_id == PORT_OUTLET
    assert receipt.pump_station_id == STATION_CLEANSER
    assert receipt.pump_outlet_interface_id == INTERFACE_CLEANSER_PUMP_OUTLET
    assert receipt.source_route_id == ROUTE_CLEANSER_SOURCE
    assert receipt.manifold_route_id == ROUTE_CLEANSER_MANIFOLD
    assert receipt.manifold_branch_id == BRANCH_CLEANSER
    assert receipt.manifold_inlet_id == INLET_CLEANSER
    receipt.validate_current_sources(
        authority=sources.model.authority,
        cleanser=sources.cleanser,
        pump=sources.pump,
        manifold=sources.manifold,
        distribution=sources.distribution,
    )


def test_current_release_maturity_is_separated_from_moving_candidate_geometry(built):
    _, receipt = built
    assert receipt.storage_release_status == STORAGE_RELEASE_STATUS
    assert receipt.pump_release_status == PUMP_RELEASE_STATUS
    assert receipt.source_route_status == SOURCE_ROUTE_STATUS
    assert receipt.manifold_route_status == MANIFOLD_ROUTE_STATUS
    assert receipt.manifold_branch_status == MANIFOLD_BRANCH_STATUS
    assert receipt.outlet_status == OUTLET_STATUS
    assert receipt.groove_status == GROOVE_STATUS
    assert receipt.physical_validation_eligible is False
    assert receipt.evidence_status == PHYSICAL_EVIDENCE_STATUS


def test_candidate_heads_are_exact_and_never_release_authority(built):
    _, receipt = built
    assert tuple((item.pr_number, item.head_sha, item.disposition) for item in receipt.moving_candidates) == (
        (CANDIDATE_STORAGE_PR, CANDIDATE_STORAGE_HEAD, DISPOSITION_REWORK),
        (CANDIDATE_PUMP_PR, CANDIDATE_PUMP_HEAD, DISPOSITION_REBASE_REQUIRED),
        (CANDIDATE_ROUTING_AUDIT_PR, CANDIDATE_ROUTING_AUDIT_HEAD, DISPOSITION_AUDIT_ONLY),
    )
    assert all(item.consumable_as_release_authority is False for item in receipt.moving_candidates)
    with pytest.raises(CleanserGraphError, match="released authority"):
        replace(receipt.moving_candidates[0], consumable_as_release_authority=True)
    with pytest.raises(CleanserGraphError, match="disposition"):
        replace(receipt.moving_candidates[1], disposition="RELEASED")


def test_released_source_blob_bindings_match_checked_out_sources():
    root = Path(__file__).resolve().parents[1]
    for source_id, relative_path, expected_blob in RELEASED_SOURCE_BLOBS:
        path = root / relative_path
        assert path.is_file(), source_id
        assert _git_blob_sha(path) == expected_blob, source_id


def test_six_released_cleanser_outlet_datums_preserve_fluid_frame_and_order(built):
    sources, receipt = built
    assert tuple(item.outlet_id for item in receipt.outlet_datums) == tuple(
        f"MANIFOLD-OUTLET-CLEANSER-{index:02d}" for index in range(1, 7)
    )
    assert all(item.fluid_identity == "CLEANSER" for item in receipt.outlet_datums)
    assert all(item.frame_id == WORLD_FRAME_ID for item in receipt.outlet_datums)
    assert len({item.source_triangle_index for item in receipt.outlet_datums}) == 6

    released = tuple(
        item for item in sources.distribution.placements if item.fluid_identity == "CLEANSER"
    )
    assert tuple(item.center_world_mm for item in receipt.outlet_datums) == tuple(
        item.center_xyz_mm for item in released
    )
    assert tuple(item.lateral_direction_world for item in receipt.outlet_datums) == tuple(
        item.lateral_direction_xyz for item in released
    )


def test_released_distribution_is_datum_only_not_dimensioned_groove_geometry(built):
    sources, receipt = built
    assert receipt.outlet_status == OUTLET_STATUS
    assert receipt.groove_status == GROOVE_STATUS
    cleanser_grooves = tuple(
        groove
        for groove, placement in zip(
            sources.distribution.grooves,
            sources.distribution.placements,
            strict=True,
        )
        if placement.fluid_identity == "CLEANSER"
    )
    assert len(cleanser_grooves) == 6
    assert all(
        groove.width_mm is None and groove.depth_mm is None and groove.length_mm is None
        for groove in cleanser_grooves
    )


def test_identity_frame_status_and_physical_evidence_promotion_fail_closed(built):
    _, receipt = built
    with pytest.raises(CleanserGraphError, match="alias"):
        replace(receipt, fluid_identity="FRESH_WATER")
    with pytest.raises(CleanserGraphError, match="canonical world frame"):
        replace(receipt, frame_id="LOCAL")
    with pytest.raises(CleanserGraphError, match="maturity/evidence status"):
        replace(receipt, pump_release_status="RELEASED_REALIZED_PUMP")
    with pytest.raises(CleanserGraphError, match="physical validation"):
        replace(receipt, physical_validation_eligible=True)


def test_stale_architecture_digests_fail_against_current_sources(built):
    sources, receipt = built
    cases = (
        ("source_cleanser_architecture_sha256", "storage architecture"),
        ("source_pump_architecture_sha256", "pump architecture"),
        ("source_manifold_architecture_sha256", "manifold architecture"),
        ("source_distribution_architecture_sha256", "distribution architecture"),
    )
    for field, message in cases:
        stale = replace(receipt, **{field: "a" * 64})
        with pytest.raises(CleanserGraphError, match=message):
            stale.validate_current_sources(
                authority=sources.model.authority,
                cleanser=sources.cleanser,
                pump=sources.pump,
                manifold=sources.manifold,
                distribution=sources.distribution,
            )


def test_malformed_candidate_and_nonfinite_outlet_values_fail_closed(built):
    _, receipt = built
    candidate = receipt.moving_candidates[0]
    with pytest.raises(CleanserGraphError, match="positive integer"):
        CandidateSourceReceipt(
            candidate_id=candidate.candidate_id,
            pr_number=True,
            head_sha=candidate.head_sha,
            source_blobs=candidate.source_blobs,
            disposition=candidate.disposition,
        )
    with pytest.raises(CleanserGraphError, match="candidate head"):
        replace(candidate, head_sha="A" * 40)
    outlet = receipt.outlet_datums[0]
    with pytest.raises(CleanserGraphError, match="finite"):
        replace(outlet, protected_clearance_mm=math.nan)
    with pytest.raises(CleanserGraphError, match="unit length"):
        replace(outlet, lateral_direction_world=(1.0, 1.0, 0.0))


def test_candidate_source_blob_path_duplication_fails_closed(built):
    _, receipt = built
    candidate = receipt.moving_candidates[0]
    duplicate = (candidate.source_blobs[0], candidate.source_blobs[0])
    with pytest.raises(CleanserGraphError, match="cannot repeat"):
        replace(candidate, source_blobs=duplicate)


def test_receipt_manifest_is_deterministic_and_json_strict(built):
    _, receipt = built
    first = receipt.manifest()
    second = receipt.manifest()
    assert first == second
    assert first["receipt_sha256"] == receipt.receipt_sha256
    encoded = json.dumps(first, sort_keys=True, allow_nan=False)
    assert json.loads(encoded) == first
    assert first["moving_candidates"][0]["consumable_as_release_authority"] is False
    assert len(first["outlet_datums"]) == 6
