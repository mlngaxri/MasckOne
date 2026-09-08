"""Bounded geometric sensitivity, fill planes and service rejection evidence."""
from dataclasses import replace
import math
from pathlib import Path
import json
import cadquery as cq
from .realized_waste_cartridge import (
    build_realized_waste_cartridge, volume, box, cylinder, bounds,
    RealizedWasteCartridgeError, protected_prism,
)

def wall_separation(candidate):
    # Measure original nested skin faces away from the deliberately open rim.
    # Both sets omit horizontal floor/lid caps; intentional bores are not walls.
    def sides(shape):
        return [f for f in shape.val().Faces()
                if not (f.geomType()=='PLANE' and abs(f.normalAt().z)>0.999999)]
    inner=cq.Compound.makeCompound(sides(candidate.inner_reference))
    outer=cq.Compound.makeCompound(sides(candidate.outer_reference))
    return dict(minimum_nested_side_separation_mm=inner.distance(outer),
                planar_floor_mm=candidate.seed.floor_mm,lid_mm=candidate.seed.lid_mm,
                semantics='NOMINAL_BREP_SEPARATION_EXCLUDES_INTENTIONAL_PORTS_NOT_PROCESS_CAPABILITY')

def orientation_fill(candidate):
    """Exact chamber/half-space intersections at the lower open port edge.

    Hypothetical freely communicating open ports, no valves, capillarity, wetting,
    foam, media or dynamic effects. These volumes are NOT retained capacities.
    """
    result=[]
    for angle in (-90.,-30.,0.,30.,90.):
        r=math.radians(angle)
        up=(0.,math.cos(r),math.sin(r))
        inlet_height=-82*up[1]+14*up[2]-1.2
        vent_height=-89*up[1]+18*up[2]-abs(up[1])*1.
        height=min(inlet_height,vent_height)
        origin=tuple(height*x for x in up)
        plane=cq.Plane(origin=origin,xDir=(1,0,0),normal=up)
        half=cq.Workplane(plane).box(500,500,500,centered=(True,True,False)).translate(tuple(-500*x for x in up))
        filled=candidate.installed_free_cavity_reference.intersect(half)
        # Rotate so up maps to +Z, then take OCC's bounded minimum elevation.
        oriented=candidate.installed_free_cavity_reference.rotate((0,0,0),(1,0,0),90-angle)
        low=oriented.val().BoundingBox().zmin
        result.append(dict(pitch_deg=angle,up_world=up,open_port_fill_plane_mm=height,
                           lowest_cavity_height_mm=low,liquid_region_count=len(filled.val().Solids()),
                           geometric_volume_below_open_ports_mL=volume(filled)/1000))
    return dict(method='BREP_HALFSPACE_GRAVITY_GEOMETRY_ONLY',retained_capacity_mL=None,
                residual_liquid_uL=None,physical_validation_eligible=False,orientations=result)

def local_bolt_sweeps(candidate):
    rows=[]
    for name,sign in (('left',-1),('right',1)):
        # Exact continuous union of a cylinder translating along its own axis.
        sweep=cylinder((sign*35.9,-82,17),(sign,0,0),6.,1.2)
        guide=candidate.device_parts[name+'_bolt_guide']
        row=dict(id=name+'_bolt_retract',translation_world_mm=(sign*2,0,0),
                 coverage='EXACT_CONTINUOUS_AXIAL_CYLINDER_SWEEP_T_IN_0_1',
                 closure_intersection_mm3=volume(sweep.intersect(candidate.closure_solid)),
                 guide_intersection_mm3=volume(sweep.intersect(guide)),
                 shell_intersection_mm3=volume(sweep.intersect(candidate.model.shell.solid)),
                 retracted_clearance_mm=candidate.device_parts[name+'_bolt'].translate((sign*2,0,0)).val().distance(candidate.closure_solid.val()))
        if any(row[k]>1e-7 for k in ('closure_intersection_mm3','guide_intersection_mm3','shell_intersection_mm3')):
            raise RealizedWasteCartridgeError('local bolt continuous sweep collides')
        row['status']='LOCAL_GEOMETRY_PASS_NOT_INSTALLED_DEVICE_SERVICE'
        rows.append(row)
    return rows

