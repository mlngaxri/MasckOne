"""Energy-conserving OFF-FACE fixture model. No human-use settings or controller.

All transport, material and imposed-load values are study inputs. CAD supplies
volumes and areas; neither calculated capacity nor a positive reserve is evidence
of skin performance. Each cheek has an independent enthalpy state.
"""
from dataclasses import dataclass, asdict
import math

DEWPOINT_SOURCE = 'https://sensirion.com/file/datasheet_sht7x'
TEC_SOURCE = 'https://tark-solutions.com/sites/default/files/ckfinder/files/resources/Handbooks/Thermoelectric-Handbook-1120.pdf'


def finite(**values):
    for key, value in values.items():
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError(f'{key} must be finite numeric input')


def dewpoint_screen(ambient_C, RH_percent, surface_C, uncertainty_K):
    finite(ambient_C=ambient_C, RH_percent=RH_percent, surface_C=surface_C,
           uncertainty_K=uncertainty_K)
    if not 0 <= ambient_C <= 50 or not 0 < RH_percent <= 100 or uncertainty_K < 0:
        raise ValueError('outside above-water approximation domain')
    gamma = math.log(RH_percent / 100) + 17.62 * ambient_C / (243.12 + ambient_C)
    dp = 243.12 * gamma / (17.62 - gamma)
    margin = surface_C - dp
    state = ('NO_CONDENSATION_EXPECTED_FROM_MODEL' if margin > uncertainty_K else
             'CONDENSATION_LIKELY' if margin < -uncertainty_K else 'CONDENSATION_POSSIBLE')
    return dict(dewpoint_C=dp, surface_minus_dewpoint_K=margin, state=state,
                human_temperature_limit=False, local_wet_microclimate_verified=False)


@dataclass(frozen=True)
class Store:
    cavity_mm3: float
    liquid_density_g_ml: float
    fill_fraction: float
    planning_latent_J_g: float
    specific_heat_J_gK: float
    shell_heat_capacity_J_K: float
    phase_band_K: float

    def __post_init__(self):
        finite(**asdict(self))
        if min(asdict(self).values()) <= 0 or self.fill_fraction > 1:
            raise ValueError('positive store inputs; fill cannot exceed cavity')

    @property
    def mass_g(self):
        return self.cavity_mm3 / 1000 * self.liquid_density_g_ml * self.fill_fraction

    @property
    def sensible_J_K(self):
        return self.mass_g * self.specific_heat_J_gK + self.shell_heat_capacity_J_K

    @property
    def capacity_J(self):
        return self.mass_g * self.planning_latent_J_g

    def temperature_above_solidus_K(self, enthalpy_J):
        # H=0 at solidus; phase band includes shell/PCM sensible energy.
        band_capacity = self.capacity_J + self.sensible_J_K * self.phase_band_K
        if enthalpy_J < 0:
            return enthalpy_J / self.sensible_J_K
        if enthalpy_J <= band_capacity:
            return enthalpy_J / band_capacity * self.phase_band_K
        return self.phase_band_K + (enthalpy_J - band_capacity) / self.sensible_J_K


@dataclass(frozen=True)
class FixtureInputs:
    store: Store
    plate_heat_capacity_J_K: float
    wet_water_equivalent_g: float
    water_cp_J_gK: float
    imposed_load_delta_K: float
    load_conductance_W_K: float
    plate_center_edge_W_K: float
    plate_store_W_K: float
    plate_ambient_W_K: float
    plate_back_W_K: float
    back_ambient_W_K: float
    back_heat_capacity_J_K: float
    sensor_heat_capacity_J_K: float
    sensor_plate_W_K: float
    ambient_delta_K: float
    initial_plate_delta_K: float
    initial_store_enthalpy_J: float
    motor_to_store_W: float
    heater_center_fraction: float=.2

    def __post_init__(self):
        values={k:v for k,v in asdict(self).items() if k!='store'}
        finite(**values)
        signed={'imposed_load_delta_K','ambient_delta_K','initial_plate_delta_K',
                'initial_store_enthalpy_J'}
        if any(v < 0 for k,v in values.items() if k not in signed):
            raise ValueError('negative capacity, mass, conductance or heat source')
        if self.heater_center_fraction>1:raise ValueError('invalid spatial heater fraction')
        if min(self.plate_heat_capacity_J_K,self.back_heat_capacity_J_K,
               self.sensor_heat_capacity_J_K,self.plate_center_edge_W_K,
               self.plate_store_W_K,self.sensor_plate_W_K) <= 0:
            raise ValueError('positive dynamic capacities and conductive paths required')


