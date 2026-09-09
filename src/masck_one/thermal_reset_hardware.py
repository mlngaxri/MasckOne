"""Passive thermal cassette and reset cradle for an OFF-FACE engineering fixture.

This is the selected bench comparison in the existing WARM/COOL lane. It is not
an approved energized wearable. Unselected heater, sensors, PCM and fasteners are
explicit package/media references. Machined parts have complete analytic B-reps.
"""
from dataclasses import dataclass, asdict
from hashlib import sha256
import json, math, re
from pathlib import Path
import cadquery as cq
from .warm_cool_package import SOURCE_MAIN_SHA, AUTHORITY_BLOB_SHA, _require_release_authority
from .authority import load_authority

SCHEMA='MASCK_ONE_THERMAL_RESET_HARDWARE'
OWNER_BASE_SHA='61b4da28f8fbd45fc1a9885db4366f8506d2043e'
TREATMENT_READ_ONLY_SHA='43c3866eea56801696068ad4e417d5b21498682d'


@dataclass(frozen=True)
class Parameters:
    store_width_mm: float=24.
    store_height_mm: float=40.
    store_depth_mm: float=8.
    wall_mm: float=.7
    floor_mm: float=.6
    lid_mm: float=.6
    plate_width_mm: float=22.
    plate_height_mm: float=28.
    plate_thickness_mm: float=1.
    plate_y_offset_mm: float=6.
    choke_length_mm: float=2.
    choke_width_mm: float=.92
    fin_count: int=9
    fin_thickness_mm: float=.4
    fin_height_mm: float=6.
    fin_pitch_mm: float=2.3
    fill_port_diameter_mm: float=2.
    reset_travel_mm: float=20.

    def __post_init__(self):
        for name,value in asdict(self).items():
            if type(value) not in (float,int) or not math.isfinite(value) or value<=0:
                raise ValueError(f'positive finite {name} required')
        if type(self.fin_count) is not int or self.fin_count<1:
            raise ValueError('integral fin count required')
        if self.fin_height_mm>=self.store_depth_mm-self.floor_mm-self.lid_mm:
            raise ValueError('connected headspace above fins required')
        if (self.fin_count-1)*self.fin_pitch_mm+self.fin_thickness_mm>=self.store_width_mm-2*self.wall_mm:
            raise ValueError('fin array must fit store cavity')
        if min(self.store_width_mm,self.store_height_mm)<=2*self.wall_mm:
            raise ValueError('positive cavity required')
        if self.plate_width_mm>self.store_width_mm or self.plate_y_offset_mm+self.plate_height_mm/2>self.store_height_mm/2:
            raise ValueError('plate must stay inside store XY footprint')


def box(x,y,z,c):
    return cq.Workplane('XY').box(x,y,z).translate(c).val()


def cylinder(r,h,c):
    return cq.Solid.makeCylinder(r,h,cq.Vector(*c))


def positive(part,name):
    if not part.isValid() or len(part.Solids())!=1 or not math.isfinite(part.Volume()) or part.Volume()<=0:
        raise ValueError(f'{name}: expected one valid positive manufactured B-rep')
    return part


def intersection(a,b):
    total=0.
    for s in a.Solids():
        for t in b.Solids():
            common=s.intersect(t)
            for v in common.Solids():
                value=v.Volume()
                if not v.isValid() or not math.isfinite(value) or value<0:
                    raise ValueError('invalid common, cannot claim clearance')
                total+=value
    return total


