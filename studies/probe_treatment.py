import cadquery as cq,math
from masck_one.model import build_model
from masck_one.structural_frame_actuator_reactions import build_structural_frame_actuator_reactions
from masck_one.structural_frame_realization import _protected_zone_solid
m=build_model();f=build_structural_frame_actuator_reactions(model=m)
frame=f.frame_with_reaction_counterparts
b=frame.val().BoundingBox();print('frame_bounds',b.xmin,b.xmax,b.ymin,b.ymax,b.zmin,b.zmax,flush=True)
for r in f.reactions:
 b=r.socket_tool.val().BoundingBox();print(r.reaction_id,r.center_xy_mm,'socket_z',b.zmin,b.zmax,'key_extra',r.keyed_socket_tool.cut(r.socket_tool).val().Volume(),flush=True)
