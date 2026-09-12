"""PR 158 reproducible proof campaign. No production geometry or human fit claim.

Rigid residual capacity and normal accommodation are counterfactual study inputs.
They do not qualify a manufactured aperture, support, seal, or capture mechanism.
"""
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
import json
import math
import subprocess

import numpy as np
from scipy.optimize import minimize

from .adversarial_fit_proof import (
    ROOT, BOUNDS, Variation, FitProofError, source_snapshot, face, digest,
    nominal_landmarks, warp, transform, solve_registration, capacity_result,
    pair_distance_lower_bound, adversarial_search, boundary_search, alignment_rank,
)
from .adversarial_fit_campaign import save, surface_demand, capture_slices, visualise

SEED = 20260912
MODULES = ('adversarial_fit_proof.py', 'adversarial_fit_geometry.py',
           'adversarial_fit_campaign.py', 'adversarial_fit_study.py')
UNKNOWN = ('UNKNOWN_SOURCE_GEOMETRY', 'UNKNOWN_COMPLIANCE', 'PHYSICAL_VALIDATION_REQUIRED')


def code_identity():
    return {p: sha256(Path(__file__).with_name(p).read_bytes()).hexdigest() for p in MODULES}


def provenance():
    s = source_snapshot()
    return {'main': s['main'], 'original_analyzed_main': s.get('original_analyzed_main', s['main']),
            'pr': 158, 'branch': 'proof/adversarial-fit-20260912',
            'analysis_checkout_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
            'code_hashes': code_identity(), 'snapshot_digest': digest(s),
            'geometry_identities': [r for r in s['consumed_files'] if not r['path'].startswith('docs/')],
            'coordinate_frame': s['coordinate_frame'], 'evidence': 'SYNTHETIC_DIGITAL_ONLY'}


def source_status(root=ROOT):
    try:
        source_snapshot(root)
    except (FitProofError, FileNotFoundError, ValueError) as e:
        return {'status': 'UNKNOWN_SOURCE_GEOMETRY', 'reason': str(e), 'may_execute': False}
    return {'status': 'VERIFIED_INPUT_IDENTITIES', 'may_execute': True}


def endpoint_status(r, capacity=None):
    """Endpoint evidence and actual passive capture are different propositions."""
    conditional = capacity_result(r, capacity) if capacity is not None else None
    if conditional == 'PROVEN_RIGID_CAPACITY_FAILURE':
        status = 'PROVEN_DIGITAL_FAILURE'
    elif r.get('max_residual_mm') is not None:
        status = 'NUMERICAL_CANDIDATE'
    else:
        status = 'NUMERICAL_INDETERMINATE'
    return {'FINAL_REGISTRATION_FEASIBILITY': status,
            'conditional_capacity_classification': conditional,
            'assumed_local_residual_capacity_mm': capacity,
            'capacity_is_qualified': False,
            'PASSIVE_CAPTURE_STATUS': 'UNKNOWN', 'whole_product_fit': 'UNKNOWN',
            'unresolved': list(UNKNOWN), 'continuous_acquisition_proved': False}


def metrics(v, pose):
    nom = np.array(list(nominal_landmarks().values()))
    vector = transform(warp(nom, v), pose) - nom
    residual = np.linalg.norm(vector, axis=1)
    surface = surface_demand(v, {'pose': pose})
    return {'residual_vector_xyz_mm': dict(zip(nominal_landmarks(), vector.tolist())),
            'residual_norm_mm': dict(zip(nominal_landmarks(), residual.tolist())),
            'max_mm': float(residual.max()), 'rms_mm': float(np.sqrt(np.mean(residual**2))),
            'surface': surface}


def make_witness(name, v, initial=(0.,)*6, registration=None, capacity=None,
                 method='minimax', indices=None, multistart=False):
    r = registration or solve_registration(v, initial=initial, multistart=multistart)
    posed = metrics(v, r['pose']) if r.get('pose') is not None else None
    return {'schema': 'MASCK_FIT_WITNESS_2', 'id': name, 'provenance': provenance(),
            'generator_revision': code_identity()['adversarial_fit_proof.py'],
            'parameters': asdict(v), 'parameter_bounds': face(v)['bounds'],
            'initial_transform': list(initial), 'solved_transform': r.get('pose'),
            'allowable_pose_limits': r.get('pose_limits'), 'active_adjustment_state': r.get('adjustments'),
            'method': method, 'sparse_indices': indices, 'solver_seed': SEED,
            'solver_configuration': {'multistart': multistart, 'initial_only': False},
            'registration': r, 'measurements': posed, 'classification': endpoint_status(r, capacity),
            'affected_domains': {'protected': list(nominal_landmarks()),
                'required_regions': 'UNKNOWN_CS015_TO_MEASURED_SURFACE_REGISTRATION'},
            'perturbation_from_nominal_normalized_l2': v.normalized_distance,
            'nearest_qualified_passing_case': None,
            'physical_results': None, 'film_access_or_population_claim': False}