def cassette(p=Parameters()):
    """Local origin is store XY center and depth mid-plane, +Z into dry package.

    Four integral 0.92 mm square columns distribute and meter conductance. Gap
    is machined from opposite sides, leaving the columns. They are stationary;
    there is no conductive member attached to the massage suspension.
    """
    z0=-p.store_depth_mm/2
    zlid=p.store_depth_mm/2-p.lid_mm
    cavity=box(p.store_width_mm-2*p.wall_mm,p.store_height_mm-2*p.wall_mm,
               p.store_depth_mm-p.floor_mm-p.lid_mm,(0,0,(z0+p.floor_mm+zlid)/2))
    tray=box(p.store_width_mm,p.store_height_mm,p.store_depth_mm-p.lid_mm,(0,0,(z0+zlid)/2)).cut(cavity)
    # All fins stop below the lid and short of side walls; headspace is connected.
    for i in range(p.fin_count):
        x=(i-(p.fin_count-1)/2)*p.fin_pitch_mm
        fin=box(p.fin_thickness_mm,p.store_height_mm-4*p.wall_mm,p.fin_height_mm+.1,
                (x,0,z0+p.floor_mm+(p.fin_height_mm-.1)/2))
        tray=tray.fuse(fin)
    free=cavity.cut(tray).clean()
    positive(free,'connected PCM cavity reference')
    plate_top=z0-p.choke_length_mm
    plate_front=plate_top-p.plate_thickness_mm
    plate=box(p.plate_width_mm,p.plate_height_mm,p.plate_thickness_mm,
              (0,p.plate_y_offset_mm,plate_top-p.plate_thickness_mm/2))
    posts=[(x,p.plate_y_offset_mm+y) for x in (-8.,8.) for y in (-8.,8.)]
    for x,y in posts:
        post=box(p.choke_width_mm,p.choke_width_mm,p.choke_length_mm+.2,
                 (x,y,(plate_top+z0)/2))
        tray=tray.fuse(post)
    tray=tray.fuse(plate).clean()
    # Two sensor wells on the dry side retain a continuous metal floor.
    sensors={}
    for tag,x in [('control',-7.),('independent_fault',7.)]:
        well=box(2.,2.,.25,(x,p.plate_y_offset_mm+9.,plate_top-.125))
        tray=tray.cut(well).clean()
        sensors[tag]=well
    lid=box(p.store_width_mm,p.store_height_mm,p.lid_mm,(0,0,zlid+p.lid_mm/2))
    plug=cylinder(p.fill_port_diameter_mm/2,p.lid_mm,(0,-16.,zlid))
    lid=lid.cut(plug).clean()
    # Planar lap land is the 0.7 mm tray rim; lid and fill plug need a qualified
    # continuous metal joining process. No seal-performance claim follows.
    # Nonstructural dielectric sheet/carrier for an externally qualified foil heater.
    heater_carrier=box(18.,24.,.10,(0,p.plate_y_offset_mm,plate_top+.05))
    heater=box(18.,24.,.05,(0,p.plate_y_offset_mm,plate_top+.125))
    insulator=box(p.plate_width_mm-.4,p.plate_height_mm-.4,1.5,
                  (0,p.plate_y_offset_mm,plate_top+.9))
    for x,y in posts:
        hole=box(p.choke_width_mm+.4,p.choke_width_mm+.4,2.,(x,y,plate_top+1.))
        insulator=insulator.cut(hole)
        heater_carrier=heater_carrier.cut(hole)
        heater=heater.cut(hole)
    for x in (-7.,7.):
        hole=box(2.4,2.4,2.,(x,p.plate_y_offset_mm+9.,plate_top+1.))
        insulator=insulator.cut(hole);heater_carrier=heater_carrier.cut(hole);heater=heater.cut(hole)
    # Harness exits the stationary superior edge, not through a moving flexure.
    insulator=insulator.cut(box(4.,8.,2.,(0,p.plate_y_offset_mm+11.,plate_top+1.))).clean()
    harness=box(3.6,8.,1.,(0,p.plate_y_offset_mm+11.,plate_top+.8))
    # Captive polymer lid for the dry laminate stack. Side hooks slide into blind
    # longitudinal grooves outside the liquid cavity, with a closed +Y end stop.
    retainer=box(22.,27.,.25,(0,p.plate_y_offset_mm,plate_top+1.775))
    retainer=retainer.cut(box(18.,23.,.5,(0,p.plate_y_offset_mm,plate_top+1.775)))
    for sign in (-1.,1.):
        groove=box(.35,26.,.35,(sign*11.875,p.plate_y_offset_mm-.2,z0+.35))
        tray=tray.cut(groove)
        hook=box(.6,25.6,.25,(sign*12.,p.plate_y_offset_mm-.2,z0+.35))
        leg=box(.25,25.6,1.,(sign*12.275,p.plate_y_offset_mm-.2,z0-.05))
        bridge=box(1.5,25.6,.25,(sign*11.65,p.plate_y_offset_mm-.2,plate_top+1.775))
        retainer=retainer.fuse(hook).fuse(leg).fuse(bridge)
    retainer=retainer.clean()
    material={'finned_store_and_choked_plate':tray.clean(),'store_lid':lid,'fill_plug':plug,
              'heater_dielectric_carrier':heater_carrier.clean(),'backside_insulator':insulator,
              'laminate_retainer':retainer}
    refs={'PCM_INTERNAL_VOID':free,'HEATER_SUPPLIER_ENVELOPE':heater,
          'CONTROL_SENSOR_ENVELOPE':sensors['control'],
          'FAULT_SENSOR_ENVELOPE':sensors['independent_fault'],'HARNESS_PASSAGE':harness}
    for k,v in material.items():positive(v,k)
    for k,v in refs.items():positive(v,k)
    return material,refs,dict(plate_front_z_mm=plate_front,cavity_mm3=free.Volume(),
            lid_seal_land_width_mm=p.wall_mm,plate_area_mm2=p.plate_width_mm*p.plate_height_mm,
            choke_total_section_mm2=4*p.choke_width_mm**2,choke_length_mm=p.choke_length_mm,
            choke_positions_local_mm=posts,heater_size_mm=[18.,24.],
            heater_post_neighborhood_power_fraction_DOE=.6,
            fin_area_mm2=2*p.fin_count*(p.store_height_mm-4*p.wall_mm)*p.fin_height_mm,
            PCM_maximum_half_pitch_mm=(p.fin_pitch_mm-p.fin_thickness_mm)/2)


