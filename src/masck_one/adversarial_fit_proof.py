"""Isolated synthetic fit proof. Never a population model or production controller.

The released pose envelope is reused, including fixed Z. Anatomical landmark
residual acceptance is UNKNOWN. Capacity bands are explicit sensitivity inputs,
not new human-use tolerances. Numerical registration is not passive acquisition.
"""
from dataclasses import dataclass, asdict, fields
from hashlib import sha256
from pathlib import Path
import json
import math
import numpy as np
from scipy.optimize import minimize

from .authority import load_authority
from .facial_surface import build_planar_development_surface
from .spatial import RigidTransform, Vector3

SCHEMA='MASCK_SYNTHETIC_FIT_PROOF_1'
FRAME='MASCK_ONE_AUTHORITY_WORLD_MM'
ROOT=Path(__file__).resolve().parents[2]


class FitProofError(ValueError):
    pass


def digest(value):
    return sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def number(v):
    if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):
        raise FitProofError('finite real required')
    return float(v)


# All lengths are perturbations in mm from the released planar reference.
# These bounds deliberately include difficult shapes. They are not percentiles,
# supported fit claims, human dimensions, or modifications to authority.
BOUNDS={
    'face_width':(-16.,16.),'face_height':(-18.,18.),
    'cheek_prominence':(-8.,12.),'cheek_curvature':(-6.,6.),
    'brow_projection':(-6.,10.),'forehead_curvature':(-6.,8.),
    'bridge_projection':(-5.,14.),'nasal_width':(-6.,6.),
    'lower_face_projection':(-8.,10.),'chin_projection':(-6.,12.),
    'jaw_width':(-12.,12.),'eye_spacing':(-12.,12.),
    'mouth_y':(-10.,10.),'mouth_width':(-8.,8.),
    'asymmetry':(-8.,8.),'local_curvature':(-5.,5.),
}


@dataclass(frozen=True)
class Variation:
    face_width: float=0.
    face_height: float=0.
    cheek_prominence: float=0.
    cheek_curvature: float=0.
    brow_projection: float=0.
    forehead_curvature: float=0.
    bridge_projection: float=0.
    nasal_width: float=0.
    lower_face_projection: float=0.
    chin_projection: float=0.
    jaw_width: float=0.
    eye_spacing: float=0.
    mouth_y: float=0.
    mouth_width: float=0.
    asymmetry: float=0.
    local_curvature: float=0.

    def __post_init__(self):
        for f in fields(self):
            v=number(getattr(self,f.name));lo,hi=BOUNDS[f.name]
            if not lo<=v<=hi:raise FitProofError('outside explicit synthetic range: '+f.name)

    @property
    def normalized_distance(self):
        return math.sqrt(sum((v/max(abs(x) for x in BOUNDS[k]))**2 for k,v in asdict(self).items()))


def source_snapshot(root=ROOT):
    path=root/'analysis/fit_proof/sources.json'
    data=json.loads(path.read_text())
    for row in data['consumed_files']:
        p=root/row['path']
        if not p.is_file() or sha256(p.read_bytes()).hexdigest()!=row['sha256']:
            raise FitProofError('missing/stale consumed source: '+row['path'])
    return data


def rotation(angles):
    r=RigidTransform.from_extrinsic_xyz(Vector3(0,0,0),roll_x_deg=number(angles[0]),
             pitch_y_deg=number(angles[1]),yaw_z_deg=number(angles[2]))
    return np.asarray(r.rotation.rows)


def transform(points, pose):
    pose=np.array([number(x) for x in pose])
    if pose.shape!=(6,):raise FitProofError('pose order tx,ty,tz,rx,ry,rz')
    return np.asarray(points)@rotation(pose[3:]).T+pose[:3]


def nominal_landmarks(authority=None):
    a=authority or load_authority()
    e=a.get('geometry','eye','centers_mm');n=a.get('geometry','nostrils','centers_mm')
    m=a.get('geometry','mouth','center_mm')
    return {'EYE_LEFT':[*e['left'],0.], 'EYE_RIGHT':[*e['right'],0.],
            'NOSTRIL_LEFT':[*n['left'],0.], 'NOSTRIL_RIGHT':[*n['right'],0.],
            'MOUTH':[*m,0.]}


