"""Continuous oblique withdrawal corridor, conditional on released interfaces.

The swept B-reps are exact translation images of conservative convex material
enclosures. They are not actual cartridge material or capacity. Containment is
checked against every authored material solid before any clearance can pass.
"""
from hashlib import sha1
import math
from pathlib import Path

import cadquery as cq
import numpy as np
from scipy.spatial import ConvexHull

from .realized_waste_cartridge import box, volume, RealizedWasteCartridgeError
from . import structural_frame_realization as frame_source

FRAME_OWNER_HEAD = '34273de3bd86294080e51873c212e988b4a966f4'
FRAME_SOURCE_BLOB = '0ea2ada736825fe1a0e06491d16690ae98cfccde'
TRANSLATION_MM = (0., 30., -45.)
ENVELOPE_SCALE = 1.001


def _convex_solid(points):
    p = np.asarray(points, dtype=float)
    if not np.isfinite(p).all():
        raise RealizedWasteCartridgeError('nonfinite service enclosure')
    hull = ConvexHull(p)
    faces = []
    for indices, equation in zip(hull.simplices, hull.equations):
        a, b, c = p[indices]
        if np.dot(np.cross(b-a, c-a), equation[:3]) < 0:
            b, c = c, b
        wire = cq.Wire.makePolygon([cq.Vector(*v) for v in (a,b,c,a)])
        faces.append(cq.Face.makeFromWires(wire))
    solid = cq.Solid.makeSolid(cq.Shell.makeShell(faces))
    if not solid.isValid() or len(solid.Solids()) != 1 or solid.Volume() <= 0:
        raise RealizedWasteCartridgeError('invalid convex service B-rep')
    return solid


def _enclosures():
    # Circumscribed polygon sections plus explicit reference-envelope padding.
    # Splitting at both loft breaks avoids a hull bridging a nonconvex shoulder.
    # The 0.1% reference growth is at most 0.037 mm in X, 0.018 mm in Y and
    # 0.0055 mm in Z. It alters no product material or numerical acceptance bound.
    n = 128
    wp = None
    previous = 0
    for z,w,h in ((-2,151.2,198.2),(-1,151.2,198.2),(10,164.2,203.2),(22,168.2,206.2)):
        points = [(w/2/math.cos(math.pi/n)*math.cos(2*math.pi*i/n),
                   h/2/math.cos(math.pi/n)*math.sin(2*math.pi*i/n)) for i in range(n)]
        wp = (cq.Workplane('XY',origin=(0,0,z)) if wp is None else wp.workplane(offset=z-previous)).polyline(points).close()
        previous = z
    envelope = wp.loft(ruled=True).intersect(box((74,36,20),(0,-80,8))).val()
    pieces = []
    for low,high in ((-2,-1),(-1,10),(10,18)):
        part = envelope.intersect(box((200,200,high-low),(0,-80,(low+high)/2)).val())
        center = np.array((0,-80,(low+high)/2))
        points = [tuple(center+(np.array(v.toTuple())-center)*ENVELOPE_SCALE) for v in part.Vertices()]
        pieces.append(_convex_solid(points))
    return tuple(pieces)


def require_material_coverage(candidate, enclosures):
    if not enclosures or any(not s.isValid() for s in enclosures):
        raise RealizedWasteCartridgeError('service enclosure missing or invalid')
    for name, material in (('body',candidate.body_solid),('closure',candidate.closure_solid)):
        outside = material.val().cut(*enclosures)
        if abs(outside.Volume()) > 1e-7 or outside.Solids():
            raise RealizedWasteCartridgeError('service envelope does not contain '+name)


def build_service_corridor(candidate, translation=TRANSLATION_MM):
    candidate.validate()
    delta = np.asarray(translation, dtype=float)
    if delta.shape != (3,) or not np.isfinite(delta).all() or np.linalg.norm(delta) == 0:
        raise RealizedWasteCartridgeError('invalid service translation')
    raw = Path(frame_source.__file__).read_bytes()
    if sha1(f'blob {len(raw)}\0'.encode()+raw).hexdigest() != FRAME_SOURCE_BLOB:
        raise RealizedWasteCartridgeError('stale frame corridor producer')
    enclosures = _enclosures()
    require_material_coverage(candidate, enclosures)
    sweeps = []
    for source in enclosures:
        points = [v.toTuple() for v in source.Vertices()]
        # For a convex P, conv(P, P+d) = P + [0,d], the complete continuous sweep.
        sweeps.append(_convex_solid(points + [tuple(np.array(p)+delta) for p in points]))
    m = candidate.model
    obstacles = {a.name:a.solid.val() for a in (m.shell,m.nasal_interface,*m.actuator_envelopes,
                                               m.water_reservoir_envelope,m.battery_reference_envelope)}
    frame = frame_source.build_structural_frame_realization(model=m)
    obstacles['CELL6_CURRENT_FRAME_CANDIDATE'] = frame.solid.val()
    checks = {name:[float(s.intersect(obstacle).Volume()) for s in sweeps]
              for name,obstacle in obstacles.items()}
    if any(not math.isfinite(v) or abs(v)>1e-7 for row in checks.values() for v in row):
        raise RealizedWasteCartridgeError('continuous service corridor collision')
    interfaces = dict(candidate.device_parts)
    interfaces['inlet_handoff_reference'] = candidate.inlet_connector_clearance_reference
    witness = cq.Compound.makeCompound([candidate.body_solid.val(),candidate.closure_solid.val()]).translate(tuple(delta*.02))
    contacts = {name:float(witness.intersect(s.val()).Volume()) for name,s in interfaces.items()}
    report = dict(
        status='CONTINUOUS_SHELL_PACKAGE_FRAME_CORRIDOR_CLEAR_INTERFACES_UNRESOLVED',
        translation_world_mm=list(translation), continuous_interval=[0.,1.],
        proof='EXACT_CONVEX_POLYTOPE_SWEEPS_WITH_CHECKED_COMPLETE_MATERIAL_CONTAINMENT',
        reference_envelope_scale=ENVELOPE_SCALE, material_outside_enclosures_mm3=0.,
        obstacle_intersections_mm3=checks,
        frame_owner_pr=117, frame_owner_head=FRAME_OWNER_HEAD, frame_source_blob=FRAME_SOURCE_BLOB,
        physical_material_shape_ids=['body','closure'],
        reference_shape_ids=['oblique_service_enclosures','oblique_service_sweeps'],
        wearer_present=False, powered=False,
        anatomy_during_service='WEARER_ABSENT_INSTALLED_PROTECTED_EXCLUSION_STILL_REQUIRED',
        interface_witness_translation_world_mm=list(delta*.02),
        fixed_interface_exact_material_witness_mm3=contacts,
        continuous_installed_device_path_proven=False,
        unresolved=['KEY_AND_BOLT_CAPTURE_ACCESS','WET_DISCONNECT_AND_PASSIVE_BACKFLOW_SEQUENCE',
                    'DEVICE_INTERFACE_FRAME_ATTACHMENT','EXTERIOR_OWNER_REBIND'],
        physical_validation_eligible=False,
    )
    return report, {'oblique_service_enclosures':cq.Workplane(obj=cq.Compound.makeCompound(enclosures)),
                    'oblique_service_sweeps':cq.Workplane(obj=cq.Compound.makeCompound(sweeps))}
