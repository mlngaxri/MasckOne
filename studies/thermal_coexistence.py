"""Coupled heat accounting for inert fixtures. Missing cleaner/skin properties stay unknown."""
import json,math
from pathlib import Path
from scipy.optimize import brentq
from thermal_network import tec,solve

def warming(q,delta,rc=12,rh=8):
 pcm=301.15;th=pcm+delta+q*rc
 def state(i):
  tc=brentq(lambda tc:tc-pcm+rh*tec(i,tc,th)[0],pcm-100,pcm+20)
  qc,p=tec(i,tc,th);return qc+p-q,qc,p,tc
 i=brentq(lambda i:state(i)[0],0,1.2);_,qc,p,tc=state(i)
 return dict(store_extraction_W=qc*6,electrical_W=p*6,store_side_drop_K=pcm-tc)

def study():
 g=json.loads(Path('studies/generated/geometry_report.json').read_text())
 copper_volume=sum(v['volume_mm3'] for k,v in g['thermal_geometry'].items() if k.startswith(('cheek_spreader','fixed_folded_bus')))
 capacity_copper=copper_volume*.00889*.385
 additional_capacity=3.0 # explicit DOE for barriers/modules, excluding user or skin
 startup_capacity=capacity_copper+additional_capacity
 mass=g['pcm_void_mm3']/1000*.875*.77
 usable=mass/1000*(250000*.925-30000)*.7
 # Geometry sizes produce unequal cell capacities. Independently allocate the
 # six TEC heat loads; equal current would strand energy in the wider cells.
 cell_volumes=[2934.6,2934.6,1547.6]*2
 weights=[v/sum(cell_volumes) for v in cell_volumes]
 def cool_device(q,delta):
  cases=[solve(q*w,delta,12,8) for w in weights]
  return sum(v['electrical_W_per_cell'] for v in cases),cases
 records=[]
 for mode in ('COOL','WARM'):
  for q,delta in ((1,4),(2,4),(2,8)):
   if mode=='COOL':
    pin,v=cool_device(q,delta);stored=q+pin;allocation=usable*.6
   else:
    v=warming(q/6,delta);pin=v['electrical_W'];stored=v['store_extraction_W'];allocation=usable*.4
   # 0.5W environmental leakage scenario; actuator heat coupling bounded separately.
   startup=startup_capacity*delta;needed=stored*180+.5*180+startup
   records.append(dict(mode=mode,total_inert_contact_load_W=q,contact_delta_from_PCM_K=delta,
    electrical_W=pin,PCM_heat_rate_W=stored,startup_J=startup,environmental_leak_J=90,
    required_energy_J=needed,allocated_energy_J=allocation,margin_J=allocation-needed))
 water=[]
 # Controlled fresh WATER 3.2 + 0.8mL; cleanser heat capacity is genuinely unknown.
 for wet_ml in (0,.4,4.):
  delta=8;water_J=wet_ml*4.18*delta;effective_q=2+water_J/180
  pin,v=cool_device(effective_q,delta);needed=(effective_q+pin+.5)*180+startup_capacity*delta
  water.append(dict(water_exposure_scenario_mL=wet_ml,added_water_sensible_J=water_J,
   required_energy_J=needed,allocated_cooling_J=usable*.6,margin_J=usable*.6-needed,
   cleanser_thermal_properties='UNKNOWN_NOT_COUNTED',
   residual_requirement_is_not_measured_residual=True))
 # Passive dock cannot freeze this PCM when ambient is above its congealing band.
 # Reversed onboard TECs reject into a conductive dock platen + forced-air heat sink.
 dock=[]
 for ambient_delta in (0,4,8):
  q_store=1.5;rsink=1.5;rcontact=1.0
  def balance(qhot):
   hot_delta=ambient_delta+qhot*(rsink+rcontact)
   w=warming(qhot/6,hot_delta,12,8)
   return w['store_extraction_W']-q_store
  try:
   qhot=brentq(balance,1.6,8);elec=qhot-q_store
   dock.append(dict(ambient_above_PCM_K=ambient_delta,heat_extracted_from_store_W=q_store,
     rejected_to_air_W=qhot,onboard_TEC_electrical_W=elec,
     assumed_dock_sink_K_W=rsink,assumed_dock_contact_K_W=rcontact,
     full_usable_enthalpy_reset_s=usable/q_store,
     reset_600J_s=600/q_store,dock_fan_power_and_contact_conductance_unqualified=True))
  except ValueError:dock.append(dict(ambient_above_PCM_K=ambient_delta,status='NO_SOLUTION_WITHIN_SEARCH_BRACKET'))
 per_cell=[]
 pin,cells=cool_device(2,8)
 for idx,(w,c) in enumerate(zip(weights,cells)):
  need=(2*w+c['electrical_W_per_cell']+.5*w)*180+startup_capacity*8*w
  per_cell.append(dict(cell=idx,void_mm3=cell_volumes[idx],heat_allocation=w,energy_required_J=need,
    energy_available_J=usable*.6*w,margin_J=usable*.6*w-need))
 return dict(per_cell_cooling_check=per_cell,cold_path_resistance_scenario_K_W_per_cell=12,
   cold_path_basis='0.25mm barrier k=0.2 DOE plus two 0.35x26mm copper folds and contact/spreading reserve',
   TEC_control='six independently balanced stationary modules; equal-current operation is not assumed',exact_PCM_void_mm3=g['pcm_void_mm3'],PCM_fill_fraction_assumption=.875,PCM_mass_g=mass,
   planning_usable_enthalpy_J=usable,shared_contact_area_mm2=2*22*28,
   cold_copper_volume_mm3=copper_volume,cold_copper_heat_capacity_J_K=capacity_copper,
   additional_heat_capacity_scenario_J_K=additional_capacity,mode_cases=records,water_sensitivity=water,
   actuator_heat_four_station_at_0p2N_bias_W=4*(.2/.45)**2*1.5,
   dock_cases=dock,back_to_back_cooling='NOT_GUARANTEED; UPDATE_ENTHALPY_STATE_AND_LIMIT_UNREADY_COOL',
   scheduling_decision='Prefer cooling after fluid delivery/recovery; full concurrent fresh-fluid load can exhaust margin.',
   evidence='ENERGY_AND_RESISTANCE_MODEL_ONLY; NO_HUMAN_TEMPERATURE_LIMITS_OR_PERFORMANCE_CLAIMS')
if __name__=='__main__':
 r=study();Path('studies/thermal_coexistence_results.json').write_text(json.dumps(r,indent=2,allow_nan=False)+'\n');print(json.dumps(r,indent=2))
