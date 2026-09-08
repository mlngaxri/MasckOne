"""Architecture bounds for inert fixtures. Assumptions are not material qualification."""
import math,json
from pathlib import Path
import numpy as np
from scipy.optimize import brentq

def budget():
 m=2.7e-6;k=.07414875;w=2*math.pi*40;A=.26;F=.27;P=.2
 rows=[]
 for ks,c in [(0,0),(.02,.00015),(.08,.0003),(.2,.001)]:
  z=complex(k+ks-m*w*w,w*c);dynamic=A*abs(z)
  rows.append(dict(seal_stiffness_N_mm=ks,seal_damping_N_s_mm=c,static_preload_N=P,
    flexure_force_amplitude_N=k*A,inertial_force_amplitude_N=m*w*w*A,
    seal_elastic_amplitude_N=ks*A,seal_damping_amplitude_N=w*c*A,
    resultant_dynamic_force_N=dynamic,remaining_peak_force_N=F-P-dynamic,
    continuous_current_RMS_A=math.sqrt(P*P+dynamic*dynamic/2)/.45,
    copper_loss_W=1.5*(P*P+dynamic*dynamic/2)/.45**2,
    force_limited_amplitude_mm=(F-P)/abs(z)))
 # Passive-only spring has to absorb uncertain mean load within the 0.09 mm
 # center reserve. This forces stiffness far above the useful 40 Hz suspension.
 passive_k=P/(.35-A)
 # A constant-bias spring helps nominal load but cannot follow an unknown interval.
 hybrid=[dict(preload_N=p,bias_N=.1,required_active_bias_N=p-.1,
    DC_copper_W=((p-.1)/.45)**2*1.5) for p in (0,.1,.2)]
 # Shifting the neutral of the same guide is not free: stress/predeflection remain.
 neutral=.1/k
 # Straight thermal strap Pareto: k_bend/G = E*t^2/(k_thermal*L^2).
 # Four clamped-guided foils, required G=0.25 W/K, max .01 N at .26 mm.
 straps=[]
 E=110000 # copper elastic modulus DOE only, not a material allowable
 conductivity=.388 # W/(mm K), source C110 data used elsewhere
 for t in (.025,.05,.1):
  L=10;G=.25;b_total=G*L/(conductivity*t)
  stiffness=E*b_total*t**3/L**3
  straps.append(dict(foil_mm=t,span_mm=L,required_total_width_mm=b_total,
    conductance_W_K=G,added_axis_stiffness_N_mm=stiffness,extra_force_N=stiffness*A))
 # Capacitance uses actual electrode annulus minus central split, integrated area.
 r1,r2,a=3.7,5.9,.1
 def strip(r):return 2*(a*math.sqrt(r*r-a*a)+r*r*math.asin(a/r))
 area=math.pi*(r2*r2-r1*r1)-(strip(r2)-strip(r1));gap=.545
 capacitance_pf=8.8541878128e-3*area/gap
 return dict(force_cases=rows,pure_passive=dict(required_k_N_mm=passive_k,
    dynamic_force_N=abs(passive_k-m*w*w)*A,status='REJECTED_FOR_0.20N_SCENARIO'),
    hybrid_bias_cases=hybrid,adjustable_same_flexure_neutral_mm=neutral,
    adjustable_neutral_status='REJECT_SAME_GUIDE_PRESTRAIN; exceeds nominal travel and unqualified fatigue range',
    bistable_status='REJECTED_AS_PRIMARY_CENTERER; snap state and preload sensitivity conflict with a continuous quiet neutral',
    selected='ACTIVE_BIAS_PLUS_LIGHT_FLEXURE; waveform-subtracted slow trim; fixture impedance identification needed',
    moving_thermal_straps=straps,position_sensor=dict(total_active_area_mm2=area,
    nominal_gap_mm=gap,nominal_capacitance_pF=capacitance_pf,
    nominal_signal_for_2um_fF=capacitance_pf/gap*.002*1000,
    requirement='Demonstrate <=1ms total measured delay and <=2um RMS in the installed wet/dry enclosure; not implied by catalog sample rate'),
    disturbance_boundary='0.05N abrupt load step contacts soft stop in model; loss of full stroke must be detected and waveform withdrawn.',
    physical_validation=False)
if __name__=='__main__':
 r=budget();Path('studies/force_and_interface_budget_results.json').write_text(json.dumps(r,indent=2,allow_nan=False)+'\n');print(json.dumps(r,indent=2))
