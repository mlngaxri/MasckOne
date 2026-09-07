"""Export exact full-travel guard sweeps without factory-attachment promotion."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import cadquery as cq
from masck_one import retention_hazard_guards as g


def main():
    output = Path(sys.argv[1])
    package = g.build_retention_hazard_guards()
    g.export_retention_hazard_guard_review(output, package)
    comparisons = []
    for sign, guard in ((-1, package.left_adjustment_guard), (1, package.right_adjustment_guard)):
        yoke = g.occipital._build_yoke(sign, 155.0)[0]
        bounds = g._adjust_guard_primitive_bounds((76.5, 87.5) if sign == 1 else (-87.5, -76.5))
        old = g._exact_axis_x_sweep(bounds, -sign * 22, "rejected inboard sweep")
        cq.exporters.export(yoke.solid, str(output / (yoke.part_id.lower() + '_material_candidate.step')))
        comparisons.append({
            'guard_id': guard.part_id,
            'old_yoke_intersection_mm3': g._intersection_mm3(old, yoke.solid),
            'new_yoke_intersection_mm3': g._intersection_mm3(guard.exact_factory_install_sweep, yoke.solid),
            'new_yoke_distance_mm': g._distance_mm(guard.exact_factory_install_sweep, yoke.solid),
            'motion_translation_x_mm': guard.install_translation_x_mm,
            'whole_factory_assembly_closed': False,
        })
    for guard in package.guards:
        for shape, suffix in ((guard.solid, ''), (guard.exact_factory_install_sweep, '_exact_factory_install_sweep_reference')):
            restored = cq.importers.importStep(str(output / (guard.part_id.lower() + suffix + '.step'))).val()
            source = shape.val()
            if not restored.isValid() or len(restored.Solids()) != 1:
                raise ValueError('invalid guard STEP round trip')
            if abs(restored.Volume(1e-12) - source.Volume(1e-12)) > 1e-6:
                raise ValueError('guard STEP volume changed')
            if source.cut(restored).Volume() > 1e-7 or restored.cut(source).Volume() > 1e-7:
                raise ValueError('guard STEP material changed')
    report = {
        'source_head_sha': subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip(),
        'source_base_sha': g.SOURCE_MAIN_SHA,
        'source_guard_blob_sha': g._git_blob_sha(Path(g.__file__)),
        'source_yoke_blob_sha': g.SOURCE_OCCIPITAL_GIT_BLOB_SHA,
        'comparisons': comparisons,
        'step_round_trip': 'VALID_SINGLE_SOLIDS_AND_BIDIRECTIONAL_MATERIAL_EQUALITY',
        'physical_validation': False,
        'sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir()) if p.is_file()},
    }
    (output / 'guard_installation_review.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
