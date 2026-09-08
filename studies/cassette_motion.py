"""Continuous rigid-motion geometry checks, with elastic suspension kept separate."""
import json,math
from pathlib import Path
import cadquery as cq
from treatment_geometry import *


def rigid_axial_sweep(name,lo,hi):
 if name=='moving_cup':return join(cup_features(lo,hi))
 if name=='moving_rear_clamp':return ring(6.8,7.6,-7.475+lo,-7.2+hi)
 if name=='moving_front_clamp':return ring(1.25,2.8,8.025+lo,8.3+hi)
 raise ValueError('unbound motion member')


def run():
 mat,ref=cassette();moving=('moving_cup','moving_rear_clamp','moving_front_clamp')
 fixed=[k for k in mat if k not in (*moving,'rear_spiral','front_spiral')]
 r={'nominal_pairs':{},'continuous_nominal_motion':{},'elastic_motion':'NOT_SOLVED_BY_RIGID_SWEEPS'}
 for k in moving:
  r['nominal_pairs'][k]={f:iv(mat[k],mat[f]) for f in fixed}
  sw=rigid_axial_sweep(k,-.26,.26)
  r['continuous_nominal_motion'][k]={'valid':valid(sw),'swept_volume_mm3':sw.Volume(),
    'intersections_mm3':{f:iv(sw,mat[f]) for f in fixed},'supplier_housing_mm3':iv(sw,ref['supplier_magnet_package'])}
  sw.exportBrep(str(ROOT/'studies/generated'/f'{k}_continuous_sweep.brep'))
 print(json.dumps(r,indent=2));Path('studies/generated/cassette_motion_report.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':run()
