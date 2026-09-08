"""Screen exact current point/route interfaces, never invent missing channel walls."""
from treatment_geometry import *
from treatment_interfaces import thermal_interfaces
from continuous_service import cylinder_motion_bound
from masck_one.realized_waste_backbone import Line3
from masck_one.realized_waste_backbone_release import build_current_waste_routing_sources,build_current_cell4_waste_backbone_release

def study():
    src=build_current_waste_routing_sources();release=build_current_cell4_waste_backbone_release()
    mat,ref=thermal_interfaces();obstacles={}
    for kind,c in STATION_POSES.items():
        b=cylinder_motion_bound(c,0,0)
        obstacles[kind+'_R']=b;obstacles[kind+'_L']=b.mirror('YZ')
    combined=mat|obstacles;outlets=[]
    for o in src.distribution.placements:
        # Controlled placement clearance radius is a conservative local reservation.
        p=cq.Solid.makeSphere(o.required_clearance_mm,cq.Vector(*o.center_xyz_mm))
        hits={k:iv(p,v) for k,v in combined.items() if iv(p,v)>1e-7}
        outlets.append(dict(id=o.outlet_id,fluid=o.fluid_identity,center=o.center_xyz_mm,intersections_mm3=hits))
    routes=[]
    for r in release.realization.routes:
        cells=[]
        for primitive in r.centerline:
            lo,hi=map(np.array,primitive.bounds_xyz_mm);rad=r.service_clearance_radius_mm if hasattr(r,'service_clearance_radius_mm') else 3.2
            bound=box(*(hi-lo+2*rad),tuple((lo+hi)/2))
            # Refine nonzero AABB flags against the actual continuous route tube.
            if isinstance(primitive,Line3):
                tube=bar(primitive.start.as_tuple(),primitive.end.as_tuple(),rad)
            else:
                edge=cq.Edge.makeCircle(primitive.radius_mm,cq.Vector(*primitive.center.as_tuple()),
                    cq.Vector(0,0,1),primitive.start_angle_deg,primitive.start_angle_deg+primitive.sweep_angle_deg)
                wire=cq.Wire.assembleEdges([edge]);pnt=edge.positionAt(0);tangent=edge.tangentAt(0)
                tube=cq.Workplane(cq.Plane(origin=pnt,normal=tangent)).circle(rad).sweep(wire).val()
            tube=join([tube,cq.Solid.makeSphere(rad,cq.Vector(*primitive.start.as_tuple())),
                       cq.Solid.makeSphere(rad,cq.Vector(*primitive.end.as_tuple()))])
            if not valid(tube):raise ValueError('invalid route reservation sweep')
            hits={k:iv(tube,v) for k,v in combined.items() if iv(tube,v)>1e-7}
            cells.append(dict(primitive=primitive.manifest(),exact_route_reservation_vs_material_or_cassette_bound_mm3=hits))
        routes.append(dict(id=r.route_id,fluid=r.fluid_identity,stage=r.stage,segments=cells))
    result=dict(outlets=outlets,routes=routes,source_distribution=src.distribution.architecture_sha256,
       source_waste=release.realization.manifest_sha256,
       missing_geometry=['fresh channel walls/cross-sections','registered outlet-to-groove surfaces','acquisition gutters','pump installed hardware'],
       complete_cleaning_coexistence=False,physical_validation=False)
    Path('studies/generated/cleaning_coexistence_report.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':study()