def dock(p,plate_front):
    # Extrusion-compatible fins/base/raised rail, cut to length. One central
    # rail relief leaves two receiver lands. No separate pucks or bearings.
    top=plate_front-4.
    sink=box(140.,60.,3.,(0,-10.,top-1.5))
    rail=box(140.,p.plate_height_mm,4.1,(0,-10.+p.plate_y_offset_mm,plate_front-2.05))
    rail=rail.cut(box(76.,p.plate_height_mm+1.,4.2,(0,-10.+p.plate_y_offset_mm,plate_front-2.)))
    sink=sink.fuse(rail)
    for y in range(-35,20,4):
        sink=sink.fuse(box(140.,1.,18.1,(0,float(y),top-3.-8.95)))
    # Cradle mounts outside the sink with a planar flange and four M2-clearance
    # bores. Fasteners remain supplier references; no thread is approximated as
    # accepted material. Left master / right relieved guide avoids spacing bind.
    base=box(152.,70.,2.,(0,-10.,top-4.))
    base=base.cut(box(140.4,60.4,3.,(0,-10.,top-4.)))
    guide_parts=[]
    for x,relief in [(-52.,0.),(52.,1.)]:
        outer=box(35.,66.,8.,(x,-10.,plate_front+4.))
        zbase=plate_front-.1
        cavity=(cq.Workplane('XY').workplane(offset=zbase).center(x,-10.)
                .rect(p.store_width_mm+1.2+relief,p.store_height_mm+.4)
                .workplane(offset=8.2).rect(p.store_width_mm+7.2+relief,p.store_height_mm+6.4)
                .loft(combine=True).val())
        guide=outer.cut(cavity)
        # Core thick end regions for molded-polymer development; do not make a
        # heavy solid block merely to obtain a visually solid touch surface.
        for y in (-38.,18.):
            guide=guide.cut(box(27.,7.,6.1,(x,y,plate_front+5.05)))
        # Two exterior risers connect each guide to the base flange.
        for y in (-42.,22.):
            guide=guide.fuse(box(6.,2.,abs(top-4.-plate_front)+1.,
                                (x,y,(top-4.+plate_front)/2)))
        guide_parts.append(guide)
    for g in guide_parts:base=base.fuse(g)
    # Cross rails connect the two sides of the cradle outside the heat-sink block.
    for y in (-43.,23.):
        base=base.fuse(box(145.,3.,3.,(0,y,top-3.)))
    # Cradle flange holes, external to thermal contact and drainage area.
    for x in (-73.,73.):
        for y in (-37.,17.):
            hole=cylinder(1.1,5.,(x,y,top-6.))
            base=base.cut(hole)
    return {'dock_receiver_heat_sink':positive(sink.clean(),'dock sink'),
            'dock_acquisition_cradle':positive(base.clean(),'dock cradle')}


