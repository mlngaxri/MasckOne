"""Source-bound architecture B-reps for digital and inert bench evaluation only.
Not released material, supplier internals, operating instructions or human-use CAD.
"""
from pathlib import Path
import math,json,hashlib
import cadquery as cq
import numpy as np
from masck_one.model import build_model
from masck_one.structural_frame_realization import _protected_zone_solid

ROOT=Path(__file__).resolve().parents[1]
BASE='a0ea51874d8967c512468932fac627e8bba5f95f'
FRAME_HEAD='4b1e38f7456fbf06fd30a5f2280e0dabfda7ee2c'
STATION_POSES={'superior':(36,70,7),'inferior':(52,-45,3)}

def box(x,y,z,center): return cq.Workplane('XY').box(x,y,z).translate(center).val()
def cylinder(r,z0,z1): return cq.Workplane('XY').circle(r).extrude(z1-z0).translate((0,0,z0)).val()
def ring(ri,ro,z0,z1): return cylinder(ro,z0,z1).cut(cylinder(ri,z0-1,z1+1))
def join(shapes):
    a=shapes[0]
    for b in shapes[1:]:a=a.fuse(b)
    return a.clean()
def bar(a,b,r):
    a,b=cq.Vector(*a),cq.Vector(*b);d=b-a
    return cq.Solid.makeCylinder(r,d.Length,a,d.normalized())
def iv(a,b):
    # Exceptions are errors, never silently reported as collision-free.
    aa,bb=a.BoundingBox(),b.BoundingBox()
    if any(getattr(aa,q+'max')<getattr(bb,q+'min') or getattr(bb,q+'max')<getattr(aa,q+'min') for q in 'xyz'):return 0.
    s=a.intersect(b)
    return sum(max(0.,v.Volume()) for v in s.Solids())
def valid(a): return bool(a.isValid() and len(a.Solids())==1 and a.Volume()>0)
def pose(a,c,angle=61): return a.rotate((0,0,0),(0,1,0),angle).translate(c)

def spiral(z,hand=1,t=.05):
    # Curved 2-D centerline offset, circular ends, datum-based boundaries.
    arms=[]
    for phase in (0,120,240):
        s=np.linspace(0,1,81);r=6.95+(2.85-6.95)*s;theta=np.radians(phase+hand*110*s)
        p=np.column_stack((r*np.cos(theta),r*np.sin(theta)))
        tang=np.gradient(p,axis=0);tang/=np.linalg.norm(tang,axis=1)[:,None]
        normal=np.column_stack((-tang[:,1],tang[:,0]));left=p+.2*normal;right=p-.2*normal
        outline=np.vstack((left,right[::-1]))
        a=cq.Workplane('XY').polyline(outline.tolist()).close().extrude(t).translate((0,0,z-t/2)).val()
        ends=[cylinder(.2,z-t/2,z+t/2).translate((*q,0)) for q in (p[0],p[-1])]
        arms.append(join([a,*ends]))
    return join([ring(1.6,3.05,z-t/2,z+t/2),ring(6.8,7.6,z-t/2,z+t/2),*arms])

def cup_features(lo=0.,hi=0.):
    # Every feature is a fixed XY profile extruded along the one moving axis.
    # Expanding each interval is its exact continuous translation sweep.
    parts=[ring(6.8,7.6,-7.85+lo,-7.525+hi),
       ring(1.6,6.4,6.8+lo,7.2+hi),ring(1.6,2.8,7.15+lo,7.975+hi)]
    for deg in (0,120,240):
        th=math.radians(deg);x,y=6.35*math.cos(th),6.35*math.sin(th)
        parts += [cylinder(.23,-7.65+lo,7.0+hi).translate((x,y,0)),
          box(.95,.4,.4+hi-lo,(6.75,0,-7.65+(lo+hi)/2)).rotate((0,0,0),(0,0,1),deg)]
    return parts


