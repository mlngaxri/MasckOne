import cadquery as cq,math,itertools,json
from masck_one.model import build_model,_loft_ellipses
from masck_one.structural_frame_realization import _protected_zone_solid
m=build_model(); protected=[]
for p in m.protected_volumes.all:
 z=p.zone;protected.append(_protected_zone_solid(center_x_mm=z.center.x,center_y_mm=z.center.y,envelope_width_mm=z.envelope_width_mm,envelope_height_mm=z.envelope_height_mm,angle_deg=z.angle_deg,z_min_mm=-30,z_max_mm=40).val())
base=cq.Workplane('XY').circle(8.0).extrude(19).translate((0,0,-9.5)).val()
rows=[]
for x,y,z,az in itertools.product((36,42,48),(65,70,75),(7,9),(0,45,90)):
 s=base.rotate((0,0,0),(0,1,0),61).rotate((0,0,0),(0,0,1),az).translate((x,y,z))
 if any(s.intersect(p).Volume()>1e-7 for p in protected):continue
 sh=s.intersect(m.shell.solid.val()).Volume()
 if sh<1e-7:rows.append(dict(center=[x,y,z],azimuth_deg=az,protected_mm3=0,shell_mm3=sh,bbox=[s.BoundingBox().zmin,s.BoundingBox().zmax]))
print(json.dumps(rows,indent=2));open('studies/cassette_corridor_results.json','w').write(json.dumps(rows,indent=2)+'\n')
