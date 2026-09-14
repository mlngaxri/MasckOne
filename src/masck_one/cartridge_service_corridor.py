"""Current-main oblique cartridge service corridor, with frame proof withheld.

The swept B-reps are reference geometry only. They prove a continuous translation
against current released shell/package obstacles. Current main has no released
structural-frame B-rep, so this module cannot and does not promote installed
extraction or insertion.
"""
from __future__ import annotations

from hashlib import sha1
from pathlib import Path
import math

import cadquery as cq
import numpy as np
from scipy.spatial import ConvexHull

from . import structural_frame as frame_contract
from .realized_waste_cartridge import (
    BLIND_SERVICE_CHECKPOINT_SHA,
    RealizedWasteCartridgeError,
    box,
    volume,
)

CURRENT_FRAME_CONTRACT_BLOB = "bda5ba87d232c0e6a22e200975a80414a10c9a83"
TRANSLATION_WORLD_MM = (0.0, 30.0, -45.0)
ENVELOPE_SCALE = 1.001
TOL_MM3 = 1e-7


def _require_current_frame_contract() -> None:
    raw = Path(frame_contract.__file__).read_bytes()
    actual = sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
    if actual != CURRENT_FRAME_CONTRACT_BLOB:
        raise RealizedWasteCartridgeError("current-main structural-frame contract moved")


def _convex_solid(points):
    points_array = np.asarray(points, dtype=float)
    if not np.isfinite(points_array).all():
        raise RealizedWasteCartridgeError("nonfinite service enclosure")
    hull = ConvexHull(points_array)
    faces = []
    for indices, equation in zip(hull.simplices, hull.equations):
        a, b, c = points_array[indices]
        if np.dot(np.cross(b - a, c - a), equation[:3]) < 0:
            b, c = c, b
        wire = cq.Wire.makePolygon([cq.Vector(*value) for value in (a, b, c, a)])
        faces.append(cq.Face.makeFromWires(wire))
    solid = cq.Solid.makeSolid(cq.Shell.makeShell(faces))
    if not solid.isValid() or len(solid.Solids()) != 1 or solid.Volume() <= 0:
        raise RealizedWasteCartridgeError("invalid convex service B-rep")
    return solid


def _enclosures():
    """Conservative convex pieces that fully contain body and closure."""
    count = 128
    workplane = None
    previous_z = 0
    for z, width, height in (
        (-2, 151.2, 198.2),
        (-1, 151.2, 198.2),
        (10, 164.2, 203.2),
        (22, 168.2, 206.2),
    ):
        points = [
            (
                width / 2 / math.cos(math.pi / count) * math.cos(2 * math.pi * i / count),
                height / 2 / math.cos(math.pi / count) * math.sin(2 * math.pi * i / count),
            )
            for i in range(count)
        ]
        workplane = (
            cq.Workplane("XY", origin=(0, 0, z))
            if workplane is None
            else workplane.workplane(offset=z - previous_z)
        )
        workplane = workplane.polyline(points).close()
        previous_z = z

    envelope = workplane.loft(ruled=True).intersect(box((74, 36, 20), (0, -80, 8))).val()
    pieces = []
    for low, high in ((-2, -1), (-1, 10), (10, 18)):
        part = envelope.intersect(box((200, 200, high - low), (0, -80, (low + high) / 2)).val())
        center = np.array((0, -80, (low + high) / 2))
        points = [
            tuple(center + (np.array(vertex.toTuple()) - center) * ENVELOPE_SCALE)
            for vertex in part.Vertices()
        ]
        pieces.append(_convex_solid(points))
    return tuple(pieces)


def require_material_coverage(candidate, enclosures) -> None:
    if not enclosures or any(not solid.isValid() for solid in enclosures):
        raise RealizedWasteCartridgeError("service enclosure missing or invalid")
    for name, material in (
        ("body", candidate.body_solid),
        ("closure", candidate.closure_solid),
    ):
        outside = material.val().cut(*enclosures)
        if abs(outside.Volume()) > TOL_MM3 or outside.Solids():
            raise RealizedWasteCartridgeError(f"service envelope does not contain {name}")