def transient(inputs: FixtureInputs, phases, step_s=0.02):
    """Coupled five-node enthalpy balance using fixed-step RK4.

    Phases are (label, duration_s, electrical_heat_W). A nonnegative imposed
    heater heat source is a boundary condition, not an electrical build recipe.
    Temperatures are DELTAS from a user-supplied material solidus, not setpoints.
    """
    finite(step_s=step_s)
    if not 0 < step_s <= 0.05:
        raise ValueError('step outside validated integration range')
    for label,duration,power in phases:
        finite(duration_s=duration,power_W=power)
        if duration <= 0 or power < 0 or not isinstance(label,str):
            raise ValueError('invalid thermal phase')
    p=inputs
    C=(p.plate_heat_capacity_J_K+p.wet_water_equivalent_g*p.water_cp_J_gK)/2
    # Stability is checked against the fastest lumped time constant.
    min_tau=min(C/(p.plate_center_edge_W_K+p.plate_store_W_K+p.load_conductance_W_K+
                     p.plate_ambient_W_K+p.plate_back_W_K+p.sensor_plate_W_K),
                p.sensor_heat_capacity_J_K/p.sensor_plate_W_K,
                p.back_heat_capacity_J_K/max(p.plate_back_W_K+p.back_ambient_W_K,1e-12))
    if step_s > min_tau/4:
        raise ValueError('time step must resolve fastest thermal node')
    # state: center, edge, sensor, store enthalpy, back, cumulative energy terms
    y=[p.initial_plate_delta_K]*3+[p.initial_store_enthalpy_J,p.ambient_delta_K]+[0.]*5
    initial_energy=C*(y[0]+y[1])+p.sensor_heat_capacity_J_K*y[2]+y[3]+p.back_heat_capacity_J_K*y[4]
    def rate(s,power):
        center,edge,sensor,H,back=s[:5]
        storeT=p.store.temperature_above_solidus_K(H)
        qce=p.plate_center_edge_W_K*(center-edge)
        qcs=p.sensor_plate_W_K*(center-sensor)
        qst=p.plate_store_W_K*(edge-storeT)
        qloadC=p.load_conductance_W_K/2*(p.imposed_load_delta_K-center)
        qloadE=p.load_conductance_W_K/2*(p.imposed_load_delta_K-edge)
        qairC=p.plate_ambient_W_K/2*(p.ambient_delta_K-center)
        qairE=p.plate_ambient_W_K/2*(p.ambient_delta_K-edge)
        qback=p.plate_back_W_K*((center+edge)/2-back)
        qba=p.back_ambient_W_K*(back-p.ambient_delta_K)
        # Selected foil study places 60% near columns, with 40% distributed.
        # Two-node approximation maps that to 20% center / 80% edge heating.
        return [(power*p.heater_center_fraction+qloadC+qairC-qce-qcs-qback/2)/C,
                (power*(1-p.heater_center_fraction)+qloadE+qairE+qce-qst-qback/2)/C,qcs/p.sensor_heat_capacity_J_K,
                qst+p.motor_to_store_W,(qback-qba)/p.back_heat_capacity_J_K,
                power,qloadC+qloadE,qairC+qairE-qba,p.motor_to_store_W,qback]
    out=[];samples=[];time=0.;peak_gradient=0.;peak_sensor_lag=0.;exhaustion=None
    for label,duration,power in phases:
        count=math.ceil(duration/step_s);dt=duration/count;phase_start=list(y);trajectory=[]
        for index in range(count):
            a=rate(y,power);b=rate([v+dt*k/2 for v,k in zip(y,a)],power)
            c=rate([v+dt*k/2 for v,k in zip(y,b)],power)
            d=rate([v+dt*k for v,k in zip(y,c)],power)
            y=[v+dt*(i+2*j+2*k+l)/6 for v,i,j,k,l in zip(y,a,b,c,d)]
            time+=dt
            trajectory.append(((index+1)*dt,(y[0]+y[1])/2))
            peak_gradient=max(peak_gradient,abs(y[0]-y[1]))
            peak_sensor_lag=max(peak_sensor_lag,abs(y[0]-y[2]))
            if exhaustion is None and y[3]>=p.store.capacity_J:
                exhaustion=time
            if index % max(1,round(5/dt))==0:
                samples.append(dict(phase=label,time_s=time,plate_delta_K=(y[0]+y[1])/2,
                    center_delta_K=y[0],edge_delta_K=y[1],store_enthalpy_J=y[3]))
        start_mean=(phase_start[0]+phase_start[1])/2;end_mean=(y[0]+y[1])/2
        target=start_mean+.9*(end_mean-start_mean);direction=1 if end_mean>start_mean else -1
        endpoint_response=next((t for t,v in trajectory if direction*(v-target)>=0),None)
        out.append(dict(phase=label,time_s=time,plate_delta_K=end_mean,
                        time_to_90_percent_of_phase_endpoint_change_s=endpoint_response,
                        response_definition='PHASE_ENDPOINT_CHANGE_NOT_ASYMPTOTIC_OR_HUMAN_RESPONSE',
                        store_delta_K=p.store.temperature_above_solidus_K(y[3]),
                        store_enthalpy_J=y[3],latent_planning_margin_J=p.store.capacity_J-y[3],
                        imposed_load_to_plate_J=y[6]-phase_start[6],
                        heater_energy_J=y[5]-phase_start[5],backside_energy_J=y[9]-phase_start[9]))
    final_energy=C*(y[0]+y[1])+p.sensor_heat_capacity_J_K*y[2]+y[3]+p.back_heat_capacity_J_K*y[4]
    energy_residual=final_energy-initial_energy-sum(y[5:9])
    return dict(phases=out,transient_samples=samples,heater_energy_J=y[5],load_energy_J=y[6],ambient_energy_J=y[7],
                motor_energy_J=y[8],energy_balance_residual_J=energy_residual,
                peak_center_edge_gradient_K=peak_gradient,peak_sensor_lag_K=peak_sensor_lag,
                sensor_time_constant_s=p.sensor_heat_capacity_J_K/p.sensor_plate_W_K,
                store_exhaustion_s=exhaustion,reset_energy_to_solidus_J=max(0.,y[3]),
                input_status='ASSUMED_OFF_FACE_BOUNDARY_CONDITIONS',human_use_eligible=False)


