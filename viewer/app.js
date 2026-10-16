import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { TessellateModifier } from 'three/addons/modifiers/TessellateModifier.js';

/**
 * MASCK ONE — source-informed 3D concept viewer.
 * Geometric parameters and CMF tokens are drawn from:
 * config/masck_one_authority.yaml
 * config/masck_brand_authority.yaml
 * docs/BRAND_ARCHITECTURE.md
 * docs/CORE_SKETCH_NON_NEGOTIABLES.md
 *
 * This is intentionally NOT a native engineering STEP tessellation.
 * Shell curvature, internal mechanical placements and dock shape are visual studies.
 * Units in the scene are millimetres. +X wearer-right, +Y superior, +Z anterior.
 */
const AUTH = Object.freeze({
  body: {width:172, height:210, wall:1.8},
  eye: {left:[-31.5,35],right:[31.5,35],width:46,height:30},
  mouth: {center:[0,-50],width:58,height:32},
  nostril: {left:[-10.5,-7.5],right:[10.5,-7.5]},
  actuators:4,
  water: {size:[26,25,10],capacityMl:6.5},
  cartridge: {size:[74,36,20],minimumRetainedMl:35},
  seamGap:0.4,
  colors: {shell:'#E9E5DC',control:'#DED9CF',interface:'#CFC8BC',mechanics:'#454542',optical:'#F2EFE7'}
});

const canvas=document.getElementById('three-canvas');
const stage=canvas.closest('.stage');
const scene=new THREE.Scene();
const camera=new THREE.PerspectiveCamera(32,1,0.1,1600);
camera.position.set(93,42,480);
const renderer=new THREE.WebGLRenderer({canvas,alpha:true,antialias:true,preserveDrawingBuffer:true,powerPreference:'high-performance'});
renderer.setPixelRatio(Math.min(devicePixelRatio||1,2));
renderer.outputColorSpace=THREE.SRGBColorSpace;
renderer.toneMapping=THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure=1.85;
renderer.shadowMap.enabled=true;
renderer.shadowMap.type=THREE.PCFSoftShadowMap;
const environment=new RoomEnvironment();
const pmrem=new THREE.PMREMGenerator(renderer);
scene.environment=pmrem.fromScene(environment,0.035).texture;
pmrem.dispose();
const hemi=new THREE.HemisphereLight(0xffffff,0x8b8377,2.25); scene.add(hemi);
const key=new THREE.DirectionalLight(0xfff9eb,4.6);
key.position.set(-120,180,270);key.castShadow=true;
key.shadow.mapSize.set(2048,2048);key.shadow.camera.left=-280;key.shadow.camera.right=280;
key.shadow.camera.top=280;key.shadow.camera.bottom=-280;key.shadow.camera.near=1;key.shadow.camera.far=800;
key.shadow.bias=-0.00016;key.shadow.normalBias=0.018;scene.add(key);
const fill=new THREE.DirectionalLight(0xd3d9de,2.2);fill.position.set(210,65,120);scene.add(fill);
const rimLight=new THREE.DirectionalLight(0xffffff,2.7);rimLight.position.set(65,-85,-190);scene.add(rimLight);
const ground=new THREE.Mesh(new THREE.PlaneGeometry(900,900),new THREE.ShadowMaterial({opacity:0.15}));
ground.position.z=-120;ground.receiveShadow=true;scene.add(ground);

