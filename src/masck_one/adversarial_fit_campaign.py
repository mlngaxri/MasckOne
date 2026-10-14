"""Reproducible bounded fit campaign and debug exports. Analysis only."""
from dataclasses import asdict
from pathlib import Path
from hashlib import sha256
import json
import math
import sys
import numpy as np
from .adversarial_fit_proof import (
    Variation, BOUNDS, ROOT, source_snapshot, face, nominal_landmarks, warp, transform,
    solve_registration, capacity_result, alignment_rank, boundary_search,
    adversarial_search, pair_distance_lower_bound, assess,
)


def save(path, data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2,sort_keys=True,allow_nan=False)+'\n')


def smallest_found(adversary, capacity_mm=3.):
    """Shrink and prune a proven conditional failure. No global optimum claim."""
    nom=np.array(list(nominal_landmarks().values()))
    vector=dict(adversary['variation'])
    def failed(d):return pair_distance_lower_bound(warp(nom,Variation(**d)),nom)['lower_bound_mm']>capacity_mm+1e-6
    if not failed(vector):return None
    # Remove independent mechanisms of failure before reducing the remaining ray.
    for key in sorted(vector,key=lambda k:abs(vector[k])):
        candidate={**vector,key:0.}
        if failed(candidate):vector=candidate
    lo,hi=0.,1.
    for _ in range(30):
        mid=(lo+hi)/2
        if failed({k:v*mid for k,v in vector.items()}):hi=mid
        else:lo=mid
    v=Variation(**{k:x*hi for k,x in vector.items()})
    r=solve_registration(v)
    return {'parameters':asdict(v),'normalized_perturbation':v.normalized_distance,
            'source_main':face(v)['source_main'],'generator_sha256':face(v)['generator_sha256'],
            'source_snapshot_digest':face(v)['source_snapshot_digest'],'frame':face(v)['frame'],
            'conditional_capacity_mm':capacity_mm,'registration':r,
            'proof':'Rigid-distance invariant exceeds assumed local residual capacity',
            'lower_ray_scale':lo,'upper_ray_scale':hi,'scale_bracket':hi-lo,
            'minimum_claim':'SMALLEST_ON_PRUNED_EXPLORED_RAY_NOT_GLOBAL',
            'physical_failure_claimed':False}


def capture_slices(v, grid=7):
    """Optimizer-start sensitivity only. Existing passive capture policy absent."""
    rows=[]
    slices=[('XY',0,1,np.linspace(-8,8,grid)),('RX_RY',3,4,np.linspace(-6,6,grid)),
            ('Z_RZ',2,5,np.linspace(-6,6,grid))]
    for name,i,j,values in slices:
        for a in values:
            for b in values:
                initial=np.zeros(6);initial[i]=a;initial[j]=b
                r=solve_registration(v,initial=initial,initial_only=True,multistart=False)
                rows.append({'slice':name,'a':float(a),'b':float(b),'initial_pose':initial.tolist(),
                    'registered_pose':r.get('pose'),'numerical_residual_mm':r.get('max_residual_mm'),
                    'optimizer_converged':r.get('optimizer_converged',False),
                    'capture_status':'UNKNOWN_PASSIVE_KINEMATICS_AND_CONTACT_LAWS',
                    'initial_z_defined_by_authority':bool(initial[2]==0),
                    'continuous_path_proved':False,'physically_recoverable':None})
    return {'scope':'NUMERICAL_SEED_BASIN_NOT_MECHANICAL_CAPTURE','rows':rows,
            'robustly_recoverable_proven':0,'marginally_recoverable_proven':0,
            'unknown':len(rows),'evidence_boundary':'No source-bound guide/contact transition law; endpoint optimization cannot prove acquisition'}


