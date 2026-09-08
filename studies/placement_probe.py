import cadquery as cq, math, itertools,json
from masck_one.model import build_model
from masck_one.structural_frame_realization import _protected_zone_solid
m=build_model();protected=[]
for p in m.protected_volumes.all:
 z=p.zone;protected.append((z.zone_id,_protected_zone_solid(center_x_mm=z.center.x,center_y_mm=z.center.y,envelope_width_mm=z.envelope_width_mm,envelope_height_mm=z.envelope_height_mm,angle_deg=z.angle_deg,z_min_mm=-30,z_max_mm=40).val()))
rows=[]
for station,ys in [('superior',(62,66,70,74))]:
 for x,y,z in itertools.product((48,51,54,57),ys,(8,11)):
  # Bounding actual purchased assembly, including coil cap at midstroke.
  shape=cq.Workplane('XY').circle(6.35).extrude(16.5, both=False).translate((0,0,-8.25)).rotate((0,0,0),(0,1,0),61).translate((x,y,z)).val()
  v=sum(shape.intersect(p).Volume() for _,p in protected)
  sh=shape.intersect(m.shell.solid.val()).Volume()
  if v<1e-7 and sh<1e-7:rows.append(dict(station=station,center=[x,y,z],protected=v,shell=sh))
print(json.dumps(rows,indent=2))