def cassette():
    material={};reference={}
    material['rear_spiral']=spiral(-7.5,1)
    material['front_spiral']=spiral(8,-1)
    material['moving_cup']=join(cup_features())
    material['moving_rear_clamp']=ring(6.8,7.6,-7.475,-7.2)
    material['moving_front_clamp']=ring(1.6,2.8,8.025,8.3)
    back=ring(1.6,3.0,-9.1,-8.7)
    fixed=[back,ring(1.6,2.8,-8.8,-7.525),ring(6.8,8.7,8.025,8.6)]
    for deg in (60,180,300):
        th=math.radians(deg);x,y=8.25*math.cos(th),8.25*math.sin(th)
        fixed += [cylinder(.4,-8.9,8.4).translate((x,y,0)),bar((0,0,-8.9),(x,y,-8.9),.3)]
    material['fixed_cage']=join(fixed)
    material['fixed_rear_clamp']=ring(1.6,2.8,-7.475,-7.2)
    material['fixed_front_clamp']=ring(6.8,8.7,7.7,7.975)
    # Rigid fault stops outside nominal +/-.26; compliant buffer surfaces remain separate.
    material['rear_stop_ring']=join([ring(6.8,7.6,-8.4,-8.3),*[cylinder(.22,-8.9,-8.3).translate((7.1*math.cos(math.radians(d)),7.1*math.sin(math.radians(d)),0)) for d in (60,180,300)]])
    material['rear_buffer']=ring(6.8,7.6,-8.3,-8.2)
    # The stationary stop carrier also supports two capacitive electrodes.
    # This removes a separate sensor bracket and adds no moving magnet/wire.
    material['front_stop_ring']=join([ring(3.1,6.4,7.78,7.975),
        ring(3.1,3.6,7.65,7.78),ring(6.,6.4,7.65,7.78),
        *[bar((6.2*math.cos(math.radians(d)),6.2*math.sin(math.radians(d)),7.85),
          (7.1*math.cos(math.radians(d)),7.1*math.sin(math.radians(d)),7.85),.12) for d in (60,180,300)]])
    material['front_buffer_inner']=ring(3.1,3.6,7.55,7.65)
    material['front_buffer_outer']=ring(6.,6.4,7.55,7.65)
    electrode=ring(3.7,5.9,7.745,7.78)
    material['position_electrode_A']=electrode.intersect(box(6,14,.1,(3.1,0,7.76)))
    material['position_electrode_B']=electrode.intersect(box(6,14,.1,(-3.1,0,7.76)))
    # A real dielectric separates each electrode from the conductive stop carrier.
    for name in ('A','B'):
        substrate=material['position_electrode_'+name].translate((0,0,.035))
        material['position_electrode_dielectric_'+name]=substrate
        material['front_stop_ring']=material['front_stop_ring'].cut(substrate)
    # Integrate the structural stop supports into their actual rigid members.
    # No overlapping nominal parts are mislabeled as an attachment interface.
    material['front_stop_ring']=join([material['front_stop_ring'],material.pop('fixed_front_clamp')])
    material['fixed_cage']=join([material['fixed_cage'],material.pop('rear_stop_ring')])
    reference['supplier_magnet_package']=cylinder(5.55,-7.1,1.9)
    reference['supplier_total_package_bound']=cylinder(5.55,-7.1,6.8)
    reference['supplier_coil_front_datum']=cq.Vertex.makeVertex(0,0,6.8)
    reference['rear_mount_fastener_reservation']=cylinder(2.8,-11.1,-9.1)
    reference['front_mount_fastener_reservation']=cylinder(2.8,8.3,10.3)
    material['rear_magnet_seating_spacer']=ring(1.6,2.8,-7.2,-7.1)
    # Drawing: 9mm magnet, 12.7mm fully retracted, 3.2mm actuator travel.
    # Coil mating face = -7.1 +12.7 +1.2 =6.8, coincident with cup rear face.
    # The 1.2mm offset is a packaging choice, not a measured force-flatness claim.

    reference['commanded_cup_sweep']=ring(6.8,7.6,-8.11,-7.265) # one feature; full sweep below
    return material,reference

def protected(model):
    d={}
    for p in model.protected_volumes.all:
        z=p.zone;d[z.zone_id]=_protected_zone_solid(center_x_mm=z.center.x,center_y_mm=z.center.y,
          envelope_width_mm=z.envelope_width_mm,envelope_height_mm=z.envelope_height_mm,angle_deg=z.angle_deg,z_min_mm=-40,z_max_mm=50).val()
    return d

def translation_envelope(shape,travel):
    # Guaranteed continuous superset for pure axial translation: sweep every face.
    # Prism(shape) is not valid for a solid; face prisms plus endpoints form its union sweep.
    from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
    from OCP.gp import gp_Vec
    pieces=[shape,shape.translate(travel)]
    for f in shape.Faces():
        prism=cq.Shape.cast(BRepPrimAPI_MakePrism(f.wrapped,gp_Vec(*travel)).Shape())
        if prism.Solids(): pieces.extend(prism.Solids())
    return join(pieces)


def thermal_cell_specs():
    for side in (-1,1):
      for i,y in enumerate((-26.,-10.,6.)):
        if side<0:y=(-23.9,-9.2,6.8)[i]
        height=10.4 if side<0 and i==0 else 14.6
        yield side,i,side*(52.5 if i<2 else 54.5),y,(19. if i<2 else 10.),height