def compare_capabilities(cases, base_results):
    """Abstract interface requirements only; no canonical CAD is changed."""
    variants={
        'CURRENT_RIGID':{'new_dofs':0,'sizes':1,'user_adjustments':0,'subsystem_coupling':'CURRENT'},
        'ONE_GLOBAL_Z':{'new_dofs':1,'sizes':1,'user_adjustments':None,'subsystem_coupling':'WHOLE_FRONT'},
        'TWO_PROPORTIONAL_REFERENCE_SIZES':{'new_dofs':0,'sizes':2,'user_adjustments':0,'subsystem_coupling':'REQUALIFY_ALL_APERTURES'},
    }
    rows=[];size_grid_rows=[]
    for label,v in cases:
        base=base_results[label]
        z=solve_registration(v,extra_z_mm=10,multistart=False)
        sizes=[solve_registration(v,target_scale=(s,s),multistart=False) for s in (.95,1.05)]
        size_grid_rows.append({'case':label,'residual_by_scale':{
            '0.95':sizes[0].get('max_residual_mm'),'1.0':base.get('max_residual_mm'),
            '1.05':sizes[1].get('max_residual_mm')}})
        sized=min(sizes,key=lambda r:r.get('max_residual_mm',math.inf))
        for name,result in [('CURRENT_RIGID',base),('ONE_GLOBAL_Z',z),('TWO_PROPORTIONAL_REFERENCE_SIZES',sized)]:
            rows.append({'case':label,'variant':name,'residual_mm':result.get('max_residual_mm'),
                         'capacity_sensitivity':{str(b):capacity_result(result,b) for b in (1.,3.,5.)},
                         'whole_fit':'UNKNOWN'})
    totals={name:{str(b):sum(r['capacity_sensitivity'][str(b)]=='CANDIDATE_WITHIN_ASSUMED_CAPACITY'
              for r in rows if r['variant']==name) for b in (1.,3.,5.)} for name in variants}
    pair_counts={}
    for a,b in [('0.95','1.0'),('1.0','1.05'),('0.95','1.05')]:
        pair_counts[a+'+'+b]={str(t):sum(min(r['residual_by_scale'][a] if r['residual_by_scale'][a] is not None else math.inf,
            r['residual_by_scale'][b] if r['residual_by_scale'][b] is not None else math.inf)<=t+1e-6
            for r in size_grid_rows) for t in (1.,3.,5.)}
    return {'variant_complexity':variants,'cases':len(cases),'rows':rows,'within_counterfactual_capacity':totals,
            'two_size_grid_search_counts':pair_counts,'size_grid_rows':size_grid_rows,
            'capacity_bands_mm':[1,3,5],'capacity_qualification':'NONE_SENSITIVITY_ONLY',
            'z_capability_mm':10,'size_scales':[.95,1.05],
            'scale_qualification':'SYNTHETIC_REFERENCE_TARGETS_NOT_MANUFACTURED_SIZES',
            'minimum_sufficient_production_adaptability':None,
            'selection_rule':'Pareto compare residual reduction, extra DOFs, size inventory and user burden; no arbitrary combined cost score',
            'missing':'Aperture/support/region-access constraints must be re-evaluated before any capability is sufficient'}


def surface_demand(v, registration):
    """Residual shape versus the planar reference; not pressure or a support limit."""
    f=face(v,include_mesh=True)
    if f['folded_cells']:return {'status':'INVALID_SYNTHETIC_MESH','folded_cells':f['folded_cells']}
    posed=transform(f['vertices'],registration['pose']);z=posed[:,2]
    return {'status':'SYNTHETIC_REFERENCE_DEPARTURE_ONLY','z_min_mm':float(z.min()),
            'z_max_mm':float(z.max()),'z_span_mm':float(np.ptp(z)),
            'maximum_absolute_z_mm':float(np.max(np.abs(z))),
            'qualified_local_travel_mm':None,'seal_support_feasible':'UNKNOWN',
            'interpretation':'A small landmark residual cannot hide this remaining non-rigid shape demand'}


def visualise(output, cases, results, capture, adversary):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.tri import Triangulation
    fig,axes=plt.subplots(1,3,figsize=(13,4),layout='constrained')
    for ax,name in zip(axes,['XY','RX_RY','Z_RZ']):
        rows=[r for r in capture['rows'] if r['slice']==name]
        pts=ax.scatter([r['a'] for r in rows],[r['b'] for r in rows],c=[r['numerical_residual_mm'] if r['numerical_residual_mm'] is not None else math.nan for r in rows],
                       cmap='magma',s=70,edgecolor='#777777')
        ax.set(title=name+' starting-pose slice',xlabel='First coordinate (mm or deg)',ylabel='Second coordinate (mm or deg)')
        fig.colorbar(pts,ax=ax,label='Residual after numerical registration (mm)')
    fig.suptitle('Every mechanical capture state remains UNKNOWN. Numerical seeds are not a capture proof.',fontsize=11)
    fig.savefig(output/'capture_slices.svg');plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,5),subplot_kw={'projection':'3d'},layout='constrained')
    for ax,v,title in zip(axes,[Variation(),Variation(**adversary['variation'])],['Released planar reference','Adversarial synthetic reference']):
        f=face(v,include_mesh=True);q=np.array(f['vertices']);tri=np.array(f['triangles'])
        ax.plot_trisurf(q[:,0],q[:,1],q[:,2],triangles=tri,color='#b5c2c9',alpha=.65,linewidth=0,rasterized=True)
        pts=np.array(list(f['landmarks'].values()));ax.scatter(*pts.T,c='#b04040',s=22)
        ax.set(title=title,xlabel='+X right / mm',ylabel='+Y superior / mm',zlabel='+Z anterior / mm',zlim=(-15,35))
        ax.view_init(elev=22,azim=-70)
    fig.suptitle('Synthetic reference meshes only. No human fit or population evidence.',fontsize=11)
    fig.savefig(output/'morphology_comparison.svg');plt.close(fig)
    labels=[k for k,_ in cases];values=[results[k]['max_residual_mm'] for k in labels]
    fig,ax=plt.subplots(figsize=(10,max(4,len(labels)*.18)),layout='constrained')
    ax.barh(labels,values,color='#596c7e');ax.set(xlabel='Required minimax landmark accommodation (mm)',
       title='Residual demand, not fit pass rate. Qualified capacity remains UNKNOWN.')
    fig.savefig(output/'residual_demands.svg');plt.close(fig)


