"""Offset-output and sensor observability model for inert fixtures only."""
from treatment_geometry import *
from mounted_station import station
from treatment_physics import diaphragm_stiffness

def study():
    K=diaphragm_stiffness(-7.5,True,1,.05,n=36)+diaphragm_stiffness(8,False,-1,.05,n=36)
    C=np.linalg.inv(K);rows=[]
    for kind,c in STATION_POSES.items():
        mat,ref=station(kind,c)
        p=ref['output_shoe_center'].translate(tuple(-x for x in c)).rotate((0,0,0),(0,1,0),-61).Center()
        lever=np.array(p.toTuple())
        # Actuator force cancels the net axial preload, not its offset bending moment.
        wrench=np.r_[np.zeros(3),np.cross(lever,np.array([0.,0.,.2]))]
        q=C@wrench;tilt=float(np.linalg.norm(q[3:5]))
        # Area integration of both electrodes. Average capacitance rejects first-order
        # tilt; differential channel detects one tilt component, not two independent tilts.
        xyz=[];weights=[]
        for radius in np.linspace(3.7,5.9,121):
            for theta in np.linspace(0,2*math.pi,360,endpoint=False):
                x,y=radius*math.cos(theta),radius*math.sin(theta)
                if abs(x)>=.1:xyz.append((x,y));weights.append(radius)
        xy=np.array(xyz);w=np.array(weights);errors=[]
        for position in (-.26,0,.26):
            gap=.545-position
            actual_gap=gap-(q[3]*xy[:,1]-q[4]*xy[:,0])
            apparent_gap=1/np.average(1/actual_gap,weights=w)
            errors.append(dict(position_mm=position,tilt_induced_position_bias_mm=gap-apparent_gap,
                minimum_local_gap_mm=float(min(actual_gap))))
        # Local closed-section arm is a conservative cantilever idealization.
        I=(1.4*1.0**3-1.0*.6**3)/12
        arm_deflection=.2*10**3/(3*200000*I)
        radial_demand=.05+16.5*math.tan(math.radians(.2))+np.linalg.norm(q[:2])+16*tilt
        rows.append(dict(station=kind,output_lever_mm=lever.tolist(),residual_wrench_N_Nmm=wrench.tolist(),
            linear_response_mm_rad=q.tolist(),tilt_rad=tilt,
            supplier_radial_gap_mm=.25,radial_error_scenario_mm=radial_demand,
            radial_gap_remaining_mm=.25-radial_demand,
            sensor_average_bias=errors,arm_deflection_at_0p2N_mm=arm_deflection,
            alignment_seeds=dict(offset_mm=.05,angle_deg=.2),
            limitations=['ideal rigid diaphragm clamps','linear beam stiffness only',
                'offset arm inertia and frame modes require assembled modal analysis',
                'sensor fringing, parasitic capacitance, noise and wet drift unmeasured']))
    result=dict(cases=rows,physical_validation=False,scope='INERT_BENCH_DESIGN_MODEL')
    Path('studies/mounted_wrench_results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':study()