def replay(w):
    if w.get('schema') != 'MASCK_FIT_WITNESS_2':
        raise FitProofError('unsupported witness schema')
    p = w['provenance']; s = source_snapshot()
    if p['snapshot_digest'] != digest(s) or p['main'] != s['main'] or p['code_hashes'] != code_identity():
        raise FitProofError('stale source/generator identity; do not silently replay another revision')
    if set(w['parameters']) != set(BOUNDS):
        raise FitProofError('complete parameter vector required')
    v = Variation(**w['parameters'])
    if w['method'] == 'sparse':
        r = sparse_registration(v, w['sparse_indices'], w['initial_transform'])
    elif w['method'] == 'minimax':
        r = solve_registration(v, initial=w['initial_transform'], multistart=w['solver_configuration']['multistart'])
    else:
        raise FitProofError('unknown witness method')
    result = make_witness(w['id'], v, w['initial_transform'], r,
        w['classification']['assumed_local_residual_capacity_mm'], w['method'], w['sparse_indices'],
        w['solver_configuration']['multistart'])
    result['provenance'] = w['provenance']
    return result


def sparse_registration(v, indices=(0, 1), initial=(0.,)*6):
    """Counterexample observables, never permission to ignore other anatomy."""
    nom = np.array(list(nominal_landmarks().values())); points = warp(nom, v)
    indices = tuple(indices)
    if not indices or any(i not in range(len(nom)) for i in indices):
        raise FitProofError('invalid sparse observable set')
    from .authority import load_authority
    a = load_authority(); radius = a.number('geometry', 'misregistration', 'translation_radial_max_mm')
    angle = a.number('geometry', 'misregistration', 'rotation_max_deg')
    bounds = [(-radius, radius)]*2 + [(0., 0.)] + [(-angle, angle)]*3 + [(0., 200.)]
    def residual(x): return np.linalg.norm(transform(points, x[:6])-nom, axis=1)
    def constraints(x): return np.r_[radius**2-x[0]**2-x[1]**2, x[6]-residual(x)[list(indices)]]
    seeds = [np.array(initial, float), np.zeros(6)]
    for sign in (-1, 1):
        for axis in (3, 4, 5):
            q = np.zeros(6); q[axis] = sign*angle; seeds.append(q)
    candidates = []
    for seed in seeds:
        seed = np.array([np.clip(x, *b) for x, b in zip(seed, bounds)])
        if np.linalg.norm(seed[:2]) > radius: seed[:2] *= radius/np.linalg.norm(seed[:2])
        r = minimize(lambda x: x[-1], np.r_[seed, max(residual(seed)[list(indices)])+.01],
            method='SLSQP', bounds=bounds, constraints={'type': 'ineq', 'fun': constraints},
            options={'maxiter': 200, 'ftol': 1e-9})
        if min(constraints(r.x)) >= -1e-6:
            candidates.append((float(max(residual(r.x)[list(indices)])), r.x[:6].tolist(), bool(r.success)))
    if not candidates: return {'status': 'NUMERICAL_INDETERMINATE'}
    candidates.sort(key=lambda q: (q[0], q[1])); value, pose, converged = candidates[0]
    near = [q for error, q, _ in candidates if error <= value+1e-5]
    return {'status': 'SPARSE_NUMERICAL_CANDIDATE_NOT_SEATING', 'pose': pose,
            'observed_max_residual_mm': value, 'max_residual_mm': float(max(residual(pose))),
            'sparse_indices': list(indices), 'optimizer_converged': converged,
            'near_equal_pose_candidates': near,
            'near_equal_translation_span_mm': np.ptp(np.array(near)[:, :3], axis=0).tolist(),
            'near_equal_rotation_span_deg': np.ptp(np.array(near)[:, 3:], axis=0).tolist(),
            'rigid_invariant_bound': pair_distance_lower_bound(points, nom),
            'pose_limits': {'xy_radius_mm': radius, 'z_mm': 0, 'extrinsic_xyz_each_deg': angle},
            'adjustments': {'existing_product_adjustments': []}, 'whole_fit': 'UNKNOWN'}