def campaign(output, random_cases=16, grid=7):
    source=source_snapshot();output.mkdir(parents=True,exist_ok=True)
    cases=[('NOMINAL',Variation())]
    for name,(lo,hi) in BOUNDS.items():
        cases.extend([(name+'_LOW',Variation(**{name:lo})),(name+'_HIGH',Variation(**{name:hi}))])
    cases.append(('COMBINED_MODERATE',Variation(face_width=8,eye_spacing=6)))
    rng=np.random.default_rng(20260912)
    for i in range(random_cases):
        params={k:float(rng.uniform(lo*.5,hi*.5)) for k,(lo,hi) in BOUNDS.items()}
        cases.append((f'COUPLED_{i:03}',Variation(**params)))
    results={};witnesses=[]
    for label,v in cases:
        r=solve_registration(v,multistart=False);results[label]=r
        witnesses.append({'case':label,'face':face(v),'starting_pose':[0]*6,
            'best_attempted_registration':r,'active_adjustments':[],
            'failed_constraints':[],'unresolved_constraints':assess({})['unknown'],
            'solver_status':r['status'],'minimum_perturbation_from_passing':None,
            'result':'DIGITAL_INDETERMINATE','evidence_class':'SYNTHETIC_DIGITAL'})
    save(output/'cases.json',witnesses)
    adversary=adversarial_search();save(output/'adversary.json',adversary)
    smallest=smallest_found(adversary);save(output/'smallest_conditional_witness.json',smallest)
    boundary=boundary_search('eye_spacing',12,3);save(output/'eye_spacing_boundary.json',boundary)
    capture=capture_slices(Variation(),grid);save(output/'capture.json',capture)
    capabilities=compare_capabilities(cases,results);save(output/'capabilities.json',capabilities)
    names=list(nominal_landmarks());nom=np.array(list(nominal_landmarks().values()))
    observability={'eye_only':alignment_rank(nom[:2]),'five_landmarks':alignment_rank(nom),
                   'meaning':'Potential datum strategy requirement, not a new sensor or retention mechanism'}
    save(output/'observability.json',observability)
    surface_demands={name:surface_demand(v,results[name]) for name,v in cases
                     if name in ('NOMINAL','asymmetry_HIGH','cheek_prominence_HIGH','bridge_projection_HIGH','COMBINED_MODERATE')}
    save(output/'surface_demands.json',surface_demands)
    visualise(output,cases,results,capture,adversary)
    summary={'schema':'MASCK_FIT_CAMPAIGN_1','main':source['main'],'source_snapshot_digest':digest_source(source),
             'generator_sha256':sha256(Path(__file__).with_name('adversarial_fit_proof.py').read_bytes()).hexdigest(),
             'campaign_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
             'decision':'D_DIGITAL_INDETERMINATE','synthetic_morphologies':len(cases),
             'structure':{'nominal':1,'one_parameter_boundaries':32,'combined_moderate':1,'coupled_seeded':random_cases},
             'adversarial_evaluations':adversary['evaluations'],'starting_poses':len(capture['rows']),
             'capture_proven':0,'capture_unknown':len(capture['rows']),
             'smallest_conditional_witness':smallest,'capability_counts':capabilities['within_counterfactual_capacity'],
             'eye_only_rigid_null_modes':observability['eye_only']['unconstrained_rigid_modes'],
             'surface_demands':surface_demands,
             'human_fit':False,'population_statistics':False,'whole_face_complete':False,
             'upstream_dependencies':source['unresolved'],
             'runtime':{'python':sys.version.split()[0],'numpy':np.__version__},
             'physical_experiment':'Unpowered adjustable headform alignment study with registered protected references and independent pose metrology; qualify support/seal travel and identify false seated states before human use'}
    save(output/'summary.json',summary)
    return summary


def digest_source(source):
    return sha256(json.dumps(source,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path)
    p.add_argument('--replay',type=Path);p.add_argument('--grid',type=int,default=7)
    p.add_argument('--random-cases',type=int,default=16)
    args=p.parse_args()
    if args.replay:
        d=json.loads(args.replay.read_text());d=d.get('face',d)
        source=source_snapshot()
        expected=sha256(Path(__file__).with_name('adversarial_fit_proof.py').read_bytes()).hexdigest()
        if set(d.get('parameters',{}))!=set(BOUNDS) or d.get('source_main')!=source['main'] or \
                d.get('generator_sha256')!=expected or d.get('source_snapshot_digest')!=digest_source(source):
            raise ValueError('Incomplete or stale witness; refusing nominal/default replay')
        v=Variation(**d['parameters'])
        save(args.output,{'face':face(v,include_mesh=True),'registration':solve_registration(v)})
    else:
        r=campaign(args.output,args.random_cases,args.grid)
        print(json.dumps({k:r[k] for k in ('main','decision','synthetic_morphologies','adversarial_evaluations','starting_poses')}))
