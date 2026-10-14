"""Export passive OFF-FACE bench components with exact producer identity."""
import argparse,json
from pathlib import Path
import cadquery as cq
from masck_one.thermal_reset_hardware import export_thermal_reset,build_thermal_reset_hardware

parser=argparse.ArgumentParser()
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--source-head',required=True)
args=parser.parse_args()
manifest=export_thermal_reset(args.output,args.source_head)
parts,refs,geometry=build_thermal_reset_hardware()
checks=[]
for name,before in parts.items():
    after=cq.importers.importStep(str(args.output/f'{name}.step')).val()
    if not after.isValid() or len(after.Solids())!=1:raise ValueError(f'{name}: invalid round trip')
    delta=after.Volume()-before.Volume()
    # Analytic parts: a strict engineering check, with measured deltas retained.
    if abs(delta)>1e-6:raise ValueError(f'{name}: STEP volume change {delta} mm3')
    checks.append(dict(component=name,before_mm3=before.Volume(),after_mm3=after.Volume(),delta_mm3=delta))
for name,count in [('THERMAL_LEFT',6),('THERMAL_RIGHT',6),('OFF_FACE_DOCK',2),('THERMAL_DOCKED_BENCH',14),('THERMAL_BENCH_SERVICE',14)]:
    shape=cq.importers.importStep(str(args.output/f'{name}.step')).val()
    if not shape.isValid() or len(shape.Solids())!=count:raise ValueError(f'{name}: assembly membership changed')
result=dict(source_head_sha=args.source_head,material_component_count=len(parts),reference_count=len(refs),
            solid_roundtrips=checks,whole_product_assembly_exported=False,native_fusion_import_tested=False)
(args.output/'step_verification.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
print(json.dumps(result,indent=2))