const mat={
  shell:new THREE.MeshPhysicalMaterial({color:AUTH.colors.shell,roughness:0.44,metalness:0.035,clearcoat:0.22,clearcoatRoughness:0.54,side:THREE.DoubleSide}),
  inside:new THREE.MeshPhysicalMaterial({color:0xbeb8ae,roughness:0.72,metalness:0.015,side:THREE.DoubleSide}),
  elastomer:new THREE.MeshPhysicalMaterial({color:AUTH.colors.interface,roughness:0.82,metalness:0.0,clearcoat:0.05,side:THREE.DoubleSide}),
  seal:new THREE.MeshPhysicalMaterial({color:0xa8a49b,roughness:0.94,metalness:0.0}),
  structural:new THREE.MeshStandardMaterial({color:0x787873,metalness:0.38,roughness:0.45}),
  dark:new THREE.MeshPhysicalMaterial({color:AUTH.colors.mechanics,metalness:0.22,roughness:0.63}),
  graphite:new THREE.MeshPhysicalMaterial({color:0x393b38,metalness:0.44,roughness:0.48}),
  bearing:new THREE.MeshPhysicalMaterial({color:0xb8b7af,roughness:0.38,metalness:0.2}),
  liquid:new THREE.MeshPhysicalMaterial({color:0xc5c7c3,roughness:0.17,metalness:0.03,transmission:0.18,thickness:1.5,transparent:true,opacity:0.78}),
  tubing:new THREE.MeshStandardMaterial({color:0x8c948e,roughness:0.53,metalness:0.15}),
  optical:new THREE.MeshPhysicalMaterial({color:AUTH.colors.optical,roughness:0.23,emissive:0xece6d5,emissiveIntensity:0.08}),
  strap:new THREE.MeshPhysicalMaterial({color:0xbcb8ae,roughness:0.91,metalness:0.0,side:THREE.DoubleSide}),
  pad:new THREE.MeshPhysicalMaterial({color:0xd2cabf,roughness:0.84,metalness:0.0}),
  dock:new THREE.MeshPhysicalMaterial({color:0xd8d4cc,roughness:0.53,clearcoat:0.18,clearcoatRoughness:0.6}),
  ceramic:new THREE.MeshPhysicalMaterial({color:AUTH.colors.control,roughness:0.31,clearcoat:0.20,clearcoatRoughness:0.46})
};

const rig=new THREE.Group();scene.add(rig);
const productRoot=new THREE.Group();rig.add(productRoot);
const assembly={};
for(const key of ['shell','interface','actuators','fluid','waste','retention','frame']){
  const g=new THREE.Group();g.name=key;productRoot.add(g);assembly[key]=g;
}
const dockGroup=new THREE.Group();rig.add(dockGroup);
assembly.dock=dockGroup;
const anchors={};
const formMaterial=mat.shell;

// The silhouette is deliberately sculptural and frameless: neither goggles
// nor a respirator, with aperture sizes and positions from the authority.
function makeOutline(){
  const s=new THREE.Shape();
  s.moveTo(0,103);
  s.bezierCurveTo(35,105,70,93,82,70);
  s.bezierCurveTo(89,50,87,22,84,-6);
  s.bezierCurveTo(83,-45,70,-81,42,-98);
  s.bezierCurveTo(21,-110,-21,-110,-42,-98);
  s.bezierCurveTo(-70,-81,-83,-45,-84,-6);
  s.bezierCurveTo(-87,22,-89,50,-82,70);
  s.bezierCurveTo(-70,93,-35,105,0,103);
  return s;
}
function ovalHole(x,y,rx,ry){
  const p=new THREE.Path();
  p.absellipse(x,y,rx,ry,0,Math.PI*2,true,0);
  return p;
}
function formShape(){
  const s=makeOutline();
  for(const c of [AUTH.eye.left,AUTH.eye.right])s.holes.push(ovalHole(c[0],c[1],AUTH.eye.width/2,AUTH.eye.height/2));
  s.holes.push(ovalHole(0,AUTH.mouth.center[1],AUTH.mouth.width/2,AUTH.mouth.height/2));
  for(const c of [AUTH.nostril.left,AUTH.nostril.right])s.holes.push(ovalHole(c[0],c[1],5,5.7));
  return s;
}
function faceDepth(x,y){
  const px=Math.max(0,1-Math.pow(Math.abs(x)/93,2));
  const py=Math.max(0,1-Math.pow(Math.abs(y-4)/129,2));
  const cheek=17*Math.pow(px*py,0.8);
  const nose=13*Math.exp(-Math.pow(x/18,2)-Math.pow((y+2)/36,2));
  const brow=2.8*Math.exp(-Math.pow((y-52)/21,2));
  const chin=3.2*Math.exp(-Math.pow((y+81)/30,2));
  return cheek+nose+brow+chin+2.0;
}
function moldedShell(){
  const sh=formShape();
  let geo=new THREE.ExtrudeGeometry(sh,{depth:AUTH.body.wall,steps:1,bevelEnabled:true,bevelThickness:.7,bevelSize:.7,bevelSegments:4,curveSegments:32});
  geo=new TessellateModifier(11,5).modify(geo);
  const p=geo.getAttribute('position');
  for(let i=0;i<p.count;i++){
    const x=p.getX(i),y=p.getY(i),z=p.getZ(i);
    p.setZ(i,z+faceDepth(x,y));
  }
  geo.computeVertexNormals();
  geo.computeBoundingSphere();
  return geo;
}
function mesh(geometry,material,parent,position=[0,0,0],rotation=null){
  const m=new THREE.Mesh(geometry,material);m.position.set(...position);
  if(rotation)m.rotation.set(...rotation);
  m.castShadow=true;m.receiveShadow=true;parent.add(m);return m;
}
function rounded(size,radius,material,parent,position){
  return mesh(new RoundedBoxGeometry(...size,6,radius),material,parent,position);
}
function tube(parent,pts,radius,material,closed=false){
  const curve=new THREE.CatmullRomCurve3(pts.map(p=>new THREE.Vector3(...p)),closed,'centripetal');
  return mesh(new THREE.TubeGeometry(curve,Math.max(28,pts.length*10),radius,8,closed),material,parent);
}
function zAt(x,y,offset=0){return faceDepth(x,y)+offset;}
const shell=mesh(moldedShell(),formMaterial,assembly.shell);
anchors.shell=[0,0,30];

