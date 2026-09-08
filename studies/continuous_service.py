"""Continuous conservative B-rep proof, with measured enclosure of every moving solid."""
import math,json
from pathlib import Path
import cadquery as cq
import numpy as np
from scipy.spatial import ConvexHull
from treatment_geometry import *

def cylinder_motion_bound(center,lo=-32,hi=0,angle=61,n=32):
    # Circumscribed polygon, not an inscribed tessellation. Radial excess is explicit.
    R=8.7/math.cos(math.pi/n);verts=[]
    for zz in (-9.4,8.6):
      for i in range(n):
        p=cq.Vertex.makeVertex(R*math.cos(2*math.pi*i/n),R*math.sin(2*math.pi*i/n),zz)
        q=np.array(pose(p,center,angle).Center().toTuple())
        verts.extend([q+np.array([0,0,lo]),q+np.array([0,0,hi])])
    v=np.unique(np.array(verts),axis=0);h=ConvexHull(v);faces=[]
    for ids,eq in zip(h.simplices,h.equations):
      tri=v[ids].copy()
      if np.dot(np.cross(tri[1]-tri[0],tri[2]-tri[0]),eq[:3])<0:tri=tri[::-1]
      w=cq.Wire.makePolygon([cq.Vector(*p) for p in tri],close=True)
      faces.append(cq.Face.makeFromWires(w))
    s=cq.Solid.makeSolid(cq.Shell.makeShell(faces))
    if not valid(s):raise ValueError('invalid circumscribed motion polyhedron')
    return s

def z_projection_bound(s,lo=-32):
    # Every prism shares a real +Z-facing planar datum. First prove this construction
    # encloses the original solid; then extend every interval by the complete motion.
    pieces=[];base=[];zmin=s.BoundingBox().zmin
    for f in s.Faces():
      if f.geomType()=='PLANE' and f.normalAt().z>.999999:
        depth=f.Center().z-zmin
        if depth>1e-7:
          base.append(cq.Solid.extrudeLinear(f.outerWire(),f.innerWires(),(0,0,-depth)))
          pieces.append(cq.Solid.extrudeLinear(f.outerWire(),f.innerWires(),(0,0,-depth+lo)))
    b=join(base);sweep=join(pieces)
    if not valid(sweep) or s.cut(b).Volume()>1e-7:raise ValueError('projection does not enclose source solid')
    return sweep

def verify():
 from mounted_station import station
 out=ROOT/'studies/generated';frame=cq.Shape.importBrep(str(out/'consumed_frame_reactions.brep'))
 boundary=cq.Shape.importBrep(str(out/'consumed_supported_pre_roll_boundary.brep'))
 model=build_model();pz=protected(model);thermal,tr=thermal_cells();r={}
 for kind,c in [('superior',(40,70,7)),('inferior',(52,-44,5))]:
   mat,ref=station(kind,c)
   frame_port=frame.cut(ref['required_draw_pin_bore']).cut(ref['required_key_port'])
   installed={k:dict(frame_mm3=iv(s,frame_port),boundary_mm3=iv(s,boundary),
       protected_mm3=sum(iv(s,p) for p in pz.values())) for k,s in mat.items()}
   env=cylinder_motion_bound(c);env0=cylinder_motion_bound(c,0,0)
   bare,_=cassette()
   containment={k:pose(s,c).cut(env0).Volume() for k,s in bare.items()}
   sweeps={'cassette':env,'bridge':z_projection_bound(ref['bridge_shape']),
           'output_shoe':z_projection_bound(mat['output_shoe'])}
   tests={}
   for k,s in sweeps.items():
     tests[k]=dict(valid=valid(s),frame_mm3=iv(s,frame_port),boundary_mm3=iv(s,boundary),
       protected_mm3=sum(iv(s,p) for p in pz.values()),
       thermal_material_mm3=sum(iv(s,p) for p in thermal.values()))
     s.exportBrep(str(out/f'{kind}_{k}_service_bound.brep'))
   r[kind]=dict(installed=installed,nominal_enclosure_deficit_mm3=containment,continuous_service=tests,
       motion_vector_mm=[0,0,-32],cylinder_bound_radial_excess_mm=8.7*(1/math.cos(math.pi/32)-1),
       state='FACTORY_SERVICE: facial liner and draw fastener removed, dry connector disconnected; socket shoe remains.',
       whole_product_service=False,excluded_unaccepted_sources=['retention roots/crown','final eye-roll exterior'])
 Path('studies/generated/continuous_service_report.json').write_text(json.dumps(r,indent=2,allow_nan=False)+'\n');print(json.dumps(r,indent=2))
if __name__=='__main__':verify()
