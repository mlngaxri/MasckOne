import cadquery as cq,itertools,json
from treatment_geometry import *
m=build_model();pz=protected(m);boundary=cq.Shape.importBrep('studies/generated/consumed_supported_pre_roll_boundary.brep')
base=cylinder(8.7,-9.4,8.6)
thermal_envelopes=[box(w+3,16,14,(x,y,10.2)) for x,y,w in [(52.5,-26,19),(52.5,-10,19),(54.5,6,10)]]
rows=[]
for x,y,z,angle in itertools.product((48,50,52,54),(-44,-48,-52),(3,5),(-61,61)):
 s=pose(base,(x,y,z),angle)
 if any(iv(s,p)>1e-7 for p in thermal_envelopes):continue
 if iv(s,pz['MASCK_ONE-PROTECTED-MOUTH'])>1e-7:continue
 v=iv(s,boundary)
 if v<1e-7:
  row=dict(center=[x,y,z],angle=angle,protected_mm3=0,thermal_envelope_mm3=0,supported_pre_roll_mm3=v)
  rows.append(row);print(row,flush=True)
Path('studies/inferior_corridor_results.json').write_text(json.dumps(rows,indent=2)+'\n')