def thermal_cells():
    mat={};ref={}
    # Six distributed cells; PCM and semiconductor envelopes are references.
    # Three cells per side stay inboard of the secondary HMI band reservation.
    for side in (-1,1):
      for _,i,x,y,width,cell_h in [spec for spec in thermal_cell_specs() if spec[0]==side]:
        name=f'{"L" if side<0 else "R"}_{i}'
        nfin=16 if i<2 else 8
        outer=box(width+.6,cell_h+.6,11.6,(x,y,10.2))
        cavity=box(width,cell_h,11,(x,y,10.2))
        # open at -Z for a separately bonded metal base; top and side walls .30
        open_cut=box(width,cell_h,12,(x,y,9.7))
        body=outer.cut(open_cut)
        base=box(width+.6,cell_h+.6,.3,(x,y,4.55))
        fins=[box(.05,cell_h,10,(x-width/2+.6+j*(width-1.2)/(nfin-1),y,9.7)) for j in range(nfin)]
        finpack=join([base,*fins])
        mat[f'cell_body_{name}']=body
        mat[f'cell_fin_base_{name}']=finpack
        void=cavity.cut(finpack)
        ref[f'pcm_void_{name}']=void
        # 6.1 x 7.2 x 2.14 exact catalog packaging only.
        ref[f'tec_package_{name}']=box(6.1,7.2,2.14,(x,y,3.18))
        mat[f'cold_bus_{name}']=box(width+.6,cell_h+.6,.6,(x,y,1.81))
        insulation=box(width+3,cell_h+3,14,(x,y,10.2)).cut(outer)
        # A bottom opening preserves the solid thermal path, not fictitious insulation.
        insulation=insulation.cut(box(width+.6,cell_h+.6,3,(x,y,3.8)))
        mat[f'insulation_{name}']=insulation.intersect(box(30,16,30,(x,y,10)))
      # Same stationary contact plate serves both heat-flow directions.
      mat[f'cheek_spreader_{side}']=box(22,28,.35,(side*52,-4,-3.5))
      mat[f'contact_barrier_{side}']=box(22,28,.25,(side*52,-4,-3.8))
      # Folded stationary heat path: two vertical blades join the contact spreader
      # to a single continuous cold bus. No foil bridge flexes with massage.
      spine=box(9,47.2,.6,(side*54,-10,1.81))
      keys=[k for k in mat if k.startswith('cold_bus_') and k.split('_')[2]==('L' if side<0 else 'R')]
      bus=join([spine,*[mat.pop(k) for k in keys]])
      blades=[box(.35,26,4.835,(side*x,-4,-.9075)) for x in (49,56)]
      mat[f'fixed_folded_bus_{side}']=join([bus,*blades])
    return mat,ref


def measure():
    out=ROOT/'studies'/'generated';out.mkdir(exist_ok=True)
    material,reference=cassette();tm,tr=thermal_cells()
    model=build_model();pz=protected(model)
    report={'base_main':BASE,'frame_head':FRAME_HEAD,'human_use_eligible':False,
      'integration_status':'REACTION_FRAME_ACCEPTED; PROPOSED_PORTS_REQUIRED; SUPPORTED_PRE_ROLL_DIAGNOSTIC_ONLY',
      'material_geometry':{},'stations':{},'thermal_geometry':{}}
    for k,v in material.items():report['material_geometry'][k]={'valid':valid(v),'solids':len(v.Solids()),'volume_mm3':v.Volume()}
    for k,v in tm.items():report['thermal_geometry'][k]={'valid':valid(v),'solids':len(v.Solids()),'volume_mm3':v.Volume()}
    for station,center in STATION_POSES.items():
      arr={k:pose(v,center) for k,v in material.items()}
      rr={k:pose(v,center) for k,v in reference.items() if k=='supplier_total_package_bound'}
      items=arr|rr
      report['stations'][station]={'center_mm':center,'axis_deg':61,'parts':{k:{
          'protected_mm3':{z:iv(v,p) for z,p in pz.items()},'released_shell_mm3':iv(v,model.shell.solid.val()),
          'z_range_mm':[v.BoundingBox().zmin,v.BoundingBox().zmax]} for k,v in items.items()}}
      cq.exporters.export(cq.Compound.makeCompound(list(arr.values())),str(out/f'{station}_cassette_material.step'))
    for k,v in tm.items():
      report['thermal_geometry'][k]['protected_mm3']=sum(iv(v,p) for p in pz.values())
      report['thermal_geometry'][k]['released_shell_mm3']=iv(v,model.shell.solid.val())
    report['pcm_cells_mm3']={k:v.Volume() for k,v in tr.items() if k.startswith('pcm_void')}
    report['pcm_void_mm3']=sum(report['pcm_cells_mm3'].values())
    cq.exporters.export(cq.Compound.makeCompound(list(tm.values())),str(out/'shared_thermal_material.step'))
    cq.exporters.export(cq.Compound.makeCompound(list(tr.values())),str(out/'shared_thermal_reference.step'))
    (out/'geometry_report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':measure()
