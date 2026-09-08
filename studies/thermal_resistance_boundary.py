"""Resistance and local-store sensitivity for the selected inert thermal fixture."""
import json
from pathlib import Path
from thermal_network import solve

def study():
    v1=json.loads(Path('studies/thermal_v1_selection_results.json').read_text())
    base=next(c for c in v1['cooling'] if c['water_mL']==.4 and not c['concurrent_massage'])
    volumes=json.loads(Path('studies/generated/geometry_report.json').read_text())['pcm_cells_mm3']
    ids=sorted(volumes);vol=[volumes[k] for k in ids]
    weights=[.5*v/sum(vol[:3] if i<3 else vol[3:]) for i,v in enumerate(vol)]
    q=2+.4*4.18*8/180;rows=[]
    for rc in (6,12,24):
      for rh in (4,8,16):
        cells=[solve(q*w,8,rc,rh*(14.6/10.4 if i==0 else 1)) for i,w in enumerate(weights)]
        if any(c is None for c in cells):
          rows.append(dict(cold_K_W=rc,hot_K_W=rh,operating_solution=False));continue
        power=sum(c['electrical_W_per_cell'] for c in cells)
        need=(q+power+.5)*180+base['startup_J']+base['prior_motor_heat_upper_bound_J']
        local=[]
        for i,(w,c) in enumerate(zip(weights,cells)):
          capacity=base['planning_available_J']*vol[i]/sum(vol)
          required=(q*w+c['electrical_W_per_cell']+.5*w)*180+base['startup_J']*w
          local.append(capacity-required)
        rows.append(dict(cold_K_W=rc,hot_K_W=rh,short_cell_area_correction=14.6/10.4,
          operating_solution=True,TEC_electrical_W=power,global_margin_J=base['planning_available_J']-need,
          local_margin_before_motor_heat_J=local,
          left_side_margin_after_half_motor_J=sum(local[:3])-base['prior_motor_heat_upper_bound_J']/2,
          right_side_margin_after_half_motor_J=sum(local[3:])-base['prior_motor_heat_upper_bound_J']/2))
    result=dict(cases=rows,resistances='DOE values including interfaces, not measured performance',
      rejection_rule='No operating solution or negative cell enthalpy reserve rejects that operating case.',
      motor_coupling='Neither per-side nor global reserve proves arbitrary concentrated motor heat. Per-cell readiness must gate operation.',
      physical_validation=False)
    Path('studies/thermal_resistance_boundary_results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':study()
