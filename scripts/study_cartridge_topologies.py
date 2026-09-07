import cadquery as cq, json, argparse
from pathlib import Path
from masck_one.realized_waste_cartridge import require_sources, SOURCE_GIT_BLOB_IDENTITIES
require_sources()
parser=argparse.ArgumentParser()
parser.add_argument('--output',default='generated/cartridge-topology-study.json')
args=parser.parse_args()
from masck_one.model import build_model, _loft_ellipses

m=build_model()
def box(size,center): return cq.Workplane('XY').box(*size).translate(center)
def ellipse(a,b,z,h,center=(0,-50)):
 return cq.Workplane('XY',origin=(center[0],center[1],z)).ellipse(a,b).extrude(h)
def vol(s): return sum(x.Volume(1e-12) for x in s.val().Solids())/1000
package=m.waste_cartridge_envelope.solid
mouth=ellipse(38.5,25.5,-30,80)
inside=_loft_ellipses([(-2,151.4,198.4),(-1,151.4,198.4),(10,164.4,203.4),(22,168.4,206.4)])
rear=cq.Workplane('XY',origin=(0,0,-3)).ellipse(151.4/2,198.4/2).extrude(24)
print('ceilings',json.dumps({'full':vol(package.cut(mouth)), 'inner':vol(package.cut(mouth).intersect(inside)), 'rear_passage':vol(package.cut(mouth).intersect(rear))}),flush=True)
rows=[]
for architecture in ('flat_film_tray','shallow_cap','rear_passage_film'):
 for wall,floor,lid in ((1.2,1.2,2),(.8,.8,.3),(.6,.6,.25),(.5,.5,.2),(.4,.4,.2)):
  # DOE only, no process minimum is established by this table.
  cavity=box((74-2*wall,36-2*wall,20-floor-lid),(0,-80,8+(floor-lid)/2)).cut(ellipse(38.5+wall,25.5+wall,-30,80))
  if architecture=='shallow_cap':
   cavity=cavity.cut(box((74,36,1),(0,-80,17-lid)))
  if architecture=='rear_passage_film':
   corridor=cq.Workplane('XY',origin=(0,0,-3)).ellipse(151.4/2-wall,198.4/2-wall).extrude(24)
   cavity=cavity.intersect(corridor)
  else:
   inset=_loft_ellipses([(-2,151.4-2*wall,198.4-2*wall),(-1,151.4-2*wall,198.4-2*wall),(10,164.4-2*wall,203.4-2*wall),(22,168.4-2*wall,206.4-2*wall)])
   cavity=cavity.intersect(inset)
  row=dict(architecture=architecture,wall=wall,floor=floor,lid=lid,cavity_mL=vol(cavity),solids=len(cavity.val().Solids()),valid=cavity.val().isValid())
  rows.append(row);print(json.dumps(row),flush=True)
path=Path(args.output)
path.parent.mkdir(parents=True,exist_ok=True)
path.write_text(json.dumps({'source_git_blobs':dict(SOURCE_GIT_BLOB_IDENTITIES),'status':'REJECTED_CAPACITY_CEILINGS_WITHIN_CHOSEN_POCKET_BEFORE_INTERFACE_LOSSES','rows':rows},indent=2)+'\n')

