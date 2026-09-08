import cadquery as cq,json
from masck_one.model import build_model
from masck_one.exterior_inferior_turnover import build_inferior_turnover_exterior_shell
m=build_model();s=build_inferior_turnover_exterior_shell(m.authority,m.facial_reference,m.protected_volumes).val()
assert s.isValid() and len(s.Solids())==1
from masck_one.exterior_eye_roll import _final_crown_face,_posterior_eye_support_patch
from masck_one.exterior_rigid_clearance import cut_rigid_hard_envelopes
face=_final_crown_face(m.authority,m.facial_reference)
for z in (m.protected_volumes.eye_left.zone,m.protected_volumes.eye_right.zone):
 p=_posterior_eye_support_patch(face,wall_mm=m.authority.number('geometry','shell_nominal_wall_mm'),roll_radius_mm=m.authority.number('geometry','eye','inner_edge_roll_radius_mm'),eye_width_mm=z.envelope_width_mm,eye_height_mm=z.envelope_height_mm,eye_x_mm=z.center.x,eye_y_mm=z.center.y,eye_cant_deg=z.angle_deg)
 s=s.fuse(p).clean()
s=cut_rigid_hard_envelopes(cq.Workplane(obj=s),m.protected_volumes).val()
assert s.isValid() and len(s.Solids())==1
s.exportBrep('studies/generated/consumed_supported_pre_roll_boundary.brep')
print('DIAGNOSTIC PRE-ROLL ONLY; FINAL EYE ROLL BUILDER FAILS; NOT FINAL EXTERIOR',s.Volume(),flush=True)
