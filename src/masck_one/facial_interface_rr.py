"""RR instrumentation insert for the canonical CS018 unpowered bench fixture.

Analytic inert coupon variants and manually positioned contact controls only.
No facial fit, powered cosmetic apparatus, fluid recipe or human-use procedure.
"""
from hashlib import sha256
import json
from pathlib import Path
import cadquery as cq
from .facial_interface_bench import Parameters, build, box, cylinder, positive, common_volume, translation_bound
from .facial_interface_measurements import STAGES, template


def instrumentation(p=Parameters(), existing=None):
    material,refs,base_report = existing if existing is not None else build(p)
    material=dict(material);refs=dict(refs)
    coupon=material['coupon']
    # Integral registration tabs remain outside the active 30 x 40 mm domain.
    fiducials={}
    for x in (-25,25):
        for y in (-25,25):
            coupon=coupon.fuse(box(10,8,2.2,(x,y,-5)))
            fx=x+(-2 if x<0 else 2)
            coupon=coupon.cut(cylinder(.6,.5,(fx,y,-4.3)))
            fiducials[f'FID_{"L" if x<0 else "R"}_{"B" if y<0 else "T"}']=[fx,y,-3.9]
    collectors={}
    for side,x in [('left',-20),('right',20)]:
        coupon=coupon.cut(box(2.8,40.6,1.6,(x,0,-4.6)))
        trough=box(2.4,40,1.4,(x,0,-4.6)).cut(box(1.4,39,1.3,(x,0,-4.25)))
        collectors['boundary_collector_'+side]=positive(trough.clean(),'removable boundary collector')
        refs['BOUNDARY_'+side.upper()]=box(1.4,39,4,(x,0,-2.9))
    material['coupon']=positive(coupon.clean(),'instrumented weighable coupon')
    material.update(collectors)
    # A separate contact-control insert replaces the dirty cassette for C/D.
    # Crossbar sits on existing removable pins and locates on the same posts.
    bar=box(76,8,4,(0,0,37.25))
    for x in (-32,32):bar=bar.cut(cylinder(3+p.guide_radial_clearance_mm,6,(x,0,34)))
    contacts={};pins={}
    R=p.coupon_radius_mm
    inner=cylinder(R,80,(0,-40,-R),(0,1,0))
    shell=cylinder(R+1.2,80,(0,-40,-R),(0,1,0)).cut(inner)
    for side,x in [('left',-9),('right',9)]:
        shoe=shell.intersect(box(10,10,8,(x,0,0)))
        shoe=shoe.fuse(box(4,4,49,(x,0,24.5))).cut(inner)
        shoe=shoe.fuse(box(8,8,2,(x,0,49)))
        # Square guide constrains both rotations and lateral translation.
        bar=bar.cut(box(4.3,4.3,6,(x,0,37.25)))
        z=37.25-p.normal_lift_mm
        shoe=shoe.cut(cylinder(1.35,10,(x,-5,z),(0,1,0)))
        bar=bar.cut(cylinder(1.35,10,(x,-5,37.25),(0,1,0)))
        pin=cylinder(1.25,12,(x,-6,37.25),(0,1,0)).fuse(cylinder(2,1,(x,-7,37.25),(0,1,0)))
        contacts['contact_'+side]=positive(shoe.clean(),'controlled contact island')
        pins['contact_pin_'+side]=positive(pin.clean(),'contact parking pin')
        # Bounding prism minus the upward-closed coupon is conservative over
        # the entire +Z path, retaining the curved initial contact boundary.
        refs['CONTACT_LIFT_'+side.upper()]=translation_bound(shoe,(0,0,p.normal_lift_mm)).cut(inner)
    alternate={k:v for k,v in material.items() if k!='clean_cassette'}
    alternate.update(contacts);alternate.update(pins);alternate['contact_crossbar']=positive(bar.clean(),'contact crossbar')
    base_states=base_report['states']
    states={}
    for sid,lift_left,lift_right in [('PERMANENT_CONTACT',0,0),('FIRST_EXIT',p.normal_lift_mm,0),
                                    ('ALL_CONTACT_CLEAR',p.normal_lift_mm,p.normal_lift_mm)]:
        transforms=dict(base_states['ISOLATED'])
        transforms.pop('clean_cassette',None)
        # Dirty catch tray is parked until both contacts clear its corridor.
        transforms['catch_shutter']=(0,0 if lift_left and lift_right else p.shutter_travel_mm,0)
        for side,lift in [('left',lift_left),('right',lift_right)]:
            transforms['contact_'+side]=(0,0,lift)
            transforms['contact_pin_'+side]=(0,0,0) if lift else (0,-20,0)
        states[sid]=transforms
    checks={}
    for sid,transforms in states.items():
        posed=[(k,s.translate(transforms.get(k,(0,0,0)))) for k,s in alternate.items()]
        for i,(a,s) in enumerate(posed):
            for b,t in posed[i+1:]:checks[sid+'/'+a+'/'+b]=common_volume(s,t)
    for side in ('left','right'):
        moving=refs['CONTACT_LIFT_'+side.upper()]
        # A full bounding box would fill the guide hole/empty cap corners. The
        # bar clearance is checked using the exact stem extrusion over the full
        # guide height, since the wide shoe/cap cannot reach the bar in this stroke.
        x=-9 if side=='left' else 9
        stem_bound=box(4,4,4,(x,0,37.25))
        checks['lift/'+side+'/bar_stem']=common_volume(stem_bound,bar)
        for k in ('coupon','normal_guide_left','normal_guide_right'):
            checks['lift/'+side+'/'+k]=common_volume(moving,alternate[k])
        lifted=contacts['contact_'+side].translate((0,0,p.normal_lift_mm))
        checks['scan/'+side]=common_volume(refs['DELIVERY_SCAN'],lifted)
        checks['shutter/'+side]=common_volume(refs['SHUTTER_TRANSLATION'],lifted)
        checks['lift/'+side+'/other']=common_volume(moving,contacts['contact_'+('right' if side=='left' else 'left')])
    checks['scan/bar']=common_volume(refs['DELIVERY_SCAN'],bar)
    # Film contact is the intended negative control. The final clear case has
    # positive standoff; its release moves outward, never laterally across film.
    footprints={}
    for side,s in contacts.items():
        footprints[side]={k:common_volume(v,s) for k,v in refs.items() if k.startswith('CHEEK_COUPON_')}
        checks['clear/'+side+'/film']=common_volume(s.translate((0,0,p.normal_lift_mm)),refs['FILM'])
    report={'schema':'MASCK_RR_INSTRUMENTATION_1','parameters':base_report['parameters'],
            'scope':'OFF_FACE_UNPOWERED_INERT_ANALOG','human_use_eligible':False,'physical_result':None,
            'base_source_sha256':sha256(Path(__file__).with_name('facial_interface_bench.py').read_bytes()).hexdigest(),
            'source_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
            'fiducials_mm':fiducials,'image_requirement':'Calibrated curved-surface rectification before rigid fiducial registration',
            'required_cells':[k for k in refs if k.startswith('CHEEK_COUPON_')],
            'contact_cell_intersections_mm3':footprints,'states':states,'collision_volumes_mm3':checks,
            'collision_blockers':[k for k,v in checks.items() if v>1e-7],
            'case_A':'Permanent contact negative control; do not credit occluded cells',
            'case_B':'Canonical full-cassette lift, isolation and under-tray application path',
            'case_C':'Independent first/second island exit with external base carrying reaction throughout',
            'case_D':'Secondary application to first-exposed then second-exposed cells; no return onto completed film',
            'reaction_boundary':'Bench base only; no cranial support or wearable transfer claim',
            'mass':{'material_volumes_mm3':{k:v.Volume() for k,v in alternate.items()},
                    'material_density':None,'bench_mass':None,'wearable_mass':None},
            'measurement_components':['coupon',*collectors],
            'stability_evidence':'Geometric pin/guide constraint only; force/deflection/support telemetry required',
            'surface_calibration':'Unqualified; do not infer local deposited quantity from uncalibrated brightness'}
    return material,alternate,refs,report


