"""Representative mounted cassette; frame fixture is an explicit proposed interface port.
The reaction frame builds; proposed saddle ports and downstream integration remain open.
"""
import math,json
from pathlib import Path
import cadquery as cq
from treatment_geometry import *
from masck_one.structural_frame_actuator_reactions import (REACTION_X_MM,REACTION_Y_MM,
 BOSS_WIDTH_MM,BOSS_HEIGHT_MM,SOCKET_WIDTH_MM,SOCKET_HEIGHT_MM,SOCKET_DEPTH_MM)


def swept_tube(points,width=4.8,height=3.,wall=.35):
    a,b=np.array(points[0]),np.array(points[1]);axis=(b-a)/np.linalg.norm(b-a)
    lateral=np.cross(axis,np.array([0.,0.,1.]));lateral/=np.linalg.norm(lateral)
    pl=cq.Plane(origin=tuple(a),xDir=tuple(lateral),normal=tuple(axis))
    path=cq.Workplane('XY').polyline(points)
    return cq.Workplane(pl).rect(width,height).rect(width-2*wall,height-2*wall).sweep(path,transition='right').val()


def station(kind,center):
    mat,ref=cassette();world={k:pose(s,center) for k,s in mat.items()}
    cx,cy=REACTION_X_MM,REACTION_Y_MM*(1 if kind=='superior' else -1)
    fixture=box(BOSS_WIDTH_MM,BOSS_HEIGHT_MM,5.4,(cx,cy,-2.7)).cut(box(SOCKET_WIDTH_MM,SOCKET_HEIGHT_MM,SOCKET_DEPTH_MM,(cx,cy,-SOCKET_DEPTH_MM/2)))
    source_fixture=fixture
    # These are NEW required ports, not claimed present in current #117.
    axial_hole=cylinder(1.8,-8,2).translate((cx,cy,0))
    key_port=box(1.5,2,1.25,(cx+3.75,cy,-.625))
    fixture=fixture.cut(axial_hole).cut(key_port)
    # Recessed keyed draw shoe bears on the socket FLOOR; it adds no anterior bulk.
    # Its barrel receives a standard draw fastener, whose threads require selection.
    pilot=join([box(5.8,5.8,1.15,(cx,cy,-.675)),
        box(1.3,1.8,1.15,(cx+3.45,cy,-.675)),
        cylinder(1.7,-5.2,-.6).translate((cx,cy,0))]).cut(cylinder(1.,-6,1).translate((cx,cy,0)))
    world['socket_draw_shoe']=pilot
    # Posterior saddle solves the frame/exterior conflict at the outboard socket.
    # Return the load directly to the fixed rear hub, not a long front cage cantilever.
    target=pose(cq.Vertex.makeVertex(0,2.8,-9.0),center).Center().toTuple()
    if kind=='superior':points=[(cx,cy,-6.4),(64,59,-6.4),(56,66,-6.4),(target[0],target[1],-6.4)]
    else:points=[(cx,cy,-6.4),(target[0],target[1],-6.4)]
    tube=swept_tube(points,height=2.)
    saddle=box(8.8,8.8,1.,(cx,cy,-5.9)).cut(cylinder(1.05,-8,-4).translate((cx,cy,0)))
    tower=bar(points[-1],target,.85)
    bridge=join([saddle,tube,tower])
    # One fabricated rigid carrier, not two overlapping alleged mating parts.
    world['fixed_cage']=join([world['fixed_cage'],bridge])
    # The peripheral moving cup transfers motion to a separate light output shoe.
    # Offset the rod boot into a clear serviceable corridor. A short closed-section
    # moving arm carries force from the rear clamp without crossing the rear stops.
    dy=10.0 if kind=='superior' else -10.0
    arm_z=-6.6+(5-center[2])/math.cos(math.radians(61)) if kind=='inferior' else -6.6
    arm_local=box(1.4,abs(dy)+.6,1.,(7.1,dy/2,arm_z)).cut(
        box(1.,abs(dy)+1,.6,(7.1,dy/2,arm_z)))
    root=cylinder(.4,-7.4,arm_z+.5).translate((7.1,0,0))
    end=cylinder(.4,arm_z-.5,arm_z+.5).translate((7.1,dy,0))
    arm_local=join([arm_local,root,end])
    takeoff=pose(cq.Vertex.makeVertex(7.1,dy,arm_z),center).Center().toTuple()
    shoe_center=(takeoff[0],takeoff[1],-6.3)
    world['output_shoe']=join([pose(arm_local,center),box(8,10,.6,shoe_center),
        bar(takeoff,(takeoff[0],takeoff[1],-6.2),.4)])
    def polycyl(r,z0,z1):
        n=32;rr=r/math.cos(math.pi/n)
        pts=[(rr*math.cos(2*math.pi*j/n),rr*math.sin(2*math.pi*j/n)) for j in range(n)]
        return cq.Workplane('XY').polyline(pts).close().extrude(z1-z0).translate((0,0,z0)).val()
    bounds=[pose(box(1.4,abs(dy)+.6,1.,(7.1,dy/2,arm_z)),center),
        pose(polycyl(.4,-7.4,arm_z+.5).translate((7.1,0,0)),center),
        pose(polycyl(.4,arm_z-.5,arm_z+.5).translate((7.1,dy,0)),center),
        box(8,10,.6,shoe_center),
        polycyl(.4,-6.2,takeoff[2]).translate((takeoff[0],takeoff[1],0))]
    # Fastener identity is kept as purchased-hardware reference, not invented threads.
    ref={'bridge_shape':bridge,'output_piece_bounds':cq.Compound.makeCompound(bounds),'output_arm_local':arm_local,'output_shoe_center':cq.Vertex.makeVertex(*shoe_center),'frame_fixture_original':source_fixture,'frame_fixture_required_port':fixture,
      'required_key_port':key_port,'required_draw_pin_bore':axial_hole,
      'draw_fastener_envelope':join([cylinder(.9,-7.4,-1.8),cylinder(1.8,-7.9,-7.4)]).translate((cx,cy,0)),
      'supplier_magnet_package':pose(ref['supplier_magnet_package'],center)}
    return world,ref