def false_seat_search(cases):
    """Select maximum unobserved mismatch inside an explicitly hypothetical band."""
    rows = []
    for name, v, r in cases:
        if 'pose' not in r: continue
        m = metrics(v, r['pose'])
        rows.append({'case': name, 'parameters': asdict(v), 'registration': r, 'metrics': m})
    candidates = [r for r in rows if r['metrics']['max_mm'] <= 1.]
    strongest = max(candidates, key=lambda q: q['metrics']['surface'].get('maximum_absolute_z_mm', -math.inf)) if candidates else None
    return {'search': 'MAX_SURFACE_DEPARTURE_GIVEN_HYPOTHETICAL_1MM_LANDMARK_OBSERVATION_BAND',
            'observation_band_qualified': False, 'cases': rows, 'strongest': strongest,
            'false_seated_physical_state_proven': False,
            'meaning': 'Counterexample to landmark-only surface-fit inference'}


# Cost vector entries are scenario assumptions, not measured cost or convenience.
# [added DOFs, independently adjusted elements, user settings upper bound,
#  extra SKUs, coupled subsystem groups, regional moving interfaces]
CAPABILITIES = {
    'CURRENT': {'cost': [0, 0, 0, 0, 0, 0]},
    'GLOBAL_Z10': {'z': 10., 'cost': [1, 1, 1, 0, 1, 0]},
    'XY8': {'xy': 8., 'cost': [2, 1, 2, 0, 1, 0]},
    'ANGLES6': {'angle': 6., 'cost': [3, 1, 3, 0, 1, 0]},
    'BILATERAL_Z5': {'bilateral': 5., 'cost': [2, 2, 2, 0, 3, 2]},
    'LOCAL_NORMAL5': {'local': 5., 'cost': [5, 5, 5, 0, 3, 5]},
    'SIZES_100_105': {'scales': [1., 1.05], 'cost': [0, 0, 0, 1, 4, 0]},
    'SIZES_095_100_105': {'scales': [.95, 1., 1.05], 'cost': [0, 0, 0, 2, 4, 0]},
    'SIZE_AND_LOCAL': {'scales': [1., 1.05], 'local': 5., 'cost': [5, 5, 5, 1, 4, 5]},
}


def capability_registration(v, capability, scale=1.):
    """Minimax relaxation of interface requirements, not manufactured geometry.

    Local normal travel is analytically eliminated by projection onto its interval.
    Five independently floating targets are a deliberately optimistic lower burden
    relaxation; their coherence, protection and surface continuity remain UNKNOWN.
    """
    from .authority import load_authority
    a = load_authority(); xy = capability.get('xy', a.number('geometry', 'misregistration', 'translation_radial_max_mm'))
    angle = capability.get('angle', a.number('geometry', 'misregistration', 'rotation_max_deg'))
    z = capability.get('z', 0.); local = capability.get('local', 0.); bilateral = capability.get('bilateral', 0.)
    nom = np.array(list(nominal_landmarks().values())); target = nom*np.array([scale, scale, 1.])
    p = warp(nom, v); signs = np.sign(nom[:, 0])
    bounds = [(-xy, xy)]*2 + [(-z, z)] + [(-angle, angle)]*3 + [(-bilateral, bilateral)]*2 + [(0., 200.)]
    def residual(x):
        delta = transform(p, x[:6])-target
        delta[:, 2] -= np.where(signs < 0, x[6], np.where(signs > 0, x[7], 0.))
        delta[:, 2] -= np.clip(delta[:, 2], -local, local)
        return np.linalg.norm(delta, axis=1)
    def cons(x): return np.r_[xy**2-x[0]**2-x[1]**2, x[-1]-residual(x)]
    seeds = [np.zeros(8)]
    base = solve_registration(v, multistart=False)
    if base.get('pose') is not None: seeds.append(np.r_[base['pose'], 0., 0.])
    candidates = []
    for seed in seeds:
        r = minimize(lambda x: x[-1], np.r_[seed, max(residual(seed))+.01], method='SLSQP',
            bounds=bounds, constraints={'type': 'ineq', 'fun': cons}, options={'maxiter': 200, 'ftol': 1e-9})
        if min(cons(r.x)) >= -1e-6:
            candidates.append((float(max(residual(r.x))), r.x.tolist(), bool(r.success)))
    if not candidates: return {'status': 'NUMERICAL_INDETERMINATE', 'residual_mm': None}
    candidates.sort(key=lambda q: (q[0], q[1])); value, q, converged = candidates[0]
    return {'status': 'NUMERICAL_CAPABILITY_RELAXATION', 'residual_mm': value,
            'pose': q[:6], 'bilateral_offsets_mm': q[6:8], 'normal_interval_mm': local,
            'scale': scale, 'optimizer_converged': converged,
            'rigid_lower_bound_mm': None if local or bilateral else pair_distance_lower_bound(p, target)['lower_bound_mm'],
            'whole_fit': 'UNKNOWN', 'passive_capture': 'UNKNOWN',
            'anatomy_support_requalification_required': True}


