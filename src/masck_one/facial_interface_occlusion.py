"""Read-only CS-018 producer bindings and development-surface shadow mapping.

This module does not implement routines, readiness or product intelligence.
Projection occupancy is not skin contact, delivered product, film or fit proof.
"""
from hashlib import sha256
import json
from pathlib import Path
import cadquery as cq
from .facial_interface_bench import FacialInterfaceError, common_volume, box
from .model import build_model


def verify_sources(root: Path) -> dict:
    snapshot=json.loads((root/'docs/contracts/facial_interface_sources.json').read_text())
    for row in snapshot['sources']:
        if row['owner']=='main':
            if sha256((root/row['path']).read_bytes()).hexdigest()!=row['sha256']:
                raise FacialInterfaceError('consumed released producer changed: '+row['path'])
    return snapshot


def rectangle_clip(vertices,bounds):
    """Analytic convex polygon clipping, not sampling of motion or coverage."""
    polygon=list(vertices)
    for axis,edge,keep_greater in [(0,bounds[0],True),(0,bounds[1],False),(1,bounds[2],True),(1,bounds[3],False)]:
        output=[]
        if not polygon:break
        previous=polygon[-1]
        for current in polygon:
            pin=previous[axis]>=edge if keep_greater else previous[axis]<=edge
            cin=current[axis]>=edge if keep_greater else current[axis]<=edge
            if pin!=cin:
                fraction=(edge-previous[axis])/(current[axis]-previous[axis])
                output.append(tuple(previous[i]+fraction*(current[i]-previous[i]) for i in range(2)))
            if cin:output.append(current)
            previous=current
        polygon=output
    return abs(sum(polygon[i][0]*polygon[(i+1)%len(polygon)][1]-polygon[(i+1)%len(polygon)][0]*polygon[i][1] for i in range(len(polygon))))/2 if polygon else 0.0


def map_rectangle(model,bounds):
    rows=[]
    for t in model.coverage_mesh.triangles:
        vertices=[model.facial_surface.mesh.vertices[i] for i in t.vertex_indices]
        area=rectangle_clip([(p.x,p.y) for p in vertices],bounds)
        if area>1e-9:
            rows.append({'triangle_index':t.triangle_index,'region':t.region_id,'is_target':t.is_target,
                'projected_occupancy_mm2':area,'completion':'UNRESOLVED','surface_sha256':model.coverage_mesh.source_surface_sha256})
    return rows


