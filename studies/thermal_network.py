"""Inert-load architecture selection; no human-use temperatures or controller code."""
import json,math
from pathlib import Path
import numpy as np
from scipy.optimize import brentq

# Ferrotec reference guide sec11: generic 71-couple/6A model scaled to18/1.2.
# This is a vendor-supported modeling method, not a tested curve for our assembly.
S=[.013345,-5.37574e-5,7.42731e-7,-1.27141e-9]
R=[2.08317,-1.98763e-2,8.53832e-5,-9.03143e-8]
K=[.476218,-3.89821e-6,-8.64864e-6,2.20869e-8]
def prop(coeff,a,b):
 if abs(b-a)<1e-8:return sum(c*a**i for i,c in enumerate(coeff))
 return sum(c*(b**(i+1)-a**(i+1))/(i+1)/(b-a) for i,c in enumerate(coeff))
def tec(i,tc,th):
 s=prop(S,tc,th)*18/71;r=prop(R,tc,th)*6/1.2*18/71;k=prop(K,tc,th)*1.2/6*18/71
 q=s*tc*i-.5*i*i*r-k*(th-tc);p=(s*(th-tc)+i*r)*i
 return q,p

def solve(q,delta,rc,rh):
 # Per-cell load; temperatures are bench boundary conditions derived from PCM datasheet.
 pcm=301.15;tc=pcm-delta-q*rc
 def residual(i):
  def hotbal(th):
   qc,p=tec(i,tc,th);return th-pcm-rh*(qc+p)
  th=brentq(hotbal,pcm-20,pcm+100);qc,p=tec(i,tc,th)
  return qc-q,th,p
 xs=np.linspace(0,1.2,121)
 for a,b in zip(xs[:-1],xs[1:]):
  if residual(a)[0]<0<=residual(b)[0]:
   i=brentq(lambda i:residual(i)[0],a,b);_,th,p=residual(i)
   return dict(electrical_W_per_cell=p,hot_W_per_cell=q+p,hot_rise_above_PCM_K=th-pcm,
      bench_COP=q/p,current_per_cell_A=i,tec_delta_K=th-tc)
 return None

def study():
 geom=json.loads(Path('studies/generated/geometry_report.json').read_text())
 void=geom['pcm_void_mm3'];liquid_density=.77;fill=.875
 # Reserve expansion from measured cavity, not external cell size. Conservative density basis.
 mass_g=void/1000*fill*liquid_density
 enthalpy=(250000*.925-2000*15)*.7*mass_g/1000
 cases=[]
 for q,delta,rh in __import__('itertools').product((.5,1,2,4),(0,4,8),(5,8,12)):
  r=solve(q/6,delta,6,rh)
  if r:
   pin=r['electrical_W_per_cell']*6;hot=q+pin
   # External insulation conduction uses geometry area in final refinement.
   leak=.03*.005/.0012*4
   startup=30;energy=(hot+leak)*180+startup
   r.update(total_bench_load_W=q,contact_below_PCM_K=delta,hot_path_K_W_per_cell=rh,
    electrical_W_total=pin,hot_W_total=hot,assumed_parasitic_leak_W=leak,
    energy_180s_J=energy,cooling_allocation_J=.6*enthalpy,margin_J=.6*enthalpy-energy)
   cases.append(r)
 return dict(source='https://thermal.ferrotec.com/technology/thermoelectric-reference-guide/thermalref11/',
   package_source='https://thermal.ferrotec.com/products/peltier-thermoelectric-cooler-modules/9503_018_012-m/',
   package_mm=[6.1,7.2,2.14],module_count=6,pcm_mass_g=mass_g,planning_enthalpy_J=enthalpy,
   design_status='FINITE_BUFFER_CONDITIONAL; NO_HUMAN_USE_SETTINGS_OR_PHYSICAL_PERFORMANCE',cases=cases)
if __name__=='__main__':
 r=study();Path('studies/thermal_network_results.json').write_text(json.dumps(r,indent=2,allow_nan=False)+'\n')
 print(json.dumps({k:v for k,v in r.items() if k!='cases'},indent=2))
 for row in r['cases']:
  if row['hot_path_K_W_per_cell']==8:print(json.dumps(row))
