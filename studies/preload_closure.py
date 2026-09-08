"""Load/centering trade study for inert bench fixtures, not human loading advice."""
import json,math
from pathlib import Path
import numpy as np
from scipy.integrate import solve_ivp
from treatment_physics import diaphragm_stiffness


def centering_case(preload=.2,mass_g=2.7,thickness=.05):
 K=diaphragm_stiffness(-7.5,True,1,thickness)+diaphragm_stiffness(8,False,-1,thickness)
 C=np.linalg.inv(K);k=1/C[2,2];omega=2*math.pi*40;m=mass_g/1e6
 # Compare passive centering against a finite bidirectional command envelope.
 nominal_amplitude=.26;soft_onset=.35;center_allowance=soft_onset-nominal_amplitude
 passive_min_k=preload/center_allowance
 minimum_dynamic_force=abs(passive_min_k-m*omega**2)*nominal_amplitude
 # Inert-load simulation only. Center acquisition precedes stroke enable.
 # Controller numbers are design-study coefficients, not deployable firmware.
 kp=.7;kd=2*.8*math.sqrt(m*(k+kp));ki=35;force_limit=.27
 def rhs(t,y):
  x,v,integ=y
  f_unsat=-kp*x-kd*v-ki*integ
  f=np.clip(f_unsat,-force_limit,force_limit)
  dint=x if abs(f_unsat)<force_limit or x*f_unsat>0 else 0
  return [v,(f-k*x-preload)/m,dint]
 sol=solve_ivp(rhs,[0,.7],[0,0,0],max_step=.0001,rtol=1e-8,atol=1e-10)
 x=sol.y[0];idx=np.where(np.abs(x)>.02)[0];settle=sol.t[idx[-1]+1] if len(idx) and idx[-1]+1<len(sol.t) else None
 force=-kp*x-kd*sol.y[1]-ki*sol.y[2]
 # Offset shoe transfers an axial force with a real bending moment into both diaphragms.
 r=np.array([9.8,0,-9.1]);wrench=np.r_[np.array([0,0,preload]),np.cross(r,np.array([0,0,preload]))]
 q=C@wrench
 return dict(preload_scenario_N=preload,passive_offset_mm=preload/k,passive_minimum_centered_k_N_mm=passive_min_k,
   passive_minimum_40Hz_force_N=minimum_dynamic_force,continuous_motor_reference_N=.27,
   active_acquisition_peak_displacement_mm=float(max(abs(x))),active_acquisition_settle_to_20um_s=settle,
   active_acquisition_peak_force_N=float(max(abs(np.clip(force,-force_limit,force_limit)))),
   active_final_offset_mm=float(x[-1]),hard_stop_study_mm=.45,soft_stop_study_mm=soft_onset,
   normal_command_amplitude_mm=nominal_amplitude,
   force_for_steady_preload_N=preload,steady_coil_loss_W=(preload/.45)**2*1.5,
   offset_output_wrench_N_Nmm=wrench.tolist(),offset_output_response_mm_rad=q.tolist(),
   assumed_sensor_alignment_offset_mm=.05,assumed_angular_alignment_deg=.2,
   supplier_radial_air_gap_mm=.25,
   estimated_radial_error_mm=.05+16.5*math.tan(math.radians(.2))+abs(q[0])+8*abs(q[4]),
   controls_required=['noncontact displacement sensor','center acquisition before stroke','stroke ramp',
     'current saturation and anti-windup','centering-error amplitude derating','loss-of-signal quiet fault'],
   evidence='LUMPED_LINEAR_BENCH_MODEL_ONLY_NO_CONTROLLER_OR_SAFETY_VALIDATION')

if __name__=='__main__':
 rows=[centering_case(p) for p in (.05,.1,.2)]
 Path('studies/preload_closure_results.json').write_text(json.dumps(rows,indent=2,allow_nan=False)+'\n')
 print(json.dumps(rows,indent=2))