def export(output:Path,p=Parameters()):
    original,alternate,refs,r=instrumentation(p)
    if r['collision_blockers']:raise ValueError('RR collision gate: '+str(r['collision_blockers']))
    output.mkdir(parents=True,exist_ok=True)
    parts={**original,**alternate}
    r['components']=[]
    for name,s in parts.items():
        f=output/(name+'.step');cq.exporters.export(s,str(f))
        imported=cq.importers.importStep(str(f)).val();positive(imported,name)
        delta=abs(imported.Volume()-s.Volume())
        if delta>2e-4:raise ValueError('STEP drift: '+name)
        r['components'].append({'id':name,'classification':'MANUFACTURED_BENCH_CANDIDATE',
            'fusion_class':'A_ANALYTIC_NATIVE_REBUILD','source_sha256':r['source_sha256'],
            'local_frame':'COUPON_CROWN_ORIGIN_Z_OUTWARD_Y_CYLINDER_AXIS',
            'world_transform':[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]],
            'parent':'MASCK_RR_OFF_FACE','step_volume_delta_mm3':delta,
            'parameters':r['parameters'],'material':'UNQUALIFIED_INERT_BENCH_MATERIAL'})
    for sid,transforms in r['states'].items():
        a=cq.Assembly(name='MASCK_RR_'+sid)
        for name,s in alternate.items():a.add(s,name=name,loc=cq.Location(cq.Vector(*transforms.get(name,(0,0,0)))))
        a.save(str(output/(sid+'.step')))
    cq.exporters.export(cq.Compound.makeCompound(list(refs.values())),str(output/'REFERENCE_ONLY.step'))
    r['step_sha256']={f.name:sha256(f.read_bytes()).hexdigest() for f in output.glob('*.step')}
    (output/'fusion_rr_handoff.json').write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
    for rr in STAGES:
        run=template(rr);run['geometry_revision']=r['source_sha256'];run['coupon_radius_mm']=p.coupon_radius_mm
        (output/(rr+'_run.json')).write_text(json.dumps(run,indent=2)+'\n')
    return r


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path)
    parser.add_argument('--radius',type=float,default=80)
    args=parser.parse_args();r=export(args.output,Parameters(coupon_radius_mm=args.radius))
    print(json.dumps({'components':len(r['components']),'collision_blockers':r['collision_blockers'],'physical_result':None}))