def dock_reset(energy_J,store_above_ambient_K,contact_area_mm2,contact_h_W_m2K,
               sink_area_m2,ambient_h_W_m2K,fin_efficiency,store_internal_K_W,
               charging_heat_into_sink_W=0.):
    finite(**locals())
    if energy_J<0 or min(contact_area_mm2,contact_h_W_m2K,sink_area_m2,ambient_h_W_m2K,
                         fin_efficiency)<=0 or fin_efficiency>1 or store_internal_K_W<0 or charging_heat_into_sink_W<0:
        raise ValueError('invalid dock energy/transport input')
    Rc=1/(contact_area_mm2*1e-6*contact_h_W_m2K)
    Rs=1/(sink_area_m2*ambient_h_W_m2K*fin_efficiency)
    driving=store_above_ambient_K-charging_heat_into_sink_W*Rs
    if driving<=0:
        return dict(state='PASSIVE_RESET_IMPOSSIBLE_AT_BOUNDARY',reset_s=None,
                    contact_K_W=Rc,sink_K_W=Rs,active_off_face_sink_required=True)
    q=driving/(Rc+Rs+store_internal_K_W)
    return dict(state='LATENT_PLATEAU_ESTIMATE_ONLY',plateau_heat_W=q,reset_s=energy_J/q,
                contact_K_W=Rc,sink_K_W=Rs,active_off_face_sink_required=False,
                solidus_endpoint_verified=False,final_sensible_cooldown_not_included=True)


