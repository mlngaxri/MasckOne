"""Energy-conserving architecture comparison for inert thermal fixtures.
No human-use temperature setpoints. Capacity is a conservative planning quantity,
not qualified PCM latent capacity or a product runtime claim.
"""
import json,math
from pathlib import Path
from scipy.optimize import brentq
from thermal_network import solve,tec,K,prop
from thermal_coexistence import study as previous

def dewpoint(t,rh):
    # Algebraic inverse of NOAA/NWS saturation-vapor-pressure expression.
    g=math.log10(rh/100)+7.5*t/(237.3+t)
    return 237.3*g/(7.5-g)

def study():
    old=previous();g=json.loads(Path('studies/generated/geometry_report.json').read_text())
    ids=sorted(g['pcm_cells_mm3']);vol=[g['pcm_cells_mm3'][k] for k in ids]
    weight=[v/sum(vol) for v in vol];U=old['planning_usable_enthalpy_J']
    C=old['cold_copper_heat_capacity_J_K']+3
    motor=4*.2976 # rounded-up multirate steady result, inert preload scenario
    # Worst coupling bound accounts for all prior motor electrical heat, without
    # inventing a measured motor-to-store thermal resistance or cooling curve.
    prior_motor_J=motor*180
    cooling=[]
    for water,concurrent in [(0,False),(.4,False),(4,False),(.4,True)]:
      q=2+water*4.18*8/180
      cells=[solve(q*w,8,12,8) for w in weight]
      if any(c is None for c in cells):raise ValueError('no TEC operating solution')
      pin=sum(c['electrical_W_per_cell'] for c in cells)
      for c in cells:
        assert abs(c['hot_W_per_cell']-(q*weight[cells.index(c)]+c['electrical_W_per_cell']))<1e-9
      concurrent_J=motor*180 if concurrent else 0
      # Pessimistic all historical motor heat enters the store. Independent of the
      # additional simultaneous motor heat; no claimed conduction path is hidden.
      need=(q+pin+.5)*180+C*8+prior_motor_J+concurrent_J
      per=[]
      for i,(w,c) in enumerate(zip(weight,cells)):
        # Distributed even motor coupling is only a scenario. Also report local
        # available reserve so a concentrated coupling can be assessed separately.
        n=(q*w+c['electrical_W_per_cell']+.5*w)*180+C*8*w
        per.append(dict(cell=ids[i],capacity_J=U*w,base_required_J=n,
           remaining_before_motor_coupling_J=U*w-n))
      cooling.append(dict(water_mL=water,concurrent_massage=concurrent,
         net_inert_contact_W=2,water_sensible_J=water*4.18*8,TEC_electrical_W=pin,
         TEC_current_A=[c['current_per_cell_A'] for c in cells],
         store_energy_from_contact_water_TEC_J=(q+pin)*180,
         environmental_parasitic_J=90,startup_J=C*8,
         prior_motor_heat_upper_bound_J=prior_motor_J,concurrent_motor_J=concurrent_J,
         total_required_J=need,planning_available_J=U,margin_J=U-need,per_cell=per))
    warming=[]
    for delta in (4,8):
      # Reversible TEC left electrically open during resistive WARM. Include its
      # unavoidable thermal conduction; shorting the TEC would be a different model.
      conductance=prop(K,301.15,301.15+delta)*1.2/6*18/71
      r_module=1/conductance
      qstore=6*delta/(12+r_module+8)
      delivered=2;power=delivered+qstore+.5
      energy=power*180+C*delta
      warming.append(dict(contact_delta_from_PCM_K=delta,delivered_inert_W=delivered,
          off_TEC_module_K_W=r_module,heat_leak_to_PCM_W=qstore,
          steady_resistive_heater_W=power,electrical_energy_180s_plus_startup_Wh=energy/3600,
          PCM_energy_consumed_J=qstore*180,PCM_energy_remaining_J=U-qstore*180,
          benchmark_battery_Wh=3.7*1.1,benchmark_energy_fraction=energy/3600/(3.7*1.1)))
    dew=[]
    for t,rh in [(22,40),(25,60),(28,80),(30,90)]:
      dp=dewpoint(t,rh)
      dew.append(dict(ambient_C=t,RH_percent=rh,dewpoint_C=dp,
        dry_exposed_cold_surface_minimum_scenario_C=dp+2,
        uncertainty_reserve_DOE_K=2,not_human_temperature_limit=True))
    return dict(selected='SHARED_STATIONARY_SPREADERS; RESISTIVE_WARM; TEC_COOL; FULLY_SOLID_PCM_RESET',
      why='Slight heater-laminate complexity buys full cooling reserve and an observable reset endpoint; mixed-phase startup rejected.',
      physical_validation=False,cooling=cooling,warming=warming,condensation=dew,
      condensed_water_latent_load='UNKNOWN; DEWPOINT_GATE_OR_MEASURED_MASS_TRANSFER_REQUIRED',
      sensor_architecture=['contact plate sensor per side','cold TEC-side sensor per side','store sensor per cell','ambient humidity/temperature outside wet region'],
      readiness='Per-cell reset endpoint plus enthalpy accounting; do not infer phase fraction from plateau temperature.',
      rejected_or_conditional={
        'all_reversible_TEC_60_40_PCM':'PROMISING_BUT_INFERIOR_RESERVE; earlier 0.4mL case only 76.84J before motor coupling',
        'passive_PCM_direct_contact':'CONDITIONAL; no independent temperature modulation, PCM band and starting state dictate response',
        'wearable_natural_convection_TEC':'REJECTED_IN_4W_REJECTION_5K_SCENARIO; 0.16m2 at h=5W/m2K exceeds calm compact shell area',
        'water_sensible_store':'4K gives 16.72J/g versus ~140.88J/g planning PCM, before containment; mass penalty',
        'moving_thermal_spreader':'REJECTED; stiffness and moving mass penalize the 40Hz guide'},
      cooling_sequence='CLEAN/MASSAGE, RECOVERY, COOL with oscillation off preferred; no added user handling',
      sources=['https://www.weather.gov/media/epz/wxcalc/vaporPressure.pdf',
       'https://thermal.ferrotec.com/technology/thermoelectric-reference-guide/thermalref11/'])
if __name__=='__main__':
 r=study();Path('studies/thermal_v1_selection_results.json').write_text(json.dumps(r,indent=2,allow_nan=False)+'\n')
 print(json.dumps(r,indent=2))
