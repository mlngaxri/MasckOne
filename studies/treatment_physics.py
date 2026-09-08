"""Architecture calculations for inert bench loads, not facial-use settings."""
import json, math
from pathlib import Path
import numpy as np
from scipy.linalg import eigh


def beam(a,b,E,G,w,t):
    d=b-a;L=np.linalg.norm(d);ex=d/L;ez=np.array((0.,0.,1.));ey=np.cross(ez,ex)
    R=np.vstack((ex,ey,ez));T=np.zeros((12,12))
    for i in range(4):T[i*3:i*3+3,i*3:i*3+3]=R
    A=w*t;Iy=w*t**3/12;Iz=t*w**3/12;J=w*t**3/3*(1-.63*t/w)
    K=np.zeros((12,12))
    for ids,k in [([0,6],E*A/L),([3,9],G*J/L)]:K[np.ix_(ids,ids)]+=k*np.array([[1,-1],[-1,1]])
    kb=np.array([[12,6*L,-12,6*L],[6*L,4*L*L,-6*L,2*L*L],[-12,-6*L,12,-6*L],[6*L,2*L*L,-6*L,4*L*L]])
    K[np.ix_([1,5,7,11],[1,5,7,11])]+=E*Iz/L**3*kb
    sign=np.diag((1,-1,1,-1))
    K[np.ix_([2,4,8,10],[2,4,8,10])]+=E*Iy/L**3*(sign@kb@sign)
    return T.T@K@T


def diaphragm_stiffness(z,reverse=False,hand=1,t=.06,w=.4,n=18):
    # The two rigid boundaries are the actual inner hub and outer rim.
    # Condense all curved-arm internal DOFs, retaining a common output's six DOFs.
    total=np.zeros((6,6))
    for phase in (0,2*math.pi/3,4*math.pi/3):
        s=np.linspace(0,1,n+1);rad=6.95+(2.85-6.95)*s;ang=phase+hand*math.radians(110)*s
        p=np.array([rad*np.cos(ang),rad*np.sin(ang),np.full(n+1,z)]).T
        K=np.zeros((6*(n+1),6*(n+1)))
        for i in range(n):
            ids=list(range(i*6,(i+2)*6));K[np.ix_(ids,ids)]+=beam(p[i],p[i+1],200000,200000/2.6,w,t)
        moving=0 if reverse else n;fixed=n if reverse else 0
        internal=[i for i in range(6*(n+1)) if i//6 not in (moving,fixed)]
        edge=list(range(moving*6,moving*6+6))
        condensed=K[np.ix_(edge,edge)]-K[np.ix_(edge,internal)]@np.linalg.solve(K[np.ix_(internal,internal)],K[np.ix_(internal,edge)])
        x,y,zz=p[moving];skew=np.array([[0,-zz,y],[zz,0,-x],[-y,x,0.]])
        B=np.eye(6);B[:3,3:]=-skew
        total+=B.T@condensed@B
    return total


def mechanical_study():
    rows=[]
    for thickness in (.04,.05,.06,.07):
        K=diaphragm_stiffness(-7.5,True,1,thickness)+diaphragm_stiffness(8.,False,-1,thickness)
        C=np.linalg.inv(K);mass=.0027
        M=np.diag([mass/1000]*3+[mass*30/1000,mass*30/1000,mass*25/1000])
        freqs=np.sqrt(np.maximum(eigh(K,M,eigvals_only=True),0))/(2*math.pi)
        q=C@np.array([0,0,.2,0,0,0])
        k=1/C[2,2];amp=.26;omega=2*math.pi*40
        free_force=abs(k-mass/1000*omega**2)*amp
        rows.append(dict(thickness_mm=thickness,stiffness_6dof=K.tolist(),
            axial_stiffness_N_per_mm=k,radial_stiffness_N_per_mm=[1/C[0,0],1/C[1,1]],
            eigenfrequencies_Hz=freqs.tolist(),coupled_response_to_axial_0p2N=q.tolist(),
            free_space_drive_force_peak_N=free_force,
            conservative_force_with_0p2N_load_N=.2+free_force,
            force_reference_continuous_N=.27,
            thermal_bridge_in_motion=False,
            projected_stroke_pp_mm=[.52*math.sin(math.radians(61)),.52*math.cos(math.radians(61))],
            moving_mass_assumption_g=mass*1000,physical_validation=False))
    return rows


def thermal_study():
    # RT28HC supplier total enthalpy is over 21..36 C, NOT pure latent heat.
    total_low=250000*(1-.075);sensible=2000*(36-21)
    latent_planning=total_low-sensible
    # Geometry targets, not an actual retained/encapsulated PCM qualification.
    pcm_volume_cm3=6*(10*14.6*11-8*.05*14.6*10)/1000*.875
    pcm_mass_kg=pcm_volume_cm3*.77/1000
    useful=pcm_mass_kg*latent_planning*.7
    rows=[]
    for load in (.5,1.,2.,4.):
        for cop in (.35,.6,1.,1.5):
            pin=load/cop;hot=load+pin
            for ambient_difference in (0,4,8):
                leak=.03*.006/.0012*ambient_difference # explicit insulation DOE
                energy=(hot+leak)*180+20
                rows.append(dict(total_bench_cooling_W=load,cop_assumption=cop,
                    electrical_W=pin,hot_side_W=hot,ambient_delta_K=ambient_difference,
                    insulation_leak_W=leak,energy_180s_J=energy,
                    initial_cooling_allocation_J=useful*.6,
                    margin_J=useful*.6-energy,physical_performance_proven=False))
    air=[]
    for q in (1,2,4):
        hot=2*q
        air.append(dict(cooling_W=q,assumed_COP=1,heat_to_air_W=hot,
            required_exposed_area_m2_at_h5_delta5=hot/25,
            rise_K_on_0p02m2_at_h5=hot/(5*.02)))
    return dict(pcm_nominal_melting_range_C=[27,29],supplier_total_enthalpy_range_C=[21,36],
        low_total_enthalpy_J_kg=total_low,sensible_subtraction_J_kg=sensible,
        derived_latent_planning_J_kg=latent_planning,usable_fraction_assumption=.7,
        pcm_volume_cm3=pcm_volume_cm3,pcm_mass_g=pcm_mass_kg*1000,
        available_planning_energy_J=useful,initial_solid_fraction_assumption=.6,
        cases=rows,air_sink_rejection=air,
        verdict='THERMAL_BUFFER_ARCHITECTURE_REQUIRES_LOAD_COP_LEAK_AND_STATE_OF_CHARGE_GATES',
        source='https://www.rubitherm.eu/media/products/datasheets/Techdata_-RT28HC_EN_21012026.PDF')

if __name__=='__main__':
    r=dict(mechanical=mechanical_study(),thermal=thermal_study(),evidence='LINEAR_BEAM_AND_LUMPED_ENERGY_DESIGN_STUDY_NOT_PHYSICAL_VALIDATION')
    out=Path('studies/treatment_physics_results.json');out.write_text(json.dumps(r,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'mechanical':[{k:v for k,v in x.items() if k!='stiffness_6dof'} for x in r['mechanical']],
                      'thermal':{k:v for k,v in r['thermal'].items() if k!='cases'}},indent=2))
