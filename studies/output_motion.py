"""Source-enclosing continuous rigid output motion; boot elasticity stays separate."""
from treatment_geometry import *
from treatment_interfaces import thermal_interfaces,wet_boot
from mounted_station import station
from continuous_service import polyhedron_motion_bound

def study():
 out=ROOT/'studies/generated';report={}
 frame=cq.Shape.importBrep(str(out/'consumed_frame_reactions.brep'));ext=cq.Shape.importBrep(str(out/'consumed_supported_pre_roll_boundary.brep'));pz=protected(build_model());thermal,_=thermal_interfaces()
 for kind,c in STATION_POSES.items():
  m,r=station(kind,c);p=r['output_shoe_center'].Center();boot=wet_boot((p.x,p.y),z=-5.55,height=-.1)
  axis=np.array([math.sin(math.radians(61)),0,math.cos(math.radians(61))]);delta=axis*.26
  sw=polyhedron_motion_bound(r['output_piece_bounds'],-delta,delta)
  rest=m['output_shoe']
  for piece in r['output_piece_bounds'].Solids():rest=rest.cut(piece)
  assert rest.Volume()<1e-7 and valid(sw)
  fixed={k:v for k,v in m.items() if k not in ('moving_cup','moving_rear_clamp','moving_front_clamp','rear_spiral','front_spiral','output_shoe')}
  fixed|={'stationary_boot_seat':boot['stationary_boot_seat'],'frame':frame,'supported_pre_roll_boundary':ext,**pz,**thermal}
  fixed['frame']=frame.cut(r['required_draw_pin_bore']).cut(r['required_key_port'])
  hits={k:iv(sw,v) for k,v in fixed.items()}
  nominal_boot={name:{k:iv(s,v) for k,v in m.items() if iv(s,v)>1e-7} for name,s in boot.items()}
  report[kind]=dict(center_mm=c,output_center_mm=p.toTuple(),valid=valid(m['output_shoe']),
      output_sweep_valid=valid(sw),swept_volume_mm3=sw.Volume(),source_enclosure_deficit_mm3=rest.Volume(),
      rigid_sweep_intersections_mm3=hits,nominal_boot_intersections_mm3=nominal_boot,
      moving_part_mass_model='Mass scenarios include extra arm allowance; density/alloy/hardware not production-qualified',
      nonlinear_boot_motion='UNRESOLVED: nominal boot and rigid-seat clearance are not an elastic sweep',
      supplier_termination_pins='UNDIMENSIONED_IN_PUBLIC_DRAWING; package wiring proof incomplete')
  sw.exportBrep(str(out/f'{kind}_output_operational_bound.brep'))
 Path('studies/generated/output_motion_report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':study()
