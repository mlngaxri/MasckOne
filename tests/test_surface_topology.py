from dataclasses import FrozenInstanceError

import pytest

from masck_one.surface_continuity import SeamContinuityMetrics, SurfaceContinuityReport
from masck_one.surface_topology import SeamTopologyBinding, SurfaceTopologyError, SurfaceTopologyManifest, TopologyContinuityBinding

SHA = "a" * 64
WORLD = "MASCK_ONE_ROOT_WORLD_MM"

class LyingStr(str):
    def __eq__(self, other): return True
    def __ne__(self, other): return False
    def __hash__(self): return str.__hash__(self)

def seam(seam_id="shell.cheek", patch_a="patch.cheek", patch_b="patch.temple", edge_a="edge.outer", edge_b="edge.inner"):
    return SeamTopologyBinding(seam_id, patch_a, patch_b, edge_a, edge_b)

def manifest(*seams): return SurfaceTopologyManifest(SHA, WORLD, tuple(seams or (seam(),)))
def continuity(seam_id="shell.cheek", target="G2", gap=0.0): return SurfaceContinuityReport(SHA, WORLD, (SeamContinuityMetrics(seam_id, target, 5, gap, 0.0, 0.0),))
def bound(topology=None, report=None):
    topology = topology or manifest(); return topology.bind_continuity_report(report or continuity())
def corrupt(obj, field, value): object.__setattr__(obj, field, value); return obj

def test_manifest_is_deterministic_and_binds_continuity():
    first, second = manifest(), manifest(); assert first.manifest_sha256 == second.manifest_sha256; first.assert_current_geometry(SHA)
    binding = first.bind_continuity_report(continuity()); first.assert_continuity_report(binding); assert binding.binding_sha256 == first.bind_continuity_report(continuity()).binding_sha256

def test_binding_digest_commits_to_exact_continuity_metrics():
    topology = manifest(); nominal = topology.bind_continuity_report(continuity(gap=0.0)); changed = topology.bind_continuity_report(continuity(gap=0.01))
    assert nominal.report.report_sha256 != changed.report.report_sha256
    assert nominal.binding_sha256 != changed.binding_sha256

def test_topology_endpoint_provenance_rejects_same_namespace_different_assignments():
    topology_a = manifest(seam()); topology_b = manifest(seam(patch_a="patch.forehead", patch_b="patch.temple", edge_a="edge.lower", edge_b="edge.inner"))
    assert topology_a.source_geometry_sha256 == topology_b.source_geometry_sha256; assert tuple(x.seam_id for x in topology_a.seams) == tuple(x.seam_id for x in topology_b.seams); assert topology_a.manifest_sha256 != topology_b.manifest_sha256
    with pytest.raises(SurfaceTopologyError, match="different topology manifest"): topology_b.assert_continuity_report(topology_a.bind_continuity_report(continuity()))

def test_raw_report_cannot_bypass_endpoint_provenance_gate():
    with pytest.raises(SurfaceTopologyError, match="TopologyContinuityBinding"): manifest().assert_continuity_report(continuity())

def test_stale_geometry_and_local_frame_fail_closed():
    with pytest.raises(SurfaceTopologyError, match="stale"): manifest().assert_current_geometry("b" * 64)
    with pytest.raises(SurfaceTopologyError, match="coordinate frame"): SurfaceTopologyManifest(SHA, "LOCAL_MM", (seam(),))

def test_identity_aliases_and_reversed_orientation_are_rejected():
    for bad in (" Shell.cheek", "Shell.cheek", "shell/cheek", "shell.\u212acheek"):
        with pytest.raises(SurfaceTopologyError, match="canonical"): seam(bad)
    with pytest.raises(SurfaceTopologyError, match="orientation"): SeamTopologyBinding("shell.cheek", "patch.temple", "patch.cheek", "edge.inner", "edge.outer")

def test_hostile_string_subclasses_fail_at_all_topology_identity_boundaries():
    with pytest.raises(SurfaceTopologyError, match="exact canonical"): manifest().assert_current_geometry(LyingStr("b" * 64))
    for field in ("seam_id", "patch_a_id", "patch_b_id", "patch_a_boundary_id", "patch_b_boundary_id"):
        values = dict(seam_id="shell.cheek", patch_a_id="patch.cheek", patch_b_id="patch.temple", patch_a_boundary_id="edge.outer", patch_b_boundary_id="edge.inner"); values[field] = LyingStr(values[field])
        with pytest.raises(SurfaceTopologyError, match="exact canonical"): SeamTopologyBinding(**values)
    with pytest.raises(SurfaceTopologyError, match="coordinate frame"): SurfaceTopologyManifest(SHA, LyingStr(WORLD), (seam(),))
    with pytest.raises(SurfaceTopologyError, match="exact canonical"): TopologyContinuityBinding(LyingStr("b" * 64), continuity())