def audit(root: Path,thermal_package: Path | None=None):
    snapshot=verify_sources(root)
    model=build_model()
    participants=[]
    for c in model.components:
        shape=c.solid.val();b=shape.BoundingBox()
        rows=map_rectangle(model,(b.xmin,b.xmax,b.ymin,b.ymax))
        participants.append({'id':c.name,'owner':'main','source':'src/masck_one/model.py',
            'role':c.geometry_role.value,'shape_valid':shape.isValid(),
            'footprint_kind':'CONSERVATIVE_BREP_BOUND_PROJECTION_NOT_EXACT_CONTACT',
            'region_cells':rows,'phase_states':{s:'UNKNOWN' for s in ['PLACEMENT','CLEAN','RINSE_RECOVER','TREAT','LEAVE_ON','SETTLE','RELEASE']},
            'required_exit':'Source-bound exit and independent reaction before final application',
            'geometry_is_anatomical_evidence':False})
    thermal=[]
    if thermal_package:
        manifest=json.loads((thermal_package/'fusion_thermal_handoff.json').read_text())
        source=next(x for x in snapshot['sources'] if x['owner']=='thermal')
        if manifest['producer_head_sha']!=source['head'] or manifest['source_file_sha256'][source['path']]!=source['sha256']:
            raise FacialInterfaceError('thermal producer/source mismatch')
        for component in manifest['components']:
            name=component['component_id']
            if not name.endswith('finned_store_and_choked_plate'):continue
            file=thermal_package/(name+'.step')
            if sha256(file.read_bytes()).hexdigest()!=manifest['step_sha256'][file.name]:
                raise FacialInterfaceError('thermal STEP bytes changed')
            shape=cq.importers.importStep(str(file)).val()
            if not shape.isValid() or len(shape.Solids())!=1:
                raise FacialInterfaceError('thermal imported material invalid')
            transform=component['world_transform'];offset=tuple(transform[i][3] for i in range(3))
            shape=shape.translate(offset)
            z=component['local_datums']['contact_plane_z_mm']+offset[2]
            faces=[f for f in shape.Faces() if f.geomType()=='PLANE' and abs(f.Center().z-z)<1e-7 and abs(f.normalAt().z)>.999999]
            if len(faces)!=1:raise FacialInterfaceError('ambiguous exact thermal contact face')
            face=faces[0];b=face.BoundingBox()
            # Source parameter and actual B-rep must agree before rectangle clipping.
            area=face.Area();params=component['parameters']
            if abs(area-params['plate_width_mm']*params['plate_height_mm'])>1e-7:
                raise FacialInterfaceError('thermal contact is no longer the bound rectangular face')
            rows=map_rectangle(model,(b.xmin,b.xmax,b.ymin,b.ymax))
            protected={}
            for volume in model.protected_volumes.all:
                zone=volume.zone
                cutter=(cq.Workplane('XY').workplane(offset=z-1).ellipse(zone.envelope_width_mm/2,zone.envelope_height_mm/2)
                    .extrude(2).val().rotate((0,0,0),(0,0,1),zone.angle_deg).translate((zone.center.x,zone.center.y,0)))
                plate_prism=box(params['plate_width_mm'],params['plate_height_mm'],1,(face.Center().x,face.Center().y,z))
                protected[zone.zone_id]=common_volume(plate_prism,cutter)
            thermal.append({'id':name,'source':source,'step_sha256':manifest['step_sha256'][file.name],
                'geometry_role':component['classification'],'world_transform':transform,
                'contact_plane_z_mm':z,'exact_planar_contact_area_mm2':area,'region_cells':rows,
                'pure_normal_retraction_retains_projected_shadow':True,
                'projected_shadow_after_any_pure_z_translation_mm2':area,
                'protected_prism_intersections_mm3':protected,
                'phase_states':{'TREAT':'CONTACT_INTENT_BENCH_ONLY','LEAVE_ON':'UNKNOWN_NO_OWNER_EXIT_PATH','RELEASE':'UNKNOWN'},
                'whole_product_registration':'UNRESOLVED','physical_validation':'REQUIRED'})
    # Missing owner instances are explicit participants, not omitted zero shadows.
    for owner in ('treatment','retention','frame','exterior'):
        participants.append({'id':owner+'_unresolved_face_facing_inventory','owner':owner,
            'source_bindings':[r for r in snapshot['sources'] if r['owner']==owner],
            'geometry_execution':'NOT_REEXECUTED_NO_NEW_ACCEPTED_ASSEMBLY_RECEIPT',
            'role':'UNRESOLVED_CANNOT_PROMOTE_TO_MATERIAL','region_cells':None,
            'phase_states':{'LEAVE_ON':'UNKNOWN','RELEASE':'UNKNOWN'},
            'blocker':'Exact assembled instance footprints, reaction transfer and normal release from canonical owner required'})
    return {'schema':'CS018_DEVELOPMENT_OCCLUSION_AUDIT','sources':snapshot,
        'participants':participants,'thermal_exact_contact_faces':thermal,
        'source_surface':model.coverage_mesh.source_surface_id,
        'source_surface_sha256':model.coverage_mesh.source_surface_sha256,
        'surface_kind':'PLANAR_DEVELOPMENT_REFERENCE_NOT_REGISTERED_ANATOMY',
        'whole_face_complete':False,'cs018_closed':False,'human_use_eligible':False}
