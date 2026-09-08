"""Position-only fixed-lag observer study for inert loads; no product controller."""
import json,math
from pathlib import Path
import numpy as np
from scipy.signal import cont2discrete
from scipy.linalg import solve_discrete_are

def case(delay_ms=1,noise_um=2,mass_g=2.7):
 dt=.0005;k=.07414875;nom_m=2.7e-6;actual_m=mass_g/1e6
 def plant(m):
  A=np.array([[0,1,0],[-k/m,0,-1/m],[0,0,0.]])
  B=np.array([[0],[1/m],[0.]])
  return cont2discrete((A,B,np.array([[1.,0,0]]),np.zeros((1,1))),dt)[:2]
 Ad,Bd=plant(nom_m);At,Bt=plant(actual_m);C=np.array([[1.,0,0]])
 R=np.array([[max(noise_um/1000,.0001)**2]])
 Q=np.diag([1e-10,1e-3,.005**2]);P=solve_discrete_are(Ad.T,C.T,Q,R);H=(P@C.T@np.linalg.inv(C@P@C.T+R))[:,0]
 d=round(delay_ms/1000/dt);N=1600;truth=np.zeros((N+1,3));est=np.zeros((N+1,3));u=np.zeros(N);refs=np.zeros(N);truth[0,2]=.2
 rng=np.random.default_rng(872);kp=.7;kd=2*.8*math.sqrt(nom_m*(k+kp))
 for n in range(N):
  if n>=d:
   j=n-d;z=truth[j,0]+rng.normal(0,noise_um/1000);est[j]+=H*(z-est[j,0])
   for jj in range(j,n):est[jj+1]=Ad@est[jj]+Bd[:,0]*u[jj]
  t=n*dt;tr=t-.2;T=.08;w=2*math.pi*40
  if tr<=0:a=da=dda=0.
  elif tr<T:a=.13*(1-math.cos(math.pi*tr/T));da=.13*math.pi/T*math.sin(math.pi*tr/T);dda=.13*(math.pi/T)**2*math.cos(math.pi*tr/T)
  else:a=.26;da=dda=0.
  r=a*math.sin(w*tr);v=da*math.sin(w*tr)+a*w*math.cos(w*tr);acc=dda*math.sin(w*tr)+2*da*w*math.cos(w*tr)-a*w*w*math.sin(w*tr)
  # Mid-interval feedforward accounts for zero-order hold at the commanded frequency.
  if tr>=T:
   rmid=.26*math.sin(w*(tr+dt/2));amid=-w*w*rmid;ff=nom_m*amid+k*rmid
  else:ff=nom_m*acc+k*r
  u[n]=np.clip(ff+est[n,2]-kp*(est[n,0]-r)-kd*(est[n,1]-v),-.27,.27)
  refs[n]=r;truth[n+1]=At@truth[n]+Bt[:,0]*u[n];est[n+1]=Ad@est[n]+Bd[:,0]*u[n]
 steady=np.arange(N)*dt>.4;err=truth[:-1,0]-refs
 return dict(sensor_delay_ms=delay_ms,position_noise_rms_um=noise_um,actual_mass_g=mass_g,
   acquisition_peak_mm=float(max(abs(truth[:400,0]))),steady_tracking_peak_error_mm=float(max(abs(err[steady]))),
   steady_tracking_RMS_error_mm=float(np.sqrt(np.mean(err[steady]**2))),
   peak_displacement_mm=float(max(abs(truth[:,0]))),peak_force_N=float(max(abs(u))),
   steady_motor_copper_W=float(np.mean((u[steady]/.45)**2)*1.5),
   measured_position_only=True,observer_replays_known_input_history=True,
   wet_membrane_and_frame_modelled=False,physical_validation=False)
if __name__=='__main__':
 rows=[case(d,n,m) for d,n,m in [(0,0,2.7),(.5,2,2.7),(1,2,2.7),(1,2,2.2),(1,2,3.2),(2,5,2.7)]]
 Path('studies/centering_observer_results.json').write_text(json.dumps(rows,indent=2,allow_nan=False)+'\n');print(json.dumps(rows,indent=2))
