"""CS-018 unpowered, off-face contact-transition geometry.

Selected reduced-region experiment: external reaction, lift the dirty cassette,
interpose a catch shutter, then traverse a separate clean delivery head below it.
No wearable fit, human use, application performance or SPF claim is authorized.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from hashlib import sha256
import json
from pathlib import Path
import cadquery as cq
from . import _contracts


class FacialInterfaceError(ValueError):
    pass


@dataclass(frozen=True)
class Parameters:
    coupon_radius_mm: float = 80.0
    normal_lift_mm: float = 14.0
    shutter_travel_mm: float = 52.0
    delivery_half_travel_mm: float = 17.0
    film_reference_mm: float = 0.2
    guide_radial_clearance_mm: float = 0.15
    shutter_vertical_clearance_mm: float = 0.2

    def __post_init__(self):
        for k,v in asdict(self).items():
            _contracts.positive(v,k,FacialInterfaceError)
        if self.coupon_radius_mm < 60 or self.coupon_radius_mm > 120:
            raise FacialInterfaceError('coupon DOE radius outside the modeled fixture family')
        if not 14 <= self.normal_lift_mm <= 18:
            raise FacialInterfaceError('lift must clear the catch shutter and remain within guide stroke')
        if self.shutter_travel_mm < 48:
            raise FacialInterfaceError('dirty-cassette acquisition must have a clear shutter park')
        if not 15.5 <= self.delivery_half_travel_mm <= 18:
            raise FacialInterfaceError('delivery scan must cover the coupon and avoid frame uprights')
        if self.film_reference_mm >= 1:
            raise FacialInterfaceError('film reference is a collision study, not a product dose')
        if self.guide_radial_clearance_mm >= .3 or self.shutter_vertical_clearance_mm >= .4:
            raise FacialInterfaceError('guide DOE outside bounded nominal construction')


def box(x,y,z,c):
    return cq.Workplane('XY').box(x,y,z).translate(c).val()


def cylinder(radius,height,origin,direction=(0,0,1)):
    return cq.Solid.makeCylinder(radius,height,cq.Vector(*origin),cq.Vector(*direction))


def positive(s,name):
    if not s.isValid() or len(s.Solids()) != 1 or s.Volume() <= 0:
        raise FacialInterfaceError(name + ': requires one valid positive B-rep')
    return s


def common_volume(a,b):
    value=0.0
    for x in a.Solids():
        for y in b.Solids():
            q=x.intersect(y)
            if not q.isValid():
                raise FacialInterfaceError('invalid intersection is not clearance evidence')
            value += sum(s.Volume() for s in q.Solids())
    return _contracts.non_negative(value,'common volume',FacialInterfaceError)


def translation_bound(s,vector):
    """Exact union bound of a source bounding box along one pure translation.

    Conservative continuous prism, never sampled poses. Kept as REFERENCE.
    It can reject a valid motion conservatively; it cannot hide a collision.
    """
    if sum(v != 0 for v in vector) != 1:
        raise FacialInterfaceError('one-axis translation required')
    for v in vector:_contracts.finite(v,'translation',FacialInterfaceError)
    b=s.BoundingBox()
    lo=[b.xmin,b.ymin,b.zmin];hi=[b.xmax,b.ymax,b.zmax]
    for i,v in enumerate(vector):lo[i]+=min(0,v);hi[i]+=max(0,v)
    return box(*(hi[i]-lo[i] for i in range(3)),tuple((hi[i]+lo[i])/2 for i in range(3)))


def build(p=Parameters()):
    R=p.coupon_radius_mm
    target_cylinder=cylinder(R,80,(0,-40,-R),(0,1,0))
    # Removable inert coupon: curved analytic top, flat datum flange, four bores.
    coupon=target_cylinder.intersect(box(32,44,4.2,(0,0,-1.9)))
    coupon=coupon.fuse(box(44,56,2.2,(0,0,-5.0))).clean()
    for x in (-19,19):
        for y in (-25,25):coupon=coupon.cut(cylinder(1.6,4,(x,y,-7)))
    coupon=positive(coupon.clean(),'curved coupon')
    # Externally supported fixture; it deliberately does not prove a wearable
    # cranial reaction path. Bore interfaces, not overlapping compounds, locate it.
    base=box(116,140,4,(12,20,-8.1))
    for x in (-19,19):
        for y in (-25,25):base=base.cut(cylinder(1.25,4,(x,y,-10.1)))
    for x in (-32,32):
        base=base.fuse(box(10,12,5,(x,0,-3.7)))
        base=base.cut(cylinder(3,12,(x,0,-10.1)))
    # Separate master and relieved posts; guide pair constrains rotation.
    posts={f'normal_guide_{side}':cylinder(3,50,(x,0,-10.1)) for side,x in [('left',-32),('right',32)]}
    clean_shell=cylinder(R+1.2,44,(0,-22,-R),(0,1,0)).cut(target_cylinder)
    clean_shell=clean_shell.intersect(box(36,44,6,(0,0,0)))
    ring=clean_shell.cut(box(24,32,12,(0,0,1)))
    pad=clean_shell.intersect(box(10,10,12,(0,0,1)))
    clean=ring.fuse(pad)
    # All ring/island connections are integral material above the coupon.
    for x in (-15,0,15):clean=clean.fuse(box(4,6,22,(x,0,9)))
    clean=clean.fuse(box(70,8,4,(0,0,20)))
    clean=clean.cut(target_cylinder)
    for x in (-32,32):
        hole=cylinder(3+p.guide_radial_clearance_mm,45,(x,0,-4))
        if x>0:hole=hole.fuse(hole.translate((.6,0,0)))
        clean=clean.cut(hole)
    clean=positive(clean.clean(),'dirty contact cassette')
    parking_pins={}
    for side,x in [('left',-32),('right',32)]:
        clean=clean.cut(cylinder(1.35,14,(x,-7,20),(0,1,0)))
        posts['normal_guide_'+side]=posts['normal_guide_'+side].cut(
            cylinder(1.35,14,(x,-7,20+p.normal_lift_mm),(0,1,0)))
        pin=cylinder(1.25,12,(x,-6,20+p.normal_lift_mm),(0,1,0))
        pin=pin.fuse(cylinder(2,1.2,(x,-7,20+p.normal_lift_mm),(0,1,0)))
        parking_pins['parking_pin_'+side]=positive(pin.clean(),'lift parking pin')
    # Catch shutter is a single shallow tray. It enters only AFTER full lift.
    # The bottom is continuous, with raised perimeter; no drain above the coupon.
    tray=box(44,48,.6,(0,0,9.3))
    tray=tray.fuse(box(44,48,1.6,(0,0,10.1)).cut(box(41.6,45.6,3,(0,0,10.1))))
    # Lateral tongues run in matching external C-slots outside the coupon.
    for y in (-25,25):tray=tray.fuse(box(44,3,.6,(0,y,9.3)))
    tray=positive(tray.clean(),'catch shutter')
    rails={}
    for y in (-25,25):
        rail=box(p.shutter_travel_mm+100,6,2.8,(p.shutter_travel_mm/2,y,9.8))
        slot=box(p.shutter_travel_mm+102,3.4,.6+2*p.shutter_vertical_clearance_mm,(p.shutter_travel_mm/2,y,9.3))
        # Slot opens inward so the tray and tongue are one manufacturable part.
        slot=slot.fuse(box(p.shutter_travel_mm+102,3,2.8,(p.shutter_travel_mm/2,y+(-2 if y>0 else 2),9.6)))
        rail=rail.cut(slot)
        for x in (-44,64):
            rail=rail.fuse(box(5,6,14.7,(x,y,1.25)))
        rails[f'shutter_guide_{"left" if y<0 else "right"}']=positive(rail.clean(),'shutter guide')
    tray=tray.rotate((0,0,0),(0,0,1),90)
    rails={k:v.rotate((0,0,0),(0,0,1),90) for k,v in rails.items()}
    # Separate clean applicator has an open, inspectable gallery and long slot.
    # No flow, compatibility or film claim follows from this passage geometry.
    head=box(6,72,3,(0,0,5.5))
    for y in (-34,34):head=head.fuse(box(10,6,5,(0,y,5.5)))
    # Four addressable rows, each with independent water, cleanser and return
    # passages. No shared gallery can spread a command to an exhausted row.
    passages={}
    for row,y in enumerate((-15,-5,5,15)):
        for fluid,x in [('FRESH_WATER',-2),('CLEANSER',0),('MIXED_WASTE',2)]:
            passage=box(.8,8,3,(x,y,5.5))
            head=head.cut(passage)
            passages[f'ROW_{row}_{fluid}']=passage

    for y in (-34,34):head=head.cut(cylinder(1.5+p.guide_radial_clearance_mm,10,(-5,y,5.5),(1,0,0)))
    head=positive(head.clean(),'independent applicator')
    cap=box(6,44,.8,(0,0,7.4))
    for y in (-15,-5,5,15):
        for x in (-2,0,2):cap=cap.cut(cylinder(.4,3,(x,y,6)))

    # Two alignment bores and continuous mating lands, separate lid and body.
    for y in (-21,21):
        hole=cylinder(.6,4,(0,y,4))
        head=head.cut(hole);cap=cap.cut(hole)
    delivery_rails={f'delivery_guide_{tag}':cylinder(1.5,84,(-42,y,5.5),(1,0,0)) for tag,y in [('left',-34),('right',34)]}
    # Fixed support towers meet rail ends through radial bores.
    for y in (-34,34):
        for x in (-41,41):
            tower=box(4,6,16,(x,y,-.1)).cut(cylinder(1.5,8,(x-4,y,5.5),(1,0,0)))
            base=base.fuse(tower)
    base=positive(base.clean(),'external reaction base')
    material={'coupon':coupon,'reaction_base':base,'clean_cassette':clean,'catch_shutter':tray,
        'delivery_body':positive(head.clean(),'delivery body'),'delivery_lid':positive(cap.clean(),'delivery lid'),**posts,**rails,**delivery_rails,**parking_pins}
    # Every coupon datum and grip stays outside the required observation domain.
    film=cylinder(R+p.film_reference_mm,40,(0,-20,-R),(0,1,0)).cut(target_cylinder)
    film=positive(film.intersect(box(30,40,5,(0,0,0))),'film reference')
    cells={}
    for i in range(3):
        for j in range(4):
            cells[f'CHEEK_COUPON_X{i}_Y{j}']=positive(film.intersect(box(10,10,8,(-10+i*10,-15+j*10,0))),'cell')
    # Conservative continuous lift envelope, cut below the fixed convex coupon
    # top. For +Z motion of this upward-closed head, the removed cylinder is
    # outside the head for the ENTIRE path, not just sampled poses.
    lift=box(36,44,26+p.normal_lift_mm,(0,0,9+p.normal_lift_mm/2))
    lift=lift.fuse(box(70,8,4+p.normal_lift_mm,(0,0,20+p.normal_lift_mm/2))).cut(target_cylinder)
    for x in (-32,32):
        hole=cylinder(3+p.guide_radial_clearance_mm,70,(x,0,-10))
        if x>0:hole=hole.fuse(hole.translate((.6,0,0)))
        lift=lift.cut(hole)
    lift=positive(lift.clean(),'continuous normal lift reference')
    travel=25+p.delivery_half_travel_mm
    mid=(-25+p.delivery_half_travel_mm)/2
    scan=box(6+travel,72,3,(mid,0,5.5)).fuse(box(6+travel,44,.8,(mid,0,7.4)))
    for y in (-34,34):scan=scan.fuse(box(10+travel,6,5,(mid,y,5.5)))
    # Remove the two continuous guide bores from its conservative motion bound.
    for y in (-34,34):scan=scan.cut(cylinder(1.5+p.guide_radial_clearance_mm,90,(-45,y,5.5),(1,0,0)))
    shutter=translation_bound(tray,(0,p.shutter_travel_mm,0))
    refs={'FILM':film,'NORMAL_LIFT':lift,'DELIVERY_SCAN':scan,'SHUTTER_TRANSLATION':shutter,
        'DELIVERY_ACCESS':box(2*p.delivery_half_travel_mm+1,40,8,(0,0,0)),**cells,
        **{'FLUID_PASSAGE_'+k:v for k,v in passages.items()}}
    service=box(36,44,76,(0,0,34+p.normal_lift_mm))
    service=service.fuse(box(70,8,54,(0,0,45+p.normal_lift_mm)))
    service=service.cut(target_cylinder.translate((0,0,p.normal_lift_mm)))
    for x in (-32,32):
        hole=cylinder(3+p.guide_radial_clearance_mm,120,(x,0,-10))
        if x>0:hole=hole.fuse(hole.translate((.6,0,0)))
        service=service.cut(hole)
    refs['NORMAL_CASSETTE_SERVICE']=positive(service.clean(),'cassette withdrawal reference')
    states={
        'CONTACT':{'clean_cassette':(0,0,0),'catch_shutter':(0,p.shutter_travel_mm,0),'delivery_body':(-25,0,0),'delivery_lid':(-25,0,0)},
        'LIFTED':{'clean_cassette':(0,0,p.normal_lift_mm),'catch_shutter':(0,p.shutter_travel_mm,0),'delivery_body':(-25,0,0),'delivery_lid':(-25,0,0)},
        'ISOLATED':{'clean_cassette':(0,0,p.normal_lift_mm),'catch_shutter':(0,0,0),'delivery_body':(-25,0,0),'delivery_lid':(-25,0,0)},
    }
    for state in ('CONTACT','LIFTED'):
        for key in parking_pins:states[state][key]=(0,-20,0)
    states['SERVICE']=dict(states['ISOLATED'])
    states['SERVICE']['clean_cassette']=(0,0,p.normal_lift_mm+50)
    for key in parking_pins:states['SERVICE'][key]=(0,-20,0)
    # The scan is enabled only after dirty-contact isolation; finished film is
    # separated from all fixed/departing functional parts by positive standoff.
    checks={}
    clean_lifted=clean.translate((0,0,p.normal_lift_mm))
    for side,x in [('left',-32),('right',32)]:
        pin_sweep=cylinder(1.25,32,(x,-26,20+p.normal_lift_mm),(0,1,0))
        pin_sweep=pin_sweep.fuse(cylinder(2,21.2,(x,-27,20+p.normal_lift_mm),(0,1,0)))
        refs['PARKING_PIN_'+side]=pin_sweep
        checks['parking_pin/'+side+'/head']=common_volume(pin_sweep,clean_lifted)
        checks['parking_pin/'+side+'/post']=common_volume(pin_sweep,posts['normal_guide_'+side])
    for name, obstacle in {'coupon':coupon,**posts,**delivery_rails,**rails}.items():
        checks['lift/'+name]=common_volume(lift,obstacle)
    for name, obstacle in {'film':film,'shutter':tray,**posts,**delivery_rails,**rails}.items():
        checks['service/'+name]=common_volume(service,obstacle)
    for name, obstacle in {'body':head.translate((-25,0,0)),'lid':cap.translate((-25,0,0))}.items():
        checks['lift/parked_'+name]=common_volume(lift,obstacle)
        checks['service/parked_'+name]=common_volume(service,obstacle)
    for name, obstacle in posts.items():checks['shutter/'+name]=common_volume(shutter,obstacle)
    checks['shutter/lifted_dirty_cassette']=common_volume(shutter,clean_lifted)
    checks['shutter/film']=common_volume(shutter,film)
    checks['scan/lifted_dirty_cassette']=common_volume(scan,clean_lifted)
    checks['scan/catch_shutter']=common_volume(scan,tray)
    checks['scan/film']=common_volume(scan,film)
    for name,obstacle in {**posts,**delivery_rails,**rails}.items():checks['scan/'+name]=common_volume(scan,obstacle)
    # Lateral C-guide slot geometry is checked against the moving tray itself;
    # its full bounding box includes empty interior below the side tongues.
    for name,rail in rails.items():
        # Exact box extrusion of the planar tray section along X, preserving YZ voids.
        swept=box(44+p.shutter_travel_mm,48,.6,(p.shutter_travel_mm/2,0,9.3))
        for y in (-23.4,23.4):swept=swept.fuse(box(44+p.shutter_travel_mm,1.2,1.6,(p.shutter_travel_mm/2,y,10.1)))
        for y in (-25,25):swept=swept.fuse(box(44+p.shutter_travel_mm,3,.6,(p.shutter_travel_mm/2,y,9.3)))
        swept=swept.fuse(box(44+p.shutter_travel_mm,48,1.6,(p.shutter_travel_mm/2,0,10.1)))
        # Over-conservative filled tray interior is safe for the guides outside Y24.
        swept=swept.rotate((0,0,0),(0,0,1),90)
        checks['shutter/'+name]=common_volume(swept,rail)
    access={key:common_volume(cell,refs['DELIVERY_ACCESS'])/cell.Volume() for key,cell in cells.items()}
    for state,transforms in states.items():
        entries=list(material.items())
        for i,(a,s) in enumerate(entries):
            for b,t in entries[i+1:]:
                checks[state+'/'+a+'/'+b]=common_volume(s.translate(transforms.get(a,(0,0,0))),t.translate(transforms.get(b,(0,0,0))))
    unresolved=[k for k,v in checks.items() if v>1e-7]
    return material,refs,{'schema':'MASCK_CS018_OFF_FACE_BENCH','parameters':asdict(p),'states':states,
        'fluid_interfaces':{key:{'fluid':key.split('_',2)[2], 'row':int(key.split('_')[1]),
            'separate_passage_volume_mm3':shape.Volume(),'port_diameter_mm':.8,
            'external_isolation':'REQUIRED_OFF_FACE_BENCH_SELECTOR_NOT_IMPLEMENTED_ON_WEARABLE',
            'hydraulic_validation':'UNKNOWN','passive_backflow_owner':'UNCHANGED_EXISTING_MIXED_WASTE_OWNER'} for key,shape in passages.items()},
        'collision_volumes_mm3':checks,'collision_blockers':unresolved,'cell_access_fractions':access,
        'whole_face_complete':False,'human_use_eligible':False,'physical_evidence':'NOT_PERFORMED',
        'selected_scope':'REDUCED_REGION_UNPOWERED_INERT_SURROGATE',
        'wearable_reaction_path':'BLOCKED: registered non-required-region retention/support handoff absent',
        'material_volumes_mm3':{k:v.Volume() for k,v in material.items()},'wearable_added_mass_g':None,
        'bench_material_density_g_mm3':None,'bench_mass_g':None,
        'reference_policy':'All motion, film and delivery access volumes are non-material references',
        'emergency_release':'NO_SEQUENCE_LOCK_IMPLEMENTED; wearable emergency release remains solely with its canonical owner',
        'assembly_interfaces':'Coupon four flange bores; normal guides master plus relieved mate; C-guided catch tray; twin transverse applicator guides; lid pin bores. Supplier retention/clamp hardware and forces remain unqualified.'}


def export(output: Path,p=Parameters()):
    material,refs,report=build(p)
    if report['collision_blockers']:
        raise FacialInterfaceError('continuous collision gate: '+str(report['collision_blockers']))
    output.mkdir(parents=True,exist_ok=True)
    report['component_step_roundtrip']={}
    for name,shape in material.items():
        file=output/(name+'.step')
        cq.exporters.export(shape,str(file))
        imported=cq.importers.importStep(str(file)).val()
        positive(imported,name+' STEP round trip')
        delta=abs(imported.Volume()-shape.Volume())
        # Analytic fixture only: tight absolute bound, no tolerance promotion.
        if delta>2e-4:raise FacialInterfaceError(name+' STEP volume drift')
        report['component_step_roundtrip'][name]={'solid_count':1,'valid':True,'absolute_volume_delta_mm3':delta}

    for state,transforms in report['states'].items():
        assembly=cq.Assembly(name='MASCK_CS018_'+state)
        for name,s in material.items():assembly.add(s,name=name,loc=cq.Location(cq.Vector(*transforms.get(name,(0,0,0)))))
        assembly.save(str(output/(state+'.step')))
    cq.exporters.export(cq.Compound.makeCompound(list(refs.values())),str(output/'REFERENCE_ONLY.step'))
    report['components']=[{'id':k,'parent':'OFF_FACE_CS018_BENCH','classification':'MANUFACTURED_BENCH_CANDIDATE',
        'local_frame':'COUPON_CROWN_ORIGIN_Z_OUTWARD_Y_CYLINDER_AXIS','world_transform':[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]],
        'authority_world_transform':None,'fusion_class':'A_ANALYTIC_NATIVE_REBUILD',
        'material_role':'UNQUALIFIED_BENCH_MATERIAL','manufacturing_intent':'Analytic extrusion/cylinder/pocket, inspectable and separable',
        'parameters':asdict(p)} for k in material]
    report['functional_datums']={'A':'Coupon flange underside Z=-6.1',
        'B':'Master normal guide axis X=-32,Y=0',
        'C':'Relieved normal guide axis X=32,Y=0',
        'observation_domain':'X=-15..15,Y=-20..20 on analytic coupon'}
    report['intended_dofs']={'clean_cassette':'Z translation; pin captured in ISOLATED; pins removed for SERVICE',
        'catch_shutter':'Y translation', 'delivery_body':'X translation',
        'delivery_lid':'Rigid to delivery body; supplier clamp unresolved',
        'parking_pins':'Y insertion; removable bench hardware, not wearable release controls'}
    report['motion_evidence']='CONSERVATIVE_CONTINUOUS_TRANSLATION_BREP; no sampled-pose clearance claim'
    report['normal_wearable_release']='BLOCKED: this fixture does not represent whole-head removal'
    import subprocess
    try:
        report['source_commit']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=Path(__file__).resolve().parents[2],text=True).strip()
        report['source_worktree_dirty']=bool(subprocess.check_output(['git','status','--porcelain'],cwd=Path(__file__).resolve().parents[2],text=True).strip())
    except (OSError,subprocess.CalledProcessError):
        report['source_commit']=None;report['source_worktree_dirty']=None
    report['producer_dependencies']=json.loads((Path(__file__).resolve().parents[2]/'docs/contracts/facial_interface_sources.json').read_text())
    report['source_sha256']=sha256(Path(__file__).read_bytes()).hexdigest()
    report['source_files_sha256']={name:sha256((Path(__file__).parent/name).read_bytes()).hexdigest()
        for name in ('facial_interface_bench.py','facial_interface_occlusion.py','regional_cleansing.py','cleansing_fit.py')}
    report['runtime']={'cadquery':cq.__version__}
    report['reproducibility']='Analytic geometry and sorted semantic manifest; STEP export headers may contain runtime timestamps'

    report['step_sha256']={f.name:sha256(f.read_bytes()).hexdigest() for f in sorted(output.glob('*.step'))}
    (output/'fusion_handoff.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    return report


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    result=export(args.output)
    print(json.dumps({'components':len(result['components']), 'collision_blockers':result['collision_blockers'],
                      'whole_face_complete':result['whole_face_complete']}))