// Shell inner skin. This sits beneath the curved A-surface and is distinct
// from the independent facial-contact mechanisms.
const inner=mesh(moldedShell(),mat.inside,assembly.interface,[0,0,-4.6]);
inner.scale.set(.986,.985,.994);

// Contact system: discrete compliant islands and a peripheral support envelope.
// Their exact positions and form are visual placeholders, not released human-fit geometry.
const padCenters=[[-60,7],[60,7],[-51,-28],[51,-28],[-31,-77],[31,-77],[-45,78],[45,78]];
for(let i=0;i<padCenters.length;i++){
  const [x,y]=padCenters[i];
  const pad=mesh(new THREE.SphereGeometry(1,20,14),mat.elastomer,assembly.interface,[x,y,zAt(x,y,-13)]);
  pad.scale.set(i<2?10:11,i<2?19:15,3.2);
  const rim=mesh(new THREE.TorusGeometry(i<2?9.2:10.2,1.1,8,44),mat.seal,assembly.interface,[x,y,zAt(x,y,-13.7)]);
  rim.scale.y=i<2?1.75:1.38;
}
anchors.interface=[0,0,-6];

// Interior structural ring and cross-spine.
const fPts=[[0,91,-14],[45,84,-17],[72,48,-18],[74,0,-17],[62,-60,-17],[32,-88,-17],[-32,-88,-17],[-62,-60,-17],[-74,0,-17],[-72,48,-18],[-45,84,-17]];
tube(assembly.frame,fPts,2.5,mat.structural,true);
tube(assembly.frame,[[0,92,-15],[0,66,-20],[0,6,-23],[0,-31,-20],[0,-93,-17]],2.0,mat.structural);
anchors.frame=[0,0,-16];

// Protected eyes/mouth are clear apertures through the shell; no raised goggle rims.
// An offset inset follows the aperture shape as a low-contrast elastomer edge study.
function apertureRim(x,y,rx,ry){
  const positions=[];for(let i=0;i<=68;i++){
    const t=i/68*Math.PI*2;
    positions.push([x+rx*Math.cos(t),y+ry*Math.sin(t),zAt(x+rx*Math.cos(t),y+ry*Math.sin(t),-3.1)]);
  }
  tube(assembly.interface,positions,.8,mat.seal,true);
}
for(const p of [AUTH.eye.left,AUTH.eye.right])apertureRim(p[0],p[1],23.5,15.5);
apertureRim(0,-50,29.5,16.5);

// M-Cut signature control on the upper forehead, nearly tone-on-tone.
const cap=mesh(new THREE.CylinderGeometry(5.0,5.0,1.05,48),mat.ceramic,assembly.shell,[0,76,zAt(0,76,3.8)],[Math.PI/2,0,0]);
const cutA=tube(assembly.shell,[[-2.5,77.5,zAt(0,76,5)],[0,74.7,zAt(0,76,5)],[2.5,77.5,zAt(0,76,5)]],.38,mat.optical);
anchors.control=[0,76,30];