def warp(points, v:Variation, authority=None):
    """Smooth explicit 2.5D deformation of a reference mesh, not anatomical fitting."""
    a=authority or load_authority();w,h=a.pair('geometry','outer_xy_envelope_mm')
    q=np.asarray(points,dtype=float);x,y,z=q.T
    def g(cx,cy,sx,sy):return np.exp(-((x-cx)/sx)**2-((y-cy)/sy)**2)
    left=g(-w*.26,0,24,35);right=g(w*.26,0,24,35)
    eyes_l=g(-31.5,35,16,18);eyes_r=g(31.5,35,16,18)
    # Whole outline and regional distortions can be varied independently. Their
    # coupled landmark consequences are measured, never normalized away.
    xx=x*(1+v.face_width/w)+v.eye_spacing*.5*(eyes_r-eyes_l)
    xx+=v.nasal_width*x/21*g(0,-7.5,19,15)
    xx+=v.jaw_width*x/w*g(0,-75,70,25)
    xx+=v.mouth_width*x/58*g(0,-50,35,16)
    yy=y*(1+v.face_height/h)+v.mouth_y*g(0,-50,35,15)
    yy+=v.asymmetry*(right-left)*.25
    zz=z+v.cheek_prominence*(left+right)
    zz+=v.cheek_curvature*(g(-44,0,13,20)+g(44,0,13,20)-.5*(left+right))
    zz+=v.brow_projection*(g(-32,48,24,12)+g(32,48,24,12))
    zz+=v.forehead_curvature*g(0,75,45,22)+v.bridge_projection*g(0,12,13,26)
    zz+=v.lower_face_projection*g(0,-65,55,25)+v.chin_projection*g(0,-87,28,15)
    zz+=v.asymmetry*(right-left)+v.local_curvature*g(23,-28,11,11)
    return np.column_stack((xx,yy,zz))


def face(v, include_mesh=False):
    source=source_snapshot();a=load_authority();names=list(nominal_landmarks(a))
    nominal=np.array(list(nominal_landmarks(a).values()));points=warp(nominal,v,a)
    result={'schema':SCHEMA,'generator_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
            'source_main':source['main'],'source_snapshot_digest':digest(source),'frame':FRAME,
            'nominal_source':'build_planar_development_surface; landmark anatomical depths unresolved',
            'parameters':asdict(v),'bounds':{k:{'range_mm':list(b),'class':'SYNTHETIC_ADVERSARIAL_EXPLORATION'} for k,b in BOUNDS.items()},
            'landmarks':dict(zip(names,points.tolist())), 'population_percentile':None,
            'anatomical_validation_eligible':False}
    if include_mesh:
        surface=build_planar_development_surface(a)
        vertices=np.array([p.as_tuple() for p in surface.mesh.vertices])
        changed=warp(vertices,v,a)
        triangles=np.array(surface.mesh.triangles)
        # Mesh is debug/reference only; reject folded projected cells. Do not
        # export an invalid adversarial parameterization as a valid face.
        b=vertices[triangles];c=changed[triangles]
        def area(q):
            u=q[:,1,:2]-q[:,0,:2];v=q[:,2,:2]-q[:,0,:2]
            return u[:,0]*v[:,1]-u[:,1]*v[:,0]
        folded=np.where(area(b)*area(c)<=0)[0].tolist()
        result.update({'surface':surface.manifest(),'vertices':changed.tolist(),
                       'triangles':triangles.tolist(),'folded_cells':folded,
                       'mesh_status':'FOLDED_REFERENCE_INVALID' if folded else 'VALID_SYNTHETIC_REFERENCE_MESH'})
    result['identity']=digest(result)
    return result


def pair_distance_lower_bound(points, targets):
    """Rigid-invariant lower bound on max landmark residual, valid for all SE(3)."""
    best=(0.,None)
    for i in range(len(points)):
        for j in range(i):
            bound=abs(np.linalg.norm(points[i]-points[j])-np.linalg.norm(targets[i]-targets[j]))/2
            if bound>best[0]:best=(float(bound),(j,i))
    return {'lower_bound_mm':best[0],'pair':best[1],
            'proof':'Triangle inequality: |d_face-d_target| <= residual_i+residual_j'}