def pareto_front(rows, band):
    """Componentwise cost and conditional performance dominance; no magic weights."""
    def vector(r): return [*r['cost'], -r['within_assumed_capacity'][str(band)], r['worst_attempted_residual_mm']]
    good = [r for r in rows if r['numerical_unknowns'] == 0]
    return [r['capability'] for r in good if not any(
        all(a <= b for a, b in zip(vector(s), vector(r))) and any(a < b for a, b in zip(vector(s), vector(r)))
        for s in good if s is not r)]


def adaptability(cases):
    rows = []
    for name, c in CAPABILITIES.items():
        evaluated = []
        for label, v, base in cases:
            if name == 'CURRENT':
                result = {'residual_mm': base.get('max_residual_mm'), 'pose': base.get('pose'),
                          'status': base['status'], 'rigid_lower_bound_mm': base.get('rigid_invariant_bound', {}).get('lower_bound_mm')}
            else:
                choices = [capability_registration(v, c, scale) for scale in c.get('scales', [1.])]
                result = min(choices, key=lambda r: r['residual_mm'] if r['residual_mm'] is not None else math.inf)
            evaluated.append({'case': label, **result})
        values = [r['residual_mm'] for r in evaluated if r['residual_mm'] is not None]
        rows.append({'capability': name, 'cost': c['cost'], 'inputs': c, 'cases': evaluated,
            'within_assumed_capacity': {str(t): sum(x <= t+1e-6 for x in values) for t in (1., 3., 5.)},
            'worst_attempted_residual_mm': max(values) if values else None,
            'numerical_unknowns': len(cases)-len(values), 'actual_whole_fit_cases_resolved': 0,
            'actual_capture_cases_resolved': 0, 'false_seat_ambiguity_resolved': 0,
            'remaining_failures': ['registered_surface', 'protected_depth', 'support_seal', 'required_access', 'passive_alignment']})
    return {'recommendation': 'NO_DIGITAL_ADAPTABILITY_CHANGE_JUSTIFIED_YET',
            'reason': 'All are conditional landmark relaxations; none closes source/mechanical unknowns.',
            'same_case_count': len(cases), 'candidates': rows,
            'cost_axes': ['added_DOF', 'independent_elements', 'user_settings_upper_bound', 'extra_SKUs', 'coupled_groups', 'regional_moving_interfaces'],
            'cost_evidence': 'EXPLICIT_UNQUALIFIED_SCENARIO_VECTOR_NOT_UNIT_COST_OR_USER_RESEARCH',
            'pareto_by_assumed_capacity': {str(t): pareto_front(rows, t) for t in (1., 3., 5.)},
            'capacity_qualification': None,
            'sparse_alignment': {'two_eye_points': alignment_rank(np.array(list(nominal_landmarks().values()))[:2]),
                'plus_noncollinear_datum': alignment_rank(np.array(list(nominal_landmarks().values()))[[0, 1, 4]]),
                'decision': 'Add observability to the experiment, not unqualified production hardware',
                'new_adjustment_DOF': 0, 'physical_alignment_mechanism': 'UNKNOWN'},
            'increased_travel_ambiguity': 'Expanded admissible states cannot establish unique seating; contact law missing'}


