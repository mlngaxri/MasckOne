import pytest

from masck_one.anatomy import build_facial_reference
from masck_one.authority import load_authority
from masck_one.boundary_release import build_verified_interface_boundary_topology
from masck_one.cleanser_storage import build_cleanser_storage_architecture
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


def _graph():
    authority = load_authority()
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


def _build_waste(graph):
    return build_waste_acquisition_architecture(
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


def test_negative_zero_in_distribution_coordinate_cannot_rebind_as_current():
    graph = _graph()
    placement = graph["distribution"].placements[0]
    x, y, z = placement.center_xyz_mm
    assert z == 0.0
    object.__setattr__(placement, "center_xyz_mm", (x, y, -0.0))

    with pytest.raises(Iteration25SourceIntegrityError, match="signed zero"):
        validate_iteration25_source_graph(**graph)
    with pytest.raises(WasteAcquisitionError, match="source graph is not canonical current"):
        _build_waste(graph)


def test_negative_zero_in_direct_protected_zone_float_is_not_canonical():
    graph = _graph()
    zone = graph["protected"].mouth.zone
    assert zone.angle_deg == 0.0
    object.__setattr__(zone, "angle_deg", -0.0)

    with pytest.raises(Iteration25SourceIntegrityError, match="signed zero"):
        validate_iteration25_source_graph(**graph)