def evaluate():
 m=build_model();pz=protected(m);out=ROOT/'studies/generated';report={}
 exterior_path=out/'consumed_supported_pre_roll_boundary.brep'
 ext=cq.Shape.importBrep(str(exterior_path)) if exterior_path.exists() else None
 allmat=[]
 for kind,c in STATION_POSES.items():
  mat,ref=station(kind,c);allmat+=list(mat.values())
  rows={k:dict(valid=valid(s),solids=len(s.Solids()),volume_mm3=s.Volume(),
    protected_mm3=sum(iv(s,p) for p in pz.values()),released_shell_mm3=iv(s,m.shell.solid.val()),
    supported_pre_roll_boundary_mm3=iv(s,ext) if ext else None) for k,s in mat.items()}
  # Positive capture geometry: installed key clear, a 90-degree wrong pose is blocked.
  fixture=ref['frame_fixture_required_port'];pilot=mat['socket_draw_shoe']
  cx,cy=REACTION_X_MM,REACTION_Y_MM*(1 if kind=='superior' else -1)
  installed=iv(pilot,fixture);wrong=iv(pilot.rotate((cx,cy,0),(cx,cy,1),90),fixture)
  report[kind]={'parts':rows,'source_reaction_builder_accepted':True,
    'required_new_frame_ports':['central draw-pin bore','genuinely asymmetric key port'],
    'installed_fixture_interference_mm3':installed,'wrong_90deg_interference_mm3':wrong,
    'frame_assembly_proof':'CURRENT_REACTION_FRAME_BUILDS; RETENTION_ROOT_AND_FINAL_EXTERIOR_BUILDERS_FAIL; REQUIRED_NEW_PORTS_NOT_PROMOTED'}
  cq.exporters.export(cq.Compound.makeCompound(list(mat.values())),str(out/f'{kind}_mounted_material.step'))
  cq.exporters.export(cq.Compound.makeCompound(list(ref.values())),str(out/f'{kind}_mounted_references.step'))
 (out/'mounted_report.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report,indent=2))
if __name__=='__main__':evaluate()
