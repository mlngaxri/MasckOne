"""Read-only exact-owner geometry extraction, in an isolated source checkout.

Run with that checkout's src on PYTHONPATH. A producer exception is retained as
missing geometry evidence, never converted into empty/clear material.
"""
from dataclasses import fields, is_dataclass
from hashlib import sha256
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import traceback

import cadquery as cq


SUPPORTED_OWNERS = frozenset(('treatment', 'retention', 'frame', 'thermal', 'exterior', 'fluid'))


def _git(root, *args):
    return subprocess.check_output(
        ['git', '--no-replace-objects', '--literal-pathspecs', '-C', str(root), *args],
        stderr=subprocess.PIPE,
    )


def verify_checkout(source_root, head):
    if not isinstance(head, str) or re.fullmatch(r'[0-9a-f]{40}', head) is None:
        raise ValueError('exact lowercase 40-hex owner commit required')
    if _git(source_root, 'rev-parse', 'HEAD').decode().strip() != head:
        raise ValueError('source checkout HEAD differs from requested owner commit')
    if _git(source_root, 'status', '--porcelain', '--untracked-files=no').strip():
        raise ValueError('tracked source checkout is dirty')
    return _git(source_root, 'rev-parse', head + '^{tree}').decode().strip()


def verify_loaded_sources(source_root, head, modules=None):
    verified = {}
    for name, module in sorted((sys.modules if modules is None else modules).items()):
        f = getattr(module, '__file__', None)
        if (name == 'masck_one' or name.startswith('masck_one.')
                or name == 'studies' or name.startswith('studies.')) and f:
            p = Path(f).resolve()
            if not p.is_relative_to(source_root.resolve()):
                raise ValueError('mixed owner import: ' + str(p))
            relative = p.relative_to(source_root).as_posix()
            entry = _git(source_root, 'ls-tree', '-z', head, '--', relative).rstrip(b'\0')
            if not entry:
                raise ValueError('loaded module is not tracked at owner commit: ' + relative)
            metadata, tracked_path = entry.split(b'\t', 1)
            mode, kind, blob = metadata.decode().split()
            if mode not in ('100644', '100755') or kind != 'blob' or tracked_path.decode() != relative:
                raise ValueError('loaded module is not a regular source blob: ' + relative)
            data = _git(source_root, 'cat-file', 'blob', blob)
            if data != p.read_bytes():
                raise ValueError('loaded source bytes differ from owner commit: ' + relative)
            verified[relative] = {'head': head, 'sha256': sha256(data).hexdigest(), 'git_blob': blob}
    return verified


def extract(owner, source_root, output, head):
    source_root = source_root.resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError('fresh output directory required; previous evidence must be preserved')
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    result = {'owner': owner, 'head': head, 'status': 'UNKNOWN',
              'participants': rows, 'evidence': 'DIGITAL', 'physical_result': None,
              'human_use_eligible': False, 'capability_status': 'UNRESOLVED_OWNER_CAPABILITY',
              'capability_blockers': ['REGISTERED_ACTION_FOOTPRINTS_NOT_ESTABLISHED'],
              'source_binding_status': 'UNVERIFIED', 'loaded_source_files': {}}
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
        result['source_tree'] = verify_checkout(source_root, head)
        verify_loaded_sources(source_root, head)
        result['source_binding_status'] = 'EXACT_CHECKOUT_VERIFIED'
    except Exception as exc:
        result['status'] = 'SOURCE_BINDING_FAILED'
        result['error'] = type(exc).__name__ + ': ' + str(exc)
        return write_result(result, output)
    if owner not in SUPPORTED_OWNERS:
        result['status'] = 'UNRESOLVED_OWNER_CAPABILITY'
        result['capability_blockers'].append('UNSUPPORTED_OWNER_EXTRACTOR')
        return write_result(result, output)
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
        elif owner == 'thermal':
            from masck_one.thermal_reset_hardware import build_thermal_reset_hardware
            parts, refs, geometry = build_thermal_reset_hardware()
            walk(parts, 'material_parts'); walk(refs, 'reference_parts')
            result['geometry_report'] = geometry
            result['installed_facial_transform'] = None
        elif owner == 'exterior':
            from masck_one.authority import load_authority
            from masck_one.anatomy import build_facial_reference
            from masck_one.exterior_surface import build_refined_exterior_shell
            authority = load_authority()
            walk(build_refined_exterior_shell(authority, build_facial_reference(authority)),
                 'material_parts.exterior_shell')
        elif owner == 'fluid':
            from masck_one.wet_electrical_source_graph import build_wet_electrical_source_graph
            result['graph'] = build_wet_electrical_source_graph().manifest()
            # A route graph is not manufactured tubing, a seal, or an affected-cell footprint.
            result['capability_blockers'].append('FLUID_GRAPH_HAS_NO_REGISTERED_CONTACT_BREP')
        result['status'] = 'EXTRACTED_NOT_INTEGRATION_APPROVAL'
        if owner == 'fluid':
            result['status'] = 'OWNER_GRAPH_EXTRACTED_GEOMETRY_UNRESOLVED'
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
    try:
        verify_checkout(source_root, head)
        result['loaded_source_files'] = verify_loaded_sources(source_root, head)
        result['source_binding_status'] = 'EXACT_CHECKOUT_AND_LOADED_BLOBS_VERIFIED'
    except Exception as exc:
        result['status'] = 'SOURCE_BINDING_FAILED'
        result['source_binding_status'] = 'FAILED'
        result['source_error'] = type(exc).__name__ + ': ' + str(exc)
        for row in rows:
            row['producer_gate_passed'] = False
            row['classification'] = 'UNBOUND_REFERENCE_INPUT'
    return write_result(result, output)


def write_result(result, output):
    result['runtime'] = {'python': sys.version, 'cadquery': cq.__version__}
    result['extractor_sha256'] = sha256(Path(__file__).read_bytes()).hexdigest()
    (output / 'owner_geometry.json').write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
    print(json.dumps({k:result[k] for k in ('owner','head','status')}), flush=True)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('owner'); p.add_argument('source_root',type=Path)
    p.add_argument('output',type=Path); p.add_argument('head')
    args = p.parse_args()
    result = extract(args.owner, args.source_root, args.output, args.head)
    raise SystemExit(0 if result['status'] == 'EXTRACTED_NOT_INTEGRATION_APPROVAL' else 2)
