"""Run from the repository root in its qualified environment. No physical claim."""
from pathlib import Path
import argparse,json

parser=argparse.ArgumentParser(description='Regenerate the isolated synthetic campaign and validated-pose screens.')
parser.add_argument('output',type=Path)
args=parser.parse_args()
from masck_one.adversarial_fit_study import run,save,provenance,write_manifest
from masck_one.adversarial_fit_geometry import protected_screen
from masck_one.adversarial_fit_proof import Variation
out=args.output
if out.exists() and any(out.iterdir()):
    raise SystemExit('Use an empty output directory to preserve earlier evidence.')
summary=run(out,capabilities=True)
print('numerical campaign complete',flush=True)
rows=[]
for name in ['nominal','eye_spacing_failure','asymmetry']:
 w=json.loads((out/'witnesses'/(name+'.json')).read_text())
 r,_,_=protected_screen(Variation(**w['parameters']),w['solved_transform'])
 rows.append({'case':name,'provenance':provenance(),'receipt':r})
 print('screen complete',name,flush=True)
save(out/'projected_screens.json',rows)
summary['supersedes']={'campaign':'analysis/fit_proof/campaign_3ccd912','scope':'CURRENT_EXECUTABLE_CAMPAIGN_ONLY','historical_campaign_preserved':True}
write_manifest(out,summary)
print('complete',summary['synthetic_cases'],summary['adaptive_evaluations'],flush=True)
