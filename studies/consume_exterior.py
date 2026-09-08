import cadquery as cq,json
from masck_one.exterior_eye_roll import build_eye_rolled_exterior_shell
from masck_one.model import build_model
m=build_model()
s=build_eye_rolled_exterior_shell(m.authority,m.facial_reference,m.protected_volumes).val()
s.exportBrep('studies/generated/consumed_exterior.brep')
print(json.dumps({'valid':s.isValid(),'solids':len(s.Solids()),'volume_mm3':s.Volume()}))