def build_case_set():
    cases = [('NOMINAL', Variation())]
    for name, (lo, hi) in BOUNDS.items():
        cases += [(name+'_LOW', Variation(**{name: lo})), (name+'_HIGH', Variation(**{name: hi}))]
    cases.append(('COMBINED_MODERATE', Variation(face_width=8, eye_spacing=6)))
    rng = np.random.default_rng(SEED)
    cases += [(f'COUPLED_{i:03}', Variation(**{k: float(rng.uniform(lo*.5, hi*.5)) for k, (lo, hi) in BOUNDS.items()})) for i in range(16)]
    return cases


def write_manifest(output, summary):
    summary['artifacts'] = {str(p.relative_to(output)): sha256(p.read_bytes()).hexdigest()
        for p in sorted(output.rglob('*')) if p.is_file() and p.name != 'manifest.json'}
    save(output/'manifest.json', summary)


def validate_manifest(output):
    m = json.loads((output/'manifest.json').read_text())
    for path, expected in m['artifacts'].items():
        p = (output/path).resolve()
        if not p.is_relative_to(output.resolve()) or not p.is_file() or sha256(p.read_bytes()).hexdigest() != expected:
            raise FitProofError('artifact missing or modified: '+path)
    return m


def run(output, capabilities=False):
    output.mkdir(parents=True, exist_ok=True)
    base = [(name, v, solve_registration(v, multistart=False)) for name, v in build_case_set()]
    witnesses = [make_witness(name, v, registration=r) for name, v, r in base]
    save(output/'case_set.json', witnesses)
    adv = adversarial_search(); save(output/'adversary_search.json', adv)
    w = make_witness('ADAPTIVE_RIGID_BOUND', Variation(**adv['variation']), registration=adv['registration'], capacity=3., multistart=True)
    save(output/'witnesses/adversary.json', w)
    boundary = boundary_search('eye_spacing', 12., 3.)
    save(output/'boundary.json', boundary)
    for state, key in [('candidate', 'nearest_candidate_value'), ('failure', 'nearest_nonpassing_value')]:
        save(output/f'witnesses/eye_spacing_{state}.json', make_witness('EYE_SPACING_'+state,
             Variation(eye_spacing=boundary[key]), capacity=3.))
    false = false_seat_search(base); save(output/'false_seat_search.json', false)
    if false['strongest']:
        q = false['strongest']; save(output/'witnesses/false_surface.json', make_witness('FALSE_SURFACE', Variation(**q['parameters']), registration=q['registration']))
    v = Variation(mouth_y=10); r = sparse_registration(v)
    save(output/'witnesses/eyes_hide_mouth.json', make_witness('EYES_HIDE_MOUTH', v, registration=r, method='sparse', indices=[0, 1]))
    v = Variation(asymmetry=8); save(output/'witnesses/asymmetry.json', make_witness('ASYMMETRY_REPRODUCTION', v))
    capture = capture_slices(Variation())
    for row in capture['rows']:
        row.update(endpoint_status({'max_residual_mm': row['numerical_residual_mm']}))
    coupled = []
    for v in (Variation(asymmetry=8), Variation(face_width=8, eye_spacing=6), Variation(bridge_projection=14)):
        for axis in range(6):
            for sign in (-1, 1):
                pose = [0.]*6; pose[axis] = sign*(6. if axis < 3 else 5.)
                r = solve_registration(v, initial=pose, initial_only=True, multistart=False)
                coupled.append({'parameters': asdict(v), 'initial_pose': pose, 'registration': r, **endpoint_status(r)})
    capture['morphology_plus_pose_cases'] = coupled
    capture['total_starts'] = len(capture['rows'])+len(coupled)
    save(output/'capture.json', capture)
    initial = (5., 0., 0., 4., -4., 4.)
    save(output/'witnesses/initial_to_solved.json', make_witness('INITIAL_TO_SOLVED', Variation(asymmetry=8), initial))
    visualise(output, [(n,v) for n,v,r in base], {n:r for n,v,r in base}, capture, adv)
    extra_visuals(output)
    if capabilities: save(output/'adaptability.json', adaptability(base))
    summary = {'schema': 'MASCK_FIT_STUDY_2', 'provenance': provenance(),
        'decision': 'D_DIGITAL_INDETERMINATE', 'synthetic_cases': len(base),
        'adaptive_evaluations': adv['evaluations'], 'initial_pose_cases': capture['total_starts'],
        'capacity_bands_are_unqualified': True, 'physical_results': None,
        'source_dependencies': source_snapshot()['unresolved'], 'passive_capture_proven': 0}
    write_manifest(output, summary)
    return summary