def test_hostile_strings_cannot_bypass_nested_continuity_contract():
    report = corrupt(continuity(), "source_geometry_sha256", LyingStr("b" * 64))
    with pytest.raises(SurfaceTopologyError): manifest().bind_continuity_report(report)
    report = corrupt(continuity(), "coordinate_frame", LyingStr(WORLD))
    with pytest.raises(SurfaceTopologyError): manifest().bind_continuity_report(report)
    report = continuity(); corrupt(report.seams[0], "seam_id", LyingStr("shell.forehead"))
    with pytest.raises(SurfaceTopologyError): manifest().bind_continuity_report(report)
    report = continuity(); corrupt(report.seams[0], "target", LyingStr("G9"))
    with pytest.raises(SurfaceTopologyError, match="target"): manifest().bind_continuity_report(report)
    report = corrupt(continuity(), "evidence_status", LyingStr("PHYSICAL_VALIDATED"))
    with pytest.raises(SurfaceTopologyError, match="evidence status"): manifest().bind_continuity_report(report)

def test_duplicate_boundary_ownership_and_duplicate_seam_ids_are_rejected():
    duplicate_boundary = SeamTopologyBinding("shell.forehead", "patch.cheek", "patch.forehead", "edge.outer", "edge.lower")
    with pytest.raises(SurfaceTopologyError, match="only one exterior seam"): manifest(seam(), duplicate_boundary)
    other = SeamTopologyBinding("shell.cheek", "patch.forehead", "patch.temple", "edge.upper", "edge.lower")
    with pytest.raises(SurfaceTopologyError, match="unique"): manifest(seam(), other)

def test_continuity_must_match_geometry_and_namespace_before_binding():
    with pytest.raises(SurfaceTopologyError, match="provenance"): manifest().bind_continuity_report(SurfaceContinuityReport("b" * 64, WORLD, continuity().seams))
    with pytest.raises(SurfaceTopologyError, match="seam identities"): manifest().bind_continuity_report(continuity("shell.forehead"))

def test_continuity_binding_rejects_structural_lookalikes():
    class Lookalike: topology_manifest_sha256 = manifest().manifest_sha256; report = continuity()
    with pytest.raises(SurfaceTopologyError, match="TopologyContinuityBinding"): manifest().assert_continuity_report(Lookalike())

@pytest.mark.parametrize(("field", "value"), (("evidence_status", "CLASS_A_ACCEPTED"), ("physical_validation_eligible", True), ("coordinate_frame", "LOCAL_MM")))
def test_binding_revalidates_corrupted_report_state(field, value):
    topology = manifest(); binding = bound(topology); corrupt(binding.report, field, value)
    with pytest.raises(SurfaceTopologyError): topology.assert_continuity_report(binding)

@pytest.mark.parametrize(("field", "value"), (("target", "G9"), ("sample_count", 2), ("max_position_gap_mm", float("nan")), ("max_tangent_angle_deg", float("inf")), ("max_curvature_delta_per_mm", True)))
def test_binding_revalidates_corrupted_seam_metrics(field, value):
    topology = manifest(); binding = bound(topology); corrupt(binding.report.seams[0], field, value)
    with pytest.raises(SurfaceTopologyError): topology.assert_continuity_report(binding)

def test_binding_itself_is_revalidated_against_tampering():
    topology = manifest(); binding = bound(topology); corrupt(binding, "topology_manifest_sha256", "b" * 64)
    with pytest.raises(SurfaceTopologyError, match="different topology manifest"): topology.assert_continuity_report(binding)
    binding = bound(topology); corrupt(binding, "evidence_status", "CLASS_A_ACCEPTED")
    with pytest.raises(SurfaceTopologyError, match="controlled"): topology.assert_continuity_report(binding)

def test_evidence_promotion_and_mutation_are_blocked():
    with pytest.raises(SurfaceTopologyError, match="controlled"): SurfaceTopologyManifest(SHA, WORLD, (seam(),), evidence_status="CLASS_A_ACCEPTED")
    with pytest.raises(SurfaceTopologyError, match="controlled"): SurfaceTopologyManifest(SHA, WORLD, (seam(),), evidence_status=LyingStr("DIGITAL_TOPOLOGY_BINDING_ONLY_NOT_CLASS_A_OR_PHYSICAL_EVIDENCE"))
    for alias in (True, 1, "false"):
        with pytest.raises(SurfaceTopologyError, match="physical-validation"): SurfaceTopologyManifest(SHA, WORLD, (seam(),), physical_validation_eligible=alias)
    with pytest.raises(FrozenInstanceError): manifest().coordinate_frame = "LOCAL_MM"

def test_post_construction_corruption_is_revalidated():
    binding = seam(); object.__setattr__(binding, "seam_id", "BAD")
    with pytest.raises(SurfaceTopologyError, match="canonical"): SurfaceTopologyManifest(SHA, WORLD, (binding,))
