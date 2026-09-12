"""Read-only B-rep screens for the isolated fit proof.

Full authority protected footprints are preserved. Extrusion covers the entire
tested rigid shell. This is a conservative projected-domain screen; unresolved
anatomical depth must not be inferred from that extrusion.
"""
from hashlib import sha256
import json
from pathlib import Path
import math
import cadquery as cq
from .adversarial_fit_proof import Variation, warp, transform, source_snapshot, FitProofError
from .model import build_model


def common(a,b):
    q=a.intersect(b)
    if not q.isValid():raise FitProofError('invalid Boolean is not zero collision')
    v=sum(s.Volume() for s in q.Solids())
    if not math.isfinite(v) or v<0:raise FitProofError('invalid volume')
    return v


def protected_screen(v=Variation(),pose=(0,0,0,0,0,0),model=None):
    m=model or build_model();s=m.shell.solid.val();b=s.BoundingBox()
    if not s.isValid():raise FitProofError('released shell invalid')
    results={};shapes={}
    for volume in m.protected_volumes.all:
        z=volume.zone
        point=warp([[z.center.x,z.center.y,0]],v,m.authority)[0]
        # Only product-specific aperture variation is changed; the authority
        # rigid clearance around it is retained unchanged.
        width=z.envelope_width_mm
        if 'MOUTH' in z.zone_id:width+=v.mouth_width
        if width<=0:raise FitProofError('invalid protected width')
        # Deliberately conservative source-depth screen. Margin is a geometry
        # construction extension, not an anatomical or safety tolerance.
        reach=max(abs(b.zmin),abs(b.zmax),abs(point[2]))+200
        q=cq.Workplane('XY').workplane(offset=-reach).ellipse(width/2,z.envelope_height_mm/2).extrude(2*reach).val()
        q=q.rotate((0,0,0),(0,0,1),z.angle_deg).translate(tuple(point))
        for axis,angle in zip(((1,0,0),(0,1,0),(0,0,1)),pose[3:]):q=q.rotate((0,0,0),axis,angle)
        q=q.translate(tuple(pose[:3]));shapes[z.zone_id]=q
        amount=common(s,q)
        results[z.zone_id]={'common_mm3':amount,
            'status':'PROJECTED_PROTECTED_CONFLICT' if amount>1e-7 else 'PROJECTED_PROTECTED_CLEAR',
            'rigid_clearance_mm':z.required_rigid_clearance_mm,'shape_width_mm':width,
            'anatomical_depth':'UNKNOWN','reference_kind':'CONSERVATIVE_PROTECTED_PRISM'}
    return {'source_shell':'src/masck_one/model.py:_build_shell','source_role':m.shell.geometry_role.value,
            'source_surface_kind':m.facial_surface.descriptor.kind,'source_sha256':source_snapshot()['consumed_files'],
            'runtime_cadquery':cq.__version__,'pose':list(pose),'zones':results,
            'whole_fit':'UNKNOWN','physical_validation':False},shapes,s


def export_screen(output:Path,v=Variation(),pose=(0,0,0,0,0,0)):
    r,refs,s=protected_screen(v,pose);output.mkdir(parents=True,exist_ok=True)
    cq.exporters.export(s,str(output/'RELEASED_SHELL_READ_ONLY.step'))
    cq.exporters.export(cq.Compound.makeCompound(list(refs.values())),str(output/'PROTECTED_REFERENCE_ONLY.step'))
    r['step_sha256']={p.name:sha256(p.read_bytes()).hexdigest() for p in output.glob('*.step')}
    (output/'protected_screen.json').write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
    return r