def architecture_trade(per_cheek_heat_J,duration_s,cop,store_delta_K):
    finite(**locals())
    if min(per_cheek_heat_J,duration_s,cop,store_delta_K)<=0:raise ValueError('positive trade inputs')
    return dict(sensible_aluminum_mass_g_DOE=per_cheek_heat_J/(.9*store_delta_K),
                sensible_water_mass_g_DOE=per_cheek_heat_J/(4.18*store_delta_K),
                TEC_electrical_J=per_cheek_heat_J/cop,
                TEC_hot_store_J=per_cheek_heat_J*(1+1/cop),
                TEC_hot_W=per_cheek_heat_J*(1+1/cop)/duration_s,
                passive_latent_electrical_J=0.,
                selection='PASSIVE_LATENT_WITH_THROTTLED_SHARED_PLATE_FOR_OFF_FACE_COMPARISON',
                production_V1_selection='BLOCKED_CONTACT_IMPEDANCE_PCM_AND_PACKAGE_VALIDATION')


def local_energy_budget(capacities_J,required_J):
    """Planning acceptance is per store. Global spare energy cannot cross cheeks."""
    if not capacities_J or set(capacities_J)!=set(required_J):
        raise ValueError('exact same nonempty store identities required')
    finite(**capacities_J);finite(**required_J)
    if min(capacities_J.values())<=0 or min(required_J.values())<0:
        raise ValueError('invalid energy budget')
    margins={k:capacities_J[k]-required_J[k] for k in capacities_J}
    return dict(margins_J=margins,minimum_margin_J=min(margins.values()),
                global_margin_J=sum(margins.values()),all_stores_have_planning_reserve=min(margins.values())>=0,
                physical_readiness=False)