// Four architecture-defined actuation units. Placement and actuator shape provisional.
const actLocations=[[-46,7],[46,7],[-42,-47],[42,-47]];
for(let i=0;i<AUTH.actuators;i++){
  const [x,y]=actLocations[i];
  mesh(new THREE.CylinderGeometry(11,11,8,40),mat.dark,assembly.actuators,[x,y,-29],[Math.PI/2,0,0]);
  mesh(new THREE.CylinderGeometry(7.2,7.2,8.7,40),mat.bearing,assembly.actuators,[x,y,-24],[Math.PI/2,0,0]);
  mesh(new THREE.TorusGeometry(7.4,.66,7,42),mat.structural,assembly.actuators,[x,y,-19]);
  for(let j=0;j<3;j++){
    mesh(new THREE.CylinderGeometry(1.05,1.05,3.0,10),mat.graphite,assembly.actuators,[x+Math.cos(j*2.094)*5,y+Math.sin(j*2.094)*5,-17],[Math.PI/2,0,0]);
  }
}
anchors.actuators=[0,-19,-26];

// Dedicated fluid routes. The fluid architecture and envelope are source-backed;
// the illustrated routing and component positions are NOT released CAD.
rounded(AUTH.water.size,4,mat.liquid,assembly.fluid,[58,-5,-25]);
rounded([24,5.5,11],2.4,mat.structural,assembly.fluid,[58,-19,-24]);
const branchPoints=[[-58,47],[-38,66],[0,64],[38,66],[58,47],[-67,0],[67,0],[-58,-40],[58,-40],[-25,-83],[25,-83]];
const source=[50,-12,-22];
tube(assembly.fluid,[source,[38,4,-24],[8,9,-24],[-10,1,-24],[-35,-15,-24]],1.15,mat.tubing);
tube(assembly.fluid,[source,[57,22,-24],[45,56,-23],[0,76,-23],[-46,56,-23]],1.0,mat.tubing);
tube(assembly.fluid,[source,[36,-34,-24],[24,-68,-21],[0,-77,-20],[-24,-68,-21]],1.0,mat.tubing);
for(let i=0;i<branchPoints.length;i++){
  const [x,y]=branchPoints[i];
  const mid=[x*.72,y*.78,-24];
  const end=[x,y,Math.min(-5,zAt(x,y,-18))];
  tube(assembly.fluid,[mid,[x*.89,y*.91,-19],end],.72,i%3===0?mat.liquid:mat.tubing);
  mesh(new THREE.SphereGeometry(1.55,14,8),mat.bearing,assembly.fluid,end);
}
anchors.fluid=[45,-4,-24];

// Removable lower cartridge: actual baseline envelope 74 × 36 × 20 mm.
rounded(AUTH.cartridge.size,5.5,mat.dark,assembly.waste,[0,-65,-28]);
rounded([64,2.2,13],1.0,mat.structural,assembly.waste,[0,-47,-29]);
for(let s of [-1,1]){
  rounded([5,14,14],1.8,mat.seal,assembly.waste,[s*31,-61,-28]);
}
tube(assembly.waste,[[-50,-41,-15],[-38,-63,-15],[-24,-65,-18]],1.55,mat.tubing);
tube(assembly.waste,[[50,-41,-15],[38,-63,-15],[24,-65,-18]],1.55,mat.tubing);
anchors.waste=[0,-63,-25];

// Rear retention band study. The quick-release safety requirement is source-backed;
// the latch shapes and strap routing below are provisional concept geometry.
for(const side of [-1,1]){
  const x=side;
  tube(assembly.retention,[[x*77,18,-11],[x*92,21,-24],[x*113,24,-56],[x*98,40,-86],[x*58,49,-99]],4.8,mat.strap);
  tube(assembly.retention,[[x*71,-34,-14],[x*96,-35,-27],[x*113,-20,-55],[x*99,18,-88],[x*58,49,-99]],4.0,mat.strap);
  rounded([14,13,7],3,mat.dark,assembly.retention,[x*96,19,-38]);
  rounded([8,6,8],2,mat.bearing,assembly.retention,[x*99,19,-34]);
}
tube(assembly.retention,[[-58,49,-99],[-36,59,-114],[0,63,-120],[36,59,-114],[58,49,-99]],5.7,mat.strap);
anchors.retention=[0,14,-79];

// Dock: calm receptacle architecture. Completely provisional geometry.
rounded([197,18,113],17,mat.dock,dockGroup,[0,-145,-43]);
rounded([167,3,86],11,mat.ceramic,dockGroup,[0,-134.5,-43]);
rounded([93,2,25],7,mat.dark,dockGroup,[0,-132.5,-42]);
for(const x of [-52,52]){
  rounded([13,49,14],6,mat.dock,dockGroup,[x,-108,-59]);
  rounded([13,6,22],3,mat.seal,dockGroup,[x,-82,-51]);
}
rounded([42,2.5,14],2,mat.optical,dockGroup,[0,-134,-5]);
anchors.dock=[0,-133,-43];