def solve_registration(v, initial=(0.,0.,0.,0.,0.,0.), extra_z_mm=0., target_scale=(1.,1.), multistart=True, initial_only=False):
    """Constrained minimax registration. A found minimum is not a global no-fit proof."""
    a=load_authority();nom=np.array(list(nominal_landmarks(a).values()));p=warp(nom,v,a)
    target=nom*np.array([*target_scale,1.])
    radius=a.number('geometry','misregistration','translation_radial_max_mm')
    angle=a.number('geometry','misregistration','rotation_max_deg')
    if extra_z_mm<0 or not math.isfinite(extra_z_mm):raise FitProofError('invalid abstract Z capability')
    init=np.array([number(x) for x in initial]);
    if init.shape!=(6,):raise FitProofError('six pose coordinates required')
    bounds=[(-radius,radius),(-radius,radius),(-extra_z_mm,extra_z_mm)]+[(-angle,angle)]*3+[(0.,200.)]
    def residual(x):return np.linalg.norm(transform(p,x[:6])-target,axis=1)
    def constraints(x):return np.r_[radius**2-x[0]**2-x[1]**2,x[6]-residual(x)]
    seeds=[init] if initial_only else [np.zeros(6),init]
    if multistart and not initial_only:
        for axis in (3,4,5):
            for sign in (-1,1):
                seed=np.zeros(6);seed[axis]=sign*angle;seeds.append(seed)
    candidates=[]
    for seed in seeds:
        seed=np.array([max(lo,min(hi,x)) for x,(lo,hi) in zip(seed,bounds)])
        if np.linalg.norm(seed[:2])>radius:seed[:2]*=radius/np.linalg.norm(seed[:2])
        x=np.r_[seed,max(residual(seed))+.01]
        r=minimize(lambda x:x[6],x,method='SLSQP',bounds=bounds,
                   constraints={'type':'ineq','fun':constraints},options={'maxiter':180,'ftol':1e-9})
        if np.min(constraints(r.x))>=-1e-6:
            candidates.append((float(max(residual(r.x))),r.x[:6].tolist(),bool(r.success)))
    lower=pair_distance_lower_bound(p,target)
    if not candidates:return {'status':'NUMERICAL_INDETERMINATE','rigid_invariant_bound':lower,'whole_fit':'UNKNOWN'}
    candidates.sort(key=lambda x:(x[0],x[1]));value,pose,converged=candidates[0]
    near=[q for f,q,_ in candidates if f<=value+1e-5]
    separation=max((float(np.linalg.norm(np.array(x)-y)) for x in near for y in near),default=0.)
    return {'status':'REGISTERED_CANDIDATE_NOT_FIT_APPROVAL','pose':pose,'max_residual_mm':value,
            'per_landmark_residual_mm':dict(zip(nominal_landmarks(a),residual(np.r_[pose,value]).tolist())),
            'rigid_invariant_bound':lower,'optimizer_converged':converged,
            'near_equal_pose_separation_mixed_units':separation,
            'pose_limits':{'xy_radius_mm':radius,'extrinsic_xyz_each_deg':angle,
                           'z_mm':extra_z_mm,'z_status':'ABSTRACT_CAPABILITY_ONLY' if extra_z_mm else 'OWNER_FIXED_ZERO'},
            'adjustments':{'existing_product_adjustments':[], 'abstract_target_scale':list(target_scale)},
            'landmark_residual_acceptance_mm':None,'whole_fit':'UNKNOWN',
            'support':'UNKNOWN','seal':'UNKNOWN','passive_alignment':'UNKNOWN','region_access':'UNKNOWN'}


def capacity_result(registration, allowance_mm):
    """Counterfactual capacity sensitivity, never a qualified fit limit."""
    b=number(allowance_mm)
    if b<0:raise FitProofError('negative capacity')
    if registration.get('rigid_invariant_bound',{}).get('lower_bound_mm',0)>b+1e-8:
        return 'PROVEN_RIGID_CAPACITY_FAILURE'
    if registration.get('max_residual_mm',math.inf)<=b+1e-6:return 'CANDIDATE_WITHIN_ASSUMED_CAPACITY'
    return 'UNRESOLVED_NUMERICAL_OR_CAPACITY_FAILURE'