def plate_field(*,width_mm,height_mm,thickness_mm,conductivity_W_mK,heater_W,
                heater_width_mm,heater_height_mm,post_xy_mm,total_store_W_K,
                store_delta_K,load_W_K,load_delta_K,ambient_W_K,ambient_delta_K,
                nx=22,ny=28,post_heater_fraction=0.,post_width_mm=.92):
    """Steady finite-volume sheet screen, adiabatic perimeter, distributed load.

    Conductive columns are attached to their actual nearest cells. Total transfer
    conductance includes the downstream PCM resistance. This is a 2D thin-sheet
    architecture screen, not 3D contact/temperature or hotspot validation.
    """
    import numpy as np
    finite(width_mm=width_mm,height_mm=height_mm,thickness_mm=thickness_mm,
           conductivity_W_mK=conductivity_W_mK,heater_W=heater_W,
           total_store_W_K=total_store_W_K,store_delta_K=store_delta_K,load_W_K=load_W_K,
           load_delta_K=load_delta_K,ambient_W_K=ambient_W_K,ambient_delta_K=ambient_delta_K,
           heater_width_mm=heater_width_mm,heater_height_mm=heater_height_mm,post_heater_fraction=post_heater_fraction,post_width_mm=post_width_mm)
    if post_width_mm<=0:raise ValueError('positive post footprint required')
    if not 0<=post_heater_fraction<=1:raise ValueError('heater split must be a fraction')
    if min(width_mm,height_mm,thickness_mm,conductivity_W_mK,total_store_W_K,heater_width_mm,heater_height_mm)<=0:
        raise ValueError('positive geometry and conductive paths required')
    if min(heater_W,load_W_K,ambient_W_K)<0 or type(nx) is not int or type(ny) is not int or min(nx,ny)<2 or not post_xy_mm:
        raise ValueError('invalid finite volume inputs')
    dx=width_mm/nx;dy=height_mm/ny;N=nx*ny
    xs=(np.arange(nx)+.5)*dx-width_mm/2;ys=(np.arange(ny)+.5)*dy-height_mm/2
    A=np.zeros((N,N));b=np.zeros(N)
    gx=conductivity_W_mK*thickness_mm*.001*dy/dx
    gy=conductivity_W_mK*thickness_mm*.001*dx/dy
    heater_indices=[j*nx+i for j,y in enumerate(ys) for i,x in enumerate(xs)
                    if abs(x)<heater_width_mm/2 and abs(y)<heater_height_mm/2]
    if not heater_indices:raise ValueError('heater unresolved on grid')
    for j in range(ny):
        for i in range(nx):
            n=j*nx+i
            A[n,n]+=(load_W_K+ambient_W_K)/N
            b[n]+=(load_W_K*load_delta_K+ambient_W_K*ambient_delta_K)/N
            for ii,jj,g in [(i+1,j,gx),(i,j+1,gy)]:
                if ii<nx and jj<ny:
                    m=jj*nx+ii;A[n,n]+=g;A[m,m]+=g;A[n,m]-=g;A[m,n]-=g
    near_posts=[j*nx+i for j,y in enumerate(ys) for i,x in enumerate(xs)
                if j*nx+i in heater_indices and any(1.0<math.hypot(x-a,y-c)<3.0 for a,c in post_xy_mm)]
    if post_heater_fraction and not near_posts:raise ValueError('post heater region unresolved')
    for n in heater_indices:b[n]+=heater_W*(1-post_heater_fraction)/len(heater_indices)
    for n in near_posts:b[n]+=heater_W*post_heater_fraction/len(near_posts)
    post_weights=[]
    for x,y in post_xy_mm:
        finite(x=x,y=y)
        if abs(x)>=width_mm/2 or abs(y)>=height_mm/2:raise ValueError('post outside plate')
        half=post_width_mm/2
        weights=[]
        for j,yc in enumerate(ys):
            oy=max(0.,min(y+half,yc+dy/2)-max(y-half,yc-dy/2))
            for i,xc in enumerate(xs):
                ox=max(0.,min(x+half,xc+dx/2)-max(x-half,xc-dx/2))
                if ox*oy>0:weights.append((j*nx+i,ox*oy/post_width_mm**2))
        if abs(sum(w for n,w in weights)-1)>1e-8:raise ValueError('post footprint not contained')
        for n,w in weights:
            g=total_store_W_K/len(post_xy_mm)*w;A[n,n]+=g;b[n]+=g*store_delta_K
            post_weights.append((n,g))
    T=np.linalg.solve(A,b)
    store_heat=sum(g*(T[n]-store_delta_K) for n,g in post_weights)
    load_heat=load_W_K*(load_delta_K-float(T.mean()))
    air_heat=ambient_W_K*(ambient_delta_K-float(T.mean()))
    return dict(mean_delta_K=float(T.mean()),max_minus_min_K=float(T.max()-T.min()),
                maximum_delta_K=float(T.max()),minimum_delta_K=float(T.min()),
                store_heat_W=store_heat,load_heat_W=load_heat,
                balance_residual_W=heater_W+load_heat+air_heat-store_heat,
                temperature_delta_grid_K=T.reshape(ny,nx).tolist(),grid_shape=[nx,ny])