def build_thermal_reset_hardware(p=Parameters()):
    _require_release_authority(load_authority())
    local,refs,metrics=cassette(p)
    parts={};references={};component_data=[]
    for side,x in [('LEFT',-52.),('RIGHT',52.)]:
        origin=(x,-10.,0.)
        for name,shape in local.items():
            key=f'{side}_{name}';parts[key]=shape.translate(origin)
            component_data.append(dict(component_id=key,parent_assembly=f'THERMAL_{side}',
                local_frame='STORE_CENTER_XY_DEPTH_MIDPLANE',world_transform=[[1,0,0,x],[0,1,0,-10.],[0,0,1,0],[0,0,0,1]],
                local_datums={'contact_plane_z_mm':metrics['plate_front_z_mm'],'lid_plane_z_mm':p.store_depth_mm/2},
                classification='MANUFACTURED_BENCH_COMPONENT',fusion_class='A_NATIVE_ANALYTIC_REBUILD',
                material_role=('MACHINED_METAL' if name=='finned_store_and_choked_plate' else
                               'JOINED_METAL_CLOSURE' if name in ('store_lid','fill_plug') else 'DIELECTRIC_OR_INSULATION_UNQUALIFIED'),
                joint='RIGID_STATIONARY_THERMAL_GROUP',service='JOINED_STORE_FACTORY_ONLY; WHOLE_CASSETTE_LIFTS_+Z_IN_BENCH_CRADLE',
                feature_intent='RECTANGULAR_POCKETS_AND_FINS; INTEGRAL_COLUMNS; PLANAR_JOIN_LAND',parameters=asdict(p)))
        for name,shape in refs.items():references[f'{side}_{name}']=shape.translate(origin)
        # Conservative full bench withdrawal envelope, analytically extruded XY
        # package bound. It is not a wearable service or arbitrary rotation proof.
        zmin=metrics['plate_front_z_mm'];zmax=p.store_depth_mm/2+p.reset_travel_mm
        references[f'{side}_BENCH_WITHDRAWAL']=box(p.store_width_mm+.8,p.store_height_mm,zmax-zmin,
                                                    (x,-10.,(zmin+zmax)/2))
    dock_parts=dock(p,metrics['plate_front_z_mm']);parts.update(dock_parts)
    for key in dock_parts:
        component_data.append(dict(component_id=key,parent_assembly='OFF_FACE_RESET_DOCK',
            local_frame='AUTHORITY_ALIGNED_BENCH',world_transform=[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]],
            local_datums={'receiver_plane_z_mm':metrics['plate_front_z_mm']},
            classification='MANUFACTURED_BENCH_COMPONENT',fusion_class='A_NATIVE_ANALYTIC_REBUILD',
            material_role='METAL_HEAT_SINK' if 'sink' in key else 'STRUCTURAL_POLYMER',
            joint='RIGID_BENCH_BASE; CRADLE_M2_CLEARANCE_BORES',service='LIFT_CASSETTES_WITHOUT_LATCH',parameters=asdict(p)))
    checks={}
    checks['dock_cradle/sink']=intersection(dock_parts['dock_acquisition_cradle'],dock_parts['dock_receiver_heat_sink'])
    for side in ('LEFT','RIGHT'):
        names=[k for k in parts if k.startswith(side)]
        for i,a in enumerate(names):
            for b in names[i+1:]:checks[f'{a}/{b}']=intersection(parts[a],parts[b])
        for target in dock_parts:
            checks[f'{side}_WITHDRAWAL/{target}']=intersection(references[f'{side}_BENCH_WITHDRAWAL'],parts[target])
    manifest=dict(schema=SCHEMA,source_main_sha=SOURCE_MAIN_SHA,owner_base_sha=OWNER_BASE_SHA,
        authority_blob_sha=AUTHORITY_BLOB_SHA,read_only_treatment_head=TREATMENT_READ_ONLY_SHA,
        selected_bench_architecture='STATIONARY_CHOKED_SHARED_PLATE_FINNED_LATENT_STORE_DIRECT_PLATE_DOCK_RESET',
        production_architecture_status='BLOCKED_PHYSICAL_THERMAL_AND_WHOLE_PRODUCT_INTERFACES',
        human_use_eligible=False,parameters=asdict(p),metrics=metrics,components=component_data,
        reference_ids=list(references),internal_and_bench_motion_intersections_mm3=checks,
        cost_and_tactile_strategy={
            'dock':'MOLDED_CORED_POLYMER_ACQUISITION_CRADLE; EXTRUDED_SINK_WITH_ONE_CENTRAL_RELIEF; NO_LATCH_MAGNET_OR_BEARING',
            'acquisition':'LEFT_MASTER_RIGHT_RELIEVED_FUNNEL; 3_MM_PER_SIDE_FLARE_OVER_8P2_MM; 20_MM_VERTICAL_WITHDRAWAL_REFERENCE',
            'terminal':'BROAD_THERMAL_DATUM_CONTACT_UNDER_GRAVITY; CONTACT_PRESSURE_IS_AN_UNQUALIFIED_INPUT',
            'touch_surface':'POLYMER_EDGE_AND_GAP_FINISH_REQUIRE_TOOLING_AND_CLEANSER_COMPATIBILITY_VALIDATION',
            'store':'MONOLITHIC_MACHINED_BENCH_COUPON; PRODUCTION_COST_NOT_CLOSED; FORMING_OR_CASTING_NEEDS_THERMAL_AND_JOIN_EQUIVALENCE',
            'unit_cost':'UNKNOWN_NO_SUPPLIER_QUOTES; NO_UNIT_COST_OR_TACTILE_PERFORMANCE_CLAIM'},
        whole_product_installation='OPEN; CURRENT_TREATMENT_FULL_ASSEMBLY_GATE_RED',
        wet_interface='METAL_CONTACT_PLATE; FLUID/CONDENSATE_DRAINS_AROUND_PLATE; EXACT_OWNER_ROUTE_REBIND_OPEN',
        heater_protection='SEMANTIC_ONLY: INDEPENDENT_HARDWARE_CUTOFF_IN_SERIES; SENSOR_OPEN_SHORT_DETACH_AND_WATCHDOG_INHIBIT; NO_CONTROL_FIRMWARE',
        electrical_hardware='HEATER_SENSOR_HARNESS_REFERENCES_ONLY; NO_ENERGIZED_WEARABLE_BUILD_INSTRUCTIONS',
        reference_policy='PCM_VOID_HEATER_SENSOR_HARNESS_AND_SWEEPS_EXCLUDED_FROM_MANUFACTURED_ASSEMBLIES')
    if any(v>1e-7 for v in checks.values()):
        raise ValueError('thermal material or conservative bench motion interference: '+str({k:v for k,v in checks.items() if v>1e-7}))
    return parts,references,manifest


