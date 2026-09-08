"""Beam sensitivity and local stress demand; no allowable or fatigue qualification."""
import json,math
from pathlib import Path
import numpy as np
from treatment_physics import beam,diaphragm_stiffness

def arm_stress(t=.05,n=36,reverse=False,hand=1,stroke=.26):
 s=np.linspace(0,1,n+1);r=6.95-4.1*s;a=hand*math.radians(110)*s
 p=np.array([r*np.cos(a),r*np.sin(a),np.zeros(n+1)]).T
 K=np.zeros((6*(n+1),6*(n+1)))
 for i in range(n):
  ids=list(range(i*6,(i+2)*6));K[np.ix_(ids,ids)]+=beam(p[i],p[i+1],200000,200000/2.6,.4,t)
 moving=0 if reverse else n;fixed=n if reverse else 0
 edge=list(range(moving*6,moving*6+6));inside=[i for i in range(6*(n+1)) if i//6 not in (moving,fixed)]
 q=np.zeros(6*(n+1));q[edge[2]]=stroke
 q[inside]=np.linalg.solve(K[np.ix_(inside,inside)],-K[np.ix_(inside,edge)]@q[edge])
 peak=0;loc=None
 for i in range(n):
  d=p[i+1]-p[i];ex=d/np.linalg.norm(d);ez=np.array([0,0,1.]);ey=np.cross(ez,ex);R=np.vstack((ex,ey,ez))
  f=beam(p[i],p[i+1],200000,200000/2.6,.4,t)@q[i*6:(i+2)*6]
  for end in (0,1):
   force=R@f[end*6:end*6+3];moment=R@f[end*6+3:end*6+6]
   sig=abs(force[0])/(.4*t)+abs(moment[1])*t/2/(.4*t**3/12)+abs(moment[2])*.4/2/(t*.4**3/12)
   tau=3*abs(moment[0])/(.4*t*t);vm=math.sqrt(sig*sig+3*tau*tau)
   if vm>peak:peak=vm;loc=[i,end]
 return dict(peak_equivalent_beam_stress_MPa=peak,element_end=loc,notch_factor_included=False,
   clamp_overlap_idealized=True,large_deflection=False)

def study():
 rows=[]
 for t in (.045,.05,.055):
  K=diaphragm_stiffness(-7.5,True,1,t,n=36)+diaphragm_stiffness(8,False,-1,t,n=36);C=np.linalg.inv(K)
  k=1/C[2,2]
  for mass in (2.2,2.7,3.2):
   rows.append(dict(foil_thickness_mm=t,moving_mass_scenario_g=mass,k_N_mm=k,
    free_axial_frequency_Hz=math.sqrt(k/(mass/1e6))/(2*math.pi),
    free_40Hz_force_amplitude_N=abs(k-(mass/1e6)*(2*math.pi*40)**2)*.26,
    radial_over_axial_ratio=(1/C[0,0])/k))
 return dict(cases=rows,arm_stress_36_elements=arm_stress(),arm_stress_72_elements=arm_stress(n=72),
   max_normal_stroke_kinetic_energy_microJ=.5*.0027*(.00026*2*math.pi*40)**2*1e6,
   force_budget_for_unmodelled_wet_boot_and_wires_N=.27-.2-.02503213444290509,
   fatigue_allowable=None,physical_validation=False)
if __name__=='__main__':
 r=study();Path('studies/flexure_robustness_results.json').write_text(json.dumps(r,indent=2,allow_nan=False)+'\n');print(json.dumps(r,indent=2))
