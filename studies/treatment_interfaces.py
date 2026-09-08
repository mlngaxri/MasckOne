"""Stationary thermal/wet packaging and moving seal architecture, inert geometry only."""
from treatment_geometry import *

def heater_lane(cx,side):
    # Explicit etched-foil seed. Alloy/resistance/drive and fabrication remain unselected.
    # Flat copper spreader, not local heater pitch, must distribute heat.
    strips=[];y0=-15.;pitch=2.8;length=3.8;width=.4;t=.025
    for j in range(9):
        y=y0+j*pitch;strips.append(box(length,width,t,(cx,y,-3.2625)))
        if j<8:
            x=cx+(length-width)/2*(1 if j%2==0 else -1)
            strips.append(box(width,pitch,t,(x,y+pitch/2,-3.2625)))
    return join(strips)

def thermal_interfaces():
    mat,ref=thermal_cells();new={};refs={}
    for side in (-1,1):
        # Substrate bonds to plate rear. It avoids both vertical copper folds.
        for idx,x in enumerate((44.9,59.5)):
            xx=side*x;trace=heater_lane(xx,side)
            substrate=box(4.4,24,.10,(xx,-3.8,-3.275)).cut(trace)
            new[f'heater_dielectric_{side}_{idx}']=substrate
            new[f'heater_foil_{side}_{idx}']=trace
        # Sensor package is a reservation, not invented purchased hardware internals.
        refs[f'contact_sensor_{side}']=box(1.6,1.6,.55,(side*52,-4,-3.0))
        refs[f'cold_bus_sensor_{side}']=box(1.6,1.6,.55,(side*59,-10,1.185))
        for _,i,x,y,_,_ in [spec for spec in thermal_cell_specs() if spec[0]==side]:
            label=f'{"L" if side<0 else "R"}_{i}'
            # The earlier package left a .15mm real thermal gap. Fill it explicitly.
            new[f'hot_TIM_{label}']=box(6.1,6.2,.15,(x,y,4.325))
            # Cold bondline occupies a machined/recessed cold-pad volume, not overlap.
            tim=box(6.1,7.2,.05,(x,y,2.085))
            mat[f'fixed_folded_bus_{side}']=mat[f'fixed_folded_bus_{side}'].cut(tim)
            new[f'cold_TIM_{label}']=tim
            # Perimeter solid dielectric avoids an air pocket against exposed TEC legs.
            # Moisture permeability and adhesion are physical validation, not CAD PASS.
            package=ref[f'tec_package_{label}']
            surround=box(6.5,7.6,2.29,(x,y,3.255)).cut(package).cut(new[f'hot_TIM_{label}'])
            new[f'TEC_edge_encapsulation_{label}']=surround
            refs[f'store_sensor_{label}']=box(1.6,1.6,.55,(x,y,16.3))
    return mat|new,ref|refs

def wet_boot(center,z=-4.7,height=1.):
    # Small rod boot, not a membrane carrying all stationary thermal/fluid material.
    # Nominal conical convolution is revolved; no sliding shaft seal is assumed.
    x,y=center;t=.15
    lower=[(.4,z),(.95,z),(1.45,z+height),(2.25,z+height),(2.85,z),(3.35,z)]
    upper=[(r,zz+t) for r,zz in reversed(lower)]
    boot=cq.Workplane('XZ').polyline(lower+upper).close().revolve(360,(0,0),(0,1)).val().translate((x,y,0))
    fixed=ring(2.85,3.8,z-.10,z).translate((x,y,0))
    # Inner cuff bonds to the moving rod, outer flange is clamped by stationary liner.
    return {'convoluted_rod_boot':boot,'stationary_boot_seat':fixed}

if __name__=='__main__':
    from mounted_station import station
    mat,ref=thermal_interfaces();report={}
    out=ROOT/'studies/generated';frame=cq.Shape.importBrep(str(out/'consumed_frame_reactions.brep'))
    boundary=cq.Shape.importBrep(str(out/'consumed_supported_pre_roll_boundary.brep'));pz=protected(build_model())
    for kind,c in STATION_POSES.items():
        _,station_ref=station(kind,c);takeoff=station_ref['output_shoe_center'].Center()
        for k,s in wet_boot((takeoff.x,takeoff.y),z=-5.55,height=-.1).items():mat[f'{kind}_{k}']=s
    for k,s in mat.items():
        report[k]=dict(valid=valid(s),solids=len(s.Solids()),volume_mm3=s.Volume(),
            protected_mm3=sum(iv(s,p) for p in pz.values()),frame_mm3=iv(s,frame),
            supported_pre_roll_boundary_mm3=iv(s,boundary))
    cq.exporters.export(cq.Compound.makeCompound(list(mat.values())),str(out/'treatment_interface_material.step'))
    cq.exporters.export(cq.Compound.makeCompound(list(ref.values())),str(out/'treatment_interface_reference.step'))
    (out/'treatment_interface_report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps(report,indent=2))
