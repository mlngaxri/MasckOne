from __future__ import annotations

import math

import cadquery as cq

from masck_one.cleanser_pump_distribution import (
    CASSETTE_OUTLET_WORLD_MM,
    FLUID_IDENTITY,
    LUMEN_DIAMETER_SEED_MM,
    PACKAGE_ENVELOPE_XYZ_MM,
    PUMP_INLET_WORLD_MM,
    ROUTE_POINTS_WORLD_MM,
    SOURCE_MAIN_SHA,
    build_cleanser_pump_distribution,
)


def test_cleanser_pump_and_source_route_are_valid_source_bound_breps() -> None:
    result = build_cleanser_pump_distribution()
    assert FLUID_IDENTITY == "CLEANSER"
    assert SOURCE_MAIN_SHA == "a0ea51874d8967c512468932fac627e8bba5f95f"
    assert result.package_reference_solid.solids().size() == 1
    assert result.package_reference_solid.val().isValid()
    assert result.route_reference_solid.solids().size() == 1
    assert result.route_reference_solid.val().isValid()
    assert math.isclose(result.package_reference_solid.val().Volume(), math.prod(PACKAGE_ENVELOPE_XYZ_MM), abs_tol=1e-7)


def test_cleanser_source_route_binds_realized_cassette_to_distinct_pump() -> None:
    result = build_cleanser_pump_distribution()
    assert ROUTE_POINTS_WORLD_MM[0] == CASSETTE_OUTLET_WORLD_MM
    assert ROUTE_POINTS_WORLD_MM[-1] == PUMP_INLET_WORLD_MM
    assert result.route_centerline_length_mm == sum(
        math.dist(a, b) for a, b in zip(ROUTE_POINTS_WORLD_MM[:-1], ROUTE_POINTS_WORLD_MM[1:])
    )
    expected = math.pi * (LUMEN_DIAMETER_SEED_MM / 2.0) ** 2 * result.route_centerline_length_mm / 1000.0
    assert math.isclose(result.neutral_geometric_lumen_volume_mL, expected, rel_tol=0.0, abs_tol=1e-12)


def test_cleanser_source_route_junctions_have_positive_brep_overlap() -> None:
    result = build_cleanser_pump_distribution()
    for point in ROUTE_POINTS_WORLD_MM[1:-1]:
        witness = cq.Workplane("XY").sphere(LUMEN_DIAMETER_SEED_MM / 4.0).translate(point)
        assert result.route_reference_solid.val().intersect(witness.val()).Volume() > 0.0


def test_cleanser_route_manifest_refuses_hydraulic_or_supplier_promotion() -> None:
    manifest = build_cleanser_pump_distribution().manifest()
    assert manifest["fluid_identity"] == "CLEANSER"
    assert manifest["pump"]["selection_status"] == "DIMENSIONAL_SCREEN_ONLY_NOT_SUPPLIER_SELECTED"
    assert manifest["source_route"]["support_status"] == "BLOCKED_PENDING_RELEASED_FRAME_MEMBER_GEOMETRY"
    assert manifest["downstream"]["status"] == "BLOCKED_PENDING_RELEASED_WORLD_COORDINATE_MANIFOLD_DATUM_AND_SIX_OUTLET_PATHS"
    firewall = manifest["evidence_firewall"]
    for forbidden in ("CHEMISTRY", "VISCOSITY", "FLOW", "PRESSURE", "PRIMING", "LEAKAGE", "ORIENTATION", "CONNECTOR", "TUBING", "PUMP_SELECTION"):
        assert forbidden in firewall