def service_obstructions(candidate):
    """Reject motions with exact collision witnesses; never certify from samples.

    A single interfering state disproves a proposed continuous path. Clear states
    cannot prove the rest of a path clear. The AABB sweep is a continuous
    conservative screening reference, not a measured material swept volume.
    """
    moving=cq.Workplane(obj=cq.Compound.makeCompound([candidate.body_solid.val(),candidate.closure_solid.val()]))
    bb=bounds(moving)
    rows=[]
    for name,delta in [('inferior',(0,-1,0)),('posterior',(0,0,-1)),('anterior',(0,0,1))]:
        trial=moving.translate(delta)
        conflict=volume(trial.intersect(candidate.model.shell.solid))
        full=tuple(45*x for x in delta)
        lo=[min(bb[2*i],bb[2*i]+full[i]) for i in range(3)]
        hi=[max(bb[2*i+1],bb[2*i+1]+full[i]) for i in range(3)]
        envelope=box(tuple(b-a for a,b in zip(lo,hi)),tuple((a+b)/2 for a,b in zip(lo,hi)))
        rows.append(dict(motion=name,continuous_translation_world_mm=full,
                         continuous_envelope_method='ANALYTICAL_AABB_UNION_OVER_FULL_TRANSLATION',
                         conservative_envelope_shell_intersection_mm3=volume(envelope.intersect(candidate.model.shell.solid)),
                         witness_translation_world_mm=delta,exact_material_witness_intersection_mm3=conflict,
                         status='REJECTED_EXACT_COLLISION_WITNESS' if conflict>1e-7 else 'UNRESOLVED_NO_CONTINUOUS_MATERIAL_PROOF'))
    return dict(status='BLOCKED',rows=rows,continuous_installed_device_path_proven=False,
                frame_counterpart='UNRESOLVED',wet_disconnect_sequence='UNRESOLVED',
                physical_validation_eligible=False)

def require_installed_service_clear(candidate):
    result=service_obstructions(candidate)
    if not result['continuous_installed_device_path_proven']:
        raise RealizedWasteCartridgeError('installed service remains blocked; local bolts do not close product extraction')

def sensitivity(candidate):
    rows=[]
    for field in ('wall_mm','floor_mm','lid_mm'):
        for delta in (-.025,.025):
            seed=replace(candidate.seed,**{field:getattr(candidate.seed,field)+delta})
            c=build_realized_waste_cartridge(model=candidate.model,seed=seed,verify_route=False)
            rows.append(dict(parameter=field,change_mm=delta,cavity_mL=c.installed_geometric_free_capacity_mL,
                             capacity_change_mL=c.installed_geometric_free_capacity_mL-candidate.installed_geometric_free_capacity_mL))
    return dict(status='DOE_SENSITIVITY_NOT_CONTROLLED_MANUFACTURING_TOLERANCE',controlled_tolerance_result=None,rows=rows)

def export_cartridge_review(output):
    path=Path(output);path.mkdir(parents=True,exist_ok=True)
    c=build_realized_waste_cartridge()
    report=c.manifest()
    report['wall_separation']=wall_separation(c)
    report['local_bolt_sweeps']=local_bolt_sweeps(c)
    report['service']=service_obstructions(c)
    report['orientation_fill']=orientation_fill(c)
    report['sensitivity']=sensitivity(c)
    from .cartridge_service_corridor import build_service_corridor
    report['oblique_service_corridor'], service_shapes = build_service_corridor(c)
    shapes=c.review_shapes()
    shapes.update(service_shapes)
    roundtrips={}
    for name,s in shapes.items():
        target=path/(name+'.step');cq.exporters.export(s,str(target))
        imported=cq.importers.importStep(str(target))
        # Consistent per-solid volume semantics; artifact fidelity isn't capacity.
        dv=volume(imported)-volume(s)
        if not imported.val().isValid() or len(imported.val().Solids())!=len(s.val().Solids()) or abs(dv)>1e-4:
            raise RealizedWasteCartridgeError('cartridge STEP fidelity changed: '+name)
        roundtrips[name]=dict(valid=True,solid_count=len(imported.val().Solids()),volume_delta_mm3=dv)
    report['step_roundtrips']=roundtrips
    material=cq.Compound.makeCompound([c.body_solid.val(),c.closure_solid.val()])
    for name,direction in [('front',(0,0,1)),('rear',(0,0,-1)),('isometric',(1,-1,1))]:
        cq.exporters.export(material,str(path/(name+'.svg')),opt=dict(width=1000,height=750,projectionDir=direction,showHidden=False))
    (path/'cartridge_report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    return report

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',default='generated/cartridge-review');args=p.parse_args()
    print(json.dumps(export_cartridge_review(args.output),indent=2,allow_nan=False))