// Subtle contact shadow on the dock during dock view, invisible otherwise.
const dockShadow=new THREE.Mesh(new THREE.PlaneGeometry(900,900),new THREE.ShadowMaterial({opacity:0.21}));
dockShadow.rotation.x=-Math.PI/2;dockShadow.position.y=-155.5;dockShadow.receiveShadow=true;dockGroup.add(dockShadow);

const controls=new OrbitControls(camera,canvas);
controls.enableDamping=true;controls.dampingFactor=.06;controls.enablePan=false;
controls.minDistance=260;controls.maxDistance=800;
controls.target.set(0,-1,-12);
controls.maxPolarAngle=Math.PI;controls.minPolarAngle=0;
controls.autoRotate=false;controls.autoRotateSpeed=.62;
controls.update();
const isReduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
let currentMode='assembled';
let activeComponent='shell';
let selectedSwatch='ivory';
const modeCaptions={
  assembled:'An uninterrupted sculpted exterior. The mechanics stay quiet and out of sight.',
  exploded:'Subassemblies separated to reveal engineering systems. Internal positions are illustrative.',
  ghost:'A translucent shell reveals the architecture within; placement is a provisional visual study.',
  dock:'The envisioned prepare–wear–return experience. Dock geometry remains a concept.'
};
const placements={
  assembled:{shell:[0,0,0],interface:[0,0,0],frame:[0,0,0],actuators:[0,0,0],fluid:[0,0,0],waste:[0,0,0],retention:[0,0,0]},
  ghost:{shell:[0,0,0],interface:[0,0,0],frame:[0,0,0],actuators:[0,0,0],fluid:[0,0,0],waste:[0,0,0],retention:[0,0,0]},
  exploded:{shell:[0,4,77],interface:[0,1,33],frame:[0,0,-3],actuators:[0,-3,-37],fluid:[28,2,-52],waste:[0,-32,-78],retention:[0,12,-75]},
  dock:{shell:[0,0,0],interface:[0,0,0],frame:[0,0,0],actuators:[0,0,0],fluid:[0,0,0],waste:[0,0,0],retention:[0,0,0]}
};
for(const key of Object.keys(placements.assembled))assembly[key].userData.to=placements.assembled[key].slice();
function setMode(mode){
  currentMode=mode;
  const positions=placements[mode];
  for(const key of Object.keys(positions))assembly[key].userData.to=positions[key].slice();
  document.querySelectorAll('.mode-btn').forEach(el=>el.classList.toggle('active',el.dataset.mode===mode));
  document.getElementById('mode-caption').textContent=modeCaptions[mode];
  document.getElementById('display-mode').textContent=({assembled:'ASSEMBLED / A-SURFACE',exploded:'EXPLODED / SYSTEMS',ghost:'GHOST / ENGINEERING',dock:'DOCK / OWNERSHIP LOOP'})[mode];
  if(mode==='dock')rig.userData.dock=true;else rig.userData.dock=false;
  // Only the shell goes translucent. Components remain physically present.
  formMaterial.transparent=mode==='ghost';
  formMaterial.opacity=mode==='ghost'?.18:1;
  formMaterial.depthWrite=mode!=='ghost';
  // The backing shell should not obscure x-ray internal systems.
  inner.material.visible=mode!=='ghost';
  const dest=mode==='dock'?new THREE.Vector3(95,40,580):new THREE.Vector3(93,42,480);
  if(!isReduced)camera.userData.dest=dest;else{camera.position.copy(dest);controls.update();}
}
document.querySelectorAll('.mode-btn').forEach(el=>el.addEventListener('click',()=>setMode(el.dataset.mode)));

