from dataclasses import FrozenInstanceError

import pytest

from masck_one.surface_continuity import SeamContinuityMetrics, SurfaceContinuityReport
from masck_one.surface_topology import SeamTopologyBinding, SurfaceTopologyError, SurfaceTopologyManifest


SHA = "a" * 64
WORLD = "MASCK_ONE_ROOT_WORLD_MM"


def seam(seam_id="shell.cheek"):
    return SeamTopologyBinding(seam_id, "patch.cheek", "patch.temple", "edge.outer", "edge.inner")


def manifest(*seams):
    return SurfaceTopologyManifest(SHA, WORLD, tuple(seams or (seam(),)))


def continuity(seam_id="shell.cheek"):
    metric = SeamContinuityMetrics(seam_id, "G2", 5, 0.0, 0.0, 0.0)
    return SurfaceContinuityReport(SHA, WORLD, (metric,))


def test_manifest_is_deterministic_and_binds_continuity():
    first = manifest()
    second = manifest()
    assert first.manifest_sha256 == second.manifest_sha256
    first.assert_current_geometry(SHA)
    first.assert_continuity_report(continuity())


def test_stale_geometry_and_local_frame_fail_closed():
    with pytest.raises(SurfaceTopologyError, match="stale"):
        manifest().assert_current_geometry("b" * 64)
    with pytest.raises(SurfaceTopologyError, match="root/world"):
        SurfaceTopologyManifest(SHA, "LOCAL_MM", (seam(),))


def test_identity_aliases_and_reversed_orientation_are_rejected():
    for bad in (" Shell.cheek", "Shell.cheek", "shell/cheek", "shell.\u212acheek"):
        with pytest.raises(SurfaceTopologyError, match="canonical"):
            seam(bad)
    with pytest.raises(SurfaceTopologyError, match="orientation"):
        SeamTopologyBinding("shell.cheek", "patch.temple", "patch.cheek", "edge.inner", "edge.outer")


def test_duplicate_boundary_ownership_and_duplicate_seam_ids_are_rejected():
    duplicate_boundary = SeamTopologyBinding("shell.forehead", "patch.cheek", "patch.forehead", "edge.outer", "edge.lower")
    with pytest.raises(SurfaceTopologyError, match="only one exterior seam"):
        manifest(seam(), duplicate_boundary)
    other = SeamTopologyBinding("shell.cheek", "patch.forehead", "patch.temple", "edge.upper", "edge.lower")
    with pytest.raises(SurfaceTopologyError, match="unique"):
        manifest(seam(), other)


def test_continuity_must_match_geometry_frame_and_exact_seam_namespace():
    with pytest.raises(SurfaceTopologyError, match="provenance"):
        manifest().assert_continuity_report(SurfaceContinuityReport("b" * 64, WORLD, continuity().seams))
    with pytest.raises(SurfaceTopologyError, match="seam identities"):
        manifest().assert_continuity_report(continuity("shell.forehead"))


def test_evidence_promotion_and_mutation_are_blocked():
    with pytest.raises(SurfaceTopologyError, match="controlled"):
        SurfaceTopologyManifest(SHA, WORLD, (seam(),), evidence_status="CLASS_A_ACCEPTED")
    for alias in (True, 1, "false"):
        with pytest.raises(SurfaceTopologyError, match="physical-validation"):
            SurfaceTopologyManifest(SHA, WORLD, (seam(),), physical_validation_eligible=alias)
    with pytest.raises(FrozenInstanceError):
        manifest().coordinate_frame = "LOCAL_MM"


def test_post_construction_corruption_is_revalidated():
    binding = seam()
    object.__setattr__(binding, "seam_id", "BAD")
    with pytest.raises(SurfaceTopologyError, match="canonical"):
        SurfaceTopologyManifest(SHA, WORLD, (binding,))