def assess(evidence):
    """Unknown required inputs block A/B/C product fit judgments."""
    required=('registered_face','protected_geometry','support','seal','required_region_access',
              'treatment_reach','thermal_reach','passive_constraints','emergency_release')
    failed=[k for k in required if evidence.get(k)=='FAIL']
    unknown=[k for k in required if evidence.get(k) not in ('PASS','FAIL')]
    return {'decision':'C_ARCHITECTURAL_FIT_DEFECT' if failed else
                      ('D_DIGITAL_INDETERMINATE' if unknown else 'A_ROBUST_DIGITAL_FEASIBILITY'),
            'failed':failed,'unknown':unknown,'human_validation':False}


def alignment_rank(points):
    """Geometric observability of labeled point datums, not an alignment mechanism."""
    blocks=[]
    for x,y,z in points:
        skew=np.array([[0,-z,y],[z,0,-x],[-y,x,0]])
        blocks.append(np.column_stack((np.eye(3),-skew)))
    a=np.vstack(blocks);_,singular,vt=np.linalg.svd(a,full_matrices=True)
    rank=int(np.linalg.matrix_rank(a))
    return {'rank':rank,'unconstrained_rigid_modes':6-rank,'nullspace':vt[rank:].tolist(),
            'singular_values':singular.tolist(),'physical_datum_selection':'UNKNOWN'}


def boundary_search(parameter, signed_endpoint, capacity_mm, steps=18):
    """Bisection along one specified ray, not a global minimum morphology claim."""
    lo=0.;hi=number(signed_endpoint);evaluations=[]
    end=solve_registration(Variation(**{parameter:hi}),multistart=False)
    if capacity_result(end,capacity_mm)=='CANDIDATE_WITHIN_ASSUMED_CAPACITY':
        return {'status':'NO_FAILURE_BRACKET','parameter':parameter,'conditional_capacity_mm':capacity_mm}
    for _ in range(steps):
        mid=(lo+hi)/2;v=Variation(**{parameter:mid});r=solve_registration(v,multistart=False)
        status=capacity_result(r,capacity_mm);evaluations.append((mid,status))
        if status=='CANDIDATE_WITHIN_ASSUMED_CAPACITY':lo=mid
        else:hi=mid
    return {'parameter':parameter,'conditional_capacity_mm':capacity_mm,
            'nearest_candidate_value':lo,'nearest_nonpassing_value':hi,
            'bracket_width_mm':abs(hi-lo),'search_scope':'ONE_SYNTHETIC_PARAMETER_RAY',
            'passing':solve_registration(Variation(**{parameter:lo})),
            'failing':solve_registration(Variation(**{parameter:hi})), 'evaluations':evaluations}


def adversarial_search(seed=20260912, generations=8, population=12):
    """Deterministic differential mutation maximizes a rigid-invariant bound.

    Uses an analytic lower bound, so thousands of optimizer failures cannot be
    mistaken for geometric impossibility. Worst in explored set, not global.
    """
    rng=np.random.default_rng(seed);keys=list(BOUNDS)
    nom=np.array(list(nominal_landmarks().values()))
    def decode(x):return Variation(**{k:float(t*(BOUNDS[k][1] if t>=0 else -BOUNDS[k][0])) for k,t in zip(keys,x)})
    def score(x):return pair_distance_lower_bound(warp(nom,decode(x)),nom)['lower_bound_mm']
    pop=rng.uniform(-.65,.65,(population,len(keys)));scores=np.array([score(x) for x in pop]);count=population
    for _ in range(generations):
        for i in range(population):
            pool=[j for j in range(population) if j!=i];a,b,c=rng.choice(pool,3,replace=False)
            mutation=np.clip(pop[a]+.6*(pop[b]-pop[c]),-1,1)
            mask=rng.random(len(keys))<.65;mask[rng.integers(len(keys))]=True
            trial=np.where(mask,mutation,pop[i]);value=score(trial);count+=1
            if value>scores[i]:pop[i]=trial;scores[i]=value
    i=int(np.argmax(scores));v=decode(pop[i])
    return {'seed':seed,'evaluations':count,'algorithm':'DETERMINISTIC_DIFFERENTIAL_MUTATION_ON_RIGID_DISTANCE_BOUND',
            'variation':asdict(v),'lower_bound_mm':float(scores[i]),'registration':solve_registration(v),
            'global_optimum_claimed':False}
