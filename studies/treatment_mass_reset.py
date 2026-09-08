"""Provisional mass contributions and PCM phase timescale; no whole-product closure."""
from treatment_geometry import *
from treatment_interfaces import thermal_interfaces
from mounted_station import station

def study():
    thermal,refs=thermal_interfaces();rows=[]
    # Density seeds by proposed role, not supplier/process qualification.
    for k,s in thermal.items():
        if k.startswith(('cell_fin_base','fixed_folded_bus','cheek_spreader')):rho=.00889;basis='C110 copper source'
        elif k.startswith('heater_foil'):rho=.008;basis='resistive-alloy DOE'
        elif k.startswith('insulation'):rho=.0001;basis='insulation density DOE, process unselected'
        else:rho=.0013;basis='polymer/TIM laminate DOE, process unselected'
        rows.append(dict(id=k,mass_g=s.Volume()*rho,z_mm=s.Center().z,basis=basis))
    for k,s in refs.items():
        if k.startswith('pcm_void'):rows.append(dict(id=k,mass_g=s.Volume()/1000*.875*.77,z_mm=s.Center().z,basis='RT28HC liquid-density and fill-fraction planning assumption'))
        if k.startswith('tec_package'):rows.append(dict(id=k,mass_g=s.Volume()*.0045,z_mm=s.Center().z,basis='effective TEC density DOE, actual module mass unknown'))
    for kind,c in STATION_POSES.items():
        mat,ref=station(kind,c)
        for k,s in mat.items():
            if k.startswith('position_electrode_dielectric'):rho=.0013
            elif k.startswith('position_electrode'):rho=.00889
            elif 'buffer' in k:rho=.0012
            else:rho=.0079
            # Two representative stations mirrored in the four-zone mass estimate.
            rows.append(dict(id=kind+'_'+k,mass_g=2*s.Volume()*rho,z_mm=s.Center().z,basis='mirrored geometry; steel/polymer role density DOE'))
        rows.append(dict(id=kind+'_actuator_pair',mass_g=2*5.7,z_mm=c[2]-1.0,basis='H2W total actuator mass; axial CG offset is an assumption'))
    mass=sum(r['mass_g'] for r in rows);z=sum(r['mass_g']*r['z_mm'] for r in rows)/mass
    # Longest idealized un-finned PCM gap: 1mm above the fin tips, plus half pitch.
    distance=math.hypot(1.0,(19-1.2)/15/2)/1000
    phase=[dict(freezing_drive_DOE_K=d,one_dimensional_phase_front_timescale_s=840*201250*distance**2/(2*.2*d)) for d in (1,2,4)]
    result=dict(items=rows,estimated_treatment_contribution_g=mass,estimated_contribution_CG_z_mm=z,
        excludes=['frame base','outer shell','battery','other fluidics','retention','thermal brackets','harness','qualified screws/adhesives'],
        whole_product_mass_or_CG_closed=False,
        mechanical_envelope='17.4mm cassette diameter; 18mm main cage span; rear saddle reaches z=-7.4; output face z=-6.6; mounting fastener reservations extend beyond the cage',
        thermal_envelope='distributed store to z=17.2 including insulation; stationary contact barrier to z=-3.925; local heating laminate adds 0.10mm behind plate',
        phase_front_timescale=phase,reset_note='Energy divided by net extraction is an ideal lower time. Phase completion and contact equilibration require additional evidence.',
        physical_validation=False)
    Path('studies/treatment_mass_reset_results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':study()