def export_thermal_reset(output_dir: Path,source_head_sha: str,p=Parameters()):
    if not re.fullmatch('[0-9a-f]{40}',source_head_sha):raise ValueError('exact source SHA required')
    parts,refs,manifest=build_thermal_reset_hardware(p)
    output_dir.mkdir(parents=True,exist_ok=True)
    if any(output_dir.glob('*.step')):raise ValueError('export requires a fresh directory to exclude stale parts')
    for name,shape in parts.items():
        # Standalone manufactured files are LOCAL, assemblies below are WORLD.
        if name.startswith('LEFT'):shape=shape.translate((52.,10.,0.))
        elif name.startswith('RIGHT'):shape=shape.translate((-52.,10.,0.))
        cq.exporters.export(shape,str(output_dir/f'{name}.step'))
    for name,shape in refs.items():cq.exporters.export(shape,str(output_dir/f'{name}_REFERENCE.step'))
    for name,select in [('THERMAL_LEFT',lambda k:k.startswith('LEFT')),('THERMAL_RIGHT',lambda k:k.startswith('RIGHT')),
                        ('OFF_FACE_DOCK',lambda k:k.startswith('dock')),('THERMAL_DOCKED_BENCH',lambda k:True)]:
        assembly=cq.Assembly(name=name)
        for key,shape in parts.items():
            if select(key):assembly.add(shape,name=key)
        assembly.export(str(output_dir/f'{name}.step'))
    service=cq.Assembly(name='THERMAL_BENCH_SERVICE')
    for key,shape in parts.items():service.add(shape if key.startswith('dock') else shape.translate((0,0,p.reset_travel_mm)),name=key)
    service.export(str(output_dir/'THERMAL_BENCH_SERVICE.step'))
    manifest['source_file_sha256']={str(Path(__file__).name):sha256(Path(__file__).read_bytes()).hexdigest()}
    manifest['producer_head_sha']=source_head_sha
    manifest['standalone_part_coordinates']='LOCAL; APPLY_COMPONENT_WORLD_TRANSFORM_ONCE'
    manifest['assembly_coordinates']='WORLD; DO_NOT_APPLY_COMPONENT_TRANSFORM_AGAIN'
    for component in manifest['components']:component['source_sha']=source_head_sha
    # Normalize only nondesign header metadata; do not change topology entities.
    for path in output_dir.glob('*.step'):
        text=path.read_text()
        text=re.sub(r"FILE_NAME\('[^']*','[^']*'",f"FILE_NAME('{path.name}','1970-01-01T00:00:00'",text)
        path.write_text(text)
    header=(output_dir/'LEFT_store_lid.step').read_text().split('DATA;')[0]
    manifest['step_schema_header']=header[header.find('FILE_SCHEMA'):].strip()
    manifest['step_metadata_policy']='NORMALIZED_FILENAME_AND_TIMESTAMP; GEOMETRY_UNALTERED'
    manifest['step_sha256']={f.name:sha256(f.read_bytes()).hexdigest() for f in sorted(output_dir.glob('*.step'))}
    (output_dir/'fusion_thermal_handoff.json').write_text(json.dumps(manifest,indent=2,sort_keys=True,allow_nan=False)+'\n')
    return manifest
