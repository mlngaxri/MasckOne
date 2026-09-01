from copy import deepcopy

import pytest

from masck_one.anatomy import build_facial_reference
from masck_one.authority import Authority, load_authority
from masck_one.boundary_release import build_verified_interface_boundary_topology
from masck_one.cleanser_storage import (
    CompatibilityEvidence,
    build_cleanser_storage_architecture,
)
from masck_one.coverage import build_facial_coverage_mesh
from masck_one.distribution_geometry import build_distribution_geometry_architecture
from masck_one.distribution_manifold import build_distribution_manifold_architecture
from masck_one.facial_surface import build_planar_development_surface
from masck_one.fresh_pump_packaging import build_fresh_pump_packaging_architecture
from masck_one.interface_attachment import build_interface_attachment_architecture
from masck_one.interface_topology import build_compliant_interface_topology
from masck_one.iteration25_source_integrity import (
    Iteration25SourceIntegrityError,
    validate_iteration25_source_graph,
)
from masck_one.protected_volumes import build_protected_volumes
from masck_one.spatial import CanonicalDatums
from masck_one.structural_frame import build_structural_frame_topology
from masck_one.water_reservoir import build_water_reservoir_architecture
from masck_one.waste_acquisition import WasteAcquisitionError, build_waste_acquisition_architecture


def _sources(
    authority: Authority | None = None,
    *,
    compatibility_evidence: tuple[CompatibilityEvidence, ...] = (),
):
    authority = authority or load_authority()
    datums = CanonicalDatums.from_authority(authority)
    reference = build_facial_reference(authority, datums)
    surface = build_planar_development_surface(authority)
    protected = build_protected_volumes(authority, reference, surface)
    coverage = build_facial_coverage_mesh(authority, reference, surface, protected)
    interface = build_compliant_interface_topology(authority, coverage)
    boundaries = build_verified_interface_boundary_topology(
        authority,
        surface,
        coverage,
        interface,
    )
    attachment = build_interface_attachment_architecture(authority, boundaries)
    frame = build_structural_frame_topology(authority, attachment)
    water = build_water_reservoir_architecture(authority)
    cleanser = build_cleanser_storage_architecture(authority)
    if compatibility_evidence:
        cleanser = cleanser.with_compatibility_evidence(compatibility_evidence)
    pump = build_fresh_pump_packaging_architecture(authority, water, cleanser, frame)
    manifold = build_distribution_manifold_architecture(
        authority,
        pump,
        water,
        cleanser,
        frame,
    )
    distribution = build_distribution_geometry_architecture(
        authority,
        manifold,
        pump,
        water,
        cleanser,
        frame,
        coverage,
        protected,
    )
    return {
        "authority": authority,
        "water": water,
        "cleanser": cleanser,
        "frame": frame,
        "pump": pump,
        "manifold": manifold,
        "coverage": coverage,
        "protected": protected,
        "distribution": distribution,
    }


def _validate(graph):
    validate_iteration25_source_graph(**graph)


def test_current_repository_graph_passes_and_is_accepted_by_iteration25():
    graph = _sources()
    _validate(graph)
    waste = build_waste_acquisition_architecture(
        graph["authority"],
        graph["distribution"],
        graph["manifold"],
        graph["pump"],
        graph["water"],
        graph["cleanser"],
        graph["frame"],
        graph["coverage"],
        graph["protected"],
    )
    assert waste.physical_validation_eligible is False


def test_mutually_consistent_graph_from_mutated_inmemory_authority_is_not_current():
    authority = load_authority()
    mutated = Authority(
        data=deepcopy(authority.data),
        source=authority.source,
        validation_report=authority.validation_report,
    )
    mutated.data["structure"]["frame_deflection_p95_max_mm"] = (
        float(mutated.data["structure"]["frame_deflection_p95_max_mm"]) + 0.05
    )
    stale_but_consistent = _sources(mutated)

    with pytest.raises(
        Iteration25SourceIntegrityError,
        match="differs from the current repository authority file",
    ):
        _validate(stale_but_consistent)

    with pytest.raises(WasteAcquisitionError, match="source graph is not canonical current"):
        build_waste_acquisition_architecture(
            stale_but_consistent["authority"],
            stale_but_consistent["distribution"],
            stale_but_consistent["manifold"],
            stale_but_consistent["pump"],
            stale_but_consistent["water"],
            stale_but_consistent["cleanser"],
            stale_but_consistent["frame"],
            stale_but_consistent["coverage"],
            stale_but_consistent["protected"],
        )


def test_postconstruction_corruption_anywhere_in_inherited_graph_fails_closed():
    mutations = (
        ("water port evidence", lambda g: object.__setattr__(g["water"].ports[0], "geometry_status", "PHYSICALLY_VALIDATED")),
        ("cleanser backflow evidence", lambda g: object.__setattr__(g["cleanser"], "backflow_architecture_status", "PHYSICALLY_VALIDATED")),
        ("frame reservation evidence", lambda g: object.__setattr__(g["frame"].reservations[1], "evidence_status", "PHYSICALLY_VALIDATED")),
        ("pump route evidence", lambda g: object.__setattr__(g["pump"].routes[0], "hydraulic_status", "PHYSICALLY_VALIDATED")),
        ("manifold branch evidence", lambda g: object.__setattr__(g["manifold"].branches[0], "flow_balance_status", "PHYSICALLY_VALIDATED")),
        ("coverage evidence", lambda g: object.__setattr__(g["coverage"], "segmentation_status", "PHYSICALLY_VALIDATED")),
        ("protected-zone evidence", lambda g: object.__setattr__(g["protected"].eye_left.zone, "evidence_status", "PHYSICALLY_VALIDATED")),
        ("distribution evidence", lambda g: object.__setattr__(g["distribution"], "physical_validation_eligible", True)),
    )

    baseline = _sources()
    for label, mutate in mutations:
        graph = deepcopy(baseline)
        mutate(graph)
        with pytest.raises(Iteration25SourceIntegrityError):
            _validate(graph)


def test_same_value_hostile_string_subclass_cannot_hide_in_legacy_child_record():
    class Alias(str):
        pass

    graph = _sources()
    current = graph["water"].ports[0].geometry_status
    object.__setattr__(graph["water"].ports[0], "geometry_status", Alias(current))
    with pytest.raises(Iteration25SourceIntegrityError, match="unsupported/non-canonical type Alias"):
        _validate(graph)


def test_controlled_cleanser_compatibility_evidence_variant_remains_admissible_without_promotion():
    evidence = CompatibilityEvidence(
        evidence_id="TEST-COUPON-001",
        revision="TEST-REV-1",
        cleanser_identity="TEST-CLEANSER",
        wetted_material_identity="TEST-MATERIAL",
        evidence_kind="CONTROLLED_COUPON_TEST",
        artifact_sha256="a" * 64,
        compatible=True,
    )
    graph = _sources(compatibility_evidence=(evidence,))
    _validate(graph)
    assert graph["cleanser"].compatibility_status == "EVIDENCE_ATTACHED_REQUIRES_ENGINEERING_REVIEW"
    assert graph["cleanser"].physical_validation_eligible is False