def build_service_corridor(candidate, translation=TRANSLATION_WORLD_MM):
    """Return exact current-main obstacle checks and reference sweep B-reps."""
    candidate.validate()
    _require_current_frame_contract()

    delta = np.asarray(translation, dtype=float)
    if delta.shape != (3,) or not np.isfinite(delta).all() or np.linalg.norm(delta) == 0:
        raise RealizedWasteCartridgeError("invalid service translation")

    enclosures = _enclosures()
    require_material_coverage(candidate, enclosures)
    sweeps = []
    for source in enclosures:
        points = [vertex.toTuple() for vertex in source.Vertices()]
        sweeps.append(
            _convex_solid(
                points + [tuple(np.array(point) + delta) for point in points]
            )
        )

    model = candidate.model
    obstacles = {
        component.name: component.solid.val()
        for component in (
            model.shell,
            model.nasal_interface,
            *model.actuator_envelopes,
            model.water_reservoir_envelope,
            model.battery_reference_envelope,
        )
    }
    intersections = {
        name: [float(sweep.intersect(obstacle).Volume()) for sweep in sweeps]
        for name, obstacle in obstacles.items()
    }
    if any(
        not math.isfinite(value) or abs(value) > TOL_MM3
        for row in intersections.values()
        for value in row
    ):
        raise RealizedWasteCartridgeError("continuous current-main service corridor collision")

    interfaces = dict(candidate.device_parts)
    interfaces["inlet_handoff_reference"] = candidate.inlet_connector_clearance_reference
    moving = cq.Compound.makeCompound(
        [candidate.body_solid.val(), candidate.closure_solid.val()]
    ).translate(tuple(delta * 0.02))
    interface_contacts = {
        name: float(moving.intersect(shape.val()).Volume())
        for name, shape in interfaces.items()
    }

    report = {
        "status": "CONTINUOUS_CURRENT_MAIN_SHELL_PACKAGE_CORRIDOR_CLEAR_FRAME_BREP_UNAVAILABLE",
        "checkpoint_evidence_parent_sha": BLIND_SERVICE_CHECKPOINT_SHA,
        "translation_world_mm": list(map(float, translation)),
        "continuous_interval": [0.0, 1.0],
        "proof": "EXACT_CONVEX_POLYTOPE_SWEEPS_WITH_CHECKED_COMPLETE_MATERIAL_CONTAINMENT",
        "reference_envelope_scale": ENVELOPE_SCALE,
        "material_outside_enclosures_mm3": 0.0,
        "obstacle_intersections_mm3": intersections,
        "frame_contract_blob": CURRENT_FRAME_CONTRACT_BLOB,
        "frame_geometry_status": "BLOCKED_CURRENT_MAIN_RELEASED_FRAME_IS_TOPOLOGY_ONLY_NO_BREP",
        "stale_checkpoint_frame_evidence_status": "INVALIDATED_NOT_REUSED_PR117_REALIZED_FRAME_WAS_NOT_RELEASED_MAIN",
        "physical_material_shape_ids": ["body", "closure"],
        "reference_shape_ids": ["oblique_service_enclosures", "oblique_service_sweeps"],
        "wearer_present": False,
        "powered": False,
        "anatomy_during_service": "WEARER_ABSENT_CURRENT_RELEASED_PROTECTED_EXCLUSIONS_STILL_CHECKED",
        "interface_witness_translation_world_mm": list(map(float, delta * 0.02)),
        "fixed_interface_exact_material_witness_mm3": interface_contacts,
        "continuous_installed_device_path_proven": False,
        "blind_insertion_proven": False,
        "unresolved": [
            "RELEASED_FRAME_BREP_FOR_CONTINUOUS_COLLISION_PROOF",
            "KEY_AND_BOLT_CAPTURE_ACCESS",
            "WET_DISCONNECT_AND_PASSIVE_BACKFLOW_SEQUENCE",
            "DEVICE_INTERFACE_FRAME_ATTACHMENT",
            "REMOVED_STATE_PORT_CLOSURE",
        ],
        "physical_validation_eligible": False,
    }
    references = {
        "oblique_service_enclosures": cq.Workplane(
            obj=cq.Compound.makeCompound(enclosures)
        ),
        "oblique_service_sweeps": cq.Workplane(
            obj=cq.Compound.makeCompound(sweeps)
        ),
    }
    return report, references
