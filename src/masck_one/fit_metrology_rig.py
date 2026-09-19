"""Unpowered test equipment only. Never a wearable producer or human headform.

Digitally indexed pose cassettes replace an expensive six-axis stage. Two jaws
withdraw in the cassette's LOCAL X, leaving zero imposed pose constraints only
AFTER clamp withdrawal and independent clearance observation. Empty owner ports
are deliberately not populated with invented supports. Acquisition is therefore
blocked until a revision-bound coupon set exists.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
import argparse
import json
import math
import subprocess
import cadquery as cq
import numpy as np
from scipy.optimize import root
from .adversarial_fit_proof import (ROOT, Variation, warp, face, rotation, transform,
                                    source_snapshot, digest, nominal_landmarks)
from .authority import load_authority

REVISION = 'FIT_METROLOGY_RIG_1'
OUT = ROOT / 'generated/fit_metrology'
WITNESSES = ROOT / 'analysis/fit_proof/campaign_3ccd912/witnesses'
FIXTURE_LIMITS = {'xyz_each_mm': 10., 'rotation_each_deg': 6., 'jaw_withdrawal_mm': 55.}
# Fixture construction values, NOT product tolerances or human-use limits.
DIMENSIONS = {'base_mm':[580,400,10], 'surface_mm':[180,216],
              'surface_bottom_z_mm':-22., 'surface_flange_mm':[214,250,8],
              'host_outer_mm':[260,300], 'host_inner_mm':[230,270],
              'host_z_mm':[30,38], 'rod_diameter_mm':8., 'jaw_bore_mm':8.2,
              'mount_clearance_mm':5.5, 'index_pin_mm':4., 'index_bore_mm':4.2}


def box(x,y,z,c):
    return cq.Workplane('XY').box(x,y,z).val().translate(c)


def cylinder(r,h,p,axis=(0,0,1)):
    return cq.Solid.makeCylinder(r,h,cq.Vector(*p),cq.Vector(*axis))


def holes_z(shape, points, radius=2.75):
    for x,y in points: shape=shape.cut(cylinder(radius,260,(x,y,-120)))
    return shape


def placed(shape, pose):
    for axis,angle in zip(((1,0,0),(0,1,0),(0,0,1)),pose[3:]):
        shape=shape.rotate((0,0,0),axis,float(angle))
    return shape.translate(tuple(pose[:3]))


def matrix(pose):
    m=np.eye(4);m[:3,:3]=rotation(pose[3:]);m[:3,3]=pose[:3]
    return m.tolist()


def valid(shape):
    return shape.isValid() and len(shape.Solids())==1 and shape.Volume()>0


@dataclass
class Part:
    id: str
    shape: cq.Shape
    group: str
    material: str
    pose: tuple=(0,0,0,0,0,0)
    intent: str=''
    dimensions: dict|None=None

    @property
    def world(self): return placed(self.shape,self.pose)

    def manifest(self):
        if not valid(self.shape):raise ValueError('Invalid manufactured B-rep: '+self.id)
        return {'id':self.id,'name':self.id,'parent':self.group,
                'classification':'MANUFACTURED_TEST_EQUIPMENT',
                'material_role':self.material,'density_g_cm3':None,'mass_g':None,
                'volume_mm3':self.shape.Volume(),'local_frame':'PART_SOURCE_XYZ_MM',
                'world_transform':matrix(self.pose),'pose_extrinsic_xyz':list(self.pose),
                'intent':self.intent,'parameters':self.dimensions or {},
                'brep_valid':True,'solids':1,'fusion_class':'A_NATIVE_REBUILD_FROM_PARAMETERS',
                'moving_state':'LOCAL_X_WITHDRAWAL' if self.group=='JAWS' else 'RIGID',
                'service':'OFF_FACE_UNLOADED_FASTENER_REMOVAL'}


def sources():
    s=source_snapshot()
    return {'analyzed_main':s['main'],'snapshot_digest':digest(s),
            'source_files':s['consumed_files'],
            'fit_generator_sha256':sha256((ROOT/'src/masck_one/adversarial_fit_proof.py').read_bytes()).hexdigest(),
            'rig_generator_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
            'git_head_at_generation':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()}


def surface_specs():
    result={}
    for name,file in [('NOMINAL','nominal'),('FALSE_SURFACE','false_surface'),
                      ('ASYMMETRY','asymmetry'),('EYE_NEAREST_CANDIDATE','eye_spacing_candidate'),
                      ('EYE_NEAREST_NONPASSING','eye_spacing_failure')]:
        p=WITNESSES/(file+'.json'); w=json.loads(p.read_text())
        result[name]={'variation':Variation(**w['parameters']), 'witness_id':w['id'],
                      'witness_path':str(p.relative_to(ROOT)), 'witness_sha256':sha256(p.read_bytes()).hexdigest()}
    result['EYE_SPACING_HIGH']={'variation':Variation(eye_spacing=12),
        'witness_id':'eye_spacing_HIGH','witness_path':'analysis/fit_proof/campaign_3ccd912/case_set.json',
        'witness_sha256':sha256((WITNESSES.parent/'case_set.json').read_bytes()).hexdigest()}
    return result


def surface_part(name, variation, nx=31, ny=25):
    """Analytic-edge section loft, not tessellated mesh manufacturing geometry.

    Inverse XY warp retains the existing campaign's off-landmark Z field.
    The rectangular skirt is fixture convenience. Only the source target ellipse
    is a fit-reference domain. Sampled CAD approximation is separately reported.
    """
    a=load_authority(); wires=[]; samples=[]
    def height(x,y):
        sol=root(lambda uv:warp([[*uv,0]],variation,a)[0,:2]-[x,y],[x,y])
        if not sol.success or np.linalg.norm(sol.fun)>1e-7:raise ValueError('noninvertible surface')
        return float(warp([[*sol.x,0]],variation,a)[0,2])
    for y in np.linspace(-108,108,ny):
        pts=[cq.Vector(x,y,height(x,y)) for x in np.linspace(-90,90,nx)]
        c,d=cq.Vector(90,y,-22),cq.Vector(-90,y,-22)
        wires.append(cq.Wire.assembleEdges([cq.Edge.makeSpline(pts),cq.Edge.makeLine(pts[-1],c),
                                           cq.Edge.makeLine(c,d),cq.Edge.makeLine(d,pts[0])]))
    loft=cq.Solid.makeLoft(wires)
    top=max(loft.Faces(),key=lambda f:f.Center().z)
    # Deterministic off-grid metrology checkpoints. Not a global error bound.
    for y in np.linspace(-99,99,12):
        for x in np.linspace(-75,75,14):
            if (x/77.5)**2+(y/101)**2<=1:
                z=height(x,y)
                samples.append(cq.Vertex.makeVertex(x,y,z).distance(top))
    flange=holes_z(box(214,250,8,(0,0,-24)),[(-99,-115),(99,-115),(-99,115),(99,115)])
    # Round + relieved second pin, no four-pin overconstraint.
    flange=flange.cut(cylinder(2.1,20,(-99,0,-35)))
    slot=box(4.2,7,20,(99,0,-25)).fuse(cylinder(2.1,20,(99,-3.5,-35)),cylinder(2.1,20,(99,3.5,-35)))
    flange=flange.cut(slot)
    solid=loft.fuse(flange).clean()
    marks={name:point.tolist() for name,point in zip(nominal_landmarks(a),warp(list(nominal_landmarks(a).values()),variation,a))}
    # Actual machined/printed marks distinguish planar XY-variation witnesses.
    # These protected-center metrology dimples are not treatment or anatomy.
    for x,y,z in marks.values():solid=solid.cut(cylinder(.75,.5,(x,y,z-.4)))
    meta=face(variation)
    meta['fiducial_dimples_xyz']=marks
    meta['fiducial_diameter_mm']=1.5
    meta['fiducial_depth_mm']=.4
    meta['dimple_domains_excluded_from_surface_error']=list(marks)

    meta.update({'label':'SYNTHETIC_ADVERSARIAL_BENCH_REFERENCE_NOT_HUMAN',
                 'topology':'closed section loft + integral locating flange',
                 'section_y_mm':np.linspace(-108,108,ny).tolist(),
                 'top_profile_x_mm':np.linspace(-90,90,nx).tolist(),
                 'bottom_z_mm':-22,'sampled_approximation_max_mm':max(samples),
                 'sampled_approximation_count':len(samples),'global_approximation_bound_mm':None,
                 'full_field_as_built_scan_required':True,
                 'protected_surrogates':'registered optical overlays only; no anatomical cavities fabricated'})
    return Part('SURFACE_'+name,solid,'INTERCHANGEABLE_SURFACES','rigid dimensionally stable bench polymer; qualify as-built',
                intent='mill or print; scan installed top and datum flange before testing',dimensions=meta)


def jaw_primitives(side):
    x=side*146
    q=[([16,348,14],[x,0,-12]),([16,280,14],[x,0,22])]
    q += [([16,16,60],[x,y,11]) for y in (-145,145)]
    q += [([32,12,8],[side*134,y,26]) for y in ((-138,138) if side==-1 else (0,))]
    if side==-1:q.append(([18,16,10],[-139,0,33]))
    else:q.append(([16,16,18],[146,0,29]))  # lateral clamp boss, clear of article
    q.append(([32,8,12],[side*134,-154,34]))
    q += [([38,18,8],[side*133,y,45]) for y in (-138,138)]
    # Positive-Y preload screw support; Y=-150 remains the only rigid Y datum.
    if side==1:q.append(([32,8,18],[134,154,32]))
    return q


def build(pose=(0,0,0,0,0,0)):
    pose=tuple(float(x) for x in pose)
    if len(pose)!=6 or any(not math.isfinite(x) for x in pose):raise ValueError('six finite coordinates')
    if any(abs(x)>10 for x in pose[:3]) or any(abs(x)>6 for x in pose[3:]):
        raise ValueError('outside FIXTURE convenience range, not a product limit')
    parts=[]
    def add(id,s,g='BASE',mat='rigid fixture stock; stiffness to be measured',intent='',dims=None,p=(0,0,0,0,0,0)):
        part=Part(id,s,g,mat,p,intent,dims);parts.append(part);return part
    mount=[(x,y) for x in (-240,240) for y in (-165,165)]
    grid=[(x,y) for x in range(-250,251,50) for y in (-190,190)]
    base=holes_z(box(580,400,10,(0,0,-105)),mount+grid+[(-270,0),(270,0)])
    base=holes_z(base,[(-99,-115),(99,-115),(-99,115),(99,115)])
    add('BASE',base,intent='datum A top Z=-100; fixture mounting and instrument grid M5 clearance',dims=DIMENSIONS)
    # Central carrier elevates the synthetic surface; four external clamping towers.
    support=box(214,250,12,(0,0,-34)).cut(box(172,210,16,(0,0,-34)))
    support=holes_z(support,[(-99,-115),(99,-115),(-99,115),(99,115)])
    add('SURFACE_CARRIER',support,intent='A top Z=-28; B round pin (-99,0); C relieved pin (+99,0)')
    for x,y in [(-99,-115),(99,-115),(-99,115),(99,115)]:
        add(f'SURFACE_POST_{x}_{y}',holes_z(box(16,16,60,(x,y,-70)),[(x,y)]),intent='M5 through bolt from base into top nut; no adhesive')
    for x in (-99,99):
        # Shouldered locator: 4 mm locating portion, 6 mm seat, screw retention.
        p=cylinder(3,12,(x,0,-40)).fuse(cylinder(2,7,(x,0,-28)),box(20,10,2,(x,0,-41)))
        p=holes_z(p,[(x-7,0),(x+7,0)],1.7)
        parts[1].shape=parts[1].shape.cut(cylinder(3.05,12,(x,0,-40)))
        for xx in (x-7,x+7):parts[1].shape=parts[1].shape.cut(cylinder(1.25,9,(xx,0,-40)))
        add(f'SURFACE_PIN_{x}',p,mat='small metal locator; as-built calibration required',
            intent='integral underside flange, two M3 retained screws into carrier; 4 mm locating tip',
            dims={'retention':'two M3 screws; 2.5 mm tapping pilots in carrier'})
    # Two rods and four pose-indexed pedestals. Rods are cut-to-length hardware.
    for y in (-165,165):
        add(f'ROD_{y}',cylinder(4,500,(-250,y,-12),(1,0,0)),g='POSE_CASSETTE',
            mat='ground rod stock; straightness unqualified',intent='8 mm diameter x 500; captured split end blocks',p=pose)
        for x in (-240,240):
            block=box(24,24,32,(x,y,-12)).cut(cylinder(4.05,40,(x-20,y,-12),(1,0,0)))
            # Split below rod for bolted clamp; M4 clamp pilot (thread callout in manifest).
            block=block.cut(box(26,1,16,(x,y,-20)))
            block=block.cut(cylinder(1.65,30,(x,y-15,-22),(0,1,0)))
            add(f'ROD_CLAMP_{x}_{y}',block,g='POSE_CASSETTE',intent='M4 clamp screw across slit; two M5 mounting bores',p=pose)
            parts[-1].shape=holes_z(parts[-1].shape,[(x-7,y+7),(x+7,y+7)],2.75)
            # Ruled pedestal connects fixed base footprint to transformed cassette underside.
            lower=cq.Workplane('XY').workplane(offset=-100).center(x,y).rect(34,34).val()
            upper=placed(cq.Workplane('XY').workplane(offset=-28).center(x,y).rect(24,24).val(),pose)
            leg=cq.Solid.makeLoft([lower,upper],ruled=True)
            leg=leg.cut(cylinder(2.1,22,(x,y,-101)))
            # Top fastener pilot axes rotate WITH cassette.
            for xx in (x-7,x+7):leg=leg.cut(placed(cylinder(2.1,24,(xx,y+7,-48)),pose))
            add(f'INDEXED_LEG_{x}_{y}',leg,g='POSE_CASSETTE',intent='pose-specific rigid loft; M5 tapped blind base socket, two M5 top pilot bores',dims={'pose':list(pose),'fixture_convenience':True})
    # Host is test equipment with empty coupon ports, never a wearable substitute.
    host=box(260,300,8,(0,0,34)).cut(box(230,270,12,(0,0,34)))
    ports=[(s*122,y) for s in (-1,1) for y in (-90,-30,30,90)]
    host=holes_z(host,[(x,y+d) for x,y in ports for d in (-4,4)],1.7)
    add('COUPON_HOST',host,g='TEST_ARTICLE',intent='eight EMPTY two-M3 ports; owner adapter required; no implied contact or passive support',p=pose,
        dims={'ports_xyz':[[x,y,30] for x,y in ports],'coupon_state':'EMPTY_UNKNOWN','source_owner_geometry':None})
    # Rail jaws carry 3 Z contacts, 2 Y contacts, 1 X datum. Clamps are independent.
    for side in (-1,1):
        x=side*146
        primitives=jaw_primitives(side)
        spine=box(*primitives[0][0],primitives[0][1])
        for dims,center in primitives[1:]:spine=spine.fuse(box(*dims,center))
        for y in (-138,138):spine=spine.cut(cylinder(1.65,30,(side*124,y,28)))
        if side==1:
            spine=spine.cut(cylinder(1.65,30,(132,0,34),(1,0,0)))
            spine=spine.cut(cylinder(1.65,30,(124,140,34),(0,1,0)))
        for y in (-165,165):spine=spine.cut(cylinder(4.1,40,(x-20,y,-12),(1,0,0)))
        # Manual travel handle through hole away from article.
        spine=spine.cut(cylinder(3,30,(x,0,-28)))
        add('JAW_LEFT' if side==-1 else 'JAW_RIGHT',spine.clean(),g='JAWS',mat='rigid low-friction fixture polymer or lined rigid stock; measure drag',
            intent='slide 55 mm out along LOCAL X after clamp retreat; rod friction never used as capture evidence',p=pose,
            dims={'travel_mm':55,'direction_local':[side,0,0],'guide_diameter_mm':8.2,'guide_separation_mm':330,'box_primitives':primitives})
    # Inner and outer collars encode each jaw endpoint on both guide rods.
    for side in (-1,1):
        for y in (-165,165):
            for x in (side*132,side*215):
                c=cylinder(8,12,(x-6,y,-12),(1,0,0)).cut(cylinder(4.05,14,(x-7,y,-12),(1,0,0)))
                c=c.cut(cylinder(1.25,12,(x,y,-12),(0,0,1)))
                add(f'ROD_STOP_{x}_{y}',c,g='POSE_CASSETTE',intent='M3 radial set screw; calibrate endpoint before each cassette use',p=pose)
    # Non-contact metrology targets, three non-collinear centers in host frame.
    for i,(x,y,z) in enumerate([(-122,110,46),(122,110,46),(0,-142,46)]):
        pad=box(10,10,8,(x,y,z-4));pad=holes_z(pad,[(x,y)],1.7)
        add(f'HOST_TARGET_{i}',pad,g='TEST_ARTICLE',intent='M3 attachment; 10 mm square optical target face, no assumed tracker',p=pose)
        parts[[p.id for p in parts].index('COUPON_HOST')].shape=holes_z(parts[[p.id for p in parts].index('COUPON_HOST')].shape,[(x,y)],1.7)
    # Independent instrument uprights on base grid. 5 mm mounting slots.
    for x in (-270,270):
        bracket=box(24,24,8,(x,0,-96)).fuse(box(12,20,170,(x,0,-7)))
        bracket=holes_z(bracket,[(x,0)],2.75)
        for z in (-40,0,40,65):bracket=bracket.cut(cylinder(2.75,30,(x-15,0,z),(1,0,0)))
        add(f'PROBE_POST_{x}',bracket,g='METROLOGY',intent='M5 instrument interface; optional cameras/probes; no imposed host contact')
    # Calibration insert bolts to same carrier, replacing synthetic surface.
    cal=holes_z(box(214,250,8,(0,0,-24)),[(-99,-115),(99,-115),(-99,115),(99,115)])
    cal=cal.cut(cylinder(2.1,20,(-99,0,-35))).cut(box(4.2,11.2,20,(99,0,-25)))
    for x,y,z in [(-55,35,0),(55,35,0),(0,-55,10),(-44,0,5),(44,0,15)]:
        cal=cal.fuse(box(20,20,z+20,(x,y,(z-20)/2)))
    calibration=Part('CALIBRATION_INSERT',cal.clean(),'CALIBRATION','rigid metrology stock; as-built dimensions must be calibrated',
                     intent='five planar 20 mm targets at known CAD heights; artifact truth requires independent measurement',
                     dimensions={'target_centers_xyz':[[-55,35,0],[55,35,0],[0,-55,10],[-44,0,5],[44,0,15]]})
    return parts,calibration


def jaw_continuous_clearance(parts):
    """Conservative continuous interval proof against unchanged rigid host.

    Each pre-Boolean box primitive translates by its exact Minkowski interval.
    Filled screw and rod bores are conservative. Sweeps are reference-only.
    No sampled-pose sweep claim.
    """
    host=next(p for p in parts if p.id=='COUPON_HOST').shape
    results={}; refs={}
    for p in parts:
        if p.group!='JAWS':continue
        side=p.dimensions['direction_local'][0];refs[p.id]=[];total=0.
        for dimensions,center in p.dimensions['box_primitives']:
            dims=list(dimensions);c=list(center);dims[0]+=55;c[0]+=side*27.5
            sweep=box(*dims,c)  # exact continuous box translation, holes conservatively filled
            total+=sum(x.Volume() for x in sweep.intersect(host).Solids())
            refs[p.id].append(placed(sweep,p.pose))
        end=p.shape.translate((side*55,0,0))
        results[p.id]={'continuous_conservative_overlap_mm3':total,
            'status':'CONTINUOUS_REFERENCE_CLEAR' if total<1e-7 else 'CONSERVATIVE_OVERLAP_REQUIRES_REFINEMENT',
            'end_clearance_mm':end.distance(host),'stroke_mm':55,
            'clamp_screws':'MUST_BE_MEASURED_RETRACTED; not silently included in jaw proof'}
    return results,refs


def export(output=OUT,pose=(0,0,0,0,0,0),surfaces=True):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    parts,cal=build(pose);src=sources(); entries=[];assembly=cq.Assembly(name='OFF_FACE_FIT_METROLOGY')
    for p in parts:
        row=p.manifest(); path=output/(p.id+'.step');cq.exporters.export(p.shape,str(path))
        row['local_step']=path.name;row['step_sha256']=sha256(path.read_bytes()).hexdigest();entries.append(row)
        assembly.add(p.world,name=p.id)
    assembly.save(str(output/'ASSEMBLY_IMPOSED.step'))
    cq.exporters.export(cal.shape,str(output/'CALIBRATION_INSERT.step'));entries.append(cal.manifest())
    acquisition=cq.Assembly(name='ACQUISITION_JAWS_WITHDRAWN')
    for p in parts:
        s=p.shape.translate((p.dimensions['direction_local'][0]*55,0,0)) if p.group=='JAWS' else p.shape
        acquisition.add(placed(s,p.pose),name=p.id)
    acquisition.save(str(output/'ASSEMBLY_DISENGAGED.step'))
    clearance,refs=jaw_continuous_clearance(parts)
    cq.exporters.export(cq.Compound.makeCompound([s for ss in refs.values() for s in ss]),str(output/'REFERENCE_ONLY_WITHDRAWAL.step'))
    if surfaces:
        for name,spec in surface_specs().items():
            p=surface_part(name,spec['variation']);row=p.manifest();row['source_witness']={k:v for k,v in spec.items() if k!='variation'}
            cq.exporters.export(p.shape,str(output/(p.id+'.step')));entries.append(row)
            if name=='NOMINAL':
                assembly.add(p.world,name=p.id);acquisition.add(p.world,name=p.id)
    assembly.save(str(output/'ASSEMBLY_IMPOSED.step'))
    acquisition.save(str(output/'ASSEMBLY_DISENGAGED.step'))
    calibration_assembly=cq.Assembly(name='CALIBRATION_INSTALLED')
    for p in parts:calibration_assembly.add(p.world,name=p.id)
    calibration_assembly.add(cal.world,name=cal.id)
    calibration_assembly.save(str(output/'ASSEMBLY_CALIBRATION.step'))
    manifest={'revision':REVISION,'source':src,'coordinate_frame':'MASCK_AUTHORITY_X_RIGHT_Y_SUPERIOR_Z_ANTERIOR_MM; BENCH_Z_UP',
              'dimension_origin':'ALL FIXTURE_CONVENIENCE except source synthetic field and authority frame',
              'fixture_limits_not_product_limits':FIXTURE_LIMITS,'parts':entries,
              'continuous_withdrawal':clearance,'physical_result':None,
              'owner_coupon_status':'EMPTY_UNKNOWN; acquisition cannot establish product capture',
              'acquisition_requires':['all clamp screws retracted','both jaws at outward endpoints','independent pose trajectory',
                  'all candidate reaction supplied by identified coupons','no fixture/catcher contact'],
              'remaining_stage_constraints_after_verified_release':[],
              'imposed_datums':{'Z':[[-124,-138,30],[-124,138,30],[124,0,30]],
                                'Y':[[-124,-150,34],[124,-150,34]],'X':[[-130,0,34]]},
              'missing_production_inputs':['owner support/seal profiles','owner coupon transforms and allowed travel','passive mechanical properties'],
              'hardware_specs':[{'item':'M5 mounting bolts/nuts','interfaces':'5.5 mm clearance, 4.2 mm tapping pilots; select length from stack'},
                                {'item':'M4 retractable clamp screws','interfaces':'3.3 mm tapping pilots; ends clear Z=41 before release'},
                                {'item':'8 mm rods','interfaces':'500 mm length; 8.1 clamp bores, 8.2 jaw guides'}],
              'files':{p.name:sha256(p.read_bytes()).hexdigest() for p in output.glob('*.step')}}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    return manifest


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=OUT);p.add_argument('--pose',type=float,nargs=6,default=[0]*6)
    p.add_argument('--no-surfaces',action='store_true');args=p.parse_args()
    r=export(args.out,args.pose,not args.no_surfaces);print(json.dumps({'parts':len(r['parts']),'withdrawal':r['continuous_withdrawal']}))


if __name__=='__main__':main()
