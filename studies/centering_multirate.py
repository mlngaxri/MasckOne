"""Inert spring/mass control architecture experiment. Not embedded or human-use control.
Slow integral bias acts on waveform-subtracted displacement; a velocity-error term
stabilizes the free flexure mode. Contact is a unilateral DOE stop, not an inferred
material law. The experiment records failure, it does not prescribe operation.
"""
import math,json
from pathlib import Path
import numpy as np

K=.07414875;M=2.7e-6;W=2*math.pi*40

def run(delay_ms=1,noise_um=2,mass_g=2.7,foil_mm=.05,load=.2,seal_k=.02,
        seal_c=.00015,stop_k=4.,disturbance='none',bias_passive=0.,dt=.0001,identified_fixture=False):
    sample=.0005;hold=round(sample/dt);N=round(2.5/dt);d=round(delay_ms/1000/sample)
    k=K*(foil_mm/.05)**3+seal_k;m=mass_g/1e6
    # Actual unpowered static equilibrium with stop force. No impossible linear offset.
    p=load-bias_passive
    x=-p/k if abs(p/k)<.35 else -math.copysign((abs(p)+stop_k*.35)/(k+stop_k),p)
    v=0.;integ=0.;force=0.;vel_est=0.;prev_e=x;lp_e=x;bias=0.
    history=[];ready_history=[];rows=[];rng=np.random.default_rng(5483);r=rv=ra=0.;wave_t=None;stable=0.;phase='ACQUIRE'
    kp=.08;kd=.0011;ki=1.6;error_tau=.005;velocity_tau=.0015
    def waveform(t):
        if wave_t is None:return (0.,0.,0.)
        tr=t-wave_t;T=.25
        if tr<=0:return (0.,0.,0.)
        if tr<T:
            a=.13*(1-math.cos(math.pi*tr/T));da=.13*math.pi/T*math.sin(math.pi*tr/T);dda=.13*(math.pi/T)**2*math.cos(math.pi*tr/T)
        else:a=.26;da=dda=0.
        return a*math.sin(W*tr),da*math.sin(W*tr)+a*W*math.cos(W*tr),dda*math.sin(W*tr)+2*da*W*math.cos(W*tr)-a*W*W*math.sin(W*tr)
    for n in range(N):
        t=n*dt;r,rv,ra=waveform(t)
        actual_load=load
        if disturbance=='ramp' and t>1.6:actual_load+=.03*min(1,(t-1.6)/.2)
        if disturbance=='step' and t>1.6:actual_load+=.05
        if disturbance=='overload' and t>1.6:actual_load+=.12
        if n%hold==0:
            history.append((x+rng.normal(0,noise_um/1000),r))
            y,rd=history[max(0,len(history)-1-d)];e=y-rd
            vel_est+=(e-prev_e-vel_est*sample)/(velocity_tau+sample);prev_e=e
            lp_e+=sample/(error_tau+sample)*(e-lp_e)
            # Bias/center bandwidth is deliberately far below 40Hz. The fixed
            # nominal waveform is subtracted at its actual measurement timestamp.
            trial=integ+lp_e*sample
            u_bias=-ki*trial
            ff=(m*ra+k*r+seal_c*rv) if identified_fixture else (M*ra+(K+.02)*r+.00015*rv)
            u=u_bias+ff-kp*e-kd*vel_est
            if abs(u)<.27 or u*lp_e>0:integ=trial
            bias=-ki*integ
            force=float(np.clip(bias+ff-kp*e-kd*vel_est,-.27,.27))
            if wave_t is None:
                ready_history.append(e)
                window=np.array(ready_history[-200:])
                # Instant differentiated 2um sensor noise cannot establish standstill.
                # Assess position mean, scatter and drift over a full 100ms instead.
                if len(window)==200:
                    slope=float(np.polyfit(np.arange(200)*sample,window,1)[0])
                    if abs(window.mean())<.008 and window.std()<.004 and abs(slope)<.03 and abs(force)<.24:
                        wave_t=t;phase='WAVEFORM'
        # RK4 actual plant with unilateral soft stops. Never clamp the coordinate.
        def rhs(xx,vv):
            fs=-stop_k*max(xx-.35,0)+stop_k*max(-xx-.35,0)
            # Dissipation only while driving further into a stop. DOE, not qualified rubber.
            if xx>.35 and vv>0:fs-=.003*vv
            if xx<-.35 and vv<0:fs-=.003*vv
            return vv,(force+bias_passive-k*xx-seal_c*vv-actual_load+fs)/m
        a,b=rhs(x,v);c,e=rhs(x+dt*a/2,v+dt*b/2);f,g=rhs(x+dt*c/2,v+dt*e/2);h,j=rhs(x+dt*f,v+dt*g)
        x+=dt*(a+2*c+2*f+h)/6;v+=dt*(b+2*e+2*g+j)/6
        if n%hold==0:rows.append((t,x,v,force,r,bias,actual_load))
    a=np.array(rows);steady=(a[:,0]>max((wave_t or 2.5)+.5,1.2))&(a[:,0]<1.59)
    after=a[:,0]>1.65
    return dict(delay_ms=delay_ms,noise_um=noise_um,mass_g=mass_g,foil_mm=foil_mm,
       identified_fixture_impedance=identified_fixture,inert_preload_N=load,membrane_stiffness_DOE_N_mm=seal_k,membrane_damping_DOE_N_s_mm=seal_c,
       stop_stiffness_DOE_N_mm=stop_k,passive_bias_N=bias_passive,disturbance=disturbance,
       acquired=wave_t is not None,waveform_start_s=wave_t,
       peak_displacement_mm=float(max(abs(a[:,1]))),hard_stop_exceeded=bool(max(abs(a[:,1]))>=.45),
       steady_peak_tracking_error_mm=float(max(abs(a[steady,1]-a[steady,4]))) if any(steady) else None,
       steady_peak_displacement_mm=float(max(abs(a[steady,1]))) if any(steady) else None,
       steady_copper_W=float(np.mean((a[steady,3]/.45)**2)*1.5) if any(steady) else None,
       disturbed_peak_displacement_mm=float(max(abs(a[after,1]))),
       saturation_fraction=float(np.mean(abs(a[:,3])>=.26999)),peak_force_N=float(max(abs(a[:,3]))),
       full_stroke_under_nominal=bool(any(steady) and max(abs(a[steady,1]-a[steady,4]))<.03 and max(abs(a[steady,1]))<.32),
       evidence='LINEAR_FLEXURE_PLUS_UNILATERAL_STOP_DOE; NOT_A_DEPLOYABLE_CONTROLLER; NO_HUMAN_USE')
if __name__=='__main__':
    cases=[{},dict(delay_ms=2),dict(delay_ms=4),dict(load=.1),dict(mass_g=2.2,foil_mm=.045),
      dict(mass_g=3.2,foil_mm=.055),dict(seal_k=.08,seal_c=.0003),dict(stop_k=2),
      dict(disturbance='ramp'),dict(disturbance='step'),dict(disturbance='overload'),dict(bias_passive=.1),dict(seal_k=.08,seal_c=.0003,identified_fixture=True)]
    rows=[run(**c) for c in cases]
    Path('studies/centering_multirate_results.json').write_text(json.dumps(rows,indent=2,allow_nan=False)+'\n')
    for r in rows:print(json.dumps(r),flush=True)
