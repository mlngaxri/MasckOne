"""Read-only exact-owner geometry extraction, in an isolated source checkout.

Run with that checkout's src on PYTHONPATH. A producer exception is retained as
missing geometry evidence, never converted into empty/clear material.
"""
from dataclasses import fields, is_dataclass
from hashlib import sha256
import argparse
import json
from pathlib import Path
import subprocess
import sys
import traceback

import cadquery as cq


def extract(owner, source_root, output, head):
    source_root = source_root.resolve()
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    result = {'owner': owner, 'head': head, 'status': 'UNKNOWN',
              'participants': rows, 'evidence': 'DIGITAL', 'physical_result': None}
    def walk(obj, path):
        if isinstance(obj, cq.Workplane):
            for i, shape in enumerate(obj.vals()):
                if isinstance(shape, cq.Shape): walk(shape, path + f'.{i}')
        elif isinstance(obj, cq.Shape):
            if not obj.Solids(): return
            name = path.replace('.', '__').replace('/', '_')
            f = output / (name + '.step')
            cq.exporters.export(obj, str(f))
            b = obj.BoundingBox()
            reference = any(x in path.lower() for x in ('reference', 'sweep', 'free', 'deformed'))
            # Unknown semantic membership must not be promoted to manufactured material.
            material = 'material_parts' in path or (owner == 'frame' and not reference)
            rows.append({'id': owner + ':' + path, 'source_head': head,
                         'geometry_sha256': sha256(f.read_bytes()).hexdigest(), 'step': f.name,
                         'valid': obj.isValid(), 'solid_count': len(obj.Solids()),
                         'classification': 'REFERENCE' if reference else
                             ('OWNER_MATERIAL_CANDIDATE' if material else 'OWNER_ROLE_UNRESOLVED'),
                         'volume_sum_mm3': sum(s.Volume() for s in obj.Solids()),
                         'bounds_mm': [b.xmin,b.xmax,b.ymin,b.ymax,b.zmin,b.zmax],
                         'frame': 'OWNER_WORLD_COORDINATES_NO_NEW_TRANSFORM',
                         'registered_facial_contact': None})
        elif is_dataclass(obj):
            for f in fields(obj): walk(getattr(obj, f.name), path + '.' + f.name)
        elif isinstance(obj, dict):
            for k, v in sorted(obj.items()): walk(v, path + '.' + str(k))
        elif isinstance(obj, (list, tuple)):
            for i, v in enumerate(obj): walk(v, path + '.' + str(i))
    try:
        if owner == 'treatment':
            from masck_one.treatment_mounted_four_zone_v10 import build_mounted_four_zone_architecture_v10
            a, d = build_mounted_four_zone_architecture_v10()
            walk(a, 'mounted'); walk(d, 'datums')
        elif owner == 'retention':
            from masck_one.retention_quick_release_tactile_v3 import build_retention_quick_release_tactile_v3
            from masck_one.mechanical_interface_graph import build_mechanical_interface_graph
            walk(build_retention_quick_release_tactile_v3(), 'quick_release')
            graph = build_mechanical_interface_graph()
            result['graph'] = graph.manifest() if callable(graph.manifest) else graph.manifest
        elif owner == 'frame':
            from masck_one.structural_frame_retention_roots import build_structural_frame_retention_roots
            from masck_one.structural_frame_crown_support import build_structural_frame_crown_support
            roots = build_structural_frame_retention_roots()
            walk(roots, 'roots'); walk(build_structural_frame_crown_support(roots=roots), 'crown')
        else: raise ValueError('unsupported owner')
        result['status'] = 'EXTRACTED_NOT_INTEGRATION_APPROVAL'
    except Exception as exc:
        result['status'] = 'PRODUCER_FAILED_NO_CLEARANCE_INFERENCE'
        result['error'] = type(exc).__name__ + ': ' + str(exc)
        result['traceback'] = traceback.format_exc()
        # Preserve instantiated inputs at the failed check. This does not skip
        # or change the producer gate and never manufactures a passing assembly.
        tb=exc.__traceback__
        while tb:
            frame=tb.tb_frame
            if 'treatment_mounted_four_zone' in frame.f_code.co_filename and frame.f_code.co_name.startswith('build_'):
                for key in ('base','built','station','installed_material','physical','material','operational','service'):
                    if key in frame.f_locals:
                        walk(frame.f_locals[key], 'failed_check_inputs.'+frame.f_code.co_name+'.'+key)
            tb=tb.tb_next
        for row in rows:
            row['producer_gate_passed']=False
            row['classification']='FAILED_PRODUCER_REFERENCE_INPUT'
    modules = {}
    for name, module in sorted(sys.modules.items()):
        f = getattr(module, '__file__', None)
        if (name.startswith('masck_one') or name.startswith('studies')) and f:
            p = Path(f).resolve()
            if not p.is_relative_to(source_root.resolve()):
                raise RuntimeError('mixed owner import: ' + str(p))
            relative = p.relative_to(source_root).as_posix()
            modules[relative] = {'sha256': sha256(p.read_bytes()).hexdigest(),
                'git_blob': subprocess.check_output(['git','hash-object',str(p)],text=True).strip()}
    result['loaded_source_files'] = modules
    result['runtime'] = {'python': sys.version, 'cadquery': cq.__version__}
    (output / 'owner_geometry.json').write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
    print(json.dumps({k:result[k] for k in ('owner','head','status')}), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('owner'); p.add_argument('source_root',type=Path)
    p.add_argument('output',type=Path); p.add_argument('head')
    args = p.parse_args()
    extract(args.owner, args.source_root, args.output, args.head)
