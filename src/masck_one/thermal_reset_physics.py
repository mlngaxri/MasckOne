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

    def __post_init__(self):
        values={k:v for k,v in asdict(self).items() if k!='store'}
        finite(**values)
        signed={'imposed_load_delta_K','ambient_delta_K','initial_plate_delta_K',
                'initial_store_enthalpy_J'}
        if any(v < 0 for k,v in values.items() if k not in signed):
            raise ValueError('negative capacity, mass, conductance or heat source')
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
        # Columns connect to the edge region. A 65/35 heater distribution is an
        # explicit nonuniform DOE, not a prediction of actual foil trace density.
        return [(power*.65+qloadC+qairC-qce-qcs-qback/2)/C,
                (power*.35+qloadE+qairE+qce-qst-qback/2)/C,qcs/p.sensor_heat_capacity_J_K,
                qst+p.motor_to_store_W,(qback-qba)/p.back_heat_capacity_J_K,
                power,qloadC+qloadE,qairC+qairE-qba,p.motor_to_store_W,qback]
    out=[];samples=[];time=0.;peak_gradient=0.;peak_sensor_lag=0.;exhaustion=None
    for label,duration,power in phases:
        count=math.ceil(duration/step_s);dt=duration/count;phase_start=list(y)
        for index in range(count):
            a=rate(y,power);b=rate([v+dt*k/2 for v,k in zip(y,a)],power)
            c=rate([v+dt*k/2 for v,k in zip(y,b)],power)
            d=rate([v+dt*k for v,k in zip(y,c)],power)
            y=[v+dt*(i+2*j+2*k+l)/6 for v,i,j,k,l in zip(y,a,b,c,d)]
            time+=dt
            peak_gradient=max(peak_gradient,abs(y[0]-y[1]))
            peak_sensor_lag=max(peak_sensor_lag,abs(y[0]-y[2]))
            if exhaustion is None and y[3]>=p.store.capacity_J:
                exhaustion=time
            if index % max(1,round(5/dt))==0:
                samples.append(dict(phase=label,time_s=time,plate_delta_K=(y[0]+y[1])/2,
                    center_delta_K=y[0],edge_delta_K=y[1],store_enthalpy_J=y[3]))
        out.append(dict(phase=label,time_s=time,plate_delta_K=(y[0]+y[1])/2,
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
