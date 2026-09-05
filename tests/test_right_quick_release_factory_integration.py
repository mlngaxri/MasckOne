from __future__ import annotations

import math

from masck_one.model import build_model
from masck_one.realized_waste_backbone_release import build_current_cell4_waste_backbone_release
from masck_one.right_quick_release_assembly import (
    CLOSURE_START_Z,
    HOOK_DEFLECTION,
    _upper,
    build_right_quick_release_assembly,
)


def _bounds(solid) -> tuple[float, float, float, float, float, float]:
    bb = solid.val().BoundingBox()
    return tuple(float(v) for v in (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax))


def _aabb_separation_mm(
    first: tuple[float, float, float, float, float, float],
    second: tuple[float, float, float, float, float, float],
) -> float:
    dx = max(second[0] - first[1], first[0] - second[1], 0.0)
    dy = max(second[2] - first[3], first[2] - second[3], 0.0)
    dz = max(second[4] - first[5], first[4] - second[5], 0.0)
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def _closure_descent_bound(assembly) -> tuple[float, float, float, float, float, float]:
    """Conservative bound for every pure-Z closure state, not waypoint sampling."""
    xmin, xmax, ymin, ymax, zmin, zmax = _bounds(assembly.upper_deflected.solid)
    return xmin, xmax, ymin, ymax, zmin, zmax + CLOSURE_START_Z


def _hook_relaxation_bound(assembly) -> tuple[float, float, float, float, float, float]:
    """Endpoint envelope for the controlled 0..HOOK_DEFLECTION monotonic Y deflection."""
    source = assembly.reset.latch.guide_capsule.solid
    nominal = _bounds(_upper(source, 0.0))
    deflected = _bounds(_upper(source, HOOK_DEFLECTION))
    return (
        min(nominal[0], deflected[0]),
        max(nominal[1], deflected[1]),
        min(nominal[2], deflected[2]),
        max(nominal[3], deflected[3]),
        min(nominal[4], deflected[4]),
        max(nominal[5], deflected[5]),
    )


def _released_component_bounds(model):
    return (
        (model.shell.name, _bounds(model.shell.solid)),
        *((part.name, _bounds(part.solid)) for part in model.actuator_envelopes),
        (model.water_reservoir_envelope.name, _bounds(model.water_reservoir_envelope.solid)),
        (model.waste_cartridge_envelope.name, _bounds(model.waste_cartridge_envelope.solid)),
        (model.battery_reference_envelope.name, _bounds(model.battery_reference_envelope.solid)),
    )


def test_complete_factory_motion_bounds_clear_released_main_packages() -> None:
    """Screen complete bounded motions, not only sampled assembly positions."""
    model = build_model()
    assembly = build_right_quick_release_assembly(model=model)

    motions = (
        ("SLIDER_INSERTION_EXACT_SWEEP", _bounds(assembly.insertion_sweep.solid)),
        ("UPPER_CLOSURE_COMPLETE_DESCENT_BOUND", _closure_descent_bound(assembly)),
        ("HOOK_RELAXATION_COMPLETE_DEFLECTION_BOUND", _hook_relaxation_bound(assembly)),
    )
    fixed = _released_component_bounds(model)

    for motion_id, motion_bounds in motions:
        for component_id, component_bounds in fixed:
            separation = _aabb_separation_mm(motion_bounds, component_bounds)
            assert separation > 0.0, f"{motion_id} overlaps released-main AABB for {component_id}"

    # The factory subassembly motion stays posterior to released shell material. This
    # separating plane is also the candidate-screen datum used without consuming Cell 2.
    shell_zmin = _bounds(model.shell.solid)[4]
    assert max(bounds[5] for _, bounds in motions) < shell_zmin


def test_complete_factory_motion_bounds_clear_released_cell4_waste_service_reservations() -> None:
    """Inflate each released route by its controlled service-envelope radius."""
    model = build_model()
    assembly = build_right_quick_release_assembly(model=model)
    motions = (
        ("SLIDER_INSERTION_EXACT_SWEEP", _bounds(assembly.insertion_sweep.solid)),
        ("UPPER_CLOSURE_COMPLETE_DESCENT_BOUND", _closure_descent_bound(assembly)),
        ("HOOK_RELAXATION_COMPLETE_DEFLECTION_BOUND", _hook_relaxation_bound(assembly)),
    )

    release = build_current_cell4_waste_backbone_release()
    assert release.realization.authority_revision == assembly.reset.latch.source_authority_revision

    for route in release.realization.routes:
        bounds_min, bounds_max = route.bounds_xyz_mm
        radius = float(route.service_envelope_radius_mm)
        route_bound = (
            float(bounds_min[0]) - radius,
            float(bounds_max[0]) + radius,
            float(bounds_min[1]) - radius,
            float(bounds_max[1]) + radius,
            float(bounds_min[2]) - radius,
            float(bounds_max[2]) + radius,
        )
        for motion_id, motion_bounds in motions:
            separation = _aabb_separation_mm(motion_bounds, route_bound)
            assert separation > 0.0, f"{motion_id} overlaps Cell 4 route {route.route_id} service bound"
