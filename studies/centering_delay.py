"""Sampled inert-load control feasibility, not implementable product firmware."""
import json,math
from pathlib import Path
import numpy as np
from scipy.signal import cont2discrete

def case(delay_ms):
 dt=.00025;m=2.7e-6;k=.07414875;kp=.7;kd=2*.8*math.sqrt(m*(k+kp));ki=35
 A=np.array([[0,1],[-k/m,0.]]);B=np.array([[0],[1/m]])
 Ad,Bd,_,_,_=cont2discrete((A,B,np.eye(2),np.zeros((2,1))),dt)
 y=np.zeros(2);integ=0;queue=[y.copy() for _ in range(round(delay_ms/dt/1000)+1)];rows=[]
 for j in range(3200):
  t=j*dt
  # Smooth reference ramp, with analytic acceleration feedforward.
  tr=t-.2;T=.08;omega=2*math.pi*40
  if tr<=0:amp=da=dda=0.
  elif tr<T:amp=.13*(1-math.cos(math.pi*tr/T));da=.13*math.pi/T*math.sin(math.pi*tr/T);dda=.13*(math.pi/T)**2*math.cos(math.pi*tr/T)
  else:amp=.26;da=dda=0.
  rr=amp*math.sin(omega*tr);rv=da*math.sin(omega*tr)+amp*omega*math.cos(omega*tr)
  ra=dda*math.sin(omega*tr)+2*da*omega*math.cos(omega*tr)-amp*omega**2*math.sin(omega*tr)
  sensed=queue.pop(0);queue.append(y.copy());err=sensed[0]-rr
  u=m*ra+k*rr-kp*err-kd*(sensed[1]-rv)-ki*integ
  clipped=np.clip(u,-.27,.27)
  if abs(u)<.27 or err*u>0:integ+=err*dt
  y=Ad@y+Bd[:,0]*(clipped-.2)
  rows.append((t,y[0],rr,clipped))
 a=np.array(rows);steady=a[:,0]>.4
 return dict(assumed_total_sensor_delay_ms=delay_ms,acquisition_peak_mm=float(max(abs(a[a[:,0]<.2,1]))),
  commanded_tracking_peak_error_mm=float(max(abs(a[steady,1]-a[steady,2]))),
  peak_displacement_mm=float(max(abs(a[:,1]))),peak_force_N=float(max(abs(a[:,3]))),
  observed_soft_stop_contact=bool(max(abs(a[:,1]))>=.35),
  noise_included=False,wet_boot_stiffness_included=False,frame_compliance_included=False,
  sensor_velocity_is_idealized=True,physical_validation=False)
if __name__=='__main__':
 r=[case(d) for d in (0,.5,1,2)];Path('studies/centering_delay_results.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