const materialNotes={
  ivory:['MINERAL IVORY','#E9E5DC','Fine, low-gloss satin over a warm engineering-polymer shell.'],
  stone:['SOFT STONE','#CFC8BC','Cleanable, compliant soft-matte contact material; final grade still unqualified.'],
  graphite:['SMOKE GRAPHITE','#454542','Warm recessive graphite for mechanisms, with restrained reflectance.']
};
function setSwatch(which){
  selectedSwatch=which;
  document.querySelectorAll('.swatch-row').forEach(el=>el.classList.toggle('active',el.dataset.swatch===which));
  const data=materialNotes[which];
  document.getElementById('material-name').textContent=data[0];
  document.getElementById('material-hex').textContent=data[1];
  document.getElementById('material-desc').textContent=data[2];
  if(which==='ivory')setMode('assembled');
  if(which==='stone'){setMode('exploded');selectComponent('interface',false);}
  if(which==='graphite'){setMode('ghost');selectComponent('actuators',false);}
}
document.querySelectorAll('.swatch-row').forEach(el=>el.addEventListener('click',()=>setSwatch(el.dataset.swatch)));
function selectComponent(comp,changeMode=true){
  activeComponent=comp;
  document.querySelectorAll('.component-item').forEach(el=>el.classList.toggle('active',el.dataset.component===comp));
  if(changeMode){if(comp==='shell')setMode('assembled');else if(comp==='dock')setMode('dock');else setMode('exploded');}
  const focus=anchors[comp]||[0,0,0];
  const offset=comp==='dock'?[-4,37,10]:[focus[0]*.18,focus[1]*.24,focus[2]*.1];
  controls.target.set(...offset);
}
document.querySelectorAll('.component-item').forEach(el=>el.addEventListener('click',()=>selectComponent(el.dataset.component)));
document.getElementById('detail-toggle').addEventListener('click',()=>{
  const details=document.getElementById('disclaimer');
  details.hidden=!details.hidden;
  document.getElementById('detail-toggle').lastElementChild.textContent=details.hidden?'↗':'−';
});
document.getElementById('front-btn').addEventListener('click',()=>{
  camera.userData.dest=new THREE.Vector3(0,0,475);
  controls.target.set(0,0,0);
});
document.getElementById('iso-btn').addEventListener('click',()=>{
  camera.userData.dest=new THREE.Vector3(93,42,480);
  controls.target.set(0,0,-12);
});
document.getElementById('rotate-btn').addEventListener('click',e=>{
  controls.autoRotate=!controls.autoRotate;
  e.currentTarget.classList.toggle('active',controls.autoRotate);
  e.currentTarget.setAttribute('aria-pressed',String(controls.autoRotate));
});
document.getElementById('capture-btn').addEventListener('click',()=>{
  renderer.render(scene,camera);
  const link=document.createElement('a');
  link.download='masck-one-3d-'+currentMode+'.png';
  link.href=renderer.domElement.toDataURL('image/png');
  link.click();
});

const resize=()=>{
  const {width,height}=stage.getBoundingClientRect();
  if(width<1||height<1)return;
  camera.aspect=width/height;camera.updateProjectionMatrix();
  renderer.setSize(Math.floor(width),Math.floor(height),false);
};
new ResizeObserver(resize).observe(stage);resize();

// Prevent high frame-rate cost when the tab is hidden.
const clock=new THREE.Clock();
let previous=performance.now();
function tick(now){
  requestAnimationFrame(tick);
  const dt=Math.min(.05,(now-previous)/1000||.016);
  previous=now;
  if(document.hidden)return;
  const k=isReduced?1:1-Math.pow(.0002,dt);
  for(const [name,g] of Object.entries(assembly)){
    if(name==='dock')continue;
    const target=g.userData.to||[0,0,0];
    g.position.x=THREE.MathUtils.lerp(g.position.x,target[0],k);
    g.position.y=THREE.MathUtils.lerp(g.position.y,target[1],k);
    g.position.z=THREE.MathUtils.lerp(g.position.z,target[2],k);
  }
  const dockAmount=rig.userData.dock?1:0;
  dockGroup.visible=dockAmount===1||dockGroup.scale.x>.015;
  const scale=rig.userData.dock?1:.0001;
  dockGroup.scale.lerp(new THREE.Vector3(scale,scale,scale),k);
  productRoot.position.y=THREE.MathUtils.lerp(productRoot.position.y,rig.userData.dock?46:0,k);
  productRoot.position.z=THREE.MathUtils.lerp(productRoot.position.z,rig.userData.dock?17:0,k);
  if(camera.userData.dest){
    camera.position.lerp(camera.userData.dest,k*.6);
    if(camera.position.distanceTo(camera.userData.dest)<.35)camera.userData.dest=null;
  }
  controls.update();
  renderer.render(scene,camera);
}
requestAnimationFrame(tick);
document.getElementById('load-status').textContent='3D STUDY READY';
document.getElementById('load-status').classList.add('ready');
console.info('MASCK ONE design reconstruction initialized. Engineering source remains authoritative; visuals are not validation evidence.');