def extra_visuals(output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), layout='constrained')
    for ax, file in zip(axes, ['eye_spacing_candidate', 'eye_spacing_failure']):
        w = json.loads((output/f'witnesses/{file}.json').read_text())
        v = Variation(**w['parameters']); target = np.array(list(nominal_landmarks().values()))
        p = transform(warp(target, v), w['solved_transform'])
        ax.scatter(*target[:,:2].T, facecolors='none', edgecolors='#243e52', label='Reference')
        ax.scatter(*p[:,:2].T, marker='+', color='#b1463b', label='Solved synthetic')
        for a,b in zip(target,p): ax.plot([a[0],b[0]], [a[1],b[1]], color='#888888')
        ax.set(title=file+f"\nSpacing delta {v.eye_spacing:.9f} mm", xlabel='X / mm', ylabel='Y / mm', aspect='equal'); ax.legend(fontsize=7)
    fig.suptitle('Conditional 3 mm landmark capacity only. Neither panel proves product fit.')
    fig.savefig(output/'nearest_boundary.svg'); plt.close(fig)
    w = json.loads((output/'witnesses/false_surface.json').read_text()); v = Variation(**w['parameters'])
    f = face(v, include_mesh=True); q = transform(f['vertices'], w['solved_transform'])
    fig, ax = plt.subplots(figsize=(6, 6), layout='constrained')
    sc = ax.scatter(q[:,0], q[:,1], c=q[:,2], cmap='coolwarm', s=3, rasterized=True)
    pts = transform(np.array(list(face(v)['landmarks'].values())), w['solved_transform'])
    ax.scatter(*pts[:,:2].T, marker='x', c='black', label='Sparse landmarks')
    ax.set(title='False surface-fit confidence: synthetic reference only', xlabel='X / mm', ylabel='Y / mm', aspect='equal')
    fig.colorbar(sc, ax=ax, label='Departure from planar reference / mm'); ax.legend()
    fig.savefig(output/'false_seat_surface.svg'); plt.close(fig)
    w = json.loads((output/'witnesses/initial_to_solved.json').read_text()); f = face(Variation(**w['parameters']))
    pts = np.array(list(f['landmarks'].values()))
    fig, ax = plt.subplots(figsize=(6, 6), layout='constrained')
    for pose, label, marker in [(w['initial_transform'], 'Initial', '+'), (w['solved_transform'], 'Numerical endpoint', 'o')]:
        q = transform(pts, pose); ax.scatter(*q[:,:2].T, label=label, marker=marker)
    ax.set(title='Synthetic pose projection; no physical path asserted', xlabel='X / mm', ylabel='Y / mm', aspect='equal'); ax.legend()
    fig.savefig(output/'initial_to_solved.svg'); plt.close(fig)
    cases = json.loads((output/'case_set.json').read_text())
    rays = [w for w in cases if w['id'].endswith(('_LOW','_HIGH'))]
    values = np.array([w['measurements']['max_mm'] for w in rays]).reshape(len(BOUNDS),2)
    fig, ax = plt.subplots(figsize=(7, 7), layout='constrained')
    im = ax.imshow(values, aspect='auto', cmap='magma'); ax.set_yticks(range(len(BOUNDS)), list(BOUNDS)); ax.set_xticks([0,1],['Synthetic low boundary','Synthetic high boundary'])
    ax.set_title('Parameter sensitivity, not population failure frequency')
    fig.colorbar(im, ax=ax, label='Maximum landmark residual / mm')
    fig.savefig(output/'parameter_sensitivity.svg'); plt.close(fig)


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('output', type=Path)
    p.add_argument('--replay', type=Path); p.add_argument('--capabilities', action='store_true'); p.add_argument('--verify', action='store_true')
    a = p.parse_args()
    if a.verify: print(json.dumps(validate_manifest(a.output)['decision']))
    elif a.replay: save(a.output, replay(json.loads(a.replay.read_text())))
    else: print(json.dumps({k:v for k,v in run(a.output, a.capabilities).items() if k not in ('artifacts','provenance')}))
